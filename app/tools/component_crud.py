"""
Component CRUD, layout, copy, and config introspection.

Split from component_operations.py for maintainability.
Functions:
- _list_types, _validate_dataset, _validate_dataset_fields
- _add_component, _get_component, _get_component_data, _update_component
- _update_layout, _swap_components, _delete_component, _copy_component
- _get_breakpoints, _update_breakpoint
- _list_slugs, _list_presets
"""

import logging
import re
import hashlib
from collections import Counter

import copy
from typing import Any

from ..core.exceptions import NotFoundError, error_response, mask_sensitive
from ..core.validation import sanitize_html
from .builders import build_component_config, check_unsupported_params, generate_uid
from .text_block_helper import apply_textblock_layout_workaround
# fetch_dataset_alias_map импортируется внутри функций ниже
# (lazy import — избегаем circular: component_filters imports BREAKPOINT_COLS
# from component_crud).
from .config_schema import (
    SLUG_SCHEMA, CHART_TYPE_MAP,
    validate_config_overrides, apply_slug_overrides,
    apply_title, apply_bg_color, enrich_slug,
)
from .config_presets import PRESETS

logger = logging.getLogger(__name__)


async def _list_types(client) -> dict[str, Any]:
    """List all component types."""
    response = await client.api_call("components", "list")

    if response.get("status") != 200:
        return {"success": False, "error": response.get("message", "Unknown error")}

    data = response.get("data", [])

    # Group components by types
    charts = []
    tables = []
    maps = []
    filters = []
    other = []

    # какие типы реально создаваемы через MCP (builder chart_type_map);
    # plugin/legacy-типы (CustomChart0-3, PivotOrb/Mdx) — UI-only, add их
    # отклоняет guard'ом.
    from .builders import build_component_config  # noqa: F401 (карта ниже)
    _creatable = {
        "HsBarAMchartsChart", "HsLineAMchartsChart", "HsAreaAMchartsChart",
        "HsPieAMchartsChart", "HsRadarAMchartsChart", "HsStockAMchartsChart",
        "HsSpeedometerV2AMcharts", "HsBubbleAMchartsChart", "HsSunburstChart",
        "HsTreeMap", "HsParallelCoordsChart", "HsPivotChart",
        "HsComparisonChart", "HsTreeGraph", "HsMapLeafletChart",
        "HsTilemapChart", "HsFilterControlPanel", "HsHierarchicalFilterPanel",
        "HsSubheaderComponent", "HsIframe", "HsImagePanel", "HsPageContainer",
        "HsTotalsPanelV2", "HsTableReactabularChart", "HsTextBlock",
        "HsTabsPanel", "HsSwitchControlPanel", "HsAudioplayer",
    }

    for c in data:
        comp = {
            "id": c.get("ID"),
            "name": c.get("name"),
            "caption": c.get("caption"),
            "type": c.get("type"),
            "base": c.get("base", "internal"),
            # False = UI-only/plugin/legacy: component_crud(add) отклонит.
            # сравниваем по type (технический HsBarAMchartsChart),
            # name — человекочитаемое, в _creatable не встречается никогда.
            "mcp_creatable": c.get("type") in _creatable,
        }

        comp_type = c.get("type", "").lower()

        if "chart" in comp_type or "pie" in comp_type or "bar" in comp_type or "line" in comp_type:
            charts.append(comp)
        elif "table" in comp_type or "pivot" in comp_type:
            tables.append(comp)
        elif "map" in comp_type or "leaflet" in comp_type or "tilemap" in comp_type:
            maps.append(comp)
        elif "filter" in comp_type or "select" in comp_type:
            filters.append(comp)
        else:
            other.append(comp)

    return {
        "success": True,
        "total_count": len(data),
        "charts": charts,
        "tables": tables,
        "maps": maps,
        "filters": filters,
        "other": other
    }


