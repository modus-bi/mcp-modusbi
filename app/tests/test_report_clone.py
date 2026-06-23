#!/usr/bin/env python3
"""
Unit tests for report clone action.

Tests clone action in report_operations: copy grid, components, filters, variables.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.report_operations import report_operations


# Source report fixture
_SOURCE_REPORT = {
    "ID": 100,
    "name": "Original Dashboard",
    "caption": "Original Dashboard",
    "groupID": 5,
    "groupName": "Analytics",
    "grid": {
        "layouts": {
            "lg": [
                {"i": "0", "x": 0, "y": 0, "w": 12, "h": 4},
                {"i": "1", "x": 0, "y": 4, "w": 12, "h": 10},
            ]
        },
        "components": {
            "0": {
                "type": "HsTotalsPanelV2",
                "config": {"title": "KPI", "chartType": "totalsPanelV2"},
            },
            "1": {
                "type": "HsBarAMchartsChart",
                "config": {"title": "Sales Chart", "chartType": "barChart"},
            },
        },
    },
    "globalFilters": {"region": {"enabled": True, "selected": ["Moscow"]}},
    "globalVariables": {"year": {"value": ["2024"]}},
    "globalCategories": {"period": {"selected": "Q1", "options": ["Q1", "Q2", "Q3", "Q4"]}},
    "options": {
        "name__ru": "Original Dashboard",
        "caption__ru": "Original Dashboard",
        "allowOverlapMode": False,
    },
}

_CREATED_REPORT = {"ID": 200, "name": "Copy", "caption": "Copy", "groupID": 5, "groupName": "Analytics"}


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


def _make_mock_client(captured: dict | None = None) -> AsyncMock:
    """Create mock client for clone tests."""
    client = AsyncMock()
    client.base_url = "http://localhost:3000"

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {"status": 200, "data": [_SOURCE_REPORT]}
        if resource == "reports" and action == "create":
            return {"status": 200, "data": [_CREATED_REPORT]}
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["update_data"] = kwargs.get("data", [])
            return {"status": 200}
        if resource == "reports" and action == "list":
            return {"status": 200, "data": [_SOURCE_REPORT, _CREATED_REPORT]}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


@run_test
async def test_clone_basic():
    """Clone report copies grid and returns new ID."""
    client = _make_mock_client()
    result = await report_operations(client, action="clone", report_id=100)
    assert result.get("success"), f"Expected success: {result}"
    assert result["new_report"]["id"] == 200, f"Expected new ID 200: {result}"
    assert result["source_report_id"] == 100
    assert result["new_report"]["components_count"] == 2


@run_test
async def test_clone_default_name():
    """Clone uses '(копия)' suffix by default."""
    captured = {}
    client = _make_mock_client(captured)
    result = await report_operations(client, action="clone", report_id=100)
    assert result.get("success"), f"Expected success: {result}"
    assert "копия" in result["new_report"]["name"]


@run_test
async def test_clone_custom_name():
    """Clone with custom name."""
    captured = {}
    client = _make_mock_client(captured)
    result = await report_operations(client, action="clone", report_id=100, name="My Clone")
    assert result.get("success"), f"Expected success: {result}"
    assert result["new_report"]["name"] == "My Clone"


@run_test
async def test_clone_custom_group():
    """Clone to different group."""
    client = _make_mock_client()
    result = await report_operations(client, action="clone", report_id=100, group_id=20)
    assert result.get("success"), f"Expected success: {result}"
    assert result["new_report"]["group_id"] == 20


@run_test
async def test_clone_copies_grid():
    """Clone copies components and layouts."""
    captured = {}
    client = _make_mock_client(captured)
    result = await report_operations(client, action="clone", report_id=100)
    assert result.get("success"), f"Expected success: {result}"
    # Check that update was called with source grid
    assert captured.get("update_data"), "Expected update call"
    update = captured["update_data"][0]
    assert "0" in update["grid"]["components"]
    assert "1" in update["grid"]["components"]
    assert len(update["grid"]["layouts"]["lg"]) == 2


@run_test
async def test_clone_copies_filters():
    """Clone copies globalFilters."""
    captured = {}
    client = _make_mock_client(captured)
    await report_operations(client, action="clone", report_id=100)
    update = captured["update_data"][0]
    assert "region" in update["globalFilters"]
    assert update["globalFilters"]["region"]["selected"] == ["Moscow"]


@run_test
async def test_clone_copies_variables():
    """Clone copies globalVariables."""
    captured = {}
    client = _make_mock_client(captured)
    await report_operations(client, action="clone", report_id=100)
    update = captured["update_data"][0]
    assert "year" in update["globalVariables"]
    assert update["globalVariables"]["year"]["value"] == ["2024"]


@run_test
async def test_clone_copies_categories():
    """Clone copies globalCategories."""
    captured = {}
    client = _make_mock_client(captured)
    await report_operations(client, action="clone", report_id=100)
    update = captured["update_data"][0]
    assert "period" in update["globalCategories"]


@run_test
async def test_clone_missing_report_id():
    """Clone without report_id returns error."""
    client = _make_mock_client()
    result = await report_operations(client, action="clone")
    assert "error" in result, f"Expected error: {result}"
    assert "report_id" in result.get("missing", []) or "report_id" in result["error"].lower()


@run_test
async def test_clone_create_fails():
    """Clone returns error when create fails."""
    client = AsyncMock()

    async def mock_fail(resource, action, **kwargs):
        if resource == "reports" and action == "get":
            return {"status": 200, "data": [_SOURCE_REPORT]}
        if resource == "reports" and action == "create":
            return {"status": 500, "message": "Server error"}
        if resource == "reports" and action == "list":
            return {"status": 200, "data": []}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_fail)
    result = await report_operations(client, action="clone", report_id=100)
    assert "error" in result, f"Expected error: {result}"


async def main():
    print("=" * 60)
    print("Tests: report clone")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        test_clone_basic,
        test_clone_default_name,
        test_clone_custom_name,
        test_clone_custom_group,
        test_clone_copies_grid,
        test_clone_copies_filters,
        test_clone_copies_variables,
        test_clone_copies_categories,
        test_clone_missing_report_id,
        test_clone_create_fails,
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
