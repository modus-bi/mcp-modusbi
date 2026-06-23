#!/usr/bin/env python3
"""component_status.md — консолидированный итог по слагам (план §3).

JOIN: slug_json_table (json_path, applies_to) + slug_ui_verdicts (browser-вердикт+нота)
+ render_manifest_source (source-статус) + frontend_support (версия). Группировка по компоненту.
Колонки: слаг | json_path | source | browser | resolution | версия | нота.
"""
import json
import collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "docs/architecture/readiness/audit"
rows = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
V = json.loads((A / "slug_ui_verdicts.json").read_text(encoding="utf-8"))["verdicts"]
SRC = {}
sp = A / "render_manifest_source.json"
if sp.exists():
    SRC = {r["slug"]: r for r in json.loads(sp.read_text(encoding="utf-8"))["rows"]}
SUP = json.loads((A / "frontend_support.json").read_text(encoding="utf-8")) if (A / "frontend_support.json").exists() else {}
fe_ver = SUP.get("latest_verified", "?")

RESOLUTION = {
    "ok": "RENDERS", "dead": "render-dead (hardcode)", "amb": "conditional/ambiguous",
    "cfg": "config-only", "na": "not-applicable", "rej": "value-rejected", "": "—",
}

groups = collections.defaultdict(list)
for r in rows:
    slug = r["slug"]
    e = V.get(slug, {})
    src = SRC.get(slug, {})
    comp = r["applies_to"][0] if r["applies_to"] else "GENERIC"
    groups[comp].append({
        "slug": slug,
        "json": r.get("effective") or r.get("json") or "",
        "src": src.get("src_candidate", "?"),
        "browser": e.get("v", ""),
        "res": RESOLUTION.get(e.get("v", ""), e.get("v", "")),
        "note": (e.get("note", "") or "")[:90],
    })

cnt = collections.Counter(V[s]["v"] for s in V)
L = [f"# Статус слагов — консолидированный итог (per-component)", "",
     f"> Генерируется `scripts/gen_component_status.py`. Источники: slug_json_table + slug_ui_verdicts +",
     f"> render_manifest_source. Версия фронта (выверено): **{fe_ver}**. Колонки: слаг | json_path |",
     f"> source (читает ли адаптер) | browser-вердикт | resolution | нота.", "",
     f"**Итог:** RENDERS {cnt.get('ok',0)} · render-dead {cnt.get('dead',0)} · conditional/amb {cnt.get('amb',0)} · "
     f"config-only {cnt.get('cfg',0)} · n/a {cnt.get('na',0)} · rejected {cnt.get('rej',0)}", ""]

order = sorted(groups, key=lambda g: (-len(groups[g]), g))
for comp in order:
    items = sorted(groups[comp], key=lambda x: x["slug"])
    L += [f"## {comp} ({len(items)})", "",
          "| слаг | json_path | source | browser | resolution | нота |", "|---|---|:--:|:--:|---|---|"]
    for x in items:
        L.append(f"| `{x['slug']}` | `{x['json']}` | {x['src']} | {x['browser']} | {x['res']} | {x['note']} |")
    L.append("")

(A / "component_status.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print(f"component_status.md: {sum(len(v) for v in groups.values())} слагов, {len(groups)} компонентов, версия фронта {fe_ver}")
print(f"  {dict(cnt)}")
