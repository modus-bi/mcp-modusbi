#!/usr/bin/env python3
"""Регенерация docs/architecture/components/slugs/by-type.md из SLUG_SCHEMA.

Запуск из корня репо: python3 scripts/gen_slug_reference.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.tools.config_schema import (  # noqa: E402
    SLUG_SCHEMA, COLUMN_PROPS, RULE_PROPS, _SLUG_ALIASES, _ANCHORED_VISUAL_PROPS,
)


def fmt_type(e):
    t = e["type"]
    if t == "enum":
        return f"enum: {'/'.join(map(str, e.get('values', [])))}"
    if t in ("int", "float") and ("min" in e or "max" in e):
        return f"{t} [{e.get('min', '')}..{e.get('max', '')}]"
    return t


def main():
    groups = defaultdict(list)
    for slug, e in sorted(SLUG_SCHEMA.items()):
        section = slug.split(".")[0] if "." in slug else "(top-level)"
        groups[section].append((slug, e))

    lines = [
        "# SLUG_REFERENCE — справочник config_overrides",
        "",
        "> **Генерируется из `app/tools/config_schema.py` (SLUG_SCHEMA)** — единственный источник истины.",
        "> Регенерация: `python3 scripts/gen_slug_reference.py`.",
        f"> Слагов: **{len(SLUG_SCHEMA)}** (+ анкерные `visuals.{{anchor}}.{{prop}}`, колоночные `columns.{{field}}.{{prop}}`, правила `rules.{{n}}.{{prop}}`).",
        "",
        "Колонки: **json_path** — фактический путь записи в config (пусто = top-level/секционный handler);",
        "**applies_to** — internal-типы (пусто = все); ⚠️ = deprecated (мёртвый фронт-ключ, см. подсказку).",
        "",
        "См. также: единый справочник-соответствие **UI-контрол ↔ MCP-слаг ↔ JSON-путь** — "
        "[README.md](README.md); устаревшие имена — [aliases.md](aliases.md); "
        "что такое слаги — [концепция](../../concepts/components-json-slugs.md).",
        "",
    ]
    for section in sorted(groups):
        lines += [f"## {section}", "",
                  "| Слаг | Тип | Default | json_path | applies_to | Прим. |",
                  "|---|---|---|---|---|---|"]
        for slug, e in groups[section]:
            dep = e.get("deprecated")
            note = f"⚠️ DEPRECATED: {dep}" if dep else ""
            if e.get("invert"):
                note = (note + " " if note else "") + "значение ИНВЕРТИРУЕТСЯ"
            jp = e.get("json_path", "")
            at = ", ".join(e.get("applies_to", [])) or "все"
            lines.append(f"| `{slug}` | {fmt_type(e)} | `{e.get('default')}` | `{jp}` | {at} | {note} |")
        lines.append("")

    lines += [
        "## Анкерные visuals (per-series / per-element)", "",
        "`visuals.{anchor}.{prop}` — пишет в элемент `config.visuals[]` с `anchor == {anchor}`",
        "(имя серии у line/area/radar/stock, `value`/`caption`/`subcaption`/`trend` у KPI).",
        "Поддерживаемые prop: " + ", ".join(f"`{p}`" for p in sorted(_ANCHORED_VISUAL_PROPS)) + ".",
        "Типы: line/area/gauge/KPI/stock/radar. Anchor с точкой в имени серии не адресуется (ограничение).",
        "",
        "## Колоночные слаги (table/pivot/comparison)", "",
        "`columns.{fieldName|fieldId}.{prop}` — props: " + ", ".join(f"`{p}`" for p in sorted(COLUMN_PROPS)) + ".",
        "",
        "## Правила условного форматирования (table/pivot)", "",
        "`rules.{n}.{prop}` — props: " + ", ".join(f"`{p}`" for p in sorted(RULE_PROPS)) + ".",
        "",
        "## Алиасы", "",
        "\n".join(f"- `{a}` → `{c}`" for a, c in sorted(_SLUG_ALIASES.items())),
        "",
    ]
    out = Path(__file__).resolve().parents[1] / "docs/architecture/components/slugs/by-type.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"written {out} ({len(lines)} lines, {len(SLUG_SCHEMA)} slugs)")


if __name__ == "__main__":
    main()
