"""
Component axes operations: calculated fields + page management + pivot links + drill-down + tabs buttons + shared helpers.

Split from component_operations.py for maintainability.
Functions:
- _fetch_report_component, _sync_axes_default, _save_report (shared helpers)
- _build_calc_field, _find_field_in_axes
- _calc_fields_list, _calc_field_add, _calc_field_update, _calc_field_remove
- _page_list, _page_add, _page_remove, _page_rename
- _pivot_link_set, _pivot_link_remove
- _drill_get, _drill_add_level, _drill_delete_level, _drill_change_level
- _drill_toggle_date_range, _drill_set_field
- _tabs_button_list, _tabs_button_add, _tabs_button_delete
"""

import logging

from typing import Any

from ..core.exceptions import NotFoundError, ValidationError
from .builders import generate_uid

logger = logging.getLogger(__name__)


async def _fetch_report_component(
    client,
    report_id: int,
    component_idx: int,
) -> tuple[dict, dict, dict, str]:
    """Fetch report and extract component. Returns (report, comp, cfg, key).

    Raises NotFoundError if report missing, returns error dict as comp if
    component not found (caller must check).
    """
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    data = get_response.get("data", [])
    if not data:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)

    report = data[0]
    component_key = str(component_idx)
    comp = report.get("grid", {}).get("components", {}).get(component_key)
    if comp is None:
        raise ValidationError(
            f"Component {component_idx} not found",
            details={"component_idx": component_idx},
        )
    cfg = comp.get("config", {})
    return report, comp, cfg, component_key


def _sync_axes_default(cfg: dict) -> None:
    """Sync axesDefault from axes (common post-mutation step)."""
    axes = cfg.get("axes", [])
    cfg["axesDefault"] = [
        {**ax, "fields": list(ax.get("fields", []))} for ax in axes
    ]


async def _save_report(client, report_id: int, report: dict) -> dict | None:
    """PUT report back. Returns error dict on failure, None on success."""
    resp = await client.api_call(
        "reports", "update", object_id=report_id, data=[report]
    )
    if resp.get("status") != 200:
        return {"success": False, "error": resp.get("message", "Error saving report")}
    return None


# -------------------------------------------------------------------------
# Calculated fields management
# -------------------------------------------------------------------------

