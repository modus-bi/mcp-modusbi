"""
Query execution for MCP Server.

Operations:
- dataset_query: Get data from dataset using recordsets.create
- query_batch: Execute multiple queries on dataset
- sql_query_validate: Validate SQL query and get result fields
- dataset_create_from_sql: Create dataset with semantic layer from SQL
- preflight_check_datasource: Check if datasource can actually execute queries
"""

import logging
import re

from typing import Any
import httpx

from ..core.exceptions import mask_sensitive, require
from ..core.security import get_security_mode, SecurityMode, get_demo_limit

logger = logging.getLogger(__name__)


async def preflight_check_datasource(client, datasource_id: int) -> dict[str, Any]:
    """
    Preflight check: verify datasource can actually execute queries.

    This goes beyond check_connection by actually trying a simple query.
    Use this before expensive operations to fail fast with clear error.

    Args:
        client: InstanceClient
        datasource_id: Datasource ID to check

    Returns:
        {success: True/False, connected: bool, can_query: bool, error?: str}
    """
    # Step 1: Basic connection check
    try:
        conn_response = await client.api_call(
            "datasources",
            "check.conn",
            object_id=datasource_id
        )

        connected = conn_response.get("status") == 200

        if not connected:
            return {
                "success": False,
                "datasource_id": datasource_id,
                "connected": False,
                "can_query": False,
                "error": f"Datasource {datasource_id} connection failed",
                "hint": "Check datasource configuration in ModusBI portal"
            }
    except Exception as e:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "connected": False,
            "can_query": False,
            "error": "Connection check failed",
            "details": mask_sensitive(str(e)),
            "hint": "Check datasource credentials/host via datasource_operations(action='get').",
        }

    # Step 2: Try a simple SQL query to verify actual query execution works
    try:
        instance = client.instance
        query_url = f"{instance.base_url.rstrip('/')}/v1/api/query"

        test_payload = {
            "ID": 0,
            "cached": 0,
            "caption": "_preflight_test",
            "count": 0,
            "datacorrection_active": 0,
            "driverID": datasource_id,
            "fields": [],
            "fields_ref": [],
            "limit": 1,
            "mdx": 0,
            "name": "_preflight_test",
            "parentID": 1,
            "query": "SELECT 1 as test",
            "query_rls": "",
            "rls": 0,
            "size": 0,
            "url": ""
        }

        response = await client.raw_post(
            query_url,
            json=test_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {instance.token}"
            },
            timeout=10.0
        )

        can_query = response.status_code == 200

        if not can_query:
            return {
                "success": False,
                "datasource_id": datasource_id,
                "connected": True,
                "can_query": False,
                "error": f"Datasource connected but queries fail (HTTP {response.status_code})",
                "hint": "Database may be unreachable or credentials invalid"
            }

        return {
            "success": True,
            "datasource_id": datasource_id,
            "connected": True,
            "can_query": True,
            "message": "Datasource is fully operational"
        }

    except httpx.TimeoutException:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "connected": True,
            "can_query": False,
            "error": "Query timeout - database may be slow or unreachable"
        }
    except Exception as e:
        return {
            "success": False,
            "datasource_id": datasource_id,
            "connected": True,
            "can_query": False,
            "error": "Query test failed",
            "details": mask_sensitive(str(e)),
            "hint": "Datasource connects but SQL execution fails. Check driver, SQL dialect, or table permissions.",
        }


