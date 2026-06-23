"""
Batch operations for MCP Server.

Actions:
- components_add: Add multiple components at once
- components_delete: Delete multiple components
- layouts_update: Update multiple layouts
- styles_apply: Apply CSS to multiple reports
- reports_export: Export multiple reports
"""

import logging

import base64
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.exceptions import error_response, mask_sensitive, require
from ..core.security import check_action
from ..core.validation import sanitize_html
from .builders import build_component_config, check_unsupported_params
# fetch_dataset_alias_map импортируется lazy внутри функции
# (избегаем circular import через component_filters → component_crud).
from .component_crud import _apply_visual_overrides, _builder_error_response
from .text_block_helper import apply_textblock_layout_workaround

logger = logging.getLogger(__name__)


# Export target: override via MODUSBI_EXPORT_DIR, else <tempdir>/modusbi_exports.
DEFAULT_EXPORT_DIR = Path(
    os.environ.get("MODUSBI_EXPORT_DIR") or Path(tempfile.gettempdir()) / "modusbi_exports"
)

# единый источник типов без датасета (HsTabsPanel/HsAudioplayer/...)
from .builders import NO_DATASET_TYPES as _NO_DATA_TYPES


async def _add_multiple_components(
    client,
    report_id: int,
    components: list[dict]
) -> dict[str, Any]:
    """Add multiple components to a report at once."""
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
    report_components = grid.get("components") or {}

    added = []
    errors = []
    batch_warnings = []

    for comp_config in components:
        try:
            # Get params
            component_type = comp_config.get("component_type")
            title = comp_config.get("title")
            value_field = comp_config.get("value_field")
            dataset_id = comp_config.get("dataset_id")
            category_field = comp_config.get("category_field", "")
            aggregation = comp_config.get("aggregation", "max")  # Safe default for pre-aggregated
            value_fields_type = comp_config.get("value_fields_type", "number")
            position = comp_config.get("position")
            # Additional params (field_titles, where_filter, text_content, etc.)
            field_titles = comp_config.get("field_titles")
            where_filter = comp_config.get("where_filter")
            text_content = sanitize_html(comp_config.get("text_content"))
            row_fields = comp_config.get("row_fields")
            column_fields = comp_config.get("column_fields")
            size_field = comp_config.get("size_field")
            # Visual params (applied locally)
            stacking = comp_config.get("stacking")
            orientation = comp_config.get("orientation")
            preset = comp_config.get("preset")
            legend_visible = comp_config.get("legend_visible")
            legend_position = comp_config.get("legend_position")
            labels_visible = comp_config.get("labels_visible")
            bg_color = comp_config.get("bg_color")
            config_overrides = comp_config.get("config_overrides")

            item_missing = [n for n, v in {"component_type": component_type, "title": title}.items() if not v]
            if item_missing:
                errors.append({
                    "config": comp_config,
                    "error": "Missing required parameters",
                    "missing": item_missing,
                    "expected_types": {"component_type": "str (e.g. 'HsBarAMchartsChart')", "title": "str"},
                    "hint": "Each component entry needs component_type and title.",
                })
                continue

            # value_field + dataset_id required for data components (not text/container/filter)
            if component_type not in _NO_DATA_TYPES:
                data_missing = [n for n, v in {"value_field": value_field, "dataset_id": dataset_id}.items() if not v]
                if data_missing:
                    errors.append({
                        "config": comp_config,
                        "error": "Missing required parameters",
                        "missing": data_missing,
                        "expected_types": {"value_field": "str (comma-separated field names)", "dataset_id": "int"},
                        "hint": "Data components (charts/tables/KPI) require value_field and dataset_id.",
                    })
                    continue

            # Parse value fields
            value_fields = [f.strip() for f in value_field.split(",") if f.strip()] if value_field else []

            # Auto-assemble position from atomic x/y/w/h
            if position is None:
                x_val = comp_config.get("x")
                y_val = comp_config.get("y")
                w_val = comp_config.get("w")
                h_val = comp_config.get("h")
                if any(v is not None for v in [x_val, y_val, w_val, h_val]):
                    position = {}
                    if x_val is not None: position["x"] = x_val
                    if y_val is not None: position["y"] = y_val
                    if w_val is not None: position["w"] = w_val
                    if h_val is not None: position["h"] = h_val

            # Component index
            existing_keys = [int(k) for k in report_components.keys() if k.isdigit()]
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

            # AUTO-FIX: Tables should always use aggregation="none"
            if "Table" in component_type and aggregation != "none":
                aggregation = "none"

            # warn о игнорируемых params
            unsupported = check_unsupported_params(
                component_type=component_type,
                column_fields=column_fields,
                series_field=comp_config.get("series_field"),
                category_field=category_field,
                value_field=value_field,
            )
            if unsupported:
                # warning ≠ провал: компонент добавляется, предупреждение
                # уходит в warnings[], errors[] — только реальные отказы
                batch_warnings.append(
                    {"component": comp_config.get("title"), "warnings": unsupported})

            # подтянуть alias-map из dataset (None если utility-тип)
            from .component_filters import fetch_dataset_alias_map  # lazy: circular
            field_alias_map = await fetch_dataset_alias_map(client, dataset_id)

            # Generate config
            agg_value = None if aggregation == "none" else aggregation
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
                series_field=comp_config.get("series_field"),
                field_alias_map=field_alias_map,
            )
            # неизвестный тип → в errors[], НЕ писать в grid
            builder_error = _builder_error_response(new_component)
            if builder_error:
                builder_error.pop("success", None)
                errors.append({"config": comp_config, **builder_error})
                continue

            # Apply visual params locally before PUT
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
                new_component["config"] = cfg
                if visual_warnings:
                    errors.append({"config": comp_config, "warnings": visual_warnings})

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
                    "zIndex": len(report_components) + 1,
                    "priority": -1
                }
                apply_textblock_layout_workaround(entry, component_type)
                layouts[bp].append(entry)

            report_components[component_idx] = new_component
            added.append({
                "idx": component_idx,
                "type": component_type,
                "title": title,
                "position": position
            })

        except Exception as e:
            errors.append({
                "index": len(added) + len(errors),
                "title": comp_config.get("title"),
                "component_type": comp_config.get("component_type"),
                "error": mask_sensitive(str(e)),
                "hint": "Check that value_field/dataset_id are valid and fields exist in the dataset.",
            })

    # Update grid
    grid["layouts"] = layouts
    grid["components"] = report_components
    report["grid"] = grid

    # Save
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error")}

    # Ничего не добавлено и есть ошибки → честный success:false,
    # а не success:true с пустым результатом.
    all_failed = not added and bool(errors)
    return {
        "success": not all_failed,
        "message": f"Added {len(added)} components",
        "report_id": report_id,
        "added": added,
        "warnings": batch_warnings if batch_warnings else None,
        "errors": errors if errors else None,
        **({"hint": "No components were added — inspect errors[] for each "
                     "config; component_crud(action='types_list') lists valid "
                     "component types."} if all_failed else {}),
    }


