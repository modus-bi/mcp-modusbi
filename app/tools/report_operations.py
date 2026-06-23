"""
Report operations for MCP Server.

Actions:
- list: List reports (optional: group_id filter)
- get: Get full report info
- create: Create new report
- update: Update existing report
- delete: Delete report
- summary: Get report text summary
- components_list: List report components with positions
- groups_list: List report groups
- export: Export report to PDF/PNG/PPTX
- export_info: Get export configuration (directory, env var)
- get_options: Get report grid options
- update_options: Update report grid options
- clone: Clone report (copy grid, components, filters, variables, categories)
"""

import logging

import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from ..core.security import check_action
from ..core.exceptions import ValidationError, NotFoundError, mask_sensitive, missing_params, require

logger = logging.getLogger(__name__)


def _get_default_export_dir() -> Path:
    """
    Determine default export directory with fallback chain:
    1. MODUSBI_EXPORT_DIR environment variable
    2. ~/Downloads/modusbi_exports (user-friendly)
    3. Current working directory + /exports
    """
    # 1. Check environment variable
    env_dir = os.environ.get("MODUSBI_EXPORT_DIR")
    if env_dir:
        return Path(env_dir)

    # 2. Try user's Downloads folder
    home = Path.home()
    downloads = home / "Downloads" / "modusbi_exports"
    if home.exists():
        return downloads

    # 3. Fallback to current working directory
    return Path.cwd() / "exports"


async def _get_report_info(client, report_id: int) -> dict[str, Any]:
    """
    Internal function to get report metadata.

    Used by get, components_list, summary actions.
    """
    result = await client.api_call("reports", "get", object_id=report_id)

    if result.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    data = result.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        raise NotFoundError(f"Invalid data format for report {report_id}", object_id=report_id)

    # Extract components from grid
    grid = data.get("grid", {})
    raw_components = grid.get("components", {})

    components = []
    datasets = set()

    for idx, comp in raw_components.items():
        cfg = comp.get("config", {})

        # Component title (can be dict or string)
        caption_raw = cfg.get("caption__ru") or cfg.get("caption") or cfg.get("title")
        if isinstance(caption_raw, dict):
            caption = caption_raw.get("text") or caption_raw.get("ru") or str(caption_raw)
        elif caption_raw:
            caption = str(caption_raw)
        else:
            caption = f"Component {idx}"

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
        if dataset_id:
            datasets.add(dataset_id)

        # Fields
        fields = []
        for axis in cfg.get("axes", []):
            for field in axis.get("fields", []):
                field_info = {
                    "name": field.get("name"),
                    "alias": field.get("alias"),
                    "type": field.get("type"),
                    "dataset_id": field.get("datasetId")
                }
                fields.append(field_info)
                if field.get("datasetId"):
                    datasets.add(field["datasetId"])

        components.append({
            "idx": idx,
            "caption": caption,
            "type": comp_type,
            "dataset_id": dataset_id,
            "fields": fields
        })

    # Extract layouts for positioning
    layouts = grid.get("layouts", {})
    lg_layout = layouts.get("lg", [])

    # Add position to each component
    layout_map = {str(item.get("i")): item for item in lg_layout if isinstance(item, dict)}
    for comp in components:
        layout_item = layout_map.get(comp["idx"], {})
        comp["position"] = {
            "x": layout_item.get("x", 0),
            "y": layout_item.get("y", 0),
            "w": layout_item.get("w", 24),
            "h": layout_item.get("h", 14),
            "zIndex": layout_item.get("zIndex", 1)
        }

    # Sort components by position (y, x)
    components.sort(key=lambda c: (c["position"]["y"], c["position"]["x"]))

    return {
        "id": data.get("ID"),
        "name": data.get("name", "").rstrip("/"),
        "caption": data.get("caption", "").rstrip("/"),
        "group": data.get("groupName", "").rstrip("/"),
        "group_id": data.get("groupID"),
        "components_count": len(components),
        "components": components,
        "datasets": list(datasets),
        "global_filters": data.get("globalFilters", {}),
        "global_variables": data.get("globalVariables", {}),
        "global_categories": data.get("globalCategories", {})
    }


