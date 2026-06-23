#!/usr/bin/env python3
"""
Unit tests for conditional formatting: add/list/delete rules.

Tests simplified API for adding conditional formatting rules to tables/pivots.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

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


_TABLE_COMPONENT = {
    "type": "HsTableReactabularChart",
    "config": {
        "title": "Test Table",
        "chartType": "tableChart",
        "rules": [],
        # conditional_rule_add требует, чтобы field резолвился по
        # имени/alias/id из осей — фикстура содержит реальные поля.
        "axes": [
            {"type": "values", "fields": [
                {"name": "revenue", "id": "revenue_X7xekZ", "alias": "Выручка"},
                {"name": "profit", "id": "profit_Ab12Cd"},
                {"name": "x", "id": "x_Ef34Gh"},
            ]},
        ],
    },
}

_TABLE_WITH_RULES = {
    "type": "HsTableReactabularChart",
    "config": {
        "title": "Test Table",
        "chartType": "tableChart",
        "axes": [
            {"type": "values", "fields": [
                {"name": "revenue", "id": "revenue"},
                {"name": "cost", "id": "cost"},
                {"name": "margin", "id": "margin_Zz90Xx"},
            ]},
        ],
        "rules": [
            {
                "id": "abc123",
                "name": "revenue > 1000",
                "fieldId": "revenue",
                "cons": {"0": {"operator": ">", "value": 1000.0}},
                "color": "#ffffff",
                "background": "#4caf50",
                "wholeRow": True,
            },
            {
                "id": "def456",
                "name": "cost < 0",
                "fieldId": "cost",
                "cons": {"0": {"operator": "<", "value": 0.0}},
                "color": "#ffffff",
                "background": "#f44336",
                "wholeRow": False,
            },
        ],
    },
}


def _make_mock_client(component: dict | None = None, captured: dict | None = None) -> AsyncMock:
    """Create mock client with optional component config."""
    import copy
    client = AsyncMock()
    client.base_url = "http://localhost:3000"
    comp = copy.deepcopy(component or _TABLE_COMPONENT)

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {
                "status": 200,
                "data": [{
                    "ID": 999,
                    "grid": {
                        "layouts": {"lg": [{"i": "0", "x": 0, "y": 0, "w": 12, "h": 8}]},
                        "components": {"0": comp},
                    },
                }],
            }
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["data"] = kwargs.get("data", [])
            return {"status": 200}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


# =============================================================================
# conditional_rule_add tests
# =============================================================================

@run_test
async def test_add_rule_basic():
    """Add a basic conditional rule."""
    captured = {}
    client = _make_mock_client(captured=captured)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "revenue", "operator": ">", "value": 1000, "color": "#ffffff", "background": "#4caf50"},
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["rule_index"] == 0
    assert result["rule"]["field"] == "revenue"
    assert result["rule"]["operator"] == ">"
    assert result["rule"]["value"] == 1000


@run_test
async def test_add_rule_friendly_operators():
    """Friendly operator names work (greater_than, lt, etc.)."""
    for friendly, expected in [("greater_than", ">"), ("gte", ">="), ("lt", "<"), ("lte", "<="), ("eq", "=")]:
        client = _make_mock_client()
        result = await component_operations(
            client, action="conditional_rule_add",
            report_id=999, component_idx=0,
            config_overrides={"field": "x", "operator": friendly, "value": 0},
        )
        assert result.get("success"), f"Failed for operator '{friendly}': {result}"
        assert result["rule"]["operator"] == expected, f"'{friendly}' should resolve to '{expected}', got '{result['rule']['operator']}'"


@run_test
async def test_add_rule_with_whole_row():
    """whole_row flag passed correctly."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "revenue", "operator": ">", "value": 100, "whole_row": True},
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["rule"]["whole_row"] is True


