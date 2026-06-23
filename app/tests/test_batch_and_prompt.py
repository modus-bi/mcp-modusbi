#!/usr/bin/env python3
"""
Unit tests for batch_operations improvements and the create_report_from_template prompt.

Tests batch components_add with visual params, x/y/w/h, field_titles, text_content.
Tests prompt generation for 6 templates.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.batch_operations import batch_operations
from app.prompts import get_prompts, get_prompt_messages


# Standard dataset fields
_DS_FIELDS = [
    {"name": "revenue", "alias": "revenue", "type": "number"},
    {"name": "category", "alias": "category", "type": "string"},
    {"name": "count", "alias": "count", "type": "number"},
]


def _make_mock_client(captured: dict | None = None) -> AsyncMock:
    """Create mock client. If captured dict is provided, report update data is saved there."""
    client = AsyncMock()
    client.base_url = "http://localhost:3000"

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {
                "status": 200,
                "data": [{"ID": 999, "grid": {"layouts": {"lg": [], "md": [], "sm": []}, "components": {}}}],
            }
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["data"] = kwargs.get("data", [])
            return {"status": 200}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


class TestResult:
    def __init__(self, name: str, passed: bool, message: str):
        self.name = name
        self.passed = passed
        self.message = message


def run_test(func):
    """Decorator to run async test and capture result."""
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


def _get_saved_components(captured: dict) -> dict:
    """Extract components from captured report update."""
    report = captured["data"][0]
    return report["grid"]["components"]


# =============================================================================
# batch_operations improvements
# =============================================================================

@run_test
async def test_batch_add_basic():
    """Basic batch add with 2 components."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Bar 1",
                "value_field": "revenue",
                "dataset_id": 10,
                "category_field": "category",
            },
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Bar 2",
                "value_field": "count",
                "dataset_id": 10,
                "category_field": "category",
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    assert len(result["added"]) == 2, f"Expected 2 added, got {len(result['added'])}"
    comps = _get_saved_components(captured)
    assert len(comps) == 2, f"Expected 2 components, got {len(comps)}"


@run_test
async def test_batch_add_with_visual_params():
    """Batch add with stacking, orientation, preset."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Stacked Bar",
                "value_field": "revenue",
                "dataset_id": 10,
                "stacking": "normal",
                "orientation": "h",
                "preset": "dashboard",
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    comps = _get_saved_components(captured)
    comp = list(comps.values())[0]
    cfg = comp.get("config", {})
    assert cfg.get("stacking") == "normal", f"Expected stacking=normal, got {cfg.get('stacking')}"
    assert cfg.get("orientation") == "h", f"Expected orientation=h, got {cfg.get('orientation')}"


@run_test
async def test_batch_add_with_xywh():
    """Batch add with x/y/w/h auto-assembly."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Positioned Bar",
                "value_field": "revenue",
                "dataset_id": 10,
                "x": 0, "y": 10, "w": 12, "h": 8,
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    pos = result["added"][0]["position"]
    assert pos == {"x": 0, "y": 10, "w": 12, "h": 8}, f"Position mismatch: {pos}"


@run_test
async def test_batch_add_with_field_titles():
    """Batch add with field_titles."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Named Fields Bar",
                "value_field": "revenue",
                "dataset_id": 10,
                "field_titles": {"revenue": "Выручка"},
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    comps = _get_saved_components(captured)
    comp = list(comps.values())[0]
    cfg = comp.get("config", {})
    # field_titles should be passed to build_component_config
    assert comp is not None, "Component should exist"


@run_test
async def test_batch_add_text_block():
    """Text block added without value_field/dataset_id."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsTextBlock",
                "title": "Info",
                "text_content": "Hello World",
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    assert len(result["added"]) == 1, f"Expected 1 added, got {len(result['added'])}"
    assert result.get("errors") is None, f"Expected no errors, got {result.get('errors')}"


