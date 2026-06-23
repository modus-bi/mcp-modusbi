#!/usr/bin/env python3
"""Шаг 1 пайплайна манифеста: извлечь КАНДИДАТНЫЙ render-статус из бандла (эвристика).

Бандл — скомпилированный/минифицированный артефакт (не исходники TS). Надёжно отличить
"рендер читает ключ" от "панель настроек читает ключ" статикой нельзя (манглинг + панель≠рендер),
поэтому это КАНДИДАТЫ, а не истина. Скрипт ИЗМЕРЯЕТ точность кандидатов против браузер-вердиктов
(verdicts.json) — число даёт количественный ответ "почему бандла мало".

Эвристика на leaf (последний сегмент json-пути слага), по report.js+app.js:
  assign   = '{leaf}:'  (ключ присваивается как свойство — render/config его СТАВИТ)
  read     = '.{leaf}'  (свойство читается)
  panel    = вхождения рядом (<=90 симв) с onChange/value:/disabled (маркеры контрола панели)
  render_read = read НЕ рядом с panel-маркерами (похоже на чтение рендером)
Кандидат:
  absent           — leaf не найден
  renders-cand     — assign>0 ИЛИ render_read>0  (render ставит/читает)
  render-dead-cand — read>0 и все рядом с panel  (только панель читает, render не ставит)
"""
import json
import os
import re
from pathlib import Path
import collections

ROOT = Path(__file__).resolve().parents[1]
# Каталог с распакованным фронт-бандлом (report.*.js, app.*.js). Локальный артефакт —
# задаётся через env FRONTEND_BUNDLE_DIR (по умолчанию ./frontend-bundle рядом с репо).
BUNDLE = Path(os.environ.get("FRONTEND_BUNDLE_DIR", "frontend-bundle"))
FILES = ["report.c09c09ba357a139f9a42.js", "app.14ae364579b7400f5523.js"]

TABLE = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
V = json.loads((ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json").read_text(encoding="utf-8"))["verdicts"]

text = ""
for f in FILES:
    p = BUNDLE / f
    if p.exists():
        text += p.read_text(encoding="utf-8", errors="ignore") + "\n"

PANEL_MARK = re.compile(r"(onChange|value:|disabled:|label:|onToggle|Slider|TextField)")


def leaf_of(path):
    if not path:
        return ""
    path = path.split(" ")[0]
    seg = re.split(r"[.\[\]]+", path.strip("]"))
    return seg[-1] if seg else ""


def analyse(leaf):
    if not leaf or len(leaf) < 4 or not leaf[0].isalpha():
        return {"present": False, "skip": "leaf<4/нечитаем"}
    assigns = [m.start() for m in re.finditer(r"[,{(]\s*" + re.escape(leaf) + r":", text)]
    reads = [m.start() for m in re.finditer(r"\." + re.escape(leaf) + r"\b", text)]
    panel_reads = 0
    render_reads = 0
    for pos in reads:
        window = text[max(0, pos - 90): pos + 90]
        if PANEL_MARK.search(window):
            panel_reads += 1
        else:
            render_reads += 1
    present = bool(assigns or reads)
    if not present:
        cand = "absent"
    elif assigns or render_reads:
        cand = "renders-cand"
    else:
        cand = "render-dead-cand"
    return {"present": present, "assigns": len(assigns), "reads": len(reads),
            "panel_reads": panel_reads, "render_reads": render_reads, "cand": cand}


# leaf-коллизия: сколько РАЗНЫХ слагов делят один leaf (высокая → атрибуция к компоненту невозможна)
leaf_users = collections.Counter(leaf_of(r.get("effective") or r.get("json") or "") for r in TABLE)

rows = []
for r in TABLE:
    slug = r["slug"]
    leaf = leaf_of(r.get("effective") or r.get("json") or "")
    a = analyse(leaf)
    verd = V.get(slug, {}).get("v", "")
    a["leaf_shared_by_slugs"] = leaf_users.get(leaf, 0)
    # уточнение: render-dead-cand если панель доминирует над render-чтением и почти не присваивается
    if a.get("present") and not a.get("skip"):
        if a["panel_reads"] > a["render_reads"] and a["assigns"] <= max(1, a["panel_reads"] // 3):
            a["cand"] = "render-dead-cand"
    rows.append({"slug": slug, "leaf": leaf, "verdict": verd, **a})

# ── точность кандидатов vs браузер-вердикты (только ok/dead — где статус ясен) ──
# ok → ожидаем renders-cand; dead → ожидаем render-dead-cand
conf = collections.Counter()
graded = 0
hit = 0
for r in rows:
    if r["verdict"] not in ("ok", "dead"):
        continue
    if r.get("skip") or not r.get("present"):
        conf[(r["verdict"], "absent/skip")] += 1
        graded += 1
        continue
    expect = "renders-cand" if r["verdict"] == "ok" else "render-dead-cand"
    conf[(r["verdict"], r["cand"])] += 1
    graded += 1
    if r["cand"] == expect:
        hit += 1

acc = round(100 * hit / graded) if graded else 0
# доля render-dead, которые эвристика ВООБЩЕ поймала (recall на тяжёлых случаях)
dead_total = sum(1 for r in rows if r["verdict"] == "dead")
dead_caught = sum(1 for r in rows if r["verdict"] == "dead" and r.get("cand") == "render-dead-cand")
dead_caught_wrong = sum(1 for r in rows if r["verdict"] == "ok" and r.get("cand") == "render-dead-cand")
# коллизия: сколько ok/dead-слагов имеют leaf, делимый >1 слагом (атрибуция невозможна)
collide = sum(1 for r in rows if r["verdict"] in ("ok", "dead") and r.get("leaf_shared_by_slugs", 0) > 1)
base_rate = round(100 * sum(1 for r in rows if r["verdict"] == "ok") /
                  max(1, sum(1 for r in rows if r["verdict"] in ("ok", "dead"))))
out = {
    "_meta": {
        "purpose": "КАНДИДАТНЫЙ render-статус из бандла (эвристика) + точность vs браузер-вердикты",
        "files": FILES,
        "note": "бандл минифицирован → панель≠рендер неразличимы надёжно; это кандидаты, истину даёт браузер",
        "accuracy_vs_verdicts_pct": acc,
        "base_rate_pct": base_rate,
        "verdict": ("бандл-эвристика НЕ превосходит базовую долю — атрибуция к компоненту невозможна "
                    "(leaf-коллизия + мангленный render-модуль). Кандидаты = СЛАБЫЙ приор, истину даёт браузер."),
        "render_dead_recall": f"{dead_caught}/{dead_total} пойманных render-dead (ложно-dead на ok: {dead_caught_wrong})",
        "leaf_collision_ok_dead": f"{collide}/{graded} ok/dead-слагов имеют leaf, делимый >1 слагом (атрибуция невозможна)",
        "graded": graded, "hits": hit,
        "confusion": {f"{k[0]}→{k[1]}": v for k, v in sorted(conf.items())},
    },
    "candidates": rows,
}
(ROOT / "docs/architecture/readiness/audit/render_candidates.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK: {len(rows)} слагов. Точность кандидат↔вердикт (ok/dead): {acc}% ({hit}/{graded})")
print("Матрица (вердикт → кандидат):")
for k, v in sorted(conf.items()):
    print(f"  {k[0]:5} → {k[1]:18} : {v}")