async def query_batch(
    client,
    dataset_id: int,
    queries: list[dict]
) -> dict[str, Any]:
    """
    Execute multiple queries on a dataset in a single request.

    Each query in the list should have:
    - id: Unique identifier for the query (string)
    - params: Query parameters (select, where, group, order, etc.)

    Example queries:
    [
        {"id": "total_sales", "params": {"select": [{"name": "amount", "aggr": "sum"}]}},
        {"id": "by_region", "params": {"select": [...], "group": [{"name": "region"}]}}
    ]

    Args:
        client: InstanceClient
        dataset_id: Dataset ID
        queries: List of queries with id and params

    Returns:
        Batch results with each query's data
    """
    if not queries:
        return {"success": False, "error": "No queries provided"}

    # Apply demo limits
    max_queries = 10
    if get_security_mode() == SecurityMode.DEMO:
        max_queries = 5

    if len(queries) > max_queries:
        return {
            "success": False,
            "error": f"Too many queries. Max allowed: {max_queries}"
        }

    # Build batch request
    batch_data = []
    for q in queries:
        query_id = q.get("id")
        params = q.get("params", {})

        if not query_id:
            return {"success": False, "error": "Each query must have an 'id'"}

        batch_data.append({
            "call_id": str(query_id),
            "call_params": params
        })

    try:
        response = await client.api_call(
            "recordsets",
            "recordset.batch",
            object_id=dataset_id,
            data=batch_data
        )

        if response.get("status") != 200:
            return {
                "success": False,
                "error": response.get("message", "Batch execution failed"),
                "dataset_id": dataset_id
            }

        results = []
        for item in response.get("data", []):
            call_id = item.get("call_id")
            call_error = item.get("call_error", 0)
            call_message = item.get("call_message", "")
            call_result = item.get("call_result", [])

            if call_error:
                results.append({
                    "id": call_id,
                    "success": False,
                    "error": call_message
                })
            else:
                # Extract data from result
                if call_result and isinstance(call_result, list) and call_result:
                    result_data = call_result[0] if len(call_result) == 1 else call_result
                    if isinstance(result_data, dict):
                        fields = result_data.get("fields", [])
                        rows = result_data.get("rows", result_data.get("data", []))
                    else:
                        fields = []
                        rows = call_result
                else:
                    fields = []
                    rows = []

                results.append({
                    "id": call_id,
                    "success": True,
                    "fields": [
                        {
                            "name": f.get("name") if isinstance(f, dict) else f,
                            "type": f.get("type") if isinstance(f, dict) else "unknown"
                        }
                        for f in fields
                    ] if fields else [],
                    "rows": rows,
                    "rows_count": len(rows) if isinstance(rows, list) else 0
                })

        # The backend may answer status:200 with an empty data[] on a
        # contract-valid batch. Without this check the tool would return
        # success:true with results:[], which misrepresents the outcome.
        # Hard-fail ONLY on that signature (results empty); a non-empty
        # results where every query legitimately matched zero rows is NOT
        # necessarily this case — keep success:true with a warning instead.
        if not results:
            return {
                "success": False,
                "dataset_id": dataset_id,
                "queries_count": len(queries),
                "results": results,
                "error": "portal returned empty data",
                "warning": (
                    "portal returned empty data; use dataset_query per query"
                ),
                "hint": (
                    "The batch path (recordsets.recordset.batch) may return "
                    "200 + empty data. Run dataset_query("
                    "dataset_id=..., select=..., group=...) once per query — "
                    "the single-query path is confirmed working."
                ),
            }

        has_any_rows = any(
            item.get("success") and item.get("rows_count", 0) > 0
            for item in results
        )
        has_errors = any(not item.get("success") for item in results)
        all_failed = results and all(not item.get("success") for item in results)
        envelope: dict[str, Any] = {
            # все под-запросы упали → честный success:false
            "success": not all_failed,
            "dataset_id": dataset_id,
            "queries_count": len(queries),
            "results": results,
        }
        if all_failed:
            envelope["error"] = "all batch sub-queries failed"
            envelope["hint"] = ("Inspect results[].error; run dataset_query "
                                "per query to isolate the failing one.")
        elif has_errors:
            envelope["warning"] = (
                "some batch sub-queries failed — inspect results[].error"
            )
        if not has_any_rows and not has_errors:
            envelope["warning"] = (
                "all queries returned 0 rows — may be a legitimate empty "
                "result or an empty batch response; cross-check one query "
                "via dataset_query"
            )
        return envelope

    except Exception as e:
        return {
            "success": False,
            "error": "Batch query failed",
            "details": mask_sensitive(str(e)),
            "dataset_id": dataset_id,
            "hint": "Inspect individual query via dataset_query to isolate which filter/field fails.",
        }


async def _get_driver_id_from_datasource(
    client, datasource_id: int
) -> tuple[int, dict[str, Any] | None, str | None]:
    """
    Get driver ID (type) from datasource.

    In ModusBI, datasources are organized hierarchically:
    - datasource.parent_id = driver type (e.g., 20 = PostgreSQL, 50 = ClickHouse)
    - datasource.id = connection ID

    Note: We use list API because get API doesn't return parentID field.

    Returns:
        Tuple of (driver_id, datasource_record, error_message). The record is
        None on error; callers use it for diagnostics (e.g. detecting a system
        metadata datasource that cannot back an ad-hoc SQL dataset).
    """
    try:
        # Use list API to get parentID (get API doesn't include it)
        response = await client.api_call("datasources", "list")

        if response.get("status") != 200:
            return 0, None, "Failed to get datasources list"

        datasources = response.get("data", [])

        # Find the datasource by ID
        for ds in datasources:
            if ds.get("ID") == datasource_id:
                # parentID in datasource = driver type (e.g., 20 for PostgreSQL)
                driver_id = ds.get("parentID", 0)
                return driver_id, ds, None

        return 0, None, f"Datasource {datasource_id} not found in list"

    except Exception as e:
        return 0, None, str(e)


# Datasource names that identify the internal portal metadata store. SQL-backed
# ad-hoc datasets cannot be created against it (backend rejects with HTTP 400).
_METADATA_DS_MARKERS = ("метаданные", "metadata")


def _is_metadata_datasource(ds_record: dict[str, Any] | None) -> bool:
    """Heuristic: True if the datasource is the system metadata store."""
    if not ds_record:
        return False
    name = (ds_record.get("name") or ds_record.get("caption") or "").strip().lower()
    return any(marker in name for marker in _METADATA_DS_MARKERS)


# --- SELECT-only guard -------------------------------------------------------
#
# The portal endpoint /v1/api/query "validates" SQL by EXECUTING it on the
# live datasource. There is NO sandbox: DML/DDL sent there reaches the
# database and mutates data. The guard below runs on the MCP side BEFORE the
# raw call and allows exactly ONE statement that is a plain SELECT
# (or WITH ... SELECT).

