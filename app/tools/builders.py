"""
Component config builders for MCP Server.

Used to generate configurations for different component types.
"""

import uuid
from typing import Any
COMPONENT_TYPE_MAP = {
    "HsBarAMchartsChart": ("barChart", "column"),
    "HsLineAMchartsChart": ("lineChart", "line"),
    "HsAreaAMchartsChart": ("areaChart", "area"),
    "HsPieAMchartsChart": ("pieChart", "pie"),
    "HsRadarAMchartsChart": ("radarChart", "radar"),
    "HsStockAMchartsChart": ("stock", "stock"),
    "HsSpeedometerV2AMcharts": ("speedometer_v2", "gauge"),
    # фронт ждёт chartType="bubble" (c "bubbleChart" UI-панель
    # настроек компонента открывается пустой)
    "HsBubbleAMchartsChart": ("bubble", "bubble"),
    "HsSunburstChart": ("sunburstChart", "sunburst"),
    "HsTreeMap": ("treeMap", "treemap"),
    "HsParallelCoordsChart": ("parallelCoordsChart", "parallel"),
    "HsPivotChart": ("pivotChart", "pivot"),
    "HsComparisonChart": ("comparisonChart", "comparison"),
    "HsTreeGraph": ("treeGraph", "tree"),
    "HsMapLeafletChart": ("mapLeaflet", "map"),
    "HsTilemapChart": ("tilemapChart", "tilemap"),
    "HsFilterControlPanel": ("FilterControlPanel", None),
    "HsHierarchicalFilterPanel": ("hierarchicalFilter", None),
    "HsSubheaderComponent": ("subheader", None),
    "HsIframe": ("iframe", None),
    "HsImagePanel": ("imagePanel", None),
    "HsPageContainer": ("pageContainer", None),
    "HsTotalsPanelV2": ("totalsPanelV2", None),
    "HsTableReactabularChart": ("table", "table"),
    "HsTextBlock": ("textBlock", None),
    "HsTabsPanel": ("tabsPanel", None),
    # Remaining types (not API-creatable)
    "HsSwitchControlPanel": ("SwitchControlPanel", None),
    "HsAudioplayer": ("audioplayer", "area"),
}




# component_types которые принимают column_fields в свой config.
# Остальные типы получают silent-ignore для column_fields — теперь возвращаем
# warning в response чтобы LLM-агент видел что параметр не применился.
# Типы без датасета: создаются без value_field/dataset_id (utility/контент).
# ЕДИНЫЙ источник для component_crud/component_operations/batch_operations.
NO_DATASET_TYPES = frozenset({
    "HsImagePanel", "HsIframe", "HsTabsPanel",
    "HsPageContainer", "HsSubheaderComponent",
    "HsTextBlock", "HsAudioplayer",
})

COLUMN_FIELDS_SUPPORTED_TYPES = frozenset({
    "HsPivotChart",        # column_fields → columns axis
    "HsComparisonChart",   # column_fields → indicators axis (UNPIVOT pattern)
})

# component_types где series_field применяется в axes.series.
# axes.series существует на bar/line/stock/bubble/radar/pie. Area наследует
# структуру line (тот же _build_chart_config).
SERIES_FIELD_SUPPORTED_TYPES = frozenset({
    "HsBarAMchartsChart",
    "HsLineAMchartsChart",
    "HsAreaAMchartsChart",
    "HsStockAMchartsChart",
})


def check_unsupported_params(
    component_type: str,
    column_fields: str | None = None,
    series_field: str | None = None,
    category_field: str | None = None,
    value_field: str | None = None,
) -> list[str]:
    """Возвращает warning'и для параметров, которые тип не поддерживает.

    column_fields/series_field на не-supported типах не применяются —
    возвращаем warnings, чтобы LLM понимал, почему multi-series не работает.
    """
    warnings = []
    if column_fields and component_type not in COLUMN_FIELDS_SUPPORTED_TYPES:
        warnings.append(
            f"column_fields={column_fields!r} ignored on {component_type} — "
            f"supported only on {sorted(COLUMN_FIELDS_SUPPORTED_TYPES)}. "
            f"For multi-series on bar/line: use series_field "
            f"or component_crud(action='copy') from a template chart."
        )
    if series_field and component_type not in SERIES_FIELD_SUPPORTED_TYPES:
        warnings.append(
            f"series_field={series_field!r} ignored on {component_type} — "
            f"supported only on {sorted(SERIES_FIELD_SUPPORTED_TYPES)}. "
            f"For non-chart types use other grouping mechanisms (pivot's "
            f"column_fields, comparison's indicators)."
        )
    # series == category даёт вырожденную серию (одна серия на категорию,
    # дублирующая ось) — почти всегда ошибка выбора поля.
    if (series_field and category_field
            and series_field.strip() == category_field.strip()):
        warnings.append(
            f"series_field == category_field ({series_field!r}): series must "
            f"be a DIFFERENT dimension than the category axis (e.g. "
            f"category_field='year', series_field='product')."
        )
    # Bubble без X-поля рендерит пустой график (NaN-оси) — value_fields[0]→Y,
    # [1]→X обязательны.
    if component_type == "HsBubbleAMchartsChart" and value_field:
        if len([f for f in value_field.split(",") if f.strip()]) < 2:
            warnings.append(
                "HsBubbleAMchartsChart requires 2 value fields "
                "(value_field='y_field,x_field'): with one field the xvalues "
                "axis stays empty and the chart renders no bubbles."
            )
    return warnings


def generate_uid() -> str:
    """Generate unique ID for component."""
    return str(uuid.uuid4())[:21].replace("-", "_")


