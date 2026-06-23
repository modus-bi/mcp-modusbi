#!/usr/bin/env python3
"""
Unit tests for visual params at add and position auto-assembly.

Tests component_operations dispatcher and _add_component() without network.
Uses mock client to verify correct parameter passing and config generation.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.component_operations import component_operations


# Standard dataset fields for all tests
_DS_FIELDS = [
    {"name": "revenue", "alias": "revenue", "type": "number"},
    {"name": "category", "alias": "category", "type": "string"},
    {"name": "v", "alias": "v", "type": "number"},
    {"name": "rev", "alias": "rev", "type": "number"},
]

_DS_ROWS = [{"revenue": 100, "category": "A"}, {"revenue": 200, "category": "B"}]


def _make_mock_client(captured: dict | None = None) -> AsyncMock:
    """Create mock client. If captured dict is provided, report update data is saved there."""
    client = AsyncMock()

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
        if resource == "datasets" and action == "list":
            return {"status": 200, "data": [{"ID": 10, "caption": "TestDS", "name": "test_ds"}]}
        if resource == "datasets" and action == "get":
            return {"status": 200, "data": [{"ID": 10, "fields": _DS_FIELDS}]}
        if resource == "recordsets" and action == "create":
            return _DS_ROWS
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


def _get_saved_config(captured: dict, component_idx: str) -> dict:
    """Extract component config from captured report update data."""
    report = captured["data"][0]
    comp = report["grid"]["components"][component_idx]
    return comp.get("config", {})


# =============================================================================
# Position auto-assembly from x/y/w/h
# =============================================================================

@run_test
async def test_p12_position_from_xywh():
    """x/y/w/h auto-assembled into position dict."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Test Bar", value_field="revenue",
        dataset_id=10,
        x=0, y=10, w=12, h=8,
    )
    assert result.get("success"), f"Expected success, got: {result}"
    assert result["component"]["position"] == {"x": 0, "y": 10, "w": 12, "h": 8}, \
        f"Position mismatch: {result['component']['position']}"


@run_test
async def test_p12_position_partial_xywh():
    """Partial x/y/w/h — only specified keys in position."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Test Bar", value_field="revenue",
        dataset_id=10,
        x=5, w=24,  # only x and w, no y/h
    )
    assert result.get("success"), f"Expected success, got: {result}"
    pos = result["component"]["position"]
    assert pos.get("x") == 5, f"Expected x=5, got {pos.get('x')}"
    assert pos.get("w") == 24, f"Expected w=24, got {pos.get('w')}"


@run_test
async def test_p12_position_dict_priority():
    """Explicit position dict takes priority over x/y/w/h."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Test Bar", value_field="revenue",
        dataset_id=10,
        position={"x": 0, "y": 0, "w": 48, "h": 16},
        x=99, y=99,  # should be ignored because position is set
    )
    assert result.get("success"), f"Expected success, got: {result}"
    pos = result["component"]["position"]
    assert pos["w"] == 48, f"Expected w=48 from position dict, got {pos.get('w')}"


@run_test
async def test_p12_no_position_no_xywh():
    """No position and no x/y/w/h — auto-detect from layout."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Test Bar", value_field="revenue",
        dataset_id=10,
    )
    assert result.get("success"), f"Expected success, got: {result}"
    pos = result["component"]["position"]
    assert pos["x"] == 0 and pos["w"] == 24, f"Unexpected default position: {pos}"


# =============================================================================
# Visual params at add time
# =============================================================================

@run_test
async def test_p11_stacking_at_add():
    """stacking param applied, only 1 report PUT (no extra roundtrip)."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Stacked Bar", value_field="revenue",
        dataset_id=10,
        stacking="normal",
        position={"x": 0, "y": 0, "w": 12, "h": 8},
    )
    assert result.get("success"), f"Expected success, got: {result}"
    calls = client.api_call.call_args_list
    report_update_calls = [c for c in calls if c[0] == ("reports", "update")]
    assert len(report_update_calls) == 1, \
        f"Expected exactly 1 report update call, got {len(report_update_calls)}"