def _apply_visual_overrides(
    cfg: dict[str, Any],
    component_type: str,
    stacking: str | None = None,
    orientation: str | None = None,
    preset: str | None = None,
    legend_visible: bool | None = None,
    legend_position: str | None = None,
    labels_visible: bool | None = None,
    bg_color: str | None = None,
    config_overrides: dict | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """
    Apply 3-level visual customization to component config (in-memory, no HTTP).

    Merge order: preset → atomic → user (user wins).
    Returns (modified_cfg, warnings).

    Note: Column field name → field ID resolution for per-column slugs is NOT done here
    because at add time the component is freshly built and field IDs are not yet assigned.
    For update, the caller should resolve column references before passing config_overrides.
    """
    warnings: list[str] = []

    # Normalize orientation: the MCP param accepts words ("horizontal"/"vertical"),
    # but the underlying slug enum is ("h"/"v"). Translate so the value is applied
    # instead of being silently dropped by slug validation.
    if orientation in ("horizontal", "vertical"):
        orientation = {"horizontal": "h", "vertical": "v"}[orientation]

    # normalize legend_position: the MCP param accepts short words
    # ("top"/"bottom"/"left"/"right"), but the slug enum legend.position
    # expects composite values (top-center, bottom-center, middle-left,
    # middle-right, ...). Translate so the value is applied instead of being
    # silently dropped by slug validation.
    _legend_pos_map = {
        "top": "top-center",
        "bottom": "bottom-center",
        "left": "middle-left",
        "right": "middle-right",
    }
    if legend_position in _legend_pos_map:
        legend_position = _legend_pos_map[legend_position]

    # bg_color (per-type handling)
    if bg_color is not None and bg_color != "":
        apply_bg_color(cfg, component_type, bg_color)

    # Map atomic visual params → slug overrides
    atomic_overrides: dict[str, Any] = {}
    _atomic_map = {
        "legend.visible": legend_visible,
        "legend.position": legend_position,
        "labels.visible": labels_visible,
        "orientation": orientation,
        "stacking": stacking,
    }
    for slug, val in _atomic_map.items():
        if val is not None:
            atomic_overrides[slug] = val

    # Preset overrides
    preset_overrides: dict[str, Any] = {}
    if preset:
        preset_overrides = PRESETS.get(preset, {})
        if not preset_overrides:
            warnings.append(f"Unknown preset '{preset}', ignored")

    # User config_overrides
    user_overrides = config_overrides or {}

    # Merge: preset → atomic → user (user wins)
    merged = {**preset_overrides, **atomic_overrides, **user_overrides}

    if merged:
        cleaned, validate_warnings = validate_config_overrides(merged, component_type)
        warnings.extend(validate_warnings)
        if cleaned:
            cfg = apply_slug_overrides(cfg, cleaned, component_type)

    # === Render-breaking guards ===
    # subMode=true на таблице БЕЗ категорий нарушает рендер всего отчёта
    # (loadReport: TypeError undefined.fields — фронту не из чего строить
    # группы промежуточных итогов).
    if cfg.get("subMode"):
        _has_categories = any(
            axis.get("fields")
            for axis in cfg.get("axes", [])
            if axis.get("type") in ("categories", "rows")
        )
        if not _has_categories:
            cfg["subMode"] = False
            warnings.append(
                "subMode (regimes.subtotals) requires category/grouping "
                "fields — disabled to prevent a whole-report render failure "
                "(frontend TypeError in loadReport)."
            )

    return cfg, warnings


def _builder_error_response(new_component: Any) -> dict[str, Any] | None:
    """guard: build_component_config возвращает error-dict (не raise)
    для неизвестного component_type. Без проверки у вызывателей битый
    компонент (type:"unknown", config:{}) записывался бы в grid с
    success:true — персистентная порча отчёта.

    Returns:
        error-конверт {"success": False, "error", "hint", ...} если builder
        вернул ошибку, иначе None (компонент валиден, можно писать в grid).
    """
    if not (isinstance(new_component, dict) and "error" in new_component):
        return None
    builder_hint = new_component.get("hint") or ""
    result = {"success": False, **new_component}
    result["hint"] = (
        (builder_hint + " " if builder_hint else "")
        + "Use component_crud(action='types_list') for the full list of valid types."
    )
    return result


async def _validate_dataset(client, dataset_id: int) -> dict[str, Any]:
    """
    Validate that dataset exists and data is accessible.

    Returns:
        {"success": True, "dataset": {...}, "rows_count": N} if valid
        {"success": False, "error": "..."} if invalid
    """
    # 1. Check dataset exists via datasets/get
    ds_response = await client.api_call("datasets", "get", object_id=dataset_id)

    if ds_response.get("status") != 200:
        return {
            "success": False,
            "error": f"Dataset {dataset_id} not found or not accessible",
            "details": ds_response.get("message", "Unknown error")
        }

    ds_data = ds_response.get("data", [])
    if not ds_data:
        return {
            "success": False,
            "error": f"Dataset {dataset_id} not found"
        }

    dataset = ds_data[0] if isinstance(ds_data, list) else ds_data
    dataset_name = dataset.get("caption") or dataset.get("name", f"Dataset {dataset_id}")

    # 2. Try to fetch data to verify accessibility
    try:
        # Use proper recordsets.create format with empty select (= all fields)
        validation_params = {
            "select": [],
            "where": [],
            "group": [],
            "order": [],
            "having": {"condition": ""},
            "series": {"enable": 0},
            "limit": 5  # Just check if data is accessible
        }
        rs_response = await client.api_call("recordsets", "create", object_id=dataset_id, data=[validation_params])

        # Response can be:
        # 1. List of rows directly (new API format)
        # 2. Dict with {status, data} (legacy format)
        if isinstance(rs_response, list):
            rows = rs_response
        elif isinstance(rs_response, dict):
            if rs_response.get("status") and rs_response.get("status") != 200:
                error_msg = rs_response.get("message", "Unknown error")
                return {
                    "success": False,
                    "error": f"Dataset '{dataset_name}' (id={dataset_id}) is not accessible",
                    "details": error_msg,
                    "hint": "Check datasource connection or dataset SQL query"
                }
            rows = rs_response.get("data", [])
        else:
            rows = []

        rows_count = len(rows)

        if rows_count == 0:
            return {
                "success": False,
                "error": f"Dataset '{dataset_name}' (id={dataset_id}) contains no data",
                "hint": "Dataset exists but returns 0 rows. Check the SQL query or data source."
            }

        return {
            "success": True,
            "dataset": {
                "id": dataset_id,
                "name": dataset_name,
                "rows_count": rows_count
            }
        }

    except Exception as e:
        return error_response(
            f"Error validating dataset {dataset_id}",
            hint="Check that the dataset exists, SQL is valid, and the datasource is reachable (preflight_check_datasource).",
            details=mask_sensitive(str(e)),
            dataset_id=dataset_id,
        )


async def _validate_dataset_fields(
    client,
    dataset_id: int,
    category_field: str,
    value_field: str
) -> dict[str, Any]:
    """
    Validate that specified fields exist in the dataset.

    Returns:
        {"success": True} if all fields exist
        {"success": False, "error": "...", "available_fields": [...]} if invalid
    """
    # Get dataset fields
    fields_response = await client.api_call("datasets", "get", object_id=dataset_id)

    if fields_response.get("status") != 200:
        return {"success": False, "error": f"Cannot get dataset {dataset_id} fields"}

    ds_data = fields_response.get("data", [])
    if not ds_data:
        return {"success": False, "error": f"Dataset {dataset_id} not found"}

    dataset = ds_data[0] if isinstance(ds_data, list) else ds_data
    dataset_name = dataset.get("caption") or dataset.get("name", f"Dataset {dataset_id}")

    # Get field names from dataset
    fields = dataset.get("fields", [])
    available_field_names = []
    for f in fields:
        name = f.get("name", "")
        alias = f.get("alias", "")
        if name:
            available_field_names.append(name)
        if alias and alias != name:
            available_field_names.append(alias)

    # Check category field (if specified)
    if category_field and category_field not in available_field_names:
        return {
            "success": False,
            "error": f"Field '{category_field}' not found in dataset '{dataset_name}'",
            "available_fields": available_field_names[:20],
            "hint": "Check field name or use dataset_operations(action='fields_list') to see available fields"
        }

    # Check value fields
    if value_field:
        value_fields = [f.strip() for f in value_field.split(",") if f.strip()]
        missing_fields = []
        for vf in value_fields:
            if vf not in available_field_names:
                missing_fields.append(vf)

        if missing_fields:
            return {
                "success": False,
                "error": f"Field(s) {missing_fields} not found in dataset '{dataset_name}'",
                "available_fields": available_field_names[:20],
                "hint": "Check field names or use dataset_operations(action='fields_list') to see available fields"
            }

    return {
        "success": True,
        # name → type из семантического слоя (для add-time проверок)
        "field_types": {f.get("name", ""): f.get("type") for f in fields if f.get("name")},
    }


async def _add_no_dataset_component(
    client,
    report_id: int,
    component_type: str,
    title: str,
    text_content: str | None = None,
    position: dict | None = None,
    stacking: str | None = None,
    orientation: str | None = None,
    preset: str | None = None,
    legend_visible: bool | None = None,
    legend_position: str | None = None,
    labels_visible: bool | None = None,
    bg_color: str | None = None,
    config_overrides: dict | None = None,
) -> dict[str, Any]:
    """Add a utility component that doesn't need a dataset (ImagePanel, Iframe, TabsPanel, etc.)."""
    text_content = sanitize_html(text_content)

    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}
    report = data[0]

    grid = report.get("grid") or {}
    layouts = grid.get("layouts") or {}
    components = grid.get("components") or {}

    # Component index
    existing_keys = [int(k) for k in components.keys() if k.isdigit()]
    component_idx = str(max(existing_keys) + 1) if existing_keys else "0"

    # Position
    if position is None:
        max_y = 0
        for layout_items in layouts.values():
            if isinstance(layout_items, list):
                for item in layout_items:
                    if isinstance(item, dict):
                        max_y = max(max_y, item.get("y", 0) + item.get("h", 4))
        position = {"x": 0, "y": max_y, "w": 24, "h": 14}

    # Build config (no dataset, no fields)
    new_component = build_component_config(
        component_type=component_type,
        title=title,
        dataset_id=None,
        category_field=None,
        value_fields=[],
        value_fields_type="number",
        aggregation=None,
        field_titles=None,
        text_content=text_content,
    )
    # неизвестный тип → error-конверт, НЕ писать в grid
    builder_error = _builder_error_response(new_component)
    if builder_error:
        return builder_error

    # Apply visual overrides
    add_warnings: list[str] = []
    _has_visual = any(v is not None for v in [
        stacking, orientation, preset, legend_visible,
        legend_position, labels_visible, bg_color, config_overrides,
    ])
    if _has_visual:
        cfg = new_component.get("config", {})
        cfg, visual_warnings = _apply_visual_overrides(
            cfg, component_type, stacking, orientation, preset,
            legend_visible, legend_position, labels_visible,
            bg_color, config_overrides,
        )
        add_warnings.extend(visual_warnings)
        new_component["config"] = cfg

    # Layouts
    layout_configs = {
        "hd": {"w": 30, "h": 16}, "lg": {"w": 24, "h": 14},
        "md": {"w": 20, "h": 14}, "sm": {"w": 15, "h": 14},
        "xs": {"w": 14, "h": 12}, "xxs": {"w": 10, "h": 10}
    }
    for bp, size in layout_configs.items():
        if bp not in layouts:
            layouts[bp] = []
        entry = {
            "x": position.get("x", 0),
            "y": position.get("y", 0),
            "w": position.get("w", size["w"]),
            "h": position.get("h", size["h"]),
            "minH": 2,
            "minW": 2 if bp in ["sm", "xs", "xxs"] else 3,
            "i": component_idx,
            "modified": False,
            "zIndex": len(components) + 1,
            "priority": -1
        }
        apply_textblock_layout_workaround(entry, component_type)
        layouts[bp].append(entry)

    components[component_idx] = new_component
    grid["layouts"] = layouts
    grid["components"] = components
    report["grid"] = grid

    # Save
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error")}

    result = {
        "success": True,
        "message": f"Utility component {component_type} added successfully",
        "report_id": report_id,
        "component": {
            "idx": component_idx,
            "type": component_type,
            "title": title,
            "dataset_id": None,
            "position": position,
        }
    }
    if add_warnings:
        result["warnings"] = add_warnings
    return result


async def _query_distinct_values(client, dataset_id, field_name, limit: int = 50):
    """Distinct-значения поля датасета через recordsets (group-by). Для series-color addressing."""
    try:
        params = {
            "select": [{"lvl": 0, "name": field_name, "alias": field_name, "calc": "", "aggr": "", "fieldAlias": field_name}],
            "where": [], "group": [{"lvl": 0, "name": field_name, "alias": field_name, "calc": "", "aggr": "", "fieldAlias": field_name}],
            "order": [], "having": {"condition": ""}, "series": {"enable": 0}, "limit": limit,
        }
        rs = await client.api_call("recordsets", "create", object_id=dataset_id, data=[params])
        rows = rs if isinstance(rs, list) else (rs.get("data", []) if isinstance(rs, dict) else [])
        out = []
        for r in rows:
            if isinstance(r, dict):
                val = r.get(field_name)
                if val is None and r:
                    val = next(iter(r.values()))
                if val is not None and str(val) not in [str(x) for x in out]:
                    out.append(val)
        return out
    except Exception:
        return []


async def _expand_series_colors(client, config_overrides, dataset_id, series_field):
    """generic visuals.mainColor / visuals.colorPalette(список) → anchored visuals.<серия>.fillColor
    по distinct-значениям серийного поля. named-палитра (str) и autoColor не раскрываются.
    Возвращает (новые_overrides, заметки)."""
    if not config_overrides or not series_field or not dataset_id:
        return config_overrides, []
    palette = config_overrides.get("visuals.colorPalette")
    main = config_overrides.get("visuals.mainColor")
    want_palette = isinstance(palette, list) and len(palette) > 0
    want_main = bool(main) and isinstance(main, str)
    if not (want_palette or want_main):
        return config_overrides, []
    values = await _query_distinct_values(client, dataset_id, series_field)
    if not values:
        return config_overrides, [
            f"series-color: не удалось получить distinct-значения серии '{series_field}' — "
            f"цвет-слаг не раскрыт (используй явный visuals.<серия>.fillColor)"
        ]
    if len(values) > 30:
        return config_overrides, [
            f"series-color: серия '{series_field}' имеет {len(values)} значений (>30) — "
            f"авто-раскрытие пропущено (используй явный visuals.<серия>.fillColor)"
        ]
    out = dict(config_overrides)
    notes = []
    if want_palette:
        out.pop("visuals.colorPalette", None)
        for i, v in enumerate(values):
            out[f"visuals.{v}.fillColor"] = palette[i % len(palette)]
        notes.append(
            f"series-color: colorPalette раскрыт в {len(values)} anchored fillColor "
            f"по сериям поля '{series_field}'"
        )
    if want_main:
        out.pop("visuals.mainColor", None)
        for v in values:
            out[f"visuals.{v}.fillColor"] = main
        notes.append(
            f"series-color: mainColor применён ко всем {len(values)} сериям '{series_field}' (monochrome)"
        )
    return out, notes


