"""
Data export operations for MCP Server.

Export component data to various formats:
- CSV: Local export, no dependencies
- Excel: Uses API reportToXlsx
"""

import logging

import csv
import io
import os
import base64
from pathlib import Path
from datetime import datetime
from typing import Any

from ..core.exceptions import require, mask_sensitive

logger = logging.getLogger(__name__)


def _get_default_export_dir() -> Path:
    """
    Determine default export directory with fallback chain:
    1. MODUSBI_EXPORT_DIR environment variable
    2. ~/Downloads/modusbi_exports (user-friendly)
    3. Current working directory + /exports
    """
    # Check environment variable
    env_dir = os.environ.get("MODUSBI_EXPORT_DIR")
    if env_dir:
        return Path(env_dir)

    # Try user's Downloads folder
    home = Path.home()
    downloads = home / "Downloads" / "modusbi_exports"
    if home.exists():
        return downloads

    # Fallback to cwd/exports
    return Path.cwd() / "exports"


async def export_component_to_csv(
    client,
    report_id: int,
    component_idx: int,
    output_dir: str | None = None,
    filename: str | None = None,
    limit: int = 10000,
    delimiter: str = ","
) -> dict[str, Any]:
    """
    Export component data to CSV file.

    This is a local export that doesn't require additional dependencies.
    Works by fetching component data and converting to CSV format.
    """
    # Get report
    result = await client.api_call("reports", "get", object_id=report_id)

    if result.get("status") != 200:
        return {"success": False, "error": f"Report not found: {result.get('message')}"}

    data = result.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        return {"success": False, "error": "Invalid report data format"}

    # Get components
    grid = data.get("grid", {})
    components = grid.get("components", {})
    report_name = data.get("name", f"report_{report_id}")

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

    # Find dataset_id
    dataset_id = cfg.get("datasetId") or cfg.get("dataSetId")

    if not dataset_id:
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                if field.get("datasetId"):
                    dataset_id = field["datasetId"]
                    break
            if dataset_id:
                break

    if not dataset_id:
        return {
            "success": False,
            "error": "Component not linked to dataset - cannot export data"
        }

    # Get data from recordset
    rs_result = await client.api_call("recordsets", "create", object_id=dataset_id, data=[{}])

    # Response can be:
    # 1. List of row-dicts directly (when using direct params) — the usual case
    # 2. Dict with {status, data} (when using wrapped params)
    # Same contract as dataset_query (see query_execute.py).
    if isinstance(rs_result, list):
        rows = rs_result
    elif isinstance(rs_result, dict):
        if rs_result.get("status") and rs_result.get("status") != 200:
            return {
                "success": False,
                "error": f"Error getting data: {rs_result.get('message', 'recordset request failed')}",
                "hint": "Check that the dataset's datasource is available: "
                        "datasource_operations(action='check_connection', datasource_id=X)"
            }
        rows = rs_result.get("data", [])
    else:
        rows = []

    if not rows:
        return {"success": False, "error": "No data returned from recordset"}

    if not isinstance(rows[0], dict):
        return {
            "success": False,
            "error": "Unexpected recordset row format (expected list of dicts)",
            "hint": "Use dataset_query to inspect the raw data for this dataset"
        }

    # Limit rows
    if limit and len(rows) > limit:
        rows = rows[:limit]
        was_limited = True
    else:
        was_limited = False

    # Build column headers from real row keys (rows are flat dicts {column: value})
    columns = list(rows[0].keys())

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter)

    # Write header
    writer.writerow(columns)

    # Write data rows (keep header order; missing keys → empty cell)
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])

    csv_content = output.getvalue()
    output.close()

    # Determine export directory
    export_dir = Path(output_dir) if output_dir else _get_default_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    if filename:
        final_filename = f"{filename}.csv"
    else:
        # Sanitize caption for filename
        safe_caption = "".join(c for c in caption if c.isalnum() or c in " _-").strip()
        if not safe_caption:
            safe_caption = f"component_{component_idx}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"{safe_caption}_{timestamp}.csv"

    file_path = export_dir / final_filename
    file_path.write_text(csv_content, encoding="utf-8-sig")  # BOM for Excel compatibility

    return {
        "success": True,
        "format": "csv",
        "saved_path": str(file_path),
        "export_dir": str(export_dir),
        "file_name": final_filename,
        "columns_count": len(columns),
        "rows_count": len(rows),
        "was_limited": was_limited,
        "limit": limit if was_limited else None,
        "component": {
            "idx": component_idx,
            "caption": caption,
            "dataset_id": dataset_id
        }
    }


