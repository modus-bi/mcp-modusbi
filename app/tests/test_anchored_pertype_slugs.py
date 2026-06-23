#!/usr/bin/env python3
"""
Регрессы «настройки не срабатывают».

Проверяют чистые функции config_schema/builders (БД/браузер не нужны):
- anchored visuals разрешены для barChart (3-part visuals.{anchor}.{prop}).
- per-type ключи (gradient→gradientEnabled, bgColor2→backgroundColor2,
  iframe bgColor→backgroundColor, image.src→config.image).
- routing: sort.headerClickSort→sortTapable; parallel colorMin/Max→top-level;
  bubble.bigNumberSuffixes принимает массив.
- tabs.height без дубля, с min/max.
- bubble size_field CSV → несколько числовых полей оси values.

Запуск: `python app/tests/test_anchored_pertype_slugs.py` или через pytest.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.tools.config_schema import (
    apply_slug_overrides,
    validate_config_overrides,
    SLUG_SCHEMA,
)
from app.tools.builders import build_component_config


def _values_axis(result):
    for ax in result["config"]["axes"]:
        if ax.get("type") == "values":
            return ax
    return None


# --- anchored visuals для barChart ---
def test_a1_bar_anchored_visuals_allowed():
    cleaned, warnings = validate_config_overrides(
        {"visuals.dead_count.color": "#ff0000"}, "HsBarAMchartsChart")
    assert "visuals.dead_count.color" in cleaned, (cleaned, warnings)
    assert not any("anchored visuals не поддерживается" in w for w in warnings), warnings


def test_a1_bar_anchored_visuals_apply():
    cfg = apply_slug_overrides({}, {"visuals.dead_count.color": "#ff0000"}, "HsBarAMchartsChart")
    vis = cfg.get("visuals")
    assert isinstance(vis, list) and any(
        e.get("anchor") == "dead_count" and e.get("color") == "#ff0000" for e in vis), cfg


def test_a1_pie_anchored_still_rejected():
    # негатив: тип без anchored-visuals по-прежнему предупреждает
    _, warnings = validate_config_overrides(
        {"visuals.x.color": "#fff"}, "HsPieAMchartsChart")
    assert any("anchored visuals не поддерживается" in w for w in warnings), warnings


# --- per-type ключи ---
def test_a2_totals_gradient():
    cfg = apply_slug_overrides({}, {"gradient": True}, "HsTotalsPanelV2")
    assert cfg.get("gradientEnabled") is True and "gradient" not in cfg, cfg


def test_a2_totals_bgcolor2():
    cfg = apply_slug_overrides({}, {"bgColor2": "#abcdef"}, "HsTotalsPanelV2")
    assert cfg.get("backgroundColor2") == "#abcdef" and "bgColor2" not in cfg, cfg


def test_a2_iframe_bgcolor():
    cfg = apply_slug_overrides({}, {"bgColor": "#abcdef"}, "HsIframe")
    assert cfg.get("backgroundColor") == "#abcdef", cfg


def test_a2_image_src_to_image():
    # image.src пишет config.image как ОБЪЕКТ {path,ID}, не голую строку
    # (фронт ждёт объект; строка → .replace() краш ImagePanel).
    cfg = apply_slug_overrides({}, {"image.src": "http://x/y.png"}, "HsImagePanel")
    assert cfg.get("image") == {"path": "http://x/y.png", "ID": "http://x/y.png"} and "src" not in cfg, cfg


# --- routing-фиксы ---
def test_a3_sort_header_click_to_sortTapable():
    cfg = apply_slug_overrides({}, {"sort.headerClickSort": False}, "HsTableReactabularChart")
    assert cfg.get("sortTapable") is False and "headerClickSort" not in cfg, cfg


def test_a3_parallel_colormin_top_level():
    cfg = apply_slug_overrides({}, {"visuals.colorMin": "#111111"}, "HsParallelCoordsChart")
    assert cfg.get("colorMin") == "#111111", cfg
    # не должно осесть в visuals[0]
    assert not (isinstance(cfg.get("visuals"), list) and cfg["visuals"]
                and cfg["visuals"][0].get("colorMin")), cfg


def test_a3_bubble_suffixes_array_accepted():
    val = [{"number": 1000, "suffix": "k"}, {"number": 1000000, "suffix": "M"}]
    cleaned, warnings = validate_config_overrides(
        {"bubble.bigNumberSuffixes": val}, "HsBubbleAMchartsChart")
    assert cleaned.get("bubble.bigNumberSuffixes") == val, (cleaned, warnings)
    cfg = apply_slug_overrides({}, {"bubble.bigNumberSuffixes": val}, "HsBubbleAMchartsChart")
    assert cfg.get("bigNumberSuffixes") == val, cfg


# --- tabs.height без дубля, с границами ---
def test_a4_tabs_height_single_with_bounds():
    entry = SLUG_SCHEMA["tabs.height"]
    assert entry.get("min") == 20 and entry.get("max") == 100, entry
    assert entry.get("type") == "int", entry


# --- bubble size_field CSV split ---
def test_a5_bubble_size_field_csv_split():
    result = build_component_config(
        "HsBubbleAMchartsChart", "T", 5, "region",
        ["dead_count", "injured_count"], "number", "sum",
        size_field="participants_count,dtp_count",
    )
    vax = _values_axis(result)
    names = [f["name"] for f in vax["fields"]]
    assert names == ["participants_count", "dtp_count"], names
    assert all(f["type"] == "number" for f in vax["fields"]), vax["fields"]


def test_a5_bubble_size_field_single_unchanged():
    result = build_component_config(
        "HsBubbleAMchartsChart", "T", 5, "region",
        ["dead_count", "injured_count"], "number", "sum",
        size_field="participants_count",
    )
    vax = _values_axis(result)
    assert [f["name"] for f in vax["fields"]] == ["participants_count"], vax["fields"]


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    print(f"Running {len(tests)} fix tests...\n")
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed}/{len(tests)} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
