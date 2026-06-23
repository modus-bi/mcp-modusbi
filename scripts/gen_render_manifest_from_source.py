#!/usr/bin/env python3
"""АВТОРИТЕТНЫЙ render-манифест из ИСХОДНИКОВ фронта (bi_react-develop).

Решает «панель≠рендер» по-настоящему: render-код = SpecGenerator/adaptor/plugins адаптеров
(src/adaptors/**), панель = *ConfigEditor (исключаем), вендорная либа amcharts3/amcharts/** (исключаем).
Для каждого слага проверяем, читает ли RENDER `config.<leaf>` → renders / render-dead. Сверяем с
браузер-вердиктами (verdicts.json) для измерения согласия. В отличие от бандла — имена читаемые.
"""
import json
import re
from pathlib import Path
import collections

ROOT = Path(__file__).resolve().parents[1]
ADAPT = ROOT / "docs/FRONTEND/bi_react-develop/src/adaptors"
TABLE = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
V = json.loads((ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json").read_text(encoding="utf-8"))["verdicts"]


def is_render_file(p):
    s = str(p).replace("\\", "/")
    if "/amcharts3/amcharts/" in s:        # вендорная либа amCharts (export/pdfmake/fabric/...)
        return False
    if "ConfigEditor" in s:                # ПАНЕЛЬ настроек, не рендер
        return False
    if ".spec." in s or "/stories" in s or "__tests__" in s:
        return False
    return True


render_files = [p for p in ADAPT.rglob("*.js") if is_render_file(p)]
# карта файл → текст (с номерами строк для evidence)
file_lines = {}
blob = []
for p in render_files:
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        continue
    file_lines[p] = lines
    blob.append("\n".join(lines))
text = "\n".join(blob)


def leaf_of(path):
    if not path:
        return ""
    path = path.split(" ")[0]
    seg = re.split(r"[.\[\]]+", path.strip("]"))
    return seg[-1] if seg else ""


def find_read(leaf):
    """Ищет чтение config-ключа в render-исходниках. Возвращает (reads_config, reads_any, evidence)."""
    if not leaf or len(leaf) < 3:
        return False, False, "leaf<3"
    # сильный сигнал: config.<leaf> / cfg.<leaf> / .<leaf> в render-коде
    cfg_pat = re.compile(r"\b(config|cfg)\." + re.escape(leaf) + r"\b")
    any_pat = re.compile(r"\b" + re.escape(leaf) + r"\b")
    reads_config = False
    evidence = ""
    for p, lines in file_lines.items():
        for i, ln in enumerate(lines):
            if cfg_pat.search(ln):
                reads_config = True
                evidence = f"{p.name}:{i+1}: {ln.strip()[:110]}"
                return True, True, evidence
    # слабее: leaf вообще встречается в render-коде (как destructured/spec.X=config.X)
    reads_any = bool(any_pat.search(text))
    if reads_any and not evidence:
        for p, lines in file_lines.items():
            for i, ln in enumerate(lines):
                if any_pat.search(ln):
                    evidence = f"{p.name}:{i+1}: {ln.strip()[:110]}"
                    break
            if evidence:
                break
    return reads_config, reads_any, evidence or "не найдено"


STATUS = {"ok": "renders", "dead": "render-dead", "cfg": "config-only", "amb": "ambiguous",
          "na": "not-applicable", "rej": "value-rejected"}
rows = []
for r in TABLE:
    slug = r["slug"]
    leaf = leaf_of(r.get("effective") or r.get("json") or "")
    reads_config, reads_any, ev = find_read(leaf)
    verd = V.get(slug, {}).get("v", "")
    # source-кандидат: config.X читается рендером → renders; не читается совсем → render-dead
    if reads_config:
        src_cand = "renders"
    elif reads_any:
        src_cand = "maybe"   # leaf есть, но не как config.X (может spec.X=config.X или хардкод)
    else:
        src_cand = "render-dead"
    rows.append({"slug": slug, "leaf": leaf, "verdict_browser": STATUS.get(verd, verd or "?"),
                 "src_reads_config": reads_config, "src_candidate": src_cand, "evidence": ev})

# согласие source ↔ браузер на ok/dead
agree = collections.Counter()
for r in rows:
    vb = r["verdict_browser"]
    if vb not in ("renders", "render-dead"):
        continue
    sc = r["src_candidate"]
    # renders↔(renders|maybe), render-dead↔render-dead
    if vb == "renders":
        agree["browser-renders / src-" + sc] += 1
    else:
        agree["browser-dead / src-" + sc] += 1

out = {"_meta": {
    "purpose": "render-контракт ИЗ ИСХОДНИКОВ (авторитетно): читает ли SpecGenerator config.<key>",
    "render_files": len(render_files),
    "source": "bi_react-develop/src/adaptors/** (SpecGenerator+adaptor+plugins; БЕЗ ConfigEditor/vendored lib)",
    "agreement_browser_vs_source": dict(agree),
}, "rows": rows}
(ROOT / "docs/architecture/readiness/audit/render_manifest_source.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"render-файлов: {len(render_files)}; слагов: {len(rows)}")
print("Согласие browser↔source (ok/dead):")
for k, v in sorted(agree.items()):
    print(f"  {k}: {v}")