def _parse_extra_fields(
    fields_str: str | None,
    dataset_id: int,
    field_titles: dict[str, str] | None = None,
    field_alias_map: dict[str, str] | None = None,
) -> list[dict]:
    """Parse comma-separated field names into field config dicts for axes.

    Used by pivot (row_fields, column_fields) and bubble (size_field).

    Args:
        fields_str: Comma-separated field names, e.g. "Region,District"
        dataset_id: Dataset ID to embed into each field config
        field_titles: Optional {name: display_title} mapping
        field_alias_map: {name: alias} из dataset, fallback на name.

    Returns:
        List of field config dicts, each with keys:
        datasetId, agg, units, type, name, alias, title, id
    """
    if not fields_str:
        return []
    if field_titles is None:
        field_titles = {}
    if field_alias_map is None:
        field_alias_map = {}
    result = []
    for name in (f.strip() for f in fields_str.split(",") if f.strip()):
        result.append({
            "datasetId": dataset_id,
            "agg": None,
            "units": None,
            "type": "string",
            "name": name,
            "alias": field_alias_map.get(name) or name,
            "title": field_titles.get(name, ""),
            "id": generate_uid()
        })
    return result


def build_component_config(
    component_type: str,
    title: str,
    dataset_id: int,
    category_field: str,
    value_fields: list[str],
    value_fields_type: str,
    aggregation: str | None,
    field_titles: dict[str, str] | None = None,
    where_filter: list[dict] | None = None,
    text_content: str | None = None,
    row_fields: str | None = None,
    column_fields: str | None = None,
    size_field: str | None = None,
    field_alias_map: dict[str, str] | None = None,
    series_field: str | None = None,
    subheader_field: str | None = None,
    info_fields: str | None = None,
) -> dict[str, Any]:
    """
    Build component configuration based on type.

    Args:
        component_type: Type of component (e.g., HsTableReactabularChart)
        title: Component title
        dataset_id: Dataset ID
        category_field: Category field name
        value_fields: List of value field names
        value_fields_type: Type for value fields
        aggregation: Aggregation function
        field_titles: Dict mapping field names to human-readable titles
                      e.g., {"region": "Регион", "product": "Товар"}
        where_filter: Filter conditions for the component
                      e.g., [{"field": "region", "operator": "=", "value": "North"}]
        field_alias_map: {name: alias} из dataset.
            Если передан — используется для alias всех field configs (category,
            value, where_filter). Иначе alias=name (legacy). Fetch на caller'е
            (async — например component_crud._add_component вызывает
            _fetch_dataset_alias_map перед build_component_config).
    """
    if field_titles is None:
        field_titles = {}
    if where_filter is None:
        where_filter = []
    if field_alias_map is None:
        field_alias_map = {}

    def _alias_for(name: str) -> str:
        """Resolve alias: from dataset map, fallback to name."""
        if not name:
            return name
        return field_alias_map.get(name) or name

    # Generate UIDs for fields
    category_uid = generate_uid() if category_field else None
    value_uids = [generate_uid() for _ in value_fields]

    # Category field config(s). Sunburst/TreeMap поддерживают ИЕРАРХИЮ:
    # category_field="level1,level2,..." → несколько полей в categories-оси.
    # Прочие типы используют только первое поле (старое поведение).
    category_field_configs: list[dict] = []
    if category_field:
        for i, cat_name in enumerate(
                f.strip() for f in category_field.split(",") if f.strip()):
            category_field_configs.append({
                "datasetId": dataset_id,
                "agg": None,  # Category fields don't need aggregation - ModusBI uses "agg" not "aggr"
                "units": None,
                "type": "string",
                "name": cat_name,
                "alias": _alias_for(cat_name),
                "title": field_titles.get(cat_name, ""),
                "id": category_uid if i == 0 else generate_uid(),
            })
    category_field_config = category_field_configs[0] if category_field_configs else None

    # Value fields configs
    # IMPORTANT: When category_field is set (GROUP BY), value fields MUST have aggregation!
    # Frontend forms recordset request with group:[category] and select:[values]
    # If agg is null/empty, SQL fails: "column must appear in GROUP BY clause"
    # For pre-aggregated datasets, use "max" - returns single value per category unchanged

    # EXCEPTION: TreeGraph — ALL fields must have agg=null (identity/linkage/values).
    # TreeGraph expects flat parent-child recordset, no GROUP BY at all.
    effective_agg = aggregation
    agg_was_implicit = False
    if component_type in ("HsTreeGraph", "HsParallelCoordsChart"):
        # TreeGraph + ParallelCoords: force null aggregation on ALL fields.
        # TreeGraph expects flat parent-child recordset, no GROUP BY.
        # ParallelCoords expects raw rows (each row = one line across axes).
        effective_agg = None
        agg_was_implicit = False
    elif category_field and not aggregation and "Table" not in component_type:
        # Category exists = GROUP BY will be used, need aggregation for values.
        # Tables are excluded: they don't aggregate, frontend would emit
        # "SELECT MAX(...) ... no GROUP BY" and Postgres would fail.
        effective_agg = "max"  # Safe default for pre-aggregated data
        agg_was_implicit = True

    value_field_configs = [
        {
            "datasetId": dataset_id,
            "agg": effective_agg,  # ModusBI API uses "agg" (NOT "aggr"!) - verified from real API response
            "units": None,
            "type": value_fields_type,
            "name": vf,
            "alias": _alias_for(vf),
            "title": field_titles.get(vf, ""),
            "id": value_uids[i]
        }
        for i, vf in enumerate(value_fields)
    ]

    # series_field → axes.series.fields для multi-series chart.
    # Frontend строит N серий через distinct values поля series.
    # Поддерживается только chart-типами (bar/line/area/stock/bubble/radar/pie).
    # Pivot/Comparison используют column_fields (другой механизм).
    series_field_configs = []
    if series_field and series_field.strip():
        series_field_configs.append({
            "datasetId": dataset_id,
            "agg": None,  # series — это группировка, не aggregation
            "units": None,
            "type": "string",
            "name": series_field.strip(),
            "alias": _alias_for(series_field.strip()),
            "title": field_titles.get(series_field.strip(), ""),
            "id": generate_uid(),
        })

    # Component type → (config_json_type, visual_type) for building output JSON.
    # NOTE: These values go into the component config that the frontend reads.
    # They may differ from config_schema.py CHART_TYPE_MAP which is used only
    # for slug validation (applies_to matching). Both maps are intentionally
    # separate: this one = frontend contract, that one = slug namespace.
    chart_type_map = COMPONENT_TYPE_MAP
    if component_type not in chart_type_map:
        # Reject unknown types instead of silently falling back to barChart.
        # Frontend would render an empty bar without warning, hiding the typo.
        return {
            "error": f"Unknown component_type {component_type!r}",
            "available_types": sorted(chart_type_map.keys()),
            "hint": "Common mistakes: 'HsKpiPanel'→use 'HsTotalsPanelV2'; "
                    "'HsTable'→use 'HsTableReactabularChart'.",
        }
    chart_type, visual_type = chart_type_map[component_type]

    # === HsTextBlock (Text Block) ===
    if component_type == "HsTextBlock":
        return _build_text_block_config(
            title, chart_type, text_content or ""
        )

    # === HsTableReactabularChart (Table) ===
    if component_type == "HsTableReactabularChart":
        return _build_table_config(
            title, chart_type, visual_type,
            category_field_config, value_field_configs,
            where_filter, field_alias_map=field_alias_map,
        )

    # === HsTotalsPanelV2 (Totals Panel) ===
    if component_type == "HsTotalsPanelV2":
        # extra value-fields с valueType=subheader/info для
        # многострочных KPI. valueType='subheader' = подзаголовок-строка,
        # 'info' = произвольная информационная строка (с опц. title).
        extra_kpi_fields: list[dict] = []
        if subheader_field and subheader_field.strip():
            extra_kpi_fields.append({
                "datasetId": dataset_id,
                "agg": effective_agg or "max",
                "units": None,
                "type": value_fields_type,
                "name": subheader_field.strip(),
                "alias": _alias_for(subheader_field.strip()),
                "title": field_titles.get(subheader_field.strip(), ""),
                "id": generate_uid(),
                "valueType": "subheader",  # frontend KPI render mode
            })
        if info_fields and info_fields.strip():
            for nm in (f.strip() for f in info_fields.split(",") if f.strip()):
                extra_kpi_fields.append({
                    "datasetId": dataset_id,
                    "agg": effective_agg or "max",
                    "units": None,
                    "type": value_fields_type,
                    "name": nm,
                    "alias": _alias_for(nm),
                    "title": field_titles.get(nm, ""),
                    "id": generate_uid(),
                    "valueType": "info",
                    "showTitle": True,  # info-строка с title (опц.)
                })
        return _build_totals_panel_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs,
            extra_value_fields=extra_kpi_fields,
        )

    # === HsPieAMchartsChart (Pie Chart) ===
    if component_type == "HsPieAMchartsChart":
        return _build_pie_config(
            component_type, title, chart_type, visual_type,
            category_field_config, value_field_configs
        )

    # === HsRadarAMchartsChart (Radar Chart) ===
    if component_type == "HsRadarAMchartsChart":
        return _build_radar_config(
            component_type, title, chart_type, visual_type,
            category_field_config, value_field_configs
        )

    # === HsStockAMchartsChart (Stock / Time Series) ===
    if component_type == "HsStockAMchartsChart":
        return _build_stock_config(
            component_type, title, chart_type, visual_type,
            category_field_config, value_field_configs,
            series_field_configs=series_field_configs,
        )

    # === HsSpeedometerV2AMcharts (Gauge) ===
    if component_type == "HsSpeedometerV2AMcharts":
        return _build_speedometer_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs
        )

    # === HsBubbleAMchartsChart (Bubble) ===
    if component_type == "HsBubbleAMchartsChart":
        # size_field может прийти как CSV ("a,b") — разбиваем на отдельные
        # числовые поля (иначе одно поле с именем-CSV → бэкенд «нет данных»).
        size_field_config = [
            {
                "datasetId": dataset_id,
                "agg": aggregation,
                "units": None,
                "type": "number",
                "name": nm,
                "alias": nm,
                "title": (field_titles or {}).get(nm, ""),
                "id": generate_uid()
            }
            for nm in (f.strip() for f in size_field.split(",")) if nm
        ] if size_field else None
        return _build_bubble_config(
            component_type, title, chart_type, visual_type,
            category_field_config, value_field_configs,
            size_field_config=size_field_config,
        )

    # === HsSunburstChart (Sunburst) ===
    if component_type == "HsSunburstChart":
        return _build_sunburst_config(
            component_type, title, chart_type, visual_type,
            category_field_configs, value_field_configs
        )

    # === HsTreeMap (TreeMap) ===
    if component_type == "HsTreeMap":
        return _build_treemap_config(
            component_type, title, chart_type,
            category_field_configs, value_field_configs
        )

    # === HsParallelCoordsChart (Parallel Coordinates) ===
    if component_type == "HsParallelCoordsChart":
        return _build_parallel_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs
        )

    # === HsPivotChart (Pivot Table) ===
    if component_type == "HsPivotChart":
        # Parse row_fields and column_fields into field configs
        row_field_configs = _parse_extra_fields(row_fields, dataset_id, field_titles, field_alias_map)
        column_field_configs = _parse_extra_fields(column_fields, dataset_id, field_titles, field_alias_map)
        return _build_pivot_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs,
            row_field_configs=row_field_configs,
            column_field_configs=column_field_configs,
        )

    # === HsComparisonChart (Comparison Table) ===
    if component_type == "HsComparisonChart":
        # column_fields → indicators axis (STRING field for metric names in UNPIVOT pattern)
        indicator_field_configs = _parse_extra_fields(column_fields, dataset_id, field_titles, field_alias_map)
        return _build_comparison_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs,
            indicator_field_configs=indicator_field_configs,
        )

    # === HsTreeGraph (Graph / Tree) ===
    if component_type == "HsTreeGraph":
        return _build_tree_graph_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs
        )

    # === HsMapLeafletChart (Geo Map) — pass all value fields (lat, lng, metric)
    if component_type == "HsMapLeafletChart":
        return _build_map_config(
            component_type, title, chart_type, visual_type,
            category_field_config, value_field_configs
        )

    # === HsTilemapChart (Tile Map) ===
    if component_type == "HsTilemapChart":
        return _build_tilemap_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs
        )

    # === HsFilterControlPanel (Filter Panel) ===
    if component_type == "HsFilterControlPanel":
        return _build_filter_panel_config(
            component_type, title, chart_type, value_field_configs
        )

    # === HsTabsPanel (Navigation Tabs) ===
    if component_type == "HsTabsPanel":
        return _build_tabs_panel_config(component_type, title, chart_type)

    # === HsAudioplayer (Speech Analytics Player) ===
    if component_type == "HsAudioplayer":
        return _build_audioplayer_config(
            component_type, title, chart_type, value_field_configs
        )

    # === HsIframe (Embedded Page) ===
    if component_type == "HsIframe":
        return _build_iframe_config(component_type, title, chart_type)

    # === HsImagePanel (Image Panel) ===
    if component_type == "HsImagePanel":
        return _build_image_panel_config(component_type, title, chart_type)

    # === HsHierarchicalFilterPanel (Hierarchical Filter) ===
    if component_type == "HsHierarchicalFilterPanel":
        return _build_hierarchical_filter_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs
        )

    # === HsSwitchControlPanel (Switch / Category Switcher) ===
    if component_type == "HsSwitchControlPanel":
        return _build_switch_panel_config(
            component_type, title, chart_type,
            category_field_config, value_field_configs
        )

    # === Simple utility components ===
    if component_type in (
        "HsSubheaderComponent",
        "HsPageContainer",
    ):
        return _build_simple_config(component_type, title, chart_type)

    # === Bar/Line/Area charts (default) ===
    # HsLineAMchartsChart and HsAreaAMchartsChart intentionally fall through here.
    # They share the same config structure as HsBarAMchartsChart — only chart_type
    # and visual_type differ (set via chart_type_map above).
    return _build_chart_config(
        component_type, title, chart_type, visual_type,
        category_field_config, value_field_configs,
        series_field_configs=series_field_configs,
    )


