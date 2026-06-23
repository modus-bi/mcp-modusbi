#!/usr/bin/env python3
"""
Unit tests for P5 (map geokeys: geodata_list, map_set_geokeys, map_get_geokeys).

Tests geodata API listing and geokeys config manipulation on map components.
"""

import asyncio
import copy
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
            print(f"  \u2705 {name}")
        except AssertionError as e:
            results.append(TestResult(name, False, str(e)))
            print(f"  \u274c {name}: {e}")
        except Exception as e:
            results.append(TestResult(name, False, f"Exception: {e}"))
            print(f"  \u274c {name}: {type(e).__name__}: {e}")
    return wrapper


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

_MAP_COMPONENT = {
    "type": "HsMapLeafletChart",
    "config": {
        "type": "HsMapLeafletChart",
        "chartType": "mapLeaflet",
        "caption__ru": "Test Map",
        "datasetId": 100,
        "axes": [
            {"type": "filters", "fields": []},
            {
                "type": "categories",
                "fields": [
                    {
                        "id": "__field_abc123",
                        "name": "region",
                        "type": "string",
                        "datasetId": 100,
                    }
                ],
            },
            {
                "type": "values",
                "fields": [
                    {
                        "id": "__field_val456",
                        "name": "total_count",
                        "type": "number",
                        "datasetId": 100,
                        "agg": "sum",
                    }
                ],
            },
        ],
    },
}

_MAP_WITH_GEOKEYS = {
    "type": "HsMapLeafletChart",
    "config": {
        "type": "HsMapLeafletChart",
        "chartType": "mapLeaflet",
        "caption__ru": "Map with geokeys",
        "datasetId": 100,
        "geokeys": {
            "__field_abc123": {
                "type": "fo.geojson.json",
                "geofield": "NAME",
            }
        },
        "axes": [
            {"type": "filters", "fields": []},
            {
                "type": "categories",
                "fields": [
                    {
                        "id": "__field_abc123",
                        "name": "region",
                        "type": "string",
                        "datasetId": 100,
                    }
                ],
            },
            {
                "type": "values",
                "fields": [
                    {
                        "id": "__field_val456",
                        "name": "total_count",
                        "type": "number",
                        "datasetId": 100,
                        "agg": "sum",
                    }
                ],
            },
        ],
    },
}

_TABLE_COMPONENT = {
    "type": "HsTableReactabularChart",
    "config": {
        "type": "HsTableReactabularChart",
        "chartType": "tableChart",
        "caption__ru": "Test Table",
    },
}

_GEODATA_RESPONSE = {
    "status": 200,
    "data": [
        {"name": "fo.geojson.json", "type": "geojson", "description": "Федеральные округа"},
        {"name": "ao.geojson.json", "type": "geojson", "description": "Автономные округа"},
        {"name": "russia_regions_adm4_2022.geojson.json", "type": "geojson", "description": "Регионы РФ"},
    ],
}


def _make_mock_client(
    component: dict | None = None,
    captured: dict | None = None,
    geodata: dict | None = None,
) -> AsyncMock:
    """Create mock client with optional component config and geodata response."""
    client = AsyncMock()
    client.base_url = "http://localhost:3000"
    comp = copy.deepcopy(component or _MAP_COMPONENT)

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {
                "status": 200,
                "data": [{
                    "ID": 999,
                    "grid": {
                        "layouts": {"lg": [{"i": "0", "x": 0, "y": 0, "w": 24, "h": 15}]},
                        "components": {"0": comp},
                    },
                }],
            }
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["data"] = kwargs.get("data", [])
            return {"status": 200}
        return {"status": 200, "data": []}

    async def mock_api_get(path: str, **kwargs):
        if path == "geodata":
            return geodata or _GEODATA_RESPONSE
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    client.api_get = AsyncMock(side_effect=mock_api_get)
    return client


# =============================================================================
# geodata_list tests
# =============================================================================

@run_test
async def test_geodata_list_returns_list():
    """P5/D1: geodata_list returns available GeoJSON files."""
    client = _make_mock_client()
    result = await component_operations(client, action="geodata_list")
    assert result.get("success"), f"Expected success: {result}"
    assert result["count"] == 3
    names = [g["name"] for g in result["geodata"]]
    assert "fo.geojson.json" in names
    assert "ao.geojson.json" in names