async def _list_reports(
    client,
    group_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List all reports with optional group filter (paginated)."""
    response = await client.api_call("reports", "list")

    if response.get("status") != 200:
        return {"error": response.get("message", "Unknown error")}

    data = response.get("data", [])

    # Filter by group if specified
    if group_id is not None:
        data = [r for r in data if r.get("groupID") == group_id]

    total = len(data)
    page = data[offset:offset + limit] if limit else data[offset:]

    items = [
        {
            "id": r.get("ID"),
            "name": r.get("name"),
            "caption": r.get("caption"),
            "group_id": r.get("groupID"),
            "group_name": r.get("groupName"),
            "deleted": r.get("deleted", 0) == 1
        }
        for r in page
    ]

    return {
        "success": True,
        "count": len(items),
        "total_count": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total,
        "filter": {"group_id": group_id} if group_id else None,
        "items": items,
    }


async def _list_groups(
    client,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List all report groups (paginated)."""
    response = await client.api_call("reportgroups", "list")

    if response.get("status") != 200:
        return {"error": response.get("message", "Unknown error")}

    data = response.get("data", [])
    total = len(data)
    page = data[offset:offset + limit] if limit else data[offset:]

    items = [
        {
            "id": g.get("ID"),
            "name": g.get("name"),
            "caption": g.get("caption"),
            "parent_id": g.get("parentID"),
            "menu": g.get("menu", 0) == 1
        }
        for g in page
    ]

    return {
        "success": True,
        "count": len(items),
        "total_count": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(items) < total,
        "items": items,
    }


async def _get_report(client, report_id: int) -> dict[str, Any]:
    """Get full report information."""
    info = await _get_report_info(client, report_id)
    return {"success": True, **info}


async def _get_summary(client, report_id: int) -> dict[str, Any]:
    """Get text summary of report."""
    info = await _get_report_info(client, report_id)

    # Build text summary
    summary_parts = [
        f"## Report: {info['caption']}",
        f"ID: {info['id']}, Group: {info['group']}",
        f"Components: {info['components_count']}",
        "",
        "### Components:"
    ]

    for comp in info["components"]:
        field_names = [f["alias"] or f["name"] for f in comp["fields"][:5]]
        fields_str = ", ".join(field_names) if field_names else "no fields"
        summary_parts.append(
            f"- **{comp['caption']}** ({comp['type']}): {fields_str}"
        )

    if info["global_filters"]:
        summary_parts.append("")
        summary_parts.append("### Global Filters:")
        for name in list(info["global_filters"].keys())[:5]:
            summary_parts.append(f"- {name}")

    return {
        "success": True,
        "summary": "\n".join(summary_parts),
        "data": info
    }


async def _list_components(client, report_id: int) -> dict[str, Any]:
    """List report components with positions."""
    info = await _get_report_info(client, report_id)

    return {
        "success": True,
        "report_id": info["id"],
        "report_name": info["caption"],
        "items": [
            {
                "idx": c["idx"],
                "caption": c["caption"],
                "type": c["type"],
                "position": c.get("position", {})
            }
            for c in info["components"]
        ]
    }


async def _create_report(
    client,
    name: str,
    caption: str,
    group_id: int,
    remark: str = "",
    parent_id: int = 0,
    description: str = "",
    ord: int = 0
) -> dict[str, Any]:
    """Create new report."""
    report_data = {
        "parentID": parent_id,
        "globalFilters": {},
        "grid": {
            "layouts": {},
            "components": {}
        },
        "options": {
            "name__ru": name,
            "caption__ru": caption,
            "remark__ru": f"<p>{remark}</p>" if remark else "",
            "description__ru": description,
            "allowOverlapMode": False,
            "recalculatedCellMode": True,
            "caption__en": "",
            "name__en": ""
        },
        "groupID": group_id,
        "caption": caption,
        "name": name,
        "ord": ord,
        "description": description
    }

    response = await client.api_call("reports", "create", data=[report_data])

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to create report")
        }

    data = response.get("data", [])

    # If API didn't return data, get ID via list_reports
    if not data:
        list_response = await client.api_call("reports", "list")
        if list_response.get("status") == 200:
            all_reports = list_response.get("data", [])
            matching = [
                r for r in all_reports
                if r.get("groupID") == group_id and r.get("name", "").rstrip("/") == name
            ]
            if matching:
                created = max(matching, key=lambda x: x.get("ID", 0))
                return {
                    "success": True,
                    "message": "Report created successfully",
                    "report": {
                        "id": created.get("ID"),
                        "name": created.get("name", "").rstrip("/"),
                        "caption": created.get("caption", "").rstrip("/"),
                        "group_id": created.get("groupID"),
                        "group_name": created.get("groupName", "").rstrip("/")
                    }
                }

        return {
            "success": False,
            "error": "Report created but could not retrieve its ID"
        }

    created = data[0]
    logger.info(
        "audit:report_create instance=%s report_id=%s name=%r group_id=%s",
        client.instance.name, created.get("ID"), name, group_id,
    )

    return {
        "success": True,
        "message": "Report created successfully",
        "report": {
            "id": created.get("ID"),
            "name": created.get("name", "").rstrip("/"),
            "caption": created.get("caption", "").rstrip("/"),
            "group_id": created.get("groupID"),
            "group_name": created.get("groupName", "").rstrip("/")
        }
    }


