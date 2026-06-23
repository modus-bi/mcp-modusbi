"""
Config schema for MCP slug-based component configuration.

Provides:
- SLUG_SCHEMA: Registry of ~260 verified slugs with types, ranges, defaults
- validate_config_overrides(): Validate and clean user-provided overrides
- apply_slug_overrides(): Apply flat slugs to nested JSON config
- apply_title(): Per-type title handling (table vs chart vs totals)
- apply_bg_color(): Per-type background color (bgColor vs backgroundColor)
- suggest_slug(): Fuzzy matching for unknown slugs
"""

from __future__ import annotations

import copy
import json as _json
from difflib import get_close_matches
from pathlib import Path as _Path
from typing import Any


# UI-метаданные слагов (название контрола и секция config-панели фронта).
# Отдаётся LLM в list_slugs.
try:
    SLUG_UI_META: dict[str, dict[str, str]] = _json.loads(
        (_Path(__file__).parent / "slug_ui_meta.json").read_text(encoding="utf-8"))
except Exception:
    SLUG_UI_META = {}


def slug_ui_info(slug: str) -> dict[str, str]:
    """UI-контекст слага: {ui_label, ui_section} из config-панели фронта (или {})."""
    return SLUG_UI_META.get(slug, {})


def enrich_slug(slug: str, schema: dict[str, Any]) -> dict[str, Any]:
    """schema + ui_label/ui_section для вывода LLM (не мутирует SLUG_SCHEMA)."""
    ui = SLUG_UI_META.get(slug)
    if not ui:
        return schema
    return {**schema, "ui_label": ui.get("ui_label"), "ui_section": ui.get("ui_section")}


# ============================================================
# SLUG_SCHEMA — Registry of all verified MCP slugs
# Source: builders.py configs, API responses, real JSON configs
# ============================================================

