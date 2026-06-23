#!/usr/bin/env python3
"""Единый справочник-соответствие слагов: MCP-слаг ↔ UI-контрол ↔ JSON-путь (фронт-ключ) ↔ тип ↔ default.

Генерирует docs/architecture/components/slugs/README.md из трёх источников:
  - docs/architecture/components/slugs/slug-table.json — слаг → JSON-путь, applies_to, deprecated, invert;
  - app/tools/slug_ui_meta.json                        — слаг → UI-контрол (название в панели), секция;
  - app/tools/config_schema.SLUG_SCHEMA                — тип и значение по умолчанию.

Запуск: python3 scripts/gen_slug_catalog.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.tools.config_schema import SLUG_SCHEMA  # noqa: E402

OUT = ROOT / "docs/architecture/components/slugs/README.md"
TABLE = ROOT / "docs/architecture/components/slugs/slug-table.json"
UIMETA = ROOT / "app/tools/slug_ui_meta.json"

rows = json.loads(TABLE.read_text(encoding="utf-8"))["rows"]
ui = json.loads(UIMETA.read_text(encoding="utf-8"))


def esc(s):
    return (s or "").replace("|", "\\|")


def json_path(r):
    if r.get("json"):
        return f"`{r['json']}`"
    if r.get("effective"):
        return f"`({r['effective']})`"  # секционный ключ — итоговое имя внутри секции
    return "_секционно_"


def default_of(slug):
    d = SLUG_SCHEMA.get(slug, {}).get("default")
    if d is None or d == "":
        return "—"
    return f"`{d}`"


def status_of(r):
    if r.get("deprecated"):
        return "устар."
    if r.get("invert"):
        return "инверт."
    return ""


L = [
    "# Справочник слагов: соответствие MCP ↔ UI ↔ JSON",
    "",
    "> Генерируется из `app/tools/config_schema.py` (SLUG_SCHEMA) — единый источник истины для всех",
    "> слаг-файлов (этот каталог, [by-type.md](by-type.md), [aliases.md](aliases.md), [slug-table.json](slug-table.json)).",
    "> Регенерация: `python3 scripts/gen_slug_catalog.py`.",
    "",
    "**Слаг** — короткое плоское имя одной настройки компонента (например `legend.visible`, `margin.l`,",
    "`colors.palette`). Слаги передаются словарём `config_overrides` в инструменты `component_crud` и",
    "`component_styling`; сервер сам раскладывает каждый слаг в нужный **JSON-путь** внутри конфигурации",
    "компонента, откуда его читает фронтенд портала при отрисовке.",
    "",
    "У одной настройки три имени:",
    "",
    "- **UI-контрол** — как настройка называется в панели справа на портале (то, что видит пользователь);",
    "- **MCP-слаг** — ключ, который ассистент передаёт в `config_overrides`;",
    "- **JSON-путь** — куда значение ложится в конфигурации (это и есть «фронт-ключ», который читает рендер).",
    "",
    "Как применить слаг:",
    "",
    "```text",
    'component_crud(action="update", report_id=<id>, component_idx=0,',
    '               config_overrides={"legend.visible": false, "margin.l": 12})',
    "```",
    "",
    "Подробно про саму идею слагов и зачем три имени — в концепции",
    "[components-json-slugs.md](../../concepts/components-json-slugs.md). Те же слаги, **сгруппированные по",
    "типам компонентов**, — в [by-type.md](by-type.md); устаревшие имена и псевдонимы — в",
    "[aliases.md](aliases.md). Машиночитаемые данные этой таблицы — в [slug-table.json](slug-table.json).",
    "",
    "## Как читать таблицу",
    "",
    "- **MCP-слаг** — ключ для `config_overrides`.",
    "- **UI-контрол** — название в панели настроек портала. Пусто (`—`) = прямого контрола в UI нет,",
    "  настройка задаётся только через `config_overrides`.",
    "- **Секция** — раздел панели настроек, где находится контрол.",
    "- **JSON-путь** — фронт-ключ в конфигурации компонента, **фактический путь записи** (трассирован;",
    "  для большинства слагов совпадает с путём по схеме). `(в скобках)` — ключ обрабатывается секционно",
    "  (итоговое имя внутри своей секции конфига). Машиночитаемый [slug-table.json](slug-table.json) хранит",
    "  оба варианта пути (поля `json` и `effective`).",
    "- **Тип** и **По умолчанию** — из схемы слагов.",
    "- **Применяется к** — типы компонентов, к которым относится слаг; «оформительские» = общие настройки",
    "  (контейнер/диаграммы в целом).",
    "- **Статус** — `устар.` (использовать новое имя, см. aliases.md) или `инверт.` (значение пишется",
    "  с инверсией, например «скрыть» ↔ «показать»).",
    "",
    f"Всего слагов: **{len(rows)}**. Кроме них есть **шаблонные семейства**, задаваемые по образцу",
    "(свой ключ на каждую серию / поле / правило) и потому поимённо в таблицу не вынесенные: анкерные",
    "`visuals.{anchor}.{prop}` (на серию графика), колоночные `columns.{field}.{prop}` (на поле",
    "таблицы/сводной), правила условного форматирования `rules.{n}.{prop}` — их разбор в [by-type.md](by-type.md).",
    "",
    "| MCP-слаг | UI-контрол | Секция | JSON-путь | Тип | По умолчанию | Применяется к | Статус |",
    "|---|---|---|---|---|---|---|---|",
]

for r in sorted(rows, key=lambda x: x["slug"]):
    s = r["slug"]
    m = ui.get(s, {})
    lbl = esc(m.get("ui_label", "")) or "—"
    sec = esc(m.get("ui_section", "")) or "—"
    typ = r.get("type") or SLUG_SCHEMA.get(s, {}).get("type") or "—"
    at = r.get("applies_to") or []
    at_cell = esc(", ".join(at)) if at else "оформительские"
    L.append(
        f"| `{s}` | {lbl} | {sec} | {json_path(r)} | {typ} | {default_of(s)} | {at_cell} | {status_of(r)} |"
    )

L.append("")
OUT.write_text("\n".join(L), encoding="utf-8")
print(f"written {OUT.relative_to(ROOT)} | slugs: {len(rows)}")
