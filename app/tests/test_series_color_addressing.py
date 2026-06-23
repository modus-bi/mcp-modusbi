"""ЧАСТЬ 2: series-color addressing — generic цвет-слаги → anchored visuals.<серия>.fillColor.

Ворота (report 1034): anchored visuals.<значение_серии>.fillColor РЕНДЕРИТ цвет серии.
_expand_series_colors раскрывает generic visuals.colorPalette(список)/visuals.mainColor в
anchored fillColor по distinct-значениям серийного поля (запрос distinct в component_crud).
named-палитра(str)/autoColor НЕ раскрываются (фронт-палитра непрозрачна).
"""
import asyncio

import app.tools.component_crud as cc
from app.tools.config_schema import apply_slug_overrides, validate_config_overrides

SERIES = ["Тяжёлый", "С погибшими", "Легкий"]


def _patch_distinct(monkeypatch, values=SERIES):
    async def fake(client, ds, field, limit=50):
        return list(values)
    monkeypatch.setattr(cc, "_query_distinct_values", fake)


def test_palette_list_distributes_across_series(monkeypatch):
    _patch_distinct(monkeypatch)
    out, notes = asyncio.run(cc._expand_series_colors(
        "client", {"visuals.colorPalette": ["#ff0000", "#00ff00"]}, 531, "severity"))
    assert "visuals.colorPalette" not in out
    assert out["visuals.Тяжёлый.fillColor"] == "#ff0000"
    assert out["visuals.С погибшими.fillColor"] == "#00ff00"
    assert out["visuals.Легкий.fillColor"] == "#ff0000"  # i % len
    assert any("colorPalette раскрыт" in n for n in notes)


def test_maincolor_monochrome_all_series(monkeypatch):
    _patch_distinct(monkeypatch)
    out, _ = asyncio.run(cc._expand_series_colors(
        "client", {"visuals.mainColor": "#123456"}, 531, "severity"))
    assert "visuals.mainColor" not in out
    assert all(out[f"visuals.{s}.fillColor"] == "#123456" for s in SERIES)


def test_named_palette_not_expanded(monkeypatch):
    _patch_distinct(monkeypatch)
    out, notes = asyncio.run(cc._expand_series_colors(
        "client", {"visuals.colorPalette": "pal_2018"}, 531, "severity"))
    assert out == {"visuals.colorPalette": "pal_2018"}  # str не раскрывается
    assert notes == []


def test_no_series_field_noop(monkeypatch):
    _patch_distinct(monkeypatch)
    ov = {"visuals.colorPalette": ["#ff0000"]}
    out, notes = asyncio.run(cc._expand_series_colors("client", ov, 531, None))
    assert out == ov and notes == []


def test_empty_distinct_degrades_gracefully(monkeypatch):
    async def empty(client, ds, field, limit=50):
        return []
    monkeypatch.setattr(cc, "_query_distinct_values", empty)
    ov = {"visuals.mainColor": "#123456"}
    out, notes = asyncio.run(cc._expand_series_colors("client", ov, 531, "severity"))
    assert out == ov  # не раскрыт, слаг сохранён
    assert any("не удалось" in n for n in notes)


def test_too_many_series_skipped(monkeypatch):
    _patch_distinct(monkeypatch, [f"s{i}" for i in range(40)])
    ov = {"visuals.colorPalette": ["#ff0000"]}
    out, notes = asyncio.run(cc._expand_series_colors("client", ov, 531, "severity"))
    assert out == ov  # >30 серий → пропуск
    assert any(">30" in n or "пропущено" in n for n in notes)


def test_expanded_overrides_render_anchored():
    """Раскрытые anchored-слаги проходят validate+apply → visuals[{anchor,fillColor}]."""
    overrides = {"visuals.Тяжёлый.fillColor": "#ff0000", "visuals.Легкий.fillColor": "#00ff00"}
    cleaned, _ = validate_config_overrides(overrides, "HsBarAMchartsChart")
    cfg = apply_slug_overrides({}, cleaned, "HsBarAMchartsChart")
    anchors = {e["anchor"]: e.get("fillColor") for e in cfg.get("visuals", [])}
    assert anchors == {"Тяжёлый": "#ff0000", "Легкий": "#00ff00"}
