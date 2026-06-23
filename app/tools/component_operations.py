"""
Component operations dispatcher for MCP Server.

Thin dispatcher that delegates to sub-modules:
- component_crud: CRUD, layout, copy, config introspection
- component_filters: global filters + filter axis + cascade management
- component_axes: calculated fields + page management

Actions:
- types_list: List component types
- get: Get component configuration
- add: Add component to report
- update: Update component (title, dataset, fields, aggregation)
- delete: Delete component
- data: Get component data
- layout_update: Update component position/size (all breakpoints)
- layout_get_breakpoints: Get layout for all breakpoints
- layout_update_breakpoint: Update layout for single breakpoint
- swap: Swap two components
- copy: Deep-copy component (same or cross-report)
- set_global_filter / reset_global_filters: Global filter management
- filter_fields_list / filter_field_add / filter_field_remove: Filter axis
- filter_set_cascade: Set/remove cascade dependency (filterBy)
- calc_fields_list / calc_field_add / calc_field_update / calc_field_remove
- page_list / page_add / page_remove / page_rename: PageContainer tabs
- pivot_link_set / pivot_link_remove: Pivot drill-through links
- drill_get / drill_add_level / drill_delete_level / drill_change_level
- drill_toggle_date_range / drill_set_field: Drill-down hierarchy management
- list_slugs / list_presets: Config introspection
- conditional_rule_add / conditional_rule_list / conditional_rule_delete: Conditional formatting
- field_sort_set: Set sort order on field (report_id, component_idx, value_field, config_overrides={"order":"desc"})
- geodata_list: List available GeoJSON files on portal
- map_set_geokeys: Set geokeys (geo-binding) on map component
- map_get_geokeys: Get geokeys config from map component
"""

import logging

from typing import Any

from ..core.exceptions import missing_params, require
from ..core.security import check_action

logger = logging.getLogger(__name__)

# --- CRUD, layout, copy, config introspection ---
from .component_crud import (
    _list_types,
    _validate_dataset,
    _validate_dataset_fields,
    _add_component,
    _get_component,
    _get_component_data,
    _update_component,
    _update_layout,
    _swap_components,
    _delete_component,
    _copy_component,
    _get_breakpoints,
    _update_breakpoint,
    _list_slugs,
    _list_presets,
)

# --- Global filters + filter axis + cascade ---
from .component_filters import (
    _set_global_filter,
    _reset_global_filters,
    _filter_fields_list,
    _filter_field_add,
    _filter_field_remove,
    _filter_set_cascade,
    _filters_grid_layout,
)

# --- Calculated fields + page management + pivot links + drill-down ---
from .component_axes import (
    _fetch_report_component,
    _sync_axes_default,
    _save_report,
    _calc_fields_list,
    _calc_field_add,
    _calc_field_update,
    _calc_field_remove,
    _page_list,
    _page_add,
    _page_remove,
    _page_rename,
    _pivot_link_set,
    _pivot_link_remove,
    _drill_get,
    _drill_add_level,
    _drill_delete_level,
    _drill_change_level,
    _drill_toggle_date_range,
    _drill_set_field,
    _tabs_button_list,
    _tabs_button_add,
    _tabs_button_delete,
)


# ---------------------------------------------------------------------------
# Conditional formatting helpers
# ---------------------------------------------------------------------------

# Mapping: friendly operator names → cons.operator values.

# По исходникам фронта поддерживаются операторы:
# 1. строгий numeric (+e>+t.value): {>, <, >=, <=, =}
# 2. с contains ('~') через (e+"").includes(t.value): {>, <, >=, <=, =, ~}
# 3. polymorphic: {>, <, >=, <=, =, like_both} — `=` поддерживает строки
# через a===e.value без coerce.
# `!=` не поддерживается ни в одной ветке фронта.
# `~` (contains) — экспериментально, не все code-path его уважают.
_OPERATOR_MAP = {
    ">": ">", ">=": ">=", "<": "<", "<=": "<=", "=": "=",
    "gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "eq": "=",
    "greater_than": ">", "greater_or_equal": ">=",
    "less_than": "<", "less_or_equal": "<=", "equal": "=",
    # '~' для contains (substring match) — найден в одном
    # из switches фронта, работает для column-level rules.
    "~": "~", "contains": "~",
}

# операторы которые принимают строковое value без float-coerce.
# Фронт обрабатывает их как a===e.value (без +coerce) или includes() для ~.
# Для остальных (<, >, <=, >=) — принудительный float (numeric comparison).
_STRING_SAFE_OPS = frozenset({"=", "~"})

# Типы, поддерживающие conditional formatting (rules.* slugs).
# Согласовано с config_schema.py: rules.* применяются только к
# chart_type in ("table", "pivotChart"). На других типах config.rules
# не применяется.
_CONDITIONAL_RULE_TYPES = frozenset({
    "HsTableReactabularChart", "HsPivotChart",
})