async def _delete_multiple_components(
    client,
    report_id: int,
    indices: list[int]
) -> dict[str, Any]:
    """Delete multiple components from report."""
    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    layouts = grid.get("layouts", {})
    components = grid.get("components", {})

    deleted = []
    not_found = []

    for idx in indices:
        component_key = str(idx)
        if component_key in components:
            del components[component_key]
            # Remove from all layouts
            for bp in layouts:
                layouts[bp] = [item for item in layouts[bp] if item.get("i") != component_key]
            deleted.append(idx)
        else:
            not_found.append(idx)

    grid["layouts"] = layouts
    grid["components"] = components
    report["grid"] = grid

    # Save report
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error")}

    # Ничего не удалено и есть промахи → честный success:false.
    return {
        "success": bool(deleted) or not not_found,
        "message": f"Deleted {len(deleted)} components",
        "report_id": report_id,
        "deleted": deleted,
        "not_found": not_found if not_found else None
    }


async def _update_multiple_layouts(
    client,
    report_id: int,
    layouts_updates: list[dict]
) -> dict[str, Any]:
    """Update layouts for multiple components."""
    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    grid = report.get("grid", {})
    layouts = grid.get("layouts", {})
    components = grid.get("components", {})

    updated = []
    not_found = []

    breakpoints = ["hd", "lg", "md", "sm", "xs", "xxs"]

    for layout_update in layouts_updates:
        component_idx = layout_update.get("component_idx")
        if component_idx is None:
            # Запись без component_idx — это промах (типовая ошибка: 'idx'
            # вместо 'component_idx'), а не «пропустить молча».
            not_found.append({"entry": layout_update, "reason": "no component_idx"})
            continue

        component_key = str(component_idx)
        if component_key not in components:
            not_found.append(component_idx)
            continue

        x = layout_update.get("x")
        y = layout_update.get("y")
        w = layout_update.get("w")
        h = layout_update.get("h")
        z_index = layout_update.get("z_index")

        for bp in breakpoints:
            if bp not in layouts:
                continue
            for item in layouts[bp]:
                if item.get("i") == component_key:
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
                    break

        updated.append(component_idx)

    grid["layouts"] = layouts
    report["grid"] = grid

    # Save report
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error")}

    # Ничего не обновлено и есть промахи → честный success:false.
    return {
        "success": bool(updated) or not not_found,
        "message": f"Updated {len(updated)} layouts",
        "report_id": report_id,
        "updated": updated,
        "not_found": not_found if not_found else None
    }


