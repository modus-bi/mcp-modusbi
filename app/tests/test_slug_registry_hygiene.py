#!/usr/bin/env python3
"""
Гигиена реестра слагов + спорные json-пути + guard анти-дубль-ключ.

Запуск: `python app/tests/test_slug_registry_hygiene.py` или pytest.
"""
import re
import sys
import collections
from pathlib import Path

_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root))

from app.tools.config_schema import (
    apply_slug_overrides, validate_config_overrides, SLUG_SCHEMA,
)


# --- Tabs: orientation поддерживает "v" ---
def test_tabs_orientation_vertical():
    cleaned, _ = validate_config_overrides({"tabs.orientation": "v"}, "HsTabsPanel")
    assert cleaned.get("tabs.orientation") == "v", cleaned


# --- Pivot: numbersEnabled не deprecated, пишет numbers.enabled ---
def test_pivot_numbers_not_deprecated():
    assert "deprecated" not in SLUG_SCHEMA["pivot.numbersEnabled"], SLUG_SCHEMA["pivot.numbersEnabled"]
    cfg = apply_slug_overrides({}, {"pivot.numbersEnabled": True}, "HsPivotChart")
    assert cfg.get("numbers", {}).get("enabled") is True, cfg


# --- Sunburst: groupPercent больше не applies_to sunburst ---
def test_groupPercent_not_sunburst():
    assert "sunburstChart" not in SLUG_SCHEMA["labels.groupPercent"]["applies_to"]
    cleaned_s, _ = validate_config_overrides({"labels.groupPercent": 5.0}, "HsSunburstChart")
    assert "labels.groupPercent" not in cleaned_s  # skip на sunburst
    cleaned_p, _ = validate_config_overrides({"labels.groupPercent": 5.0}, "HsPieAMchartsChart")
    assert "labels.groupPercent" in cleaned_p     # работает на pie


# --- sunburst.visibleLayers → visibleLayersNumber (render-key) ---
def test_sunburst_visible_layers_to_initial():
    cfg = apply_slug_overrides({}, {"sunburst.visibleLayers": 3}, "HsSunburstChart")
    assert cfg.get("visibleLayersNumber") == 3 and "visibleLayers" not in cfg, cfg


# --- tilemap.legendPosition новый; legendX/Y deprecated→skip ---
def test_tilemap_legend_xy_nested():
    # tilemap хранит позицию легенды как legend.positionX/positionY (вложенно)
    cfg = apply_slug_overrides({}, {"tilemap.legendX": "left", "tilemap.legendY": "top"}, "HsTilemapChart")
    assert cfg["legend"]["positionX"] == "left", cfg
    assert cfg["legend"]["positionY"] == "top", cfg
    # старый top-level legendPosition больше не плодим
    assert "legendPosition" not in cfg, cfg


# --- deprecated → skip (общий механизм) ---
def test_deprecated_slug_skipped():
    cfg = apply_slug_overrides({}, {"viewType.resetEnabled": True}, "HsFilterControlPanel")
    assert "resetEnabled" not in cfg, cfg
    cfg2 = apply_slug_overrides({}, {"map.clusterMarkers": True}, "HsMapLeafletChart")
    assert "clusterMarkers" not in cfg2, cfg2


# --- map.initialZoom остаётся рабочим override (НЕ deprecated) ---
def test_map_initialzoom_still_works():
    assert "deprecated" not in SLUG_SCHEMA["map.initialZoom"]
    cfg = apply_slug_overrides({"initialZoom": 5}, {"map.initialZoom": 12}, "HsMapLeafletChart")
    assert cfg.get("initialZoom") == 12, cfg


# --- GUARD: нет дублирующихся ключей в SLUG_SCHEMA ---
def test_no_duplicate_slug_keys():
    src = (_root / "app" / "tools" / "config_schema.py").read_text(encoding="utf-8")
    start = src.index("SLUG_SCHEMA")
    end = src.index("\n}\n", start)  # первое закрытие dict на уровне модуля
    keys = re.findall(r'^\s{4}"([^"]+)":\s*\{', src[start:end], re.M)
    dups = [k for k, c in collections.Counter(keys).items() if c > 1]
    assert not dups, f"Дублирующиеся ключи SLUG_SCHEMA: {dups}"
    assert len(keys) > 300, f"подозрительно мало ключей: {len(keys)}"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    print(f"Running {len(tests)} registry hygiene tests...\n")
    for t in tests:
        try:
            t(); print(f"  ✅ {t.__name__}"); passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {type(e).__name__}: {e}"); failed += 1
    print(f"\nResults: {passed}/{len(tests)} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
