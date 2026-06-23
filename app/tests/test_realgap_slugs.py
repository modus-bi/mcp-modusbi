#!/usr/bin/env python3
"""
Real-gap слаги (контрол на фронте есть, slug не было).

Проверяют, что каждый слаг пишет значение в подтверждённый фронтом json-путь.
Чистые функции config_schema. Запуск: `python app/tests/test_realgap_slugs.py` или pytest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.tools.config_schema import apply_slug_overrides, validate_config_overrides


def _with_values_axis():
    return {"axes": [{"type": "categories"}, {"type": "values"}]}


def _vaxis(cfg):
    for ax in cfg["axes"]:
        if ax["type"] == "values":
            return ax
    return {}


def _caxis(cfg):
    for ax in cfg["axes"]:
        if ax["type"] == "categories":
            return ax
    return {}


# --- оси: реальные фронт-ключи ---
def test_axes_value_props():
    # value-ось: showFirst/LastLabel/Tick (bool), rangeMode (enum)
    for slug, key in [
        ("axes.firstLabel", "showFirstLabel"), ("axes.firstTick", "showFirstTick"),
        ("axes.lastLabel", "showLastLabel"), ("axes.lastTick", "showLastTick"),
    ]:
        cfg = apply_slug_overrides(_with_values_axis(), {slug: False}, "HsLineAMchartsChart")
        assert _vaxis(cfg).get(key) is False, (slug, cfg)
    cfg = apply_slug_overrides(_with_values_axis(), {"axes.rangeMode": "tozero"}, "HsLineAMchartsChart")
    assert _vaxis(cfg).get("rangeMode") == "tozero", cfg
    # customZoom — на ось КАТЕГОРИЙ
    cfg = apply_slug_overrides(_with_values_axis(), {"axes.customZoom": True}, "HsLineAMchartsChart")
    assert _caxis(cfg).get("customZoom") is True, cfg


# --- bypassCollisions: рендер читает top-level config.bypassCheckCollisions ---
def test_labels_bypass_collisions():
    cfg = apply_slug_overrides({}, {"labels.bypassCollisions": True}, "HsBarAMchartsChart")
    assert cfg["bypassCheckCollisions"] is True, cfg


def test_labels_outer_angle_pie():
    cfg = apply_slug_overrides({}, {"labels.outerLabelsAngle": 45}, "HsPieAMchartsChart")
    assert cfg["labels"]["outerLabelsAngle"] == 45, cfg


def test_labels_values_nested_treemap():
    cfg = apply_slug_overrides({}, {"labels.valuesFontSize": 14, "labels.valuesTopMargin": 8}, "HsTreeMap")
    assert cfg["labels"]["value"]["fontsize"] == 14, cfg
    assert cfg["labels"]["value"]["topMargin"] == 8, cfg


# --- доп. ось / стилизация ---
def test_main_extra_axis():
    # фронт читает main.extraAxis вложенно
    cfg = apply_slug_overrides({}, {"main.extraAxis": True}, "HsBarAMchartsChart")
    assert cfg["main"]["extraAxis"] is True, cfg


def test_visuals_chart_type():
    cfg = apply_slug_overrides({}, {"visuals.chartType": "bar"}, "HsBarAMchartsChart")
    assert cfg.get("visualType") == "bar" and "chartType" not in cfg, cfg
    # markerDistance/outlineColor — per-series visuals[], не styleCommons


# --- фильтр-селектор ---
def test_viewType_modes():
    cfg = apply_slug_overrides({}, {
        "viewType.addInvertedSwitch": True,
        "viewType.clearSelection": True,
        "viewType.unlimitedSearch": True,
    }, "HsFilterControlPanel")
    assert cfg.get("addInversedFilter") is True, cfg
    assert cfg.get("clearSelection") is True, cfg
    assert cfg.get("unlimitedSearch") is True, cfg


# --- карта: аннотация ---
def test_map_annotation_text():
    cfg = apply_slug_overrides({}, {"map.annotationText": "Привет"}, "HsMapLeafletChart")
    assert cfg.get("annotation") == "Привет", cfg


# --- markers leaf-rename: clusteringThreshold→clusterizationSize (render-key) ---
def test_markers_leaf_rename():
    cfg = apply_slug_overrides({"markers": {}}, {
        "map.markers.clusteringThreshold": 100,
        "map.markers.tooltipWordWrap": True,
        "map.markers.labelMinZoom": 5,
    }, "HsMapLeafletChart")
    assert cfg["markers"]["clusterizationSize"] == 100, cfg
    assert cfg["markers"]["lineWrap"] is True, cfg
    assert cfg["markers"]["minZoomLevel"] == 5, cfg
    # старые (несуществующие во фронте) ключи НЕ пишутся
    assert "clusteringThreshold" not in cfg["markers"], cfg
    assert "tooltipWordWrap" not in cfg["markers"], cfg


# --- validate принимает новые слаги для нужного типа ---
def test_validate_accepts_new_slugs():
    cleaned, warnings = validate_config_overrides(
        {"axes.customZoom": True, "main.extraAxis": True}, "HsBarAMchartsChart")
    assert "axes.customZoom" in cleaned and "main.extraAxis" in cleaned, (cleaned, warnings)
    # applies_to гейт: outerLabelsAngle только для pie → на bar предупреждение+skip
    cleaned2, warnings2 = validate_config_overrides(
        {"labels.outerLabelsAngle": 45}, "HsBarAMchartsChart")
    assert "labels.outerLabelsAngle" not in cleaned2, (cleaned2, warnings2)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    print(f"Running {len(tests)} real-gap slug tests...\n")
    for t in tests:
        try:
            t(); print(f"  ✅ {t.__name__}"); passed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {type(e).__name__}: {e}"); failed += 1
    print(f"\nResults: {passed}/{len(tests)} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