async def _add_component(
    client,
    report_id: int,
    component_type: str,
    title: str,
    value_field: str = "",
    dataset_id: int | None = None,
    dataset_name: str | None = None,
    category_field: str | None = None,
    aggregation: str = "max",  # Safe default for pre-aggregated datasets
    value_fields_type: str = "number",
    position: dict | None = None,
    field_titles: dict | None = None,
    where_filter: list[dict] | None = None,
    text_content: str | None = None,
    row_fields: str | None = None,
    column_fields: str | None = None,
    size_field: str | None = None,
    series_field: str | None = None,
    subheader_field: str | None = None,
    info_fields: str | None = None,
    # Visual params applied locally before PUT (saves 1 HTTP roundtrip)
    stacking: str | None = None,
    orientation: str | None = None,
    preset: str | None = None,
    legend_visible: bool | None = None,
    legend_position: str | None = None,
    labels_visible: bool | None = None,
    bg_color: str | None = None,
    config_overrides: dict | None = None,
) -> dict[str, Any]:
    """
    Add component to report.

    Args:
        report_id: Report ID to add component to
        component_type: Type of component (HsBarAMchartsChart, HsLineAMchartsChart, etc.)
        title: Component title
        value_field: Value field(s), comma-separated for multiple
        dataset_id: Dataset ID
        dataset_name: Alternative to dataset_id - search by name
        category_field: Category/dimension field for grouping
        aggregation: Aggregation function for value fields.

            ## FOR LLM: How to choose aggregation

            **RULE 1: Check if dataset is PRE-AGGREGATED (SQL has GROUP BY)**
            If dataset SQL looks like:
            ```sql
            SELECT region, COUNT(*) as order_count, AVG(amount) as avg_amount
            FROM sales GROUP BY region
            ```
            Then data is ALREADY aggregated. Use:
            - aggregation="max" - SAFE DEFAULT for pre-aggregated data
              (returns the single value per category unchanged)

            **RULE 2: For RAW datasets (no GROUP BY in SQL)**
            If dataset SQL looks like:
            ```sql
            SELECT * FROM sales
            ```
            Then you MUST aggregate:
            - "sum" - for counts, amounts, totals (order_count, revenue, quantity)
            - "avg" - for averages, rates (avg_price, conversion_rate)
            - "count" - to count rows
            - "min"/"max" - for extremes

            **RULE 3: Match field semantics**
            - Field name contains "count", "total", "sum" -> use "sum"
            - Field name contains "avg", "average", "rate" -> use "max" (already averaged)
            - Field name contains "percent", "ratio" -> use "max" (already calculated)

            **RULE 4: TABLES (HsTableReactabularChart) - ALWAYS use "none"**
            Tables should display ALL rows from dataset without grouping.
            - aggregation="none" - shows all rows as-is
            - If you use "max"/"sum"/etc, table will show only 1 aggregated row!

            **Examples:**
            - Pre-aggregated dataset with `order_count` -> aggregation="max"
            - Pre-aggregated dataset with `avg_amount` -> aggregation="max"
            - Raw dataset, want total orders -> aggregation="sum"
            - Raw dataset, want average price -> aggregation="avg"
            - TABLE component -> aggregation="none" (ALWAYS!)

        value_fields_type: Type for value fields ("number" or "string")
        position: Position dict {"x": int, "y": int, "w": int, "h": int}
        field_titles: Dict mapping field names to human-readable titles
                      e.g., {"object_name": "Object API", "command_name": "Command"}
        where_filter: Filter conditions for the component
                      e.g., [{"field": "object_name", "operator": "=", "value": "imports"}]
        text_content: HTML content for HsTextBlock component
    """
    text_content = sanitize_html(text_content)

    # ── No-dataset utility types: skip dataset/field validation entirely ──
    from .builders import NO_DATASET_TYPES as _NO_DATASET_TYPES
    if component_type in _NO_DATASET_TYPES:
        return await _add_no_dataset_component(
            client, report_id, component_type, title,
            text_content=text_content, position=position,
            stacking=stacking, orientation=orientation, preset=preset,
            legend_visible=legend_visible, legend_position=legend_position,
            labels_visible=labels_visible, bg_color=bg_color,
            config_overrides=config_overrides,
        )

    # Get dataset_id by name
    if dataset_name:
        ds_response = await client.api_call("datasets", "list")
        if ds_response.get("status") != 200:
            return {"success": False, "error": f"Error: {ds_response.get('message')}"}

        all_datasets = ds_response.get("data", [])
        found = None
        search_name = dataset_name.lower().strip()

        # Exact match
        for ds in all_datasets:
            if (ds.get("caption") or "").lower().strip() == search_name or \
               (ds.get("name") or "").lower().strip() == search_name:
                found = ds
                break

        # Partial match
        if not found:
            for ds in all_datasets:
                if search_name in (ds.get("caption") or "").lower() or \
                   search_name in (ds.get("name") or "").lower():
                    found = ds
                    break

        if not found:
            available = [f"{ds.get('ID')}: {ds.get('caption')}" for ds in all_datasets[:10]]
            return {"success": False, "error": f"Dataset '{dataset_name}' not found", "available": available}

        dataset_id = found.get("ID")

    if not dataset_id:
        return {"success": False, "error": "Specify dataset_id or dataset_name"}

    # Validate dataset - check if data is accessible
    validation = await _validate_dataset(client, dataset_id)
    if not validation["success"]:
        return validation

    # Validate fields exist in dataset
    fields_validation = await _validate_dataset_fields(
        client, dataset_id, category_field, value_field
    )
    if not fields_validation["success"]:
        return fields_validation

    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]

    # Parse value fields
    value_fields = [f.strip() for f in value_field.split(",") if f.strip()]
    if not value_fields:
        return {"success": False, "error": "No value fields specified"}

    # Get grid
    grid = report.get("grid") or {}
    layouts = grid.get("layouts") or {}
    components = grid.get("components") or {}

    # Component index
    existing_keys = [int(k) for k in components.keys() if k.isdigit()]
    component_idx = str(max(existing_keys) + 1) if existing_keys else "0"

    # Determine position
    if position is None:
        max_y = 0
        for layout_items in layouts.values():
            if isinstance(layout_items, list):
                for item in layout_items:
                    if isinstance(item, dict):
                        max_y = max(max_y, item.get("y", 0) + item.get("h", 4))
        position = {"x": 0, "y": max_y, "w": 24, "h": 14}

    # Generate config
    # IMPORTANT: Aggregation logic depends on component type and category_field:
    # - TABLES (HsTableReactabularChart): ALWAYS use "none" to show all rows
    # - CHARTS with category_field: GROUP BY is used -> value fields need aggregation
    # For pre-aggregated data, "max" safely returns the single value per category

    # AUTO-FIX: Tables should always use aggregation="none"
    if "Table" in component_type and aggregation != "none":
        aggregation = "none"  # Tables must show all rows, not aggregate

    add_warnings: list[str] = []
    if aggregation == "none":
        agg_value = None  # Will be handled by builders.py based on category_field
    else:
        agg_value = aggregation
    # Warn if aggregation will be auto-set by builders.py
    if category_field and not agg_value and "Table" not in component_type:
        add_warnings.append(
            "aggregation not specified with category_field -- auto-set to 'max'. "
            "Pass aggregation='sum'/'avg'/etc. for explicit control."
        )
    # warn о игнорируемых params (column_fields / series_field)
    # TreeGraph: фронт делает Number(identity) при scroll-to-root — строковый
    # identity (value_fields[0]) даёт NaN → null-reference в GoJS.
    if component_type == "HsTreeGraph" and value_fields:
        _first_type = fields_validation.get("field_types", {}).get(value_fields[0])
        if _first_type == "string":
            add_warnings.append(
                f"HsTreeGraph identity field '{value_fields[0]}' is STRING — "
                f"frontend does Number(identity) and fails on NaN; use a "
                f"numeric id (e.g. ROW_NUMBER() in dataset SQL)."
            )
    add_warnings.extend(check_unsupported_params(
        component_type=component_type,
        column_fields=column_fields,
        series_field=series_field,
        category_field=category_field,
        value_field=value_field,
    ))
    # подтянуть alias-map из dataset чтобы builder использовал
    # русские aliases (а не fallback на name) в category/value/where fields.
    from .component_filters import fetch_dataset_alias_map  # lazy: circular
    field_alias_map = await fetch_dataset_alias_map(client, dataset_id)
    new_component = build_component_config(
        component_type=component_type,
        title=title,
        dataset_id=dataset_id,
        category_field=category_field,
        value_fields=value_fields,
        value_fields_type=value_fields_type,
        aggregation=agg_value,
        field_titles=field_titles,
        where_filter=where_filter,
        text_content=text_content,
        row_fields=row_fields,
        column_fields=column_fields,
        size_field=size_field,
        series_field=series_field,
        subheader_field=subheader_field,
        info_fields=info_fields,
        field_alias_map=field_alias_map,
    )
    # неизвестный тип → error-конверт, НЕ писать в grid
    builder_error = _builder_error_response(new_component)
    if builder_error:
        return builder_error

    # generic mainColor/colorPalette → anchored visuals.<серия>.fillColor (до validate)
    if config_overrides and series_field and dataset_id:
        config_overrides, _sc_notes = await _expand_series_colors(
            client, config_overrides, dataset_id, series_field)
        add_warnings.extend(_sc_notes)

    # Apply visual params locally before PUT (no extra HTTP roundtrip)
    _has_visual = any(v is not None for v in [
        stacking, orientation, preset, legend_visible,
        legend_position, labels_visible, bg_color, config_overrides,
    ])
    if _has_visual:
        cfg = new_component.get("config", {})
        cfg, visual_warnings = _apply_visual_overrides(
            cfg, component_type, stacking, orientation, preset,
            legend_visible, legend_position, labels_visible,
            bg_color, config_overrides,
        )
        add_warnings.extend(visual_warnings)
        new_component["config"] = cfg

    # Layout configs for breakpoints
    layout_configs = {
        "hd": {"w": 30, "h": 16}, "lg": {"w": 24, "h": 14},
        "md": {"w": 20, "h": 14}, "sm": {"w": 15, "h": 14},
        "xs": {"w": 14, "h": 12}, "xxs": {"w": 10, "h": 10}
    }

    for bp, size in layout_configs.items():
        if bp not in layouts:
            layouts[bp] = []
        entry = {
            "x": position.get("x", 0),
            "y": position.get("y", 0),
            "w": position.get("w", size["w"]),
            "h": position.get("h", size["h"]),
            "minH": 2,
            "minW": 2 if bp in ["sm", "xs", "xxs"] else 3,
            "i": component_idx,
            "modified": False,
            "zIndex": len(components) + 1,
            "priority": -1
        }
        # HsTextBlock-only: фронт клампит до 88px без modified=True/group=-1.
        # No-op для всех остальных типов. См. text_block_helper.
        apply_textblock_layout_workaround(entry, component_type)
        layouts[bp].append(entry)

    components[component_idx] = new_component
    grid["layouts"] = layouts
    grid["components"] = components
    report["grid"] = grid

    # Save
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error")}

    result = {
        "success": True,
        "message": "Component added successfully",
        "report_id": report_id,
        "component": {
            "idx": component_idx,
            "type": component_type,
            "title": title,
            "dataset_id": dataset_id,
            "position": position
        }
    }
    # карта без geokeys не рендерится — подсказываем map_set_geokeys
    if "MapLeaflet" in component_type and not new_component.get("config", {}).get("geokeys"):
        result["hint"] = (
            "Карта НЕ отрисуется без гео-привязки. Следующим шагом вызови "
            "component_styling(action='map_set_geokeys', report_id=..., component_idx=" + str(component_idx) + ", "
            "config_overrides={'latfield':'lat','lonfield':'lng'}) — bubble (круги на координатах), "
            "ИЛИ config_overrides={'geo_type':'fo.geojson.json','geofield':'NAME'} — choropleth (заливка полигонов)."
        )
    if add_warnings:
        result["warnings"] = add_warnings
    return result