def _build_table_config(
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    where_filter: list[dict] | None = None,
    field_alias_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build table configuration."""
    if field_alias_map is None:
        field_alias_map = {}
    all_fields = []
    if category_field_config:
        all_fields.append(category_field_config)
    all_fields.extend(value_field_configs)

    # Build filter fields from where_filter
    filter_fields = []
    if where_filter:
        for wf in where_filter:
            # Accept both key conventions: component_crud uses field/operator,
            # the batch WhereClause schema uses name/op. Read both so where_filter
            # is not silently dropped depending on the call path.
            field_name = wf.get("field") or wf.get("name", "")
            filter_fields.append({
                "datasetId": value_field_configs[0].get("datasetId") if value_field_configs else None,
                "name": field_name,
                # B
                "alias": field_alias_map.get(field_name) or field_name,
                "type": "string",
                "id": generate_uid(),
                "values": [wf.get("value", "")],
                "operator": wf.get("operator") or wf.get("op", "=")
            })

    axes = [
        {"name": "filters", "title": "Filters", "type": "filters", "fields": filter_fields},
        {"name": "categories", "title": "Categories", "type": "categories", "fields": []},
        {"name": "series", "title": "Series", "type": "series", "fields": []},
        {
            "name": "y",
            "title": "Values",
            "type": "values",
            "selectedFieldIndex": -2,
            "fields": all_fields,
            "sortable": True
        }
    ]

    columns = {f["id"]: {"valueSeparator": True} for f in all_fields}

    return {
        "type": "HsTableReactabularChart",
        "config": {
            "title": {"text": title},
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "precision": 0,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"t": 0, "l": 0, "b": 0, "r": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "settings": {
                "AllowResizable": True,
                "AllowResponsible": False,
                "AllowSort": True,
                "AllowSearch": False,
                "AllowTree": False,
                "AllowPagination": False,
                "AllowColumnDnD": True,
                "AllowVirtualization": True,
                "AllowFixedWidth": False,
                "AllowExport": False,
                "AllowToggleVisibility": False,
                "AllowAutoWidth": True,
                "AllowMultilineHeader": True
            },
            "massUpdate": {"enabled": False, "keyField": None, "formURL": None, "rowLimit": 0, "limitWarn": False},
            "allowMultivalues": True,
            "allowNoCategories": True,
            "visuals": [],
            "rules": [],
            "dirty": False,
            "columns": columns,
            "axesDefault": axes.copy()
        }
    }


def _build_totals_panel_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    extra_value_fields: list[dict] | None = None,
) -> dict[str, Any]:
    """Build totals panel configuration.

    extra_value_fields кладутся в axes.values после главного
    value-поля. Каждое поле уже имеет valueType (subheader/info), который
    задаётся в caller'е (component_crud builder helpers).
    """
    if extra_value_fields is None:
        extra_value_fields = []

    main_value = [value_field_configs[0]] if value_field_configs else []
    all_values = main_value + extra_value_fields

    axes = [
        {"name": "filters", "title": "Filters", "type": "filters", "fields": []},
        {
            "name": "Categories",
            "title": "Categories",
            "type": "categories",
            "fields": [category_field_config] if category_field_config else []
        },
        {
            "name": "Indicator",
            "title": "Indicator",
            "type": "values",
            "fields": all_values,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "subtitle": "",
            "chartType": chart_type,
            "orientation": "v",
            "showtitle": True,
            "maximizable": False,
            "autoApply": True,
            "noexport": False,
            "nocopy": False,
            "precision": -1,
            "percentPrecision": 1,
            "backgroundColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 10, "r": 10, "t": 10, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "visuals": [
                {"anchor": "value", "label": "Value", "visible": True, "thresholdForPercent": 100, "font": {"size": 2.8, "weight": 600}},
                {"anchor": "caption", "label": "Caption", "visible": True, "font": {"size": 1}},
                {"anchor": "subcaption", "label": "Subcaption", "visible": True, "font": {"size": 0.8}},
                {"anchor": "trend", "label": "Trend", "visible": True, "font": {"size": 1.2}}
            ],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_pie_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
) -> dict[str, Any]:
    """Build pie chart configuration.

    donut mode + center sum + label template доступны через
    config_overrides={"showDonut": True, "summEnabled": True,
    "labelsTemplate": "[[categories]] — [[percents]]%"} — slugs в
    SLUG_SCHEMA.
    """
    axes = [
        {"name": "filters", "title": "Filters", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Categories",
            "type": "categories",
            "scaleType": "category",
            "visible": False,
            "showtitle": False,
            "showscale": False,
            "showgrid": False,
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "series", "title": "Series", "type": "series", "fields": []},
        {
            "name": "values",
            "title": "Values",
            "type": "values",
            "visible": False,
            "showtitle": False,
            "showscale": False,
            "showgrid": False,
            "fields": [value_field_configs[0]] if value_field_configs else [],
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 5, "r": 5, "t": 10, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "orientation": "h", "position": "auto"},
            "labels": {
                "visible": True,
                "position": "auto",
                "hidePercent": 2,
                "groupPercent": 0.5,
                "groupCount": 9,
                "switchControlNumberOfSegments": False,
                "inner": {},
                "outer": {}
            },
            "visuals": [],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_chart_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    series_field_configs: list[dict] | None = None,
) -> dict[str, Any]:
    """Build Bar/Line/Area chart configuration.

    series_field_configs (если не пуст) кладётся в axes.series.
    Frontend строит N серий через distinct values этого поля (multi-series).
    """
    if series_field_configs is None:
        series_field_configs = []
    axes = [
        {"name": "filters", "title": "Filters", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Categories",
            "type": "categories",
            "scaleType": "category",
            "visible": True,
            "showtitle": False,
            "showscale": True,
            "showgrid": False,
            "showlabels": True,
            "fixedZoom": False,
            "fixedZoomValue": 10,
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "series", "title": "Series", "type": "series", "fields": series_field_configs},
        {
            "name": "values",
            "title": "Values",
            "type": "values",
            "visible": True,
            "showtitle": False,
            "showscale": True,
            "showgrid": False,
            "showlabels": True,
            "fields": value_field_configs,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "orientation": "v",
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            # default baseColor чтобы bars не рендерились пустыми
            # (#FFFFFF на белом фоне). Можно переопределить через
            # config_overrides={"data.baseColor": "#XXX"}.
            "baseColor": "#1F77B4",  # matplotlib classic blue, нейтральный
            "colorStep": 0,
            "margin": {"l": 5, "r": 10, "t": 10, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "position": "auto", "order": "normal"},
            "labels": {"visible": False, "position": "auto", "inner": {}, "outer": {}},
            "visuals": [],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_text_block_config(
    title: str,
    chart_type: str,
    text_content: str
) -> dict[str, Any]:
    """Build text block configuration.

    Args:
        title: Component title
        chart_type: Type (should be "textBlock")
        text_content: HTML content for the text block
    """
    return {
        "type": "HsTextBlock",
        "config": {
            "title": title,
            "description": text_content,
            "description__ru": text_content,
            "chartType": chart_type,
            "autoApply": True,
            "dirty": False,
            "filters": {},
            "filtersDefault": {},
            "margin": {"l": 10, "r": 10, "t": 10, "b": 10, "pad": 0},
            "maximizable": True,
            "nocopy": False,
            "noexport": True,
            "outline": {"enabled": False, "width": 4},
            "showtitle": False,
            "visuals": []
        }
    }


# ============================================================
# Radar, Stock, Speedometer
# ============================================================

def _build_radar_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build radar chart configuration."""
    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "scaleType": "category",
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "series", "title": "Серии", "type": "series", "fields": []},
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "visible": True,
            "showtitle": False,
            "showscale": True,
            "showgrid": True,
            "gridType": "circles",
            "showlabels": True,
            "radarlabels": True,
            "fields": value_field_configs,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "filled": True,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 5, "r": 5, "t": 0, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "position": "auto", "order": "normal"},
            "labels": {
                "visible": False,
                "position": "auto",
                "outer": {"fontsize": 10, "color": "rgba(68,68,68,1)"}
            },
            "visuals": [],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_stock_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    series_field_configs: list[dict] | None = None,
) -> dict[str, Any]:
    """Build stock (time series) chart configuration.

    series_field_configs кладётся в axes.series.
    """
    if series_field_configs is None:
        series_field_configs = []
    # Stock chart category must be date type with asc order
    if category_field_config:
        category_field_config["type"] = "date"
        category_field_config["order"] = "asc"

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "scaleType": "category",
            "visible": True,
            "showscale": True,
            "showtitle": False,
            "showgrid": False,
            "showlabels": True,
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "series", "title": "Серии", "type": "series", "fields": series_field_configs},
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "visible": True,
            "showtitle": False,
            "showscale": True,
            "showgrid": False,
            "showlabels": True,
            "selectedFieldIndex": -2,
            "fields": value_field_configs,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 5, "r": 5, "t": 5, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "position": "auto", "order": "normal"},
            "labels": {
                "visible": False,
                "position": "auto",
                "outer": {"fontsize": 12, "color": "rgba(68,68,68,1)"}
            },
            "visuals": [],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_speedometer_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build speedometer (gauge) configuration."""
    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "Категории",
            "title": "Категории",
            "type": "categories",
            "fields": [category_field_config] if category_field_config else []
        },
        {
            "name": "Показатель",
            "title": "Показатель",
            "type": "values",
            "visible": True,
            "fields": value_field_configs[:1] if value_field_configs else [],
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": "gauge",
            "autoApply": True,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 10, "r": 10, "t": 5, "b": 10, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": False, "position": "auto", "order": "normal"},
            "grid": {
                "visible": True,
                "width": 15,
                "minimum": 0,
                "maximum": 100,
                "tickCount": 5,
                "minorTickCount": 5,
                "labelFrequency": 1,
                "palette": {
                    "gradeCount": 2,
                    "gradientMode": False,
                    "invert": False,
                    "colors": ["#00D361", "#FF5433"]
                }
            },
            "labels": {
                "visible": True,
                "position": "inside",
                "outer": {"fontsize": 12, "color": "rgba(68,68,68,1)"},
                "inner": {"fontsize": 12, "color": "rgba(68,68,68,1)"}
            },
            "usePrefixes": False,
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


# ============================================================
# Bubble, Sunburst, TreeMap, ParallelCoords
# ============================================================

def _build_bubble_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    size_field_config: dict | list | None = None,
) -> dict[str, Any]:
    """Build bubble chart configuration.

    Bubble chart uses unique axes: xvalues, yvalues, values.
    value_fields[0] → Y axis, value_fields[1] → X axis.
    size_field → values axis (bubble size). If not provided, falls back to value_fields[0].
    size_field_config may be a single dict (legacy) or a list (CSV size_field).
    """
    # Split value fields: first=Y, second=X
    y_fields = [value_field_configs[0]] if value_field_configs else []
    x_fields = [value_field_configs[1]] if len(value_field_configs) > 1 else []
    # Size field: explicit (dict или list) или fallback на все value_field_configs
    if isinstance(size_field_config, dict):
        size_field_config = [size_field_config]
    size_fields = size_field_config if size_field_config else value_field_configs

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "scaleType": "category",
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "series", "title": "Серии", "type": "series", "fields": []},
        {
            "name": "yvalues",
            "title": "Значения Y",
            "type": "yvalues",
            "fields": y_fields,
            "sortable": True
        },
        {
            "name": "xvalues",
            "title": "Значения X",
            "type": "xvalues",
            "fields": x_fields,
            "sortable": True
        },
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "fields": size_fields,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 5, "r": 10, "t": 10, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "position": "auto", "order": "normal"},
            "labels": {"visible": False, "position": "auto", "inner": {}, "outer": {}},
            "visuals": [],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_sunburst_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_configs: list[dict] | dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build sunburst chart configuration.

    Sunburst supports multiple category fields for hierarchy levels:
    category_field="level1,level2,..." кладёт ВСЕ поля в categories-ось.
    """
    if isinstance(category_field_configs, dict):
        category_field_configs = [category_field_configs]
    cat_fields = list(category_field_configs or [])

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "fields": cat_fields
        },
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "fields": value_field_configs[:1] if value_field_configs else [],
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 5, "r": 5, "t": 10, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "position": "auto"},
            "labels": {"visible": True, "position": "auto"},
            "visuals": [],
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_treemap_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_configs: list[dict] | dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build treemap configuration (ECharts).

    Поддерживает иерархию: category_field="level1,level2,..." → все поля
    в categories-оси (уровни вложенности).
    """
    if isinstance(category_field_configs, dict):
        category_field_configs = [category_field_configs]
    cat_fields = list(category_field_configs or [])

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "Категории",
            "title": "Категории",
            "type": "categories",
            "fields": cat_fields
        },
        {"name": "series", "type": "series", "title": "Серии", "fields": []},
        {
            "name": "Значения",
            "title": "Значения",
            "type": "values",
            "fields": value_field_configs[:1] if value_field_configs else [],
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "filterMode": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 15, "r": 15, "t": 15, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "balloon": {"visible": True},
            "labels": {"visible": True, "position": "auto"},
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_parallel_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build parallel coordinates configuration (D3.js)."""
    # ParallelCoords puts all fields on single values axis
    all_fields = []
    if category_field_config:
        all_fields.append(category_field_config)
    all_fields.extend(value_field_configs)

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "Значения",
            "title": "Значения",
            "type": "values",
            "selectedFieldIndex": -2,
            "fields": all_fields,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "autoApply": True,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"t": 25, "r": 60, "b": 10, "l": 60},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "colorMin": "#b0071d",
            "colorMax": "#231480",
            "inversions": [],
            "tableSize": 100,
            "exportFromTable": False,
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


