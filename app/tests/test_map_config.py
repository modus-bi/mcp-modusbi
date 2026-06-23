#!/usr/bin/env python3
"""
Unit tests for map configuration extension.

Tests map center slugs, builder defaults, and slug override handling
for HsMapLeafletChart and HsTilemapChart.
"""

import asyncio
import copy
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.config_schema import SLUG_SCHEMA, apply_slug_overrides, CHART_TYPE_MAP
from app.tools.builders import build_component_config


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
# Slug schema tests
# =============================================================================

@run_test
async def test_map_center_slugs_exist():
    """map.center.lat and map.center.lng slugs exist in schema."""
    assert "map.center.lat" in SLUG_SCHEMA, "Missing map.center.lat"
    assert "map.center.lng" in SLUG_SCHEMA, "Missing map.center.lng"


@run_test
async def test_map_center_slug_properties():
    """Center slugs have correct type, min, max, default."""
    lat = SLUG_SCHEMA["map.center.lat"]
    assert lat["type"] == "float"
    assert lat["min"] == -90.0
    assert lat["max"] == 90.0
    assert lat["applies_to"] == ["mapLeaflet"]

    lng = SLUG_SCHEMA["map.center.lng"]
    assert lng["type"] == "float"
    assert lng["min"] == -180.0
    assert lng["max"] == 180.0


@run_test
async def test_map_slug_count():
    """At least 37 map slugs (35 base + 2 center)."""
    map_slugs = [k for k in SLUG_SCHEMA if k.startswith("map.")]
    assert len(map_slugs) >= 37, f"Expected >=37 map slugs, got {len(map_slugs)}: {sorted(map_slugs)[:5]}..."


@run_test
async def test_tilemap_slug_count():
    """At least 16 tilemap slugs."""
    tilemap_slugs = [k for k in SLUG_SCHEMA if k.startswith("tilemap.")]
    assert len(tilemap_slugs) >= 16, f"Expected >=16 tilemap slugs, got {len(tilemap_slugs)}"


@run_test
async def test_chart_type_map_has_maps():
    """CHART_TYPE_MAP has entries for map component types."""
    assert "HsMapLeafletChart" in CHART_TYPE_MAP
    assert "HsTilemapChart" in CHART_TYPE_MAP
    assert CHART_TYPE_MAP["HsMapLeafletChart"] == "mapLeaflet"
    assert CHART_TYPE_MAP["HsTilemapChart"] == "tilemapChart"


# =============================================================================
# Builder tests
# =============================================================================

@run_test
async def test_build_map_no_initial_zoom():
    """Map builder does not write initialZoom — frontend ignores it
    (zoom is determined by Leaflet bounds), so the dead key is not written."""
    comp = build_component_config(
        component_type="HsMapLeafletChart",
        title="Test Map",
        dataset_id=10,
        category_field="region",
        value_fields=["value"],
        value_fields_type="number",
        aggregation="sum",
    )
    cfg = comp["config"]
    assert "initialZoom" not in cfg, f"Dead key initialZoom written: {cfg.get('initialZoom')}"


@run_test
async def test_build_map_has_auto_center():
    """Map builder includes autoCenter default."""
    comp = build_component_config(
        component_type="HsMapLeafletChart",
        title="Test Map",
        dataset_id=10,
        category_field="region",
        value_fields=["value"],
        value_fields_type="number",
        aggregation="sum",
    )
    cfg = comp["config"]
    assert cfg.get("autoCenter") is True


@run_test
async def test_build_map_has_markers():
    """Map builder includes markers defaults — frontend reads the
    INVERTED clusterizationOff; dead keys clustering/clusterMarkers
    are not written."""
    comp = build_component_config(
        component_type="HsMapLeafletChart",
        title="Test Map",
        dataset_id=10,
        category_field="region",
        value_fields=["value"],
        value_fields_type="number",
        aggregation="sum",
    )
    cfg = comp["config"]
    assert "markers" in cfg
    assert cfg["markers"]["showLabels"] is True
    assert cfg["markers"]["showTooltip"] is True
    # clustering off by default = clusterizationOff: True
    assert cfg["markers"]["clusterizationOff"] is True
    assert "clustering" not in cfg["markers"], "Dead key clustering written"
    assert "clusterMarkers" not in cfg["markers"], "Dead key clusterMarkers written"


@run_test
async def test_build_tilemap_has_auto_zoom():
    """Tilemap builder includes autoZoom default."""
    comp = build_component_config(
        component_type="HsTilemapChart",
        title="Test Tilemap",
        dataset_id=10,
        category_field="region",
        value_fields=["value"],
        value_fields_type="number",
        aggregation="sum",
    )
    cfg = comp["config"]
    assert cfg.get("autoZoom") is True


