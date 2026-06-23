#!/usr/bin/env python3
"""
Regression tests for the add-guard, update warnings, and CF type-guard.

add with an unknown component_type: a guard on every caller of
    build_component_config (_add_component, _add_no_dataset_component,
    batch components_add) returns success:false and does NOT write to the
    grid (so a builder error-dict never persists into the report).
update: series_field/column_fields are add-only parameters; on update
    they produce an honest warning instead of being silently ignored.
conditional_rule_add: type-guard — on non-table/pivot components it
    returns success:false instead of a false success.
"""

import asyncio
import copy
import sys
from pathlib import Path
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.component_crud import (
    _add_component,
    _add_no_dataset_component,
    _builder_error_response,
)
from app.tools.batch_operations import _add_multiple_components
from app.tools.component_operations import component_operations


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
# Mock client
# =============================================================================

def _make_client(
    captured: dict | None = None,
    components: dict | None = None,
) -> AsyncMock:
    """Mock client: report 35 + dataset 5 (region/amount) + recordsets data."""
    client = AsyncMock()
    client.base_url = "http://localhost:3000"

    report = {
        "ID": 35,
        "grid": {
            "layouts": {"lg": []},
            "components": copy.deepcopy(components or {}),
        },
    }
    dataset = {
        "ID": 5,
        "caption": "Test DS",
        "fields": [
            {"name": "region", "alias": "Регион"},
            {"name": "amount", "alias": "Сумма"},
        ],
    }

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {"status": 200, "data": [report]}
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["data"] = kwargs.get("data", [])
            return {"status": 200}
        if resource == "datasets" and action == "get":
            return {"status": 200, "data": [dataset]}
        if resource == "recordsets" and action == "create":
            return {"status": 200, "data": [{"region": "A", "amount": 1}]}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


def _update_calls(client: AsyncMock) -> list:
    """Все вызовы reports/update (запись в grid)."""
    return [
        c for c in client.api_call.call_args_list
        if c.args[:2] == ("reports", "update")
    ]


# =============================================================================
# helper
# =============================================================================

@run_test
async def test_addguard_helper_passes_valid_component():
    """A valid component (no 'error') → None, the guard does not trigger."""
    assert _builder_error_response({"type": "HsBarAMchartsChart", "config": {}}) is None
    assert _builder_error_response(None) is None


@run_test
async def test_addguard_helper_wraps_error_dict():
    """A builder error-dict → success:false envelope + hint about types_list."""
    res = _builder_error_response({
        "error": "Unknown component_type 'HsBogusChart'",
        "available_types": ["HsBarAMchartsChart"],
        "hint": "Common mistakes: ...",
    })
    assert res is not None
    assert res["success"] is False
    assert "Unknown component_type" in res["error"]
    assert "types_list" in res["hint"], res["hint"]
    assert "available_types" in res


# =============================================================================
# _add_component (data path)
# =============================================================================

@run_test
async def test_addguard_add_invalid_type_returns_error():
    """add with a typo in the type → success:false + error + hint."""
    client = _make_client()
    res = await _add_component(
        client, report_id=35, component_type="HsBogusChart", title="X",
        value_field="amount", dataset_id=5, category_field="region",
    )
    assert res.get("success") is False, f"Expected success:false: {res}"
    assert "Unknown component_type" in res.get("error", ""), res
    assert "types_list" in res.get("hint", ""), res
    assert "available_types" in res, res


@run_test
async def test_addguard_add_invalid_type_not_written_to_grid():
    """A broken component is NOT written to the report (reports/update not called)."""
    client = _make_client()
    await _add_component(
        client, report_id=35, component_type="HsBogusChart", title="X",
        value_field="amount", dataset_id=5,
    )
    assert not _update_calls(client), "reports/update must NOT be called for invalid type"


@run_test
async def test_addguard_add_noncreatable_type_rejected():
    """A non-creatable type (CustomChart1) → success:false, no write."""
    client = _make_client()
    res = await _add_component(
        client, report_id=35, component_type="CustomChart1", title="X",
        value_field="amount", dataset_id=5,
    )
    assert res.get("success") is False, res
    assert not _update_calls(client)


@run_test
async def test_addguard_add_valid_type_unaffected():
    """A valid type is still added (the guard does not break the happy path)."""
    captured: dict = {}
    client = _make_client(captured=captured)
    res = await _add_component(
        client, report_id=35, component_type="HsBarAMchartsChart", title="Sales",
        value_field="amount", dataset_id=5, category_field="region",
        aggregation="sum",
    )
    assert res.get("success") is True, res
    saved_components = captured["data"][0]["grid"]["components"]
    assert saved_components["0"]["type"] == "HsBarAMchartsChart", saved_components