async def _get_component_data(
    client,
    report_id: int,
    component_idx: int,
    limit: int = 100
) -> dict[str, Any]:
    """Get component data."""
    # Get report
    result = await client.api_call("reports", "get", object_id=report_id)

    if result.get("status") != 200:
        return {"success": False, "error": f"Error: {result.get('message')}"}

    data = result.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        return {"success": False, "error": "Invalid data format"}

    # Get components
    grid = data.get("grid", {})
    components = grid.get("components", {})

    # Find component
    component_key = str(component_idx)
    if component_key not in components:
        return {
            "success": False,
            "error": f"Component {component_idx} not found",
            "available": list(components.keys())
        }

    comp = components[component_key]
    cfg = comp.get("config", {})

    # Component caption
    caption_raw = cfg.get("caption__ru") or cfg.get("caption") or cfg.get("title")
    if isinstance(caption_raw, dict):
        caption = caption_raw.get("text") or caption_raw.get("ru") or str(caption_raw)
    elif caption_raw:
        caption = str(caption_raw)
    else:
        caption = f"Component {component_idx}"

    # Native class identity drives axis semantics; chartType is a renderer slug.
    # An inactive Comparison series and Pivot's pivotAgg/pivotOrder must be
    # interpreted identically to the actual frontend.
    comp_type = comp.get("type") or cfg.get("type") or cfg.get("chartType") or "unknown"
    comp_type = {"comparisonChart": "HsComparisonChart", "pivotChart": "HsPivotChart"}.get(comp_type, comp_type)

    # Find dataset_id, collect fields and filters from component config
    dataset_id = cfg.get("datasetId") or cfg.get("dataSetId")
    component_fields = []
    category_fields = []  # Fields from categories axis → group by
    order_fields = []
    sort_select_fields = []
    filter_conditions = []

    for axis in cfg.get("axes", []):
        axis_type = axis.get("type", "")

        if comp_type == "HsComparisonChart" and axis_type == "series" and axis.get("selectedFieldIndex") == -1:
            continue

        # Extract filter fields
        if axis_type == "filters":
            for field in axis.get("fields", []):
                field_name = field.get("name", "")
                operator = field.get("operator", "=")
                selection = (cfg.get("filters") or {}).get(field_name, {})
                if field.get("global"):
                    selection = (data.get("globalFilters") or {}).get(field.get("alias") or field_name, selection)
                values = selection.get("selected", field.get("values", [])) if selection.get("enabled", True) else []
                if field_name and values:
                    # Build where condition in proper recordsets.create format
                    filter_conditions.append({
                        "lvl": 0,
                        "name": field_name,
                        "not": False,
                        "values": values,
                        "operators": [operator] * len(values),
                        "logicOr": 1 if len(values) > 1 else 0  # OR for multiple values
                    })
            continue

        # Track category fields for group-by
        if axis_type in {"categories", "series", "rows", "columns", "objects", "indicators", "identity", "linkage"}:
            for field in axis.get("fields", []):
                fname = field.get("name", "")
                if fname:
                    category_fields.append(fname)
                    selection = (cfg.get("filters") or {}).get(fname, (cfg.get("filters") or {}).get(field.get("alias"), {}))
                    if ((axis_type == "objects" and selection.get("type") == "by compare") or
                            (axis_type == "indicators" and selection.get("type") == "by value")) and selection.get("selected"):
                        selected = selection["selected"]
                        filter_conditions.append({"lvl": 0, "name": fname, "not": False, "values": selected,
                            "operators": ["="] * len(selected), "logicOr": int(len(selected) > 1)})
                    direction = field.get("pivotOrder") if comp_type == "HsPivotChart" else field.get("order")
                    if direction in {"asc", "desc"}:
                        sort_value = field.get("sortByFieldValue") or fname
                        sort_name, _, sort_calc = sort_value.partition("$!$")
                        sort_alias = fname + "_sortBy" if sort_calc else fname
                        if sort_calc:
                            sort_select_fields.append({"lvl": 0, "name": sort_name, "alias": sort_alias,
                                "calc": sort_calc, "aggr": field.get("sortByAgg") or "max", "fieldAlias": field.get("sortByFieldName") or sort_name})
                        order_fields.append({"name": sort_name, "alias": sort_alias, "calc": sort_calc,
                            "direction": direction, "dir": direction, "orderIndex": field.get("orderIndex", 0)})

        # Extract data fields
        for field in axis.get("fields", []):
            if field.get("datasetId"):
                if not dataset_id:
                    dataset_id = field["datasetId"]
            field_info = {
                "id": field.get("id"),
                "axis": axis_type,
                "name": field.get("name"),
                "alias": field.get("alias") or field.get("name"),
                "title": field.get("title", ""),  # Human-readable title
                "aggr": (field.get("pivotAgg") or "sum") if comp_type == "HsPivotChart" and axis_type == "values" else field.get("agg") or field.get("aggregation") or "",
                "calc": field.get("calc", "") if field.get("type") == "calculated" else "",
            }
            component_fields.append(field_info)

    if not dataset_id:
        return {
            "success": True,
            "component": {
                "caption": caption,
                "type": comp_type
            },
            "message": "Component not linked to dataset",
            "columns": [],
            "rows": [],
            "total_rows": 0
        }

    # Build select based on component fields (if any configured)
    # Format: [{lvl, name, alias, calc, aggr, fieldAlias}]
    select_fields = []
    def identifier(name):
        return str(name).encode("utf-8")[:63].decode("utf-8", errors="ignore")
    field_counts = Counter(identifier(f.get("name", "")) for f in component_fields)
    has_collisions = any(n>1 for n in field_counts.values())
    column_bindings = []
    used_aliases = {name for name,count in field_counts.items() if count==1}
    if component_fields:
        for index,f in enumerate(component_fields):
            field_name = f.get("name", "")
            field_title = f.get("title") or field_name  # Use title for fieldAlias
            aggr = f.get("aggr", "")
            output_name = field_name
            if field_counts[identifier(field_name)]>1:
                output_name = "giga_field_"+hashlib.sha256(str([f.get("id"),f.get("axis"),index]).encode()).hexdigest()[:20]
                while output_name in used_aliases:output_name+="_"
            used_aliases.add(output_name)
            if has_collisions:
                column_bindings.append({"id":f.get("id"),"axis":f.get("axis"),"field":field_name,"label":field_title,"aggregation":aggr,"output_name":identifier(output_name)})
            select_fields.append({
                "lvl": 0,
                "name": field_name,
                "alias": output_name,
                "calc": f.get("calc", ""),
                "aggr": aggr if aggr else "",
                "fieldAlias": field_title  # Human-readable name
            })

    # Build group-by from category fields when aggregation is present
    select_fields.extend(sort_select_fields)
    # Calculated raw expressions (e.g. graph parent or formatted table cells)
    # are not aggregates. Pivot/comparison use dimensions outside categories.
    has_aggregation = any(f.get("aggr") or re.search(r"\b(?:SUM|AVG|MIN|MAX|COUNT)\s*\(", f.get("calc") or "", re.I) for f in component_fields)
    group_fields = []
    if has_aggregation and category_fields:
        category_fields.extend(f["name"] for f in component_fields if not f.get("aggr") and not f.get("calc"))
        for fname in dict.fromkeys(category_fields):
            expression = next((f.get("calc") for f in component_fields if f["name"] == fname and f.get("calc")), "")
            group_fields.append({
                "lvl": 0,
                "name": fname,
                "alias": fname,
                "calc": expression,
                "aggr": "",
                "fieldAlias": fname
            })
        for order in order_fields:
            if not order.get("calc"):
                order["calc"] = next((f.get("calc") for f in component_fields if f["name"] == order["name"] and f.get("calc")), "")

    # Get data from recordset with proper format
    data_params = {
        "select": select_fields,  # Use component fields or empty for all
        "where": filter_conditions,  # Apply component filters
        "group": group_fields,
        "order": sorted(order_fields, key=lambda item: item.get("orderIndex", 0)),
        "having": {"condition": ""},
        "series": {"enable": 0},
        "limit": limit
    }
    rs_result = await client.api_call("recordsets", "create", object_id=dataset_id, data=[data_params])

    # Response can be list (direct rows) or dict with status
    if isinstance(rs_result, list):
        rows = rs_result
    elif isinstance(rs_result, dict):
        if rs_result.get("status") and rs_result.get("status") != 200:
            return {"success": False, "error": f"Error getting data: {rs_result.get('message')}"}
        rows = rs_result.get("data", [])
    else:
        rows = []

    columns = list(rows[0].keys()) if rows else []
    if column_bindings and rows:
        expected_outputs = {b["output_name"] for b in column_bindings}
        if any(not expected_outputs.issubset(row) for row in rows):
            return {"success":False,"error":"COLUMN_BINDING_MISMATCH: query omitted projected field outputs","column_bindings":column_bindings}

    return {
        "success": True,
        "component": {
            "idx": component_idx,
            "caption": caption,
            "type": comp_type
        },
        "dataset_id": dataset_id,
        "columns": columns,
        "column_bindings": column_bindings,
        "rows": rows[:limit],
        "total_rows": len(rows),
        "limited": len(rows) > limit
    }


