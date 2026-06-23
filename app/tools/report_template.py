"""
Report template operations for MCP Server.

Actions:
- list: List available report templates with ASCII previews
- preview: Detailed layout preview for a specific template
- scaffold: Create report and populate with template components
"""

import logging

from typing import Any

from ..core.exceptions import require
from ..core.security import check_action
from .batch_operations import _add_multiple_components, _NO_DATA_TYPES
from .report_operations import _create_report

logger = logging.getLogger(__name__)


# Types that don't need value_field/dataset_id during scaffold
_SCAFFOLD_NO_DATA = _NO_DATA_TYPES | frozenset({"HsFilterControlPanel", "HsHierarchicalFilterPanel"})


# ---------------------------------------------------------------------------
# Template definitions
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict[str, Any]] = {
    "kpi_dashboard": {
        "name": "KPI Dashboard",
        "description": "3 filters + 4 KPI (2x2) + main chart + treemap + detail table",
        "cols": 48,
        "components": [
            {"type": "HsFilterControlPanel", "title": "Фильтр 1", "x": 0, "y": 0, "w": 16, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 2", "x": 16, "y": 0, "w": 16, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 3", "x": 32, "y": 0, "w": 16, "h": 3, "slot": "filter"},
            {"type": "HsTotalsPanelV2", "title": "KPI 1", "x": 0, "y": 3, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "KPI 2", "x": 24, "y": 3, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "KPI 3", "x": 0, "y": 6, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "KPI 4", "x": 24, "y": 6, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsBarAMchartsChart", "title": "Основной график", "x": 0, "y": 9, "w": 48, "h": 7, "slot": "chart", "preset": "dashboard"},
            {"type": "HsTreeMap", "title": "По категориям", "x": 0, "y": 16, "w": 24, "h": 8, "slot": "chart"},
            {"type": "HsTableReactabularChart", "title": "Детальная таблица", "x": 24, "y": 16, "w": 24, "h": 8, "slot": "table"},
        ],
        "ascii": (
            "+--------------------------------------------------+ 48 cols\n"
            "| [Filter 1 ▼]  | [Filter 2 ▼]  | [Filter 3 ▼]   |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|       KPI #1 (w=24)    |      KPI #2 (w=24)      |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|       KPI #3 (w=24)    |      KPI #4 (w=24)      |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|              Main Chart (bar)                     |  h=7\n"
            "+------------------------+-------------------------+\n"
            "|       TreeMap          |        Table             |  h=8\n"
            "+------------------------+-------------------------+"
        ),
    },
    "ranking": {
        "name": "Ranking",
        "description": "2 filters + top-N bar + treemap + table + 2 comparison charts",
        "cols": 48,
        "components": [
            {"type": "HsFilterControlPanel", "title": "Фильтр 1", "x": 0, "y": 0, "w": 24, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 2", "x": 24, "y": 0, "w": 24, "h": 3, "slot": "filter"},
            {"type": "HsBarAMchartsChart", "title": "Топ-N", "x": 0, "y": 3, "w": 24, "h": 7, "slot": "chart", "orientation": "h", "preset": "dashboard"},
            {"type": "HsTreeMap", "title": "Treemap", "x": 24, "y": 3, "w": 24, "h": 7, "slot": "chart"},
            {"type": "HsTableReactabularChart", "title": "Таблица рейтинга", "x": 0, "y": 10, "w": 48, "h": 8, "slot": "table"},
            {"type": "HsBarAMchartsChart", "title": "Сравнение 1", "x": 0, "y": 18, "w": 24, "h": 6, "slot": "chart", "stacking": "normal", "preset": "dashboard"},
            {"type": "HsBarAMchartsChart", "title": "Сравнение 2", "x": 24, "y": 18, "w": 24, "h": 6, "slot": "chart", "orientation": "h", "preset": "dashboard"},
        ],
        "ascii": (
            "+--------------------------------------------------+ 48 cols\n"
            "| [Filter 1 ▼]           | [Filter 2 ▼]            |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|   Bar Chart Top-N      |       Treemap            |  h=7\n"
            "+------------------------+-------------------------+\n"
            "|          Table (full width, drill-down)           |  h=8\n"
            "+------------------------+-------------------------+\n"
            "|  Stacked Bar Chart     |    Horizontal Bar        |  h=6\n"
            "+------------------------+-------------------------+"
        ),
    },
    "comparison": {
        "name": "Period Comparison",
        "description": "2 filters + 4 KPI (2x2) + stacked bar + pie + text + table",
        "cols": 48,
        "components": [
            {"type": "HsFilterControlPanel", "title": "Фильтр 1", "x": 0, "y": 0, "w": 24, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 2", "x": 24, "y": 0, "w": 24, "h": 3, "slot": "filter"},
            {"type": "HsTotalsPanelV2", "title": "Текущий период", "x": 0, "y": 3, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "Прошлый период", "x": 24, "y": 3, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "Изменение %", "x": 0, "y": 6, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "Изменение абс.", "x": 24, "y": 6, "w": 24, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsBarAMchartsChart", "title": "Сравнение по категориям", "x": 0, "y": 9, "w": 24, "h": 7, "slot": "chart", "stacking": "normal", "preset": "dashboard"},
            {"type": "HsPieAMchartsChart", "title": "Распределение", "x": 24, "y": 9, "w": 24, "h": 7, "slot": "chart", "preset": "dashboard"},
            {"type": "HsTextBlock", "title": "Пояснение", "x": 0, "y": 16, "w": 48, "h": 3, "slot": "text", "text_content": "Добавьте описание или выводы здесь"},
            {"type": "HsTableReactabularChart", "title": "Детализация", "x": 0, "y": 19, "w": 48, "h": 8, "slot": "table"},
        ],
        "ascii": (
            "+--------------------------------------------------+ 48 cols\n"
            "| [Filter 1 ▼]           | [Filter 2 ▼]            |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|   KPI curr (w=24)      |   KPI prev (w=24)       |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|   KPI Δ% (w=24)        |   KPI Δ abs (w=24)      |  h=3\n"
            "+------------------------+-------------------------+\n"
            "|  Stacked Bar (current)  |     Pie Chart           |  h=7\n"
            "+------------------------+-------------------------+\n"
            "|       Text Block (description)                    |  h=3\n"
            "+--------------------------------------------------+\n"
            "|          Table (category detail)                  |  h=8\n"
            "+--------------------------------------------------+"
        ),
    },
    "factor_analysis": {
        "name": "Factor Analysis",
        "description": "2 filters + 3 KPI (total/delta/factor sum) + waterfall bar + detail table",
        "cols": 48,
        "components": [
            {"type": "HsFilterControlPanel", "title": "Фильтр 1", "x": 0, "y": 0, "w": 24, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 2", "x": 24, "y": 0, "w": 24, "h": 3, "slot": "filter"},
            {"type": "HsTotalsPanelV2", "title": "Итого", "x": 0, "y": 3, "w": 16, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "Изменение", "x": 16, "y": 3, "w": 16, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "Сумма факторов", "x": 32, "y": 3, "w": 16, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsBarAMchartsChart", "title": "Факторный анализ", "x": 0, "y": 6, "w": 48, "h": 8, "slot": "chart", "preset": "dashboard"},
            {"type": "HsTableReactabularChart", "title": "Детали факторов", "x": 0, "y": 14, "w": 48, "h": 8, "slot": "table"},
        ],
        "ascii": (
            "+--------------------------------------------------+ 48 cols\n"
            "| [Filter 1 ▼]           | [Filter 2 ▼]            |  h=3\n"
            "+-------------+-------------+----------------------+\n"
            "|  KPI Total  |   KPI Δ     |   KPI Factor Sum     |  h=3\n"
            "+-------------+-------------+----------------------+\n"
            "|          Waterfall / Bar Chart (factors)          |  h=8\n"
            "+--------------------------------------------------+\n"
            "|          Table (factor details + deltas)          |  h=8\n"
            "+--------------------------------------------------+"
        ),
    },
    "geo_analytics": {
        "name": "Geo Analytics",
        "description": "3 filters + 3 KPI + map + bar chart + territory table",
        "cols": 48,
        "components": [
            {"type": "HsFilterControlPanel", "title": "Фильтр 1", "x": 0, "y": 0, "w": 16, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 2", "x": 16, "y": 0, "w": 16, "h": 3, "slot": "filter"},
            {"type": "HsFilterControlPanel", "title": "Фильтр 3", "x": 32, "y": 0, "w": 16, "h": 3, "slot": "filter"},
            {"type": "HsTotalsPanelV2", "title": "KPI 1", "x": 0, "y": 3, "w": 16, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "KPI 2", "x": 16, "y": 3, "w": 16, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsTotalsPanelV2", "title": "KPI 3", "x": 32, "y": 3, "w": 16, "h": 3, "slot": "kpi", "preset": "kpi"},
            {"type": "HsMapLeafletChart", "title": "Карта территорий", "x": 0, "y": 6, "w": 24, "h": 10, "slot": "chart"},
            {"type": "HsBarAMchartsChart", "title": "По территориям", "x": 24, "y": 6, "w": 24, "h": 10, "slot": "chart", "orientation": "h", "preset": "dashboard"},
            {"type": "HsTableReactabularChart", "title": "Детали", "x": 0, "y": 16, "w": 48, "h": 8, "slot": "table"},
        ],
        "ascii": (
            "+--------------------------------------------------+ 48 cols\n"
            "| [Filter 1 ▼]  | [Filter 2 ▼]  | [Filter 3 ▼]   |  h=3\n"
            "+-------------+-------------+----------------------+\n"
            "|   KPI #1    |   KPI #2    |       KPI #3         |  h=3\n"
            "+-------------+-------------+----------------------+\n"
            "|      Map (bubble)        | Bar Chart (h)          |  h=10\n"
            "+------------------------+-------------------------+\n"
            "|           Table (by territory)                    |  h=8\n"
            "+--------------------------------------------------+"
        ),
    },
    "simple": {
        "name": "Simple Report",
        "description": "Filter panel + main chart + detail table (no tabs, 3 components)",
        "cols": 48,
        "components": [
            {"type": "HsFilterControlPanel", "title": "Фильтры", "x": 0, "y": 0, "w": 48, "h": 3, "slot": "filter"},
            {"type": "HsBarAMchartsChart", "title": "Основной график", "x": 0, "y": 3, "w": 48, "h": 10, "slot": "chart", "preset": "dashboard"},
            {"type": "HsTableReactabularChart", "title": "Данные", "x": 0, "y": 13, "w": 48, "h": 14, "slot": "table"},
        ],
        "ascii": (
            "+--------------------------------------------------+ 48 cols\n"
            "| [Filter 1 ▼]    [Filter 2 ▼]    [Date]           |  h=3\n"
            "+--------------------------------------------------+\n"
            "|            Main Chart (bar/line/pie)              |  h=10\n"
            "+--------------------------------------------------+\n"
            "|            Table (detail data)                    |  h=14\n"
            "+--------------------------------------------------+"
        ),
    },
}


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def _list_templates() -> dict[str, Any]:
    """Return all available templates with descriptions and ASCII previews."""
    templates = []
    for key, tpl in TEMPLATES.items():
        types = [c["type"] for c in tpl["components"]]
        # Compact type summary: group duplicates
        type_counts: dict[str, int] = {}
        for t in types:
            type_counts[t] = type_counts.get(t, 0) + 1
        type_summary = []
        for t, count in type_counts.items():
            type_summary.append(f"{t} x{count}" if count > 1 else t)

        templates.append({
            "name": key,
            "description": tpl["description"],
            "component_count": len(tpl["components"]),
            "component_types": type_summary,
            "ascii_preview": tpl["ascii"],
        })
    return {"success": True, "count": len(templates), "templates": templates}


def _preview_template(template: str) -> dict[str, Any]:
    """Return detailed layout preview for a single template."""
    tpl = TEMPLATES.get(template)
    if not tpl:
        valid = ", ".join(sorted(TEMPLATES.keys()))
        return {
            "success": False,
            "error": f"Unknown template: {template}",
            "hint": f"Valid: {valid}",
        }

    components = []
    data_count = 0
    no_data_count = 0
    for idx, comp in enumerate(tpl["components"]):
        needs_data = comp["type"] not in _SCAFFOLD_NO_DATA
        if needs_data:
            data_count += 1
        else:
            no_data_count += 1
        components.append({
            "idx": idx,
            "type": comp["type"],
            "title": comp["title"],
            "x": comp["x"],
            "y": comp["y"],
            "w": comp["w"],
            "h": comp["h"],
            "slot": comp.get("slot", ""),
            "needs_data": needs_data,
        })

    return {
        "success": True,
        "template": template,
        "description": tpl["description"],
        "ascii_layout": tpl["ascii"],
        "components": components,
        "data_components_count": data_count,
        "no_data_components_count": no_data_count,
        "hint": "Use action='scaffold' with dataset_id to create this layout",
    }


def _build_batch_components(
    components: list[dict], dataset_id: int | None,
    category_field: str | None = None,
    value_field: str | None = None,
) -> list[dict[str, Any]]:
    """Convert template component defs to batch_operations format.

    Если переданы category_field/value_field — биндим реальные поля по слотам
    (filter→категория, kpi→метрики по кругу, chart→категория+метрика,
    table→категория+все метрики). Без них — прежний каркас с placeholder
    `value` (поля привязываются вручную через component_crud update).
    """
    metrics = [f.strip() for f in (value_field or "").split(",") if f.strip()]
    kpi_cursor = 0
    batch = []
    for comp in components:
        entry: dict[str, Any] = {
            "component_type": comp["type"],
            "title": comp["title"],
            "x": comp["x"], "y": comp["y"],
            "w": comp["w"], "h": comp["h"],
        }
        # Data components need value_field/dataset_id for batch validation
        if comp["type"] not in _NO_DATA_TYPES:
            entry["dataset_id"] = dataset_id
            slot = comp.get("slot", "")
            if not metrics:
                entry["value_field"] = "value"
            elif slot == "filter" or comp["type"] == "HsFilterControlPanel":
                entry["value_field"] = category_field or metrics[0]
                # string — иначе batch-default 'number' рендерит слайдер
                entry["value_fields_type"] = "string"
            elif slot == "kpi":
                entry["value_field"] = metrics[kpi_cursor % len(metrics)]
                kpi_cursor += 1
                entry["aggregation"] = "sum"
            elif slot == "table" or "Table" in comp["type"]:
                cols = ([category_field] if category_field else []) + metrics
                entry["value_field"] = ",".join(cols)
                entry["value_fields_type"] = "string"
                entry["aggregation"] = "none"
            else:  # chart-слоты
                if category_field:
                    entry["category_field"] = category_field
                entry["value_field"] = metrics[0]
                entry["aggregation"] = "sum"
        if comp.get("text_content"):
            entry["text_content"] = comp["text_content"]
        for key in ("preset", "stacking", "orientation"):
            if comp.get(key):
                entry[key] = comp[key]
        batch.append(entry)
    return batch


async def _scaffold_template(
    client,
    template: str,
    dataset_id: int | None = None,
    report_id: int | None = None,
    name: str | None = None,
    group_id: int | None = None,
    category_field: str | None = None,
    value_field: str | None = None,
) -> dict[str, Any]:
    """Create report and populate with template components."""
    tpl = TEMPLATES.get(template)
    if not tpl:
        valid = ", ".join(sorted(TEMPLATES.keys()))
        return {
            "success": False,
            "error": f"Unknown template: {template}",
            "hint": f"Valid: {valid}",
        }

    # Check if any data component exists and dataset_id is missing
    has_data_components = any(
        c["type"] not in _NO_DATA_TYPES for c in tpl["components"]
    )
    if has_data_components and not dataset_id:
        return require(
            {"dataset_id": dataset_id},
            tool="report_template", action="scaffold",
            types={"dataset_id": "int"},
            example=f"report_template(action='scaffold', template='{template}', dataset_id=5, name='My Dashboard')",
        )

    # Step 1: Resolve or create report
    report_created = False
    if not report_id:
        report_name = name or tpl["name"]
        create_result = await _create_report(
            client, name=report_name, caption=report_name,
            group_id=group_id or 1,
        )
        if not create_result.get("success"):
            return {"success": False, "error": f"Failed to create report: {create_result.get('error', 'unknown')}"}
        report_id = create_result["report"]["id"]
        report_created = True

    # Step 2: Build + add components (1 GET + 1 PUT)
    batch_components = _build_batch_components(
        tpl["components"], dataset_id,
        category_field=category_field, value_field=value_field,
    )
    result = await _add_multiple_components(client, report_id, batch_components)
    if not result.get("success"):
        return {"success": False, "error": f"Scaffold failed: {result.get('error', 'unknown')}"}

    # Step 2b: равномерное распределение filter-row по 6 breakpoints.
    # Шаблон выкладывает фильтры на y=0 для одного breakpoint (lg, cols=48).
    # Без grid_layout другие breakpoints (hd=60, sm=30, ...) получат
    # пропорционально wrong w. Вызываем filters_grid_layout для filters-row.
    filter_indices = [
        idx for idx, c in enumerate(tpl["components"])
        if c.get("type") == "HsFilterControlPanel" and c.get("y", 0) == 0
    ]
    layout_warnings: list[str] = []
    if filter_indices and len(filter_indices) > 1:
        from .component_filters import _filters_grid_layout  # lazy import
        try:
            grid_result = await _filters_grid_layout(
                client, report_id,
                component_indices=filter_indices,
                cols=len(filter_indices),
                rows=1, y_start=0, h=3,
            )
            if not grid_result.get("success"):
                layout_warnings.append(
                    f"filters_grid_layout failed: {grid_result.get('error')}"
                )
            elif grid_result.get("warnings"):
                # неравномерное деление по некоторым breakpoints — non-blocking
                layout_warnings.extend(grid_result["warnings"])
        except Exception as exc:
            layout_warnings.append(f"filters_grid_layout exception: {exc}")

    # Step 3: Build response
    comp_info = [
        {
            "idx": idx, "type": c["type"], "title": c["title"],
            "slot": c.get("slot", ""),
            "needs_data": c["type"] not in _SCAFFOLD_NO_DATA,
        }
        for idx, c in enumerate(tpl["components"])
    ]
    # fields_bound — по факту распарсенных метрик (value_field=',' давал бы
    # placeholder при fields_bound=True), тем же выражением, что в билдере.
    _metrics = [f for f in (value_field or "").split(",") if f.strip()]
    fields_bound = bool(_metrics)
    next_steps = []
    if category_field and not fields_bound:
        next_steps.append(
            "⚠️ category_field ignored: биндинг требует value_field (метрики); "
            "передайте value_field или привяжите поля вручную."
        )
    if fields_bound and any(c["type"] == "HsMapLeafletChart" for c in tpl["components"]):
        next_steps.append(
            "Карта (HsMapLeafletChart) требует геопривязку после scaffold: "
            "component_styling(action='map_set_geokeys', config_overrides="
            "{'latfield':..., 'lonfield':...}) или geo_type/geofield для choropleth."
        )
    if not fields_bound:
        next_steps.append(
            f"Update data components with real field names: component_crud(action='update', report_id={report_id}, component_idx=N, value_field='real_field') "
            f"— или сразу передавайте category_field/value_field в scaffold, чтобы поля привязались автоматически."
        )
    next_steps += [
        f"Add filter fields: component_filters(action='filter_field_add', report_id={report_id}, component_idx=N, "
        f"value_field='field_name', alias='Русское название', field_type='string', dataset_id=DS). "
        f"⚠️ CRITICAL: call filter_field_add on EVERY data component (charts, tables, KPIs, maps) — not just FilterControlPanel! "
        f"Without this, global filter is created but data components do NOT react to filter selection.",
        f"Customize styles: component_crud(action='update', report_id={report_id}, component_idx=N, preset='dashboard')",
        "Pro filter layout: replace single FilterControlPanel with separate ones (1 field each, horizontal). "
        "Style each: config_overrides={\"outline.enabled\": true, \"outline.width\": 1, "
        "\"outline.color\": \"rgba(179,179,179,1)\", \"bgColor\": \"rgba(255,255,255,1)\", "
        "\"margin.l\": 5, \"margin.r\": 5}",
    ]
    response = {
        "success": True,
        "message": f"Scaffolded '{template}' with {len(tpl['components'])} components on report {report_id}",
        "report_id": report_id,
        "report_created": report_created,
        "template": template,
        "fields_bound": fields_bound,
        "components": comp_info,
        "added": result.get("added", []),
        "next_steps": next_steps,
    }
    if layout_warnings:
        response["layout_warnings"] = layout_warnings
    return response


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

async def report_template(
    client,
    action: str,
    template: str | None = None,
    report_id: int | None = None,
    dataset_id: int | None = None,
    name: str | None = None,
    group_id: int | None = None,
    category_field: str | None = None,
    value_field: str | None = None,
) -> dict[str, Any]:
    """Report template operations: list, preview, scaffold."""
    match action:
        case "list":
            return _list_templates()
        case "preview":
            err = require(
                {"template": template},
                tool="report_template", action="preview",
                types={"template": "str (one of: kpi_dashboard, ranking, comparison, factor_analysis, geo_analytics, simple)"},
                example="report_template(action='preview', template='kpi_dashboard')",
            )
            if err:
                return err
            return _preview_template(template)
        case "scaffold":
            check_action("create")
            err = require(
                {"template": template},
                tool="report_template", action="scaffold",
                types={"template": "str (one of: kpi_dashboard, ranking, comparison, factor_analysis, geo_analytics, simple)"},
                example="report_template(action='scaffold', template='kpi_dashboard', dataset_id=5, name='My Dashboard')",
            )
            if err:
                return err
            return await _scaffold_template(
                client, template, dataset_id, report_id, name, group_id,
                category_field=category_field, value_field=value_field,
            )
        case _:
            return {"success": False, "error": f"Unknown action: {action}. Valid: list, preview, scaffold"}
