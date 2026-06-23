"""
Reportgroup operations for MCP Server.

Actions:
- list: List all report groups
- get: Get group by ID
- create: Create new group
- update: Update group
- delete: Delete group
- move: Move group to new parent
"""

import logging

from typing import Any

from ..core.security import check_action
from ..core.exceptions import NotFoundError, missing_params, require

logger = logging.getLogger(__name__)


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
            "parent_id": g.get("parent_group_id"),
            "menu": bool(g.get("menu")),
            "is_extended": bool(g.get("is_extended")),
            "has_reports": bool(g.get("has_reports")),
            "empty": bool(g.get("empty")),
            "level_ord": g.get("level_ord")
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


async def _get_group(client, group_id: int) -> dict[str, Any]:
    """Get report group by ID."""
    response = await client.api_call("reportgroups", "get", object_id=group_id)

    if response.get("status") != 200:
        raise NotFoundError(f"Report group {group_id} not found", object_id=group_id)

    data = response.get("data", [])
    if not data:
        raise NotFoundError(f"Report group {group_id} not found", object_id=group_id)

    g = data[0]
    return {
        "success": True,
        "group": {
            "id": g.get("ID"),
            "name": g.get("name"),
            "caption": g.get("caption"),
            "parent_id": g.get("parent_group_id"),
            "menu": bool(g.get("menu")),
            "is_default": bool(g.get("def")),
            "is_extended": bool(g.get("is_extended")),
            "has_reports": bool(g.get("has_reports")),
            "empty": bool(g.get("empty")),
            "level_ord": g.get("level_ord"),
            "options": g.get("options", {}),
            "image": g.get("image")
        }
    }


async def _create_group(
    client,
    name: str,
    caption: str | None = None,
    parent_id: int = 0,
    menu: bool = True,
    is_extended: bool = True,
    options: dict | None = None,
    image: str | None = None
) -> dict[str, Any]:
    """Create new report group."""
    group_data = {
        "name": name,
        "caption": caption or name,
        "parent_group_id": parent_id or None,  # 0/None → root (null); backend HTTP 500 on 0
        "menu": 1 if menu else 0,
        "is_extended": 1 if is_extended else 0,
        "options": options or {}
    }

    if image:
        group_data["image"] = image

    response = await client.api_call("reportgroups", "create", data=[group_data])

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to create group")
        }

    data = response.get("data", [])
    if data:
        created = data[0]
        return {
            "success": True,
            "message": "Report group created successfully",
            "group": {
                "id": created.get("ID"),
                "name": created.get("name"),
                "caption": created.get("caption"),
                "parent_id": created.get("parent_group_id")
            }
        }

    return {
        "success": True,
        "message": "Group created but could not retrieve its ID"
    }


async def _update_group(
    client,
    group_id: int,
    name: str | None = None,
    caption: str | None = None,
    parent_id: int | None = None,
    menu: bool | None = None,
    is_extended: bool | None = None,
    options: dict | None = None,
    image: str | None = None
) -> dict[str, Any]:
    """Update report group."""
    # First get current group
    result = await client.api_call("reportgroups", "get", object_id=group_id)

    if result.get("status") != 200:
        return {"success": False, "error": f"Group {group_id} not found"}

    data = result.get("data", [])
    if not data:
        return {"success": False, "error": f"Group {group_id} not found"}

    current = data[0]
    changes = {}

    # Build update data
    update_data = {
        "ID": group_id,
        "name": name if name is not None else current.get("name"),
        "caption": caption if caption is not None else current.get("caption"),
        "parent_group_id": (parent_id or None) if parent_id is not None else current.get("parent_group_id"),  # 0 → root null
        "menu": (1 if menu else 0) if menu is not None else current.get("menu"),
        "is_extended": (1 if is_extended else 0) if is_extended is not None else current.get("is_extended"),
        "options": options if options is not None else current.get("options", {}),
        "def": current.get("def", 0)  # Preserve default flag
    }

    if image is not None:
        update_data["image"] = image

    # Track changes
    if name is not None and name != current.get("name"):
        changes["name"] = {"old": current.get("name"), "new": name}
    if caption is not None and caption != current.get("caption"):
        changes["caption"] = {"old": current.get("caption"), "new": caption}
    if parent_id is not None and parent_id != current.get("parent_group_id"):
        changes["parent_id"] = {"old": current.get("parent_group_id"), "new": parent_id}
    if menu is not None and menu != bool(current.get("menu")):
        changes["menu"] = {"old": bool(current.get("menu")), "new": menu}

    response = await client.api_call("reportgroups", "update", object_id=group_id, data=[update_data])

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to update group")
        }

    return {
        "success": True,
        "message": f"Group {group_id} updated",
        "group_id": group_id,
        "changes": changes if changes else None
    }


