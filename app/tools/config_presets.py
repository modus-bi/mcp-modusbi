"""
Config presets for MCP component styling.

Each preset is a dict of {slug: value} using slugs from SLUG_SCHEMA.
Merge order: preset → atomic params → user config_overrides (user wins).

"""

from __future__ import annotations

from typing import Any


PRESETS: dict[str, dict[str, Any]] = {
    "minimal": {
        "legend.visible": False,
        "labels.visible": False,
        "outline.enabled": False,
        "showtitle": False,
        "margin.l": 0,
        "margin.r": 0,
        "margin.t": 0,
        "margin.b": 0,
    },
    "presentation": {
        "legend.visible": True,
        "legend.position": "bottom-center",
        "legend.fontSize": 16,
        "labels.visible": True,
        "labels.fontSize": 14,
        "fontSize": 16,
        "showtitle": True,
        "margin.t": 20,
        "margin.b": 15,
        "outline.enabled": True,
        "outline.width": 1,
    },
    "dashboard": {
        "legend.visible": True,
        "legend.position": "auto",
        "legend.fontSize": 10,
        "labels.visible": False,
        "fontSize": 11,
        "margin.l": 2,
        "margin.r": 2,
        "margin.t": 5,
        "margin.b": 2,
    },
    "dark": {
        "bgColor": "rgba(30,30,30,1)",
        "legend.bgColor": "rgba(40,40,40,0.8)",
        "legend.visible": True,
        "balloon.bgColor": "rgba(50,50,50,0.9)",
    },
    "print": {
        "legend.visible": True,
        "legend.position": "bottom-center",
        "labels.visible": True,
        "outline.enabled": True,
        "outline.width": 2,
        "bgColor": "rgba(255,255,255,1)",
        "showtitle": True,
        "fontSize": 14,
    },
    "kpi": {
        "showtitle": True,
        "outline.enabled": False,
        "margin.l": 0,
        "margin.r": 0,
        "margin.t": 5,
        "margin.b": 5,
    },
}
