"""RENDER contract: _RENDER_DEAD + warn-on-apply + guard synced with verdicts.

Slugs whose config is written correctly but which the frontend does not render
(verdict v==dead) are listed in _RENDER_DEAD. validate warns on apply (the value
is still written — it is config-correct). Guard: _RENDER_DEAD MUST match the
dead verdicts in verdicts.json (otherwise the schema and reality have diverged).
"""
import json
from pathlib import Path

import pytest

from app.tools.config_schema import (
    _RENDER_DEAD,
    validate_config_overrides,
)

ROOT = Path(__file__).resolve().parents[2]
VERDICTS = ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json"

# on (short verdict name) → chart_type (as in applies_to). "*" = all components of the slug.
_ON2CT = {
    "bar": "barChart", "pie": "pieChart", "table": "table", "map": "mapLeaflet",
    "speedometer": "speedometerV2", "tilemap": "tilemapChart", "sunburst": "sunburstChart",
    "stock": "stockChart", "treegraph": "treeGraph", "filterControl": "FilterControlPanel",
    "line": "lineChart", "area": "areaChart", "pivot": "pivotChart", "bubble": "bubbleChart",
    "generic@bar": "barChart", "generic@totals": "totalsPanelV2",
    "generic": "*", "bar/line/area": "*",
}


def _dead_from_verdicts():
    v = json.loads(VERDICTS.read_text(encoding="utf-8"))["verdicts"]
    out = {}
    for slug, e in v.items():
        if e.get("v") == "dead":
            on = e.get("on", "")
            out[slug] = _ON2CT.get(on, on)
    return out


def test_render_dead_synced_with_verdicts():
    """Guard: _RENDER_DEAD == dead verdicts in verdicts.json (catches schema/reality drift)."""
    expected = _dead_from_verdicts()
    assert _RENDER_DEAD == expected, (
        "Mismatch between _RENDER_DEAD and verdicts.json (v==dead). "
        f"Only in schema: {set(_RENDER_DEAD) - set(expected)}; "
        f"only in verdicts: {set(expected) - set(_RENDER_DEAD)}"
    )


def test_validate_warns_on_render_dead():
    """Applying a render-dead slug on its component → RENDER-DEAD warning, but the slug is written."""
    cleaned, warnings = validate_config_overrides({"legend.borderWidth": 3}, "HsBarAMchartsChart")
    assert "legend.borderWidth" in cleaned, "render-dead slug must be WRITTEN (not skipped)"
    assert any("RENDER-DEAD" in w for w in warnings)


def test_render_dead_star_warns_any_component():
    """main.extraAxis ('*') warns on any of its components."""
    _, warnings = validate_config_overrides({"main.extraAxis": True}, "HsLineAMchartsChart")
    assert any("RENDER-DEAD" in w for w in warnings)


def test_render_dead_no_warning_on_other_component():
    """A render-dead slug on pie does NOT warn on bar (component-aware, no over-warning)."""
    _, warnings = validate_config_overrides({"labels.fontSize": 18}, "HsBarAMchartsChart")
    assert not any("RENDER-DEAD" in w for w in warnings)


def test_ok_slug_no_render_dead_warning():
    """A confirmed working slug (table.theme) is NOT marked render-dead."""
    assert "table.theme" not in _RENDER_DEAD
    _, warnings = validate_config_overrides({"table.theme": "dark"}, "HsTableReactabularChart")
    assert not any("RENDER-DEAD" in w for w in warnings)