async def _get_component(
    client,
    report_id: int,
    component_idx: int,
    include_raw: bool = False,
) -> dict[str, Any]:
    """Get full component configuration.

    include_raw=True добавляет в ответ config_raw — полный сырой config
    компонента как он хранится в отчёте (для аудита slug-ов: slugs_applied
    в update — лишь счётчик, подтверждение реальной записи — здесь).
    """
    # Get report
    result = await client.api_call("reports", "get", object_id=report_id)

    if result.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    data = result.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        raise NotFoundError(f"Invalid data format for report {report_id}", object_id=report_id)

    # Get grid and components
    grid = data.get("grid", {})
    components = grid.get("components", {})
    layouts = grid.get("layouts", {})

    # Find component
    component_key = str(component_idx)
    if component_key not in components:
        return {
            "success": False,
            "error": f"Component {component_idx} not found",
            "available": list(components.keys())
        }

    comp = components[component_key]
    cfg = comp.get("config", {})

    # Extract caption/title
    caption_raw = cfg.get("caption__ru") or cfg.get("caption") or cfg.get("title")
    if isinstance(caption_raw, dict):
        caption = caption_raw.get("text") or caption_raw.get("ru") or str(caption_raw)
    elif caption_raw:
        caption = str(caption_raw)
    else:
        caption = f"Component {component_idx}"

    # Component type
    comp_type = (
        cfg.get("type") or
        cfg.get("componentType") or
        cfg.get("chartType") or
        comp.get("type") or
        "unknown"
    )

    # Dataset ID
    dataset_id = cfg.get("datasetId") or cfg.get("dataSetId")

    # Extract fields from axes
    fields = []
    axes_info = []
    for axis in cfg.get("axes", []):
        axis_type = axis.get("type", "unknown")
        axis_fields = []
        for field in axis.get("fields", []):
            field_info = {
                "name": field.get("name"),
                "alias": field.get("alias"),
                "type": field.get("type"),
                "dataset_id": field.get("datasetId"),
                "aggregation": field.get("agg") or field.get("aggregation")  # API stores as "agg"
            }
            axis_fields.append(field_info)
            fields.append(field_info)
            if not dataset_id and field.get("datasetId"):
                dataset_id = field["datasetId"]
        axes_info.append({
            "type": axis_type,
            "fields": axis_fields
        })

    # Get position from layouts (use lg as primary)
    position = {}
    lg_layout = layouts.get("lg", [])
    for item in lg_layout:
        if isinstance(item, dict) and str(item.get("i")) == component_key:
            position = {
                "x": item.get("x", 0),
                "y": item.get("y", 0),
                "w": item.get("w", 24),
                "h": item.get("h", 14),
                "zIndex": item.get("zIndex", 1)
            }
            break

    # Extract additional config options
    config_options = {
        "showLegend": cfg.get("showLegend"),
        "showTooltip": cfg.get("showTooltip"),
        "colorPalette": cfg.get("colorPalette"),
        "orientation": cfg.get("orientation"),
        "stacked": cfg.get("stacked"),
        "aggregation": cfg.get("aggregation")
    }
    # Remove None values
    config_options = {k: v for k, v in config_options.items() if v is not None}

    # Include geokeys for map components
    geokeys = cfg.get("geokeys")
    if geokeys:
        config_options["geokeys"] = geokeys

    # Include link for iframe/image components
    link = cfg.get("link")
    if link:
        config_options["link"] = link

    component_info: dict[str, Any] = {
        "idx": component_key,
        "type": comp_type,
        "title": caption,
        "dataset_id": dataset_id,
        "position": position,
        "axes": axes_info,
        "fields": fields,
        "config": config_options,
        # Discoverability: какие ключи реально есть в сыром config
        "config_keys": sorted(cfg.keys()),
    }
    if include_raw:
        component_info["config_raw"] = cfg
    return {
        "success": True,
        "component": component_info
    }