async def _update_report(
    client,
    report_id: int,
    name: str | None = None,
    caption: str | None = None,
    group_id: int | None = None,
    remark: str | None = None,
    description: str | None = None,
    ord: int | None = None,
    global_filters: dict | None = None
) -> dict[str, Any]:
    """Update existing report."""
    # First get current report data
    get_response = await client.api_call("reports", "get", object_id=report_id)

    if get_response.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    data = get_response.get("data", [])
    if not data:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    current = data[0]

    # Handle global_filters - merge with existing if provided
    current_filters = current.get("globalFilters", {})
    if global_filters is not None:
        # Merge: update existing filters with new ones
        current_filters.update(global_filters)

    # Build update data - only update provided fields
    update_data = {
        "ID": report_id,
        "name": name if name is not None else current.get("name"),
        "caption": caption if caption is not None else current.get("caption"),
        "report_group_id": group_id if group_id is not None else current.get("groupID"),
        "grid": current.get("grid", {}),
        "globalFilters": current_filters,
        "globalVariables": current.get("globalVariables", {}),
        "globalCategories": current.get("globalCategories", {}),
        "options": current.get("options", {})
    }

    # Update optional fields if provided
    if remark is not None:
        update_data["remark"] = remark
        if "options" in update_data:
            update_data["options"]["remark__ru"] = f"<p>{remark}</p>" if remark else ""

    if description is not None:
        update_data["description"] = description
        if "options" in update_data:
            update_data["options"]["description__ru"] = description

    if ord is not None:
        update_data["ord"] = ord

    response = await client.api_call("reports", "update", object_id=report_id, data=[update_data])

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to update report")
        }

    # Return updated info
    updated_data = response.get("data", [])
    if updated_data:
        updated = updated_data[0]
        return {
            "success": True,
            "message": f"Report {report_id} updated",
            "report": {
                "id": updated.get("ID"),
                "name": updated.get("name", "").rstrip("/"),
                "caption": updated.get("caption", "").rstrip("/"),
                "group_id": updated.get("groupID"),
                "group_name": updated.get("groupName", "").rstrip("/")
            }
        }

    return {
        "success": True,
        "message": f"Report {report_id} updated",
        "report_id": report_id
    }


async def _delete_report(client, report_id: int) -> dict[str, Any]:
    """Delete report."""
    response = await client.api_call("reports", "delete", object_id=report_id)

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to delete report")
        }

    return {
        "success": True,
        "message": f"Report {report_id} deleted",
        "report_id": report_id
    }


async def _clone_report(
    client,
    report_id: int,
    name: str | None = None,
    group_id: int | None = None,
) -> dict[str, Any]:
    """Clone a report: copy grid, components, filters, variables, categories."""
    source = await _get_report_raw(client, report_id)

    src_name = source.get("name", "Report")
    new_name = name or f"{src_name} (копия)"
    new_group = group_id or source.get("groupID", 1)

    # Step 1: Create empty report
    create_result = await _create_report(
        client,
        name=new_name,
        caption=new_name,
        group_id=new_group,
    )
    if not create_result.get("success"):
        return {"error": f"Failed to create report: {create_result.get('error', 'unknown')}"}

    new_id = create_result["report"]["id"]

    # Step 2: Copy grid (components + layouts), filters, variables, categories, options
    src_options = dict(source.get("options", {}))
    src_options["name__ru"] = new_name
    src_options["caption__ru"] = new_name

    update_data = {
        "ID": new_id,
        "name": new_name,
        "caption": new_name,
        "report_group_id": new_group,
        "grid": source.get("grid", {}),
        "globalFilters": source.get("globalFilters", {}),
        "globalVariables": source.get("globalVariables", {}),
        "globalCategories": source.get("globalCategories", {}),
        "options": src_options,
    }

    response = await client.api_call("reports", "update", object_id=new_id, data=[update_data])
    if response.get("status") != 200:
        return {"error": f"Report created (ID={new_id}) but failed to copy content"}

    # Count components
    components = source.get("grid", {}).get("components", {})
    comp_count = len(components)

    return {
        "success": True,
        "message": f"Report cloned: {src_name} → {new_name}",
        "source_report_id": report_id,
        "new_report": {
            "id": new_id,
            "name": new_name,
            "group_id": new_group,
            "components_count": comp_count,
        }
    }