# =============================================================================
# _add_no_dataset_component (utility path)
# =============================================================================

@run_test
async def test_addguard_no_dataset_invalid_type_rejected():
    """An invalid type on the utility path → success:false, no write."""
    client = _make_client()
    res = await _add_no_dataset_component(
        client, report_id=35, component_type="HsBogusPanel", title="X",
    )
    assert res.get("success") is False, res
    assert "Unknown component_type" in res.get("error", ""), res
    assert not _update_calls(client), "reports/update must NOT be called for invalid type"


@run_test
async def test_addguard_no_dataset_valid_type_unaffected():
    """A valid utility type (HsImagePanel) is still added."""
    captured: dict = {}
    client = _make_client(captured=captured)
    res = await _add_no_dataset_component(
        client, report_id=35, component_type="HsImagePanel", title="Logo",
    )
    assert res.get("success") is True, res
    saved_components = captured["data"][0]["grid"]["components"]
    assert saved_components["0"]["type"] == "HsImagePanel", saved_components


# =============================================================================
# batch components_add
# =============================================================================

@run_test
async def test_addguard_batch_invalid_in_errors_not_added():
    """batch with valid+invalid → invalid in errors[], only valid in the grid."""
    captured: dict = {}
    client = _make_client(captured=captured)
    res = await _add_multiple_components(client, report_id=35, components=[
        {"component_type": "HsBarAMchartsChart", "title": "OK",
         "value_field": "amount", "dataset_id": 5, "category_field": "region"},
        {"component_type": "HsBogusChart", "title": "Broken",
         "value_field": "amount", "dataset_id": 5},
    ])
    assert res.get("success") is True, res
    assert len(res["added"]) == 1, res["added"]
    assert res["added"][0]["type"] == "HsBarAMchartsChart"
    errors = res.get("errors") or []
    assert any("Unknown component_type" in (e.get("error") or "") for e in errors), errors
    # only the valid component is in the saved grid
    saved_components = captured["data"][0]["grid"]["components"]
    assert len(saved_components) == 1, saved_components
    assert saved_components["0"]["type"] == "HsBarAMchartsChart"


@run_test
async def test_addguard_batch_all_invalid_nothing_added():
    """batch of only invalid types → added=0, grid empty."""
    captured: dict = {}
    client = _make_client(captured=captured)
    res = await _add_multiple_components(client, report_id=35, components=[
        {"component_type": "HsBogusChart", "title": "B1",
         "value_field": "amount", "dataset_id": 5},
        {"component_type": "HsPivotOrbChart", "title": "B2",
         "value_field": "amount", "dataset_id": 5},
    ])
    assert len(res["added"]) == 0, res["added"]
    assert len(res.get("errors") or []) == 2, res.get("errors")
    saved_components = captured["data"][0]["grid"]["components"]
    assert saved_components == {}, saved_components


@run_test
async def test_addguard_batch_error_has_hint():
    """A batch error record contains a hint about types_list + config."""
    client = _make_client()
    res = await _add_multiple_components(client, report_id=35, components=[
        {"component_type": "HsBogusChart", "title": "Broken",
         "value_field": "amount", "dataset_id": 5},
    ])
    errors = res.get("errors") or []
    assert errors, res
    err = errors[0]
    assert "types_list" in (err.get("hint") or ""), err
    assert err.get("config", {}).get("title") == "Broken", err


# =============================================================================
# update — series_field/column_fields add-only warning
# =============================================================================

_BAR_COMPONENT = {
    "type": "HsBarAMchartsChart",
    "config": {"title": "Bar", "chartType": "barChart", "axes": []},
}


@run_test
async def test_update_series_field_warns_add_only():
    """update: series_field is applied.

    On a component WITHOUT a series axis — an honest warning (not silent-ignore);
    application on a component WITH an axis is covered by the series-rebuild unit test.
    """
    client = _make_client(components={"0": copy.deepcopy(_BAR_COMPONENT)})
    res = await component_operations(
        client, action="update", report_id=35, component_idx=0,
        title="New title", series_field="city", aggregation="",
    )
    assert res.get("success") is True, res
    warnings = res.get("warnings") or []
    assert any("no series axis" in w for w in warnings), warnings


@run_test
async def test_update_column_fields_warns_add_only():
    """update: column_fields passed → 'add-only' warning."""
    client = _make_client(components={"0": copy.deepcopy(_BAR_COMPONENT)})
    res = await component_operations(
        client, action="update", report_id=35, component_idx=0,
        title="New title", column_fields="month", aggregation="",
    )
    warnings = res.get("warnings") or []
    assert any("column_fields is add-only" in w for w in warnings), warnings