async def _calc_fields_list(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """List all calculated fields in any axis of a component."""
    _report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    calc_fields: list[dict[str, Any]] = []
    for axis in cfg.get("axes", []):
        axis_type = axis.get("type", "")
        for field in axis.get("fields", []):
            if field.get("type") == "calculated":
                calc_fields.append({
                    "name": field.get("name"),
                    "sql_expression": field.get("calc") or field.get("alias", ""),
                    "axis_type": axis_type,
                    "dataset_id": field.get("datasetId"),
                    "display_name": field.get("title__ru", ""),
                })

    return {
        "success": True,
        "report_id": report_id,
        "component_idx": component_idx,
        "component_type": comp.get("type", ""),
        "items": calc_fields,
        "count": len(calc_fields),
    }


def _build_calc_field(
    calc_expression: str,
    dataset_id: int | None,
    display_name: str | None,
) -> dict[str, Any]:
    """Build a calculated field dict with proper name format."""
    uid = generate_uid()
    return {
        "name": f"{{Вычисляемое поле}}_{uid}_name",
        "alias": calc_expression,
        "type": "calculated",
        "agg": None,
        "datasetId": dataset_id,
        "id": generate_uid(),
        "bk": 0,
        "calc": calc_expression,
        "correctable": 0,
        "draft": True,
        "expression": [],
        "filterSqlType": None,
        "inactive": None,
        "order": None,
        "orderIndex": None,
        "prop": {},
        "title": "",
        "title__ru": display_name or "",
        "units": None,
        "valueType": "value",
    }


async def _calc_field_add(
    client,
    report_id: int,
    component_idx: int,
    calc_expression: str,
    target_axis: str = "values",
    dataset_id: int | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Add a calculated field to a component axis."""
    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )
    axes = cfg.get("axes", [])

    resolved_ds = dataset_id or cfg.get("datasetId") or cfg.get("dataSetId") or next(
        (f.get("datasetId") for a in axes for f in a.get("fields", []) if f.get("datasetId")), None
    )
    field = _build_calc_field(calc_expression, resolved_ds, display_name)

    # Find or create target axis
    target = next((a for a in axes if a.get("type") == target_axis), None)
    if target is None:
        target = {"type": target_axis, "fields": []}
        axes.append(target)
        cfg["axes"] = axes

    target.setdefault("fields", []).append(field)
    _sync_axes_default(cfg)

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Calculated field added to component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "field_name": field["name"],
        "axis": target_axis,
        "sql_expression": calc_expression,
    }


def _find_field_in_axes(axes: list[dict], field_name: str) -> tuple[dict | None, str]:
    """Find a field by name across all axes. Returns (field, axis_type)."""
    for axis in axes:
        for field in axis.get("fields", []):
            if field.get("name") == field_name:
                return field, axis.get("type", "")
    return None, ""


async def _calc_field_update(
    client,
    report_id: int,
    component_idx: int,
    field_name: str,
    calc_expression: str | None = None,
    display_name: str | None = None,
) -> dict[str, Any]:
    """Update SQL expression or display name of a calculated field."""
    if not calc_expression and not display_name:
        return {"success": False, "error": "Nothing to update: provide calc_expression or display_name"}

    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )
    axes = cfg.get("axes", [])

    found_field, found_axis_type = _find_field_in_axes(axes, field_name)
    if found_field is None:
        return {"success": False, "error": f"Field '{field_name}' not found in any axis"}
    if found_field.get("type") != "calculated":
        return {"success": False, "error": f"Field '{field_name}' is not a calculated field"}

    if calc_expression is not None and calc_expression != "":
        found_field["alias"] = calc_expression
        found_field["calc"] = calc_expression
        found_field["draft"] = True
    if display_name is not None and display_name != "":
        found_field["title__ru"] = display_name

    _sync_axes_default(cfg)

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Calculated field '{field_name}' updated",
        "report_id": report_id,
        "component_idx": component_idx,
        "field_name": field_name,
        "axis": found_axis_type,
        "sql_expression": found_field.get("calc") or found_field.get("alias", ""),
    }


async def _calc_field_remove(
    client,
    report_id: int,
    component_idx: int,
    field_name: str,
) -> dict[str, Any]:
    """Remove a calculated field from any axis."""
    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )
    axes = cfg.get("axes", [])

    removed_from_axis = None
    for axis in axes:
        original_fields = axis.get("fields", [])
        new_fields = [f for f in original_fields if f.get("name") != field_name]
        if len(new_fields) < len(original_fields):
            axis["fields"] = new_fields
            removed_from_axis = axis.get("type", "")
            break

    if removed_from_axis is None:
        available = [
            f.get("name")
            for axis in axes
            for f in axis.get("fields", [])
            if f.get("name")
        ]
        return {
            "success": False,
            "error": f"Field '{field_name}' not found in any axis",
            "available_fields": available,
            "hint": "Pass value_field = one of available_fields (the field name/alias, "
                    "not the SQL expression). Use calc_fields_list to inspect.",
        }

    _sync_axes_default(cfg)

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Calculated field '{field_name}' removed from component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "removed_field": field_name,
        "removed_from_axis": removed_from_axis,
    }


# -------------------------------------------------------------------------
# PageContainer page management
# -------------------------------------------------------------------------

async def _page_list(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """List pages (tabs) of a PageContainer component."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "pagecontainer" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a PageContainer"}

    visuals = cfg.get("visuals", [])
    pages = [
        {
            "id": v.get("id"),
            "anchor": v.get("anchor"),
            "label_text": v.get("labelText"),
            "tab_width": v.get("tabWidth"),
        }
        for v in visuals
    ]

    return {
        "success": True,
        "report_id": report_id,
        "component_idx": component_idx,
        "pages": pages,
        "count": len(pages),
    }


async def _page_add(
    client,
    report_id: int,
    component_idx: int,
    label_text: str,
    anchor: str | None = None,
) -> dict[str, Any]:
    """Add a new page (tab) to a PageContainer component."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "pagecontainer" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a PageContainer"}

    visuals = cfg.get("visuals", [])

    # Determine next page id
    existing_ids = [v.get("id", 0) for v in visuals if isinstance(v.get("id"), int)]
    new_id = max(existing_ids) + 1 if existing_ids else 1

    new_visual = {
        "id": new_id,
        "anchor": anchor or label_text,
        "labelText": label_text,
        "tabWidth": {"type": "auto", "value": "auto", "label": "Авто"},
        "isHtml": False,
        "tab": None,
    }
    visuals.append(new_visual)
    cfg["visuals"] = visuals

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Page '{label_text}' added to PageContainer {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "page_id": new_id,
        "label_text": label_text,
    }


async def _page_remove(
    client,
    report_id: int,
    component_idx: int,
    page_id: int,
) -> dict[str, Any]:
    """Remove a page (tab) from a PageContainer component by page id."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "pagecontainer" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a PageContainer"}

    visuals = cfg.get("visuals", [])
    new_visuals = [v for v in visuals if v.get("id") != page_id]

    if len(new_visuals) == len(visuals):
        return {"success": False, "error": f"Page with id={page_id} not found in PageContainer {component_idx}"}

    cfg["visuals"] = new_visuals

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Page {page_id} removed from PageContainer {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "removed_page_id": page_id,
        "remaining_pages": len(new_visuals),
    }


