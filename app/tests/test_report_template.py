#!/usr/bin/env python3
"""
Unit tests for the report_template tool.

Tests list/preview/scaffold actions for 6 report templates.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.report_template import report_template, TEMPLATES, _SCAFFOLD_NO_DATA


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
    """Create mock client for template tests."""
    client = AsyncMock()
    client.base_url = "http://localhost:3000"

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {
                "status": 200,
                "data": [{"ID": 999, "grid": {"layouts": {"lg": [], "md": [], "sm": []}, "components": {}}}],
            }
        if resource == "reports" and action == "create":
            return {"status": 200, "data": [{"ID": 500, "name": "New Report"}]}
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["data"] = kwargs.get("data", [])
            return {"status": 200}
        if resource == "reports" and action == "list":
            return {"status": 200, "data": [{"ID": 500, "name": "New Report"}]}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


# =============================================================================
# list action tests
# =============================================================================

@run_test
async def test_list_returns_all_templates():
    """list returns all 6 templates."""
    client = _make_mock_client()
    result = await report_template(client, action="list")
    assert result.get("success"), f"Expected success: {result}"
    assert result["count"] == 6, f"Expected 6 templates, got {result['count']}"


@run_test
async def test_list_has_required_fields():
    """Each template has name, description, component_count, ascii_preview."""
    client = _make_mock_client()
    result = await report_template(client, action="list")
    for tpl in result["templates"]:
        for field in ["name", "description", "component_count", "component_types", "ascii_preview"]:
            assert field in tpl, f"Missing field '{field}' in template {tpl.get('name')}"


@run_test
async def test_list_component_counts():
    """Component counts match template definitions."""
    client = _make_mock_client()
    result = await report_template(client, action="list")
    expected = {"kpi_dashboard": 10, "ranking": 7, "comparison": 10, "factor_analysis": 7, "geo_analytics": 9, "simple": 3}
    for tpl in result["templates"]:
        name = tpl["name"]
        assert name in expected, f"Unknown template: {name}"
        assert tpl["component_count"] == expected[name], f"{name}: expected {expected[name]}, got {tpl['component_count']}"


# =============================================================================
# preview action tests
# =============================================================================

@run_test
async def test_preview_kpi_dashboard():
    """preview returns ascii_layout and components for kpi_dashboard."""
    client = _make_mock_client()
    result = await report_template(client, action="preview", template="kpi_dashboard")
    assert result.get("success"), f"Expected success: {result}"
    assert "ascii_layout" in result
    assert len(result["components"]) == 10


@run_test
async def test_preview_components_have_position():
    """Each component in preview has x/y/w/h."""
    client = _make_mock_client()
    result = await report_template(client, action="preview", template="simple")
    for comp in result["components"]:
        for field in ["x", "y", "w", "h"]:
            assert field in comp, f"Missing '{field}' in component {comp.get('title')}"


@run_test
async def test_preview_needs_data_flag():
    """needs_data correctly flags data vs no-data components."""
    client = _make_mock_client()
    result = await report_template(client, action="preview", template="comparison")
    # comparison has HsTextBlock (no data) and data components
    text_comp = next(c for c in result["components"] if c["type"] == "HsTextBlock")
    assert text_comp["needs_data"] is False, "HsTextBlock should not need data"
    kpi_comp = next(c for c in result["components"] if c["type"] == "HsTotalsPanelV2")
    assert kpi_comp["needs_data"] is True, "HsTotalsPanelV2 should need data"


@run_test
async def test_preview_invalid_template():
    """preview returns error for unknown template."""
    client = _make_mock_client()
    result = await report_template(client, action="preview", template="nonexistent")
    assert "error" in result, f"Expected error: {result}"
    assert "nonexistent" in result["error"]
    # envelope consistency — success:false + hint with the list of templates
    assert result.get("success") is False, f"Expected success:false: {result}"
    assert "Valid:" in result.get("hint", ""), f"Expected hint with valid list: {result}"


@run_test
async def test_preview_missing_template():
    """preview without template returns error."""
    client = _make_mock_client()
    result = await report_template(client, action="preview")
    assert "error" in result, f"Expected error: {result}"


# =============================================================================
# scaffold action tests
# =============================================================================

@run_test
async def test_scaffold_creates_report():
    """scaffold without report_id creates new report."""
    client = _make_mock_client()
    result = await report_template(client, action="scaffold", template="simple", dataset_id=10)
    assert result.get("success"), f"Expected success: {result}"
    assert result["report_created"] is True
    assert result["report_id"] == 500


@run_test
async def test_scaffold_uses_existing_report():
    """scaffold with report_id adds to existing report."""
    client = _make_mock_client()
    result = await report_template(client, action="scaffold", template="simple", report_id=999, dataset_id=10)
    assert result.get("success"), f"Expected success: {result}"
    assert result["report_created"] is False
    assert result["report_id"] == 999


@run_test
async def test_scaffold_correct_component_count():
    """scaffold adds correct number of components for kpi_dashboard."""
    captured = {}
    client = _make_mock_client(captured)
    result = await report_template(client, action="scaffold", template="kpi_dashboard", report_id=999, dataset_id=10)
    assert result.get("success"), f"Expected success: {result}"
    assert len(result["added"]) == 10, f"Expected 10 added, got {len(result['added'])}"
    # Check captured grid has 10 components
    grid = captured["data"][0]["grid"]
    assert len(grid["components"]) == 10


@run_test
async def test_scaffold_positions_correct():
    """scaffold positions match template spec."""
    captured = {}
    client = _make_mock_client(captured)
    result = await report_template(client, action="scaffold", template="simple", report_id=999, dataset_id=10)
    assert result.get("success"), f"Expected success: {result}"
    # Simple: 3 components — filter(0,0,48,3), chart(0,3,48,10), table(0,13,48,14)
    positions = [(a["position"]["x"], a["position"]["y"], a["position"]["w"], a["position"]["h"]) for a in result["added"]]
    assert positions[0] == (0, 0, 48, 3), f"Filter position: {positions[0]}"
    assert positions[1] == (0, 3, 48, 10), f"Chart position: {positions[1]}"
    assert positions[2] == (0, 13, 48, 14), f"Table position: {positions[2]}"


@run_test
async def test_scaffold_no_data_skip_value_field():
    """No-data components (PageContainer, TextBlock, Filter) don't have value_field."""
    captured = {}
    client = _make_mock_client(captured)
    result = await report_template(client, action="scaffold", template="comparison", report_id=999, dataset_id=10)
    assert result.get("success"), f"Expected success: {result}"
    # Check that no-data components in info have needs_data=False
    text_comps = [c for c in result["components"] if c["type"] == "HsTextBlock"]
    assert len(text_comps) == 1
    assert text_comps[0]["needs_data"] is False


