#!/usr/bin/env python3
"""Ре-проверка render-dead слагов против исходников: ищем пропущенные leaf-грепом чтения.

Для каждого слага с вердиктом dead грепаем его render-модуль(и) РАСШИРЕННО:
case-insensitive leaf, `_.get(config,'leaf')` (lodash — пропускался), деструктуризация носителя.
Если концепт ВСЁ-ТАКИ упоминается → CANDIDATE (ручная проверка: wrong-key/conditional, как legend/summColor).
Если нигде → CONFIRMED-DEAD (фронт-хардкод/не читается).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FE = ROOT / "docs/FRONTEND/bi_react-develop"
V = json.loads((ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json").read_text(encoding="utf-8"))["verdicts"]
rows = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
JP = {r["slug"]: (r.get("effective") or r.get("json") or "") for r in rows}
AP = {r["slug"]: (r["applies_to"] or []) for r in rows}

A3 = "src/adaptors/AMcharts3ChartAdaptor"
COMP_DIR = {
    "barChart": A3, "lineChart": A3, "pieChart": A3, "areaChart": A3, "radarChart": A3,
    "speedometerV2": A3, "bubbleChart": A3,
    "stockChart": "src/adaptors/AMcharts4ChartAdaptor",
    "treeMap": "src/adaptors/EChartsChartAdaptor", "tilemapChart": "src/adaptors/EChartsChartAdaptor",
    "sunburstChart": "src/adaptors/EChartsChartAdaptor",
    "table": "src/adaptors/ReactabularChartAdaptor", "treeGraph": "src/adaptors/GoJSChartAdaptor",
    "mapLeaflet": "src/charts/HsMapLeafletChart",
    "totalsPanelV2": "src/adaptors/CommonChartAdaptor", "comparisonChart": "src/adaptors/CommonChartAdaptor",
}
ALL_ADAPT = sorted(set(COMP_DIR.values()))


def load_dir(rel):
    d = FE / rel
    if not d.exists():
        return ""
    out = []
    for p in d.rglob("*.js"):
        s = str(p).replace("\\", "/")
        if "/amcharts3/amcharts/" in s or ".spec." in s:
            continue
        out.append(p.read_text(encoding="utf-8", errors="ignore"))
    for p in d.rglob("*.ts"):
        s = str(p).replace("\\", "/")
        if ".spec." in s or ".d.ts" in s:
            continue
        out.append(p.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(out)


CACHE = {}


def text_for(dirs):
    key = tuple(dirs)
    if key not in CACHE:
        CACHE[key] = "\n".join(load_dir(d) for d in dirs)
    return CACHE[key]


def leaf_of(path):
    seg = re.split(r"[.\[\]]+", (path or "").split(" ")[0].strip("]"))
    return seg[-1] if seg else ""


def scan(leaf, blob):
    if not leaf or len(leaf) < 3:
        return None
    # 1) точное config.leaf (уже знаем) | 2) case-insensitive leaf | 3) _.get(config,'leaf') | 4) деструктуризация
    pats = {
        "config.leaf": re.compile(r"\b(config|cfg)\." + re.escape(leaf) + r"\b"),
        "ci-leaf": re.compile(r"\b" + re.escape(leaf) + r"\b", re.I),
        "lodash-get": re.compile(r"_\.get\(\s*config\s*,\s*['\"][^'\"]*" + re.escape(leaf) + r"[^'\"]*['\"]", re.I),
    }
    hits = {}
    for name, pat in pats.items():
        m = pat.search(blob)
        if m:
            ln = blob[:m.start()].count("\n") + 1
            snippet = blob.splitlines()[ln - 1].strip()[:100] if ln <= blob.count("\n") + 1 else ""
            hits[name] = snippet
    return hits


candidates, confirmed = [], []
for slug, e in V.items():
    if e["v"] != "dead":
        continue
    leaf = leaf_of(JP.get(slug, ""))
    comps = AP.get(slug, [])
    dirs = ALL_ADAPT if not comps else sorted({COMP_DIR.get(c) for c in comps if COMP_DIR.get(c)})
    if not dirs:
        dirs = ALL_ADAPT
    blob = text_for(tuple(dirs))
    hits = scan(leaf, blob)
    rec = {"slug": slug, "leaf": leaf, "dirs": dirs, "hits": hits or {}}
    # CANDIDATE если есть config.leaf или lodash-get (сильные сигналы чтения), пропущенные ранее
    if hits and ("config.leaf" in hits or "lodash-get" in hits):
        candidates.append(rec)
    elif hits and "ci-leaf" in hits:
        rec["weak"] = True
        candidates.append(rec)
    else:
        confirmed.append(rec)

out = {"render_dead_total": len(candidates) + len(confirmed),
       "candidates_for_recheck": candidates, "confirmed_dead": [c["slug"] for c in confirmed]}
(ROOT / "docs/architecture/readiness/audit/render_dead_recheck.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"render-dead {len(candidates)+len(confirmed)}: КАНДИДАТЫ на ре-проверку {len(candidates)}, подтверждённо-dead {len(confirmed)}")
print("\n=== КАНДИДАТЫ (концепт упомянут в адаптере — проверить вручную) ===")
for c in candidates:
    strong = "config.leaf" in c["hits"] or "lodash-get" in c["hits"]
    tag = "СИЛЬНЫЙ" if strong else "слабый(ci)"
    ev = c["hits"].get("config.leaf") or c["hits"].get("lodash-get") or c["hits"].get("ci-leaf", "")
    print(f"  [{tag}] {c['slug']:30} leaf={c['leaf']:18} {ev[:80]}")
