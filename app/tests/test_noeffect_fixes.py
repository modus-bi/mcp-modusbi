"""Tests for slug-to-frontend-key mapping of theme and pie geometry.

- table.theme: the frontend matches config.theme against
  [theme_classic/blue/dark/compact/compact2], so a free string like "dark"
  is mapped via an enum + value_map.
- pie visuals.startAngle/innerRadius: the frontend reads TOP-LEVEL
  startAngle/innerRadius, not visuals[], so these are written at top level.
"""
from app.tools.config_schema import apply_slug_overrides, validate_config_overrides

TABLE = "HsTableReactabularChart"
PIE = "HsPieAMchartsChart"


def test_table_theme_friendly_alias_maps_to_theme_prefix():
    for friendly, real in [("dark", "theme_dark"), ("blue", "theme_blue"),
                           ("classic", "theme_classic"), ("compact", "theme_compact"),
                           ("light", "theme_classic")]:
        cl, _ = validate_config_overrides({"table.theme": friendly}, TABLE)
        cfg = apply_slug_overrides({}, cl, TABLE)
        assert cfg.get("theme") == real, (friendly, cfg)


def test_table_theme_real_value_passthrough():
    cl, _ = validate_config_overrides({"table.theme": "theme_compact2"}, TABLE)
    cfg = apply_slug_overrides({}, cl, TABLE)
    assert cfg.get("theme") == "theme_compact2"


def test_table_theme_invalid_rejected():
    cl, w = validate_config_overrides({"table.theme": "bogus"}, TABLE)
    assert "table.theme" not in cl and w


def test_pie_startangle_top_level_not_visuals():
    cl, _ = validate_config_overrides({"visuals.startAngle": 120}, PIE)
    cfg = apply_slug_overrides({}, cl, PIE)
    assert cfg.get("startAngle") == 120
    assert cfg.get("visuals") is None  # not stored in visuals[]


def test_pie_innerradius_top_level_and_clamp():
    cl, _ = validate_config_overrides({"visuals.innerRadius": 30}, PIE)
    cfg = apply_slug_overrides({}, cl, PIE)
    assert cfg.get("innerRadius") == 30
    # max 45 (frontend ×2%)
    cl2, _ = validate_config_overrides({"visuals.innerRadius": 90}, PIE)
    cfg2 = apply_slug_overrides({}, cl2, PIE)
    assert cfg2.get("innerRadius") == 45