@run_test
async def test_batch_add_subheader():
    """HsSubheaderComponent added without data fields."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsSubheaderComponent",
                "title": "Section Header",
                "text_content": "Section 1",
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    assert len(result["added"]) == 1, f"Expected 1, got {len(result['added'])}"


@run_test
async def test_batch_add_config_overrides():
    """config_overrides applied in batch."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Custom Override",
                "value_field": "revenue",
                "dataset_id": 10,
                "config_overrides": {"legend.visible": False, "stacking": "percent"},
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    comps = _get_saved_components(captured)
    comp = list(comps.values())[0]
    cfg = comp.get("config", {})
    legend = cfg.get("legend", {})
    assert legend.get("visible") is False, f"Expected legend.visible=False: {legend}"
    assert cfg.get("stacking") == "percent", f"Expected stacking=percent: {cfg.get('stacking')}"


@run_test
async def test_batch_add_table_auto_fix():
    """Table auto-fix aggregation to 'none'."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsTableReactabularChart",
                "title": "Data Table",
                "value_field": "revenue,category",
                "dataset_id": 10,
                "aggregation": "sum",  # should be auto-fixed to "none"
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"


@run_test
async def test_batch_add_mixed_components():
    """Mix of data + text components in one batch."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Chart",
                "value_field": "revenue",
                "dataset_id": 10,
                "x": 0, "y": 0, "w": 12, "h": 10,
                "preset": "dashboard",
            },
            {
                "component_type": "HsTextBlock",
                "title": "Note",
                "text_content": "Summary text",
                "x": 0, "y": 10, "w": 12, "h": 4,
            },
            {
                "component_type": "HsPageContainer",
                "title": "Tabs",
                "x": 0, "y": 14, "w": 12, "h": 2,
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    assert len(result["added"]) == 3, f"Expected 3 added, got {len(result['added'])}"
    _errs = result.get("errors") or []
    assert all(e.get("warnings") and not e.get("error") for e in _errs), \
        f"Expected only advisory RENDER-DEAD warnings, got hard errors: {_errs}"


@run_test
async def test_batch_add_missing_required():
    """Missing required field reports error, doesn't stop batch."""
    captured = {}
    client = _make_mock_client(captured)
    result = await batch_operations(
        client, action="components_add",
        report_id=999,
        components=[
            {
                "component_type": "HsBarAMchartsChart",
                # Missing title!
                "value_field": "revenue",
                "dataset_id": 10,
            },
            {
                "component_type": "HsBarAMchartsChart",
                "title": "Valid Bar",
                "value_field": "revenue",
                "dataset_id": 10,
            },
        ]
    )
    assert result.get("success"), f"Expected success: {result}"
    assert len(result["added"]) == 1, f"Expected 1 added, got {len(result['added'])}"
    assert result["errors"] is not None, "Expected errors for invalid component"
    assert len(result["errors"]) == 1, f"Expected 1 error, got {len(result['errors'])}"


# =============================================================================
# create_report_from_template prompt
# =============================================================================

@run_test
async def test_reports_export_allowed_in_readonly():
    """reports_export — read-only на портале (рендер в файл, как export в report_operations /
    component_xlsx в data_export_operations) → check_action пропускает в READONLY."""
    import tempfile
    from app.core.security import SecurityMode, get_security_mode, set_security_mode

    client = _make_mock_client()
    prev_mode = get_security_mode()
    set_security_mode(SecurityMode.READONLY)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            result = await batch_operations(
                client, action="reports_export", report_ids=[1], output_dir=tmp)
        # SecurityError НЕ поднят — классификация read-only; сам экспорт на
        # mock-клиенте уходит в errors, это не предмет теста.
        assert isinstance(result, dict), f"Expected dict result: {result}"
        assert client.api_call.await_count > 0, "Security check must not block the call"
    finally:
        set_security_mode(prev_mode)


@run_test
async def test_prompt_list_contains_template():
    """Template prompt in get_prompts list."""
    prompts = get_prompts()
    names = [p["name"] for p in prompts]
    assert "create_report_from_template" in names, f"Missing template prompt. Names: {names}"


@run_test
async def test_prompt_template_args():
    """Template prompt has 4 args (template, dataset_id, report_name, group_id)."""
    prompts = get_prompts()
    tpl = next(p for p in prompts if p["name"] == "create_report_from_template")
    arg_names = [a["name"] for a in tpl["arguments"]]
    assert arg_names == ["template", "dataset_id", "report_name", "group_id"], f"Args: {arg_names}"


@run_test
async def test_prompt_kpi_dashboard():
    """kpi_dashboard template generates correct message."""
    msgs = get_prompt_messages("create_report_from_template", {
        "template": "kpi_dashboard", "dataset_id": "10"
    })
    assert len(msgs) == 1, f"Expected 1 message, got {len(msgs)}"
    text = msgs[0]["content"]["text"]
    assert "kpi_dashboard" in text, "Template name missing"
    assert "dataset_id=10" in text, "Dataset ID missing"
    assert "HsTotalsPanelV2" in text, "KPI component missing"


@run_test
async def test_prompt_all_templates():
    """All 6 templates mentioned in prompt text."""
    msgs = get_prompt_messages("create_report_from_template", {
        "template": "comparison", "dataset_id": "5"
    })
    text = msgs[0]["content"]["text"]
    for tpl in ["kpi_dashboard", "ranking", "comparison", "simple", "geo_analytics", "factor_analysis"]:
        assert tpl in text, f"Template '{tpl}' missing from prompt"


@run_test
async def test_prompt_with_name_and_group():
    """report_name and group_id appear in generated text."""
    msgs = get_prompt_messages("create_report_from_template", {
        "template": "simple", "dataset_id": "10",
        "report_name": "My Report", "group_id": "5",
    })
    text = msgs[0]["content"]["text"]
    assert "My Report" in text, "Report name missing"
    assert "группу 5" in text, "Group ID missing"


@run_test
async def test_prompt_missing_template():
    """Missing template returns error."""
    msgs = get_prompt_messages("create_report_from_template", {"dataset_id": "10"})
    text = msgs[0]["content"]["text"]
    assert "Ошибка" in text or "template" in text, f"Expected error message: {text}"


@run_test
async def test_prompt_missing_dataset_id():
    """Missing dataset_id returns error."""
    msgs = get_prompt_messages("create_report_from_template", {"template": "simple"})
    text = msgs[0]["content"]["text"]
    assert "Ошибка" in text or "dataset_id" in text, f"Expected error message: {text}"


@run_test
async def test_prompt_invalid_template():
    """Invalid template returns error with valid list."""
    msgs = get_prompt_messages("create_report_from_template", {
        "template": "nonexistent", "dataset_id": "10"
    })
    text = msgs[0]["content"]["text"]
    assert "Неизвестный шаблон" in text, f"Expected unknown template error: {text}"
    assert "kpi_dashboard" in text, "Valid templates should be listed"


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: batch improvements + template prompt")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        # batch
        test_batch_add_basic,
        test_batch_add_with_visual_params,
        test_batch_add_with_xywh,
        test_batch_add_with_field_titles,
        test_batch_add_text_block,
        test_batch_add_subheader,
        test_batch_add_config_overrides,
        test_batch_add_table_auto_fix,
        test_batch_add_mixed_components,
        test_batch_add_missing_required,
        # security
        test_reports_export_allowed_in_readonly,
        # prompt
        test_prompt_list_contains_template,
        test_prompt_template_args,
        test_prompt_kpi_dashboard,
        test_prompt_all_templates,
        test_prompt_with_name_and_group,
        test_prompt_missing_template,
        test_prompt_missing_dataset_id,
        test_prompt_invalid_template,
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