@run_test
async def test_update_without_addonly_params_no_warning():
    """update: without series_field/column_fields (or "") → no add-only warning."""
    client = _make_client(components={"0": copy.deepcopy(_BAR_COMPONENT)})
    res = await component_operations(
        client, action="update", report_id=35, component_idx=0,
        title="New title", series_field="", column_fields="", aggregation="",
    )
    assert res.get("success") is True, res
    warnings = res.get("warnings") or []
    assert not any("add-only" in w for w in warnings), warnings


# =============================================================================
# conditional_rule_add — type-guard (только table/pivot)
# =============================================================================

# conditional_rule_add requires field to resolve from the axes —
# the fixtures contain the amount field.
_AMOUNT_AXES = [
    {"type": "values", "fields": [{"name": "amount", "id": "amount_Ab12Cd"}]},
]

_TABLE_COMPONENT = {
    "type": "HsTableReactabularChart",
    "config": {
        "title": "Table", "chartType": "tableChart", "rules": [],
        "axes": copy.deepcopy(_AMOUNT_AXES),
    },
}

_PIVOT_COMPONENT = {
    "type": "HsPivotChart",
    "config": {
        "title": "Pivot", "chartType": "pivotChart", "rules": [],
        "axes": copy.deepcopy(_AMOUNT_AXES),
    },
}

_RULE = {"field": "amount", "operator": ">", "value": 1000, "background": "#f44336"}


@run_test
async def test_conditional_rule_add_on_bar_rejected():
    """type-guard: rule on bar → success:false + component_type, no write."""
    client = _make_client(components={"0": copy.deepcopy(_BAR_COMPONENT)})
    res = await component_operations(
        client, action="conditional_rule_add", report_id=35, component_idx=0,
        config_overrides=dict(_RULE),
    )
    assert res.get("success") is False, f"Expected success:false on bar: {res}"
    assert "table/pivot" in res.get("error", ""), res
    assert res.get("component_type") == "HsBarAMchartsChart", res
    assert not _update_calls(client), "rule must NOT be saved on unsupported type"


@run_test
async def test_conditional_rule_add_on_table_works():
    """type-guard: rule on table is still added."""
    client = _make_client(components={"0": copy.deepcopy(_TABLE_COMPONENT)})
    res = await component_operations(
        client, action="conditional_rule_add", report_id=35, component_idx=0,
        config_overrides=dict(_RULE),
    )
    assert res.get("success") is True, res
    assert res.get("rule_index") == 0, res


@run_test
async def test_conditional_rule_add_on_pivot_works():
    """type-guard: rule on pivot is still added."""
    client = _make_client(components={"0": copy.deepcopy(_PIVOT_COMPONENT)})
    res = await component_operations(
        client, action="conditional_rule_add", report_id=35, component_idx=0,
        config_overrides=dict(_RULE),
    )
    assert res.get("success") is True, res


@run_test
async def test_conditional_rule_add_lists_supported_types():
    """type-guard: error contains supported_types for LLM self-correction."""
    client = _make_client(components={"0": copy.deepcopy(_BAR_COMPONENT)})
    res = await component_operations(
        client, action="conditional_rule_add", report_id=35, component_idx=0,
        config_overrides=dict(_RULE),
    )
    assert set(res.get("supported_types") or []) == {
        "HsTableReactabularChart", "HsPivotChart",
    }, res


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: add-guard + update warnings + CF type-guard")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        test_addguard_helper_passes_valid_component,
        test_addguard_helper_wraps_error_dict,
        test_addguard_add_invalid_type_returns_error,
        test_addguard_add_invalid_type_not_written_to_grid,
        test_addguard_add_noncreatable_type_rejected,
        test_addguard_add_valid_type_unaffected,
        test_addguard_no_dataset_invalid_type_rejected,
        test_addguard_no_dataset_valid_type_unaffected,
        test_addguard_batch_invalid_in_errors_not_added,
        test_addguard_batch_all_invalid_nothing_added,
        test_addguard_batch_error_has_hint,
        test_update_series_field_warns_add_only,
        test_update_column_fields_warns_add_only,
        test_update_without_addonly_params_no_warning,
        test_conditional_rule_add_on_bar_rejected,
        test_conditional_rule_add_on_table_works,
        test_conditional_rule_add_on_pivot_works,
        test_conditional_rule_add_lists_supported_types,
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