async def _save_global_filters(
    client, report_id: int, current: dict, filters: dict
) -> dict[str, Any]:
    """Persist globalFilters back to report via update API (full replace)."""
    update_data = {
        "ID": report_id,
        "name": current.get("name"),
        "caption": current.get("caption"),
        "report_group_id": current.get("groupID"),
        "grid": current.get("grid", {}),
        "globalFilters": filters,
        "globalVariables": current.get("globalVariables", {}),
        "globalCategories": current.get("globalCategories", {}),
        "options": current.get("options", {}),
    }
    response = await client.api_call(
        "reports", "update", object_id=report_id, data=[update_data]
    )
    if response.get("status") != 200:
        return {"error": response.get("message", "Failed to update report")}
    return {"success": True}


async def _list_global_filters(client, report_id: int) -> dict[str, Any]:
    """List all globalFilters for a report."""
    current = await _get_report_raw(client, report_id)
    filters = current.get("globalFilters", {})

    items = [
        {"name": name, **{k: v for k, v in f.items()}}
        for name, f in filters.items()
    ]

    return {
        "success": True,
        "report_id": report_id,
        "count": len(items),
        "items": items,
    }


async def _delete_global_filter(
    client, report_id: int, name: str
) -> dict[str, Any]:
    """Delete a global filter by name. Error if not exists."""
    current = await _get_report_raw(client, report_id)
    filters = current.get("globalFilters", {})

    if name not in filters:
        return {"error": f"Global filter '{name}' not found", "available": list(filters.keys())}

    del filters[name]
    result = await _save_global_filters(client, report_id, current, filters)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Global filter '{name}' deleted",
        "report_id": report_id,
        "remaining": list(filters.keys()),
    }


async def _get_report_raw(client, report_id: int) -> dict[str, Any]:
    """Fetch raw report data from API. Raises NotFoundError if missing."""
    response = await client.api_call("reports", "get", object_id=report_id)
    if response.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)
    data = response.get("data", [])
    if not data:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)
    return data[0]


async def _save_variables(
    client, report_id: int, current: dict, variables: dict
) -> dict[str, Any]:
    """Persist globalVariables back to report via update API."""
    update_data = {
        "ID": report_id,
        "name": current.get("name"),
        "caption": current.get("caption"),
        "report_group_id": current.get("groupID"),
        "grid": current.get("grid", {}),
        "globalFilters": current.get("globalFilters", {}),
        "globalVariables": variables,
        "globalCategories": current.get("globalCategories", {}),
        "options": current.get("options", {}),
    }
    response = await client.api_call(
        "reports", "update", object_id=report_id, data=[update_data]
    )
    if response.get("status") != 200:
        return {"error": response.get("message", "Failed to update report")}
    return {"success": True}


async def _list_variables(client, report_id: int) -> dict[str, Any]:
    """List all globalVariables for a report."""
    current = await _get_report_raw(client, report_id)
    variables = current.get("globalVariables", {})

    items = [
        {"name": name, "value": var.get("value", [])}
        for name, var in variables.items()
    ]

    return {
        "success": True,
        "report_id": report_id,
        "count": len(items),
        "items": items,
    }


async def _add_variable(
    client, report_id: int, name: str, value: list[str]
) -> dict[str, Any]:
    """Add a new variable. Error if already exists."""
    current = await _get_report_raw(client, report_id)
    variables = current.get("globalVariables", {})

    if name in variables:
        return {"error": f"Variable '{name}' already exists. Use variable_update to change it."}

    variables[name] = {"value": value}
    result = await _save_variables(client, report_id, current, variables)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Variable '{name}' added",
        "report_id": report_id,
        "variable": {"name": name, "value": value},
    }