@run_test
async def test_geodata_list_empty():
    """P5/D1: geodata_list handles empty response."""
    client = _make_mock_client(geodata={"status": 200, "data": []})
    result = await component_operations(client, action="geodata_list")
    assert result.get("success"), f"Expected success: {result}"
    assert result["count"] == 0
    assert result["geodata"] == []


# =============================================================================
# map_set_geokeys tests
# =============================================================================

@run_test
async def test_set_geokeys_basic():
    """P5/D2: Set geokeys on map component."""
    captured = {}
    client = _make_mock_client(captured=captured)
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"},
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["field_id"] == "__field_abc123"
    assert result["geokeys"]["__field_abc123"]["type"] == "fo.geojson.json"
    assert result["geokeys"]["__field_abc123"]["geofield"] == "NAME"


@run_test
async def test_set_geokeys_missing_geo_type():
    """P5/D2: Error when geo_type missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={"geofield": "NAME"},
    )
    assert "error" in result
    # API evolved to bubble/choropleth modes: incomplete config → "Invalid geokeys"
    assert "Invalid geokeys" in result["error"]


@run_test
async def test_set_geokeys_missing_geofield():
    """P5/D2: Error when geofield missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={"geo_type": "fo.geojson.json"},
    )
    assert "error" in result
    # API evolved to bubble/choropleth modes: incomplete config → "Invalid geokeys"
    assert "Invalid geokeys" in result["error"]


@run_test
async def test_set_geokeys_resolves_field_id():
    """P5/D2: Resolves field_id from categories axis."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={"geo_type": "ao.geojson.json", "geofield": "ABBREV"},
    )
    assert result.get("success"), f"Expected success: {result}"
    # Must resolve to __field_abc123 (the categories field id)
    assert "__field_abc123" in result["geokeys"]


@run_test
async def test_set_geokeys_merges_with_existing():
    """P5/D2: Merges new geokey with existing ones."""
    captured = {}
    # Start with a map that already has geokeys
    comp = copy.deepcopy(_MAP_WITH_GEOKEYS)
    # Add a second categories field
    comp["config"]["axes"][1]["fields"].append({
        "id": "__field_xyz789",
        "name": "district",
        "type": "string",
        "datasetId": 100,
    })
    client = _make_mock_client(component=comp, captured=captured)
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={
            "geo_type": "spb_districts.geojson.json",
            "geofield": "NAME",
            "category_field": "district",
        },
    )
    assert result.get("success"), f"Expected success: {result}"
    # Both geokeys should exist
    geokeys = result["geokeys"]
    assert "__field_abc123" in geokeys  # existing
    assert "__field_xyz789" in geokeys  # new


@run_test
async def test_set_geokeys_preserves_other_config():
    """P5/D2: Setting geokeys doesn't wipe other config."""
    captured = {}
    comp = copy.deepcopy(_MAP_COMPONENT)
    comp["config"]["initialZoom"] = 8
    comp["config"]["autoCenter"] = True
    client = _make_mock_client(component=comp, captured=captured)
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"},
    )
    assert result.get("success"), f"Expected success: {result}"
    # Verify saved data preserves other config
    assert captured.get("data"), "Expected report data to be saved"
    saved_cfg = captured["data"][0]["grid"]["components"]["0"]["config"]
    assert saved_cfg.get("initialZoom") == 8
    assert saved_cfg.get("autoCenter") is True


@run_test
async def test_set_geokeys_error_on_non_map():
    """P5/D2: Error when trying to set geokeys on non-map component."""
    client = _make_mock_client(component=copy.deepcopy(_TABLE_COMPONENT))
    result = await component_operations(
        client, action="map_set_geokeys",
        report_id=999, component_idx=0,
        config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"},
    )
    assert "error" in result
    assert "not a map" in result["error"]


# =============================================================================
# map_get_geokeys tests
# =============================================================================