@run_test
async def test_add_rule_with_bold_indicator():
    """bold and indicator params work."""
    captured = {}
    client = _make_mock_client(captured=captured)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={
            "field": "profit", "operator": ">=", "value": 0,
            "bold": True, "indicator": "up", "indicator_color": "#4caf50",
        },
    )
    assert result.get("success"), f"Expected success: {result}"


@run_test
async def test_add_rule_auto_name():
    """Rule name auto-generated from field/operator/value."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "revenue", "operator": ">", "value": 1000},
    )
    assert result.get("success"), f"Expected success: {result}"
    assert "revenue > 1000" in result["message"]


@run_test
async def test_add_rule_appends_to_existing():
    """New rule appended after existing rules (correct index)."""
    import copy
    comp = copy.deepcopy(_TABLE_WITH_RULES)
    client = _make_mock_client(component=comp)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "margin", "operator": "<=", "value": 0, "background": "#ff0000"},
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["rule_index"] == 2, f"Expected index 2 (appended), got {result['rule_index']}"


@run_test
async def test_add_rule_missing_field():
    """Error when field missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"operator": ">", "value": 100},
    )
    assert "error" in result
    assert "field" in result["missing"]


@run_test
async def test_add_rule_missing_operator():
    """Error when operator missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "x", "value": 100},
    )
    assert "error" in result
    assert "operator" in result["missing"]


@run_test
async def test_add_rule_invalid_operator():
    """Error for unknown operator."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "x", "operator": "BADOP", "value": 100},
    )
    assert "error" in result
    assert "Unknown operator" in result["error"]


@run_test
async def test_add_rule_missing_value():
    """Error when value missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "x", "operator": ">"},
    )
    assert "error" in result
    assert "value" in result["missing"]


# =============================================================================
# conditional_rule_list tests
# =============================================================================

@run_test
async def test_list_rules_empty():
    """List rules on component with no rules."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_list",
        report_id=999, component_idx=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["count"] == 0
    assert result["rules"] == []


@run_test
async def test_list_rules_with_data():
    """List rules on component with existing rules."""
    client = _make_mock_client(component=_TABLE_WITH_RULES)
    result = await component_operations(
        client, action="conditional_rule_list",
        report_id=999, component_idx=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["count"] == 2
    assert result["rules"][0]["field"] == "revenue"
    assert result["rules"][0]["operator"] == ">"
    assert result["rules"][0]["value"] == 1000.0
    assert result["rules"][1]["field"] == "cost"


# =============================================================================
# conditional_rule_delete tests
# =============================================================================

@run_test
async def test_delete_rule():
    """Delete a rule by index."""
    import copy
    comp = copy.deepcopy(_TABLE_WITH_RULES)
    captured = {}
    client = _make_mock_client(component=comp, captured=captured)
    result = await component_operations(
        client, action="conditional_rule_delete",
        report_id=999, component_idx=0, field_index=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["remaining_rules"] == 1


@run_test
async def test_delete_rule_invalid_index():
    """Error for out-of-range rule index."""
    client = _make_mock_client(component=_TABLE_WITH_RULES)
    result = await component_operations(
        client, action="conditional_rule_delete",
        report_id=999, component_idx=0, field_index=99,
    )
    assert "error" in result
    assert "out of range" in result["error"]


@run_test
async def test_delete_rule_missing_params():
    """Error when params missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="conditional_rule_delete",
        report_id=999, component_idx=0,
    )
    assert "error" in result


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: conditional formatting rules")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        # add
        test_add_rule_basic,
        test_add_rule_friendly_operators,
        test_add_rule_with_whole_row,
        test_add_rule_with_bold_indicator,
        test_add_rule_auto_name,
        test_add_rule_appends_to_existing,
        test_add_rule_missing_field,
        test_add_rule_missing_operator,
        test_add_rule_invalid_operator,
        test_add_rule_missing_value,
        # list
        test_list_rules_empty,
        test_list_rules_with_data,
        # delete
        test_delete_rule,
        test_delete_rule_invalid_index,
        test_delete_rule_missing_params,
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