async def _update_component(
    client,
    report_id: int,
    component_idx: int,
    title: str | None = None,
    dataset_id: int | None = None,
    category_field: str | None = None,
    value_field: str | None = None,
    aggregation: str | None = None,
    text_content: str | None = None,
    legend_visible: bool | None = None,
    legend_position: str | None = None,
    labels_visible: bool | None = None,
    orientation: str | None = None,
    bg_color: str | None = None,
    stacking: str | None = None,
    config_overrides: dict | None = None,
    preset: str | None = None,
    field_titles: dict | None = None,
    series_field: str | None = None,
) -> dict[str, Any]:
    """Update component configuration with 3-level visual customization."""
    text_content = sanitize_html(text_content)

    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)

    if get_response.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    data = get_response.get("data", [])
    if not data:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    report = data[0]
    grid = report.get("grid", {})
    components = grid.get("components", {})

    # Find component
    component_key = str(component_idx)
    if component_key not in components:
        return {
            "success": False,
            "error": f"Component {component_idx} not found",
            "available": list(components.keys())
        }

    comp = components[component_key]
    cfg = comp.get("config", {})

    # Track changes
    changes = {}

    component_type = comp.get("type", "")
    warnings_all = []

    # Update title (per-type handling)
    # Guard: MCP framework may send "" instead of None for unset optional str params
    if title is not None and title != "":
        old_title = cfg.get("caption__ru") or cfg.get("caption") or cfg.get("title")
        if isinstance(old_title, dict):
            old_title = old_title.get("text", "")
        apply_title(cfg, component_type, title)
        changes["title"] = {"old": old_title, "new": title}

    # Update dataset_id
    if dataset_id is not None:
        old_dataset_id = cfg.get("datasetId") or cfg.get("dataSetId")
        cfg["datasetId"] = dataset_id
        cfg["dataSetId"] = dataset_id

        # Update dataset_id in all axes fields
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                field["datasetId"] = dataset_id

        changes["dataset_id"] = {"old": old_dataset_id, "new": dataset_id}

    # Build dataset field metadata map (alias + type from semantic layer)
    # Load when: dataset changed, or category/value fields updated
    ds_alias_map: dict[str, str] = {}
    ds_type_map: dict[str, str] = {}
    effective_ds_id = dataset_id or cfg.get("datasetId") or cfg.get("dataSetId")
    if not effective_ds_id:
        # Fallback: some components store datasetId only on axis fields (e.g. batch-created),
        # not at top level. Recover it so rebuilding value/category fields doesn't unlink the dataset.
        for _axis in cfg.get("axes", []):
            for _field in _axis.get("fields", []):
                if _field.get("datasetId"):
                    effective_ds_id = _field["datasetId"]
                    break
            if effective_ds_id:
                break
        if effective_ds_id:
            cfg["datasetId"] = effective_ds_id
            cfg["dataSetId"] = effective_ds_id
    if effective_ds_id and (dataset_id or category_field or value_field
                            or series_field):
        try:
            ds_resp = await client.api_call("datasets", "get", object_id=effective_ds_id)
            if ds_resp.get("status") == 200:
                ds_data = ds_resp.get("data", [])
                if ds_data:
                    for f in ds_data[0].get("fields", []):
                        fname = f.get("name", "")
                        falias = f.get("alias", fname)
                        ftype = f.get("type", "number")
                        if fname:
                            ds_type_map[fname] = ftype
                            if falias and falias != fname:
                                ds_alias_map[fname] = falias
        except Exception:
            pass  # Fallback: use field name as alias, "number" as type

    # When dataset changed, refresh aliases on ALL existing axis fields from dataset
    if dataset_id and ds_alias_map:
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                fname = field.get("name", "")
                if fname in ds_alias_map:
                    field["alias"] = ds_alias_map[fname]

    # Update aggregation
    if aggregation is not None and aggregation != "":
        # AUTO-FIX: Tables should always use aggregation="none"
        comp_type = comp.get("type", "")
        if "Table" in comp_type and aggregation != "none":
            aggregation = "none"  # Tables must show all rows, not aggregate

        old_aggregation = cfg.get("aggregation")
        cfg["aggregation"] = aggregation if aggregation != "none" else None

        # Update aggregation in all value axes
        # IMPORTANT: ModusBI API uses "agg" field (NOT "aggregation"!) - verified from real API response
        # Axis types: "valueY", "value", "valueX", "values" (plural form used in some configs)
        # BubbleChart uses "yvalues", "xvalues" — must be included!
        _VALUE_AXIS_TYPES = {"valueY", "value", "valueX", "values", "yvalues", "xvalues"}
        for axis in cfg.get("axes", []):
            if axis.get("type") in _VALUE_AXIS_TYPES:
                for field in axis.get("fields", []):
                    field["agg"] = aggregation if aggregation != "none" else None

        changes["aggregation"] = {"old": old_aggregation, "new": aggregation}

    # Update category_field
    # Guard: MCP framework may send "" instead of None for unset optional str params
    if category_field is not None and category_field != "":
        for axis in cfg.get("axes", []):
            if axis.get("type") in ["categoryX", "category", "categoryY", "categories"]:
                old_field = axis.get("fields", [{}])[0].get("name") if axis.get("fields") else None
                cat_alias = ds_alias_map.get(category_field, category_field)
                if axis.get("fields"):
                    axis["fields"][0]["name"] = category_field
                    axis["fields"][0]["alias"] = cat_alias
                else:
                    # Create field in empty categories axis
                    axis["fields"] = [{
                        "name": category_field,
                        "alias": cat_alias,
                        "type": "string",
                        "datasetId": effective_ds_id,
                        "id": generate_uid(),
                    }]
                changes["category_field"] = {"old": old_field, "new": category_field}
                break

    # Update series_field: перестраиваем axes.series.fields
    # (контракт как у add).
    if series_field is not None and series_field != "":
        from .builders import SERIES_FIELD_SUPPORTED_TYPES
        comp_hs_type = comp.get("type", "")
        if comp_hs_type not in SERIES_FIELD_SUPPORTED_TYPES:
            warnings_all.append(
                f"series_field ignored on {comp_hs_type} — supported only on "
                f"{sorted(SERIES_FIELD_SUPPORTED_TYPES)}."
            )
        else:
            for axis in cfg.get("axes", []):
                if axis.get("type") == "series":
                    old_series = [f.get("name") for f in axis.get("fields", [])]
                    axis["fields"] = [{
                        "datasetId": effective_ds_id,
                        "agg": None,  # series — группировка, не aggregation
                        "units": None,
                        "type": "string",
                        "name": series_field.strip(),
                        "alias": ds_alias_map.get(series_field.strip(),
                                                  series_field.strip()),
                        "title": "",
                        "id": generate_uid(),
                    }]
                    changes["series_field"] = {"old": old_series,
                                               "new": [series_field.strip()]}
                    break
            else:
                warnings_all.append(
                    "series_field: component has no series axis — not applied."
                )

    # Update value_field
    # Guard: MCP framework may send "" instead of None for unset optional str params
    _VALUE_AXIS_TYPES_ALL = {"valueY", "value", "valueX", "values", "yvalues", "xvalues"}
    if value_field is not None and value_field != "":
        value_fields = [f.strip() for f in value_field.split(",") if f.strip()]

        def _make_field_entry(vf: str, agg_axis: dict) -> dict:
            calculated = next((f for a in cfg.get("axes", []) for f in a.get("fields", [])
                               if f.get("name") == vf and f.get("type") == "calculated"), None)
            if calculated is not None:
                return copy.deepcopy(calculated)
            # IMPORTANT: ModusBI API uses "agg" field (NOT "aggregation"!)
            # Effective aggregation: explicit param → top-level cfg →
            # existing field-level agg on this axis.
            agg = None
            if aggregation and aggregation != "none":
                agg = aggregation
            else:
                agg = cfg.get("aggregation")
                if not agg and agg_axis.get("fields"):
                    agg = agg_axis["fields"][0].get("agg")
            return {
                "name": vf,
                "alias": ds_alias_map.get(vf, vf),
                "type": ds_type_map.get(vf, "number"),
                "datasetId": effective_ds_id,
                "agg": agg,
                "id": generate_uid(),
            }

        axes_by_type = {a.get("type"): a for a in cfg.get("axes", [])}
        y_axis = axes_by_type.get("yvalues")
        x_axis = axes_by_type.get("xvalues")
        if y_axis is not None and x_axis is not None:
            # Bubble: контракт builder'а — value_fields[0]→Y, [1]→X.
            # value_fields[0] идёт в yvalues, value_fields[1] — в xvalues;
            # иначе пустая xvalues даёт пустой рендер + NaN-слайдеры.
            old_fields = ([f.get("name") for f in y_axis.get("fields", [])]
                          + [f.get("name") for f in x_axis.get("fields", [])])
            y_axis["fields"] = [_make_field_entry(value_fields[0], y_axis)] if value_fields else []
            x_axis["fields"] = ([_make_field_entry(value_fields[1], x_axis)]
                                if len(value_fields) > 1 else [])
            changes["value_field"] = {"old": old_fields, "new": value_fields}
            if len(value_fields) < 2:
                warnings_all.append(
                    "bubble requires 2 value fields (Y,X): xvalues axis left "
                    "empty — chart will not render bubbles"
                )
        else:
            for axis in cfg.get("axes", []):
                if axis.get("type") in _VALUE_AXIS_TYPES_ALL:
                    old_fields = [f.get("name") for f in axis.get("fields", [])]
                    axis["fields"] = [_make_field_entry(vf, axis) for vf in value_fields]
                    changes["value_field"] = {"old": old_fields, "new": value_fields}
                    break

    # Update text_content (set all three keys for compatibility)
    # Guard: MCP framework may send "" instead of None for unset optional str params
    if text_content is not None and text_content != "":
        cfg["textContent"] = text_content
        cfg["description"] = text_content
        cfg["description__ru"] = text_content
        changes["text_content"] = {"old": "...", "new": "..."}

    # === Resolve column field names -> field IDs for per-column slugs (update only) ===
    resolved_overrides = config_overrides
    if config_overrides and any(k.startswith("columns.") for k in config_overrides):
        name_to_id: dict[str, str] = {}
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                fname = field.get("name", "")
                fid = field.get("id", fname)
                if fname:
                    name_to_id[fname] = fid
        resolved: dict[str, Any] = {}
        for key, val in config_overrides.items():
            if key.startswith("columns."):
                col_parts = key.split(".", 2)
                if len(col_parts) == 3:
                    _, field_ref, prop = col_parts
                    field_id = name_to_id.get(field_ref, field_ref)
                    resolved[f"columns.{field_id}.{prop}"] = val
                    continue
            resolved[key] = val
        resolved_overrides = resolved

    # series-color addressing (update): раскрыть generic visuals.mainColor/colorPalette(список)
    # в anchored visuals.<серия>.fillColor по distinct серии. Серию берём из series_field-параметра
    # или из существующей series-оси компонента. ДО validate/apply (как в _add_component).
    _ds = dataset_id or cfg.get("datasetId") or cfg.get("dataSetId")
    _series = series_field.strip() if (series_field and series_field.strip()) else None
    if not _series:
        for _axis in cfg.get("axes", []):
            if _axis.get("type") == "series":
                _flds = _axis.get("fields", [])
                if _flds:
                    _series = _flds[0].get("name")
                break
    if resolved_overrides and _series and _ds:
        resolved_overrides, _sc_notes = await _expand_series_colors(
            client, resolved_overrides, _ds, _series)
        warnings_all.extend(_sc_notes)

    # === Apply 3-level visual overrides (shared with _add_component) ===
    cfg, visual_warnings = _apply_visual_overrides(
        cfg, component_type, stacking, orientation, preset,
        legend_visible, legend_position, labels_visible,
        bg_color, resolved_overrides,
    )
    warnings_all.extend(visual_warnings)

    # Track changes
    if bg_color is not None and bg_color != "":
        changes["bg_color"] = bg_color
    if preset:
        changes["preset"] = preset
    # Check if any overrides were actually applied
    merged = {**(PRESETS.get(preset, {}) if preset else {})}
    _atomic = {"legend.visible": legend_visible, "legend.position": legend_position,
               "labels.visible": labels_visible,
               "orientation": {"horizontal": "h", "vertical": "v"}.get(orientation, orientation),
               "stacking": stacking}
    merged.update({s: v for s, v in _atomic.items() if v is not None})
    merged.update(resolved_overrides or {})
    if merged:
        cleaned, _ = validate_config_overrides(merged, component_type)
        if cleaned:
            changes["config_overrides"] = cleaned

    # Apply field_titles to existing axis fields (set "title" property)
    if field_titles:
        titles_applied = 0
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                fname = field.get("name", "")
                if fname in field_titles:
                    field["title"] = field_titles[fname]
                    titles_applied += 1
        if titles_applied:
            changes["field_titles"] = {k: v for k, v in field_titles.items()}

    # Save config back
    comp["config"] = cfg
    components[component_key] = comp
    grid["components"] = components
    report["grid"] = grid

    # Save report
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])

    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error saving report")}

    result: dict[str, Any] = {
        "success": True,
        "message": f"Component {component_idx} updated",
        "report_id": report_id,
        "component_idx": component_idx,
        "changes": changes,
    }
    if warnings_all:
        result["warnings"] = warnings_all
    if merged:
        result["slugs_applied"] = len(changes.get("config_overrides", {}))
    return result