@run_test
async def test_build_tilemap_has_tile_size():
    """Tilemap builder includes tileSize default."""
    comp = build_component_config(
        component_type="HsTilemapChart",
        title="Test Tilemap",
        dataset_id=10,
        category_field="region",
        value_fields=["value"],
        value_fields_type="number",
        aggregation="sum",
    )
    cfg = comp["config"]
    assert cfg.get("tileSize") == 40


# =============================================================================
# Slug override tests
# =============================================================================

@run_test
async def test_slug_override_map_center():
    """map.center.lat/lng overrides create nested center object."""
    cfg = {"chartType": "mapLeaflet", "title": "Test"}
    result = apply_slug_overrides(cfg, {
        "map.center.lat": 48.856,
        "map.center.lng": 2.352,
    })
    assert "center" in result, f"Missing center in config: {list(result.keys())}"
    assert result["center"]["lat"] == 48.856, f"center.lat={result['center'].get('lat')}"
    assert result["center"]["lng"] == 2.352, f"center.lng={result['center'].get('lng')}"


@run_test
async def test_slug_override_map_initial_zoom():
    """map.initialZoom override sets initialZoom."""
    cfg = {"chartType": "mapLeaflet", "title": "Test", "initialZoom": 5}
    result = apply_slug_overrides(cfg, {
        "map.initialZoom": 12,
    })
    assert result["initialZoom"] == 12


@run_test
async def test_slug_override_map_markers():
    """map.markers.* overrides create nested markers object;
    map.markers.clustering (deprecated) writes inverted
    markers.clusterizationOff — the frontend key clustering is dead."""
    cfg = {"chartType": "mapLeaflet", "title": "Test", "markers": {}}
    result = apply_slug_overrides(cfg, {
        "map.markers.clustering": True,
        "map.markers.showLabels": False,
        "map.markers.clusteringThreshold": 100,
    })
    # clustering=True (enable) → clusterizationOff=False (inverted)
    assert result["markers"]["clusterizationOff"] is False
    assert "clustering" not in result["markers"], "Dead key clustering written"
    assert result["markers"]["showLabels"] is False
    # frontend reads clusterizationSize (slug map.markers.clusteringThreshold пишет именно его)
    assert result["markers"]["clusterizationSize"] == 100


@run_test
async def test_slug_override_map_legend():
    """map.legend.* overrides create nested legend object."""
    cfg = {"chartType": "mapLeaflet", "title": "Test", "legend": {}}
    result = apply_slug_overrides(cfg, {
        "map.legend.position": "topright",
        "map.legend.visible": False,
        "map.legend.gradeNumber": 8,
    })
    assert result["legend"]["position"] == "topright"
    assert result["legend"]["visible"] is False
    assert result["legend"]["gradeNumber"] == 8


@run_test
async def test_slug_override_tilemap():
    """tilemap.* overrides work correctly.
    startColor/endColor → legend.color[] ([start, end]); the dead scale
    section is left untouched; popup → popupEnabled (the frontend key)."""
    cfg = {"chartType": "tilemapChart", "title": "Test",
           "scale": {"startColor": "blue", "endColor": "red"}}
    result = apply_slug_overrides(cfg, {
        "tilemap.startColor": "#e3f2fd",
        "tilemap.endColor": "#1565c0",
        "tilemap.tileType": "hex",
        "tilemap.autoZoom": False,
        "tilemap.popup": True,
    })
    # gradient is read by the frontend from legend.color = [start, end]
    assert result["legend"]["color"] == ["#e3f2fd", "#1565c0"], \
        f"legend.color={result.get('legend', {}).get('color')}"
    # the dead scale section is not modified
    assert result["scale"] == {"startColor": "blue", "endColor": "red"}, \
        f"scale={result['scale']}"
    assert result["tiles"]["type"] == "hex"
    assert result.get("autoZoom") is False
    # frontend reads popupEnabled, the popup key is not written
    assert result.get("popupEnabled") is True
    assert "popup" not in result, "Dead key popup written"


@run_test
async def test_slug_override_map_background():
    """map.background.* overrides work."""
    cfg = {"chartType": "mapLeaflet", "title": "Test"}
    result = apply_slug_overrides(cfg, {
        "map.background.allowTiles": False,
        "map.background.backgroundColor": "#f0f0f0",
    })
    assert result["background"]["allowTiles"] is False
    assert result["background"]["backgroundColor"] == "#f0f0f0"


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: map configuration extension")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        # slugs
        test_map_center_slugs_exist,
        test_map_center_slug_properties,
        test_map_slug_count,
        test_tilemap_slug_count,
        test_chart_type_map_has_maps,
        # builder
        test_build_map_no_initial_zoom,
        test_build_map_has_auto_center,
        test_build_map_has_markers,
        test_build_tilemap_has_auto_zoom,
        test_build_tilemap_has_tile_size,
        # slug overrides
        test_slug_override_map_center,
        test_slug_override_map_initial_zoom,
        test_slug_override_map_markers,
        test_slug_override_map_legend,
        test_slug_override_tilemap,
        test_slug_override_map_background,
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