# String literals, dollar-quoted strings, quoted identifiers and comments are
# stripped BEFORE keyword analysis, so the word UPDATE inside a literal does
# not trigger a false positive and a semicolon inside a literal is not
# treated as a statement separator.
_SQL_NOISE_RE = re.compile(
    r"--[^\n]*"                                                # line comment
    r"|/\*.*?\*/"                                              # block comment
    r"|\$\$.*?\$\$"                                            # untagged $$...$$ string
    r"|\$(?P<tag>[A-Za-z_][A-Za-z0-9_]*)\$.*?\$(?P=tag)\$"     # tagged $x$...$x$ string
    r"|[eE]'(?:[^'\\]|\\.|'')*'"                               # E'...' string (escapes)
    r"|'(?:[^']|'')*'"                                         # standard '...' string
    r'|"(?:[^"]|"")*"',                                        # quoted identifier
    re.DOTALL,
)

# Statement-level keywords that must never reach the executing endpoint.
# Checked as whole words on the stripped SQL: also catches DML inside
# WITH-CTEs (data-modifying CTE) and SELECT ... INTO (creates a table).
_SQL_FORBIDDEN_WORDS = frozenset({
    "insert", "update", "delete", "merge", "into",
    "drop", "alter", "create", "truncate", "grant", "revoke",
})

_SQL_WORD_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")

_SQL_GUARD_HINT = (
    "sql_query_validate is NOT a sandbox: the portal validates by EXECUTING "
    "the query on the live datasource. Send exactly one SELECT "
    "(or WITH ... SELECT) statement; DML/DDL and multi-statement SQL are "
    "rejected on the MCP side. If a column name collides with a SQL keyword "
    '(e.g. "update"), double-quote it.'
)


def _sql_select_only_guard(sql_query: str) -> dict[str, Any] | None:
    """
    MCP-side pre-send guard: allow exactly ONE statement and only
    SELECT / WITH ... SELECT.

    Returns an error envelope {success: False, error, details, hint} on
    violation, or None when the SQL is safe to send to the portal.
    """
    cleaned = _SQL_NOISE_RE.sub(" ", sql_query or "")

    statements = [s for s in cleaned.split(";") if s.strip()]

    if not statements:
        return {
            "success": False,
            "error": "only single SELECT allowed",
            "details": "no SQL statement found",
            "hint": _SQL_GUARD_HINT,
            "query": (sql_query or "")[:100],
        }

    if len(statements) > 1:
        return {
            "success": False,
            "error": "only single SELECT allowed",
            "details": f"multi-statement SQL detected ({len(statements)} statements)",
            "hint": _SQL_GUARD_HINT,
            "query": sql_query[:100],
        }

    stmt = statements[0]
    # Leading "(" is legal read-only SQL: "(SELECT 1) UNION ALL (SELECT 2)".
    first_word_match = re.match(r"[\s(]*([A-Za-z_]+)", stmt)
    first_word = first_word_match.group(1).lower() if first_word_match else ""

    if first_word not in ("select", "with"):
        return {
            "success": False,
            "error": "only single SELECT allowed",
            "details": (
                f"statement starts with '{first_word.upper() or '?'}', "
                f"expected SELECT or WITH"
            ),
            "hint": _SQL_GUARD_HINT,
            "query": sql_query[:100],
        }

    forbidden = sorted(
        {w.lower() for w in _SQL_WORD_RE.findall(stmt)} & _SQL_FORBIDDEN_WORDS
    )
    if forbidden:
        return {
            "success": False,
            "error": "only single SELECT allowed",
            "details": (
                f"forbidden keyword(s) in statement: "
                f"{', '.join(w.upper() for w in forbidden)}"
            ),
            "hint": _SQL_GUARD_HINT,
            "query": sql_query[:100],
        }

    return None


