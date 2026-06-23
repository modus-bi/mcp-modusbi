#!/usr/bin/env python3
"""Текущая таблица соответствия слаг → json (фактический путь записи) + проверка единообразия.

Путь записи определяется ФАКТИЧЕСКИ: применяем sentinel через apply_slug_overrides и находим,
куда он лёг (ground truth, без реимплементации диспетчера). Источник — живой SLUG_SCHEMA.
Выход: docs/architecture/components/slugs/slug-table.{md,json}.
"""
import sys, json, copy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.config_schema import SLUG_SCHEMA, apply_slug_overrides, CHART_TYPE_MAP, _TOP_LEVEL_PER_TYPE

# обратная карта chart-type → Hs* (для component_type в apply)
REV = {v: k for k, v in CHART_TYPE_MAP.items()}
SENT = "§SENT§"

# slug → per-type расхождения (totalsPanelV2/imagePanel/iframe пишут в иной ключ)
_PER_TYPE_BY_SLUG = {}
for (ct, sl), key in _TOP_LEVEL_PER_TYPE.items():
    _PER_TYPE_BY_SLUG.setdefault(sl, []).append(f"{ct}→{key}")

# Object-wrapper слаги: handler намеренно пишет config.<json> как ОБЪЕКТ, поэтому
# sentinel-лист (напр. image.path) отличается от json-листа (image) — это НЕ расхождение.
_OBJECT_WRAPPER = {"image.src"}  # config.image = {path, ID} (краш-фикс ImagePanel)


def _find(node, path=""):
    """Вернуть json-путь, где лежит SENT (рекурсивно)."""
    if node == SENT:
        return path
    if isinstance(node, dict):
        for k, v in node.items():
            r = _find(v, f"{path}.{k}" if path else k)
            if r:
                return r
    if isinstance(node, list):
        for i, v in enumerate(node):
            r = _find(v, f"{path}[{i}]")
            if r:
                return r
    return None


def effective_path(slug, entry):
    """Куда слаг ФАКТИЧЕСКИ пишет (трассировка sentinel)."""
    ct = ""
    at = entry.get("applies_to")
    if at:
        ct = REV.get(at[0], at[0])
    # visuals:[] — как у прод-билдеров (иначе visuals.* падают в top-level fallback)
    base = {"axes": [{"type": "categories", "fields": []}, {"type": "values", "fields": []}], "visuals": []}
    try:
        out = apply_slug_overrides(base, {slug: SENT}, ct)
    except Exception as e:
        return f"(error: {type(e).__name__})"
    p = _find(out)
    if p:
        # per-type расхождение (slug без applies_to пишет иной ключ у totals/image/iframe)
        if slug in _PER_TYPE_BY_SLUG:
            return f"{p}  [per-type: {', '.join(_PER_TYPE_BY_SLUG[slug])}]"
        return p
    # sentinel не найден (invert/transform/deprecated-skip) → объяснить
    if entry.get("deprecated"):
        return "(deprecated → не пишется)"
    if entry.get("invert"):
        return entry.get("json_path", "?") + " (inverted)"
    return entry.get("json_path") or "(section-derived / transform)"


rows = []
for slug in sorted(SLUG_SCHEMA):
    e = SLUG_SCHEMA[slug]
    rows.append({
        "slug": slug,
        "json": e.get("json_path") or "",
        "effective": effective_path(slug, e),
        "type": e.get("type"),
        "path_write": bool(e.get("path_write")),
        "invert": bool(e.get("invert")),
        "deprecated": bool(e.get("deprecated")),
        "applies_to": e.get("applies_to") or [],
    })

# ── проверка единообразия: лист ФАКТИЧЕСКОГО пути == лист декларированного json ──
import re as _re
def _leaf(p):
    if not p:
        return ""
    p = p.split(" ")[0]                       # отбросить "(inverted)"
    return _re.split(r'[.\[\]]+', p.strip(']'))[-1].lower()

issues = []
for r in rows:
    s = r["slug"]
    # 1) apply бросил исключение
    if r["effective"].startswith("(error"):
        issues.append((s, f"apply бросил исключение: {r['effective']}"))
        continue
    # 2) invert без path_write — инверсия обрабатывается только в path_write-ветке
    if r["invert"] and not r["path_write"]:
        issues.append((s, "invert=True, но path_write=False — инверсия не сработает"))
    # 3) нет type
    if not r["type"]:
        issues.append((s, "нет поля type"))
    # 4) РЕАЛЬНЫЙ mismatch: декларирован json_path, но фактический лист записи иной
    if r["json"] and not r["deprecated"] and not r["invert"] and s not in _OBJECT_WRAPPER:
        if _leaf(r["effective"]) and _leaf(r["effective"]) != _leaf(r["json"]):
            issues.append((s, f"факт. лист '{_leaf(r['effective'])}' != json-лист '{_leaf(r['json'])}' (факт={r['effective']})"))

out = {"count": len(rows), "rows": rows, "uniformity_issues": [{"slug": a, "issue": b} for a, b in issues]}
Path("docs/architecture/components/slugs/slug-table.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# ── markdown ──
L = [f"# Таблица соответствия слаг → json (текущее состояние, {len(rows)} слагов)", "",
     "> Регенерируется `scripts/gen_slug_json_table.py` из живого `SLUG_SCHEMA`. Путь записи —",
     "> **фактический** (трассировка sentinel через `apply_slug_overrides` на базе с `axes`+`visuals:[]`).",
     "> Для invert/deprecated значение sentinel не находится — путь берётся из декларации (помечено).",
     "> Слаги без `applies_to` показаны в generic-варианте; per-type расхождения (totals/image/iframe) — в `[per-type: …]`.",
     "",
     f"**Единообразие** (для слагов с декларированным `json_path`: факт. лист записи == json-лист): "
     f"расхождений **{len(issues)}**." + (" ✓ все приведены к одному виду." if not issues else ""),
     ""]
if issues:
    L += ["## ⚠️ Замечания единообразия", "", "| слаг | замечание |", "|---|---|"]
    L += [f"| `{a}` | {b} |" for a, b in issues]
    L.append("")
L += ["## Все слаги", "", "| слаг | json (схема) | факт. путь записи | тип | pw | inv | dep |",
      "|---|---|---|---|:--:|:--:|:--:|"]
for r in rows:
    L.append(f"| `{r['slug']}` | {('`'+r['json']+'`') if r['json'] else '—'} | `{r['effective']}` | "
             f"{r['type']} | {'✓' if r['path_write'] else ''} | {'✓' if r['invert'] else ''} | {'✓' if r['deprecated'] else ''} |")
Path("docs/architecture/components/slugs/slug-table.md").write_text("\n".join(L) + "\n", encoding="utf-8")

print(f"OK: {len(rows)} слагов, замечаний единообразия: {len(issues)}")
for a, b in issues:
    print(f"  ⚠ {a}: {b}")