async def _apply_styles_to_reports(
    client,
    report_ids: list[int],
    css: str
) -> dict[str, Any]:
    """Apply CSS to multiple reports."""
    success = []
    errors = []

    for report_id in report_ids:
        try:
            # Get report
            get_response = await client.api_call("reports", "get", object_id=report_id)
            if get_response.get("status") != 200:
                errors.append({"report_id": report_id, "error": get_response.get("message", "Error")})
                continue

            data = get_response.get("data", [])
            if not data:
                errors.append({"report_id": report_id, "error": "Report not found"})
                continue

            report = data[0]
            if "options" not in report:
                report["options"] = {}
            report["options"]["CSStext"] = css

            # Update report
            update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])
            if update_response.get("status") != 200:
                errors.append({"report_id": report_id, "error": update_response.get("message", "Error")})
            else:
                success.append(report_id)

        except Exception as e:
            errors.append({
                "report_id": report_id,
                "error": mask_sensitive(str(e)),
                "hint": "Check that the report exists and CSS is syntactically valid.",
            })

    # Ни один отчёт не обновился, но есть ошибки → честный success:false.
    return {
        "success": bool(success) or not errors,
        "message": f"Applied CSS to {len(success)} reports",
        "success_reports": success,
        "errors": errors if errors else None
    }