async def sql_query_validate(
    client,
    sql_query: str,
    datasource_id: int = 1,
    dataset_name: str = "temp_validation"
) -> dict[str, Any]:
    """
    Validate SQL query and get result fields structure.

    Uses /v1/api/query endpoint to validate SQL query and
    determine the fields (columns) that will be returned.

    This is useful for:
    - Checking SQL syntax before saving dataset
    - Getting field types and names from query result
    - Previewing dataset structure

    SECURITY: the portal endpoint is NOT a sandbox — it validates by
    EXECUTING the query on the live datasource. MCP therefore allows only a
    SINGLE SELECT (or WITH ... SELECT) statement; DML/DDL and multi-statement
    SQL are rejected here before reaching the portal.

    Args:
        client: InstanceClient
        sql_query: SQL query to validate
        datasource_id: Datasource ID (connection ID)
        dataset_name: Temporary name for validation (not saved)

    Returns:
        Validation result with fields structure

    Example:
        result = await sql_query_validate(
            client,
            sql_query="SELECT id, name, created_at FROM users LIMIT 10",
            datasource_id=1
        )
        # Returns: {success: True, fields: [{name: "id", type: "number"}, ...]}
    """
    # guard: the portal EXECUTES whatever SQL it receives, so DML/DDL and
    # multi-statement input must never leave the MCP. Checked before any
    # portal round-trip.
    guard_error = _sql_select_only_guard(sql_query)
    if guard_error:
        return guard_error

    # Get driver_id from datasource
    driver_id, _ds_record, error = await _get_driver_id_from_datasource(client, datasource_id)
    if error:
        return {
            "success": False,
            "error": f"Failed to get datasource info: {error}",
            "datasource_id": datasource_id
        }

    # Build dataset structure for validation
    # parentID = datasource_id (connection ID)
    # driverID = driver type from datasource.parent_id
    validation_payload = {
        "ID": 0,  # New dataset
        "cached": 0,
        "caption": dataset_name,
        "count": 0,
        "datacorrection_active": 0,
        "driverID": driver_id,  # Driver type (e.g., 20 for PostgreSQL)
        "fields": [],
        "fields_ref": [],
        "limit": 100,
        "mdx": 0,
        "name": dataset_name,
        "parentID": datasource_id,  # Datasource connection ID
        "query": sql_query,
        "query_rls": "",
        "rls": 0,
        "size": 0,
        "url": ""
    }

    try:
        # Call query validation endpoint directly
        instance = client.instance
        query_url = f"{instance.base_url.rstrip('/')}/v1/api/query"

        response = await client.raw_post(
            query_url,
            json=validation_payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {instance.token}"
            },
            timeout=30.0
        )

        if response.status_code != 200:
            # Тело ответа содержит реальную причину (синтаксис/runtime/DDL) —
            # без него пользователь видел голое «HTTP 500».
            try:
                body_msg = (response.json().get("message") or "")[:300]
            except Exception:
                body_msg = ""
            if not body_msg:
                body_msg = (response.text or "")[:200]
            envelope = {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "query": sql_query[:100]
            }
            if body_msg:
                envelope["details"] = mask_sensitive(body_msg)
                envelope["hint"] = ("Сообщение портала в details: проверьте "
                                    "синтаксис SQL и существование таблиц/колонок.")
            return envelope

        data = response.json()

        # Check for API-level errors
        if data.get("status") and data.get("status") != 200:
            return {
                "success": False,
                "error": data.get("message", "Query validation failed"),
                "query": sql_query[:100]
            }

        # Extract fields from response
        fields = data.get("fields", [])

        return {
            "success": True,
            "valid": True,
            "fields": [
                {
                    "id": f.get("ID"),
                    "name": f.get("name"),
                    "alias": f.get("alias"),
                    "type": f.get("type"),
                    "description": f.get("description", "")
                }
                for f in fields
            ],
            "fields_count": len(fields),
            "query_preview": sql_query[:200] + "..." if len(sql_query) > 200 else sql_query,
            "datasource_id": datasource_id
        }

    except httpx.RequestError as e:
        return {
            "success": False,
            "error": "Connection error while validating SQL",
            "details": mask_sensitive(str(e)),
            "hint": "The datasource is unreachable; run preflight_check_datasource to diagnose.",
            "query": sql_query[:100],
        }
    except Exception as e:
        return {
            "success": False,
            "error": "SQL validation failed",
            "details": mask_sensitive(str(e)),
            "hint": "Check SQL syntax and referenced table/column names.",
            "query": sql_query[:100],
        }