async def _page_rename(
    client,
    report_id: int,
    component_idx: int,
    page_id: int,
    label_text: str,
) -> dict[str, Any]:
    """Rename a page (tab) in a PageContainer component."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "pagecontainer" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a PageContainer"}

    visuals = cfg.get("visuals", [])
    target_visual = None
    for v in visuals:
        if v.get("id") == page_id:
            target_visual = v
            break

    if target_visual is None:
        return {"success": False, "error": f"Page with id={page_id} not found in PageContainer {component_idx}"}

    old_label = target_visual.get("labelText", "")
    target_visual["labelText"] = label_text
    target_visual["anchor"] = label_text

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Page {page_id} renamed from '{old_label}' to '{label_text}'",
        "report_id": report_id,
        "component_idx": component_idx,
        "page_id": page_id,
        "label_text": label_text,
    }


# -------------------------------------------------------------------------
# Pivot drill-through links (pivotLink)
# -------------------------------------------------------------------------

_VALID_LINK_TARGETS = ("_blank", "_self")


async def _pivot_link_set(
    client,
    report_id: int,
    component_idx: int,
    field_id: str,
    target_url: str,
    link_title: str | None = None,
    link_target: str = "_blank",
) -> dict[str, Any]:
    """Set a drill-through link on a pivot field.

    Writes config.pivotLink[field_id] = {target, url, title}.
    Does NOT overwrite other fields' links.
    """
    if link_target not in _VALID_LINK_TARGETS:
        return {
            "success": False,
            "error": (
                f"Invalid link_target '{link_target}'. "
                f"Must be one of: {', '.join(_VALID_LINK_TARGETS)}"
            ),
        }

    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "pivot" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a PivotChart"}

    pivot_link = cfg.setdefault("pivotLink", {})
    pivot_link[field_id] = {
        "target": link_target,
        "url": target_url,
        "title": link_title or "",
    }

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Pivot link set for field '{field_id}' on component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "field_id": field_id,
        "link": pivot_link[field_id],
    }


async def _pivot_link_remove(
    client,
    report_id: int,
    component_idx: int,
    field_id: str,
) -> dict[str, Any]:
    """Remove a drill-through link from a pivot field.

    Deletes config.pivotLink[field_id]. Errors if field_id not in pivotLink.
    """
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "pivot" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a PivotChart"}

    pivot_link = cfg.get("pivotLink", {})
    if field_id not in pivot_link:
        existing = list(pivot_link.keys()) if pivot_link else []
        return {
            "success": False,
            "error": (
                f"Field '{field_id}' not found in pivotLink. "
                f"Existing fields: {existing}"
            ),
        }

    del pivot_link[field_id]

    # Clean up empty pivotLink dict
    if not pivot_link:
        cfg.pop("pivotLink", None)

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Pivot link removed for field '{field_id}' on component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "field_id": field_id,
    }


# =========================================================================
# Drill-down hierarchy management
# Frontend: config.drill.hierarchy (array of field IDs), config.drill.drillDateByRange (bool)
# Note: drillDownActive is Redux runtime state, NOT config — MCP can only
# configure the drill hierarchy, not activate drill mode.
# Supported by ALL component types via generic SETTINGS_ACTION_HANDLERS.
# =========================================================================

async def _drill_get(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """Read current drill-down config for a component.

    Returns config.drill (hierarchy + drillDateByRange + fields) or empty defaults.
    """
    _report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    drill = cfg.get("drill", {})
    return {
        "success": True,
        "report_id": report_id,
        "component_idx": component_idx,
        "drill": {
            "hierarchy": drill.get("hierarchy", []),
            "drillDateByRange": drill.get("drillDateByRange", False),
            "fields": drill.get("fields", {}),
        },
    }


async def _drill_add_level(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """Add a new level to drill-down hierarchy (push null — to be set via drill_change_level)."""
    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    drill = cfg.setdefault("drill", {})
    hierarchy = drill.setdefault("hierarchy", [])
    hierarchy.append(None)

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Drill level added (index {len(hierarchy) - 1}, set field via drill_change_level)",
        "report_id": report_id,
        "component_idx": component_idx,
        "hierarchy": hierarchy,
    }


async def _drill_delete_level(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """Remove the last level from drill-down hierarchy (pop semantics)."""
    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    drill = cfg.get("drill", {})
    hierarchy = drill.get("hierarchy", [])
    if not hierarchy:
        return {"success": False, "error": "Drill hierarchy is empty, nothing to delete"}

    removed = hierarchy.pop()

    # Clean up empty drill config
    if not hierarchy and not drill.get("fields") and not drill.get("drillDateByRange"):
        cfg.pop("drill", None)

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Drill level removed (was: {removed})",
        "report_id": report_id,
        "component_idx": component_idx,
        "hierarchy": cfg.get("drill", {}).get("hierarchy", []),
    }


async def _drill_change_level(
    client,
    report_id: int,
    component_idx: int,
    field_index: int,
    field_id: str | None,
) -> dict[str, Any]:
    """Change field at a specific drill hierarchy level.

    Args:
        field_index: 0-based index in hierarchy array
        field_id: Dataset field ID to set (or None to clear)
    """
    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    drill = cfg.get("drill", {})
    hierarchy = drill.get("hierarchy", [])

    if field_index < 0 or field_index >= len(hierarchy):
        return {
            "success": False,
            "error": (
                f"field_index {field_index} out of range. "
                f"Hierarchy has {len(hierarchy)} levels (0-{len(hierarchy) - 1})"
            ),
        }

    hierarchy[field_index] = field_id

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Drill level {field_index} set to '{field_id}'",
        "report_id": report_id,
        "component_idx": component_idx,
        "hierarchy": hierarchy,
    }


async def _drill_toggle_date_range(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """Toggle drillDateByRange boolean in drill config."""
    report, _comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    drill = cfg.setdefault("drill", {})
    current = drill.get("drillDateByRange", False)
    drill["drillDateByRange"] = not current

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"drillDateByRange toggled: {current} → {not current}",
        "report_id": report_id,
        "component_idx": component_idx,
        "drillDateByRange": not current,
    }


async def _drill_set_field(
    client,
    report_id: int,
    component_idx: int,
    drill_category_id: str,
    drill_direction: str,
    drill_selected: str,
) -> dict[str, Any]:
    """Set drill field mapping (table-only: drill.fields[categoryId][direction] = selected)."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "table" not in comp_type.lower():
        return {"success": False, "error": f"drill_set_field is table-only, component is '{comp_type}'"}

    drill = cfg.setdefault("drill", {})
    fields = drill.setdefault("fields", {})
    fields.setdefault(drill_category_id, {})[drill_direction] = drill_selected

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Drill field set: {drill_category_id}[{drill_direction}] = {drill_selected}",
        "report_id": report_id,
        "component_idx": component_idx,
        "drill_fields": fields,
    }