async def _delete_group(client, group_id: int) -> dict[str, Any]:
    """Delete report group."""
    response = await client.api_call("reportgroups", "delete", object_id=group_id)

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to delete group")
        }

    return {
        "success": True,
        "message": f"Group {group_id} deleted",
        "group_id": group_id
    }


async def _move_group(
    client,
    group_id: int,
    parent_id: int,
    previous_group_id: int | None = None
) -> dict[str, Any]:
    """Move report group to new parent."""
    move_data = {
        "group_id": group_id,
        "parent_group_id": parent_id or None  # 0 → root null (backend HTTP 500 on 0)
    }

    if previous_group_id is not None:
        move_data["previous_group_id"] = previous_group_id

    response = await client.api_call("reportgroups", "move", data=[move_data])

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to move group")
        }

    data = response.get("data", [])
    if data:
        moved = data[0]
        return {
            "success": True,
            "message": f"Group {group_id} moved to parent {parent_id}",
            "group": {
                "id": moved.get("ID"),
                "name": moved.get("name"),
                "parent_id": moved.get("parent_group_id"),
                "level_ord": moved.get("level_ord")
            }
        }

    return {
        "success": True,
        "message": f"Group {group_id} moved"
    }


async def reportgroup_operations(
    client,
    action: str,
    group_id: int | None = None,
    name: str | None = None,
    caption: str | None = None,
    parent_id: int | None = None,
    menu: bool | None = None,
    is_extended: bool | None = None,
    options: dict | None = None,
    image: str | None = None,
    previous_group_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    CRUD operations for report groups.

    Actions:
    - list: List all report groups (paginated via limit/offset)
    - get: Get group by ID (group_id required)
    - create: Create group (name required; caption, parent_id, menu, options optional)
    - update: Update group (group_id required; name, caption, parent_id, menu optional)
    - delete: Delete group (group_id required)
    - move: Move group (group_id, parent_id required; previous_group_id optional)
    """
    match action:
        case "list":
            return await _list_groups(client, limit=limit, offset=offset)

        case "get":
            err = require(
                {"group_id": group_id},
                tool="reportgroup_operations", action="get",
                types={"group_id": "int"},
            )
            if err:
                return err
            return await _get_group(client, group_id)

        case "create":
            check_action("create")
            err = require(
                {"name": name},
                tool="reportgroup_operations", action="create",
                types={"name": "str (latin identifier, e.g. 'sales')"},
                example="reportgroup_operations(action='create', name='Sales', caption='Sales Department', parent_id=1, menu=True)",
            )
            if err:
                return err
            return await _create_group(
                client, name,
                caption=caption,
                parent_id=parent_id or 0,
                menu=menu if menu is not None else True,
                is_extended=is_extended if is_extended is not None else True,
                options=options,
                image=image
            )

        case "update":
            check_action("update")
            err = require(
                {"group_id": group_id},
                tool="reportgroup_operations", action="update",
                types={"group_id": "int"},
            )
            if err:
                return err
            return await _update_group(
                client, group_id,
                name=name, caption=caption, parent_id=parent_id,
                menu=menu, is_extended=is_extended, options=options, image=image
            )

        case "delete":
            check_action("delete")
            err = require(
                {"group_id": group_id},
                tool="reportgroup_operations", action="delete",
                types={"group_id": "int"},
            )
            if err:
                return err
            return await _delete_group(client, group_id)

        case "move":
            check_action("move")
            err = require(
                {"group_id": group_id, "parent_id": parent_id},
                tool="reportgroup_operations", action="move",
                types={"group_id": "int", "parent_id": "int"},
                example="reportgroup_operations(action='move', group_id=25, parent_id=20, previous_group_id=10)",
            )
            if err:
                return err
            return await _move_group(client, group_id, parent_id, previous_group_id)

        case _:
            return {"error": f"Unknown action: {action}"}
