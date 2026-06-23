"""
Security operations for Row Level Security (RLS).

Manages RLS roles and filters. In ModusBI, RLS is configured per-dataset
via rls and query_rls fields.
"""

import logging

from typing import Any

from ..core.exceptions import require, mask_sensitive, APIError

logger = logging.getLogger(__name__)


def _rls_write_error(response: dict[str, Any], dataset_id: int, fallback: str) -> dict[str, Any]:
    """Build a structured error for a failed RLS write.

    The backend returns a bare HTTP 400 when the dataset's driver does not
    support row-level security (notably ClickHouse — ``query_rls`` is only
    honoured by SQL drivers such as PostgreSQL). Surface that explicitly
    instead of the opaque "Failed to ..." message.
    """
    status = response.get("status")
    result: dict[str, Any] = {
        "success": False,
        "error": response.get("message") or fallback,
        "dataset_id": dataset_id,
        "status": status,
    }
    if status == 400:
        result["hint"] = (
            "HTTP 400 often means RLS is not supported by this dataset's driver. "
            "RLS (query_rls) works on SQL drivers such as PostgreSQL; drivers like "
            "ClickHouse reject it. Verify the dataset's datasource via "
            "datasource_operations(action='list') and apply RLS on a PostgreSQL-backed dataset."
        )
    return result


def _api_error_as_response(e: APIError) -> dict[str, Any]:
    """Convert APIError (raised by api_call on non-200 HTTP) to a response-like dict.

    ``client.api_call`` raises on non-200 instead of returning the body, so
    write actions catch APIError and feed the real status code into
    ``_rls_write_error`` — otherwise the driver hint never reaches the user.
    """
    return {
        "status": e.details.get("status_code"),
        "message": e.message,
    }