@run_test
async def test_scaffold_invalid_template():
    """scaffold with unknown template returns error."""
    client = _make_mock_client()
    result = await report_template(client, action="scaffold", template="nonexistent", dataset_id=10)
    assert "error" in result, f"Expected error: {result}"
    # envelope consistency — success:false + hint with the list of templates
    assert result.get("success") is False, f"Expected success:false: {result}"
    assert "Valid:" in result.get("hint", ""), f"Expected hint with valid list: {result}"


@run_test
async def test_scaffold_missing_dataset_id():
    """scaffold without dataset_id returns error for templates with data components."""
    client = _make_mock_client()
    result = await report_template(client, action="scaffold", template="simple")
    assert "error" in result, f"Expected error: {result}"
    assert "dataset_id" in result["missing"]


@run_test
async def test_scaffold_has_next_steps():
    """scaffold response includes next_steps."""
    client = _make_mock_client()
    result = await report_template(client, action="scaffold", template="simple", report_id=999, dataset_id=10)
    assert result.get("success"), f"Expected success: {result}"
    assert "next_steps" in result
    assert len(result["next_steps"]) >= 2


@run_test
async def test_scaffold_all_templates():
    """scaffold works for all 6 templates."""
    for template_name, tpl in TEMPLATES.items():
        client = _make_mock_client()
        result = await report_template(client, action="scaffold", template=template_name, report_id=999, dataset_id=10)
        assert result.get("success"), f"Failed for {template_name}: {result}"
        assert len(result["added"]) == len(tpl["components"]), \
            f"{template_name}: expected {len(tpl['components'])} components, got {len(result['added'])}"


@run_test
async def test_unknown_action():
    """Unknown action returns error."""
    client = _make_mock_client()
    result = await report_template(client, action="unknown")
    assert "error" in result, f"Expected error: {result}"


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: report_template")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        # list
        test_list_returns_all_templates,
        test_list_has_required_fields,
        test_list_component_counts,
        # preview
        test_preview_kpi_dashboard,
        test_preview_components_have_position,
        test_preview_needs_data_flag,
        test_preview_invalid_template,
        test_preview_missing_template,
        # scaffold
        test_scaffold_creates_report,
        test_scaffold_uses_existing_report,
        test_scaffold_correct_component_count,
        test_scaffold_positions_correct,
        test_scaffold_no_data_skip_value_field,
        test_scaffold_invalid_template,
        test_scaffold_missing_dataset_id,
        test_scaffold_has_next_steps,
        test_scaffold_all_templates,
        test_unknown_action,
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