async def _update_variable(
    client, report_id: int, name: str, value: list[str]
) -> dict[str, Any]:
    """Update existing variable value. Error if not exists."""
    current = await _get_report_raw(client, report_id)
    variables = current.get("globalVariables", {})

    if name not in variables:
        return {"error": f"Variable '{name}' not found. Use variable_add to create it."}

    variables[name]["value"] = value
    result = await _save_variables(client, report_id, current, variables)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Variable '{name}' updated",
        "report_id": report_id,
        "variable": {"name": name, "value": value},
    }


async def _delete_variable(
    client, report_id: int, name: str
) -> dict[str, Any]:
    """Delete a variable. Error if not exists."""
    current = await _get_report_raw(client, report_id)
    variables = current.get("globalVariables", {})

    if name not in variables:
        return {"error": f"Variable '{name}' not found"}

    del variables[name]
    result = await _save_variables(client, report_id, current, variables)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Variable '{name}' deleted",
        "report_id": report_id,
    }


async def _save_categories(
    client, report_id: int, current: dict, categories: dict
) -> dict[str, Any]:
    """Persist globalCategories back to report via update API."""
    update_data = {
        "ID": report_id,
        "name": current.get("name"),
        "caption": current.get("caption"),
        "report_group_id": current.get("groupID"),
        "grid": current.get("grid", {}),
        "globalFilters": current.get("globalFilters", {}),
        "globalVariables": current.get("globalVariables", {}),
        "globalCategories": categories,
        "options": current.get("options", {}),
    }
    response = await client.api_call(
        "reports", "update", object_id=report_id, data=[update_data]
    )
    if response.get("status") != 200:
        return {"error": response.get("message", "Failed to update report")}
    return {"success": True}


async def _list_categories(client, report_id: int) -> dict[str, Any]:
    """List all globalCategories for a report."""
    current = await _get_report_raw(client, report_id)
    categories = current.get("globalCategories", {})

    items = [
        {
            "name": name,
            "selected": cat.get("selected", ""),
            "enabled": cat.get("enabled", False),
            "options": cat.get("options", []),
        }
        for name, cat in categories.items()
    ]

    return {
        "success": True,
        "report_id": report_id,
        "count": len(items),
        "items": items,
    }


async def _add_category(
    client,
    report_id: int,
    name: str,
    selected: str,
    options: list[str],
) -> dict[str, Any]:
    """Add a new category. Error if already exists."""
    current = await _get_report_raw(client, report_id)
    categories = current.get("globalCategories", {})

    if name in categories:
        return {"error": f"Category '{name}' already exists. Use category_update to change it."}

    categories[name] = {
        "selected": selected,
        "enabled": True,
        "options": options,
    }
    result = await _save_categories(client, report_id, current, categories)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Category '{name}' added",
        "report_id": report_id,
        "category": {"name": name, "selected": selected, "enabled": True, "options": options},
    }


async def _update_category(
    client,
    report_id: int,
    name: str,
    selected: str | None = None,
    options: list[str] | None = None,
) -> dict[str, Any]:
    """Update existing category. Error if not exists."""
    current = await _get_report_raw(client, report_id)
    categories = current.get("globalCategories", {})

    if name not in categories:
        return {"error": f"Category '{name}' not found. Use category_add to create it."}

    if selected is not None:
        categories[name]["selected"] = selected
    if options is not None:
        categories[name]["options"] = options

    result = await _save_categories(client, report_id, current, categories)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Category '{name}' updated",
        "report_id": report_id,
        "category": {
            "name": name,
            "selected": categories[name].get("selected", ""),
            "enabled": categories[name].get("enabled", False),
            "options": categories[name].get("options", []),
        },
    }


async def _delete_category(
    client, report_id: int, name: str
) -> dict[str, Any]:
    """Delete a category. Error if not exists."""
    current = await _get_report_raw(client, report_id)
    categories = current.get("globalCategories", {})

    if name not in categories:
        return {"error": f"Category '{name}' not found"}

    del categories[name]
    result = await _save_categories(client, report_id, current, categories)
    if "error" in result:
        return result

    return {
        "success": True,
        "message": f"Category '{name}' deleted",
        "report_id": report_id,
    }