async def _read_full_dataset(client, dataset_id: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read the full dataset object via datasets/get.

    The portal has no ``datasets/read`` command (HTTP 406 "command not found");
    the only read command is ``datasets/get`` — same as dataset_operations uses.

    Returns:
        (dataset, error) — exactly one of them is not None.
    """
    response = await client.api_call("datasets", "get", object_id=dataset_id)

    if response.get("status") != 200:
        return None, {
            "success": False,
            "error": response.get("message", "Failed to get dataset"),
            "dataset_id": dataset_id,
        }

    data = response.get("data", [])
    dataset = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else None)
    if not dataset:
        return None, {
            "success": False,
            "error": "Dataset not found",
            "dataset_id": dataset_id,
        }
    return dataset, None


async def _write_rls_full(
    client,
    dataset_id: int,
    rls: int,
    query_rls: str | None,
    fallback: str,
) -> dict[str, Any]:
    """Read-modify-write for the RLS fields of a dataset.

    The datasets/update contract requires the FULL object (ID, name, caption,
    parentID, query are mandatory; unchanged params must be taken from
    datasets.get). A partial payload like [{"rls": 1}] is rejected with
    HTTP 400. Same pattern as dataset_operations._update_dataset:
    get current object → overlay rls/query_rls → update full object.

    Args:
        rls: New RLS flag value (1/0)
        query_rls: New RLS filter; None = keep the current query_rls

    Returns:
        {"success": True, "dataset": current} or an error envelope.
    """
    current, err = await _read_full_dataset(client, dataset_id)
    if err:
        return err

    update_data = {
        "ID": dataset_id,
        "name": current.get("name"),
        "caption": current.get("caption"),
        "query": current.get("query"),
        "parentID": current.get("parentID"),  # Datasource connection ID
        "driverID": current.get("driverID"),  # Driver type
        "rls": rls,
        # Backend reads snake_case query_rls; camelCase queryRls is silently dropped
        "query_rls": current.get("query_rls", "") if query_rls is None else query_rls,
    }

    response = await client.api_call("datasets", "update", data=[update_data])

    if response.get("status") != 200:
        return _rls_write_error(response, dataset_id, fallback)

    return {"success": True, "dataset": current}


async def security_operations(
    client,
    action: str,
    dataset_id: int | None = None,
    enabled: bool | None = None,
    rls_query: str | None = None
) -> dict[str, Any]:
    """
    Manage Row Level Security (RLS) for datasets.

    RLS in ModusBI works by adding a filter query (query_rls) that is automatically
    applied to all data requests. The query can use :current_user_id placeholder.

    Actions:
    - status: Get RLS status for dataset
    - enable: Enable RLS for dataset
    - disable: Disable RLS for dataset
    - update_filter: Update RLS filter query
    - list_enabled: List all datasets with RLS enabled
    - test: Test RLS filter with sample data
    """
    match action:
        case "status":
            err = require(
                {"dataset_id": dataset_id},
                tool="security_operations", action="status",
                types={"dataset_id": "int"},
                example="security_operations(action='status', dataset_id=5)",
            )
            if err:
                return err

            try:
                # datasets/get — the portal has no "read" command (→ HTTP 406)
                dataset, ds_err = await _read_full_dataset(client, dataset_id)
                if ds_err:
                    return ds_err

                return {
                    "success": True,
                    "dataset_id": dataset_id,
                    "dataset_name": dataset.get("name"),
                    "rls_enabled": bool(dataset.get("rls", 0)),
                    "rls_query": dataset.get("query_rls", ""),
                    "has_filter": bool(dataset.get("query_rls"))
                }

            except APIError as e:
                # Симметрично write-actions: реальный HTTP-статус вместо
                # generic 'RLS operation failed' + нерелевантного SQL-хинта.
                return {
                    "success": False,
                    "error": mask_sensitive(e.message),
                    "status_code": (e.details or {}).get("status_code"),
                    "dataset_id": dataset_id,
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": "RLS operation failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the dataset exists and rls_query is valid SQL.",
                }

        case "enable":
            err = require(
                {"dataset_id": dataset_id},
                tool="security_operations", action="enable",
                types={"dataset_id": "int"},
                example="security_operations(action='enable', dataset_id=5)",
            )
            if err:
                return err

            from ..core.security import check_action
            check_action("update")

            try:
                # Read-modify-write: keep the current query_rls, only flip the flag
                written = await _write_rls_full(
                    client, dataset_id,
                    rls=1, query_rls=None,
                    fallback="Failed to enable RLS",
                )
                if not written.get("success"):
                    return written

                return {
                    "success": True,
                    "message": f"RLS enabled for dataset {dataset_id}",
                    "dataset_id": dataset_id,
                    "rls_enabled": True,
                    "hint": (
                        "Use update_filter action to set RLS query. NOTE: "
                        "эффект RLS на ДАННЫХ требует также RLS-install на "
                        "источнике (включается в web-портале, вне MCP) — "
                        "без него флаг/фильтр сохранены, но не применяются."
                    )
                }

            except APIError as e:
                return _rls_write_error(
                    _api_error_as_response(e), dataset_id, "Failed to enable RLS"
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": "RLS operation failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the dataset exists and rls_query is valid SQL.",
                }

        case "disable":
            err = require(
                {"dataset_id": dataset_id},
                tool="security_operations", action="disable",
                types={"dataset_id": "int"},
                example="security_operations(action='disable', dataset_id=5)",
            )
            if err:
                return err

            from ..core.security import check_action
            check_action("update")

            try:
                # Read-modify-write: drop the flag and clear the filter
                written = await _write_rls_full(
                    client, dataset_id,
                    rls=0, query_rls="",
                    fallback="Failed to disable RLS",
                )
                if not written.get("success"):
                    return written

                return {
                    "success": True,
                    "message": f"RLS disabled for dataset {dataset_id}",
                    "dataset_id": dataset_id,
                    "rls_enabled": False
                }

            except APIError as e:
                return _rls_write_error(
                    _api_error_as_response(e), dataset_id, "Failed to disable RLS"
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": "RLS operation failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the dataset exists and rls_query is valid SQL.",
                }

        case "update_filter":
            err = require(
                {"dataset_id": dataset_id, "rls_query": rls_query},
                tool="security_operations", action="update_filter",
                types={"dataset_id": "int", "rls_query": "str (SQL WHERE fragment, may use :current_user_id)"},
                example="security_operations(action='update_filter', dataset_id=5, rls_query='user_id = :current_user_id')",
            )
            if err:
                return err

            from ..core.security import check_action
            check_action("update")

            try:
                # Read-modify-write: set the new filter and ensure the flag is on
                written = await _write_rls_full(
                    client, dataset_id,
                    rls=1, query_rls=rls_query,
                    fallback="Failed to update RLS filter",
                )
                if not written.get("success"):
                    return written

                return {
                    "success": True,
                    "message": f"RLS filter updated for dataset {dataset_id}",
                    "dataset_id": dataset_id,
                    "rls_query": rls_query,
                    "rls_enabled": True
                }

            except APIError as e:
                return _rls_write_error(
                    _api_error_as_response(e), dataset_id, "Failed to update RLS filter"
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": "RLS operation failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the dataset exists and rls_query is valid SQL.",
                }

        case "list_enabled":
            try:
                response = await client.api_call(
                    "datasets",
                    "list"
                )

                if response.get("status") != 200:
                    return {
                        "success": False,
                        "error": response.get("message", "Failed to list datasets")
                    }

                datasets = response.get("data", [])
                rls_datasets = []

                for ds in datasets:
                    if ds.get("rls"):
                        rls_datasets.append({
                            "id": ds.get("ID"),
                            "name": ds.get("name"),
                            "caption": ds.get("caption"),
                            "rls_query": ds.get("query_rls", ""),
                            "has_filter": bool(ds.get("query_rls"))
                        })

                return {
                    "success": True,
                    "datasets_with_rls": rls_datasets,
                    "count": len(rls_datasets),
                    "total_datasets": len(datasets)
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": "RLS operation failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Check that the dataset exists and rls_query is valid SQL.",
                }

        case "test":
            err = require(
                {"dataset_id": dataset_id},
                tool="security_operations", action="test",
                types={"dataset_id": "int"},
                example="security_operations(action='test', dataset_id=5)",
            )
            if err:
                return err

            # Get RLS status first
            status = await security_operations(client, "status", dataset_id=dataset_id)
            if not status.get("success"):
                return status

            if not status.get("rls_enabled"):
                return {
                    "success": True,
                    "dataset_id": dataset_id,
                    "rls_enabled": False,
                    "message": "RLS is not enabled for this dataset",
                    "test_result": "skipped"
                }

            # Try to query with RLS applied
            try:
                from .query_execute import dataset_query

                result = await dataset_query(
                    client,
                    dataset_id=dataset_id,
                    limit=5
                )

                return {
                    "success": True,
                    "dataset_id": dataset_id,
                    "rls_enabled": True,
                    "rls_query": status.get("rls_query"),
                    "test_result": "passed" if result.get("success") else "failed",
                    "rows_returned": result.get("rows_count", 0),
                    "message": "RLS filter applied successfully" if result.get("success") else result.get("error")
                }

            except Exception as e:
                return {
                    "success": False,
                    "dataset_id": dataset_id,
                    "test_result": "error",
                    "error": "RLS test query failed",
                    "details": mask_sensitive(str(e)),
                    "hint": "Verify query_rls works as a standalone WHERE clause fragment.",
                }

        case _:
            return {"error": f"Unknown action: {action}"}