async def dataset_query(
    client,
    dataset_id: int,
    select: list[dict] | None = None,
    where: list[dict] | None = None,
    group: list[dict] | None = None,
    order: list[dict] | None = None,
    limit: int = 1000,
    variables: dict[str, list] | None = None
) -> dict[str, Any]:
    """
    Query data from a dataset using recordsets API.

    This is the correct way to get data from ModusBI.
    Raw SQL execution on datasources is NOT supported by the API.

    Args:
        client: InstanceClient
        dataset_id: Dataset ID (NOT datasource_id!)
        select: Fields to select, e.g. [{"name": "amount", "aggr": "sum"}]
        where: Filter conditions
        group: Grouping fields
        order: Ordering fields
        limit: Max rows (default 1000); 0 = no rows (like SQL LIMIT 0), negative rejected
        variables: SQL variables for :variable_name substitution in dataset query.
            Format: {"var_name": ["value1", "value2"]}

    Returns:
        Query results with fields and rows

    Example:
        # Get all data from dataset
        result = await dataset_query(client, dataset_id=5)

        # Get aggregated data
        result = await dataset_query(
            client,
            dataset_id=5,
            select=[{"name": "region"}, {"name": "amount", "aggr": "sum"}],
            group=[{"name": "region"}]
        )

        # Query with SQL variables
        result = await dataset_query(
            client,
            dataset_id=42,
            variables={"region": ["Moscow"], "year": [2024]}
        )
    """
    # отрицательный limit отклоняем до похода в портал (иначе срезает
    # последнюю строку и даёт ложный truncated:true).
    if limit is not None and limit < 0:
        return {
            "success": False,
            "error": "limit must be >= 0",
            "dataset_id": dataset_id,
            "hint": (
                "limit=0 вернёт 0 строк (как SQL LIMIT 0); положительный "
                "limit ограничивает выборку; default 1000."
            ),
        }

    # Apply demo limits
    requested_limit = limit
    demo_capped = False
    if get_security_mode() == SecurityMode.DEMO:
        max_rows = get_demo_limit("max_query_rows")
        if limit > max_rows:
            limit = max_rows
            demo_capped = True

    # Build query params according to API documentation
    # Convert simplified format to full recordsets.create format

    # Transform select fields to full format
    # Input: [{"name": "region"}, {"name": "amount", "aggr": "sum"}]
    # Output: [{"lvl": 0, "name": "region", "alias": "[values][0]", "calc": "", "aggr": "", "fieldAlias": "region"}, ...]
    full_select = []
    if select:
        for idx, field in enumerate(select):
            field_name = field.get("name", "")
            aggr = field.get("aggr", "")
            full_select.append({
                "lvl": 0,
                "name": field_name,
                "alias": f"[values][{idx}]",
                "calc": field.get("calc", ""),
                "aggr": aggr,
                "fieldAlias": field_name
            })

    # Transform group fields to full format
    # Input: [{"name": "region"}]
    # Output: [{"name": "region", "calc": "", "alias": "[categories]"}]
    full_group = []
    if group:
        for field in group:
            field_name = field.get("name", "")
            full_group.append({
                "name": field_name,
                "calc": field.get("calc", ""),
                "alias": "[categories]"
            })

    # Transform order fields.
    # Портал читает ключ "direction" (не "dir") — со старым ключом
    # сортировка всегда ASC; и отбрасывает условие с пустым alias.
    # Автоподставляем alias из select ([values][idx]) / group ([categories]).
    # first-wins при дублях имён в select — консистентно с name-based
    # резолвом портала (берётся первое вхождение).
    _order_alias_by_name: dict[str, str] = {}
    for idx, f in enumerate(select or []):
        _order_alias_by_name.setdefault(f.get("name", ""), f"[values][{idx}]")
    for f in (group or []):
        _order_alias_by_name.setdefault(f.get("name", ""), "[categories]")
    full_order = []
    if order:
        for field in order:
            fname = field.get("name", "")
            direction = str(field.get("direction") or field.get("dir", "asc")).lower()
            # портал интерполирует direction в SQL как есть — белый список
            if direction not in ("asc", "desc"):
                direction = "asc"
            alias = (field.get("alias")
                     or _order_alias_by_name.get(fname)
                     or fname)
            full_order.append({
                "name": fname,
                "alias": alias,
                "direction": direction,
                # старый ключ оставляем для совместимости со старыми порталами
                "dir": direction,
            })

    # Transform where fields to full format
    # Input: [{"name": "status", "op": "=", "value": "completed"}]
    # Output: [{"lvl": 0, "name": "status", "not": false, "values": ["completed"], "operators": ["="], "logicOr": 0}]
    full_where = []
    if where:
        for cond in where:
            # Support both simplified and full format
            if "values" in cond and "operators" in cond:
                # Already in full format
                full_where.append(cond)
                continue
            # Convert simplified format
            op = cond.get("oper") or cond.get("op", "=")
            op_norm = " ".join(str(op).lower().split())
            if op_norm in ("is", "is not", "is null", "is not null"):
                # NULL-проверка. Литеральный JSON null внутри values
                # включает флаг Null (values остаётся пустым), "not": true
                # даёт IS NOT NULL. Без флага портал отбрасывает условие
                # (нет значений и нет Null-флага → пропуск).
                if cond.get("value") not in (None, ""):
                    # op='is' + непустое value — несовместимы: иначе value
                    # отбрасывается и условие превращается в IS NULL,
                    # подменяя семантику. Отклоняем громко.
                    return {
                        "success": False,
                        "error": (
                            f"where: op={op!r} — это NULL-проверка "
                            f"(IS [NOT] NULL); value="
                            f"{cond.get('value')!r} с ней не сочетается"
                        ),
                        "dataset_id": dataset_id,
                        "hint": (
                            "Для сравнения со значением используйте "
                            "op '='/'!='; для NULL-проверки уберите value."
                        ),
                    }
                full_where.append({
                    "lvl": cond.get("lvl", 0),
                    "name": cond.get("name", ""),
                    "not": op_norm in ("is not", "is not null"),
                    "values": [None],
                    "operators": [],
                    "logicOr": cond.get("logicOr", 0)
                })
                continue
            val = cond.get("value")
            if val is None and op_norm in ("=", "!=", "<>"):
                # естественное альтернативное написание NULL-проверки
                # ({'op':'=','value':None}; exclude_none в server.py вообще
                # выбрасывает ключ value). Без этой ветки уходило бы
                # values:[] и портал отбросил бы условие (потеря фильтра).
                full_where.append({
                    "lvl": cond.get("lvl", 0),
                    "name": cond.get("name", ""),
                    "not": op_norm in ("!=", "<>"),
                    "values": [None],
                    "operators": [],
                    "logicOr": cond.get("logicOr", 0)
                })
                continue
            full_where.append({
                "lvl": cond.get("lvl", 0),
                "name": cond.get("name", ""),
                "not": cond.get("not", False),
                # 0/False — валидные значения фильтра: проверяем на None,
                # а не truthiness (иначе value=0 терялся бы как values:[])
                "values": [val] if val is not None else [],
                "operators": [op],
                "logicOr": cond.get("logicOr", 0)
            })

    params = {
        "select": full_select,
        "where": full_where,
        "group": full_group,
        "order": full_order,
        "having": {"condition": ""},
        "series": {"enable": 0}
    }
    if limit is not None:
        # limit=0 валиден (как SQL LIMIT 0). Портал трактует
        # limit<=0 как «без ограничения», поэтому для 0 запрашиваем
        # минимум (1 строку) и режем до нуля на нашей стороне.
        params["limit"] = limit if limit > 0 else 1

    if variables:
        params["variables"] = [
            {"name": name, "values": vals if isinstance(vals, list) else [vals]}
            for name, vals in variables.items()
            if name and vals is not None
        ]

    try:
        # Use recordsets.create - the correct API command
        # URL: /v1/api/recordsets/{dataset_id}
        response = await client.api_call(
            "recordsets",
            "create",
            object_id=dataset_id,
            data=[params]
        )

        # Response can be:
        # 1. List of rows directly (when using direct params)
        # 2. Dict with {status, data} (when using wrapped params)
        if isinstance(response, list):
            # Direct response - rows array
            rows = response
        elif isinstance(response, dict):
            if response.get("status") and response.get("status") != 200:
                status = response.get("status")
                error_msg = response.get("message", "Query execution failed")

                hints = []
                if status == 500:
                    hints = [
                        "The datasource for this dataset may be unavailable",
                        "Use datasource_operations(action='check_connection', datasource_id=X) to verify"
                    ]
                elif status == 404:
                    hints = [f"Dataset {dataset_id} may not exist"]
                elif status == 403:
                    hints = ["Permission denied - check RLS settings"]

                return {
                    "success": False,
                    "error": f"Ошибка API: HTTP {status}" if status else error_msg,
                    "dataset_id": dataset_id,
                    "hints": hints if hints else None
                }
            rows = response.get("data", [])
        else:
            rows = []

        # Rows are list of dicts like {"field_name": value, ...}
        if not rows:
            result = {
                "success": True,
                "dataset_id": dataset_id,
                "fields": [],
                "rows": [],
                "rows_count": 0,
                "truncated": False
            }
            if demo_capped:
                result["demo_capped"] = True
                result["requested_limit"] = requested_limit
                result["effective_limit"] = limit
                result["note"] = (
                    f"DEMO mode: row limit capped {requested_limit} → {limit} "
                    f"(max_query_rows). Run with --readwrite/--readonly for full results."
                )
            return result

        # Extract field names from first row (or use select parameter)
        if isinstance(rows[0], dict):
            field_names = list(rows[0].keys())
            fields = [{"name": fn, "alias": fn, "type": "unknown"} for fn in field_names]
        else:
            fields = []
            field_names = []

        # limit=0 — честные 0 строк; сравнение с None вместо truthy
        # (иначе 0 → falsy → все строки, -1 → rows[:-1] + ложный truncated)
        returned_rows = rows[:limit] if limit is not None else rows
        result = {
            "success": True,
            "dataset_id": dataset_id,
            "fields": fields,
            "rows": returned_rows,
            "rows_count": len(returned_rows),
            # limit=0 — пользователь явно запросил 0 строк (метаданные),
            # ничего не «усечено»; truncated только при положительном лимите.
            "truncated": limit is not None and limit > 0 and len(rows) > limit
        }
        if demo_capped:
            # DEMO cap is itself a form of truncation: the user asked for more
            # rows than the mode allows, so surface it explicitly instead of a
            # silent truncated:false (the backend already returned ≤ limit rows).
            result["truncated"] = True
            result["demo_capped"] = True
            result["requested_limit"] = requested_limit
            result["effective_limit"] = limit
            result["note"] = (
                f"DEMO mode: row limit capped {requested_limit} → {limit} "
                f"(max_query_rows). Run with --readwrite/--readonly for full results."
            )
        return result

    except Exception as e:
        return {
            "success": False,
            "error": "dataset_query failed",
            "details": mask_sensitive(str(e)),
            "dataset_id": dataset_id,
            "hint": "Run sql_query_validate on the dataset SQL or check preflight_check_datasource.",
        }


