"""
Datasource operations for MCP Server.

Actions (READ-ONLY — write operations not supported via MCP):
- list: List all datasources
- get: Get datasource info
- tables_list: List database tables
- table_fields: Get table fields
- check_connection: Check connection status

Note: create/update/delete datasources must be done via web UI or direct HTTP API.
"""

import logging

from typing import Any

from ..core.exceptions import APIError, NotFoundError, mask_sensitive, missing_params, require

logger = logging.getLogger(__name__)

# Тип драйвера источника по parent_id (FK на driver в метабазе портала).
_DRIVER_BY_PARENT = {
    20: "postgres",
    50: "clickhouse",
    10: "mssql",
    11: "mssql",
    60: "vertica",
    5: "sqlite",
    1: "meta",
}

# form_field_type_id → строковый тип поля (метабаза form_field_type:
# 1=string, 2=number, 3=date — включая datetime; 4='not supported').
# Неизвестные ID → type=None, сырой form_field_type_id остаётся в ответе.
_FIELD_TYPE_BY_ID = {
    1: "string",
    2: "number",
    3: "date",
}


async def _list_datasources(
    client,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List all datasources (paginated)."""
    try:
        response = await client.api_call("datasources", "list")
    except APIError as e:
        return {
            "success": False,
            "error": mask_sensitive(e.message),
            "status_code": (e.details or {}).get("status_code"),
        }

    if response.get("status") != 200:
        return {"success": False, "error": response.get("message", "Unknown error")}

    data = response.get("data", [])
    total = len(data)
    page = data[offset:offset + limit] if limit else data[offset:]

    # Примечание: list API не возвращает db_host, db_name, form
    # Для полной информации используйте action="get" с datasource_id
    items = [
        {
            "id": d.get("ID"),
            "name": d.get("name"),
            "caption": d.get("caption"),
            "description": d.get("description"),
            "parent_id": d.get("parentID"),
            "ord": d.get("ord")
        }
        for d in page
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


async def _get_datasource(client, datasource_id: int) -> dict[str, Any]:
    """Get datasource info."""
    # api_call кидает APIError на любой non-200 — без перехвата friendly-ветки
    # ниже были мёртвым кодом, пользователь видел raw-трейс HTTP 500/404.
    try:
        response = await client.api_call("datasources", "get", object_id=datasource_id)
    except APIError as e:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "error": mask_sensitive(e.message),
            "status_code": (e.details or {}).get("status_code"),
        }

    if response.get("status") != 200:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "error": f"Datasource {datasource_id} not found",
        }

    data = response.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        return {
            "success": False,
            "datasource_id": datasource_id,
            "error": f"Invalid data format for datasource {datasource_id}",
        }

    # Возвращаем только публичные поля. Поля db_host/db_port/db_name/db_schema/
    # db_user/db_url намеренно не выдаются: при prompt-injection LLM мог бы
    # экспортировать internal DB hostname/port/user в third-party endpoint.
    # Тип драйвера = parent_id (FK на driver), а НЕ `form` (это feature-флаг
    # «формы ввода данных», 1/0) — нужен LLM для выбора SQL-диалекта.
    # get всегда отдаёт parentID (default 0); falsy-or сломал бы значение 0
    parent_id = data.get("parentID")
    if parent_id is None:
        parent_id = data.get("parent_id")
    return {
        "success": True,
        "datasource": {
            "id": data.get("ID"),
            "name": data.get("name"),
            "caption": data.get("caption"),
            "parent_id": parent_id,  # тип драйвера: 20=postgres, 50=clickhouse, 10=mssql, 5=files, 1=meta
            "driver_hint": _DRIVER_BY_PARENT.get(parent_id),
            "form": data.get("form"),  # feature-флаг «формы ввода данных» (1/0), НЕ драйвер
            "description": data.get("description"),
        }
    }


async def _list_tables(client, datasource_id: int) -> dict[str, Any]:
    """List database tables for datasource."""
    try:
        response = await client.api_call(
            "datasources",
            "tables.list",
            object_id=datasource_id
        )
    except APIError as e:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "error": mask_sensitive(e.message),
            "status_code": (e.details or {}).get("status_code"),
            "hint": "Источник недоступен или не существует — datasource_operations(action='check_connection') для диагностики.",
        }

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Unknown error")
        }

    tables = response.get("data", [])

    # API может возвращать разные ключи: table, name, TABLE_NAME
    items = [
        {
            "name": t.get("table") or t.get("name") or t.get("TABLE_NAME"),
            "schema": t.get("schema") or t.get("TABLE_SCHEMA") or "public",
            "type": t.get("type") or t.get("TABLE_TYPE", "TABLE")
        }
        for t in tables
    ]

    return {
        "success": True,
        "datasource_id": datasource_id,
        "count": len(items),
        "items": items
    }


async def _get_table_fields(
    client,
    datasource_id: int,
    table_name: str,
    schema: str = "public"
) -> dict[str, Any]:
    """Get table fields/columns."""
    try:
        response = await client.api_call(
            "datasources",
            "tables.fields.list",
            object_id=datasource_id,
            data=[{"table": table_name, "schema": schema}]
        )
    except APIError as e:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "table_name": table_name,
            "error": mask_sensitive(e.message),
            "status_code": (e.details or {}).get("status_code"),
        }

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Unknown error")
        }

    fields = response.get("data", [])

    # Контракт tables.fields.list НЕ отдаёт type/DATA_TYPE/nullable/isPrimary —
    # тип приходит как form_field_type_id (1=строка, 2=число), плюс
    # len/precision/required/pk. Раньше читались несуществующие ключи →
    # type был всегда null, nullable/is_primary — всегда default.
    items = [
        {
            "name": f.get("name") or f.get("COLUMN_NAME"),
            "type": (f.get("type") or f.get("DATA_TYPE")
                     or _FIELD_TYPE_BY_ID.get(f.get("form_field_type_id"))),
            "form_field_type_id": f.get("form_field_type_id"),
            "len": f.get("len"),
            "precision": f.get("precision"),
            # required = «обязательность ввода в форме» — для identity/PK-
            # колонок может быть 0 при NOT NULL.
            "nullable": not f.get("required", False),
            "is_primary": bool(f.get("pk", f.get("isPrimary", False)))
        }
        for f in fields
    ]

    return {
        "success": True,
        "datasource_id": datasource_id,
        "table_name": table_name,
        "schema": schema,
        "count": len(items),
        "items": items
    }


async def _check_connection(client, datasource_id: int) -> dict[str, Any]:
    """Check datasource connection status."""
    try:
        response = await client.api_call(
            "datasources",
            "check.conn",  # Правильная команда API
            object_id=datasource_id
        )
    except APIError as e:
        # Для check_connection ошибка HTTP = честный ответ «не подключается».
        return {
            "success": False,
            "datasource_id": datasource_id,
            "connected": False,
            "error": mask_sensitive(e.message),
            "status_code": (e.details or {}).get("status_code"),
        }

    if response.get("status") != 200:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "connected": False,
            "error": response.get("message", "Connection failed")
        }

    data = response.get("data", {})
    if isinstance(data, list) and data:
        data = data[0]

    return {
        "success": True,
        "datasource_id": datasource_id,
        "connected": data.get("connected", True),
        "message": data.get("message", "Connection successful")
    }


async def datasource_operations(
    client,
    action: str,
    datasource_id: int | None = None,
    table_name: str | None = None,
    schema: str = "public",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Read-only operations for data sources (database connections).

    Actions:
    - list: List all datasources (paginated via limit/offset)
    - get: Get datasource info
    - tables_list: List database tables
    - table_fields: Get table fields (with schema support)
    - check_connection: Check connection status

    Read-only tool. Datasource create/update/delete is intentionally not exposed
    through MCP — manage datasource connections via the ModusBI portal web UI.
    """
    match action:
        case "list":
            return await _list_datasources(client, limit=limit, offset=offset)

        case "get":
            err = require(
                {"datasource_id": datasource_id},
                tool="datasource_operations", action="get",
                types={"datasource_id": "int"},
            )
            if err:
                return err
            return await _get_datasource(client, datasource_id)

        case "create" | "update" | "delete":
            return {
                "error": f"Action '{action}' is not supported for datasources via MCP. "
                         "Use the web portal or direct HTTP API to manage datasource connections."
            }

        case "tables_list":
            err = require(
                {"datasource_id": datasource_id},
                tool="datasource_operations", action="tables_list",
                types={"datasource_id": "int"},
            )
            if err:
                return err
            return await _list_tables(client, datasource_id)

        case "table_fields":
            err = require(
                {"datasource_id": datasource_id, "table_name": table_name},
                tool="datasource_operations", action="table_fields",
                types={"datasource_id": "int", "table_name": "str"},
            )
            if err:
                return err
            return await _get_table_fields(client, datasource_id, table_name, schema)

        case "check_connection":
            err = require(
                {"datasource_id": datasource_id},
                tool="datasource_operations", action="check_connection",
                types={"datasource_id": "int"},
            )
            if err:
                return err
            return await _check_connection(client, datasource_id)

        case _:
            return {"error": f"Unknown action: {action}"}