async def _conditional_rule_add(
    client, report_id: int, component_idx: int,
    rule_config: dict,
) -> dict[str, Any]:
    """Add a conditional formatting rule to a table/pivot component.

    rule_config keys:
      field (str, required): field name to apply the rule to
      operator (str, required): ">", ">=", "<", "<=", "=", or friendly names
      value (float/int, required): threshold value
      name (str, optional): rule display name
      color (str, optional): text color, e.g. "#ffffff"
      background (str, optional): background color, e.g. "#f44336"
      whole_row (bool, optional): apply to entire row
      bold (bool, optional): make text bold
      indicator (str, optional): "up", "down", "dot"
      indicator_color (str, optional): indicator color
    """
    if not rule_config:
        return missing_params(
            ["config_overrides (rule definition with field, operator, value)"],
            tool="component_styling", action="conditional_rule_add",
            example="component_styling(action='conditional_rule_add', report_id=35, component_idx=0, config_overrides={'field':'amount', 'operator':'>', 'value':1000, 'background':'#f44336'})",
        )

    field = rule_config.get("field")
    operator = rule_config.get("operator")
    value = rule_config.get("value")

    # Inspect all three rule fields at once so the LLM sees the full list of gaps.
    rule_missing: list[str] = []
    if not field:
        rule_missing.append("field")
    if not operator:
        rule_missing.append("operator")
    if value is None:
        rule_missing.append("value")
    if rule_missing:
        return missing_params(
            rule_missing,
            tool="component_styling", action="conditional_rule_add",
            types={
                "field": "str (field name in component axes)",
                "operator": "str (>, >=, <, <=, =, !=; or gt/gte/lt/lte/eq/ne)",
                "value": "float | int (для numeric ops) | str (для = и !=,)",
            },
            example="component_styling(action='conditional_rule_add', report_id=35, component_idx=0, config_overrides={'field':'amount', 'operator':'>', 'value':1000, 'background':'#f44336'})",
        )

    # Resolve operator
    op_str = str(operator).lower().strip()
    # операторы, которых нет в коде фронта: `!=`, regex, starts_with, in.
    # `contains` есть как `~`.
    UNSUPPORTED_OPS = {"!=", "ne", "not_equal", "starts_with", "ends_with",
                       "regex", "in", "not_in"}
    if op_str in UNSUPPORTED_OPS:
        return {
            "success": False,
            "error": (
                f"Operator {operator!r} not supported by frontend. "
                f"Available: >, >=, <, <=, = (numeric или строки), ~ (contains, "
                f"substring match — только некоторые code-path). "
                f"Workaround для !=: дублировать правило с противоположным "
                f"условием. Для regex/starts_with: numeric rank-колонка в SQL."
            ),
        }
    resolved_op = _OPERATOR_MAP.get(str(operator))
    if not resolved_op:
        return {"success": False, "error": f"Unknown operator: {operator}. Valid: >, >=, <, <=, =, ~ (contains), or aliases gt/gte/lt/lte/eq"}

    # Get report to count existing rules
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": f"Report {report_id} not found"}
    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    comp_key = str(component_idx)
    components = report.get("grid", {}).get("components", {})
    if comp_key not in components:
        return {"success": False, "error": f"Component {component_idx} not found"}

    comp = components[comp_key]
    cfg = comp.get("config", {})

    # Type-guard: rules.* работают только на table/pivot.
    comp_type = comp.get("type", "")
    if comp_type not in _CONDITIONAL_RULE_TYPES:
        return {
            "success": False,
            "error": (
                f"conditional formatting поддерживается только table/pivot "
                f"({', '.join(sorted(_CONDITIONAL_RULE_TYPES))}), "
                f"component {component_idx} is {comp_type!r}"
            ),
            "component_type": comp_type,
            "supported_types": sorted(_CONDITIONAL_RULE_TYPES),
        }

    existing_rules = cfg.get("rules", [])
    rule_idx = len(existing_rules)

    # Resolve field name → internal field ID (e.g. "amount" → "amount_X7xekZ").
    # Резолвим по имени, alias или уже готовому field-id из осей;
    # промах — явная ошибка (иначе сырое имя записалось бы в fieldId и
    # правило молча не применилось бы на опечатке поля).
    name_to_id: dict[str, str] = {}
    alias_to_id: dict[str, str] = {}
    known_ids: set[str] = set()
    for axis in cfg.get("axes", []):
        for f in axis.get("fields", []):
            fname = f.get("name", "")
            fid = f.get("id", fname)
            if fname:
                name_to_id[fname] = fid
            falias = f.get("alias", "")
            if falias:
                alias_to_id[falias] = fid
            if fid:
                known_ids.add(fid)
    resolved_field_id = name_to_id.get(field) or alias_to_id.get(field)
    if not resolved_field_id:
        if field in known_ids:
            resolved_field_id = field  # уже internal field-id из осей
        else:
            return {
                "success": False,
                "error": f"field '{field}' not found in axes",
                "available": sorted(set(name_to_id) | set(alias_to_id)),
                "hint": (
                    "Передайте name, alias или field-id поля из осей компонента "
                    "(см. 'available')."
                ),
            }

    # для =/!= value может быть строкой (статусы "FAIL"/"PASS").
    # Для прочих numeric операторов — обязательный coerce в float.
    if resolved_op in _STRING_SAFE_OPS and isinstance(value, str):
        cons_value = value  # string as-is
    else:
        try:
            cons_value = float(value)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": (
                    f"value={value!r} cannot be converted to float for "
                    f"operator {resolved_op!r}. Numeric operators (>, >=, <, <=) "
                    f"требуют числовое value. Для текстовых статусов используйте "
                    f"operator='=' или '~' (contains) с string value."
                ),
            }

    # Build slug overrides for the new rule
    prefix = f"rules.{rule_idx}"
    slug_overrides = {
        f"{prefix}.name": rule_config.get("name", f"{field} {resolved_op} {value}"),
        f"{prefix}.fieldId": resolved_field_id,
        f"{prefix}.cons.operator": resolved_op,
        f"{prefix}.cons.value": cons_value,
    }

    # Optional properties
    if rule_config.get("color"):
        slug_overrides[f"{prefix}.color"] = rule_config["color"]
    if rule_config.get("background"):
        slug_overrides[f"{prefix}.background"] = rule_config["background"]
    if rule_config.get("whole_row") is not None:
        slug_overrides[f"{prefix}.wholeRow"] = bool(rule_config["whole_row"])
    if rule_config.get("bold") is not None:
        slug_overrides[f"{prefix}.isTextBold"] = bool(rule_config["bold"])
    if rule_config.get("indicator"):
        slug_overrides[f"{prefix}.indicatorType"] = rule_config["indicator"]
    if rule_config.get("indicator_color"):
        slug_overrides[f"{prefix}.indicatorColor"] = rule_config["indicator_color"]

    # Delegate to _update_component with slug overrides
    result = await _update_component(
        client, report_id, component_idx,
        config_overrides=slug_overrides,
    )

    if not result.get("success"):
        return result

    return {
        "success": True,
        "message": f"Added rule #{rule_idx}: {field} {resolved_op} {value}",
        "rule_index": rule_idx,
        "rule": {
            "field": field,
            "operator": resolved_op,
            "value": value,
            "color": rule_config.get("color"),
            "background": rule_config.get("background"),
            "whole_row": rule_config.get("whole_row", False),
        },
    }


