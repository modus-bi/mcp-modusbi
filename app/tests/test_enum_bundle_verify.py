"""Enum-slug verification against the frontend's accepted option values.

Ensures MCP enums only accept values the frontend actually recognizes;
values the frontend does not know are rejected (no silent no-effect).
"""
from app.tools.config_schema import validate_config_overrides as V

LINE = "HsLineAMchartsChart"
BAR = "HsBarAMchartsChart"


def _accepted(slug, val, ct):
    cleaned, _ = V({slug: val}, ct)
    return slug in cleaned


def test_markertype_frontend_shapes_only():
    # frontend markerTypes = circle/square/diamond/triangle-up/down/left/right
    for ok in ("circle", "square", "diamond", "triangle-up", "triangle-right"):
        assert _accepted("visuals.markerType", ok, LINE), ok
    for bad in ("triangle", "none"):  # bare triangle и none во фронте отсутствуют
        assert not _accepted("visuals.markerType", bad, LINE), bad


def test_linedashstyle_frontend_values():
    # frontend dash = solid/dot/dash/longdash (как style.lineMode)
    for ok in ("solid", "dot", "dash", "longdash"):
        assert _accepted("visuals.lineDashStyle", ok, LINE), ok
    for bad in ("dashed", "dotted"):  # не существуют во фронте
        assert not _accepted("visuals.lineDashStyle", bad, LINE), bad


def test_legend_order_reversed_only():
    # frontend: order==="reversed" (и "normal"); "reverse" без d невалиден
    assert _accepted("legend.order", "reversed", BAR)
    assert _accepted("legend.order", "normal", BAR)
    assert not _accepted("legend.order", "reverse", BAR)