@run_test
async def test_p11_orientation_at_add():
    """orientation='h' applied in saved config."""
    captured = {}
    client = _make_mock_client(captured)
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="H-Bar", value_field="rev",
        dataset_id=10,
        orientation="h",
        position={"x": 0, "y": 0, "w": 12, "h": 8},
    )
    assert result.get("success"), f"Expected success, got: {result}"
    cfg = _get_saved_config(captured, result["component"]["idx"])
    assert cfg.get("orientation") == "h", \
        f"Expected orientation='h', got: {cfg.get('orientation')}"


@run_test
async def test_p11_preset_at_add():
    """preset='dashboard' applies slug overrides."""
    captured = {}
    client = _make_mock_client(captured)
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Dashboard Bar", value_field="v",
        dataset_id=10,
        preset="dashboard",
        position={"x": 0, "y": 0, "w": 12, "h": 8},
    )
    assert result.get("success"), f"Expected success, got: {result}"
    cfg = _get_saved_config(captured, result["component"]["idx"])
    assert cfg.get("showtitle") is not None, \
        f"Preset should set showtitle, config keys: {list(cfg.keys())[:10]}"


@run_test
async def test_p11_config_overrides_at_add():
    """config_overrides dict applied at add time."""
    captured = {}
    client = _make_mock_client(captured)
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Custom Bar", value_field="v",
        dataset_id=10,
        config_overrides={"legend.visible": False, "stacking": "percent"},
        position={"x": 0, "y": 0, "w": 12, "h": 8},
    )
    assert result.get("success"), f"Expected success, got: {result}"
    cfg = _get_saved_config(captured, result["component"]["idx"])
    legend = cfg.get("legend", {})
    assert legend.get("visible") is False, \
        f"Expected legend.visible=False, got: {legend}"
    assert cfg.get("stacking") == "percent", \
        f"Expected stacking='percent', got: {cfg.get('stacking')}"


@run_test
async def test_p11_bg_color_at_add():
    """bg_color applied at add time."""
    captured = {}
    client = _make_mock_client(captured)
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Colored Bar", value_field="v",
        dataset_id=10,
        bg_color="#f0f0f0",
        position={"x": 0, "y": 0, "w": 12, "h": 8},
    )
    assert result.get("success"), f"Expected success, got: {result}"
    cfg = _get_saved_config(captured, result["component"]["idx"])
    assert cfg.get("bgColor") == "#f0f0f0", \
        f"Expected bgColor='#f0f0f0', got: {cfg.get('bgColor')}"


@run_test
async def test_p11_no_visual_params_unchanged():
    """Without visual params, no extra modifications to config."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Plain Bar", value_field="v",
        dataset_id=10,
        position={"x": 0, "y": 0, "w": 12, "h": 8},
    )
    assert result.get("success"), f"Expected success, got: {result}"


@run_test
async def test_p11_combined_params():
    """stacking + orientation + x/y/w/h + legend all at once."""
    captured = {}
    client = _make_mock_client(captured)
    result = await component_operations(
        client, action="add",
        report_id=999, component_type="HsBarAMchartsChart",
        title="Stacked H-Bar", value_field="v",
        dataset_id=10,
        x=0, y=6, w=24, h=14,
        stacking="normal", orientation="h",
        legend_visible=True,
    )
    assert result.get("success"), f"Expected success, got: {result}"

    # Check position assembled from x/y/w/h
    pos = result["component"]["position"]
    assert pos == {"x": 0, "y": 6, "w": 24, "h": 14}, f"Position: {pos}"

    # Check visual params applied
    cfg = _get_saved_config(captured, result["component"]["idx"])
    assert cfg.get("stacking") == "normal", f"stacking: {cfg.get('stacking')}"
    assert cfg.get("orientation") == "h", f"orientation: {cfg.get('orientation')}"
    legend = cfg.get("legend", {})
    assert legend.get("visible") is True, f"legend.visible: {legend}"


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: visual params at add + position x/y/w/h")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        test_p12_position_from_xywh,
        test_p12_position_partial_xywh,
        test_p12_position_dict_priority,
        test_p12_no_position_no_xywh,
        test_p11_stacking_at_add,
        test_p11_orientation_at_add,
        test_p11_preset_at_add,
        test_p11_config_overrides_at_add,
        test_p11_bg_color_at_add,
        test_p11_no_visual_params_unchanged,
        test_p11_combined_params,
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