async def _conditional_rule_list(
    client, report_id: int, component_idx: int,
) -> dict[str, Any]:
    """List existing conditional formatting rules on a component."""
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"error": f"Report {report_id} not found"}
    data = get_response.get("data", [])
    if not data:
        return {"error": f"Report {report_id} not found"}

    comp_key = str(component_idx)
    components = data[0].get("grid", {}).get("components", {})
    if comp_key not in components:
        return {"error": f"Component {component_idx} not found"}

    cfg = components[comp_key].get("config", {})
    rules = cfg.get("rules", [])

    result_rules = []
    for idx, rule in enumerate(rules):
        cons = rule.get("cons", {})
        # cons can be {"0": {"operator": ..., "value": ...}, "1": ...} or flat
        op = cons.get("0", {}).get("operator") if isinstance(cons.get("0"), dict) else cons.get("operator")
        val = cons.get("0", {}).get("value") if isinstance(cons.get("0"), dict) else cons.get("value")
        result_rules.append({
            "index": idx,
            "name": rule.get("name", ""),
            "field": rule.get("fieldId"),
            "operator": op,
            "value": val,
            "color": rule.get("color"),
            "background": rule.get("background"),
            "whole_row": rule.get("wholeRow", False),
        })

    return {
        "success": True,
        "count": len(result_rules),
        "rules": result_rules,
    }


async def _conditional_rule_delete(
    client, report_id: int, component_idx: int,
    rule_index: int,
) -> dict[str, Any]:
    """Delete a conditional formatting rule by index."""
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"error": f"Report {report_id} not found"}
    data = get_response.get("data", [])
    if not data:
        return {"error": f"Report {report_id} not found"}

    report = data[0]
    comp_key = str(component_idx)
    components = report.get("grid", {}).get("components", {})
    if comp_key not in components:
        return {"error": f"Component {component_idx} not found"}

    comp = components[comp_key]
    cfg = comp.get("config", {})
    rules = cfg.get("rules", [])

    if not rules:
        return {"error": "No rules exist on this component"}
    if rule_index < 0 or rule_index >= len(rules):
        return {"error": f"Rule index {rule_index} out of range (0-{len(rules) - 1})"}

    removed = rules.pop(rule_index)
    cfg["rules"] = rules
    comp["config"] = cfg
    components[comp_key] = comp

    # Save
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
    if update_response.get("status") != 200:
        return {"error": f"Failed to save: {update_response.get('message', 'unknown')}"}

    return {
        "success": True,
        "message": f"Deleted rule #{rule_index}: {removed.get('name', '')}",
        "remaining_rules": len(rules),
    }


# ---------------------------------------------------------------------------
# Field sort helpers
# ---------------------------------------------------------------------------


async def _field_sort_set(
    client, report_id: int, component_idx: int,
    field_name: str, order: str | None,
) -> dict[str, Any]:
    """Set order (asc/desc/null) on a field in any axis of the component."""
    report, comp, cfg, comp_key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    if order and order not in ("asc", "desc"):
        return {"error": f"Invalid order '{order}', use 'asc', 'desc', or null to clear"}

    # Find field in axes
    found = False
    for axis in cfg.get("axes", []):
        for field in axis.get("fields", []):
            if field.get("name") == field_name:
                field["order"] = order
                field["orderIndex"] = 0 if order else None
                found = True
                break
        if found:
            break

    if not found:
        return {"error": f"Field '{field_name}' not found in axes"}

    _sync_axes_default(cfg)
    comp["config"] = cfg
    report["grid"]["components"][comp_key] = comp

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Field '{field_name}' order set to '{order}'",
        "report_id": report_id,
        "component_idx": component_idx,
    }


# ---------------------------------------------------------------------------
# Geodata + Map geokeys helpers
# ---------------------------------------------------------------------------


async def _geodata_list(client) -> dict[str, Any]:
    """List available GeoJSON files from the portal."""
    result = await client.api_get("geodata")
    # API may return list directly or {"data": [...]}
    if isinstance(result, list):
        items = result
    else:
        items = result.get("data", [])
    geodata = []
    for g in items:
        if isinstance(g, dict):
            # API may put filename in "name", "description", or "file" field
            name = g.get("name") or g.get("description") or g.get("file") or ""
            geodata.append({
                "id": g.get("id"),
                "name": name,
                "type": g.get("type", ""),
                "description": g.get("description", ""),
            })
        else:
            geodata.append({"name": str(g), "type": "", "description": ""})
    return {
        "success": True,
        "geodata": geodata,
        "count": len(geodata),
        "hint": (
            "Choropleth работает только с PRELOADED GeoJSON из этого списка "
            "(map_set_geokeys: geo_type=<name>, geofield=<property>). "
            "Загрузка кастомного GeoJSON через MCP не поддерживается — "
            "добавляется администратором через web-портал. Для произвольных "
            "координат используйте bubble-режим (latfield/lonfield)."
        ),
    }


