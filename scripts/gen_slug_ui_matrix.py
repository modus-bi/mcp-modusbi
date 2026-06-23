#!/usr/bin/env python3
"""Матрица UI-верификации: все 339 слагов × вердикт (или ⬜ не-проверено), по компонентам.

Источники: docs/architecture/components/slugs/slug-table.json (полный список 339 + applies_to),
docs/architecture/readiness/audit/slug_ui_verdicts.json (пер-слаговые вердикты).
Выход: docs/architecture/readiness/audit/slug_ui_matrix.md — «где прошёл UI-аудит, где нет».
"""
import json, collections
from pathlib import Path

ROOT = Path(__file__).parent.parent
rows = json.load(open(ROOT / "docs/architecture/components/slugs/slug-table.json", encoding="utf-8"))["rows"]
V = json.load(open(ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json", encoding="utf-8"))
verd = V["verdicts"]
ICON = {"ok": "✅", "dead": "🔴", "cfg": "🟡cfg", "amb": "⚠️", "rej": "⚪rej", "na": "⚪na", "": "⬜"}

# T3-blocked компоненты (рендер недостижим — браузер не тратим)
BLOCKED = {"mapLeaflet": "Leaflet не монтируется", "comparisonChart": "frontend-блокер",
           "pageContainer": "builder gap", "subheader": "builder gap"}
OUT_OF_SCOPE = {"audioplayer"}


def tier(slug, e):
    if e["deprecated"]:
        return "T3", "deprecated→skip"
    at = e["applies_to"]
    for c in at:
        if c in BLOCKED:
            return "T3", "blocked: " + BLOCKED[c]
        if c in OUT_OF_SCOPE:
            return "T3", "вне scope (audio)"
    if slug.startswith("balloon."):
        return "T2", "hover-эфемерный"
    if slug.startswith("data."):
        return "T2", "no-ui"
    return "T1", ""


# группировка по «основному» компоненту (applies_to[0]) либо GENERIC
groups = collections.defaultdict(list)
for r in rows:
    slug = r["slug"]
    t, treason = tier(slug, r)
    g = r["applies_to"][0] if r["applies_to"] else "GENERIC"
    vr = verd.get(slug, {})
    groups[g].append({"slug": slug, "tier": t, "treason": treason,
                      "v": vr.get("v", ""), "note": vr.get("note", "") or treason,
                      "on": vr.get("on", ""), "w": vr.get("w", "")})

# счётчики покрытия
total = len(rows)
done = sum(1 for r in rows if r["slug"] in verd)
by_v = collections.Counter(verd[s]["v"] for s in verd)
# «требует UI» = T1 не-проверенные
need_ui = [r["slug"] for r in rows if tier(r["slug"], r)[0] == "T1" and r["slug"] not in verd]

L = [f"# Матрица UI-верификации слагов — все {total} × вердикт", "",
     f"> Генерируется `scripts/gen_slug_ui_matrix.py` из `slug_json_table.json` (полный список) +",
     f"> `slug_ui_verdicts.json` (пер-слаговые вердикты).",
     "> «Прошёл UI-аудит» = есть вердикт; **⬜ = не проверено**.", "",
     "## Покрытие", "",
     f"- Всего слагов: **{total}**",
     f"- Прошли UI-проверку (есть вердикт): **{done}** ({round(100*done/total)}%)",
     f"- Не проверено (⬜): **{total-done}**",
     f"- T1 (renderable) ещё НЕ проверено: **{len(need_ui)}** ← осталось гонять браузером",
     "",
     "Вердикты: " + " · ".join(f"{ICON[k]} {n}" for k, n in by_v.most_common()),
     "",
     "| код | значение |", "|---|---|"]
for k, vtext in V["_meta"]["codes"].items():
    L.append(f"| {ICON.get(k, k)} | {vtext} |")
L += ["| ⬜ | НЕ проверено |", ""]

# порядок групп: сначала проверенные/частые компоненты, GENERIC первым
order = ["GENERIC"] + sorted([g for g in groups if g != "GENERIC"],
                             key=lambda g: (-sum(1 for x in groups[g] if x["v"]), g))
for g in order:
    items = sorted(groups[g], key=lambda x: x["slug"])
    nd = sum(1 for x in items if x["v"])
    L += [f"## {g} — {nd}/{len(items)} проверено", "",
          "| слаг | тир | вердикт | где/нота |", "|---|:--:|:--:|---|"]
    for x in items:
        ic = ICON.get(x["v"], "⬜")
        whereon = x["on"] if x["v"] else ""
        L.append(f"| `{x['slug']}` | {x['tier']} | {ic} | {whereon}{(' — '+x['note']) if x['note'] else ''} |")
    L.append("")

Path(ROOT / "docs/architecture/readiness/audit/slug_ui_matrix.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"OK: {total} слагов, проверено {done} ({round(100*done/total)}%), не проверено {total-done}; T1-остаток {len(need_ui)}")
print("по группам (проверено/всего):")
for g in order:
    nd = sum(1 for x in groups[g] if x["v"])
    print(f"  {nd:2}/{len(groups[g]):2}  {g}")
