#!/usr/bin/env python3
"""Генерация app/tools/slug_ui_meta.json — UI-метаданные слагов (название контрола + секция панели).

Источник:
  1. UI-карты компонентов (внутренние таблицы UI-готовности) — таблицы
     `| UI-секция | UI-контрол | JSON-путь | Тип | MCP-slug | ...` (browser-probed, русские названия).
  2. Fallback для непокрытых: секция из префикса слага + humanized-название из leaf.

Отдаётся LLM в list_slugs (enrich_slug) — чтобы знать UI-контекст слага.
"""
import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from tools.config_schema import SLUG_SCHEMA  # noqa: E402

PREFIX_SECTION = {
    "axes": "Оси", "legend": "Легенда", "labels": "Подписи", "margin": "Отступы",
    "outline": "Рамка компонента", "balloon": "Всплывающая подсказка", "data": "Данные",
    "visuals": "Стиль элементов", "style": "Стиль", "grid": "Шкала/индикатор",
    "regimes": "Режимы таблицы", "sort": "Сортировка", "table": "Таблица", "map": "Карта",
    "tilemap": "Плиточная карта", "sunburst": "Солнечные лучи", "pivot": "Сводная таблица",
    "totals": "Итоги", "delta": "Тренд (KPI)", "bubble": "Пузырьковая диаграмма",
    "stock": "Временные ряды", "viewType": "Тип фильтра", "hierFilter": "Иерархический фильтр",
    "switch": "Переключатель", "tabs": "Вкладки", "audio": "Аудиоплеер", "iframe": "iFrame",
    "parallel": "Параллельные координаты", "comparison": "Сравнение",
    "rules": "Условное форматирование", "columns": "Колонки", "graph": "Граф",
    "main": "Общие", "scale": "Шкала",
}
# Точечная полировка частых fallback-меток (где humanize даёт «R»/«Pad»).
OVERRIDE = {
    "margin.l": ("Отступ Лево", "Отступы"), "margin.r": ("Отступ Право", "Отступы"),
    "margin.t": ("Отступ Верх", "Отступы"), "margin.b": ("Отступ Низ", "Отступы"),
    "margin.pad": ("Внутренний отступ", "Отступы"),
}


def humanize(leaf: str) -> str:
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", leaf).replace("_", " ")
    s = s.split("[")[0].strip()
    return (s[:1].upper() + s[1:]) if s else leaf


def clean(t: str) -> str:
    return re.sub(r"\*\*|`", "", t or "").strip()


def parse_t04():
    rows = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
    jp_to_slug = collections.defaultdict(list)
    for r in rows:
        j = (r.get("effective") or r.get("json") or "").strip()
        if j:
            jp_to_slug[j].append(r["slug"])
    meta = {}
    for f in glob.glob(str(ROOT / os.environ.get("UI_MAPS_GLOB", "docs/ui-maps/components/*.md"))):
        comp = Path(f).stem
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5 or cells[0] in ("UI-секция",) or cells[0].startswith("--"):
                continue
            section, label, jsonpath = cells[0], cells[1], cells[2]
            placed = False
            for cand in re.findall(r"`([a-zA-Z][\w.]+)`", cells[4]):
                if cand in SLUG_SCHEMA and cand not in meta:
                    meta[cand] = {"ui_label": clean(label), "ui_section": clean(section), "source": "t04", "ui_component": comp}
                    placed = True
            if not placed:
                for jcand in re.findall(r"`([^`]+)`", jsonpath):
                    for s in jp_to_slug.get(jcand.strip(), []):
                        if s in SLUG_SCHEMA and s not in meta:
                            meta[s] = {"ui_label": clean(label), "ui_section": clean(section), "source": "t04", "ui_component": comp}
                            placed = True
                            break
                    if placed:
                        break
    return meta


def main():
    t04 = parse_t04()
    meta = {}
    for slug in SLUG_SCHEMA:
        entry = SLUG_SCHEMA[slug]
        if slug in OVERRIDE:
            lbl, sec = OVERRIDE[slug]
            meta[slug] = {"ui_label": lbl, "ui_section": sec, "source": "override"}
        elif slug in t04 and t04[slug]["ui_label"]:
            meta[slug] = {"ui_label": t04[slug]["ui_label"], "ui_section": t04[slug]["ui_section"], "source": "t04"}
        elif entry.get("ui_label") and entry.get("ui_section"):
            # inline UI-мета прямо в SLUG_SCHEMA-записи (напр. KPI-дизайн слаги)
            meta[slug] = {"ui_label": entry["ui_label"], "ui_section": entry["ui_section"], "source": "inline"}
        else:
            pref = slug.split(".")[0] if "." in slug else "top-level"
            meta[slug] = {"ui_label": humanize(slug.split(".")[-1]), "ui_section": PREFIX_SECTION.get(pref, "Общие"), "source": "derived"}
    out = ROOT / "app/tools/slug_ui_meta.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=0, separators=(",", ":")), encoding="utf-8")
    src = collections.Counter(e["source"] for e in meta.values())
    print(f"slug_ui_meta.json: {len(meta)} слагов = SLUG_SCHEMA ({len(SLUG_SCHEMA)}); источник {dict(src)}")


if __name__ == "__main__":
    main()