def _build_xlsx_payload(report_id: int, export_request: dict) -> dict[str, Any]:
    """
    Build the CMD body for exports/reportToXlsx.

    Contract (api/CMD/exports/reportToXlsx.md):
      {object: {name: "exports", id: 4},
       command: {name: "reportToXlsx", id: <report_id>},
       export: {...}, data: [], options: []}

    command.id carries the call context (report/widget id); the actual
    report id for template lookup lives in export.report_id.
    """
    return {
        "object": {"name": "exports", "id": 4},
        "command": {"name": "reportToXlsx", "id": report_id},
        "export": export_request,
        "data": [],
        "options": []
    }


async def export_component_to_xlsx(
    client,
    report_id: int,
    component_idx: int,
    output_dir: str | None = None,
    filename: str | None = None,
    limit: int = 10000,
    include_subtotals: bool = False,
    include_totals: bool = False
) -> dict[str, Any]:
    """
    Export component data to Excel using API reportToXlsx.

    This uses the server-side export which provides:
    - Proper Excel formatting
    - Subtotals and totals (if enabled)
    - Excel template support
    """
    # Get report configuration first
    result = await client.api_call("reports", "get", object_id=report_id)

    if result.get("status") != 200:
        return {"success": False, "error": f"Report not found: {result.get('message')}"}

    data = result.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        return {"success": False, "error": "Invalid report data format"}

    # Get components
    grid = data.get("grid", {})
    components = grid.get("components", {})
    report_name = data.get("name", f"report_{report_id}")

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

    # Find dataset_id
    dataset_id = cfg.get("datasetId") or cfg.get("dataSetId")

    if not dataset_id:
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                if field.get("datasetId"):
                    dataset_id = field["datasetId"]
                    break
            if dataset_id:
                break

    if not dataset_id:
        return {
            "success": False,
            "error": "Component not linked to dataset - cannot export data"
        }

    # Build export request based on component config
    # Get axes and fields
    axes = cfg.get("axes", [])

    columns = []
    select = []
    group = []

    field_idx = 0
    for axis in axes:
        axis_name = axis.get("name", "")
        for field in axis.get("fields", []):
            field_name = field.get("name", "")
            field_alias = field.get("alias") or field.get("caption") or field_name
            field_id = field.get("id", f"field_{field_idx}")
            field_type = _determine_field_type(field)
            aggr = field.get("agg", "") or ""  # ModusBI stores as "agg", recordset API uses "aggr"

            alias_column = f"({field_idx}) {field_name}"

            # Column definition
            col = {
                "column": alias_column,
                "title": field_alias,
                "fieldName": field_name,
                "id": field_id,
                "fieldType": field_type
            }

            # For aggregation fields, add subtotal config
            if aggr and aggr.lower() in ("sum", "avg", "count", "min", "max"):
                col["subAgg"] = aggr.lower() if include_subtotals else None
                col["subAllAgg"] = aggr.lower() if include_totals else None

            columns.append(col)

            # Select definition
            sel = {
                "name": field_name,
                "calc": field.get("calc", ""),
                "aggr": aggr,
                "alias": alias_column,
                "id": field_id,
                "fieldAlias": field_alias,
                "lvl": 0,
                "valueType": "value",
                "export": {
                    "fieldType": field_type,
                    "subAgg": col.get("subAgg"),
                    "hidden": False
                }
            }
            select.append(sel)

            # If this is a dimension (category axis), add to group
            if axis_name in ("categories", "rows", "x") and not aggr:
                group.append({
                    "name": field_name,
                    "calc": "",
                    "alias": "[rows]",
                    "id": field_id,
                    "fieldAlias": field_alias
                })
                col["isSub"] = True

            field_idx += 1

    if not columns:
        return {"success": False, "error": "No fields found in component configuration"}

    # Build export request
    export_request = {
        "report_id": report_id,
        "container_id": 0,
        "columns": columns,
        "parameters": {
            "title": caption,
            "subMode": include_subtotals,
            "subAllMode": include_totals,
            "precision": 2,
            "partialDataWarning": True
        },
        "limit": limit,
        "dataset": {
            "dataset_id": dataset_id,
            "params": {
                "select": select,
                "group": group,
                "order": [],
                "where": [],
                "having": {"condition": ""},
                "series": {"enable": 0},
                "exportToExcel": 1
            }
        }
    }

    # Call exports/reportToXlsx.
    # Contract (api/CMD/exports/reportToXlsx.md) requires command.id and a
    # top-level "export" section — api_call() can't build either, so we
    # assemble the CMD body manually and send it via the low-level raw_post.
    # Token is fresh here: the reports/get api_call above already re-authed
    # on 401 if needed.
    payload = _build_xlsx_payload(report_id, export_request)
    api_url = client.instance.get_api_url("exports")

    response = await client.raw_post(
        api_url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {client.instance.token}"
        },
        timeout=120.0  # server-side rendering of large datasets can be slow
    )

    if response.status_code != 200:
        # Keep a snippet of the backend's error text — the static string
        # alone hides the actual reason (e.g. missing export template).
        body_snippet = mask_sensitive((response.text or "")[:200])
        return {
            "success": False,
            "error": f"Ошибка API: HTTP {response.status_code}",
            "details": body_snippet or "API reportToXlsx returned error",
            "hint": "Check that the report/dataset exist and the datasource is reachable"
        }

    api_result = response.json()

    if api_result.get("status") != 200:
        return {
            "success": False,
            "error": api_result.get("message", "Export failed"),
            "details": "API reportToXlsx returned error"
        }

    result_data = api_result.get("data", [])
    if not result_data:
        return {"success": False, "error": "No data returned from export"}

    export_result = result_data[0] if isinstance(result_data, list) else result_data

    # Decode and save file
    file_data = export_result.get("data", "")
    file_name = export_result.get("filename", "export.xlsx")

    if not file_data:
        return {"success": False, "error": "No file data in export response"}

    # Determine export directory
    export_dir = Path(output_dir) if output_dir else _get_default_export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename
    if filename:
        ext = ".zip" if file_name.endswith(".zip") else ".xlsx"
        final_filename = f"{filename}{ext}"
    else:
        final_filename = file_name

    file_path = export_dir / final_filename
    file_bytes = base64.b64decode(file_data)
    file_path.write_bytes(file_bytes)

    return {
        "success": True,
        "format": "xlsx" if file_name.endswith(".xlsx") else "zip",
        "saved_path": str(file_path),
        "export_dir": str(export_dir),
        "file_name": final_filename,
        "file_size": len(file_bytes),
        "component": {
            "idx": component_idx,
            "caption": caption,
            "dataset_id": dataset_id
        },
        "settings": {
            "subtotals": include_subtotals,
            "totals": include_totals,
            "limit": limit
        }
    }