@run_test
async def test_get_geokeys_existing():
    """P5/D2: Returns existing geokeys."""
    client = _make_mock_client(component=copy.deepcopy(_MAP_WITH_GEOKEYS))
    result = await component_operations(
        client, action="map_get_geokeys",
        report_id=999, component_idx=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["has_geokeys"] is True
    assert "__field_abc123" in result["geokeys"]
    assert result["geokeys"]["__field_abc123"]["type"] == "fo.geojson.json"


@run_test
async def test_get_geokeys_empty():
    """P5/D2: Returns empty when no geokeys."""
    client = _make_mock_client(component=copy.deepcopy(_MAP_COMPONENT))
    result = await component_operations(
        client, action="map_get_geokeys",
        report_id=999, component_idx=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    assert result["has_geokeys"] is False
    assert result["geokeys"] == {}


@run_test
async def test_get_geokeys_missing_params():
    """P5/D2: Error when report_id or component_idx missing."""
    client = _make_mock_client()
    result = await component_operations(
        client, action="map_get_geokeys",
        report_id=999,
    )
    assert "error" in result


# =============================================================================
# _get_component geokeys in response tests
# =============================================================================

@run_test
async def test_get_component_shows_geokeys():
    """P5/D2: _get_component returns geokeys when present."""
    client = _make_mock_client(component=copy.deepcopy(_MAP_WITH_GEOKEYS))
    result = await component_operations(
        client, action="get",
        report_id=999, component_idx=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    config = result["component"]["config"]
    assert "geokeys" in config
    assert "__field_abc123" in config["geokeys"]


@run_test
async def test_get_component_omits_geokeys_when_absent():
    """P5/D2: _get_component omits geokeys when not set."""
    client = _make_mock_client(component=copy.deepcopy(_MAP_COMPONENT))
    result = await component_operations(
        client, action="get",
        report_id=999, component_idx=0,
    )
    assert result.get("success"), f"Expected success: {result}"
    config = result["component"]["config"]
    assert "geokeys" not in config


# =============================================================================
# Security tests
# =============================================================================

@run_test
async def test_geodata_list_readonly_allowed():
    """P5: geodata_list uses check_action('get') — allowed in readonly."""
    from app.core.security import set_security_mode, SecurityMode
    original = SecurityMode.READWRITE
    try:
        set_security_mode(SecurityMode.READONLY)
        client = _make_mock_client()
        result = await component_operations(client, action="geodata_list")
        assert result.get("success"), f"Expected success in readonly: {result}"
    finally:
        set_security_mode(original)


@run_test
async def test_set_geokeys_blocked_readonly():
    """P5: map_set_geokeys uses check_action('update') — blocked in readonly."""
    from app.core.security import set_security_mode, SecurityMode
    original = SecurityMode.READWRITE
    try:
        set_security_mode(SecurityMode.READONLY)
        client = _make_mock_client()
        try:
            result = await component_operations(
                client, action="map_set_geokeys",
                report_id=999, component_idx=0,
                config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"},
            )
            # Should have raised SecurityError
            assert False, "Expected SecurityError in readonly mode"
        except Exception as e:
            assert "SecurityError" in type(e).__name__ or "режим" in str(e).lower() or "requires" in str(e).lower(), \
                f"Expected SecurityError, got: {type(e).__name__}: {e}"
    finally:
        set_security_mode(original)


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: P5 (map geokeys + geodata_list)")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        # geodata_list
        test_geodata_list_returns_list,
        test_geodata_list_empty,
        # map_set_geokeys
        test_set_geokeys_basic,
        test_set_geokeys_missing_geo_type,
        test_set_geokeys_missing_geofield,
        test_set_geokeys_resolves_field_id,
        test_set_geokeys_merges_with_existing,
        test_set_geokeys_preserves_other_config,
        test_set_geokeys_error_on_non_map,
        # map_get_geokeys
        test_get_geokeys_existing,
        test_get_geokeys_empty,
        test_get_geokeys_missing_params,
        # _get_component with geokeys
        test_get_component_shows_geokeys,
        test_get_component_omits_geokeys_when_absent,
        # security
        test_geodata_list_readonly_allowed,
        test_set_geokeys_blocked_readonly,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    for test_func in tests:
        await test_func(results)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r.passed:
                print(f"  - {r.name}: {r.message}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