SLUG_SCHEMA: dict[str, dict[str, Any]] = {
    # ================================================
    # UNIVERSAL: All components (30 of 30)
    # Source: builders.py — ALL builders create these fields
    # ================================================

    # --- margin (5 slugs) ---
    # JSON path: config.margin.{l,r,t,b,pad}
    "margin.l":             {"type": "int", "min": 0, "max": 100, "default": 5},
    "margin.r":             {"type": "int", "min": 0, "max": 100, "default": 10},
    "margin.t":             {"type": "int", "min": 0, "max": 100, "default": 10},
    "margin.b":             {"type": "int", "min": 0, "max": 100, "default": 5},
    "margin.pad":           {"type": "int", "min": 0, "max": 50, "default": 0},

    # --- outline (3 slugs) ---
    # JSON path: config.outline.{enabled,width,color}
    "outline.enabled":      {"type": "bool", "default": False},
    "outline.width":        {"type": "int", "min": 0, "max": 20, "default": 4},
    "outline.color":        {"type": "color", "default": "#DDDFE4"},

    # --- main/top-level (13 slugs) ---
    # JSON path: config.{property} (top-level)
    "showtitle":            {"type": "bool", "default": True},
    "noexport":             {"type": "bool", "default": False},
    "nocopy":               {"type": "bool", "default": False},
    # subtitle: подзаголовок под title. Top-level config.subtitle.
    # 11 типов: barChart, lineChart, pieChart, stockChart, sunburstChart,
    # parallelCoordsChart, treeGraph, treeMap, totalsPanelV2, subheader, table.
    # Не applies_to: radarChart, bubbleChart, speedometerV2, tilemapChart,
    # comparisonChart, mapLeafletChart, pivotChart, textBlock, tabsPanel,
    # imagePanel, iframe, audioplayer, FilterControlPanel и др.
    # Фронт читает через getLocal — `subtitle__ru` приоритетнее, потом fallback
    # на `subtitle`. Через MCP пишем только `subtitle` (без __ru) — фронт
    # отрендерит благодаря fallback в любой локали.
    "subtitle":             {"type": "str", "default": "", "applies_to": [
        "barChart", "lineChart", "pieChart", "stockChart", "sunburstChart",
        "parallelCoordsChart", "treeGraph", "treeMap", "totalsPanelV2",
        "subheader", "table",
    ]},
    "bgColor":              {"type": "color", "default": "rgba(255,255,255,1)"},
    "bgColor2":             {"type": "color", "default": None},
    "orientation":          {"type": "enum", "values": ["v", "h"], "default": "v"},
    "fontSize":             {"type": "int", "min": 6, "max": 72, "default": 12},
    "numberPrecision":      {"type": "int", "min": -1, "max": 10, "default": -1},
    "percentPrecision":     {"type": "int", "min": 0, "max": 10, "default": 2},
    "scrollbars":           {"type": "bool", "default": False},
    "gradient":             {"type": "bool", "default": False},
    "stacking":             {"type": "enum", "values": ["none", "normal", "percent"], "default": "none"},
    # «Отразить зеркально» (KPI)
    "flip":                 {"type": "bool", "default": False, "applies_to": ["totalsPanelV2"]},
    # --- KPI (totalsPanelV2) ДИЗАЙН: per-element (visuals[anchor].*) + top-level ---
    # anchor-элементы карточки: value (значение), caption (заголовок), subcaption
    # (подзаголовок), trend (индикатор дельты). Запись в config.visuals[anchor].{prop}
    # (apply-ветки anchored 3/4-part). ui_section = панель настроек элемента KPI.
    "visuals.value.color":        {"type": "color", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Цвет значения", "ui_section": "Значение"},
    "visuals.value.font.size":    {"type": "float", "min": 0.5, "max": 8, "default": 2.8, "applies_to": ["totalsPanelV2"], "ui_label": "Размер значения (em)", "ui_section": "Значение"},
    "visuals.value.font.weight":  {"type": "int", "min": 100, "max": 900, "default": 600, "applies_to": ["totalsPanelV2"], "ui_label": "Жирность значения", "ui_section": "Значение"},
    "visuals.value.font.family":  {"type": "str", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Шрифт значения", "ui_section": "Значение"},
    "visuals.value.outlineColor": {"type": "color", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Цвет обводки значения", "ui_section": "Значение"},
    "visuals.value.outlineWidth": {"type": "int", "min": 0, "max": 5, "default": 0, "applies_to": ["totalsPanelV2"], "ui_label": "Ширина обводки значения (px)", "ui_section": "Значение"},
    "visuals.value.visible":      {"type": "bool", "default": True, "applies_to": ["totalsPanelV2"], "ui_label": "Показывать значение", "ui_section": "Значение"},
    "visuals.value.decimals":     {"type": "int", "min": -1, "max": 10, "default": -1, "applies_to": ["totalsPanelV2"], "ui_label": "Знаков после запятой (значение)", "ui_section": "Значение"},
    "visuals.value.font.style":   {"type": "enum", "values": ["normal", "italic"], "default": "normal", "applies_to": ["totalsPanelV2"], "ui_label": "Начертание значения", "ui_section": "Значение"},
    "visuals.value.link":         {"type": "str", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Ссылка по клику (значение)", "ui_section": "Значение"},
    "visuals.value.linkTarget":   {"type": "enum", "values": ["_blank", "_self"], "default": "_blank", "applies_to": ["totalsPanelV2"], "ui_label": "Открывать ссылку в", "ui_section": "Значение"},
    "visuals.caption.color":      {"type": "color", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Цвет заголовка", "ui_section": "Заголовок"},
    "visuals.caption.font.size":  {"type": "float", "min": 0.5, "max": 4, "default": 1.0, "applies_to": ["totalsPanelV2"], "ui_label": "Размер заголовка (em)", "ui_section": "Заголовок"},
    "visuals.caption.font.weight":{"type": "int", "min": 100, "max": 900, "default": 400, "applies_to": ["totalsPanelV2"], "ui_label": "Жирность заголовка", "ui_section": "Заголовок"},
    "visuals.caption.visible":    {"type": "bool", "default": True, "applies_to": ["totalsPanelV2"], "ui_label": "Показывать заголовок", "ui_section": "Заголовок"},
    "visuals.subcaption.color":   {"type": "color", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Цвет подзаголовка", "ui_section": "Подзаголовок"},
    "visuals.subcaption.font.size":{"type": "float", "min": 0.5, "max": 4, "default": 1.0, "applies_to": ["totalsPanelV2"], "ui_label": "Размер подзаголовка (em)", "ui_section": "Подзаголовок"},
    "visuals.subcaption.visible": {"type": "bool", "default": True, "applies_to": ["totalsPanelV2"], "ui_label": "Показывать подзаголовок", "ui_section": "Подзаголовок"},
    "visuals.trend.color":        {"type": "color", "default": None, "applies_to": ["totalsPanelV2"], "ui_label": "Цвет индикатора тренда", "ui_section": "Тренд"},
    "visuals.trend.visible":      {"type": "bool", "default": True, "applies_to": ["totalsPanelV2"], "ui_label": "Показывать индикатор тренда", "ui_section": "Тренд"},
    # top-level дизайн KPI (path_write)
    "gradientDirection":    {"type": "int", "min": -180, "max": 180, "default": 0, "applies_to": ["totalsPanelV2"], "json_path": "gradientDirection", "path_write": True, "ui_label": "Направление градиента (°)", "ui_section": "Фон"},
    "textAlign":            {"type": "enum", "values": ["left", "center", "right"], "default": "center", "applies_to": ["totalsPanelV2"], "json_path": "textAlign", "path_write": True, "ui_label": "Выравнивание текста", "ui_section": "Макет"},
    "truncateTitle":        {"type": "bool", "default": False, "applies_to": ["totalsPanelV2"], "json_path": "truncateTitle", "path_write": True, "ui_label": "Обрезать заголовок", "ui_section": "Макет"},
    "hideSpinner":          {"type": "bool", "default": False},
    # «Другая операция» по клику (config.link.operation)
    "link.operation":       {"type": "str", "default": None},
    # растянуть chart на всю ширину/высоту контейнера для
    # bar/line/pie/stock. areaChart использует общий builder с lineChart.
    "expandH":              {"type": "bool", "default": False, "applies_to": [
        "barChart", "lineChart", "areaChart", "pieChart", "stockChart",
    ]},
    "expandV":              {"type": "bool", "default": False, "applies_to": [
        "barChart", "lineChart", "areaChart", "pieChart", "stockChart",
    ]},

    # ================================================
    # CHARTS: bar, line, area, pie, radar, bubble, stock
    # ================================================

    # --- legend (10 slugs) ---
    # JSON path: config.legend.{property}
    "legend.visible":       {"type": "bool", "default": True},
    "legend.position":      {"type": "enum", "values": ["auto", "top-center", "bottom-center", "middle-left", "middle-right", "top-left", "top-right", "bottom-left", "bottom-right"], "default": "auto"},
    "legend.order":         {"type": "enum", "values": ["normal", "reversed"], "default": "normal"},
    "legend.orientation":   {"type": "enum", "values": ["h", "v"], "default": "h"},
    "legend.fontSize":      {"type": "int", "min": 6, "max": 40, "default": 12},
    "legend.bgColor":       {"type": "color", "default": None},
    "legend.borderColor":   {"type": "color", "default": None},
    "legend.borderWidth":   {"type": "int", "min": 0, "max": 5, "default": 0},
    "legend.reverse":       {"type": "bool", "default": False},
    "legend.percent":       {"type": "bool", "default": False},

    # --- labels (10 slugs, base) ---
    # JSON path: config.labels.{property}
    "labels.visible":       {"type": "bool", "default": False},
    "labels.position":      {"type": "enum", "values": ["auto", "inside", "outside"], "default": "auto"},
    "labels.fontSize":      {"type": "int", "min": 6, "max": 40, "default": 12, "json_path": "labels.inner.fontsize", "path_write": True},
    "labels.labelsColor":   {"type": "color", "default": None, "json_path": "labels.inner.color", "path_write": True},
    "labels.angle":         {"type": "int", "min": -90, "max": 90, "default": 0},
    "labels.hidePercent":   {"type": "float", "min": 0, "max": 5, "default": 0},
    "labels.template":      {"type": "str", "default": None},
    # Nested inner/outer labels (3-level path)
    "labels.outer.fontsize": {"type": "int", "min": 6, "max": 40, "default": 12},
    "labels.outer.color":   {"type": "color", "default": "rgba(68,68,68,1)"},
    "labels.inner.fontsize": {"type": "int", "min": 6, "max": 40, "default": 12},

    # --- labels PIE-specific (3 extra slugs) ---
    "labels.groupPercent":  {"type": "float", "min": 0, "max": 5, "default": 0.5, "applies_to": ["pieChart"]},
    "labels.groupCount":    {"type": "int", "min": 0, "max": 100, "default": 9, "applies_to": ["pieChart"]},
    "labels.switchControlNumberOfSegments": {"type": "bool", "default": False, "applies_to": ["pieChart"]},

    # --- axes: CATEGORY axis (8 slugs) ---
    # JSON path: config.axes[type=categories].{property}
    "axes.categoryGrid":       {"type": "bool", "default": False, "json_path": "axes[categories].showgrid"},
    "axes.categoryLabels":     {"type": "bool", "default": True, "json_path": "axes[categories].showlabels"},
    "axes.categoryScale":      {"type": "bool", "default": True, "json_path": "axes[categories].showscale"},
    "axes.categoryTitle":      {"type": "bool", "default": False, "json_path": "axes[categories].showtitle"},
    "axes.categoryLabelAngle": {"type": "int", "min": -90, "max": 90, "default": 0, "json_path": "axes[categories].tickangle", "path_write": True},
    # горизонтальный скролл категорий
    "axes.categoryScrollable": {"type": "bool", "default": False, "json_path": "axes[categories].scrollable", "path_write": True},
    # подписи min/max на оси значений
    "axes.valueShowMin":       {"type": "bool", "default": False, "json_path": "axes[values].showMin", "path_write": True},
    "axes.valueShowMax":       {"type": "bool", "default": False, "json_path": "axes[values].showMax", "path_write": True},
    "axes.categoryScrollbar":  {"type": "bool", "default": False, "json_path": "axes[categories].fixedZoom"},
    "axes.categoryMinGridWidth": {"type": "int", "min": 0, "max": 500, "default": 0, "json_path": "axes[categories].minGridWidth"},
    "axes.categoryMaxLabelWidth": {"type": "int", "min": 0, "max": 500, "default": 0, "json_path": "axes[categories].maxLabelWidth"},

    # --- axes: VALUE axis (7 slugs) ---
    # JSON path: config.axes[type=values].{property}
    "axes.valueGrid":          {"type": "bool", "default": False, "json_path": "axes[values].showgrid"},
    "axes.valueLabels":        {"type": "bool", "default": True, "json_path": "axes[values].showlabels"},
    "axes.valueScale":         {"type": "bool", "default": True, "json_path": "axes[values].showscale"},
    "axes.valueTitle":         {"type": "bool", "default": False, "json_path": "axes[values].showtitle"},
    "axes.scaleType":          {"type": "enum", "values": ["-", "linear", "log"], "default": "-", "json_path": "axes[values].scaleType"},
    "axes.labelsAccuracy":     {"type": "int", "min": 0, "max": 10, "default": 2, "json_path": "axes[values].labelsAccuracy"},
    "axes.autoZoom":           {"type": "bool", "default": False, "json_path": "axes[values].autoZoom"},
    "axes.selectedFieldIndex": {"type": "int", "min": -2, "max": 20, "default": -2, "json_path": "axes[values].selectedFieldIndex"},
    "axes.sortable":           {"type": "bool", "default": True, "json_path": "axes[values].sortable"},

    # --- balloon / tooltip (5 slugs) ---
    # JSON path: config.balloon.{property}
    "balloon.combine":      {"type": "bool", "default": False, "json_path": "balloon.allSeriesPop", "path_write": True, "invert": True},
    "balloon.template":     {"type": "str", "default": None, "json_path": "balloonTemplate", "path_write": True},
    "balloon.fontSize":     {"type": "int", "min": 6, "max": 40, "default": 12, "json_path": "balloon.fontsize", "path_write": True},
    "balloon.fontColor":    {"type": "color", "default": None, "json_path": "balloon.color", "path_write": True},
    "balloon.bgColor":      {"type": "color", "default": None, "json_path": "balloon.bgcolor", "path_write": True},

    # --- data: barChart color (2 slugs) ---
    # JSON path: config.baseColor, config.colorStep (TOP-LEVEL)
    "data.baseColor":           {"type": "color", "default": None, "applies_to": ["barChart", "pieChart"]},
    "data.colorStep":           {"type": "int", "min": -20, "max": 20, "default": 0, "applies_to": ["barChart", "pieChart"]},

    # --- data limits (7 slugs) ---
    # JSON path: config.{property} (TOP-LEVEL, not nested!)
    "data.rowsLimit":           {"type": "int", "min": 0, "max": 1000000, "default": 5000, "json_path": "rowsLimit"},
    "data.rowsLimitToShow":     {"type": "int", "min": 0, "max": 1000000, "default": 0, "json_path": "rowsLimitToShow"},
    "data.seriesLimitToShow":   {"type": "int", "min": 0, "max": 1000, "default": 0, "json_path": "seriesLimitToShow"},
    "data.rowsLimitToExport":   {"type": "int", "min": 0, "max": 1000000, "default": 0, "json_path": "rowsLimitToExport"},
    # data-handler читает json_path (вкл. вложенные)
    "data.autofillEmptySeries": {"type": "bool", "default": False, "json_path": "series.autoFill"},
    "data.intervalRefresh":     {"type": "bool", "default": False, "json_path": "refresh"},
    "data.intervalSeconds":     {"type": "int", "min": 0, "max": 600, "default": 60, "json_path": "refreshTime", "path_write": True},

    # --- visuals: universal chart (3 slugs) ---
    # JSON path: config.visuals[0].{property} (array!) or config.{property}
    "visuals.autoColor":        {"type": "bool", "default": True, "json_path": "styleCommons.autoColor", "path_write": True},
    "visuals.mainColor":        {"type": "color", "default": None},
    # str (named палитра) или список hex; список → component_crud раскрывает в anchored fillColor по сериям
    "visuals.colorPalette":     {"type": "any", "default": "pal_2018"},

    # --- visuals: bar (2 slugs) ---
    # фронт читает styleCommons.columnWidth.
    # Пользователь задаёт % (10..100), но amCharts3 ждёт ДОЛЮ 0..1: scale=0.01
    # пишет 40→0.4. Без scale целое трактуется как проценты и бары схлопываются
    # в сплошную полосу.
    "visuals.columnWidth":      {"type": "int", "min": 10, "max": 100, "default": 80, "applies_to": ["barChart"], "json_path": "styleCommons.columnWidth", "path_write": True, "scale": 0.01},
    "visuals.clustered":        {"type": "bool", "default": False, "applies_to": ["barChart"], "json_path": "styleCommons.clustered", "path_write": True, "invert": True},

    # --- visuals: line (6 slugs) ---
    "visuals.smoothing":        {"type": "bool", "default": False, "applies_to": ["lineChart", "areaChart"]},
    "visuals.lineWidth":        {"type": "int", "min": 1, "max": 10, "default": 2, "applies_to": ["lineChart", "areaChart"]},
    "visuals.lineDashStyle":    {"type": "enum", "values": ["solid", "dot", "dash", "longdash"], "default": "solid", "applies_to": ["lineChart", "areaChart"], "json_path": "styleCommons.lineMode", "path_write": True},
    "visuals.markerType":       {"type": "enum", "values": ["circle", "square", "diamond", "triangle-up", "triangle-down", "triangle-left", "triangle-right"], "default": "circle", "applies_to": ["lineChart", "areaChart"], "json_path": "styleCommons.markerMode", "path_write": True},
    "visuals.markerSize":       {"type": "int", "min": 0, "max": 20, "default": 5, "applies_to": ["lineChart", "areaChart"], "json_path": "styleCommons.markerWidth", "path_write": True},
    "visuals.markerLabels":     {"type": "bool", "default": False, "applies_to": ["lineChart", "areaChart", "bubbleChart"]},

    # --- visuals: area (1 slug) ---
    # DEPRECATED: фронт читает visuals[anchor].fillColor (rgba с alpha) —
    # используйте config_overrides {"visuals.<серия>.fillColor": "rgba(..,a)"}
    "visuals.fillOpacity":      {"type": "float", "min": 0, "max": 1, "default": 0.5, "applies_to": ["areaChart"], "deprecated": "use anchored visuals.<series>.fillColor (rgba with alpha)"},

    # ================================================
    # STYLE COMMONS: lineChart/areaChart global series
    # JSON path: config.styleCommons.{property}
    # ================================================

    "style.smoothing":          {"type": "float", "min": 0, "max": 2.0, "default": 0, "applies_to": ["lineChart", "areaChart", "barChart"]},
    "style.lineMode":           {"type": "enum", "values": [None, "dot", "dash", "longdash"], "default": None, "applies_to": ["lineChart", "areaChart"]},
    "style.lineWidth":          {"type": "int", "min": 1, "max": 10, "default": 2, "applies_to": ["lineChart", "areaChart"]},
    "style.markerMode":         {"type": "str", "default": "circle", "applies_to": ["lineChart", "areaChart"]},
    "style.markerWidth":        {"type": "int", "min": 0, "max": 20, "default": 0, "applies_to": ["lineChart", "areaChart"]},
    "style.outlineWidth":       {"type": "int", "min": 0, "max": 5, "default": 0, "applies_to": ["lineChart", "areaChart"]},
    "style.autoColor":          {"type": "enum", "values": [False, "gradient", "palette"], "default": False, "applies_to": ["lineChart", "areaChart", "barChart"]},
    "style.visType":            {"type": "enum", "values": [None, "line", "column", "bar", "area"], "default": None, "applies_to": ["lineChart", "areaChart"]},
    "style.labelsEnabled":      {"type": "bool", "default": None, "applies_to": ["lineChart", "areaChart"], "json_path": "labels.visible", "path_write": True},
    "style.clustered":          {"type": "bool", "default": None, "applies_to": ["lineChart", "areaChart"]},

    # ================================================
    # TABLE: HsTableReactabularChart
    # ================================================

    # --- regimes / settings (9 slugs) ---
    # JSON path: config.settings.{MappedName}
    "regimes.autoWidth":        {"type": "bool", "default": True, "json_path": "settings.AllowAutoWidth"},
    "regimes.columnDrag":       {"type": "bool", "default": True, "json_path": "settings.AllowColumnDnD"},
    "regimes.multilineHeader":  {"type": "bool", "default": True, "json_path": "settings.AllowMultilineHeader"},
    # фронт читает top-level subMode/subAllMode/fixNumber
    "regimes.subtotals":        {"type": "bool", "default": False, "json_path": "subMode", "path_write": True},
    "regimes.totals":           {"type": "bool", "default": False, "json_path": "subAllMode", "path_write": True},
    "regimes.fixedColumns":     {"type": "int", "min": 0, "max": 10, "default": 0, "json_path": "fixNumber", "path_write": True},
    "regimes.cellHeight":       {"type": "int", "min": 20, "max": 100, "default": 32, "json_path": "fixCellHeight", "path_write": True},
    "regimes.headerHeight":     {"type": "int", "min": 20, "max": 100, "default": 32, "json_path": "fixHeaderHeight", "path_write": True},
    "regimes.resizable":        {"type": "bool", "default": True, "json_path": "settings.AllowResizable"},

    # --- sort (2 slugs) ---
    # фронт-ключ sortMultiple (top-level)
    "sort.multiColumnSort":     {"type": "bool", "default": False, "json_path": "sortMultiple", "path_write": True},
    "sort.headerClickSort":     {"type": "bool", "default": True, "json_path": "sortTapable", "path_write": True},

    # --- table top-level (1 slug) ---
    # JSON path: config.linkByForRow (field ID used as URL on row click)
    "table.linkByForRow":       {"type": "str", "default": None, "applies_to": ["table"], "json_path": "linkByForRow"},
    # оформление таблицы (top-level фронт-ключи)
    "table.zebraType":          {"type": "enum", "values": ["none", "odd", "even"], "default": "none", "applies_to": ["table"], "json_path": "zebraType"},
    "table.zebraColor":         {"type": "color", "default": None, "applies_to": ["table"], "json_path": "zebraColor"},
    "table.headersBackground":  {"type": "color", "default": None, "applies_to": ["table"], "json_path": "headersBackground"},
    "table.headersColor":       {"type": "color", "default": None, "applies_to": ["table"], "json_path": "headersColor"},
    "table.theme":              {"type": "enum", "values": ["theme_classic", "theme_blue", "theme_dark", "theme_compact", "theme_compact2", "classic", "blue", "dark", "compact", "compact2", "light"], "default": None, "applies_to": ["table"], "json_path": "theme", "path_write": True,
                                 "value_map": {"classic": "theme_classic", "blue": "theme_blue", "dark": "theme_dark", "compact": "theme_compact", "compact2": "theme_compact2", "light": "theme_classic"}},
    # нумерация строк в шапке + точность чисел
    "table.showNumberLineInHeader": {"type": "bool", "default": False, "applies_to": ["table"], "json_path": "showNumberLineInHeader"},
    "table.precision":          {"type": "int", "min": -1, "max": 10, "default": -1, "applies_to": ["table"], "json_path": "precision"},

    # ================================================
    # TOTALS PANEL: HsTotalsPanelV2
    # NOTE: uses backgroundColor (NOT bgColor!)
    # ================================================

    # --- delta (2 slugs) ---
    "delta.delta":              {"type": "bool", "default": False, "applies_to": ["totalsPanelV2"], "json_path": "visuals[trend].hasTarget"},
    "delta.percent":            {"type": "bool", "default": False, "applies_to": ["totalsPanelV2"], "json_path": "visuals[trend].absolute (inverted)"},

    # ================================================
    # SPEEDOMETER: HsSpeedometerV2AMcharts
    # ================================================

    # --- grid (8 slugs) ---
    # top-level startAngle/endAngle (НЕ grid.*); у радара таких контролов нет
    "grid.startAngle":          {"type": "int", "min": 0, "max": 360, "default": 0, "applies_to": ["speedometerV2"], "json_path": "startAngle", "path_write": True},
    "grid.endAngle":            {"type": "int", "min": 0, "max": 360, "default": 360, "applies_to": ["speedometerV2"], "json_path": "endAngle", "path_write": True},
    # фронт хранит minimum/maximum
    "grid.min":                 {"type": "float", "default": 0, "applies_to": ["speedometerV2"], "json_path": "grid.minimum", "path_write": True},
    "grid.max":                 {"type": "float", "default": 100, "applies_to": ["speedometerV2"], "json_path": "grid.maximum", "path_write": True},
    # top-level roundLimits
    "grid.roundLimits":         {"type": "bool", "default": False, "applies_to": ["speedometerV2"], "json_path": "roundLimits", "path_write": True},
    "grid.tickCount":           {"type": "int", "min": 0, "max": 100, "default": 5, "applies_to": ["speedometerV2"]},
    # оформление шкалы gauge
    "grid.width":               {"type": "int", "min": 1, "max": 100, "default": 20, "applies_to": ["speedometerV2"]},
    "grid.color":               {"type": "color", "default": None, "applies_to": ["speedometerV2"]},
    "grid.labelsColor":         {"type": "color", "default": None, "applies_to": ["speedometerV2"]},
    "grid.labelFrequency":      {"type": "int", "min": 0, "max": 10, "default": 1, "applies_to": ["speedometerV2"]},
    "grid.minorTickCount":      {"type": "int", "min": 0, "max": 10, "default": 2, "applies_to": ["speedometerV2"]},
    # фронт хранит grid.palette.gradeCount
    "grid.gradeCount":          {"type": "int", "min": 0, "max": 20, "default": 3, "applies_to": ["speedometerV2"], "json_path": "grid.palette.gradeCount", "path_write": True},
    # палитра зон шкалы (colors[] — список rgba-строк), инверсия, градиент
    "grid.paletteColors":       {"type": "any", "default": None, "applies_to": ["speedometerV2"], "json_path": "grid.palette.colors", "path_write": True},
    "grid.paletteInvert":       {"type": "bool", "default": False, "applies_to": ["speedometerV2"], "json_path": "grid.palette.invert", "path_write": True},
    "grid.gradientMode":        {"type": "bool", "default": False, "applies_to": ["speedometerV2"], "json_path": "grid.palette.gradientMode", "path_write": True},
    # «Цвет фона индикатора» — top-level backgroundColor gauge
    "gauge.backgroundColor":    {"type": "color", "default": None, "applies_to": ["speedometerV2"], "json_path": "backgroundColor", "path_write": True},

    # ================================================
    # FILTER PANEL: HsFilterControlPanel
    # ================================================

    # --- viewType (FilterControlPanel) ---
    "viewType.displayType":     {"type": "enum", "values": ["dropdown", "panel", "slider", "period", "buttons", "twofield", "list", "radio", "checkbox", "datepicker"], "default": "dropdown", "applies_to": ["FilterControlPanel"], "json_path": "filterType", "path_write": True,
                                 "value_map": {"dropdown": None, "list": "panel", "radio": "panel", "checkbox": "panel", "datepicker": "period"}},
    "viewType.multiselect":     {"type": "bool", "default": True, "applies_to": ["FilterControlPanel"], "json_path": "multipleChoice", "path_write": True},
    "viewType.resetEnabled":    {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "resetEnabled", "deprecated": "no such frontend key; see viewType.updateOnApply/updateOnCloseDropdown"},
    "viewType.searchEnabled":   {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "searchInBaseMode", "path_write": True},
    "viewType.autoApply":       {"type": "bool", "default": True, "applies_to": ["FilterControlPanel"], "json_path": "autoApply"},
    "viewType.showAll":         {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "showAll", "deprecated": "no such frontend key"},
    "viewType.updateOnApply":   {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "updateOnApply", "path_write": True},
    "viewType.updateOnCloseDropdown": {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "updateOnCloseDropdown", "path_write": True},
    "viewType.inversed":        {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "inversed", "path_write": True},
    "viewType.hideEmptyLines":  {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "hideEmptyLines", "path_write": True},
    "viewType.sortSelectedOptionsToTop": {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "sortSelectedOptionsToTop", "path_write": True},

    # ================================================
    # PIE-SPECIFIC: HsPieAMchartsChart
    # ================================================

    "visuals.innerRadius":      {"type": "int", "min": 0, "max": 45, "default": 0, "applies_to": ["pieChart"], "json_path": "innerRadius", "path_write": True},
    "visuals.startAngle":       {"type": "int", "min": -360, "max": 360, "default": 0, "applies_to": ["pieChart"], "json_path": "startAngle", "path_write": True},

    # donut + center sum + labels template
    "showDonut":                {"type": "bool", "default": False, "applies_to": ["pieChart"]},
    "radius":                   {"type": "int", "min": 0, "max": 100, "default": 80, "applies_to": ["pieChart", "radarChart"]},
    "summEnabled":              {"type": "bool", "default": False, "applies_to": ["pieChart"]},
    "summFontSize":             {"type": "int", "min": 8, "max": 72, "default": 32, "applies_to": ["pieChart"]},
    "summColor":                {"type": "color", "default": "rgba(0,0,0,1)", "applies_to": ["pieChart"]},
    # labelsTemplate переменные: [[percents]], [[value]], [[title]], [[categories]], [[tooltip]]
    "labelsTemplate":           {"type": "str", "default": "[[percents]]%", "applies_to": ["pieChart"]},
    # шаблон balloon'а (top-level, асимметрия с labelsTemplate)
    "balloonTemplate":          {"type": "str", "default": None, "applies_to": ["pieChart"]},
    # i18n-заголовок группы «Прочее» (фронт читает groupedTitle__ru)
    "labels.groupedTitle__ru":  {"type": "str", "default": None, "applies_to": ["pieChart"]},

    # ================================================
    # BAR-SPECIFIC: HsBarAMchartsChart
    # ================================================

    "visuals.columnBorderRadius": {"type": "int", "min": 0, "max": 10, "default": 0, "applies_to": ["barChart"]},

    # ================================================
    # BUBBLE-SPECIFIC: HsBubbleAMchartsChart
    # ================================================

    # фронт читает top-level minRadius/maxRadius (дефолты фронта 3/30)
    "visuals.bubbleMinSize":    {"type": "int", "min": 1, "max": 50, "default": 3, "applies_to": ["bubbleChart"], "json_path": "minRadius", "path_write": True},
    "visuals.bubbleMaxSize":    {"type": "int", "min": 5, "max": 100, "default": 30, "applies_to": ["bubbleChart"], "json_path": "maxRadius", "path_write": True},
    # top-level фронт-ключи bubble
    "bubble.zoomToEdges":       {"type": "bool", "default": False, "applies_to": ["bubbleChart"], "json_path": "zoomToBubbleEdges", "path_write": True},
    "bubble.strictMinMax":      {"type": "bool", "default": False, "applies_to": ["bubbleChart"], "json_path": "strictMinMaxEnabled", "path_write": True},
    "bubble.filterMode":        {"type": "bool", "default": True, "applies_to": ["bubbleChart"], "json_path": "filterMode", "path_write": True},
    "bubble.showScrollbars":    {"type": "bool", "default": True, "applies_to": ["bubbleChart"], "json_path": "hideScrollbars", "invert": True, "path_write": True},
    "bubble.precision":         {"type": "int", "min": -1, "max": 10, "default": -1, "applies_to": ["bubbleChart"], "json_path": "precision", "path_write": True},
    "bubble.bigNumberSuffixes": {"type": "any", "default": [], "applies_to": ["bubbleChart"], "json_path": "bigNumberSuffixes", "path_write": True},
    # легенды цвета/размера
    "bubble.legendForColor":    {"type": "bool", "default": False, "applies_to": ["bubbleChart"], "json_path": "legendForColor.enabled", "path_write": True},
    "bubble.legendForSize":     {"type": "bool", "default": False, "applies_to": ["bubbleChart"], "json_path": "legendForSize.enabled", "path_write": True},

    # ================================================
    # RADAR-SPECIFIC: HsRadarAMchartsChart
    # ================================================

    # оба ключа фронт хранит на оси values; filled — top-level
    "grid.gridType":            {"type": "enum", "values": ["circles", "polygons"], "default": "circles", "applies_to": ["radarChart"], "json_path": "axes[values].gridType", "path_write": True},
    "grid.filled":              {"type": "bool", "default": True, "applies_to": ["radarChart"], "json_path": "filled", "path_write": True},
    "grid.radarLabels":         {"type": "bool", "default": True, "applies_to": ["radarChart"], "json_path": "axes[values].radarlabels", "path_write": True},

    # ================================================
    # PIVOT-SPECIFIC: HsPivotChart
    # ================================================

    # --- totals (6 slugs) ---
    # JSON path: config.{prop} (top-level for pivot)
    "totals.grandSumsFixed":    {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "isGrandSumsFixed"},
    "totals.sumColumnAtLeft":   {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "sumColumnAtLeft"},
    "totals.noGrandSumsX":      {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "isNoGrandSumsX"},
    "totals.noGrandSumsY":      {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "isNoGrandSumsY"},
    # isNoSums = скрыть ПРОМЕЖУТОЧНЫЕ итоги (subtotals при иерархии строк);
    # общие «Итого» скрывают isNoGrandSumsX (строки) / isNoGrandSumsY (колонки)
    "totals.noSums":            {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "isNoSums"},
    "totals.sumRowAtTop":       {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "sumRowAtTop"},

    # --- pivot config (15 slugs) ---
    # JSON path: config.{prop} (top-level for pivot)
    "pivot.theme":                   {"type": "enum", "values": [None, "light"], "default": None, "applies_to": ["pivotChart"]},
    "pivot.borderColor":             {"type": "color", "default": "", "applies_to": ["pivotChart"]},
    "pivot.fontFamily":              {"type": "str", "default": None, "applies_to": ["pivotChart"]},
    "pivot.headerFontSize":          {"type": "int", "min": 8, "max": 72, "default": None, "applies_to": ["pivotChart"]},
    "pivot.headerBackgroundColor":   {"type": "color", "default": "", "applies_to": ["pivotChart"]},
    "pivot.headerTextColor":         {"type": "color", "default": "", "applies_to": ["pivotChart"]},
    "pivot.headerAling":             {"type": "enum", "values": ["left", "center", "right"], "default": "left", "applies_to": ["pivotChart"], "json_path": "headerHorTextAlignment"},
    "pivot.dateFormat":              {"type": "str", "default": "DD.MM.YYYY", "applies_to": ["pivotChart"]},
    "pivot.showPanel":               {"type": "bool", "default": False, "applies_to": ["pivotChart"]},
    "pivot.hideMeasuresHeader":      {"type": "bool", "default": False, "applies_to": ["pivotChart"]},
    "pivot.nullVisible":             {"type": "bool", "default": False, "applies_to": ["pivotChart"]},
    "pivot.groupByOptimization":     {"type": "bool", "default": False, "applies_to": ["pivotChart"]},
    "pivot.autoHeightEnabled":       {"type": "bool", "default": True, "applies_to": ["pivotChart"]},
    # точность чисел (вкл/значение): фронт Pivot читает top-level precision
    # (-1=авто); объект numbers.* нигде не читается.
    "pivot.numbersEnabled":          {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "numbers.enabled", "path_write": True},
    "pivot.precision":               {"type": "int", "min": -1, "max": 10, "default": -1, "applies_to": ["pivotChart"], "json_path": "precision", "path_write": True},
    # высота шапки + перенос слов в шапке: фронт читает headerHorCellHeight (0=авто)
    "pivot.headerHeight":            {"type": "int", "min": 0, "max": 300, "default": 0, "applies_to": ["pivotChart"], "json_path": "headerHorCellHeight", "path_write": True},
    "pivot.headerHorWordWrapEnabled": {"type": "bool", "default": False, "applies_to": ["pivotChart"], "json_path": "headerHorWordWrapEnabled"},
    "pivot.autoWidthEnabled":        {"type": "bool", "default": True, "applies_to": ["pivotChart"]},
    # Note: isNoGrandSumsY is covered by totals.noGrandSumsY

    # ================================================
    # MAP-SPECIFIC: HsMapLeafletChart
    # ================================================

    # DEPRECATED: фронт эти ключи не читает (зум = Leaflet-bounds,
    # кластеризация = markers.clusterizationOff) — оставлены для совместимости
    "map.initialZoom":          {"type": "int", "min": 1, "max": 18, "default": 5, "applies_to": ["mapLeaflet"], "json_path": "initialZoom"},
    "map.clusterMarkers":       {"type": "bool", "default": False, "applies_to": ["mapLeaflet"], "json_path": "clusterMarkers", "deprecated": "кластеризация = map.markers.clustering (clusterizationOff)"},

    # --- map general (5 slugs) ---
    "map.filterMode":           {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.autoCenter":           {"type": "bool",  "default": True,  "applies_to": ["mapLeaflet"]},
    "map.multilayerMode":       {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.showSmallObjects":     {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    # фронт читает titleOpacity
    "map.titleBrightness":      {"type": "float", "min": 0.0, "max": 1.0, "default": 0.8, "applies_to": ["mapLeaflet"], "json_path": "titleOpacity"},
    # прозрачность аннотации
    "map.annotationOpacity":    {"type": "float", "min": 0.0, "max": 1.0, "default": 0.8, "applies_to": ["mapLeaflet"], "json_path": "annotationOpacity"},

    # --- map.legend.* (6 slugs) ---
    "map.legend.position":      {"type": "enum", "values": ["bottomright", "topright", "topleft", "bottomleft"], "default": "bottomright", "applies_to": ["mapLeaflet"]},
    "map.legend.visible":       {"type": "bool",  "default": True,  "applies_to": ["mapLeaflet"]},
    "map.legend.discrete":      {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.legend.gradeNumber":   {"type": "int",   "min": 2, "max": 20, "default": 5, "applies_to": ["mapLeaflet"]},
    "map.legend.invertColors":  {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.legend.withFilters":   {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},

    # --- map.markers.* (18 slugs) ---
    "map.markers.showLabels":          {"type": "bool",  "default": True,  "applies_to": ["mapLeaflet"]},
    "map.markers.labelsSize":          {"type": "int",   "min": 8, "max": 24, "default": 12, "applies_to": ["mapLeaflet"]},
    "map.markers.showValues":          {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.markers.valuesPrecision":     {"type": "int",   "min": -1, "max": 10, "default": -1, "applies_to": ["mapLeaflet"]},
    "map.markers.showTooltip":         {"type": "bool",  "default": True,  "applies_to": ["mapLeaflet"]},
    "map.markers.tooltipSize":         {"type": "int",   "min": 8, "max": 40, "default": 12, "applies_to": ["mapLeaflet"], "json_path": "markers.tooltipTextSize", "path_write": True},
    "map.markers.tooltipWordWrap":     {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"], "json_path": "markers.lineWrap", "path_write": True},
    "map.markers.labelMinZoom":        {"type": "int",   "min": 0, "max": 18, "default": 0,  "applies_to": ["mapLeaflet"], "json_path": "markers.minZoomLevel", "path_write": True},
    # фронт хранит ИНВЕРТИРОВАННЫЙ ключ markers.clusterizationOff
    "map.markers.clustering":          {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"], "json_path": "markers.clusterizationOff", "invert": True, "path_write": True},
    "map.markers.clusteringThreshold": {"type": "int",   "min": 10, "max": 200, "default": 50, "applies_to": ["mapLeaflet"], "json_path": "markers.clusterizationSize", "path_write": True},
    "map.markers.minSize":             {"type": "int",   "min": 0, "max": 50, "default": 0,  "applies_to": ["mapLeaflet"]},
    "map.markers.maxSize":             {"type": "int",   "min": 0, "max": 100, "default": 50, "applies_to": ["mapLeaflet"]},
    "map.markers.gradeNumberForSize":  {"type": "int",   "min": 1, "max": 10, "default": 3,  "applies_to": ["mapLeaflet"]},
    "map.markers.isLinearScale":       {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.markers.fixedExtent":         {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"]},
    "map.markers.maxValue":            {"type": "float", "default": 100.0, "applies_to": ["mapLeaflet"]},
    "map.markers.showMaxValue":        {"type": "bool",  "default": False, "applies_to": ["mapLeaflet"], "json_path": "markers.maxValueShow", "path_write": True},
    "map.markers.maxValueColor":       {"type": "color", "default": "red", "applies_to": ["mapLeaflet"]},

    # --- map.center.* (2 slugs) — DEPRECATED: фронт центрирует
    # по autoCenter/bounds, ключ center не читает ---
    "map.center.lat":                  {"type": "float", "min": -90.0, "max": 90.0, "default": 55.751, "applies_to": ["mapLeaflet"]},
    "map.center.lng":                  {"type": "float", "min": -180.0, "max": 180.0, "default": 37.618, "applies_to": ["mapLeaflet"]},

    # --- map.background.* (4 slugs) ---
    "map.background.allowTiles":       {"type": "bool", "default": True,  "applies_to": ["mapLeaflet"]},
    "map.background.allowTiles2":      {"type": "bool", "default": False, "applies_to": ["mapLeaflet"]},
    "map.background.tileUrl":          {"type": "str",  "default": "{s}.tile.osm.org/{z}/{x}/{y}.png", "applies_to": ["mapLeaflet"]},
    "map.background.backgroundColor":  {"type": "color", "default": "gray", "applies_to": ["mapLeaflet"]},

    # ================================================
    # TILEMAP-SPECIFIC: HsTilemapChart (расширение)
    # ================================================

    "tilemap.startColor":       {"type": "color", "default": "blue",   "applies_to": ["tilemapChart"]},
    "tilemap.endColor":         {"type": "color", "default": "red",    "applies_to": ["tilemapChart"]},
    "tilemap.tileType":         {"type": "enum",  "values": ["square", "hex"], "default": "square", "applies_to": ["tilemapChart"]},
    # фронт хранит размер в px (int), не enum
    "tilemap.nameFontSize":     {"type": "int",  "min": 6, "max": 40, "default": 12, "applies_to": ["tilemapChart"]},
    "tilemap.specialTiles":     {"type": "bool",  "default": False, "applies_to": ["tilemapChart"]},
    "tilemap.grouping":         {"type": "bool",  "default": True,  "applies_to": ["tilemapChart"], "json_path": "grouping.enabled", "path_write": True},
    "tilemap.deltaK":           {"type": "float", "min": 0.0, "max": 0.5, "default": 0.15, "applies_to": ["tilemapChart"], "json_path": "grouping.deltaK", "path_write": True},
    "tilemap.allowTiles":       {"type": "bool",  "default": True,  "applies_to": ["tilemapChart"]},
    "tilemap.bgTileColor":      {"type": "color", "default": "gray", "applies_to": ["tilemapChart"]},
    "tilemap.legendVisible":    {"type": "bool",  "default": True,  "applies_to": ["tilemapChart"]},
    # tilemap хранит позицию легенды РАЗДЕЛЬНО и ВЛОЖЕННО —
    # config.legend.positionX (left/right) + config.legend.positionY (top/bottom).
    "tilemap.legendX":          {"type": "enum",  "values": ["left", "right"], "default": "right", "applies_to": ["tilemapChart"], "json_path": "legend.positionX", "path_write": True},
    "tilemap.legendY":          {"type": "enum",  "values": ["top", "bottom"], "default": "bottom", "applies_to": ["tilemapChart"], "json_path": "legend.positionY", "path_write": True},
    # фронт-ключ popupEnabled
    "tilemap.popup":            {"type": "bool",  "default": False, "applies_to": ["tilemapChart"], "json_path": "popupEnabled", "path_write": True},
    "tilemap.autoZoom":         {"type": "bool",  "default": True,  "applies_to": ["tilemapChart"]},
    "tilemap.tileSize":         {"type": "int",   "min": 10, "max": 100, "default": 40, "applies_to": ["tilemapChart"]},
    "tilemap.filterMode":       {"type": "bool",  "default": False, "applies_to": ["tilemapChart"]},

    # ================================================
    # SUNBURST-SPECIFIC: HsSunburstChart
    # ================================================

    "sunburst.filterMode":      {"type": "bool",  "default": False, "applies_to": ["sunburstChart"]},
    "sunburst.darkLabels":      {"type": "bool",  "default": False, "applies_to": ["sunburstChart"]},
    "sunburst.splittedMode":    {"type": "bool",  "default": False, "applies_to": ["sunburstChart"]},
    "sunburst.ellipsisLength":  {"type": "int",   "min": 1, "max": 50, "default": 15, "applies_to": ["sunburstChart"]},
    "sunburst.minPercent":      {"type": "float", "min": 0.0, "max": 100.0, "default": 0.0, "applies_to": ["sunburstChart"]},
    "sunburst.precision":       {"type": "int",   "min": 0, "max": 10, "default": 0,  "applies_to": ["sunburstChart"]},
    "sunburst.layerExpand":     {"type": "bool",  "default": False, "applies_to": ["sunburstChart"]},
    "sunburst.visibleLayers":   {"type": "int",   "min": 1, "max": 10, "default": 2,  "applies_to": ["sunburstChart"], "json_path": "visibleLayersNumber", "path_write": True},
    "sunburst.layerButtons":    {"type": "bool",  "default": False, "applies_to": ["sunburstChart"]},
    "sunburst.colorsEnabled":   {"type": "bool",  "default": True,  "applies_to": ["sunburstChart"]},
    "sunburst.fontSize":        {"type": "float", "min": 0.4, "max": 2.0, "default": 0.8, "applies_to": ["sunburstChart"]},
    "sunburst.fontFamily":      {"type": "str",   "default": "Arial", "applies_to": ["sunburstChart"]},

    # ================================================
    # TREEMAP-SPECIFIC: HsTreeMap
    # ================================================

    # фронт хранит bool (как map/tilemap/sunburst filterMode)
    "treemap.filterMode":       {"type": "bool", "default": True, "applies_to": ["treeMap"], "json_path": "filterMode", "path_write": True},
    # точность чисел
    "treemap.precision":        {"type": "int", "min": -1, "max": 10, "default": -1, "applies_to": ["treeMap"], "json_path": "precision", "path_write": True},
    # balloon.visible (handler balloon подхватит)
    "balloon.visible":          {"type": "bool", "default": True},

    # ================================================
    # PARALLEL COORDS-SPECIFIC: HsParallelCoordsChart
    # ================================================

    "visuals.colorMin":         {"type": "color", "default": "#d94e5d", "applies_to": ["parallelCoordsChart"], "json_path": "colorMin", "path_write": True},
    "visuals.colorMax":         {"type": "color", "default": "#eac736", "applies_to": ["parallelCoordsChart"], "json_path": "colorMax", "path_write": True},
    "parallel.tableSize":       {"type": "int", "min": 0, "max": 1000, "default": 100, "applies_to": ["parallelCoordsChart"], "json_path": "tableSize", "path_write": True},

    # ================================================
    # STOCK-SPECIFIC: HsStockAMchartsChart
    # ================================================

    "stock.dateFormat":         {"type": "str", "default": "yyyy-MM-dd", "applies_to": ["stockChart"]},
    "stock.dateZoomPanel":      {"type": "bool", "default": False, "applies_to": ["stockChart"]},
    "stock.dateRangePanel":     {"type": "bool", "default": False, "applies_to": ["stockChart"]},
    "stock.scrollbarDisabled":  {"type": "bool", "default": False, "applies_to": ["stockChart"], "json_path": "scrollbar.disabled"},
    "stock.altAxisEnabled":     {"type": "bool", "default": False, "applies_to": ["stockChart"], "json_path": "altAxis.enabled"},
    "stock.dateAxisMinGridDistance": {"type": "int", "min": 10, "max": 200, "default": 30, "applies_to": ["stockChart"], "json_path": "dateAxis.minGridDistance"},
    "stock.dateAxisMaxWidth":   {"type": "int", "min": 0, "max": 500, "default": 0, "applies_to": ["stockChart"], "json_path": "dateAxis.maxWidth"},
    "stock.dateAxisTickangle":  {"type": "int_or_null", "min": -90, "max": 90, "default": None, "applies_to": ["stockChart"], "json_path": "dateAxis.tickangle"},
    "stock.dateAxisZigzag":     {"type": "bool", "default": False, "applies_to": ["stockChart"], "json_path": "dateAxis.zigzag"},
    "stock.refresh":            {"type": "bool", "default": False, "applies_to": ["stockChart"]},

    # ================================================
    # HIERARCHICAL FILTER: HsHierarchicalFilterPanel
    # ================================================

    "hierFilter.multipleChoice":          {"type": "bool", "default": True,  "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.bothChoice":              {"type": "bool", "default": True,  "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.inversed":                {"type": "bool", "default": False, "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.hideTitle":               {"type": "bool", "default": False, "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.filterTitle":             {"type": "str",  "default": "",    "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.headerWidth":             {"type": "int",  "default": 0, "min": 0, "max": 100, "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.searchInBaseMode":        {"type": "bool", "default": False, "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.searchInBaseMinNumber":   {"type": "int",  "default": 1, "min": 1, "max": 10,  "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.updateOnCloseDropdown":   {"type": "bool", "default": True,  "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.updateOnApply":           {"type": "bool", "default": False, "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.noLoadOptions":           {"type": "bool", "default": True,  "applies_to": ["hierarchicalFilterPanel"]},
    "hierFilter.sortSelectedOptionsToTop": {"type": "bool", "default": False, "applies_to": ["hierarchicalFilterPanel"]},

    # ================================================
    # SWITCH CONTROL PANEL: HsSwitchControlPanel
    # ================================================

    "switch.filterType":             {"type": "enum", "values": ["panel", "column"], "default": "column", "applies_to": ["SwitchControlPanel"]},
    "switch.selectorTitleOverride":  {"type": "str",  "default": "",               "applies_to": ["SwitchControlPanel"]},

    # ================================================
    # TABS PANEL: HsTabsPanel
    # ================================================

    "tabs.height":              {"type": "int", "min": 20, "max": 100, "default": 33, "applies_to": ["tabsPanel"]},
    "tabs.autoApply":           {"type": "bool", "default": True, "applies_to": ["tabsPanel"]},

    # ================================================
    # AUDIOPLAYER: HsAudioplayer (speech analytics)
    # ================================================

    "audio.progressBarColor":           {"type": "color", "default": "rgba(0, 139, 139, 1)", "applies_to": ["audioplayer"]},
    "audio.progressBarBackgroundColor": {"type": "color", "default": "", "applies_to": ["audioplayer"]},
    "audio.backgroundColor":            {"type": "color", "default": "", "applies_to": ["audioplayer"]},
    "audio.url":                        {"type": "str", "default": None, "applies_to": ["audioplayer"], "json_path": "resource.url", "path_write": True},
    "audio.uploadURL":                  {"type": "str", "default": None, "applies_to": ["audioplayer"], "json_path": "resource.uploadURL", "path_write": True},

    # ================================================
    # COMPARISON-SPECIFIC: HsComparisonChart
    # ================================================
    "comparison.object1":     {"type": "str",  "default": "",    "applies_to": ["comparisonChart"]},
    "comparison.object2":     {"type": "str",  "default": "",    "applies_to": ["comparisonChart"]},
    "comparison.showDelta":   {"type": "bool", "default": False, "applies_to": ["comparisonChart"]},
    "comparison.showPercent": {"type": "bool", "default": False, "applies_to": ["comparisonChart"]},
    "comparison.precision":   {"type": "int",  "min": -1, "max": 5, "default": -1, "applies_to": ["comparisonChart"]},

    # ================================================
    # TREEGRAPH-SPECIFIC: HsTreeGraph (GoJS)
    # ================================================

    "graph.layout":      {"type": "enum", "values": ["TreeLayout", "ForceDirectedLayout"], "default": "TreeLayout", "applies_to": ["treeGraph"]},
    "graph.zoomable":    {"type": "bool",  "default": True,  "applies_to": ["treeGraph"]},
    "graph.initialZoom": {"type": "float", "min": 0.01, "max": 5.0, "default": 0.7, "applies_to": ["treeGraph"]},

    # ================================================
    # TEXTBLOCK-SPECIFIC: HsTextBlock
    # ================================================

    "text.noexport":     {"type": "bool", "default": True, "applies_to": ["textBlock"]},
    "text.maximizable":  {"type": "bool", "default": True, "applies_to": ["textBlock"]},

    # ================================================
    # IMAGEPANEL-SPECIFIC: HsImagePanel
    # NOTE: uses backgroundColor (NOT bgColor!) — see apply_bg_color
    # ================================================

    "image.backgroundSize":     {"type": "enum", "values": ["contain", "cover", "initial", "100% auto", "auto 100%", "100% 100%"], "default": "contain", "applies_to": ["imagePanel"]},
    "image.backgroundPosition": {"type": "enum", "values": ["left top", "center top", "right top", "left center", "center center", "right center", "left bottom", "center bottom", "right bottom"], "default": "center center", "applies_to": ["imagePanel"]},
    "image.backgroundStyle":    {"type": "enum", "values": ["no-repeat", "repeat-x", "repeat-y", "repeat"], "default": "no-repeat", "applies_to": ["imagePanel"]},
    "image.titleSize":          {"type": "str", "default": "", "applies_to": ["imagePanel"]},
    "image.titleColor":         {"type": "color", "default": "", "applies_to": ["imagePanel"]},
    "image.linkName":           {"type": "str", "default": "", "applies_to": ["imagePanel"], "json_path": "link.name"},
    "image.linkTarget":         {"type": "enum", "values": ["_self", "_blank"], "default": "_self", "applies_to": ["imagePanel"], "json_path": "link.target"},

    # ── HsIframe ──
    "iframe.linkName":          {"type": "str", "default": "", "applies_to": ["iframe"], "json_path": "link.name"},
    "iframe.linkTarget":        {"type": "enum", "values": ["_self", "_blank"], "default": "_self", "applies_to": ["iframe"], "json_path": "link.target"},

    # ── HsTabsPanel ── (tabs.height определён выше с min/max 20-100)
    "tabs.orientation":         {"type": "enum", "values": ["h", "v"], "default": "h", "applies_to": ["tabsPanel"]},
    "tabs.visuals":             {"type": "any", "default": [], "applies_to": ["tabsPanel"], "json_path": "visuals"},

    # ── HsImagePanel ──
    "image.src":                {"type": "any", "default": None, "applies_to": ["imagePanel"], "json_path": "image"},

    # ================================================
    # Дополнительные слаги — фронт рисует контрол.
    # json-пути выверены по исходникам фронта; запись через path_write (_write_config_path).
    # ================================================
    # Оси значений (amCharts): первое/последнее деление и подпись, диапазон, zoom.
    # Фронт-ключи оси — showFirst/LastLabel/Tick; customZoom — контрол оси
    # КАТЕГОРИЙ; rangeMode — enum normal/tozero/tomin/tomax.
    "axes.customZoom":          {"type": "bool", "default": False, "json_path": "axes[categories].customZoom", "path_write": True},
    "axes.firstLabel":          {"type": "bool", "default": True,  "json_path": "axes[values].showFirstLabel", "path_write": True},
    "axes.firstTick":           {"type": "bool", "default": True,  "json_path": "axes[values].showFirstTick", "path_write": True},
    "axes.lastLabel":           {"type": "bool", "default": True,  "json_path": "axes[values].showLastLabel", "path_write": True},
    "axes.lastTick":            {"type": "bool", "default": True,  "json_path": "axes[values].showLastTick", "path_write": True},
    "axes.rangeMode":           {"type": "enum", "values": ["normal", "tozero", "tomin", "tomax"], "default": "normal", "json_path": "axes[values].rangeMode", "path_write": True},
    # Подписи данных
    # Фронт читает их ВЛОЖЕННО (labels.bypassCollisions / labels.outerLabelsAngle) —
    # секционный labels-handler сам пишет cfg["labels"][prop], path_write не нужен.
    "labels.bypassCollisions":  {"type": "bool", "default": False, "json_path": "bypassCheckCollisions", "path_write": True},
    "labels.outerLabelsAngle":  {"type": "int", "min": -90, "max": 90, "default": 0, "applies_to": ["pieChart"]},
    "labels.valuesFontSize":    {"type": "int", "min": 6, "max": 72, "default": 12, "applies_to": ["treeMap"], "json_path": "labels.value.fontsize", "path_write": True},
    "labels.valuesTopMargin":   {"type": "int", "min": 0, "max": 50, "default": 5, "applies_to": ["treeMap"], "json_path": "labels.value.topMargin", "path_write": True},
    # Доп. ось значений (Bar/Line/Area)
    # Фронт читает main.extraAxis вложенно — generic-handler пишет cfg["main"]["extraAxis"].
    "main.extraAxis":           {"type": "bool", "default": False, "applies_to": ["barChart", "lineChart", "areaChart"]},
    # Стилизация (top-level / styleCommons)
    "visuals.chartType":        {"type": "str", "default": None, "applies_to": ["barChart"], "json_path": "visualType", "path_write": True},
    # Фильтр-селектор (FilterControlPanel): доп. режимы
    "viewType.addInvertedSwitch": {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "addInversedFilter", "path_write": True},
    "viewType.clearSelection":  {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "clearSelection", "path_write": True},
    "viewType.unlimitedSearch": {"type": "bool", "default": False, "applies_to": ["FilterControlPanel"], "json_path": "unlimitedSearch", "path_write": True},
    # Карта: текст аннотации (рядом с map.annotationOpacity — яркость)
    "map.annotationText":       {"type": "str", "default": "", "applies_to": ["mapLeaflet"], "json_path": "annotation", "path_write": True},
}

# ================================================
# PER-COLUMN PROPERTIES: config.columns[fieldId].{prop}
# Used by HsTableReactabularChart for individual column settings.
# Slugs: columns.{fieldName}.{prop} — fieldName is resolved to fieldId
# by component_operations before calling apply_slug_overrides.
# ================================================
COLUMN_PROPS: dict[str, dict[str, Any]] = {
    "width":            {"type": "int", "min": 30, "max": 5000, "default": 100},
    "hidden":           {"type": "bool", "default": False},
    "precision":        {"type": "int", "min": 0, "max": 10, "default": 0},
    "dateFormat":       {"type": "str", "default": None},
    "title":            {"type": "str", "default": None},
    "title__ru":        {"type": "str", "default": None},
    "suffix":           {"type": "str", "default": None},
    "isLink":           {"type": "bool", "default": False},
    "isHtml":           {"type": "bool", "default": False},
    "rightAlign":       {"type": "bool", "default": False},
    "alignHorizontal":  {"type": "enum", "values": ["left", "center", "right"], "default": None},
    "alignVertical":    {"type": "enum", "values": ["top", "middle", "bottom"], "default": None},
    "lineWrap":         {"type": "bool", "default": False},
    "showSparkline":    {"type": "bool", "default": False},
    "showGradient":     {"type": "bool", "default": False},
    "valueSeparator":   {"type": "bool", "default": True},
    "transparency":     {"type": "int", "min": 0, "max": 100, "default": None},
    "visibleOrder":     {"type": "int", "min": 0, "max": 100, "default": None},
    "emptyAsNil":       {"type": "bool", "default": False},
    "isHideSame":       {"type": "bool", "default": False},
    "subtotalsEnabled": {"type": "bool", "default": False},
    "colorByFieldId":   {"type": "str", "default": None},
    "linkBy":           {"type": "str", "default": None},
    "titleByOtherField":{"type": "str", "default": None},
    "columnNullVisible":{"type": "bool", "default": None},
    "linkEnabled":      {"type": "bool", "default": False},
    "repeatValues":     {"type": "bool", "default": False},
    "searchEnabled":    {"type": "bool", "default": False},
}

# ================================================
# Conditional formatting rules for HsTableReactabularChart + HsPivotChart
# Slugs: rules.{index}.{prop} — index is 0-based rule number
# Table-only: sparklineColor. Pivot-only: isTypeHeader.
# ================================================
RULE_PROPS: dict[str, dict[str, Any]] = {
    "name":             {"type": "str",   "default": ""},
    "fieldId":          {"type": "str",   "default": None},
    "fieldById":        {"type": "str",   "default": None},
    "wholeRow":         {"type": "bool",  "default": False},
    "minimum":          {"type": "float", "default": None},
    "maximum":          {"type": "float", "default": None},
    # cons.value — "any" (float ИЛИ str). Фронт сравнивает actual == cons.value
    # напрямую для =/!=, поэтому строковые статусы работают без numeric rank.
    "cons.operator":    {"type": "enum",  "values": [">=", "<=", ">", "<", "=", "!="], "default": None},
    "cons.value":       {"type": "any",   "default": None},
    "logicOr":          {"type": "bool",  "default": False},
    "color":            {"type": "color", "default": None},
    "background":       {"type": "color", "default": None},
    "sparklineColor":   {"type": "color", "default": None},
    "indicatorType":    {"type": "enum",  "values": [None, "up", "down", "dot", "up2", "down2", "dot2"], "default": None},
    "indicatorColor":   {"type": "color", "default": None},
    "isTextBold":       {"type": "bool",  "default": False},
    "isTextItalic":     {"type": "bool",  "default": False},
    "isTextUnderline":  {"type": "bool",  "default": False},
    "hideTypeValue":    {"type": "bool",  "default": False},
    "hideTypeTotals":   {"type": "bool",  "default": False},
    "isTypeHeader":     {"type": "bool",  "default": False},
}

# Component type → slug namespace for applies_to validation.
# NOTE: These values are used ONLY for validate_config_overrides() and
# _list_slugs() — they match SLUG_SCHEMA applies_to strings.
# They may differ from builders.py chart_type_map which holds the actual
# config JSON type values the frontend expects. Both maps are intentionally
# separate: this one = slug validation namespace, that one = frontend contract.
CHART_TYPE_MAP: dict[str, str] = {
    # Charts (AMCharts)
    "HsBarAMchartsChart": "barChart",
    "HsLineAMchartsChart": "lineChart",
    "HsAreaAMchartsChart": "areaChart",
    "HsPieAMchartsChart": "pieChart",
    "HsRadarAMchartsChart": "radarChart",
    "HsBubbleAMchartsChart": "bubbleChart",
    "HsStockAMchartsChart": "stockChart",
    "HsSpeedometerV2AMcharts": "speedometerV2",
    # Charts (D3/ECharts)
    "HsSunburstChart": "sunburstChart",
    "HsParallelCoordsChart": "parallelCoordsChart",
    # Tables
    "HsTableReactabularChart": "table",
    "HsPivotChart": "pivotChart",
    "HsComparisonChart": "comparisonChart",
    # Maps
    "HsMapLeafletChart": "mapLeaflet",
    "HsTilemapChart": "tilemapChart",
    "HsTreeMap": "treeMap",
    # KPI
    "HsTotalsPanelV2": "totalsPanelV2",
    # Filters
    "HsFilterControlPanel": "FilterControlPanel",
    "HsHierarchicalFilterPanel": "hierarchicalFilterPanel",
    # Content / Utility
    "HsTextBlock": "textBlock",
    "HsTreeGraph": "treeGraph",
    "HsSubheaderComponent": "subheaderComponent",
    "HsIframe": "iframe",
    "HsImagePanel": "imagePanel",
    "HsPageContainer": "pageContainer",
    # Navigation
    "HsTabsPanel": "tabsPanel",
    # Remaining types
    "HsSwitchControlPanel": "SwitchControlPanel",
    "HsAudioplayer": "audioplayer",
}


# Module-level dispatch maps (defined once, not per-call)
_TILEMAP_MAP: dict[str, tuple[str, str]] = {
    "startColor":    ("scale",      "startColor"),
    "endColor":      ("scale",      "endColor"),
    "tileType":      ("tiles",      "type"),
    "nameFontSize":  ("tiles",      "nameFontSize"),
    "specialTiles":  ("tiles",      "specialTiles"),
    "grouping":      ("grouping",   "enabled"),
    "deltaK":        ("grouping",   "deltaK"),
    "allowTiles":    ("background", "allowTiles"),
    "bgTileColor":   ("background", "backgroundColor"),
    "legendVisible": ("legend",     "visible"),
    "legendX":       ("legend",     "positionX"),
    "legendY":       ("legend",     "positionY"),
}

_SUNBURST_MAP: dict[str, str] = {
    "visibleLayers": "visibleLayersNumber",
}


def suggest_slug(unknown_slug: str) -> str | None:
    """Suggest closest matching slug for a typo or unknown slug."""
    known = list(SLUG_SCHEMA.keys())
    matches = get_close_matches(unknown_slug, known, n=1, cutoff=0.7)
    return matches[0] if matches else None


# Prop-ключи anchored-элементов visuals[] (line/area per-series + KPI).
# 2-part visuals.* слаги схемы (legacy visuals[0]) добавляются
# динамически ниже.
_ANCHORED_VISUAL_PROPS = {
    # line/area per-series
    "smoothing", "lineWidth", "lineDashStyle", "markerType", "markerSize",
    "markerLabels", "fillColor", "color",
    # KPI (totalsPanelV2) per-element
    "negation", "decimals", "thresholdForPercent", "hasTarget", "absolute",
    # KPI per-element типографика/видимость/обводка (фронт: visuals[anchor].*)
    "font.size", "font.weight", "font.family", "font.style",
    "visible", "outlineColor", "outlineWidth", "link", "linkTarget",
}
# + все 2-part visuals-слаги схемы (visuals.lineWidth и т.п.), КРОМЕ
# path_write-переименованных (bubbleMinSize→minRadius живёт top-level,
# анкерная запись такого ключа была бы мёртвой)
_ANCHORED_VISUAL_PROPS |= {
    s.split(".", 1)[1] for s, entry in SLUG_SCHEMA.items()
    if s.startswith("visuals.") and s.count(".") == 1
    and not entry.get("path_write")
}


def _write_config_path(cfg: dict[str, Any], path: str, value: Any) -> None:
    """Записать value по json_path схемы (для слагов с path_write=True).

    Поддерживает: top-level ('roundLimits'), вложенные через точку
    ('grid.palette.gradeCount'), и axes-адресацию ('axes[values].gridType').
    """
    if path.startswith("axes[") and "]." in path:
        axis_type, prop = path[len("axes["):].split("].", 1)
        for axis in cfg.get("axes", []):
            if axis.get("type") == axis_type:
                axis[prop] = value
                return
        return  # оси нет — молча пропускаем (компонент без такой оси)
    node = cfg
    *parents, leaf = path.split(".")
    for p in parents:
        nxt = node.get(p)
        if not isinstance(nxt, dict):
            # повреждённый/нестандартный узел — пересоздаём, не падаем
            nxt = {}
            node[p] = nxt
        node = nxt
    node[leaf] = value


def _anchored_visual(cfg: dict[str, Any], anchor: str) -> dict[str, Any]:
    """Найти/создать элемент cfg.visuals[] с заданным anchor.

    Фронт привязывает per-series/per-element override к серии или элементу
    KPI исключительно по ключу anchor — запись без него молча игнорируется.
    """
    visuals = cfg.get("visuals")
    if isinstance(visuals, dict):
        # Legacy dict-конфиг: мигрируем содержимое в элемент массива,
        # НЕ затирая существующие настройки (review-major).
        visuals = [visuals]
        cfg["visuals"] = visuals
    elif not isinstance(visuals, list):
        visuals = []
        cfg["visuals"] = visuals
    for element in visuals:
        if isinstance(element, dict) and element.get("anchor") == anchor:
            return element
    element = {"anchor": anchor}
    visuals.append(element)
    return element


# Convenience-алиасы slug-ов: дружелюбное имя → канонический slug.
# donut → showDonut (фронт сам ставит innerRadius=60% при showDonut=true).
# Нормализуются в validate_config_overrides И в apply_slug_overrides;
# в SLUG_SCHEMA НЕ заводятся, чтобы не дублировать list_slugs/search.
_SLUG_ALIASES = {"donut": "showDonut"}

# Per-type переназначение top-level слагов: общий slug, но фронт-ключ
# у типа другой (KPI: precision вместо numberPrecision, backgroundColor
# вместо bgColor — как в apply_bg_color).
_TOP_LEVEL_PER_TYPE = {
    ("totalsPanelV2", "numberPrecision"): "precision",
    ("totalsPanelV2", "bgColor"): "backgroundColor",
    ("imagePanel", "bgColor"): "backgroundColor",
    # общий slug, фронт-ключ у типа другой.
    ("totalsPanelV2", "gradient"): "gradientEnabled",
    ("totalsPanelV2", "bgColor2"): "backgroundColor2",
    ("iframe", "bgColor"): "backgroundColor",            # фронт деструктит {backgroundColor}
    ("speedometerV2", "bgColor"): "backgroundColor",     # gauge faceColor = config.backgroundColor
}

# Render-dead слаги (config валиден, но рендер не применяет). slug → chart_type ("*" = везде).
# validate предупреждает, значение всё равно пишется.
_RENDER_DEAD = {
    "axes.autoZoom": "barChart", "axes.categoryLabelAngle": "barChart",
    "axes.categoryMaxLabelWidth": "barChart", "axes.categoryMinGridWidth": "barChart",
    "axes.categoryScrollbar": "barChart", "axes.labelsAccuracy": "barChart",
    "bubble.zoomToEdges": "bubbleChart", "expandH": "barChart", "expandV": "barChart",
    "fontSize": "barChart", "grid.width": "speedometerV2",
    "summColor": "pieChart", "tilemap.tileType": "tilemapChart",
    "viewType.addInvertedSwitch": "FilterControlPanel",
    "grid.gradeCount": "speedometerV2", "grid.gradientMode": "speedometerV2",
    "grid.paletteColors": "speedometerV2", "grid.paletteInvert": "speedometerV2",
    "labels.fontSize": "pieChart",
    "labels.groupedTitle__ru": "pieChart", "labels.labelsColor": "pieChart",
    "labels.outerLabelsAngle": "pieChart",
    "legend.borderWidth": "barChart",
    "legend.orientation": "barChart", "main.extraAxis": "*", "map.autoCenter": "mapLeaflet",
    "map.background.backgroundColor": "mapLeaflet", "map.center.lat": "mapLeaflet",
    "map.center.lng": "mapLeaflet", "map.initialZoom": "mapLeaflet",
    "pivot.showPanel": "pivotChart",
    "regimes.cellHeight": "table", "regimes.headerHeight": "table", "scrollbars": "barChart", "stock.dateFormat": "stockChart",
    "regimes.subtotals": "table", "sunburst.minPercent": "sunburstChart",
    "table.showNumberLineInHeader": "table", "tilemap.bgTileColor": "tilemapChart",
    "tilemap.legendX": "tilemapChart", "tilemap.legendY": "tilemapChart",
    "visuals.colorPalette": "barChart", "visuals.columnBorderRadius": "barChart",
    "visuals.innerRadius": "pieChart", "visuals.lineDashStyle": "lineChart", "visuals.mainColor": "barChart",
    "visuals.markerLabels": "bubbleChart", "visuals.startAngle": "pieChart",
    "data.colorStep": "pieChart",
}


def _coerce_slug_value(schema: dict[str, Any], slug: str, value: Any,
                       warnings: list[str]) -> tuple[Any, bool]:
    """Coerce/clamp value по type/min/max/values схемы. Возвращает (value, ok).

    ok=False — значение невалидно (warning добавлен, слаг надо пропустить).
    Используется и обычной, и anchored-веткой (чтобы visuals.{anchor}.{prop}
    тоже уважали диапазоны схемы, а не были голым passthrough).
    """
    t = schema.get("type")
    if t == "bool":
        if isinstance(value, str):
            value = value.lower() in ("true", "1", "yes")
        elif isinstance(value, int):
            value = bool(value)
        if not isinstance(value, bool):
            warnings.append(f"'{slug}': expected bool, got {type(value).__name__}")
            return value, False
    elif t == "int":
        try:
            value = int(value)
            if "min" in schema:
                value = max(schema["min"], value)
            if "max" in schema:
                value = min(schema["max"], value)
        except (ValueError, TypeError):
            warnings.append(f"'{slug}': expected int, got '{value}'")
            return value, False
    elif t == "float":
        try:
            value = float(value)
            if "min" in schema:
                value = max(schema["min"], value)
            if "max" in schema:
                value = min(schema["max"], value)
        except (ValueError, TypeError):
            warnings.append(f"'{slug}': expected float, got '{value}'")
            return value, False
    elif t == "enum":
        if value not in schema.get("values", []):
            warnings.append(f"'{slug}': '{value}' not in {schema.get('values')}")
            return value, False
    elif t == "color":
        if not isinstance(value, str) and value is not None:
            warnings.append(f"'{slug}': expected color string, got {type(value).__name__}")
            return value, False
    elif t == "str":
        value = str(value) if value is not None else None
    return value, True


def validate_config_overrides(
    overrides: dict[str, Any],
    component_type: str,
) -> tuple[dict[str, Any], list[str]]:
    """
    Validate config_overrides and return (cleaned, warnings).

    - Unknown slugs -> warning + skip (with fuzzy suggestion)
    - Wrong type -> warning + skip or coerce
    - Value out of range -> clamp to allowed range
    - applies_to mismatch -> warning + skip
    """
    cleaned: dict[str, Any] = {}
    warnings: list[str] = []

    chart_type = CHART_TYPE_MAP.get(component_type, "")

    # Convenience-алиасы (дружелюбное имя → канонический slug). Нормализуем
    # ДО валидации, чтобы echo (cleaned) и итоговый config совпадали и
    # list_slugs не загрязнялся дублями.
    if any(k in overrides for k in _SLUG_ALIASES):
        normalized: dict[str, Any] = {}
        for k, v in overrides.items():
            canon = _SLUG_ALIASES.get(k, k)
            if canon in normalized and normalized[canon] != v:
                warnings.append(
                    f"Alias collision: '{k}' conflicts with an earlier value "
                    f"for '{canon}'; keeping {canon}={normalized[canon]!r}"
                )
                continue
            normalized[canon] = v
        overrides = normalized

    for slug, value in overrides.items():
        # --- Per-column slugs: columns.{fieldId}.{prop} ---
        if slug.startswith("columns."):
            col_parts = slug.split(".", 2)
            if len(col_parts) != 3:
                warnings.append(f"Invalid column slug '{slug}': expected columns.{{fieldName}}.{{property}}")
                continue
            _, field_ref, prop = col_parts
            if chart_type not in ("table", "pivotChart", "comparisonChart"):
                warnings.append(
                    f"Column slugs apply to table/pivot/comparison, not {chart_type}")
                continue
            col_schema = COLUMN_PROPS.get(prop)
            if not col_schema:
                warnings.append(f"Unknown column property '{prop}' in '{slug}'")
                continue
            # Validate value against COLUMN_PROPS schema (reuse same logic)
            schema = col_schema
            expected_type = schema["type"]
            if expected_type == "bool":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                elif isinstance(value, int):
                    value = bool(value)
                if not isinstance(value, bool):
                    warnings.append(f"'{slug}': expected bool, got {type(value).__name__}")
                    continue
            elif expected_type == "int":
                try:
                    value = int(value)
                    if "min" in schema:
                        value = max(schema["min"], value)
                    if "max" in schema:
                        value = min(schema["max"], value)
                except (ValueError, TypeError):
                    warnings.append(f"'{slug}': expected int, got '{value}'")
                    continue
            elif expected_type == "float":
                try:
                    value = float(value)
                    if "min" in schema:
                        value = max(schema["min"], value)
                    if "max" in schema:
                        value = min(schema["max"], value)
                except (ValueError, TypeError):
                    warnings.append(f"'{slug}': expected float, got '{value}'")
                    continue
            elif expected_type == "enum":
                if value not in schema["values"]:
                    warnings.append(f"'{slug}': '{value}' not in {schema['values']}")
                    continue
            elif expected_type == "color":
                if not isinstance(value, str) and value is not None:
                    warnings.append(f"'{slug}': expected color string, got {type(value).__name__}")
                    continue
            elif expected_type == "str":
                value = str(value) if value is not None else None
            cleaned[slug] = value
            continue

        # --- anchored visuals — visuals.{anchor}.{prop} ---
        # anchor = имя серии (line/area) или элемент KPI
        # (value/caption/subcaption/trend). Prop-whitelist: 2-part visuals-слаги
        # схемы + доказанные anchored-ключи фронта.
        if slug.startswith("visuals.") and slug.count(".") >= 2:
            _, anchor, vis_prop = slug.split(".", 2)
            if not anchor:
                warnings.append(f"'{slug}': пустой anchor (формат visuals.{{anchor}}.{{prop}})")
                continue
            # anchored visuals есть только у этих семейств; известное
            # ограничение: anchor с точкой в имени серии не адресуется
            _ANCHORED_TYPES = {"lineChart", "areaChart", "speedometerV2",
                               "totalsPanelV2", "stock", "stockChart",
                               "radarChart", "barChart"}
            if chart_type and chart_type not in _ANCHORED_TYPES:
                warnings.append(
                    f"'{slug}': anchored visuals не поддерживается на "
                    f"{chart_type} (только line/area/gauge/KPI/stock)"
                )
                continue
            if vis_prop not in _ANCHORED_VISUAL_PROPS:
                warnings.append(
                    f"Unknown anchored visuals property '{vis_prop}' in '{slug}' "
                    f"(known: {sorted(_ANCHORED_VISUAL_PROPS)})"
                )
                continue
            # Если у anchored-слага есть запись в схеме (KPI-дизайн visuals.value.*
            # и т.п.) — уважать её type/min/max/values, а не пропускать сырьём.
            _anch_schema = SLUG_SCHEMA.get(slug)
            if _anch_schema:
                value, _ok = _coerce_slug_value(_anch_schema, slug, value, warnings)
                if not _ok:
                    continue
            cleaned[slug] = value
            continue

        # --- Per-rule slugs: rules.{index}.{prop} --- conditional formatting ---
        if slug.startswith("rules."):
            parts = slug[len("rules."):].split(".", 1)
            if len(parts) < 2:
                warnings.append(f"Invalid rules slug: '{slug}' (format: rules.{{n}}.{{prop}})")
                continue
            index_str, prop_path = parts
            try:
                idx = int(index_str)
                if idx < 0 or idx > 50:
                    warnings.append(f"rules index must be 0-50, got {idx}")
                    continue
            except ValueError:
                warnings.append(f"rules index must be integer, got '{index_str}'")
                continue
            if chart_type and chart_type not in ("table", "pivotChart"):
                warnings.append(f"Slug '{slug}' only applies to table/pivot, ignored for {chart_type}")
                continue
            rule_schema = RULE_PROPS.get(prop_path)
            if not rule_schema:
                close = get_close_matches(prop_path, list(RULE_PROPS.keys()), n=1, cutoff=0.6)
                if close:
                    warnings.append(f"Unknown rule prop '{prop_path}'. Did you mean '{close[0]}'?")
                else:
                    warnings.append(f"Unknown rule prop '{prop_path}'")
                continue
            # Validate value against RULE_PROPS schema (same logic as columns)
            schema = rule_schema
            expected_type = schema["type"]
            if expected_type == "bool":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                elif isinstance(value, int):
                    value = bool(value)
                if not isinstance(value, bool):
                    warnings.append(f"'{slug}': expected bool, got {type(value).__name__}")
                    continue
            elif expected_type == "int":
                try:
                    value = int(value)
                    if "min" in schema:
                        value = max(schema["min"], value)
                    if "max" in schema:
                        value = min(schema["max"], value)
                except (ValueError, TypeError):
                    warnings.append(f"'{slug}': expected int, got '{value}'")
                    continue
            elif expected_type == "float":
                try:
                    value = float(value)
                    if "min" in schema:
                        value = max(schema["min"], value)
                    if "max" in schema:
                        value = min(schema["max"], value)
                except (ValueError, TypeError):
                    warnings.append(f"'{slug}': expected float, got '{value}'")
                    continue
            elif expected_type == "enum":
                if value not in schema["values"]:
                    warnings.append(f"'{slug}': '{value}' not in {schema['values']}")
                    continue
            elif expected_type == "color":
                if not isinstance(value, str) and value is not None:
                    warnings.append(f"'{slug}': expected color string, got {type(value).__name__}")
                    continue
            elif expected_type == "str":
                value = str(value) if value is not None else None
            cleaned[slug] = value
            continue

        schema = SLUG_SCHEMA.get(slug)

        if not schema:
            suggestion = suggest_slug(slug)
            msg = f"Unknown slug '{slug}', ignored"
            if suggestion:
                msg += f". Did you mean '{suggestion}'?"
            warnings.append(msg)
            continue

        # Check applies_to
        if schema.get("deprecated"):
            # deprecated-слаг диспетчер apply пропускает (мёртвый фронт-ключ).
            # Дропаем здесь — консистентно с apply.
            warnings.append(
                f"Slug '{slug}' is DEPRECATED and skipped: {schema['deprecated']}"
            )
            continue
        # Render-dead: предупреждаем, но значение НЕ пропускаем (пишется).
        _dead_ct = _RENDER_DEAD.get(slug)
        if _dead_ct and (_dead_ct == "*" or _dead_ct == chart_type):
            warnings.append(
                f"Slug '{slug}' помечен RENDER-DEAD на {component_type or _dead_ct}: "
                f"запишется в config, но фронт-рендер его НЕ отображает. "
                f"Применяется без визуального эффекта."
            )
        applies_to = schema.get("applies_to")
        if applies_to and chart_type not in applies_to:
            warnings.append(
                f"Slug '{slug}' not applicable to {chart_type}, "
                f"ignored (applies to: {applies_to})"
            )
            continue

        # Type validation
        expected_type = schema["type"]

        if expected_type == "bool":
            if isinstance(value, str):
                value = value.lower() in ("true", "1", "yes")
            if not isinstance(value, bool):
                warnings.append(f"'{slug}': expected bool, got {type(value).__name__}")
                continue
            cleaned[slug] = value

        elif expected_type == "int":
            try:
                v = int(value)
                if "min" in schema:
                    v = max(schema["min"], v)
                if "max" in schema:
                    v = min(schema["max"], v)
                cleaned[slug] = v
            except (ValueError, TypeError):
                warnings.append(f"'{slug}': expected int, got '{value}'")

        elif expected_type == "int_or_null":
            if value is None or (isinstance(value, str) and value.lower() in ("null", "none", "")):
                cleaned[slug] = None
            else:
                try:
                    v = int(value)
                    if "min" in schema:
                        v = max(schema["min"], v)
                    if "max" in schema:
                        v = min(schema["max"], v)
                    cleaned[slug] = v
                except (ValueError, TypeError):
                    warnings.append(f"'{slug}': expected int or null, got '{value}'")

        elif expected_type == "float":
            try:
                v = float(value)
                if "min" in schema:
                    v = max(schema["min"], v)
                if "max" in schema:
                    v = min(schema["max"], v)
                cleaned[slug] = v
            except (ValueError, TypeError):
                warnings.append(f"'{slug}': expected float, got '{value}'")

        elif expected_type == "enum":
            allowed = schema["values"]
            if value not in allowed:
                warnings.append(f"'{slug}': '{value}' not in {allowed}")
                continue
            cleaned[slug] = value

        elif expected_type == "color":
            if isinstance(value, str):
                cleaned[slug] = value
            elif value is None:
                cleaned[slug] = None
            else:
                warnings.append(f"'{slug}': expected color string, got {type(value).__name__}")

        elif expected_type == "str":
            cleaned[slug] = str(value) if value is not None else None

        elif expected_type == "any":
            cleaned[slug] = value

    return cleaned, warnings


def apply_slug_overrides(
    config: dict[str, Any],
    overrides: dict[str, Any],
    component_type: str = "",
) -> dict[str, Any]:
    """
    Apply flat slug overrides to nested JSON component config.

    Uses explicit dispatch per section — NOT naive dot-split.
    Handles axes[categories] vs axes[values], regimes→settings mapping,
    data→top-level mapping, visuals array, etc.
    """
    cfg = copy.deepcopy(config)

    # Подстраховка для прямых вызовов apply без validate: те же алиасы.
    if any(k in overrides for k in _SLUG_ALIASES):
        overrides = {_SLUG_ALIASES.get(k, k): v for k, v in overrides.items()}

    def _find_axis(axes_list: list[dict], axis_type: str) -> dict | None:
        """Find axis by type in axes array."""
        for axis in axes_list:
            if axis.get("type") == axis_type:
                return axis
        return None

    for slug, value in overrides.items():
        # --- Явный путь схемы (path_write=True). json_path — точечный/axes-путь;
        # invert=True — фронт хранит инвертированный смысл. ---
        _entry = SLUG_SCHEMA.get(slug)
        # deprecated не пишем (warning уже в validate)
        if _entry and _entry.get("deprecated"):
            continue
        if _entry and _entry.get("path_write"):
            _val = (not value) if _entry.get("invert") else value
            # value_map: алиас → каноническое значение
            _vm = _entry.get("value_map")
            if _vm and _val in _vm:
                _val = _vm[_val]
            # scale: пользовательская единица → фронтовая (напр. columnWidth % → доля 0..1)
            _scale = _entry.get("scale")
            if _scale is not None and isinstance(_val, (int, float)) and not isinstance(_val, bool):
                _val = round(_val * _scale, 4)
            _write_config_path(cfg, _entry["json_path"], _val)
            continue

        # --- Per-column: columns.{fieldId}.{prop} → config.columns[fieldId][prop] ---
        if slug.startswith("columns."):
            col_parts = slug.split(".", 2)
            if len(col_parts) == 3:
                _, field_id, prop = col_parts
                cfg.setdefault("columns", {})
                cfg["columns"].setdefault(field_id, {})
                cfg["columns"][field_id][prop] = value
            continue

        # --- Per-rule: rules.{index}.{prop} → conditional formatting (table/pivot) ---
        if slug.startswith("rules."):
            from app.tools.builders import generate_uid  # lazy import (avoids circular, cached by Python)
            parts = slug[len("rules."):].split(".", 1)
            if len(parts) < 2:
                continue
            idx = int(parts[0])
            prop_path = parts[1]
            # Ensure rules array exists and has enough entries
            if "rules" not in cfg:
                cfg["rules"] = []
            while len(cfg["rules"]) <= idx:
                cfg["rules"].append({
                    "id": generate_uid(),
                    "name": "",
                    "fieldId": None,
                    "fieldById": None,
                    "wholeRow": False,
                    "minimum": None,
                    "maximum": None,
                    "cons": {"0": {"operator": None, "value": None}, "1": {}},
                    "logicOr": False,
                    "color": None,
                    "background": None,
                    "sparklineColor": None,
                    "indicatorType": None,
                    "indicatorColor": None,
                    "isTextBold": False,
                    "isTextItalic": False,
                    "isTextUnderline": False,
                    "hideTypeValue": False,
                    "hideTypeTotals": False,
                    "isTypeHeader": False,
                })
            rule = cfg["rules"][idx]
            # Handle nested cons.operator / cons.value → indexed format {"0": {op,val}, "1": {op,val}}
            if prop_path in ("cons.operator", "cons.value"):
                con_prop = prop_path.split(".")[1]
                cons = rule.setdefault("cons", {"0": {"operator": None, "value": None}, "1": {}})
                cons.setdefault("0", {"operator": None, "value": None})[con_prop] = value
            else:
                rule[prop_path] = value
            continue

        parts = slug.split(".")

        # ============================================
        # TOP-LEVEL (1 part): bgColor, orientation, etc.
        # ============================================
        if len(parts) == 1:
            # UI «Стекинг» фронт хранит как groupMode. Старый ключ stacking
            # оставляем для совместимости со старыми конфигами.
            _per_type_key = _TOP_LEVEL_PER_TYPE.get(
                (CHART_TYPE_MAP.get(component_type, component_type), parts[0]))
            if _per_type_key:
                cfg[_per_type_key] = value
            elif parts[0] == "stacking":
                cfg["stacking"] = value
                _group_mode = {"normal": "stack", "percent": "100%", "none": ""}
                if value in _group_mode:
                    cfg["groupMode"] = _group_mode[value]
            else:
                cfg[parts[0]] = value

        elif len(parts) == 2:
            section, prop = parts

            # --- margin -> config.margin.{prop} ---
            if section == "margin":
                cfg.setdefault("margin", {})
                cfg["margin"][prop] = value

            # --- outline -> config.outline.{prop} ---
            elif section == "outline":
                cfg.setdefault("outline", {})
                cfg["outline"][prop] = value

            # --- legend -> config.legend.{prop} ---
            elif section == "legend":
                cfg.setdefault("legend", {})
                # render-ключи в lowercase
                _LEGEND_LC = {"bgColor": "bgcolor", "borderColor": "bordercolor", "borderWidth": "borderwidth"}
                if prop == "reverse":
                    cfg["legend"]["order"] = "reversed" if value else "normal"
                elif prop == "order" and value == "reverse":
                    cfg["legend"]["order"] = "reversed"
                elif prop in _LEGEND_LC:
                    cfg["legend"][_LEGEND_LC[prop]] = value
                else:
                    cfg["legend"][prop] = value

            # --- labels -> config.labels.{prop} ---
            elif section == "labels":
                cfg.setdefault("labels", {})
                cfg["labels"][prop] = value

            # --- balloon -> config.balloon.{prop} ---
            elif section == "balloon":
                cfg.setdefault("balloon", {})
                # фронт хранит lowercase-ключ fontsize; остальные balloon-ключи совпадают.
                _balloon_prop_map = {"fontSize": "fontsize"}
                cfg["balloon"][_balloon_prop_map.get(prop, prop)] = value

            # --- axes -> SPECIFIC axis, NOT all axes! ---
            elif section == "axes":
                axes = cfg.get("axes", [])

                if prop.startswith("category"):
                    axis = _find_axis(axes, "categories")
                    if axis:
                        prop_name = prop.replace("category", "").lower()
                        axis_prop_map = {
                            "grid": "showgrid",
                            "labels": "showlabels",
                            "scale": "showscale",
                            "title": "showtitle",
                            "labelangle": "labelsAngle",
                            "scrollbar": "fixedZoom",
                            "mingridwidth": "minGridWidth",
                            "maxlabelwidth": "maxLabelWidth",
                        }
                        mapped = axis_prop_map.get(prop_name, prop_name)
                        axis[mapped] = value

                elif prop.startswith("value"):
                    axis = _find_axis(axes, "values")
                    if axis:
                        prop_name = prop.replace("value", "").lower()
                        axis_prop_map = {
                            "grid": "showgrid",
                            "labels": "showlabels",
                            "scale": "showscale",
                            "title": "showtitle",
                        }
                        mapped = axis_prop_map.get(prop_name, prop_name)
                        axis[mapped] = value

                else:
                    # Generic axis props: scaleType, labelsAccuracy, autoZoom
                    axis = _find_axis(axes, "values")
                    if axis:
                        axis[prop] = value

            # --- data -> config.{json_path|prop} (TOP-LEVEL or nested) ---
            elif section == "data":
                # handler читает json_path схемы (вложенный путь через точку).
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                if "." in mapped:
                    _write_config_path(cfg, mapped, value)
                else:
                    cfg[mapped] = value

            # --- style -> config.styleCommons.{prop} (lineChart/areaChart) ---
            elif section == "style":
                cfg.setdefault("styleCommons", {})[prop] = value

            # --- pivot -> config.{json_path|prop} (pivotChart) ---
            elif section == "pivot":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                # фронт хранит nullVisible как enum visible/hidden
                if slug == "pivot.nullVisible" and isinstance(value, bool):
                    value = "visible" if value else "hidden"
                cfg[mapped] = value

            # --- visuals -> config.visuals[0].{prop} or create ---
            elif section == "visuals":
                visuals = cfg.get("visuals")
                if isinstance(visuals, list) and len(visuals) > 0:
                    visuals[0][prop] = value
                elif isinstance(visuals, list) and len(visuals) == 0:
                    cfg["visuals"] = [{prop: value}]
                elif isinstance(visuals, dict):
                    visuals[prop] = value
                else:
                    cfg[prop] = value

            # --- regimes -> config.settings.{MappedName} ---
            elif section == "regimes":
                cfg.setdefault("settings", {})
                regime_map = {
                    "autoWidth": "AllowAutoWidth",
                    "columnDrag": "AllowColumnDnD",
                    "multilineHeader": "AllowMultilineHeader",
                    "subtotals": "AllowSubtotals",
                    "totals": "AllowTotals",
                    "fixedColumns": "AllowFixedColumns",
                    "cellHeight": "CellHeight",
                    "headerHeight": "HeaderHeight",
                    "resizable": "AllowResizable",
                }
                mapped = regime_map.get(prop, prop)
                cfg["settings"][mapped] = value

            # --- delta -> visuals[anchor='trend'] (totalsPanelV2) ---
            elif section == "delta":
                # Фронт читает тренд-настройки KPI из anchored-элемента
                # visuals[anchor='trend'], а не из top-level delta/deltaPercent
                # (те остаются undefined после любого клика в UI).
                trend = _anchored_visual(cfg, "trend")
                if prop == "percent":
                    # Полярность по фронт-бандлу:
                    # hasTarget ? (absolute ? M : (D-M)/M*100) : M
                    # т.е. процентный режим = absolute:false → ИНВЕРСИЯ.
                    trend["absolute"] = not value
                elif prop == "delta":
                    trend["hasTarget"] = value
                else:
                    trend[prop] = value

            # --- grid -> config.grid.{prop} (speedometer/radar) ---
            elif section == "grid":
                cfg.setdefault("grid", {})
                cfg["grid"][prop] = value

            # --- viewType -> config.{prop} (FilterControlPanel) ---
            elif section == "viewType":
                cfg[prop] = value

            # --- hierFilter -> config.{prop} (hierarchicalFilterPanel) ---
            elif section == "hierFilter":
                cfg[prop] = value

            # --- switch -> config.{prop} (SwitchControlPanel) ---
            elif section == "switch":
                cfg[prop] = value

            # --- sort -> config.{prop} ---
            elif section == "sort":
                cfg[prop] = value

            # --- totals -> config.{mapped_prop} (pivotChart) ---
            elif section == "totals":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                cfg[mapped] = value

            # --- map -> config.{mapped_prop} (mapLeaflet) ---
            elif section == "map":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                cfg[mapped] = value

            # --- tilemap -> nested dispatch (tilemapChart) ---
            elif section == "tilemap":
                # фронт читает градиент из legend.color[] ([start, end])
                if prop in ("startColor", "endColor"):
                    colors = cfg.setdefault("legend", {}).setdefault("color", [None, None])
                    if not isinstance(colors, list) or len(colors) < 2:
                        colors = [None, None]
                        cfg["legend"]["color"] = colors
                    colors[0 if prop == "startColor" else 1] = value
                elif prop in _TILEMAP_MAP:
                    parent, key = _TILEMAP_MAP[prop]
                    cfg.setdefault(parent, {})[key] = value
                else:
                    # top-level: popup, autoZoom, tileSize, filterMode, scale
                    schema = SLUG_SCHEMA.get(slug, {})
                    mapped = schema.get("json_path", prop)
                    cfg[mapped] = value

            # --- sunburst -> config.{prop} (sunburstChart) ---
            elif section == "sunburst":
                if prop in ("fontSize", "fontFamily"):
                    field = "size" if prop == "fontSize" else "family"
                    cfg.setdefault("font", {})[field] = value
                else:
                    mapped = _SUNBURST_MAP.get(prop, prop)
                    cfg[mapped] = value

            # --- treemap -> config.{mapped_prop} (treeMap) ---
            elif section == "treemap":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                cfg[mapped] = value

            # --- stock -> config.{mapped_prop} (stockChart) ---
            # Nested json_path: scrollbar.disabled, altAxis.enabled, dateAxis.*
            elif section == "stock":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                if "." in mapped:
                    parent, child = mapped.split(".", 1)
                    cfg.setdefault(parent, {})[child] = value
                else:
                    cfg[mapped] = value

            # --- tabs -> config.{prop} (tabsPanel) ---
            elif section == "tabs":
                cfg[prop] = value

            # --- audio -> config.{prop} (audioplayer) ---
            elif section == "audio":
                cfg[prop] = value

            # --- comparison -> config.{prop} (comparisonChart) ---
            elif section == "comparison":
                cfg[prop] = value
                # фронт сравнивает объекты через config.filters[objField]
                # = {type:"by compare", selected:[obj1,obj2]} — top-level
                # object1/object2 сами по себе сравнение не включают.
                if prop in ("object1", "object2"):
                    obj1 = cfg.get("object1")
                    obj2 = cfg.get("object2")
                    if obj1 and obj2:
                        # Бандл: ключ filters — это ALIAS/заголовок поля
                        # ("Округ": {type:"by compare",...}), не тех. имя
                        obj_field = None
                        for axis in cfg.get("axes", []):
                            if axis.get("type") in ("categories", "objects"):
                                fields = axis.get("fields", [])
                                if fields:
                                    obj_field = (fields[0].get("alias")
                                                 or fields[0].get("name"))
                                break
                        if obj_field:
                            selected = [obj1, obj2]
                            cfg.setdefault("filters", {})[obj_field] = {
                                "type": "by compare", "selected": selected,
                            }
                            cfg.setdefault("filtersDefault", {})[obj_field] = {
                                "type": "by compare", "selected": list(selected),
                            }

            # --- graph -> config.{prop} (treeGraph) ---
            elif section == "graph":
                cfg[prop] = value

            # --- text -> config.{prop} (textBlock) ---
            elif section == "text":
                cfg[prop] = value

            # --- image -> config.{prop} or nested link.* (imagePanel) ---
            elif section == "image":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                if slug == "image.src":
                    # config.image — объект {path, ID}; пустое → None
                    cfg["image"] = None if value in (None, "", False) else {"path": value, "ID": value}
                elif "." in mapped:
                    parent, child = mapped.split(".", 1)
                    node = cfg.get(parent)
                    if not isinstance(node, dict):
                        node = cfg[parent] = {}
                    node[child] = value
                else:
                    cfg[mapped] = value

            # --- iframe -> config.{prop} or nested link.* (HsIframe) ---
            # Frontend reads config.frameUrl for src (NOT link.name);
            # both are set for API compatibility.
            elif section == "iframe":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                if "." in mapped:
                    parent, child = mapped.split(".", 1)
                    cfg.setdefault(parent, {})[child] = value
                    # Sync top-level: link.name -> frameUrl, link.target -> frameName
                    if mapped == "link.name":
                        cfg["frameUrl"] = value
                    elif mapped == "link.target":
                        cfg["frameName"] = value
                else:
                    cfg[prop] = value

            # --- tabs -> config.{json_path} (HsTabsPanel) ---
            elif section == "tabs":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                cfg[mapped] = value

            # --- table -> config.{json_path} (HsTableReactabularChart) ---
            elif section == "table":
                schema = SLUG_SCHEMA.get(slug, {})
                mapped = schema.get("json_path", prop)
                cfg[mapped] = value

            # --- generic: прочие валидные 2-part секции (link.operation) ---
            else:
                cfg.setdefault(section, {})[prop] = value

        # ============================================
        # 3-LEVEL: labels.outer.fontsize, labels.inner.color,
        # map.legend.visible, map.markers.showLabels
        # ============================================
        elif len(parts) == 3:
            section, subsection, prop = parts

            # Special case: map.{subsection}.{prop} -> cfg[subsection][prop]
            # The "map." prefix is just slug namespace; config path is
            # {subsection}.{prop} (e.g. legend.visible, markers.clustering)
            if section == "map":
                cfg.setdefault(subsection, {})[prop] = value
            # anchored visuals — visuals.{anchor}.{prop} пишет в элемент
            # visuals[] с anchor=={anchor} (создаёт при отсутствии). Фронт
            # матчит per-series/per-element override ТОЛЬКО по anchor
            # (серия у line/area, value/caption/subcaption/trend у KPI).
            elif section == "visuals":
                element = _anchored_visual(cfg, subsection)
                element[prop] = value
            else:
                cfg.setdefault(section, {})
                cfg[section].setdefault(subsection, {})
                cfg[section][subsection][prop] = value

        # ============================================
        # 4-LEVEL: anchored KPI typography —
        # visuals.{anchor}.font.{size|weight|family|style} -> visuals[anchor].font.{sub}
        # ============================================
        elif len(parts) == 4 and parts[0] == "visuals" and parts[2] == "font":
            _, anchor, _, fprop = parts
            element = _anchored_visual(cfg, anchor)
            element.setdefault("font", {})[fprop] = value

    return cfg


def apply_title(cfg: dict[str, Any], component_type: str, title: str) -> None:
    """
    Set title correctly per component type.

    - Table: title = {"text": "..."}, caption + caption__ru
    - TotalsPanel: title = string, caption + caption__ru
    - Charts: title + caption + caption__ru (all string/object)

    caption__ru is ALWAYS object {"text":"...", "textBefore":"", "textAfter":""}
    """
    caption_ru_obj = {"text": title, "textBefore": "", "textAfter": ""}

    if component_type == "HsTableReactabularChart":
        cfg["title"] = {"text": title}
        cfg["caption__ru"] = caption_ru_obj
        cfg["caption"] = title
    elif component_type == "HsTotalsPanelV2":
        cfg["title"] = title
        cfg["caption__ru"] = caption_ru_obj
        cfg["caption"] = title
    else:
        cfg["title"] = title
        cfg["caption"] = title
        cfg["caption__ru"] = caption_ru_obj


def apply_bg_color(cfg: dict[str, Any], component_type: str, color: str) -> None:
    """
    Set background color per component type.

    TotalsPanelV2 and ImagePanel use 'backgroundColor', all others use 'bgColor'.
    """
    if component_type in ("HsTotalsPanelV2", "HsImagePanel"):
        cfg["backgroundColor"] = color
    else:
        cfg["bgColor"] = color
