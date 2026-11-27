"""
Dataset operations for MCP Server.

Actions:
- list: List all datasets
- get: Get dataset by ID
- fields_list: Get dataset fields
- create: Create dataset (name, datasource_id required; query, caption optional)
- update: Update dataset
- delete: Delete dataset
"""

import logging

from typing import Any

from ..core.security import check_action
from ..core.exceptions import APIError, NotFoundError, missing_params, require
# Единственная каноничная версия хелпера живёт в query_execute и возвращает
# 3-tuple (driver_id, ds_record, error). Локальный 2-tuple дубликат удалён —
# распаковка в 3 переменные давала необработанный ValueError.
from .query_execute import _get_driver_id_from_datasource

logger = logging.getLogger(__name__)


async def _list_datasets(
    client,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """List all datasets (paginated)."""
    response = await client.api_call("datasets", "list.full")

    if response.get("status") != 200:
        return {"error": response.get("message", "Unknown error")}

    data = response.get("data", [])
    total = len(data)
    page = data[offset:offset + limit] if limit else data[offset:]

    items = [
        {
            "id": d.get("ID"),
            "name": d.get("name"),
            "caption": d.get("caption"),
            # API может возвращать разные поля:
            # - parentID: ID источника данных (основной)
            # - datasourceID: альтернативное имя (для совместимости)
            # - driverID: тип драйвера/форма (не datasource!)
            "datasource_id": d.get("parentID") or d.get("datasourceID"),
            "datasource_name": d.get("datasourceName"),
            "driver_id": d.get("driverID"),
            "fields_count": len(d.get("fields", []))
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


async def _get_dataset(client, dataset_id: int) -> dict[str, Any]:
    """Get dataset metadata."""
    result = await client.api_call("datasets", "get", object_id=dataset_id)

    if result.get("status") != 200:
        raise NotFoundError(f"Dataset {dataset_id} not found", object_id=dataset_id)

    data = result.get("data", [])
    if isinstance(data, list) and data:
        data = data[0]
    elif not isinstance(data, dict):
        raise NotFoundError(f"Invalid data format for dataset {dataset_id}", object_id=dataset_id)

    fields = [
        {
            "name": f.get("name"),
            "alias": f.get("alias") or f.get("caption") or f.get("name"),
            "type": f.get("type"),
            "units": f.get("units"),
            "description": f.get("description") or f.get("comment"),
            "format": f.get("format")
        }
        for f in data.get("fields", [])
    ]

    return {
        "success": True,
        "dataset": {
            "id": data.get("ID"),
            "name": data.get("name"),
            "caption": data.get("caption"),
            # parentID = ID источника данных, driverID = тип драйвера
            "datasource_id": data.get("parentID") or data.get("datasourceID"),
            "datasource_name": data.get("datasourceName"),
            "driver_id": data.get("driverID"),
            "query": data.get("query"),  # SQL запрос датасета
            "fields_count": len(fields),
            "fields": fields,
            # Backend lazily computes count — для свежесозданных датасетов
            # возвращает 0 даже при наличии данных. Не можем отличить
            # «реально 0 строк» от «ещё не посчитано», поэтому 0/None
            # одинаково схлопываем в None. Для актуального счёта клиенты
            # должны вызвать dataset_query("SELECT COUNT(*) FROM <view>").
            "total_rows": data.get("count") or None,
        }
    }


async def _list_fields(client, dataset_id: int) -> dict[str, Any]:
    """Get dataset fields list."""
    response = await client.api_call("datasets", "get", object_id=dataset_id)

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Unknown error")
        }

    data = response.get("data", [])
    if not data:
        return {
            "success": False,
            "error": f"Dataset {dataset_id} not found"
        }

    dataset = data[0]
    fields = dataset.get("fields", [])

    items = [
        {
            "id": f.get("ID"),
            "name": f.get("name"),
            "alias": f.get("alias") or f.get("name"),
            "type": f.get("type"),
            "field_type": f.get("fieldType")
        }
        for f in fields
    ]

    return {
        "success": True,
        "dataset_id": dataset_id,
        "dataset_name": dataset.get("name"),
        "count": len(items),
        "items": items
    }


async def _create_dataset(
    client,
    name: str,
    datasource_id: int,
    query: str | None = None,
    caption: str | None = None
) -> dict[str, Any]:
    """Create new dataset."""
    # datasets/create с параметром query даёт HTTP 500 + orphan-датасет
    # (по контракту create = «пустой набор»). SQL-датасет строится только через
    # dataset_create_from_sql — роутим туда вместо отправки query в create.
    if query:
        from .query_execute import dataset_create_from_sql
        return await dataset_create_from_sql(
            client,
            sql_query=query,
            datasource_id=datasource_id,
            name=name,
            caption=caption,
        )

    dataset_data = {
        "name": name,
        "caption": caption or name,
        "parentID": datasource_id  # API uses parentID for datasource
    }

    response = await client.api_call("datasets", "create", data=[dataset_data])

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to create dataset")
        }

    data = response.get("data", [])
    if data:
        created = data[0]
        logger.info(
            "audit:dataset_create instance=%s dataset_id=%s name=%r datasource_id=%s",
            client.instance.name, created.get("ID"), name, datasource_id,
        )
        return {
            "success": True,
            "message": "Dataset created successfully",
            "dataset": {
                "id": created.get("ID"),
                "name": created.get("name"),
                "caption": created.get("caption"),
                # портал в echo create отдаёт parentID, не datasourceID —
                # fallback как в list/get, иначе datasource_id:null при персистнутой связи
                "datasource_id": created.get("datasourceID") or created.get("parentID")
            }
        }

    return {
        "success": True,
        "message": "Dataset created but could not retrieve its ID"
    }


async def _update_dataset(
    client,
    dataset_id: int,
    name: str | None = None,
    caption: str | None = None,
    query: str | None = None,
    datasource_id: int | None = None,
    rls: bool | None = None,
    query_rls: str | None = None,
    validate_query: bool = True,
    field_aliases: dict | None = None
) -> dict[str, Any]:
    """
    Update dataset.

    Args:
        dataset_id: Dataset ID to update
        name: New name (optional)
        caption: New caption (optional)
        query: New SQL query (optional) - will be validated and fields updated
        datasource_id: New datasource connection ID (optional) - will update driverID
        rls: Enable/disable Row Level Security (optional)
        query_rls: RLS query filter (optional)
        validate_query: If True, validate SQL and update fields when query changes (default: True)
        field_aliases: Dict mapping field name to {alias, description} for semantic layer
                       Example: {"region": {"alias": "Регион", "description": "Название региона"}}
    """
    # First get current dataset
    result = await client.api_call("datasets", "get", object_id=dataset_id)

    if result.get("status") != 200:
        return {
            "success": False,
            "error": f"Dataset {dataset_id} not found"
        }

    data = result.get("data", [])
    if not data:
        return {
            "success": False,
            "error": f"Dataset {dataset_id} not found"
        }

    current = data[0]

    # Track changes
    changes = {}

    # Determine effective datasource_id and driver_id
    effective_datasource_id = datasource_id if datasource_id is not None else current.get("parentID")
    effective_driver_id = current.get("driverID")

    # If datasource_id is changing, we need to get the new driver_id
    if datasource_id is not None and datasource_id != current.get("parentID"):
        driver_id, _ds_record, error = await _get_driver_id_from_datasource(client, datasource_id)
        if error:
            return {
                "success": False,
                "error": f"Failed to get driver for datasource {datasource_id}: {error}"
            }
        effective_driver_id = driver_id
        changes["datasource_id"] = {"old": current.get("parentID"), "new": datasource_id}
        changes["driver_id"] = {"old": current.get("driverID"), "new": driver_id}

    # If query is changing and validate_query is True, validate SQL and get new fields
    effective_query = query if query is not None else current.get("query")
    new_fields = None

    if query is not None and query != current.get("query") and validate_query:
        # Import sql_query_validate from query_execute
        from .query_execute import sql_query_validate

        validation = await sql_query_validate(
            client,
            sql_query=query,
            datasource_id=effective_datasource_id,
            dataset_name=name or current.get("name")
        )

        if not validation.get("success"):
            return {
                "success": False,
                "error": f"SQL validation failed: {validation.get('error')}",
                "step": "validation"
            }

        # Build new fields from validation result
        # name = AS alias from SQL (technical name in dataset, used for field_aliases)
        # alias/description = empty - user sets via field_aliases
        validated_fields = validation.get("fields", [])
        new_fields = []
        for f in validated_fields:
            field_name = f.get("name", "")

            new_fields.append({
                "ID": f.get("id", 0),
                "name": field_name,   # AS alias from SQL - this is the field key for field_aliases
                "alias": "",          # Empty - user sets via field_aliases
                "type": f.get("type", "string"),
                "description": "",    # Empty - user sets via field_aliases
                "bk": False,
                "correctable": False,
                "expression": [],
                "prop": {"date": "", "ext": "", "fileName": "", "size": ""}
            })

        changes["query"] = {"old": "...", "new": "...", "fields_updated": True}

    elif query is not None and query != current.get("query"):
        changes["query"] = {"old": "...", "new": "...", "fields_updated": False}

    # Build update data
    # IMPORTANT: Use parentID for datasource connection, driverID for driver type
    update_data = {
        "ID": dataset_id,
        "name": name if name is not None else current.get("name"),
        "caption": caption if caption is not None else current.get("caption"),
        "query": effective_query,
        "parentID": effective_datasource_id,  # Datasource connection ID
        "driverID": effective_driver_id        # Driver type
    }

    # Add new fields if query was validated
    if new_fields is not None:
        update_data["fields"] = new_fields

    # Track name change
    if name is not None and name != current.get("name"):
        changes["name"] = {"old": current.get("name"), "new": name}

    # Track caption change
    if caption is not None and caption != current.get("caption"):
        changes["caption"] = {"old": current.get("caption"), "new": caption}

    # Add RLS fields if provided
    if rls is not None:
        update_data["rls"] = 1 if rls else 0
        changes["rls"] = {"old": current.get("rls"), "new": rls}

    if query_rls is not None:
        # Backend читает snake_case query_rls (референс: security_operations
        # update_filter/disable). camelCase queryRls молча игнорировался —
        # rls-флаг персистился, а сам фильтр терялся.
        update_data["query_rls"] = query_rls
        changes["query_rls"] = {"old": "...", "new": "..."}

    # Apply field_aliases to update alias/description (semantic layer)
    if field_aliases:
        # Get current fields if we don't have new_fields from query validation
        current_fields = new_fields if new_fields else current.get("fields", [])

        updated_fields = []
        fields_changed = []
        for field in current_fields:
            field_name = field.get("name", "")
            # Always normalize field to only required keys for update API
            # Raw API response may contain extra keys that backend rejects
            field = {
                "ID": field.get("ID", field.get("id", 0)),
                "name": field_name,
                "alias": field.get("alias", ""),
                "type": field.get("type", "string"),
                "description": field.get("description", ""),
                "bk": field.get("bk", False),
                "correctable": field.get("correctable", False),
                "expression": field.get("expression", []),
                "prop": field.get("prop", {"date": "", "ext": "", "fileName": "", "size": ""})
            }
            if field_name in field_aliases:
                alias_info = field_aliases[field_name]
                # Update alias if provided
                if "alias" in alias_info:
                    field["alias"] = alias_info["alias"]
                # Update description if provided
                if "description" in alias_info:
                    field["description"] = alias_info["description"]
                fields_changed.append(field_name)
            updated_fields.append(field)

        update_data["fields"] = updated_fields
        if fields_changed:
            changes["field_aliases"] = {"updated_fields": fields_changed}

    response = await client.api_call("datasets", "update", data=[update_data])

    if response.get("status") != 200:
        error_msg = response.get("message", "Failed to update dataset")
        return {
            "success": False,
            "error": error_msg
        }

    # post-write verification. Backend может вернуть HTTP 200,
    # но фактически НЕ применить изменения. Известные случаи:
    # update field_aliases для несуществующего поля,
    # update query на bound dataset (привязан к компонентам).
    # Делаем повторный get и сравниваем по ключам.
    query_changed = query is not None and query != current.get("query")
    if field_aliases or query_changed:
        try:
            verify_resp = await client.api_call(
                "datasets", "get", object_id=dataset_id,
            )
            if verify_resp.get("status") == 200:
                vdata = verify_resp.get("data", [])
                vds = (vdata[0] if isinstance(vdata, list) and vdata else
                       vdata if isinstance(vdata, dict) else None)
                if isinstance(vds, dict) and query_changed:
                    actual_query = (vds.get("query") or "").strip()
                    if actual_query != query.strip():
                        return {
                            "success": False,
                            "error": (
                                f"Backend silently ignored query update for "
                                f"dataset {dataset_id}: HTTP 200, но SQL остался "
                                f"прежним. Типично для bound dataset — поля уже "
                                f"привязаны к компонентам отчёта."
                            ),
                            "dataset_id": dataset_id,
                            "query_not_applied": {
                                "expected": query.strip()[:300],
                                "actual": actual_query[:300],
                                "reason": "query_unchanged_after_save",
                            },
                            "hint": (
                                "Создайте новый датасет через "
                                "dataset_create_from_sql, перепривяжите "
                                "компоненты (component_crud update c новым "
                                "dataset_id), затем удалите старый датасет."
                            ),
                            "changes_attempted": changes if changes else None,
                        }
                if isinstance(vds, dict) and field_aliases:
                    actual_aliases = {
                        f.get("name"): f.get("alias", "")
                        for f in (vds.get("fields") or [])
                        if isinstance(f, dict) and f.get("name")
                    }
                    not_applied = []
                    for name, info in field_aliases.items():
                        expected = info.get("alias") if isinstance(info, dict) else None
                        if expected is None:
                            continue
                        actual = actual_aliases.get(name)
                        if actual is None:
                            # field doesn't exist in dataset at all
                            not_applied.append({
                                "name": name, "expected": expected,
                                "reason": "field_not_in_dataset",
                            })
                        elif actual != expected:
                            not_applied.append({
                                "name": name, "expected": expected,
                                "actual": actual,
                                "reason": "alias_unchanged_after_save",
                            })
                    if not_applied:
                        return {
                            "success": False,
                            "error": (
                                f"Backend silently ignored field_aliases for "
                                f"{[n['name'] for n in not_applied]}. "
                                f"Workflow: либо задайте алиасы СРАЗУ после "
                                f"dataset_create_from_sql (до filter_field_add), "
                                f"либо отвяжите поля от компонентов через "
                                f"filter_field_remove перед update'ом."
                            ),
                            "dataset_id": dataset_id,
                            "field_aliases_not_applied": not_applied,
                            "changes_attempted": changes if changes else None,
                        }
        except Exception:
            # verify не должен ломать happy path; если не получилось —
            # возвращаем success.
            pass

    return {
        "success": True,
        "message": f"Dataset {dataset_id} updated",
        "dataset_id": dataset_id,
        "changes": changes if changes else None,
        "fields_count": len(new_fields) if new_fields else None
    }


async def _delete_dataset(client, dataset_id: int) -> dict[str, Any]:
    """Delete dataset."""
    # портальный soft-delete идемпотентен — delete несуществующего id
    # отвечает 200, и no-op неотличим от удаления. Pre-check через get,
    # чтобы фантомный id давал честный success:false.
    not_found = {
        "success": False,
        "error": f"Dataset {dataset_id} not found",
        "hint": "dataset_operations(action='list') поможет найти существующие id",
    }
    try:
        check = await client.api_call("datasets", "get", object_id=dataset_id)
    except APIError as e:
        if e.details.get("status_code") == 404:
            return not_found
        raise
    if check.get("status") != 200 or not check.get("data"):
        return not_found

    response = await client.api_call("datasets", "delete", object_id=dataset_id)

    if response.get("status") != 200:
        return {
            "success": False,
            "error": response.get("message", "Failed to delete dataset")
        }

    return {
        "success": True,
        "message": f"Dataset {dataset_id} deleted",
        "dataset_id": dataset_id
    }


async def dataset_operations(
    client,
    action: str,
    dataset_id: int | None = None,
    name: str | None = None,
    caption: str | None = None,
    datasource_id: int | None = None,
    query: str | None = None,
    rls: bool | None = None,
    query_rls: str | None = None,
    field_aliases: dict | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    CRUD operations for datasets (semantic layer).

    Actions:
    - list: List all datasets (paginated via limit/offset, default limit=50)
    - get: Get dataset by ID
    - fields_list: Get dataset fields
    - create: Create dataset (name, datasource_id required; query, caption optional)
    - update: Update dataset (datasource_id, rls, query_rls, field_aliases supported)
    - delete: Delete dataset
    """
    match action:
        case "list":
            return await _list_datasets(client, limit=limit, offset=offset)

        case "get":
            err = require(
                {"dataset_id": dataset_id},
                tool="dataset_operations", action="get",
                types={"dataset_id": "int"},
            )
            if err:
                return err
            return await _get_dataset(client, dataset_id)

        case "fields_list":
            err = require(
                {"dataset_id": dataset_id},
                tool="dataset_operations", action="fields_list",
                types={"dataset_id": "int"},
            )
            if err:
                return err
            return await _list_fields(client, dataset_id)

        case "create":
            check_action("create")
            err = require(
                {"name": name, "datasource_id": datasource_id},
                tool="dataset_operations", action="create",
                types={"name": "str (latin identifier)", "datasource_id": "int"},
                example="dataset_operations(action='create', name='sales_by_region', caption='Продажи по регионам', datasource_id=1, sql='SELECT region, SUM(amount) AS total FROM sales GROUP BY region')",
            )
            if err:
                return err
            return await _create_dataset(client, name, datasource_id, query, caption)

        case "update":
            check_action("update")
            err = require(
                {"dataset_id": dataset_id},
                tool="dataset_operations", action="update",
                types={"dataset_id": "int"},
            )
            if err:
                return err
            # Guard: MCP framework шлёт "" вместо None для незаданных
            # optional str — иначе query="" перезаписал бы SQL пустым
            # (тот же quirk, что в component_crud/axes).
            return await _update_dataset(
                client, dataset_id,
                name=name or None, caption=caption or None,
                query=query or None,
                datasource_id=datasource_id, rls=rls,
                query_rls=query_rls if query_rls else None,
                field_aliases=field_aliases
            )

        case "delete":
            check_action("delete")
            err = require(
                {"dataset_id": dataset_id},
                tool="dataset_operations", action="delete",
                types={"dataset_id": "int"},
            )
            if err:
                return err
            return await _delete_dataset(client, dataset_id)

        case _:
            return {"error": f"Unknown action: {action}"}