async def _update_layout(
    client,
    report_id: int,
    component_idx: int,
    x: int | None = None,
    y: int | None = None,
    w: int | None = None,
    h: int | None = None,
    z_index: int | None = None
) -> dict[str, Any]:
    """Update component position and size."""
    # Get current report
    get_response = await client.api_call("reports", "get", object_id=report_id)

    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error getting report")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    layouts = grid.get("layouts", {})
    components = grid.get("components", {})

    # Check component exists
    component_key = str(component_idx)
    if component_key not in components:
        return {
            "success": False,
            "error": f"Component {component_idx} not found",
            "available_components": list(components.keys())
        }

    # Update layout for all screen sizes
    breakpoints = ["hd", "lg", "md", "sm", "xs", "xxs"]
    old_position = {}
    new_position = {}

    for bp in breakpoints:
        if bp not in layouts:
            continue

        layout_list = layouts[bp]
        for item in layout_list:
            if item.get("i") == component_key:
                # Save old position (only for lg)
                if bp == "lg":
                    old_position = {
                        "x": item.get("x"),
                        "y": item.get("y"),
                        "w": item.get("w"),
                        "h": item.get("h"),
                        "zIndex": item.get("zIndex")
                    }

                # Update values
                if x is not None:
                    item["x"] = x
                if y is not None:
                    item["y"] = y
                if w is not None:
                    item["w"] = w
                if h is not None:
                    item["h"] = h
                if z_index is not None:
                    item["zIndex"] = z_index

                item["modified"] = True

                # Save new position (only for lg)
                if bp == "lg":
                    new_position = {
                        "x": item.get("x"),
                        "y": item.get("y"),
                        "w": item.get("w"),
                        "h": item.get("h"),
                        "zIndex": item.get("zIndex")
                    }
                break

    # Update grid
    grid["layouts"] = layouts
    report["grid"] = grid

    # Save report
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])

    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error saving report")}

    # Get component name
    comp_config = components.get(component_key, {}).get("config", {})
    comp_title = comp_config.get("title", f"Component {component_idx}")
    if isinstance(comp_title, dict):
        comp_title = comp_title.get("text", f"Component {component_idx}")

    return {
        "success": True,
        "message": f"Component {component_idx} position updated",
        "report_id": report_id,
        "component": {
            "idx": component_idx,
            "title": comp_title,
            "old_position": old_position,
            "new_position": new_position
        }
    }


async def _swap_components(
    client,
    report_id: int,
    component_idx_1: int,
    component_idx_2: int
) -> dict[str, Any]:
    """Swap positions of two components."""
    if component_idx_1 == component_idx_2:
        return {"success": False, "error": "Cannot swap component with itself"}

    # Get current report
    get_response = await client.api_call("reports", "get", object_id=report_id)

    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error getting report")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    layouts = grid.get("layouts", {})
    components = grid.get("components", {})

    # Check both components exist
    key1, key2 = str(component_idx_1), str(component_idx_2)
    if key1 not in components:
        return {"success": False, "error": f"Component {component_idx_1} not found"}
    if key2 not in components:
        return {"success": False, "error": f"Component {component_idx_2} not found"}

    # Swap positions in all breakpoints
    breakpoints = ["hd", "lg", "md", "sm", "xs", "xxs"]

    for bp in breakpoints:
        if bp not in layouts:
            continue

        layout_list = layouts[bp]
        item1 = None
        item2 = None

        for item in layout_list:
            if item.get("i") == key1:
                item1 = item
            elif item.get("i") == key2:
                item2 = item

        if item1 and item2:
            # Swap x, y (position)
            item1["x"], item2["x"] = item2["x"], item1["x"]
            item1["y"], item2["y"] = item2["y"], item1["y"]
            item1["modified"] = True
            item2["modified"] = True

    # Update grid
    grid["layouts"] = layouts
    report["grid"] = grid

    # Save report
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])

    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error saving report")}

    # Get component names
    def get_title(comp_key):
        cfg = components.get(comp_key, {}).get("config", {})
        title = cfg.get("title", f"Component {comp_key}")
        return title.get("text", title) if isinstance(title, dict) else title

    return {
        "success": True,
        "message": f"Components {component_idx_1} and {component_idx_2} swapped",
        "report_id": report_id,
        "components": [
            {"idx": component_idx_1, "title": get_title(key1)},
            {"idx": component_idx_2, "title": get_title(key2)}
        ]
    }


async def _delete_component(
    client,
    report_id: int,
    component_idx: int
) -> dict[str, Any]:
    """Delete component from report."""
    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)

    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error getting report")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    layouts = grid.get("layouts", {})
    components = grid.get("components", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {"success": False, "error": f"Component {component_idx} not found"}

    # Get component info before deletion
    comp_config = components.get(component_key, {}).get("config", {})
    comp_title = comp_config.get("title", f"Component {component_idx}")
    if isinstance(comp_title, dict):
        comp_title = comp_title.get("text", f"Component {component_idx}")

    # Remove from components
    del components[component_key]

    # Remove from all layouts
    for bp in layouts:
        layouts[bp] = [item for item in layouts[bp] if item.get("i") != component_key]

    grid["layouts"] = layouts
    grid["components"] = components
    report["grid"] = grid

    # Save report
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])

    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error saving report")}

    return {
        "success": True,
        "message": f"Component {component_idx} deleted",
        "report_id": report_id,
        "deleted": {
            "idx": component_idx,
            "title": comp_title
        }
    }


async def _copy_component(
    client,
    report_id: int,
    component_idx: int,
    target_report_id: int | None = None,
    new_title: str | None = None,
) -> dict[str, Any]:
    """Deep-copy a component within the same report or to another report.

    Creates a new component with regenerated UIDs and auto-positioned at
    the bottom of the target report layout.
    """
    # 1. Fetch source report
    src_response = await client.api_call("reports", "get", object_id=report_id)
    if src_response.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    src_data = src_response.get("data", [])
    if not src_data:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    src_report = src_data[0]
    src_components = src_report.get("grid", {}).get("components", {})

    component_key = str(component_idx)
    if component_key not in src_components:
        return {"success": False, "error": f"Component {component_idx} not found in report {report_id}"}

    # 2. Deep-copy the component
    cloned = copy.deepcopy(src_components[component_key])

    # 3. Regenerate UIDs in axes fields
    for axis in cloned.get("config", {}).get("axes", []):
        for field in axis.get("fields", []):
            field["id"] = f"{field.get('name', 'field')}_{generate_uid()}"

    # 4. Apply new title if requested — через per-type apply_title (пишет
    # правильные ключи caption/caption__ru/title для каждого типа; ручное
    # "caption или title" оставляло старый русский заголовок в caption__ru).
    if new_title:
        cfg = cloned.get("config", {})
        apply_title(cfg, cloned.get("type", ""), new_title)
        cloned["config"] = cfg

    # 5. Determine target report
    dest_report_id = target_report_id or report_id
    if dest_report_id == report_id:
        dest_report = src_report
    else:
        dest_response = await client.api_call(
            "reports", "get", object_id=dest_report_id,
        )
        if dest_response.get("status") != 200:
            raise NotFoundError(
                f"Target report {dest_report_id} not found",
                object_id=dest_report_id,
            )
        dest_data = dest_response.get("data", [])
        if not dest_data:
            raise NotFoundError(
                f"Target report {dest_report_id} not found",
                object_id=dest_report_id,
            )
        dest_report = dest_data[0]

    grid = dest_report.get("grid") or {}
    layouts = grid.get("layouts") or {}
    components = grid.get("components") or {}

    # 6. Next component index
    existing_keys = [int(k) for k in components.keys() if k.isdigit()]
    new_idx = str(max(existing_keys) + 1) if existing_keys else "0"

    # 7. Auto-position at bottom (find max Y from lg layout)
    max_y = 0
    for layout_items in layouts.values():
        if isinstance(layout_items, list):
            for item in layout_items:
                if isinstance(item, dict):
                    max_y = max(max_y, item.get("y", 0) + item.get("h", 4))

    position = {"x": 0, "y": max_y, "w": 24, "h": 14}

    # 8. Generate layout for all 6 breakpoints (same pattern as _add_component)
    layout_configs = {
        "hd": {"w": 30, "h": 16}, "lg": {"w": 24, "h": 14},
        "md": {"w": 20, "h": 14}, "sm": {"w": 15, "h": 14},
        "xs": {"w": 14, "h": 12}, "xxs": {"w": 10, "h": 10},
    }

    for bp, size in layout_configs.items():
        if bp not in layouts:
            layouts[bp] = []
        entry = {
            "x": position["x"],
            "y": position["y"],
            "w": position.get("w", size["w"]),
            "h": position.get("h", size["h"]),
            "minH": 2,
            "minW": 2 if bp in ("sm", "xs", "xxs") else 3,
            "i": new_idx,
            "modified": False,
            "zIndex": len(components) + 1,
            "priority": -1,
        }
        apply_textblock_layout_workaround(entry, cloned.get("type", ""))
        layouts[bp].append(entry)

    # 9. Insert cloned component and save
    components[new_idx] = cloned
    grid["layouts"] = layouts
    grid["components"] = components
    dest_report["grid"] = grid

    update_resp = await client.api_call(
        "reports", "update", object_id=dest_report_id, data=[dest_report],
    )
    if update_resp.get("status") != 200:
        return {"success": False, "error": update_resp.get("message", "Error saving report")}

    cloned_title = (
        cloned.get("config", {}).get("caption__ru")
        or cloned.get("config", {}).get("caption")
        or cloned.get("config", {}).get("title")
        or ""
    )
    # caption__ru — объект {"text": ...}: в ответе отдаём строку
    if isinstance(cloned_title, dict):
        cloned_title = cloned_title.get("text", "")

    return {
        "success": True,
        "message": f"Component {component_idx} copied to index {new_idx}",
        "source_report_id": report_id,
        "target_report_id": dest_report_id,
        "source_component_idx": component_idx,
        "new_component_idx": new_idx,
        "title": cloned_title,
    }