async def _get_options(client, report_id: int) -> dict[str, Any]:
    """Get report grid options (cellMode, allowOverlapMode, freePaneMovement, etc.)."""
    current = await _get_report_raw(client, report_id)
    options = current.get("options", {})
    return {
        "success": True,
        "report_id": report_id,
        "options": {
            "cell_mode": options.get("cellMode"),
            "allow_overlap_mode": options.get("allowOverlapMode"),
            "free_pane_movement": options.get("freePaneMovement"),
            "no_gap_mode": options.get("noGapMode"),
            "recalculated_cell_mode": options.get("recalculatedCellMode"),
            "grouping_mode": options.get("groupingMode"),
        }
    }


async def _update_options(
    client,
    report_id: int,
    cell_mode: str | None = None,
    allow_overlap_mode: bool | None = None,
    free_pane_movement: bool | None = None,
    no_gap_mode: bool | None = None,
    recalculated_cell_mode: bool | None = None,
    grouping_mode: bool | None = None,
) -> dict[str, Any]:
    """Update report grid options. Only non-None params are updated."""
    valid_cell_modes = ("compact", "standard", "large")
    if cell_mode is not None and cell_mode not in valid_cell_modes:
        return {"error": f"cell_mode must be one of {valid_cell_modes}, got '{cell_mode}'"}

    current = await _get_report_raw(client, report_id)

    # Merge non-None into options (preserve existing CSStext, etc.)
    options = current.get("options", {})
    mapping = {
        "cellMode": cell_mode,
        "allowOverlapMode": allow_overlap_mode,
        "freePaneMovement": free_pane_movement,
        "noGapMode": no_gap_mode,
        "recalculatedCellMode": recalculated_cell_mode,
        "groupingMode": grouping_mode,
    }
    for key, val in mapping.items():
        if val is not None:
            options[key] = val

    # Update full report (preserve grid, globalFilters, globalVariables, globalCategories)
    update_data = {
        "ID": report_id,
        "name": current.get("name"),
        "caption": current.get("caption"),
        "report_group_id": current.get("groupID"),
        "grid": current.get("grid", {}),
        "globalFilters": current.get("globalFilters", {}),
        "globalVariables": current.get("globalVariables", {}),
        "globalCategories": current.get("globalCategories", {}),
        "options": options,
    }
    response = await client.api_call(
        "reports", "update", object_id=report_id, data=[update_data]
    )
    if response.get("status") != 200:
        return {"error": response.get("message", "Failed to update report options")}

    return {
        "success": True,
        "report_id": report_id,
        "updated_options": {k: v for k, v in mapping.items() if v is not None},
    }


def _get_export_info() -> dict[str, Any]:
    """Get current export configuration."""
    export_dir = _get_default_export_dir()
    env_var = os.environ.get("MODUSBI_EXPORT_DIR")

    return {
        "success": True,
        "export_dir": str(export_dir),
        "source": "env" if env_var else ("downloads" if "Downloads" in str(export_dir) else "cwd"),
        "env_var_set": bool(env_var),
        "env_var_name": "MODUSBI_EXPORT_DIR",
        "hint": "Set MODUSBI_EXPORT_DIR environment variable to customize export location"
    }