# ============================================================
# Pivot, Comparison, TreeGraph, Map, Tilemap
# ============================================================

def _build_pivot_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    row_field_configs: list[dict] | None = None,
    column_field_configs: list[dict] | None = None,
) -> dict[str, Any]:
    """Build pivot table configuration (6 unique axes).

    Args:
        row_field_configs: Fields for rows axis (from row_fields param).
                          Falls back to category_field_config if not provided.
        column_field_configs: Fields for columns axis (from column_fields param).
    """
    # Rows: use row_field_configs if provided, else category_field as single row
    if row_field_configs:
        rows_fields = row_field_configs
    elif category_field_config:
        rows_fields = [category_field_config]
    else:
        rows_fields = []

    axes = [
        {"name": "filters", "type": "filters", "title": "Фильтры", "selectedFieldIndex": 0, "fields": []},
        {
            "name": "rows",
            "type": "rows",
            "title": "Строки",
            "fields": rows_fields
        },
        {"name": "details", "type": "details", "title": "Детали", "fields": []},
        {
            "name": "columns",
            "type": "columns",
            "title": "Столбцы",
            "fields": column_field_configs or []
        },
        {"name": "spares", "type": "spares", "title": "Резервные", "fields": []},
        {
            "name": "values",
            "type": "values",
            "title": "Значения",
            "fields": value_field_configs,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "autoApply": True,
            "bgColor": "rgba(255, 255, 255, 1)",
            "autoHeightEnabled": True,
            "autoWidthEnabled": True,
            "margin": {"l": 5, "r": 10, "t": 10, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "dirty": False,
            "axesDefault": axes.copy(),
            "rules": []
        }
    }


def _build_comparison_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
    indicator_field_configs: list[dict] | None = None,
) -> dict[str, Any]:
    """Build comparison table configuration (unique axes: indicators, objects, values).

    ComparisonChart compares two "objects" (selected values of the objects field)
    across multiple "indicators" (metrics).

    Two data patterns supported:

    **Pattern A — UNPIVOT (recommended):**
        Dataset: region | metric_name | metric_value
        - category_field="region"          → objects axis (STRING, dimension)
        - column_fields="metric_name"      → indicators axis (STRING, metric labels)
        - value_field="metric_value"       → values axis (NUMBER, the measure)
        Objects are selected via config.filters: {"region": {"type": "by compare", "selected": [...]}}

    **Pattern B — Wide table (legacy, no indicators field):**
        Dataset: region | orders | revenue | returns
        - category_field="region"                  → objects axis
        - value_field="orders,revenue,returns"     → values + indicators (copied)
        Pattern A (UNPIVOT) is the more reliable layout for the frontend.
    """
    import copy

    # Indicators: use explicit string fields if provided (Pattern A),
    # otherwise copy value fields (Pattern B / legacy)
    if indicator_field_configs:
        indicators_fields = indicator_field_configs
    else:
        indicators_fields = copy.deepcopy(value_field_configs)

    axes = [
        {
            "name": "values",
            "type": "values",
            "title": "Значения",
            "fields": value_field_configs,
            "sortable": True
        },
        {"name": "series", "type": "series", "title": "Серии", "fields": []},
        {
            "name": "indicators",
            "type": "indicators",
            "title": "Показатели",
            "fields": indicators_fields
        },
        {
            "name": "objects",
            "type": "objects",
            "title": "Объекты",
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "filters", "type": "filters", "title": "Фильтры", "fields": []}
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "object1": "",
            "object2": "",
            "showDelta": False,
            "showPercent": False,
            "axes": axes,
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_tree_graph_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build tree graph (GoJS) configuration.

    Usage: category_field=node_key, value_field="parent_key,measure1,measure2"
      - category_field → identity axis (node key, MUST be numeric for frontend)
      - first value_field → linkage axis (parent key)
      - remaining value_fields → values axis (measures only, no linkage duplicate)

    IMPORTANT: Frontend does Number(identity) for scroll-to-root, so identity
    field MUST contain numeric values, not strings.
    """
    identity_field = category_field_config if category_field_config else None
    # First value field → linkage axis
    linkage_field = value_field_configs[0] if value_field_configs else None
    # Remaining value fields → values axis (exclude linkage field)
    measure_fields = value_field_configs[1:] if len(value_field_configs) > 1 else value_field_configs

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "identity",
            "title": "Признак",
            "type": "identity",
            "fields": [identity_field] if identity_field else []
        },
        {
            "name": "linkage",
            "title": "Связь",
            "type": "linkage",
            "fields": [linkage_field] if linkage_field else []
        },
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "fields": measure_fields,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": "tree",
            "layout": "TreeLayout",
            "model": {
                "class": "go.TreeModel",
                "nodeKeyProperty": "identity",
                "nodeParentKeyProperty": "linkage"
            },
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "zoomable": True,
            "initialZoom": 0.7,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "balloon": {
                "visible": False,
                # фронт читает lowercase fontsize
                "fontsize": 12,
                "fontColor": "rgba(0,0,0,1)",
                "bgColor": "rgba(255,255,255,1)"
            },
            "axes": axes,
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_map_config(
    component_type: str,
    title: str,
    chart_type: str,
    visual_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build Leaflet map configuration.

    Creates map with axes (categories + values). After adding the component,
    use map_set_geokeys to bind geographic data:
    - Bubble mode: config_overrides={"latfield": "lat", "lonfield": "lng"}
      Sets geodataId=-1, circles at lat/lng from data fields.
    - Choropleth mode: config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"}
      Colors GeoJSON polygons by data values.
    """
    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "fields": [category_field_config] if category_field_config else []
        },
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "fields": value_field_configs if value_field_configs else [],
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "visualType": visual_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 5, "r": 10, "t": 10, "b": 5, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "legend": {"visible": True, "position": "bottomright"},
            # initialZoom фронт не читает (зум = Leaflet-bounds)
            "autoCenter": True,
            "markers": {
                "showLabels": True,
                "showTooltip": True,
                # фронт читает clusterizationOff (инвертированный)
                "clusterizationOff": True,
            },
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_tilemap_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build tile map (Russian regions) configuration."""
    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "fields": [category_field_config] if category_field_config else []
        },
        {"name": "series", "title": "Тренд", "type": "series", "fields": []},
        {
            "name": "values",
            "title": "Значения",
            "type": "values",
            "fields": value_field_configs,
            "sortable": True
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "scale": {"startColor": "blue", "endColor": "red"},
            "legend": {"positionX": "right", "positionY": "bottom", "visible": True},
            "tiles": {"type": "square", "nameFontSize": "normal", "specialTiles": False},
            "grouping": {"enabled": True, "deltaK": 0.15},
            "autoZoom": True,
            "tileSize": 40,
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


# ============================================================
# Filter Panel, Simple/Utility components
# ============================================================

def _build_filter_panel_config(
    component_type: str,
    title: str,
    chart_type: str,
    value_field_configs: list[dict]
) -> dict[str, Any]:
    """Build filter control panel configuration."""
    # FilterPanel uses only the filters axis
    filter_fields = []
    for vf in value_field_configs:
        filter_fields.append({
            **vf,
            "agg": None,
            "global": True,
        })

    axes = [
        {
            "name": "filters",
            "type": "filters",
            "title": "Фильтры",
            "selectedFieldIndex": 0,
            "fields": filter_fields
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "autoApply": True,
            "showtitle": False,
            "noexport": True,
            "nocopy": True,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "dirty": False,
            "axesDefault": axes.copy()
        }
    }


def _build_simple_config(
    component_type: str,
    title: str,
    chart_type: str,
) -> dict[str, Any]:
    """Build simple/utility component configuration (Subheader, Iframe, Image, PageContainer, etc.)."""
    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": True,
            "nocopy": True,
            "bgColor": "rgba(255, 255, 255, 1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "dirty": False
        }
    }


# ============================================================
# HsIframe (Embedded Page)
# ============================================================

def _build_iframe_config(
    component_type: str,
    title: str,
    chart_type: str,
) -> dict[str, Any]:
    """Build iframe configuration.

    HsIframe embeds external URLs. Static mode uses frameUrl for the URL.
    Dynamic mode uses a dataset field on the values axis.
    No dataset needed for static mode.

    NOTE: Frontend reads config.frameUrl (top-level) for src, NOT config.link.name.
    Both are set for API/documentation compatibility.
    """
    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": False,
            "maximizable": True,
            "autoApply": True,
            "noexport": True,
            "nocopy": False,
            "bgColor": "rgba(255,255,255,1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "frameUrl": "",
            "link": {"name": "", "target": "_self"},
            "axes": [
                {"name": "values", "type": "values", "title": "Значения", "visible": True, "fields": []},
                {"name": "filters", "type": "filters", "title": "Фильтры", "fields": []},
                {"name": "keys", "type": "keys", "title": "Ключи", "fields": []},
            ],
            "dirty": False
        }
    }


# ============================================================
# HsImagePanel (Image Panel)
# ============================================================

def _build_image_panel_config(
    component_type: str,
    title: str,
    chart_type: str,
) -> dict[str, Any]:
    """Build image panel configuration.

    HsImagePanel displays images. Static mode: image loaded via UI.
    Dynamic mode: base64 image from a dataset field (type=file).
    No dataset needed for static mode (shows placeholder).
    """
    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": False,
            "maximizable": True,
            "autoApply": True,
            "noexport": True,
            "nocopy": True,
            "backgroundColor": "rgba(255,255,255,1)",
            "image": None,
            "backgroundSize": "contain",
            "backgroundPosition": "center center",
            "backgroundStyle": "no-repeat",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "link": {"name": "", "target": "_self"},
            "axes": [
                {"name": "values", "type": "values", "title": "Значения", "visible": True, "fields": []},
                {"name": "filters", "type": "filters", "title": "Фильтры", "fields": []},
            ],
            "dirty": False
        }
    }


# ============================================================
# HsHierarchicalFilterPanel (Hierarchical Filter)
# ============================================================

def _build_hierarchical_filter_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
) -> dict[str, Any]:
    """Build hierarchical filter configuration.

    Fields go on the 'filters' axis in hierarchy order:
    first field = top level, last field = bottom level.
    E.g., category_field=region, value_field=district,city
    → hierarchy: region > district > city
    """
    # All fields go on filters axis (hierarchy order)
    filter_fields = []
    if category_field_config:
        cat = category_field_config.copy()
        cat["type"] = "string"
        cat["agg"] = None
        filter_fields.append(cat)
    for vf in value_field_configs:
        f = vf.copy()
        f["type"] = "string"
        f["agg"] = None
        filter_fields.append(f)

    axes = [
        {
            "name": "filters",
            "title": "Фильтры",
            "type": "filters",
            "fields": filter_fields
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": True,
            "nocopy": True,
            "autoApply": True,
            "bgColor": "rgba(255,255,255,1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "axesDefault": [a.copy() for a in axes],
            "dirty": False
        }
    }


# ============================================================
# HsSwitchControlPanel (Category Switcher)
# ============================================================

def _build_switch_panel_config(
    component_type: str,
    title: str,
    chart_type: str,
    category_field_config: dict | None,
    value_field_configs: list[dict],
) -> dict[str, Any]:
    """Build switch control panel configuration.

    Manages globalCategories: each field on 'categories' axis
    becomes a selectable dimension in a dropdown.
    Uses category_field as primary, value_fields as alternatives.
    """
    # All fields go on categories axis
    cat_fields = []
    if category_field_config:
        cat = category_field_config.copy()
        cat["type"] = "string"
        cat["agg"] = None
        cat_fields.append(cat)
    for vf in value_field_configs:
        f = vf.copy()
        f["type"] = "string"
        f["agg"] = None
        cat_fields.append(f)

    axes = [
        {"name": "filters", "title": "Фильтры", "type": "filters", "fields": []},
        {
            "name": "categories",
            "title": "Категории",
            "type": "categories",
            "fields": cat_fields
        }
    ]

    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": True,
            "noexport": True,
            "nocopy": True,
            "autoApply": True,
            "bgColor": "rgba(255,255,255,1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": axes,
            "axesDefault": [a.copy() for a in axes],
            "dirty": False
        }
    }


# ============================================================
# HsTabsPanel (Navigation Tabs)
# ============================================================

def _build_tabs_panel_config(
    component_type: str,
    title: str,
    chart_type: str,
) -> dict[str, Any]:
    """Build tabs panel (navigation) configuration.

    HsTabsPanel is a container with horizontal button tabs for navigation
    between reports or triggering HTTP requests. No dataset, no axes.
    """
    return {
        "type": component_type,
        "config": {
            "title": title,
            "caption": title,
            "caption__ru": {"text": title, "textBefore": "", "textAfter": ""},
            "chartType": chart_type,
            "showtitle": False,
            "maximizable": False,
            "noexport": True,
            "nocopy": False,
            "autoApply": True,
            "orientation": "h",
            "height": 33,
            "bgColor": "rgba(255,255,255,1)",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 1},
            "filters": {},
            "filtersDefault": {},
            "variables": {},
            "visuals": [],
            "dirty": False
        }
    }


# ============================================================
# HsAudioplayer (Speech Analytics Player)
# ============================================================

def _build_audioplayer_config(
    component_type: str,
    title: str,
    chart_type: str,
    value_field_configs: list[dict],
) -> dict[str, Any]:
    """Build audioplayer configuration for speech analytics.

    Requires axes: values (audio + transcript/marker fields) + filters
    (a record-key field). The value fields carry the audio segment metadata
    (timestamps, channel, word, markers) consumed by the player.

    Config: resource.url must be set after creation with URL template.
    Not API-creatable — exists only through web UI, but can be updated via MCP.
    """
    return {
        "type": component_type,
        "config": {
            "title": title,
            "chartType": chart_type,
            "visualType": "area",
            "orientation": "v",
            "showtitle": True,
            "noexport": False,
            "nocopy": False,
            "resource": {
                "url": "",
                "uploadURL": ""
            },
            "backgroundColor": "",
            "progressBarColor": "rgba(0, 139, 139, 1)",
            "progressBarBackgroundColor": "",
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0, "pad": 0},
            "outline": {"enabled": False, "width": 4},
            "axes": [
                {"name": "values",  "type": "values",  "title": "Значения", "visible": True, "fields": value_field_configs},
                {"name": "filters", "type": "filters", "title": "Фильтры",  "fields": []},
            ],
            "dirty": False
        }
    }