# ───────────────────────────────────────────────────────
# TabsPanel button management (HsTabsPanel)
# ───────────────────────────────────────────────────────

async def _tabs_button_list(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """List buttons in a TabsPanel component."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "tabspanel" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a TabsPanel"}

    visuals = cfg.get("visuals", [])
    buttons = []
    for i, v in enumerate(visuals):
        buttons.append({
            "index": i,
            "anchor": v.get("anchor", ""),
            "labelText": v.get("labelText", ""),
            "link": v.get("link"),
            "linkTarget": v.get("linkTarget", "_self"),
            "fillColor": v.get("fillColor", ""),
            "color": v.get("color", ""),
            "actionType": v.get("actionType", "openURL"),
        })

    return {
        "success": True,
        "report_id": report_id,
        "component_idx": component_idx,
        "count": len(buttons),
        "buttons": buttons,
    }


async def _tabs_button_add(
    client,
    report_id: int,
    component_idx: int,
    label: str,
    link: str | None = None,
    fill_color: str | None = None,
    text_color: str | None = None,
    link_target: str = "_self",
    font_size: float = 1.3,
) -> dict[str, Any]:
    """Add a navigation button to a TabsPanel component.

    Args:
        label: Button text (displayed on the button).
        link: URL for navigation. None = current report (active button).
              Examples: "/report/663", "https://example.com"
        fill_color: Button background color (RGBA). Default: white.
        text_color: Button text color (RGBA). Default: dark gray.
        link_target: "_self" (same tab) or "_blank" (new tab).
        font_size: Font size in rem (default 1.3 ≈ 18px).
    """
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "tabspanel" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a TabsPanel"}

    visuals = cfg.get("visuals", [])

    # Determine next button id
    existing_ids = [v.get("id", 0) for v in visuals if isinstance(v.get("id"), int)]
    new_id = max(existing_ids) + 1 if existing_ids else len(visuals) + 1

    new_button = {
        "anchor": label,
        "id": new_id,
        "labelText": label,
        "labelText__ru": label,
        "color": text_color or "rgba(90,91,111,1)",
        "fillColor": fill_color or "rgba(255,255,255,1)",
        "font": {"size": font_size},
        "actionType": "openURL",
        "link": link,
        "linkTarget": link_target,
        "noDrillOut": False,
    }
    visuals.append(new_button)
    cfg["visuals"] = visuals

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Button '{label}' added to TabsPanel {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "button_index": len(visuals) - 1,
        "button": new_button,
    }


async def _tabs_button_delete(
    client,
    report_id: int,
    component_idx: int,
    button_index: int,
) -> dict[str, Any]:
    """Delete a button from a TabsPanel by index."""
    report, comp, cfg, _key = await _fetch_report_component(
        client, report_id, component_idx,
    )

    comp_type = comp.get("type", "")
    if "tabspanel" not in comp_type.lower():
        return {"success": False, "error": f"Component {component_idx} is '{comp_type}', not a TabsPanel"}

    visuals = cfg.get("visuals", [])
    if button_index < 0 or button_index >= len(visuals):
        return {"success": False, "error": f"Button index {button_index} out of range (0..{len(visuals) - 1})"}

    removed = visuals.pop(button_index)
    cfg["visuals"] = visuals

    err = await _save_report(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Button '{removed.get('labelText', '')}' deleted from TabsPanel {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "removed_button": removed.get("labelText", ""),
        "remaining_count": len(visuals),
    }