async def _map_set_geokeys(
    client, report_id: int, component_idx: int, geokeys_config: dict,
) -> dict[str, Any]:
    """Set geokeys (geo-binding) on a map component.

    Two modes:

    Mode 1 — Choropleth (colored polygons from GeoJSON):
      config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"}

    Mode 2 — Bubble markers (circles at lat/lng positions):
      config_overrides={"latfield": "lat", "lonfield": "lng"}
      Sets geodataId=-1, frontend reads coordinates from data fields.

    Common optional keys:
      category_field (str): match specific categories field by name
    """
    # 1. Fetch report + component via existing helper
    report, comp, cfg, comp_key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    # 2. Validate component is a map
    chart_type = cfg.get("chartType", "")
    comp_type = cfg.get("type", "")
    if "map" not in chart_type.lower() and comp_type != "HsMapLeafletChart":
        return {
            "error": f"Component {component_idx} is not a map (chartType: {chart_type}, type: {comp_type})"
        }

    # 3. Detect mode: bubble (latfield+lonfield) or choropleth (geo_type+geofield)
    latfield = geokeys_config.get("latfield")
    lonfield = geokeys_config.get("lonfield")
    geo_type = geokeys_config.get("geo_type")
    geofield = geokeys_config.get("geofield")
    is_bubble = bool(latfield and lonfield)
    is_choropleth = bool(geo_type and geofield)
    # Multilayer (двухлистовой, isSheetOne): полигоны sheet0 + точки sheet1 в ОДНОЙ карте.
    # Триггер — point_id_field вместе с обоими наборами ключей. Не ломает однолистовые
    # ветки: без point_id_field логика прежняя (bubble ИЛИ choropleth).
    point_id_field = geokeys_config.get("point_id_field")
    point_dataset_id = geokeys_config.get("point_dataset_id")
    is_multilayer = bool(point_id_field and is_bubble and is_choropleth)

    if not is_bubble and not is_choropleth:
        from ..core.exceptions import error_response
        return error_response(
            "Invalid geokeys config_overrides: need either bubble-mode or choropleth-mode keys",
            hint=(
                "Bubble mode: config_overrides={'latfield': '<lat>', 'lonfield': '<lon>'}. "
                "Choropleth: config_overrides={'geo_type': 'region', 'geofield': '<code_field>'}."
            ),
            details={
                "bubble_required": ["latfield", "lonfield"],
                "choropleth_required": ["geo_type", "geofield"],
                "provided": list(geokeys_config.keys()),
            },
        )

    # 4. Find field_id from categories axis
    target_field = geokeys_config.get("category_field")
    field_id = None
    for axis in cfg.get("axes", []):
        if axis.get("type") == "categories":
            for f in axis.get("fields", []):
                if target_field and f.get("name") == target_field:
                    field_id = f.get("id", f.get("name"))
                    break
                elif not target_field:
                    field_id = f.get("id", f.get("name"))
                    break
            break

    if not field_id:
        return {"error": "No categories field found on map component"}

    # 5. Build and merge geokeys
    geokeys = cfg.get("geokeys", {})
    geo_warn = None
    if is_multilayer:
        # Двухлистовой: sheet0 = полигоны (cat0 = field_id), sheet1 = точки (новый cat1).
        from .builders import generate_uid
        geo_id = None
        try:
            gd = await client.api_get("geodata")
            items = gd if isinstance(gd, list) else gd.get("data", [])
            for g in items:
                if isinstance(g, dict) and (g.get("name") or g.get("description") or g.get("file")) == geo_type:
                    geo_id = g.get("id")
                    break
            if geo_id is None:
                geo_warn = f"geo_type '{geo_type}' не найден в /geodata"
        except Exception as _e:  # noqa: BLE001
            geo_warn = f"не удалось получить /geodata: {_e}"
        cats_axis = next((a for a in cfg.get("axes", []) if a.get("type") == "categories"), None)
        vals_axis = next((a for a in cfg.get("axes", []) if a.get("type") == "values"), None)
        cat0_name = target_field or next(
            (f.get("name") for f in (cats_axis or {}).get("fields", [])), None)
        # geokey листа 0 — полигоны на существующем поле категории
        gk0 = {"type": geo_type, "geofield": geofield, "datafield": cat0_name}
        if geo_id is not None:
            gk0["geodataId"] = geo_id
        geokeys[field_id] = gk0
        # лист 1 — точки: новое поле категории + lon/lat значения (sheet=1).
        # dataset берём в первую очередь из поля cat0 (у него datasetId заполнен
        # надёжно), т.к. на свежесозданной карте cfg.datasetId может быть пуст.
        cat0_ds = next((f.get("datasetId") for f in (cats_axis or {}).get("fields", []) if f.get("datasetId")), None)
        pds = point_dataset_id or cat0_ds or cfg.get("datasetId") or cfg.get("dataSetId")
        cat1_id = generate_uid()
        if cats_axis is not None:
            for f in cats_axis.get("fields", []):
                f.setdefault("sheet", 0)
            cats_axis.setdefault("fields", []).append({
                "agg": None, "alias": point_id_field, "datasetId": pds, "id": cat1_id,
                "name": point_id_field, "title": "", "type": "number", "units": None, "sheet": 1,
            })
        if vals_axis is not None:
            for f in vals_axis.get("fields", []):
                f.setdefault("sheet", 0)
            vals_axis.setdefault("fields", []).extend([
                {"agg": "max", "alias": lonfield, "datasetId": pds, "id": generate_uid(),
                 "name": lonfield, "title": "", "type": "number", "units": None,
                 "valueType": "longitude", "sheet": 1},
                {"agg": "max", "alias": latfield, "datasetId": pds, "id": generate_uid(),
                 "name": latfield, "title": "", "type": "number", "units": None,
                 "valueType": "latitude", "sheet": 1},
            ])
            # Опционально: поле подсказки точки (addToTooltip=true) — детали записи
            tooltip_field = geokeys_config.get("tooltip_field")
            if tooltip_field:
                vals_axis["fields"].append({
                    "agg": "max", "alias": tooltip_field, "datasetId": pds, "id": generate_uid(),
                    "name": tooltip_field, "title": "", "type": "string", "units": None,
                    "valueType": "value", "addToTooltip": True, "sheet": 1,
                })
        geokeys[cat1_id] = {"geodataId": -1, "lonfield": lonfield, "latfield": latfield}
        cfg["isSheetOne"] = True
        cfg["multilayerMode"] = True
        mode_msg = (f"multilayer: полигоны {geo_type}(geodataId={geo_id}) sheet0 + "
                    f"точки {point_id_field}({latfield}/{lonfield}) sheet1")
    elif is_bubble:
        geokeys[field_id] = {
            "geodataId": -1,
            "latfield": latfield,
            "lonfield": lonfield,
        }
        mode_msg = f"bubble: {latfield}/{lonfield}"
    else:
        # Choropleth: фронту нужен числовой geodataId (резолв из geo_type-имени) +
        # datafield (имя поля-категории данных, которое матчится против geofield geojson).
        # Без geodataId фронт не резолвит preloaded-geojson и виснет на спиннере.
        geo_id = None
        geo_warn = None
        try:
            gd = await client.api_get("geodata")
            items = gd if isinstance(gd, list) else gd.get("data", [])
            for g in items:
                if isinstance(g, dict) and (g.get("name") or g.get("description") or g.get("file")) == geo_type:
                    geo_id = g.get("id")
                    break
            if geo_id is None:
                geo_warn = f"geo_type '{geo_type}' не найден в /geodata — geodataId не резолвлен; хороплет может не отрисоваться"
        except Exception as _e:  # noqa: BLE001
            geo_warn = f"не удалось получить /geodata для резолва geodataId: {_e}"
        datafield = target_field or next(
            (f.get("name") for axis in cfg.get("axes", []) if axis.get("type") == "categories"
             for f in axis.get("fields", [])), None)
        gk = {"type": geo_type, "geofield": geofield, "datafield": datafield}
        if geo_id is not None:
            gk["geodataId"] = geo_id
        geokeys[field_id] = gk
        mode_msg = f"choropleth: {geo_type} ({geofield}), geodataId={geo_id}, datafield={datafield}"
    cfg["geokeys"] = geokeys

    # 6. Save via reports.update
    err = await _save_report(client, report_id, report)
    if err:
        return err

    result = {
        "success": True,
        "geokeys": geokeys,
        "field_id": field_id,
        "message": f"Set geokey: {field_id} → {mode_msg}",
    }
    if geo_warn:
        result["warning"] = geo_warn
    return result