async def _export_report(
    client,
    report_id: int,
    output_type: str = "pdf",
    page_size: str = "A4",
    page_orientation: str = "portrait",
    save_to_disk: bool = True,
    output_dir: str | None = None,
    filename: str | None = None,
    timeout: int = 120
) -> dict[str, Any]:
    """
    Export report to PDF/PNG/SVG/PPTX.

    Save location priority:
    1. output_dir parameter (if specified)
    2. MODUSBI_EXPORT_DIR environment variable
    3. ~/Downloads/modusbi_exports
    4. ./exports (current working directory)
    """
    try:
        base_url = client.base_url
        report_url = f"{base_url}/report/{report_id}"
        if output_type == "pptx":
            report_url += "?export=pptx"

        request_data = [{
            "url": report_url,
            "output_type": output_type,
            "timeout": timeout,
            "delay": 1000,
            "headless": True
        }]

        if output_type == "pdf":
            request_data[0]["page_size"] = page_size
            request_data[0]["page_orientation"] = page_orientation

        result = await client.api_call(
            object_name="exports",
            command_name="automated",
            data=request_data
        )

        if result.get("status") != 200:
            return {
                "success": False,
                "error": result.get("message", "Unknown error"),
                "report_id": report_id
            }

        data = result.get("data", [{}])[0]

        if not data.get("success"):
            return {
                "success": False,
                "error": data.get("message", "Export generation error"),
                "report_id": report_id
            }

        response = {
            "success": True,
            "report_id": report_id,
            "output_type": output_type,
            "file_name": data.get("file_name"),
            "mime_type": data.get("mime_type"),
            "file_size": data.get("file_size"),
            "elapsed": data.get("elapsed")
        }

        if save_to_disk or output_dir:
            export_dir = Path(output_dir) if output_dir else _get_default_export_dir()
            export_dir.mkdir(parents=True, exist_ok=True)

            if filename:
                final_filename = f"{filename}.{output_type}"
            elif data.get("file_name"):
                final_filename = data.get("file_name")
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_filename = f"report_{report_id}_{timestamp}.{output_type}"

            file_path = export_dir / final_filename
            file_bytes = base64.b64decode(data.get("file_data", ""))
            file_path.write_bytes(file_bytes)
            response["saved_path"] = str(file_path)
            response["export_dir"] = str(export_dir)

        return response

    except Exception as e:
        return {
            "success": False,
            "error": "Report export failed",
            "details": mask_sensitive(str(e)),
            "hint": "Check that report_id exists and output_type is supported (pdf/pptx).",
            "report_id": report_id,
        }