async def dataset_create_from_sql(
    client,
    sql_query: str,
    datasource_id: int,
    name: str,
    caption: str | None = None
) -> dict[str, Any]:
    """
    Create dataset from SQL query with semantic layer (fields).

    This is the full workflow for creating a dataset:
    1. Get driver_id from datasource (datasource.parent_id = driver type)
    2. Validate SQL query via /v1/api/query → get fields structure
    3. Create dataset via /v1/api/datasets with 'update' command

    Args:
        client: InstanceClient
        sql_query: SQL query for the dataset
        datasource_id: Datasource ID (connection ID)
        name: Dataset name
        caption: Dataset caption (defaults to name)

    Returns:
        Created dataset info with ID and fields

    Example:
        result = await dataset_create_from_sql(
            client,
            sql_query="SELECT id, name, amount FROM sales WHERE status = 'active'",
            datasource_id=1,  # Connection ID, not driver type!
            name="sales_data",
            caption="Sales Dataset"
        )
    """
    # пустое/пробельное имя отклоняем require-конвертом до похода
    # в портал — иначе уходит в create и возвращается как голое
    # «HTTP 400 on create» с нерелевантным hint про datasource.
    guard = require(
        {"name": (name or "").strip() if isinstance(name, str) else name},
        tool="dataset_create_from_sql",
        example=("dataset_create_from_sql(sql_query='SELECT ...', "
                 "datasource_id=1, name='sales_data')"),
        types={"name": "str"},
    )
    if guard:
        return guard
    if isinstance(name, str):
        # имя уходит на портал уже без обрамляющих пробелов
        name = name.strip()

    # Step 1: Get driver_id from datasource
    driver_id, ds_record, error = await _get_driver_id_from_datasource(client, datasource_id)
    if error:
        return {
            "success": False,
            "error": f"Failed to get datasource info: {error}",
            "datasource_id": datasource_id,
            "step": "get_driver"
        }

    # Guard: the system "Метаданные" datasource is the portal's internal
    # metadata store, not a queryable SQL backend. Creating an ad-hoc SQL
    # dataset against it fails downstream with an opaque HTTP 400, so reject
    # it up-front with an actionable message.
    if _is_metadata_datasource(ds_record):
        ds_name = ds_record.get("name") or ds_record.get("caption") or "Метаданные"
        return {
            "success": False,
            "error": (
                f"Datasource {datasource_id} ('{ds_name}') is the system metadata "
                f"store and does not support ad-hoc SQL datasets."
            ),
            "datasource_id": datasource_id,
            "step": "validate_datasource",
            "hint": (
                "Pick a real database datasource (PostgreSQL/ClickHouse/etc.). "
                "Run datasource_operations(action='list') to see queryable connections."
            ),
        }

    # Step 2: Validate SQL and get fields
    validation = await sql_query_validate(
        client,
        sql_query=sql_query,
        datasource_id=datasource_id,
        dataset_name=name
    )

    if not validation.get("success"):
        envelope = {
            "success": False,
            "error": f"SQL validation failed: {validation.get('error')}",
            "step": "validation"
        }
        # Keep the guard's diagnostics (e.g. quoting workaround for
        # keyword-named columns) instead of swallowing them on this path.
        for key in ("details", "hint"):
            if validation.get(key):
                envelope[key] = validation[key]
        return envelope

    validated_fields = validation.get("fields", [])

    # Step 3: Build fields in API format
    # The API returns field names from AS clause in SQL
    # name = AS alias from SQL (technical name in dataset, used for field_aliases)
    # alias = empty by default (user sets via field_aliases for human-readable display)
    # description = empty by default (user sets via field_aliases for semantic layer)
    #
    # DON'T use SQL parsing to extract original column names - that breaks field_aliases!
    # User writes: SELECT region, SUM(amount) AS total FROM ...
    # API returns: name="total" (from AS clause)
    # This is correct! field_aliases uses "total" as key, not "amount"
    api_fields = []
    for f in validated_fields:
        field_name = f.get("name", "")

        api_fields.append({
            "ID": f.get("id", 0),
            "name": field_name,   # AS alias from SQL - this is the field key for field_aliases
            "alias": "",          # Empty - user sets via field_aliases
            "type": f.get("type", "string"),
            "description": "",    # Empty - user sets via field_aliases
            "bk": False,
            "correctable": False,
            "expression": [],
            "prop": {
                "date": "",
                "ext": "",
                "fileName": "",
                "size": ""
            }
        })

    # Step 4: Create dataset in two steps:
    # 4a. First create empty dataset with minimal data
    # 4b. Then update with full data (query, fields, etc.)
    #
    # IMPORTANT field mapping:
    # - parentID = datasource_id (connection ID, links dataset to datasource)
    # - driverID = driver type from datasource.parent_id (e.g., 20 = PostgreSQL)

    try:
        instance = client.instance
        datasets_url = f"{instance.base_url.rstrip('/')}/v1/api/datasets"

        # Step 4a: Create empty dataset
        create_data = {
            "command": {"name": "create"},
            "object": {"name": "datasets"},
            "data": [{
                "parentID": datasource_id,  # Datasource connection ID
                "name": name,
                "caption": caption or name
            }]
        }

        create_response = await client.raw_post(
            datasets_url,
            json=create_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {instance.token}"
            },
            timeout=30.0
        )

        if create_response.status_code != 200:
            # Тело ответа содержит реальную причину отказа (имя/права/источник) —
            # без него пользователь видел голое «HTTP 400» с hint про datasource,
            # даже когда причина была иной.
            try:
                body_msg = (create_response.json().get("message") or "")[:300]
            except Exception:
                body_msg = ""
            if not body_msg:
                body_msg = (create_response.text or "")[:200]
            result = {
                "success": False,
                "error": f"HTTP {create_response.status_code} on create",
                "datasource_id": datasource_id,
                "step": "create_dataset"
            }
            if body_msg:
                result["details"] = mask_sensitive(body_msg)
                result["hint"] = ("Сообщение портала в details: проверьте имя "
                                  "датасета и параметры источника.")
            elif create_response.status_code == 400:
                result["hint"] = (
                    "Datasource may not support ad-hoc SQL datasets (e.g. a system/"
                    "metadata source). Verify with datasource_operations(action='list') "
                    "and pick a queryable database connection."
                )
            return result

        create_result = create_response.json()
        if create_result.get("status") and create_result.get("status") != 200:
            return {
                "success": False,
                "error": create_result.get("message", "Dataset creation failed"),
                "step": "create_dataset"
            }

        # Get the new dataset ID
        created_data = create_result.get("data", [])
        if not created_data:
            return {
                "success": False,
                "error": "No dataset ID returned from create",
                "step": "create_dataset"
            }
        new_dataset_id = created_data[0].get("ID", 0)

        # Step 4b: Update dataset with full data
        dataset_payload = {
            "ID": new_dataset_id,
            "name": name,
            "caption": caption or name,
            "driverID": driver_id,      # Driver type (e.g., 20 for PostgreSQL)
            "parentID": datasource_id,  # Datasource connection ID
            "query": sql_query,
            "query_rls": "",
            "rls": 0,
            "cached": 0,
            "limit": 5000,
            "mdx": 0,
            "datacorrection_active": 0,
            "fields": api_fields,
            "fields_ref": []
        }

        update_data = {
            "command": {"name": "update"},
            "object": {"name": "datasets", "id": new_dataset_id},
            "data": [dataset_payload]
        }

        response = await client.raw_post(
            datasets_url,
            json=update_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {instance.token}"
            },
            timeout=30.0
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code} on update",
                "step": "update_dataset",
                "dataset_id": new_dataset_id
            }

        data = response.json()

        if data.get("status") and data.get("status") != 200:
            return {
                "success": False,
                "error": data.get("message", "Dataset update failed"),
                "step": "update_dataset",
                "dataset_id": new_dataset_id
            }

        # Extract created dataset info
        created_data = data.get("data", [])
        if created_data and isinstance(created_data, list):
            created = created_data[0]
            # Audit-trail консистентно с пустым create в dataset_operations —
            # покрывает и прямой вызов, и роутинг create(query).
            logger.info(
                "audit:dataset_create instance=%s dataset_id=%s name=%r datasource_id=%s",
                client.instance.name, created.get("ID"), name, datasource_id,
            )
            return {
                "success": True,
                "message": "Dataset created with semantic layer",
                "dataset": {
                    "id": created.get("ID"),
                    "name": created.get("name"),
                    "caption": created.get("caption"),
                    "datasource_id": created.get("parentID"),  # parentID = datasource connection ID
                    "driver_id": created.get("driverID"),       # driverID = driver type
                    "fields_count": len(created.get("fields", []))
                },
                "fields": [
                    {
                        "id": f.get("ID"),
                        "name": f.get("name"),
                        "alias": f.get("alias"),
                        "type": f.get("type")
                    }
                    for f in created.get("fields", [])
                ]
            }

        return {
            "success": True,
            "message": "Dataset created but response format unexpected",
            "raw_response": data
        }

    except httpx.RequestError as e:
        return {
            "success": False,
            "error": "Connection error while creating dataset",
            "details": mask_sensitive(str(e)),
            "hint": "The datasource is unreachable; run preflight_check_datasource to diagnose.",
            "step": "create_dataset",
        }
    except Exception as e:
        return {
            "success": False,
            "error": "Failed to create dataset from SQL",
            "details": mask_sensitive(str(e)),
            "hint": "Validate SQL with sql_query_validate first; field_aliases/field_types may contain invalid field names.",
            "step": "create_dataset",
        }


async def query_execute(
    client,
    datasource_id: int,
    query: str,
    limit: int = 1000
) -> dict[str, Any]:
    """
    DEPRECATED: Raw SQL execution on datasources is NOT supported by ModusBI API.

    Use dataset_query() with dataset_id instead.

    The ModusBI API only supports querying data through datasets:
    - recordsets.create with dataset_id
    - recordsets.recordset.batch for batch queries

    Args:
        client: InstanceClient
        datasource_id: Datasource ID
        query: SQL query
        limit: Max rows

    Returns:
        Error message explaining the limitation
    """
    return {
        "success": False,
        "error": "Raw SQL execution on datasources is not supported by ModusBI API",
        "hint": "Use dataset_query() with dataset_id instead of datasource_id",
        "supported_operations": [
            "dataset_query(client, dataset_id) - Query data from dataset",
            "query_batch(client, dataset_id, queries) - Batch queries on dataset"
        ],
        "datasource_id": datasource_id
    }
