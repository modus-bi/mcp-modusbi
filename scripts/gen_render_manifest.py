#!/usr/bin/env python3
"""Рендер-манифест: per-component контракт «что фронт-РЕНДЕР реально читает».

Источник — НЕ фронт-исходники (их нет, только минифицированные бандлы; Go-портал = бэкенд),
а наши ЭМПИРИЧЕСКИ проверенные данные:
  slug_json_table.json (слаг → куда MCP пишет json_path + applies_to)
  + slug_ui_verdicts.json (слаг → render-status: ok/dead/cfg/... из браузерной UI-verify).

JOIN даёт: для каждого (компонент, слаг) — куда пишем И рендерит ли фронт. Это и есть
де-факто рендер-контракт. Выход: docs/architecture/readiness/audit/render_manifest.json (+ .md сводка).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
V = json.loads((ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json").read_text(encoding="utf-8"))["verdicts"]

# render-status: ok=рендерит, dead=config верный но рендер игнорит, cfg=config-only/интерактив,
# amb=неоднозначно, na=неприменимо, rej=валидатор отклонял значение
STATUS = {"ok": "renders", "dead": "render-dead", "cfg": "config-only",
          "amb": "ambiguous", "na": "not-applicable", "rej": "value-rejected"}

# bundle-кандидаты (статический сигнал) — опционально, для поля evidence.bundle
CAND = {}
_cand_path = ROOT / "docs/architecture/readiness/audit/render_candidates.json"
if _cand_path.exists():
    CAND = {c["slug"]: c for c in json.loads(_cand_path.read_text(encoding="utf-8"))["candidates"]}


def _bundle_evidence(slug):
    c = CAND.get(slug)
    if not c or c.get("skip"):
        return "n/a (leaf нечитаем/не сканировался)"
    if not c.get("present"):
        return "absent (leaf не найден в бандле)"
    return (f"{c.get('cand','?')} · assign={c.get('assigns',0)} read={c.get('reads',0)} "
            f"panel={c.get('panel_reads',0)} (shared by {c.get('leaf_shared_by_slugs',1)} слаг)")


# согласуется ли bundle-кандидат с браузер-истиной (renders-cand↔ok, render-dead-cand↔dead)
_AGREE = {("renders-cand", "ok"): True, ("render-dead-cand", "dead"): True}

components = {}
for r in TABLE:
    slug = r["slug"]
    verd = V.get(slug, {})
    vv = verd.get("v", "")
    c = CAND.get(slug, {})
    agree = None
    if c.get("present") and vv in ("ok", "dead"):
        agree = bool(_AGREE.get((c.get("cand"), vv), False))
    entry = {
        "writes": r.get("effective") or r.get("json") or "",   # фактический путь записи MCP
        "render": STATUS.get(vv, "unverified"),                 # ИСТИНА — из браузера
        "reason": verd.get("note", "") or "",
        "evidence": {
            "browser": (verd.get("note", "") or STATUS.get(vv, "unverified")),  # authoritative
            "bundle": _bundle_evidence(slug),                                   # слабый приор
            "bundle_agrees_browser": agree,  # False = бандл ввёл бы в заблуждение
        },
    }
    targets = r["applies_to"] or ["GENERIC"]
    for ct in targets:
        components.setdefault(ct, {})[slug] = entry

# сколько (компонент,слаг) бандл бы ввёл в заблуждение (agree==False) из размеченных
_graded = [e for s in components.values() for e in s.values() if e["evidence"]["bundle_agrees_browser"] is not None]
_misled = sum(1 for e in _graded if e["evidence"]["bundle_agrees_browser"] is False)
manifest = {
    "_meta": {
        "purpose": "per-component render-contract: какие config-ключи фронт-РЕНДЕР реально читает",
        "source": "ИСТИНА (render) — empirical UI-verify (browser); evidence.bundle — слабый статический приор",
        "legend": STATUS,
        "components_count": len(components),
        "evidence_fields": {
            "browser": "authoritative — что рендер реально показал (verdicts.json)",
            "bundle": "слабый приор из gen_render_candidates (минифай-бандл) — НЕ источник истины",
            "bundle_agrees_browser": "согласуется ли бандл-кандидат с браузером (False = бандл ввёл бы в заблуждение)",
        },
        "bundle_would_mislead": f"{_misled}/{len(_graded)} размеченных (бандл расходится с браузером)",
        "note": "render!=panel: ключ может читаться панелью настроек, но игнорироваться рендером (см. render-dead)",
    },
    "components": dict(sorted(components.items())),
}
out_json = ROOT / "docs/architecture/readiness/audit/render_manifest.json"
out_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

# краткая .md-сводка по компонентам (счётчики статусов)
import collections
L = ["# Рендер-манифест — сводка (per-component render-contract)", "",
     "> Генерируется `scripts/gen_render_manifest.py` из slug_json_table + slug_ui_verdicts (эмпирика).",
     "> Полный машинный вид — `render_manifest.json`. Назначение: единый контракт «что рендер читает»,",
     "> против которого можно валидировать json_path в CI (см. test_render_dead_contract).", "",
     "| компонент | renders | render-dead | config-only | прочее |", "|---|--:|--:|--:|--:|"]
for ct, slugs in manifest["components"].items():
    c = collections.Counter(e["render"] for e in slugs.values())
    other = sum(v for k, v in c.items() if k not in ("renders", "render-dead", "config-only"))
    L.append(f"| {ct} | {c.get('renders',0)} | {c.get('render-dead',0)} | {c.get('config-only',0)} | {other} |")
(ROOT / "docs/architecture/readiness/audit/render_manifest.md").write_text("\n".join(L) + "\n", encoding="utf-8")

total = sum(len(s) for s in components.values())
dead = sum(1 for s in components.values() for e in s.values() if e["render"] == "render-dead")
print(f"OK: {len(components)} компонентов, {total} (компонент,слаг)-записей, render-dead={dead}")
print(f"→ docs/architecture/readiness/audit/render_manifest.json + .md")