async def _map_get_geokeys(
    client, report_id: int, component_idx: int,
) -> dict[str, Any]:
    """Get geokeys config from a map component."""
    _report, _comp, cfg, _comp_key = await _fetch_report_component(
        client, report_id, component_idx,
    )
    geokeys = cfg.get("geokeys", {})
    return {
        "success": True,
        "geokeys": geokeys,
        "has_geokeys": bool(geokeys),
    }


async def component_operations(
    client,
    action: str,
    report_id: int | None = None,
    component_idx: int | None = None,
    component_idx_2: int | None = None,
    component_type: str | None = None,
    title: str | None = None,
    dataset_id: int | None = None,
    dataset_name: str | None = None,
    category_field: str | None = None,
    value_field: str | None = None,
    aggregation: str = "max",  # Safe default for pre-aggregated datasets
    value_fields_type: str = "number",
    position: dict | None = None,
    x: int | None = None,
    y: int | None = None,
    w: int | None = None,
    h: int | None = None,
    z_index: int | None = None,
    limit: int = 100,
    field_titles: dict | None = None,
    where_filter: list[dict] | None = None,
    text_content: str | None = None,
    row_fields: str | None = None,
    column_fields: str | None = None,
    size_field: str | None = None,
    series_field: str | None = None,
    subheader_field: str | None = None,
    info_fields: str | None = None,
    legend_visible: bool | None = None,
    legend_position: str | None = None,
    labels_visible: bool | None = None,
    orientation: str | None = None,
    bg_color: str | None = None,
    stacking: str | None = None,
    config_overrides: dict | None = None,
    preset: str | None = None,
    alias: str | None = None,
    field_type: str | None = None,
    # === Calculated fields params ===
    calc_expression: str | None = None,
    target_axis: str | None = None,
    # === Copy / page management params ===
    target_report_id: int | None = None,
    page_id: int | None = None,
    # === Multi-breakpoint layout params ===
    breakpoint: str | None = None,
    # === Cascade filter params ===
    depends_on: str | None = None,
    reset_mode: str | None = None,
    reset_type: str | None = None,
    # === Pivot link params ===
    field_id: str | None = None,
    target_url: str | None = None,
    link_target: str = "_blank",
    # === Drill-down params ===
    field_index: int | None = None,
    drill_category_id: str | None = None,
    drill_direction: str | None = None,
    drill_selected: str | None = None,
    # === Slug category filter ===
    slug_category: str | None = None,
) -> dict[str, Any]:
    """
    CRUD operations for report components.

    Actions:
    - types_list: List component types
    - get: Get component configuration (report_id, component_idx)
    - add: Add component to report
    - add_text_block: Add text block component (report_id, title, text_content)
    - update: Update component (title, dataset, fields, visual customization)
    - delete: Delete component
    - data: Get component data
    - layout_update: Update component position/size (all breakpoints uniformly)
    - layout_get_breakpoints: Get layout positions for all breakpoints
    - layout_update_breakpoint: Update layout for a single breakpoint
    - swap: Swap two components
    - set_global_filter: Set filter value on FilterControlPanel component
    - reset_global_filters: Reset all global filters on report
    - filter_fields_list: List fields on component's filter axis
    - filter_field_add: Add field to component's filter axis (+ globalFilters entry, optional cascade)
    - filter_field_remove: Remove field from component's filter axis
    - filter_set_cascade: Set or remove cascade dependency (filterBy) on existing filter
    - calc_fields_list: List calculated fields across all axes
    - calc_field_add: Add calculated field (SQL in alias, type=calculated)
    - calc_field_update: Update calculated field SQL or display name
    - calc_field_remove: Remove calculated field from any axis
    - copy: Deep-copy component (same or cross-report)
    - page_list: List PageContainer pages/tabs
    - page_add: Add page/tab to PageContainer
    - page_remove: Remove page/tab from PageContainer
    - page_rename: Rename page/tab in PageContainer
    - pivot_link_set: Set drill-through link on pivot field (report_id, component_idx, field_id, target_url, title, link_target)
    - pivot_link_remove: Remove drill-through link from pivot field (report_id, component_idx, field_id)
    - conditional_rule_add: Add conditional formatting rule (report_id, component_idx, config_overrides={field, operator, value, ...})
    - conditional_rule_list: List conditional formatting rules (report_id, component_idx)
    - conditional_rule_delete: Delete rule by index (report_id, component_idx, field_index)
    - tabs_button_list: List buttons in TabsPanel (report_id, component_idx)
    - tabs_button_add: Add navigation button to TabsPanel (report_id, component_idx, title=label, config_overrides={link, fill_color, text_color, link_target, font_size})
    - tabs_button_delete: Delete button from TabsPanel by index (report_id, component_idx, field_index=button_index)
    - list_slugs: List available config slugs (optional component_type filter)
    - list_presets: List available presets
    """
    match action:
        case "help":
            from .help_texts import _help, HELP_COMPONENT_CRUD
            return _help(slug_category or value_field, HELP_COMPONENT_CRUD)

        case "types_list":
            return await _list_types(client)

        case "get":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="get",
                types={"report_id": "int", "component_idx": "int"},
                example="component_crud(action='get', report_id=35, component_idx=0)",
            )
            if err:
                return err
            # slug_category="raw" → включить полный сырой config (config_raw)
            # для аудита реально записанных slug-ов.
            return await _get_component(
                client, report_id, component_idx,
                include_raw=(slug_category == "raw"),
            )

        case "add":
            check_action("add")
            # Utility types (no dataset/data): ImagePanel, Iframe, TabsPanel, PageContainer, Subheader
            from .builders import NO_DATASET_TYPES as _NO_DATASET_TYPES
            if component_type in _NO_DATASET_TYPES:
                err = require(
                    {"report_id": report_id, "component_type": component_type, "title": title},
                    tool="component_crud", action="add",
                    types={"report_id": "int", "component_type": "str", "title": "str"},
                    example="component_crud(action='add', report_id=35, component_type='HsImagePanel', title='Logo')",
                )
                if err:
                    return err
            else:
                err = require(
                    {
                        "report_id": report_id,
                        "component_type": component_type,
                        "title": title,
                        "value_field": value_field,
                        "dataset_id": dataset_id,
                    },
                    tool="component_crud", action="add",
                    types={
                        "report_id": "int",
                        "component_type": "str (e.g. 'HsBarAMchartsChart')",
                        "title": "str",
                        "value_field": "str (comma-separated field names)",
                        "dataset_id": "int",
                    },
                    example="component_crud(action='add', report_id=35, component_type='HsBarAMchartsChart', title='Sales', dataset_id=5, category_field='region', value_field='amount', aggregation='sum')",
                )
                if err:
                    return err
            # Auto-assemble position from atomic x/y/w/h
            if position is None and any(v is not None for v in [x, y, w, h]):
                position = {}
                if x is not None: position["x"] = x
                if y is not None: position["y"] = y
                if w is not None: position["w"] = w
                if h is not None: position["h"] = h
            effective_agg = aggregation if aggregation else "max"
            return await _add_component(
                client, report_id, component_type, title, value_field,
                dataset_id, dataset_name, category_field, effective_agg,
                value_fields_type, position, field_titles, where_filter,
                text_content=text_content,
                row_fields=row_fields,
                column_fields=column_fields,
                size_field=size_field,
                series_field=series_field,
                subheader_field=subheader_field,
                info_fields=info_fields,
                # Visual params applied locally before PUT
                stacking=stacking,
                orientation=orientation,
                preset=preset,
                legend_visible=legend_visible,
                legend_position=legend_position,
                labels_visible=labels_visible,
                bg_color=bg_color,
                config_overrides=config_overrides,
            )

        case "add_text_block":
            check_action("add")
            err = require(
                {"report_id": report_id, "title": title, "text_content": text_content},
                tool="component_crud", action="add_text_block",
                types={"report_id": "int", "title": "str", "text_content": "str (HTML, sanitized automatically)"},
                example="component_crud(action='add_text_block', report_id=35, title='Summary', text_content='<div>...</div>')",
            )
            if err:
                return err

            from .text_block_helper import add_text_block_component
            return await add_text_block_component(
                client, report_id, title, text_content, position
            )

        case "add_chart_with_conclusion":
            check_action("add")
            err = require(
                {
                    "report_id": report_id,
                    "component_type": component_type,
                    "title": title,
                    "value_field": value_field,
                    "dataset_id": dataset_id,
                    "text_content": text_content,
                },
                tool="component_crud", action="add_chart_with_conclusion",
                types={
                    "report_id": "int",
                    "component_type": "str",
                    "title": "str",
                    "value_field": "str",
                    "dataset_id": "int",
                    "text_content": "str (HTML conclusion)",
                },
                example="component_crud(action='add_chart_with_conclusion', report_id=35, component_type='HsBarAMchartsChart', title='Hypothesis 1', dataset_id=5, category_field='region', value_field='amount', aggregation='avg', text_content='<div>...</div>')",
            )
            if err:
                return err

            from .layout_helper import add_chart_with_text_pair

            chart_config = {
                "type": component_type,
                "title": title,
                "dataset_id": dataset_id,
                "category_field": category_field,
                "value_field": value_field,
                "aggregation": aggregation if aggregation else "max"
            }

            return await add_chart_with_text_pair(
                client=client,
                report_id=report_id,
                chart_config=chart_config,
                text_html=text_content,
                text_title=title.replace("ГИПОТЕЗА", "ВЫВОД"),
                row_height=h if h else None
            )

        case "update":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="update",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            result = await _update_component(
                client, report_id, component_idx,
                title=title, dataset_id=dataset_id,
                category_field=category_field, value_field=value_field,
                aggregation=aggregation, text_content=text_content,
                legend_visible=legend_visible, legend_position=legend_position,
                labels_visible=labels_visible, orientation=orientation,
                bg_color=bg_color, stacking=stacking,
                config_overrides=config_overrides, preset=preset,
                field_titles=field_titles,
                series_field=series_field,
            )
            # column_fields/row_fields/size_field/subheader_field/info_fields —
            # add-only: _update_component не перестраивает эти оси (series_field
            # применяется). Возвращаем явный warning вместо silent-ignore.
            # Guard "v.strip()": MCP framework шлёт "" вместо None.
            _add_only = [
                name for name, v in (
                    ("column_fields", column_fields),
                    ("row_fields", row_fields),
                    ("size_field", size_field),
                    ("subheader_field", subheader_field),
                    ("info_fields", info_fields),
                ) if v and str(v).strip()
            ]
            if _add_only and isinstance(result, dict):
                result.setdefault("warnings", []).extend(
                    f"{name} is add-only, not applied on update; "
                    f"rebuild component or use component_crud(action='add')"
                    for name in _add_only
                )
            return result

        case "delete":
            check_action("delete")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="delete",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _delete_component(client, report_id, component_idx)

        case "data":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="data",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _get_component_data(client, report_id, component_idx, limit)

        case "layout_update":
            check_action("layout_update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="layout_update",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _update_layout(client, report_id, component_idx, x, y, w, h, z_index)

        case "layout_get_breakpoints":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="layout_get_breakpoints",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _get_breakpoints(client, report_id, component_idx)

        case "layout_update_breakpoint":
            check_action("layout_update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "breakpoint": breakpoint,
                },
                tool="component_crud", action="layout_update_breakpoint",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "breakpoint": "str (one of: hd, lg, md, sm, xs, xxs)",
                },
                example="component_crud(action='layout_update_breakpoint', report_id=35, component_idx=0, breakpoint='xxs', x=0, y=0, w=20, h=10)",
            )
            if err:
                return err
            return await _update_breakpoint(
                client, report_id, component_idx, breakpoint, x, y, w, h, z_index,
            )

        case "swap":
            check_action("swap")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "component_idx_2": component_idx_2},
                tool="component_crud", action="swap",
                types={"report_id": "int", "component_idx": "int", "component_idx_2": "int"},
            )
            if err:
                return err
            return await _swap_components(client, report_id, component_idx, component_idx_2)

        case "set_global_filter":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_filters", action="set_global_filter",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _set_global_filter(
                client, report_id, component_idx, value_field, alias=alias,
            )

        case "reset_global_filters":
            check_action("update")
            err = require(
                {"report_id": report_id},
                tool="component_filters", action="reset_global_filters",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _reset_global_filters(client, report_id)

        case "filter_fields_list":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_filters", action="filter_fields_list",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _filter_fields_list(client, report_id, component_idx)

        case "filter_field_add":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "value_field": value_field},
                tool="component_filters", action="filter_field_add",
                types={"report_id": "int", "component_idx": "int", "value_field": "str"},
            )
            if err:
                return err
            return await _filter_field_add(
                client, report_id, component_idx,
                value_field, alias, field_type, dataset_id,
                depends_on=depends_on,
            )

        case "filter_field_remove":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "value_field": value_field},
                tool="component_filters", action="filter_field_remove",
                types={"report_id": "int", "component_idx": "int", "value_field": "str"},
            )
            if err:
                return err
            return await _filter_field_remove(
                client, report_id, component_idx, value_field,
            )

        case "filter_set_cascade":
            check_action("update")
            err = require(
                {"report_id": report_id, "alias": alias},
                tool="component_filters", action="filter_set_cascade",
                types={
                    "report_id": "int",
                    "alias": "str (child filter alias; optional depends_on, reset_mode='min'|'max', reset_type='always')",
                },
                example="component_filters(action='filter_set_cascade', report_id=35, alias='Район', depends_on='Город', reset_mode='min')",
            )
            if err:
                return err
            return await _filter_set_cascade(
                client, report_id,
                filter_alias=alias,
                parent_alias=depends_on,
                reset_mode=reset_mode,
                reset_type=reset_type,
            )

        case "filters_grid_layout":
            check_action("update")
            # равномерно распределить N компонентов по cols×rows.
            # Параметры пробрасываются через kwargs (component_indices, cols,
            # rows, y_start, h). Раньше для grid filter-row пользователь
            # вычислял w вручную для каждого breakpoint.
            err = require(
                {"report_id": report_id, "config_overrides": config_overrides},
                tool="component_filters", action="filters_grid_layout",
                types={
                    "report_id": "int",
                    "config_overrides": "dict {component_indices:[int], cols:int, rows:int=1, y_start:int=0, h:int=3}",
                },
                example=(
                    "component_filters(action='filters_grid_layout', "
                    "report_id=752, config_overrides={"
                    "'component_indices':[14,15,16,17], 'cols':4, 'rows':1})"
                ),
            )
            if err:
                return err
            opts = config_overrides or {}
            indices = opts.get("component_indices") or []
            grid_cols = opts.get("cols")
            if not indices or not grid_cols:
                return {
                    "success": False,
                    "error": (
                        "config_overrides must contain 'component_indices' "
                        "(list[int]) and 'cols' (int >= 1)"
                    ),
                }
            return await _filters_grid_layout(
                client, report_id,
                component_indices=indices,
                cols=int(grid_cols),
                rows=int(opts.get("rows", 1)),
                y_start=int(opts.get("y_start", 0)),
                h=int(opts.get("h", 3)),
            )

        case "calc_fields_list":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="calc_fields_list",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _calc_fields_list(client, report_id, component_idx)

        case "calc_field_add":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "calc_expression": calc_expression},
                tool="component_axes", action="calc_field_add",
                types={"report_id": "int", "component_idx": "int", "calc_expression": "str"},
            )
            if err:
                return err
            # display_name = title (как в calc_field_update); fallback —
            # value_field (легаси-путь).
            return await _calc_field_add(
                client, report_id, component_idx, calc_expression,
                target_axis or "values", dataset_id,
                (title or None) or value_field,
            )

        case "calc_field_update":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "value_field": value_field},
                tool="component_axes", action="calc_field_update",
                types={"report_id": "int", "component_idx": "int", "value_field": "str"},
            )
            if err:
                return err
            return await _calc_field_update(
                client, report_id, component_idx, value_field,
                calc_expression, title,
            )

        case "calc_field_remove":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "value_field": value_field},
                tool="component_axes", action="calc_field_remove",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "value_field": "str — name (alias) of the calculated field to remove, "
                                   "as shown by calc_fields_list; NOT the SQL expression",
                },
                example="component_axes(action='calc_field_remove', report_id=35, component_idx=2, value_field='profit_margin')",
            )
            if err:
                return err
            return await _calc_field_remove(
                client, report_id, component_idx, value_field,
            )

        case "copy":
            check_action("create")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_crud", action="copy",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _copy_component(
                client, report_id, component_idx,
                target_report_id=target_report_id,
                new_title=title,
            )

        case "page_list":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="page_list",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _page_list(client, report_id, component_idx)

        case "page_add":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "title": title},
                tool="component_axes", action="page_add",
                types={"report_id": "int", "component_idx": "int", "title": "str"},
            )
            if err:
                return err
            return await _page_add(client, report_id, component_idx, title)

        case "page_remove":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "page_id": page_id},
                tool="component_axes", action="page_remove",
                types={"report_id": "int", "component_idx": "int", "page_id": "int"},
            )
            if err:
                return err
            return await _page_remove(client, report_id, component_idx, page_id)

        case "page_rename":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "page_id": page_id, "title": title},
                tool="component_axes", action="page_rename",
                types={"report_id": "int", "component_idx": "int", "page_id": "int", "title": "str"},
            )
            if err:
                return err
            return await _page_rename(client, report_id, component_idx, page_id, title)

        case "pivot_link_set":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "field_id": field_id,
                    "target_url": target_url,
                },
                tool="component_axes", action="pivot_link_set",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "field_id": "str (pivot field name or internal id)",
                    "target_url": "str (URL or /report/<id>; title + link_target are optional)",
                },
                example="component_axes(action='pivot_link_set', report_id=35, component_idx=0, field_id='region', target_url='/report/1', title='Details', link_target='_blank')",
            )
            if err:
                return err
            return await _pivot_link_set(
                client, report_id, component_idx,
                field_id, target_url, title, link_target,
            )

        case "pivot_link_remove":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "field_id": field_id},
                tool="component_axes", action="pivot_link_remove",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _pivot_link_remove(
                client, report_id, component_idx, field_id,
            )

        # --- Drill-down hierarchy management ---
        case "drill_get":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="drill_get",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _drill_get(client, report_id, component_idx)

        case "drill_add_level":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="drill_add_level",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _drill_add_level(client, report_id, component_idx)

        case "drill_delete_level":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="drill_delete_level",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _drill_delete_level(client, report_id, component_idx)

        case "drill_change_level":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "field_index": field_index,
                },
                tool="component_axes", action="drill_change_level",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "field_index": "int (drill level index; pass field_id=None to clear the level)",
                },
                example="component_axes(action='drill_change_level', report_id=35, component_idx=0, field_index=1, field_id='city')",
            )
            if err:
                return err
            return await _drill_change_level(
                client, report_id, component_idx, field_index, field_id,
            )

        case "drill_toggle_date_range":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="drill_toggle_date_range",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _drill_toggle_date_range(client, report_id, component_idx)

        case "drill_set_field":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "drill_category_id": drill_category_id,
                    "drill_direction": drill_direction,
                    "drill_selected": drill_selected,
                },
                tool="component_axes", action="drill_set_field",
                types={
                    "report_id": "int",
                    "component_idx": "int (table component only)",
                    "drill_category_id": "str (category id to drill from)",
                    "drill_direction": "str (drill direction identifier)",
                    "drill_selected": "str (selected value / target field)",
                },
                example="component_axes(action='drill_set_field', report_id=35, component_idx=0, drill_category_id='region', drill_direction='down', drill_selected='city')",
            )
            if err:
                return err
            return await _drill_set_field(
                client, report_id, component_idx,
                drill_category_id, drill_direction, drill_selected,
            )

        # --- Conditional formatting ---

        case "conditional_rule_add":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "config_overrides": config_overrides,
                },
                tool="component_styling", action="conditional_rule_add",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "config_overrides": "dict (rule: {field, operator, value, color, background, ...})",
                },
                example="component_styling(action='conditional_rule_add', report_id=35, component_idx=0, config_overrides={'field':'amount', 'operator':'>', 'value':1000, 'background':'#f44336'})",
            )
            if err:
                return err
            return await _conditional_rule_add(
                client, report_id, component_idx, config_overrides or {},
            )

        case "conditional_rule_list":
            check_action("get")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_styling", action="conditional_rule_list",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _conditional_rule_list(client, report_id, component_idx)

        case "conditional_rule_delete":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "field_index": field_index},
                tool="component_styling", action="conditional_rule_delete",
                types={"report_id": "int", "component_idx": "int", "field_index": "int"},
            )
            if err:
                return err
            return await _conditional_rule_delete(
                client, report_id, component_idx, field_index,
            )

        # --- Field sort ---

        case "field_sort_set":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "value_field": value_field,
                },
                tool="component_styling", action="field_sort_set",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "value_field": "str (field name; pass config_overrides={'order':'asc'|'desc'} or None to clear)",
                },
                example="component_styling(action='field_sort_set', report_id=35, component_idx=0, value_field='amount', config_overrides={'order':'desc'})",
            )
            if err:
                return err
            sort_order = (config_overrides or {}).get("order")
            # явный пустой/None — валидный clear; любое другое
            # невалидное значение — reject.
            if sort_order == "":
                sort_order = None
            if isinstance(sort_order, str):
                sort_order = sort_order.lower()
            if sort_order is not None and sort_order not in ("asc", "desc"):
                return {
                    "success": False,
                    "error": f"Invalid order {sort_order!r} for field_sort_set",
                    "hint": "asc | desc | пусто/None для сброса",
                }
            return await _field_sort_set(
                client, report_id, component_idx, value_field, sort_order,
            )

        # --- Geodata + Map geokeys ---

        case "geodata_list":
            check_action("get")
            return await _geodata_list(client)

        case "map_set_geokeys":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "config_overrides": config_overrides,
                },
                tool="component_styling", action="map_set_geokeys",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "config_overrides": "dict: {latfield, lonfield} bubble | {geo_type, geofield} choropleth | {geo_type, geofield, point_id_field, latfield, lonfield[, point_dataset_id]} MULTILAYER (полигоны+точки, isSheetOne)",
                },
                example="component_styling(action='map_set_geokeys', report_id=35, component_idx=0, config_overrides={'latfield':'lat', 'lonfield':'lon'})  # multilayer: добавь point_id_field+geo_type+geofield",
            )
            if err:
                return err
            return await _map_set_geokeys(
                client, report_id, component_idx, config_overrides or {},
            )

        case "map_get_geokeys":
            check_action("get")
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_styling", action="map_get_geokeys",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _map_get_geokeys(client, report_id, component_idx)

        # --- TabsPanel button management ---

        case "tabs_button_list":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="component_axes", action="tabs_button_list",
                types={"report_id": "int", "component_idx": "int"},
            )
            if err:
                return err
            return await _tabs_button_list(client, report_id, component_idx)

        case "tabs_button_add":
            check_action("update")
            err = require(
                {
                    "report_id": report_id,
                    "component_idx": component_idx,
                    "title": title,
                },
                tool="component_axes", action="tabs_button_add",
                types={
                    "report_id": "int",
                    "component_idx": "int",
                    "title": "str (button label)",
                },
                example="component_axes(action='tabs_button_add', report_id=35, component_idx=0, title='Home', config_overrides={'link':'/report/1', 'fill_color':'#1976d2', 'text_color':'#fff', 'link_target':'_blank'})",
            )
            if err:
                return err
            overrides = config_overrides or {}
            # top-level target_url/link_target поддержаны как fallback
            # к значениям из config_overrides
            return await _tabs_button_add(
                client, report_id, component_idx,
                label=title,
                link=overrides.get("link") or target_url,
                fill_color=overrides.get("fill_color"),
                text_color=overrides.get("text_color"),
                link_target=overrides.get("link_target") or link_target or "_self",
                font_size=overrides.get("font_size", 1.3),
            )

        case "tabs_button_delete":
            check_action("update")
            err = require(
                {"report_id": report_id, "component_idx": component_idx, "field_index": field_index},
                tool="component_axes", action="tabs_button_delete",
                types={"report_id": "int", "component_idx": "int", "field_index": "int"},
            )
            if err:
                return err
            return await _tabs_button_delete(
                client, report_id, component_idx, field_index,
            )

        case "list_slugs":
            # Префиксы slug_category (без расширения API surface):
            #   "search:color"    — поиск по подстроке
            #   "ui:" / "ui:legend" / "ui:search:color" — добавить UI-метаданные
            #     (ui_label/ui_section из config-панели). По умолчанию ВЫКЛ — экономит
            #     токены (+~74% к ответу); LLM включает при сборке/объяснении UI.
            search_term = None
            cat = slug_category
            include_ui = False
            if cat and cat.startswith("ui:"):
                include_ui = True
                cat = cat[len("ui:"):] or None
            if cat and cat.startswith("search:"):
                search_term = cat[len("search:"):]
                cat = None
            return _list_slugs(component_type, category=cat, search=search_term, include_ui=include_ui)

        case "list_presets":
            return _list_presets()

        case _:
            return {"error": f"Unknown action: {action}"}
