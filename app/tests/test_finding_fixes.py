#!/usr/bin/env python3
"""
Regression tests for diagnostics / UX behavior.

- security_operations RLS write on a driver that rejects RLS (ClickHouse) →
  structured hint instead of opaque "Failed to ..." on HTTP 400.
- dataset_create_from_sql against the system "Метаданные" datasource →
  actionable up-front error instead of downstream opaque HTTP 400.
- component_axes(calc_field_remove) with an unknown field → lists
  available_fields + hint clarifying value_field = field name, not SQL.
- dataset_query in DEMO mode caps row limit → surfaces demo_capped /
  requested_limit / truncated=True instead of a silent truncated:false.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.query_execute import (
    dataset_query,
    dataset_create_from_sql,
    _is_metadata_datasource,
)
from app.tools.security_operations import _rls_write_error
from app.tools.component_axes import _calc_field_remove
from app.core.security import set_security_mode, SecurityMode


class TestResult:
    def __init__(self, name: str, passed: bool, message: str):
        self.name = name
        self.passed = passed
        self.message = message


def run_test(func):
    async def wrapper(results: list[TestResult]):
        name = func.__name__
        try:
            await func()
            results.append(TestResult(name, True, "OK"))
            print(f"  ✅ {name}")
        except AssertionError as e:
            results.append(TestResult(name, False, str(e)))
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            results.append(TestResult(name, False, f"Exception: {e}"))
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
    return wrapper


# =============================================================================
# RLS write error diagnostics
# =============================================================================

@run_test
async def test_f2_rls_400_has_driver_hint():
    """HTTP 400 on RLS write → hint about unsupported driver."""
    res = _rls_write_error({"status": 400, "message": "Bad Request"}, 699, "Failed to enable RLS")
    assert res["success"] is False
    assert res["status"] == 400
    assert "hint" in res, f"Expected hint on 400: {res}"
    assert "ClickHouse" in res["hint"] and "PostgreSQL" in res["hint"], res["hint"]


@run_test
async def test_f2_rls_non400_no_driver_hint():
    """Non-400 RLS error → no misleading driver hint."""
    res = _rls_write_error({"status": 500, "message": "Server error"}, 5, "Failed to enable RLS")
    assert res["success"] is False
    assert res["status"] == 500
    assert "hint" not in res, f"Should not add driver hint on 500: {res}"
    assert res["error"] == "Server error"


# =============================================================================
# metadata datasource guard
# =============================================================================

@run_test
async def test_f3_is_metadata_datasource_detection():
    """metadata datasource detected by name (RU + EN)."""
    assert _is_metadata_datasource({"name": "Метаданные"}) is True
    assert _is_metadata_datasource({"caption": "System Metadata"}) is True
    assert _is_metadata_datasource({"name": "PostgreSQL prod"}) is False
    assert _is_metadata_datasource(None) is False
    assert _is_metadata_datasource({}) is False


def _make_ds_list_client(datasources: list[dict]) -> AsyncMock:
    client = AsyncMock()
    client.base_url = "http://localhost:3000"

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "datasources" and action == "list":
            return {"status": 200, "data": datasources}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


@run_test
async def test_f3_create_on_metadata_rejected_upfront():
    """dataset_create_from_sql on 'Метаданные' → actionable error, no create attempt."""
    client = _make_ds_list_client([{"ID": 1, "name": "Метаданные", "parentID": 0}])
    res = await dataset_create_from_sql(
        client, sql_query="SELECT 1 AS x", datasource_id=1, name="t",
    )
    assert res["success"] is False
    assert res["step"] == "validate_datasource", res
    assert "metadata" in res["error"].lower() or "Метаданные" in res["error"], res["error"]
    assert "hint" in res and "datasource_operations" in res["hint"]
    # Guard must short-circuit BEFORE any recordset/create call.
    called = [c.args[:2] for c in client.api_call.call_args_list]
    assert all(c[0] == "datasources" for c in called), f"Unexpected calls after guard: {called}"


# =============================================================================
# calc_field_remove diagnostics
# =============================================================================

def _make_report_client(components: dict) -> AsyncMock:
    client = AsyncMock()
    report = {"ID": 50, "grid": {"components": components}}

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {"status": 200, "data": [report]}
        if resource == "reports" and action == "update":
            return {"status": 200}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


@run_test
async def test_f4_calc_remove_unknown_lists_available():
    """unknown field → error lists available_fields + value_field hint."""
    components = {
        "2": {
            "type": "HsBarAMchartsChart",
            "config": {
                "axes": [
                    {"type": "values", "fields": [
                        {"name": "profit_margin", "type": "calculated"},
                        {"name": "revenue", "type": "number"},
                    ]},
                ],
            },
        },
    }
    client = _make_report_client(components)
    res = await _calc_field_remove(client, report_id=50, component_idx=2, field_name="margin")
    assert "error" in res and "not found" in res["error"], res
    assert "available_fields" in res, res
    assert set(res["available_fields"]) == {"profit_margin", "revenue"}, res["available_fields"]
    assert "value_field" in res["hint"], res["hint"]


@run_test
async def test_f4_calc_remove_success_unaffected():
    """correct field name still removes cleanly."""
    components = {
        "2": {
            "type": "HsBarAMchartsChart",
            "config": {
                "axes": [
                    {"type": "values", "fields": [
                        {"name": "profit_margin", "type": "calculated"},
                    ]},
                ],
            },
        },
    }
    client = _make_report_client(components)
    res = await _calc_field_remove(client, report_id=50, component_idx=2, field_name="profit_margin")
    assert res.get("success") is True, res
    assert res["removed_field"] == "profit_margin"


# =============================================================================
# demo silent cap
# =============================================================================

def _make_query_client(n_rows: int) -> AsyncMock:
    client = AsyncMock()
    rows = [{"id": i, "v": i * 10} for i in range(n_rows)]

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "recordsets" and action == "create":
            return {"status": 200, "data": rows}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


@run_test
async def test_f5_demo_cap_surfaced():
    """DEMO mode caps limit → demo_capped/requested_limit/truncated=True."""
    set_security_mode(SecurityMode.DEMO)
    try:
        # backend honours the capped limit and returns 100 rows
        client = _make_query_client(100)
        res = await dataset_query(client, dataset_id=5, limit=1000)
        assert res.get("success") is True, res
        assert res.get("demo_capped") is True, res
        assert res.get("requested_limit") == 1000, res
        assert res.get("effective_limit") == 100, res
        assert res.get("truncated") is True, "demo cap must not be silent"
        assert "note" in res and "DEMO" in res["note"]
    finally:
        set_security_mode(SecurityMode.READWRITE)


@run_test
async def test_f5_no_cap_when_under_limit():
    """DEMO mode with limit <= max → no demo_capped flag."""
    set_security_mode(SecurityMode.DEMO)
    try:
        client = _make_query_client(50)
        res = await dataset_query(client, dataset_id=5, limit=50)
        assert res.get("success") is True, res
        assert "demo_capped" not in res, res
        assert res.get("truncated") is False, res
    finally:
        set_security_mode(SecurityMode.READWRITE)


@run_test
async def test_f5_readwrite_no_cap():
    """READWRITE mode never caps — large limit passes through."""
    set_security_mode(SecurityMode.READWRITE)
    client = _make_query_client(500)
    res = await dataset_query(client, dataset_id=5, limit=1000)
    assert res.get("success") is True, res
    assert "demo_capped" not in res, res


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: diagnostics")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        test_f2_rls_400_has_driver_hint,
        test_f2_rls_non400_no_driver_hint,
        test_f3_is_metadata_datasource_detection,
        test_f3_create_on_metadata_rejected_upfront,
        test_f4_calc_remove_unknown_lists_available,
        test_f4_calc_remove_success_unaffected,
        test_f5_demo_cap_surfaced,
        test_f5_no_cap_when_under_limit,
        test_f5_readwrite_no_cap,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    for test_func in tests:
        await test_func(results)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")

    if failed:
        print("\nFailed tests:")
        for r in results:
            if not r.passed:
                print(f"  ❌ {r.name}: {r.message}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