def _determine_field_type(field: dict) -> str:
    """Determine field type for export."""
    field_type = field.get("type", "").lower()
    data_type = field.get("dataType", "").lower()

    if "date" in field_type or "date" in data_type:
        return "date"
    if "num" in field_type or "int" in field_type or "float" in field_type or "decimal" in data_type:
        return "number"
    if field.get("calc"):
        return "calculated"

    return "string"


async def export_operations(
    client,
    action: str,
    report_id: int | None = None,
    component_idx: int | None = None,
    output_dir: str | None = None,
    filename: str | None = None,
    limit: int = 10000,
    format: str = "csv",
    include_subtotals: bool = False,
    include_totals: bool = False
) -> dict[str, Any]:
    """
    Data export operations.

    Actions:
    - component_csv: Export component data to CSV
    - component_xlsx: Export component data to Excel (via API)
    - info: Get export directory configuration
    """
    match action:
        case "component_csv":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="data_export_operations", action="component_csv",
                types={"report_id": "int", "component_idx": "int"},
                example="data_export_operations(action='component_csv', report_id=35, component_idx=0, filename='sales.csv')",
            )
            if err:
                return err
            try:
                return await export_component_to_csv(
                    client, report_id, component_idx,
                    output_dir=output_dir,
                    filename=filename,
                    limit=limit
                )
            except Exception as e:
                # Don't leak raw tracebacks to the MCP client — error envelope
                logger.exception("component_csv export failed")
                return {
                    "success": False,
                    "error": "CSV export failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the report/component exist and the dataset's datasource is reachable"
                }

        case "component_xlsx":
            err = require(
                {"report_id": report_id, "component_idx": component_idx},
                tool="data_export_operations", action="component_xlsx",
                types={"report_id": "int", "component_idx": "int"},
                example="data_export_operations(action='component_xlsx', report_id=35, component_idx=0)",
            )
            if err:
                return err
            try:
                return await export_component_to_xlsx(
                    client, report_id, component_idx,
                    output_dir=output_dir,
                    filename=filename,
                    limit=limit,
                    include_subtotals=include_subtotals,
                    include_totals=include_totals
                )
            except Exception as e:
                # Don't leak raw tracebacks to the MCP client — error envelope
                logger.exception("component_xlsx export failed")
                return {
                    "success": False,
                    "error": "XLSX export failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the report/component exist and the dataset's datasource is reachable"
                }

        case "info":
            export_dir = _get_default_export_dir()
            return {
                "success": True,
                "default_export_dir": str(export_dir),
                "env_var_name": "MODUSBI_EXPORT_DIR",
                "env_var_value": os.environ.get("MODUSBI_EXPORT_DIR"),
                "supported_formats": ["csv", "xlsx"],
                "hint": "Set MODUSBI_EXPORT_DIR environment variable to customize export location"
            }

        case _:
            return {"error": f"Unknown action: {action}"}