async def _export_multiple_reports(
    client,
    report_ids: list[int],
    format: str = "pdf",
    output_dir: str | None = None
) -> dict[str, Any]:
    """Export multiple reports."""
    base_url = client.base_url
    export_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    export_dir.mkdir(parents=True, exist_ok=True)

    success = []
    errors = []

    for report_id in report_ids:
        try:
            report_url = f"{base_url}/report/{report_id}"
            if format == "pptx":
                report_url += "?export=pptx"

            request_data = [{
                "url": report_url,
                "output_type": format,
                "timeout": 120,
                "delay": 1000,
                "headless": True
            }]

            result = await client.api_call(
                object_name="exports",
                command_name="automated",
                data=request_data
            )

            if result.get("status") != 200:
                errors.append({"report_id": report_id, "error": result.get("message", "Error")})
                continue

            data = result.get("data", [{}])[0]
            if not data.get("success"):
                errors.append({"report_id": report_id, "error": data.get("message", "Export error")})
                continue

            # Save file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{report_id}_{timestamp}.{format}"
            file_path = export_dir / filename
            file_bytes = base64.b64decode(data.get("file_data", ""))
            file_path.write_bytes(file_bytes)

            success.append({
                "report_id": report_id,
                "saved_path": str(file_path),
                "file_size": data.get("file_size")
            })

        except Exception as e:
            errors.append({
                "report_id": report_id,
                "error": mask_sensitive(str(e)),
                "hint": "Report export requires the reports service to be reachable; verify report_id exists.",
            })

    # Ни один экспорт не удался, но есть ошибки → честный success:false.
    return {
        "success": bool(success) or not errors,
        "message": f"Exported {len(success)} reports",
        "exports": success,
        "errors": errors if errors else None
    }


async def batch_operations(
    client,
    action: str,
    report_id: int | None = None,
    report_ids: list[int] | None = None,
    components: list[dict] | None = None,
    layouts: list[dict] | None = None,
    indices: list[int] | None = None,
    css: str | None = None,
    format: str = "pdf",
    output_dir: str | None = None
) -> dict[str, Any]:
    """
    Batch operations for multiple objects.

    Actions:
    - components_add: Add multiple components at once
    - components_delete: Delete multiple components
    - layouts_update: Update multiple layouts
    - styles_apply: Apply CSS to multiple reports
    - reports_export: Export multiple reports
    """
    match action:
        case "components_add":
            check_action("components_add")
            err = require(
                {"report_id": report_id, "components": components},
                tool="batch_operations", action="components_add",
                types={"report_id": "int", "components": "list[dict] (each with component_type, title, value_field, dataset_id)"},
                example="batch_operations(action='components_add', report_id=35, components=[{'component_type':'HsBarAMchartsChart','title':'Sales','dataset_id':5,'value_field':'amount','category_field':'region','aggregation':'sum'}])",
            )
            if err:
                return err
            return await _add_multiple_components(client, report_id, components)

        case "components_delete":
            check_action("components_delete")
            err = require(
                {"report_id": report_id, "indices": indices},
                tool="batch_operations", action="components_delete",
                types={"report_id": "int", "indices": "list[int]"},
                example="batch_operations(action='components_delete', report_id=35, indices=[0, 2, 3])",
            )
            if err:
                return err
            return await _delete_multiple_components(client, report_id, indices)

        case "layouts_update":
            check_action("layouts_update")
            err = require(
                {"report_id": report_id, "layouts": layouts},
                tool="batch_operations", action="layouts_update",
                types={"report_id": "int", "layouts": "list[dict] (each {component_idx, x, y, w, h})"},
                example="batch_operations(action='layouts_update', report_id=35, layouts=[{'component_idx':0,'x':0,'y':0,'w':12,'h':8}])",
            )
            if err:
                return err
            return await _update_multiple_layouts(client, report_id, layouts)

        case "styles_apply":
            check_action("styles_apply")
            err = require(
                {"report_ids": report_ids, "css": css},
                tool="batch_operations", action="styles_apply",
                types={"report_ids": "list[int]", "css": "str (CSS text)"},
                example="batch_operations(action='styles_apply', report_ids=[35, 36], css='.hsGridPanel { border-radius: 8px; }')",
            )
            if err:
                return err
            return await _apply_styles_to_reports(client, report_ids, css)

        case "reports_export":
            check_action("reports_export")
            err = require(
                {"report_ids": report_ids},
                tool="batch_operations", action="reports_export",
                types={"report_ids": "list[int]"},
                example="batch_operations(action='reports_export', report_ids=[35, 36], format='pdf')",
            )
            if err:
                return err
            return await _export_multiple_reports(client, report_ids, format, output_dir)

        case _:
            return {"error": f"Unknown action: {action}"}
