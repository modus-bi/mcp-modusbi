#!/usr/bin/env python3
"""Синхронизирует AUTO-таблицу «Все настройки» в пер-компонентных спеках public_docs/architecture/components/reference/*.md.

Идея «M+G»: нарратив файла пишется/курируется вручную, а полная таблица слагов
(UI-контрол · MCP-слаг · JSON-путь/фронт-ключ · тип · default) ГЕНЕРИРУЕТСЯ и держится
в синхроне с кодом. Генератор заменяет ТОЛЬКО область между маркерами:

    <!-- AUTO-TABLE:START (регенерируется scripts/gen_component_tables.py) -->
    ...таблица...
    <!-- AUTO-TABLE:END -->

Нарратив вне маркеров не трогается. Запуск из корня репо:
    python3 scripts/gen_component_tables.py            # обновить все файлы reference/
    python3 scripts/gen_component_tables.py bar-chart  # один файл

Источники: app/tools/config_schema.SLUG_SCHEMA (тип/default), docs/architecture/components/slugs/slug-table.json
(json-путь/applies_to/deprecated), app/tools/slug_ui_meta.json (UI-контрол/секция).

Отслеживание изменений: после правок в SLUG_SCHEMA перезапустить генератор и закоммитить;
CI-проверка `git diff --exit-code public_docs/architecture/components/reference/` поймает несинхронизированные файлы.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import os  # noqa: E402
for _v in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD"):
    os.environ.setdefault(_v, "stub")
from app.tools.config_schema import SLUG_SCHEMA  # noqa: E402
from app.tools.builders import build_component_config  # noqa: E402

# Каталог reference/: в dev-репо генерация идёт в public_docs/ (staging),
# в публичном репо файлы уже в docs/. Берём тот, что существует.
REF_DIR = ROOT / "public_docs/architecture/components/reference"
if not REF_DIR.exists():
    REF_DIR = ROOT / "docs/architecture/components/reference"
START = "<!-- AUTO-TABLE:START (регенерируется scripts/gen_component_tables.py — правьте config_schema.py, не этот блок) -->"
END = "<!-- AUTO-TABLE:END -->"

# Hs-класс (объявляется в файле строкой «Тип компонента: `HsXxx`») → внутреннее имя типа (как в applies_to).
HS_TO_INTERNAL = {
    "HsBarAMchartsChart": "barChart", "HsLineAMchartsChart": "lineChart",
    "HsAreaAMchartsChart": "areaChart", "HsPieAMchartsChart": "pieChart",
    "HsRadarAMchartsChart": "radarChart", "HsBubbleAMchartsChart": "bubbleChart",
    "HsStockAMchartsChart": "stockChart", "HsTableReactabularChart": "table",
    "HsPivotChart": "pivotChart", "HsMapLeafletChart": "mapLeaflet",
    "HsTilemapChart": "tilemap", "HsSpeedometerV2AMcharts": "speedometerV2",
    "HsTotalsPanelV2": "totalsPanelV2", "HsTreeMap": "treeMap", "HsTreeGraph": "treeGraph",
    "HsSunburstChart": "sunburst", "HsParallelCoordsChart": "parallelCoords",
    "HsComparisonChart": "comparison", "HsFilterControlPanel": "FilterControlPanel",
    "HsHierarchicalFilterPanel": "hierarchicalFilter", "HsSwitchControlPanel": "switch",
    "HsTabsPanel": "tabs", "HsTextBlock": "textBlock", "HsImagePanel": "imagePanel",
    "HsIframe": "iframe", "HsAudioplayer": "audioplayer", "HsSubheaderComponent": "subheader",
    "HsPageContainer": "pageContainer",
}

# Базовые оформительские слаги — применимы КО ВСЕМ типам (контейнер: фон, отступы, рамка, заголовок).
ALWAYS_PREFIX = ("margin.", "outline.")
ALWAYS_TOP = {"bgColor", "bgColor2", "gradient", "gradientDirection", "showtitle", "subtitle",
              "fontSize", "nocopy", "noexport", "hideSpinner", "textAlign", "truncateTitle"}
# Графические оформительские слаги — только для семейства диаграмм (легенда/оси/подписи/серии/всплывашка).
CHART_PREFIX = ("legend.", "labels.", "axes.", "balloon.", "visuals.", "data.", "style.")
CHART_TOP = {"expandH", "expandV", "main.extraAxis"}
# Типы, к которым применимы графические универсальные слаги.
CHART_FAMILY = {"barChart", "lineChart", "areaChart", "pieChart", "radarChart", "bubbleChart",
                "stockChart", "comparison", "parallelCoords", "sunburst", "treeMap", "treeGraph",
                "tilemap", "speedometerV2"}

# Канонизация имён UI-секций (источники дают неконсистентные варианты).
SECTION_CANON = {
    "Осн.стиль": "Основной стиль", "Осн. стиль": "Основной стиль", "Стиль": "Стилизация",
    "Стиль элем.": "Стиль элементов", "Всплыв.": "Всплывающая подсказка",
    "Рамка": "Рамка компонента", "Ось Кат.": "Оси", "Ось Знач.": "Оси",
    "Клик": "Интерактив (клик)",
}
# Точечная правка неверных/неоднозначных UI-меток из источника.
LABEL_OVERRIDE = {"legend.order": "Порядок", "legend.reverse": "Реверс порядка"}
SECTION_ORDER = ["Данные", "Основной стиль", "Стилизация", "Стиль элементов", "Оси", "Легенда",
                 "Подписи", "Всплывающая подсказка", "Интерактив (клик)", "Отступы",
                 "Рамка компонента", "Общие", "Прочее"]

_rows = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
_ui = json.loads((ROOT / "app/tools/slug_ui_meta.json").read_text(encoding="utf-8"))

INTERNAL_TO_HS = {v: k for k, v in HS_TO_INTERNAL.items()}
_built_cache: dict[str, dict] = {}


def _built_config(internal: str) -> dict:
    """Собрать компонент этого типа билдером и вернуть его config — чтобы
    показывать РЕАЛЬНЫЙ default (то, что ставит билдер), а не только схемный.
    Любой сбой → пустой конфиг (тогда используется схемный default)."""
    if internal in _built_cache:
        return _built_cache[internal]
    cfg: dict = {}
    hs = INTERNAL_TO_HS.get(internal)
    if hs:
        try:
            res = build_component_config(
                component_type=hs, title="x", dataset_id=1,
                category_field="cat", value_fields=["val"],
                value_fields_type="number", aggregation="sum",
            )
            if isinstance(res, dict):
                cfg = res.get("config", {}) or {}
        except Exception:
            cfg = {}
    _built_cache[internal] = cfg
    return cfg


def _nav(cfg: dict, path: str):
    """Достать значение по дотированному пути (margin.l, outline.width)."""
    cur = cfg
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _effective_default(slug: str, sch: dict, jp, built: dict):
    """Default для таблицы: реальное значение из собранного конфига для
    bool/int-слагов (их билдер задаёт по типу), иначе схемный default."""
    sch_type = sch.get("type")
    if jp and not sch.get("invert") and sch_type in ("bool", "int") and re.fullmatch(r"[\w.]+", jp):
        val = _nav(built, jp)
        if sch_type == "bool" and isinstance(val, bool):
            return val
        if sch_type == "int" and isinstance(val, int) and not isinstance(val, bool):
            return val
    return sch.get("default")


def _relevant(r: dict, internal: str) -> bool:
    a = r.get("applies_to") or []
    if internal in a:
        return True            # специфичный для этого типа
    if a:
        return False           # специфичный для другого типа
    s = r["slug"]              # дальше — общий (applies_to пуст)
    if s in ALWAYS_TOP or any(s.startswith(p) for p in ALWAYS_PREFIX):
        return True            # базовая оформительская настройка — всем типам
    if internal in CHART_FAMILY and (s in CHART_TOP or any(s.startswith(p) for p in CHART_PREFIX)):
        return True            # графическая оформительская — только семейству диаграмм
    return False


def _ui_of(slug: str):
    m = _ui.get(slug, {})
    sec = SECTION_CANON.get(m.get("ui_section", "Прочее"), m.get("ui_section", "Прочее"))
    if sec.startswith("(") or sec.lower() in ("нет ui", "slug без ui"):
        sec = "Прочее"        # плейсхолдер-секция из источника → в «Прочее»
    lbl = m.get("ui_label", "") if m.get("source") in ("t04", "override", "inline") else ""
    lbl = LABEL_OVERRIDE.get(slug, lbl)
    return lbl, sec


def settings_table(internal: str) -> tuple[str, int]:
    sel = [r for r in _rows if _relevant(r, internal)]
    built = _built_config(internal)
    groups: dict[str, list] = defaultdict(list)
    for r in sel:
        s = r["slug"]
        lbl, sec = _ui_of(s)
        sch = SLUG_SCHEMA.get(s, {})
        eff = r.get("effective") or ""
        if r.get("json"):
            jp_cell = f"`{r['json']}`"
        elif re.fullmatch(r"[\w.\[\]]+", eff):
            jp_cell = f"`({eff})`"
        else:
            # секционный хендлер / преобразование — простого ключа в конфиге нет
            jp_cell = "_секционно_"
        nav_path = r.get("json") or (eff if re.fullmatch(r"[\w.]+", eff) else None)
        dflt = _effective_default(s, sch, nav_path, built)
        dstr = f"`{dflt}`" if dflt is not None else "—"
        note = "устар." if r.get("deprecated") else ("только этот тип" if r.get("applies_to") else "")
        groups[sec].append((lbl, s, jp_cell, r.get("type"), dstr, note))

    secs = sorted(groups, key=lambda x: (SECTION_ORDER.index(x) if x in SECTION_ORDER else 99, x))
    L = [
        "## Все настройки (config_overrides)",
        "",
        "Полный перечень слагов этого типа — специфичные для типа и общие оформительские. "
        "Колонки: **UI-контрол** — название в панели настроек портала (пусто = прямого UI-контрола нет, "
        "настройка только через `config_overrides`); **MCP-слаг** — ключ в `config_overrides`; "
        "**JSON-путь** — куда настройка пишется в конфиг и откуда её читает отображение (это и есть «фронт-ключ»; "
        "путь в `(скобках)` обрабатывается секционно — итоговый ключ внутри указанной секции конфига); "
        "**Тип**; **По умолчанию**. Полный справочник по всем типам — [Справочник настроек](../slugs/by-type.md).",
        "",
    ]
    total = 0
    for sec in secs:
        L += [f"### {sec}", "",
              "| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |",
              "|---|---|---|---|---|---|"]
        for lbl, s, jp_cell, typ, dstr, note in sorted(groups[sec], key=lambda x: x[1]):
            L.append(f"| {lbl or '—'} | `{s}` | {jp_cell} | {typ} | {dstr} | {note} |")
            total += 1
        L.append("")
    return "\n".join(L).rstrip() + "\n", total


def _internal_of(text: str, path: Path) -> str | None:
    m = re.search(r"Тип компонента:\s*`(Hs[\w]+)`", text)
    if not m:
        print(f"  ! {path.name}: не найдена строка «Тип компонента: `HsXxx`» — пропуск")
        return None
    hs = m.group(1)
    internal = HS_TO_INTERNAL.get(hs)
    if not internal:
        print(f"  ! {path.name}: неизвестный тип {hs} — пропуск")
    return internal


def update_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    internal = _internal_of(text, path)
    if not internal:
        return False
    table, n = settings_table(internal)
    block = f"{START}\n\n{table}\n{END}"
    if START in text and END in text:
        new = re.sub(re.escape(START) + r".*?" + re.escape(END), block, text, flags=re.S)
        action = "обновлён"
    else:
        # маркеров нет — вставить перед «## Связанные», иначе в конец
        if "## Связанные" in text:
            new = text.replace("## Связанные", block + "\n\n## Связанные", 1)
        else:
            new = text.rstrip() + "\n\n" + block + "\n"
        action = "маркеры добавлены"
    if new != text:
        path.write_text(new, encoding="utf-8")
    print(f"  {path.name}: {action}, слагов в таблице: {n} ({internal})")
    return True


def main(argv: list[str]) -> int:
    if not REF_DIR.exists():
        print(f"Нет каталога {REF_DIR.relative_to(ROOT)} — нечего обновлять.")
        return 0
    targets = argv[1:]
    files = sorted(p for p in REF_DIR.glob("*.md") if not p.name.startswith("_"))
    if targets:
        files = [p for p in files if p.stem in targets or p.name in targets]
    print(f"Синхронизация AUTO-таблиц в {len(files)} файл(ах) {REF_DIR.relative_to(ROOT)}/:")
    ok = sum(update_file(p) for p in files)
    print(f"Готово: обновлено {ok}/{len(files)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