async def report_operations(
    client,
    action: str,
    report_id: int | None = None,
    name: str | None = None,
    caption: str | None = None,
    group_id: int | None = None,
    remark: str | None = None,
    parent_id: int = 0,
    description: str = "",
    ord: int = 0,
    format: str = "pdf",
    page_size: str = "A4",
    page_orientation: str = "portrait",
    output_dir: str | None = None,
    filename: str | None = None,
    timeout: int = 120,
    global_filters: dict | None = None,
    variable_name: str | None = None,
    variable_value: str | list[str] | None = None,
    category_name: str | None = None,
    category_selected: str | None = None,
    category_options: list[str] | None = None,
    cell_mode: str | None = None,
    allow_overlap_mode: bool | None = None,
    free_pane_movement: bool | None = None,
    no_gap_mode: bool | None = None,
    recalculated_cell_mode: bool | None = None,
    grouping_mode: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    CRUD operations for reports.

    Actions:
    - list: List reports (optional: group_id)
    - get: Get report by ID
    - create: Create report (name, caption, group_id required; parent_id, description, ord, remark optional)
    - update: Update report (report_id required; name, caption, group_id, remark, description, ord optional)
    - delete: Delete report (report_id)
    - summary: Get report text summary
    - components_list: List report components
    - groups_list: List report groups
    - export: Export report (format: pdf/png/pptx)
    - export_info: Get export directory configuration
    - variables_list: List globalVariables (report_id required)
    - variable_add: Add variable (report_id, variable_name, variable_value required)
    - variable_update: Update variable value (report_id, variable_name, variable_value required)
    - variable_delete: Delete variable (report_id, variable_name required)
    - categories_list: List globalCategories (report_id required)
    - category_add: Add category (report_id, category_name, category_selected, category_options required)
    - category_update: Update category (report_id, category_name required; category_selected, category_options optional)
    - category_delete: Delete category (report_id, category_name required)
    - get_options: Get report grid options (report_id required)
    - update_options: Update report grid options (report_id required; cell_mode, allow_overlap_mode, etc.)
    - clone: Clone report with all components/filters/variables (report_id required; name, group_id optional)
    - global_filters_list: List all globalFilters (report_id required)
    - global_filter_delete: Delete a global filter by name (report_id, variable_name required)
    """
    match action:
        case "list":
            return await _list_reports(client, group_id, limit=limit, offset=offset)

        case "groups_list":
            return await _list_groups(client, limit=limit, offset=offset)

        case "get":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="get",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _get_report(client, report_id)

        case "summary":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="summary",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _get_summary(client, report_id)

        case "components_list":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="components_list",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _list_components(client, report_id)

        case "create":
            check_action("create")
            err = require(
                {"name": name, "caption": caption, "group_id": group_id},
                tool="report_operations", action="create",
                types={"name": "str", "caption": "str", "group_id": "int"},
            )
            if err:
                return err
            return await _create_report(
                client, name, caption, group_id,
                remark=remark or "",
                parent_id=parent_id,
                description=description,
                ord=ord
            )

        case "update":
            check_action("update")
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="update",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _update_report(
                client, report_id,
                name=name, caption=caption, group_id=group_id,
                remark=remark, description=description, ord=ord,
                global_filters=global_filters
            )

        case "delete":
            check_action("delete")
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="delete",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _delete_report(client, report_id)

        case "export":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="export",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _export_report(
                client,
                report_id,
                output_type=format,
                page_size=page_size,
                page_orientation=page_orientation,
                output_dir=output_dir,
                filename=filename,
                timeout=timeout
            )

        case "export_info":
            return _get_export_info()

        case "variables_list":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="variables_list",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _list_variables(client, report_id)

        case "variable_add":
            check_action("update")
            err = require(
                {"report_id": report_id, "variable_name": variable_name, "variable_value": variable_value},
                tool="report_operations", action="variable_add",
                types={"report_id": "int", "variable_name": "str", "variable_value": "str | list[str]"},
            )
            if err:
                return err
            val = [variable_value] if isinstance(variable_value, str) else variable_value
            return await _add_variable(client, report_id, variable_name, val)

        case "variable_update":
            check_action("update")
            err = require(
                {"report_id": report_id, "variable_name": variable_name, "variable_value": variable_value},
                tool="report_operations", action="variable_update",
                types={"report_id": "int", "variable_name": "str", "variable_value": "str | list[str]"},
            )
            if err:
                return err
            val = [variable_value] if isinstance(variable_value, str) else variable_value
            return await _update_variable(client, report_id, variable_name, val)

        case "variable_delete":
            check_action("update")
            err = require(
                {"report_id": report_id, "variable_name": variable_name},
                tool="report_operations", action="variable_delete",
                types={"report_id": "int", "variable_name": "str"},
            )
            if err:
                return err
            return await _delete_variable(client, report_id, variable_name)

        case "categories_list":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="categories_list",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _list_categories(client, report_id)

        case "category_add":
            check_action("update")
            err = require(
                {"report_id": report_id, "category_name": category_name, "category_selected": category_selected, "category_options": category_options},
                tool="report_operations", action="category_add",
                types={"report_id": "int", "category_name": "str", "category_selected": "str", "category_options": "list[str]"},
            )
            if err:
                return err
            return await _add_category(
                client, report_id, category_name, category_selected, category_options
            )

        case "category_update":
            check_action("update")
            err = require(
                {"report_id": report_id, "category_name": category_name},
                tool="report_operations", action="category_update",
                types={"report_id": "int", "category_name": "str"},
            )
            if err:
                return err
            return await _update_category(
                client, report_id, category_name,
                selected=category_selected,
                options=category_options,
            )

        case "category_delete":
            check_action("update")
            err = require(
                {"report_id": report_id, "category_name": category_name},
                tool="report_operations", action="category_delete",
                types={"report_id": "int", "category_name": "str"},
            )
            if err:
                return err
            return await _delete_category(client, report_id, category_name)

        case "get_options":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="get_options",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _get_options(client, report_id)

        case "update_options":
            check_action("update")
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="update_options",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _update_options(
                client, report_id,
                cell_mode=cell_mode,
                allow_overlap_mode=allow_overlap_mode,
                free_pane_movement=free_pane_movement,
                no_gap_mode=no_gap_mode,
                recalculated_cell_mode=recalculated_cell_mode,
                grouping_mode=grouping_mode,
            )

        case "clone":
            check_action("create")
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="clone",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _clone_report(client, report_id, name=name, group_id=group_id)

        case "global_filters_list":
            err = require(
                {"report_id": report_id},
                tool="report_operations", action="global_filters_list",
                types={"report_id": "int"},
            )
            if err:
                return err
            return await _list_global_filters(client, report_id)

        case "global_filter_delete":
            check_action("update")
            err = require(
                {"report_id": report_id, "variable_name": variable_name},
                tool="report_operations", action="global_filter_delete",
                types={"report_id": "int", "variable_name": "str (filter alias to delete)"},
            )
            if err:
                return err
            return await _delete_global_filter(client, report_id, variable_name)

        case _:
            return {"error": f"Unknown action: {action}"}