# --- Multi-breakpoint layout ---

BREAKPOINT_COLS: dict[str, int] = {
    "hd": 60, "lg": 48, "md": 40, "sm": 30, "xs": 28, "xxs": 20,
}
"""Max columns per breakpoint (react-grid-layout)."""

_VALID_BREAKPOINTS = frozenset(BREAKPOINT_COLS)


async def _get_breakpoints(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """Return layout position for every breakpoint of a component."""
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error getting report")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    components = grid.get("components", {})
    layouts = grid.get("layouts", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {
            "error": f"Component {component_idx} not found",
            "available_components": list(components.keys()),
        }

    result: dict[str, dict] = {}
    for bp in BREAKPOINT_COLS:
        for item in layouts.get(bp, []):
            if item.get("i") == component_key:
                result[bp] = {
                    "x": item.get("x", 0),
                    "y": item.get("y", 0),
                    "w": item.get("w", 0),
                    "h": item.get("h", 0),
                    "zIndex": item.get("zIndex", 1),
                }
                break

    comp_config = components[component_key].get("config", {})
    comp_title = comp_config.get("title", f"Component {component_idx}")
    if isinstance(comp_title, dict):
        comp_title = comp_title.get("text", f"Component {component_idx}")

    return {
        "success": True,
        "report_id": report_id,
        "component_idx": component_idx,
        "title": comp_title,
        "breakpoints": result,
        "cols_per_breakpoint": BREAKPOINT_COLS,
    }


async def _update_breakpoint(
    client,
    report_id: int,
    component_idx: int,
    breakpoint: str,
    x: int | None = None,
    y: int | None = None,
    w: int | None = None,
    h: int | None = None,
    z_index: int | None = None,
) -> dict[str, Any]:
    """Update layout for a single breakpoint of a component."""
    if breakpoint not in _VALID_BREAKPOINTS:
        return {
            "error": f"Invalid breakpoint: {breakpoint}",
            "valid_breakpoints": sorted(_VALID_BREAKPOINTS),
        }

    max_cols = BREAKPOINT_COLS[breakpoint]
    if w is not None and w > max_cols:
        return {
            "error": (
                f"Width {w} exceeds max columns ({max_cols}) "
                f"for breakpoint '{breakpoint}'"
            ),
            "max_cols": max_cols,
        }

    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error getting report")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    components = grid.get("components", {})
    layouts = grid.get("layouts", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {
            "error": f"Component {component_idx} not found",
            "available_components": list(components.keys()),
        }

    bp_layout = layouts.get(breakpoint, [])
    old_position: dict[str, Any] = {}
    found = False

    for item in bp_layout:
        if item.get("i") == component_key:
            old_position = {
                "x": item.get("x"),
                "y": item.get("y"),
                "w": item.get("w"),
                "h": item.get("h"),
                "zIndex": item.get("zIndex"),
            }
            if x is not None:
                item["x"] = x
            if y is not None:
                item["y"] = y
            if w is not None:
                item["w"] = w
            if h is not None:
                item["h"] = h
            if z_index is not None:
                item["zIndex"] = z_index
            item["modified"] = True
            found = True
            new_position = {
                "x": item.get("x"),
                "y": item.get("y"),
                "w": item.get("w"),
                "h": item.get("h"),
                "zIndex": item.get("zIndex"),
            }
            break

    if not found:
        return {
            "error": (
                f"Component {component_idx} not found in "
                f"breakpoint '{breakpoint}' layout"
            ),
        }

    grid["layouts"] = layouts
    report["grid"] = grid

    update_response = await client.api_call(
        "reports", "update", object_id=report_id, data=[report],
    )
    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error saving report")}

    comp_config = components[component_key].get("config", {})
    comp_title = comp_config.get("title", f"Component {component_idx}")
    if isinstance(comp_title, dict):
        comp_title = comp_title.get("text", f"Component {component_idx}")

    return {
        "success": True,
        "message": (
            f"Component {component_idx} layout updated "
            f"for breakpoint '{breakpoint}'"
        ),
        "report_id": report_id,
        "breakpoint": breakpoint,
        "max_cols": max_cols,
        "component": {
            "idx": component_idx,
            "title": comp_title,
            "old_position": old_position,
            "new_position": new_position,
        },
    }


def _list_slugs(
    component_type: str | None = None,
    category: str | None = None,
    search: str | None = None,
    include_ui: bool = False,
) -> dict[str, Any]:
    """List available config slugs with lazy loading.

    4 modes (priority: search > category > component_type > summary):
    - search set: case-insensitive substring search в имени slug'а.
      Полезно для LLM: search='color' → все slugs про цвет (12+).
    - category set: drill-down в одну категорию (e.g. 'legend' → 10 slugs).
    - component_type set: filter по типу компонента.
    - neither: category summary (counts + 2 examples each).

    добавлен search mode + опционально применяется поверх
    component_type filter (если оба переданы — пересечение).
    """
    # --- Mode 0: search (можно комбинировать с component_type) ---
    if search:
        s = search.strip().lower()
        chart_type = CHART_TYPE_MAP.get(component_type or "", "")
        result: dict[str, dict] = {}
        for slug, schema in SLUG_SCHEMA.items():
            if s not in slug.lower():
                continue
            applies_to = schema.get("applies_to")
            if component_type and applies_to and chart_type and chart_type not in applies_to:
                continue
            result[slug] = enrich_slug(slug, schema) if include_ui else schema
        return {
            "success": True,
            "search": search,
            "component_type": component_type,
            "count": len(result),
            "slugs": result,
            "hint": (
                f"No matches for {search!r} on {component_type}" if not result
                else f"{len(result)} slug(s) matching {search!r}"
            ),
        }

    # --- Mode 1: drill-down by category ---
    if category:
        filtered: dict[str, dict] = {}
        for slug, schema in SLUG_SCHEMA.items():
            prefix = slug.split(".")[0] if "." in slug else "top-level"
            if prefix == category:
                filtered[slug] = enrich_slug(slug, schema) if include_ui else schema
        if not filtered:
            all_cats = sorted(set(
                s.split(".")[0] if "." in s else "top-level" for s in SLUG_SCHEMA
            ))
            return {"success": False, "error": f"Unknown category: {category}", "available_categories": all_cats}
        return {"success": True, "category": category, "count": len(filtered), "slugs": filtered}

    # --- Mode 2: filter by component_type (existing logic) ---
    if component_type:
        chart_type = CHART_TYPE_MAP.get(component_type, "")

        result: dict[str, dict] = {}
        for slug, schema in SLUG_SCHEMA.items():
            applies_to = schema.get("applies_to")
            if applies_to and chart_type and chart_type not in applies_to:
                continue
            result[slug] = enrich_slug(slug, schema) if include_ui else schema

        categories: dict[str, dict] = {}
        for slug, schema in result.items():
            parts = slug.split(".")
            cat = parts[0] if len(parts) > 1 else "top-level"
            categories.setdefault(cat, {})
            categories[cat][slug] = schema

        return {
            "success": True,
            "component_type": component_type,
            "total_slugs": len(result),
            "categories": categories,
            "hint": "Add slug_category='ui:' for each slug's UI label & panel section "
                    "(frontend control name; OFF by default to save tokens).",
        }

    # --- Mode 3: category summary (default, lightweight) ---
    groups: dict[str, list[str]] = {}
    for slug in SLUG_SCHEMA:
        prefix = slug.split(".")[0] if "." in slug else "top-level"
        groups.setdefault(prefix, []).append(slug)

    return {
        "success": True,
        "total": len(SLUG_SCHEMA),
        "categories": {
            g: {"count": len(slugs), "examples": slugs[:2]}
            for g, slugs in sorted(groups.items())
        },
        "hint": "Use slug_category='legend' for details, or component_type='HsBarAMchartsChart' for type-specific slugs. "
                "Prefix 'ui:' (e.g. slug_category='ui:legend') to also get each slug's UI label & panel section "
                "from the frontend — OFF by default to save tokens, request when you need panel names.",
    }


def _list_presets() -> dict[str, Any]:
    """List available presets with their slug overrides."""
    return {
        "success": True,
        "presets": {
            name: {"slugs": slugs, "slug_count": len(slugs)}
            for name, slugs in PRESETS.items()
        },
        "total": len(PRESETS),
    }
