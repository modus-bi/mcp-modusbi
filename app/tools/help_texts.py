"""
Help texts for MCP tools — returned by `action="help"` to keep base docstrings
short while still exposing detailed examples on demand.

Structure:
    HELP_<tool> = {
        "_overview": "one-paragraph summary + critical warnings",
        "<action>": {
            "description": "...",
            "required": [...],
            "optional": [...],
            "examples": [{"title": "...", "call": "..."}],
            "notes": "...",   # optional
        },
    }

Dispatchers call `_help(action_name, HELP_X)` which returns the section
(or the full map if action_name is None/'all').
"""
from typing import Any


def _help(action_name: str | None, help_map: dict) -> dict[str, Any]:
    """Return help for a given action, or the full overview if None/'all'."""
    if not action_name or action_name in ("all", "overview", ""):
        return {
            "success": True,
            "overview": help_map.get("_overview", ""),
            "actions": sorted(k for k in help_map if not k.startswith("_")),
            "hint": "Call with action='help', slug_category=<action_name> for details, or action='help' alone for actions list.",
        }
    section = help_map.get(action_name)
    if section is None:
        return {
            "success": False,
            "error": f"Unknown action: {action_name}",
            "available_actions": sorted(k for k in help_map if not k.startswith("_")),
        }
    return {"success": True, "action": action_name, **section}


# =============================================================================
# component_crud
# =============================================================================
HELP_COMPONENT_CRUD = {
    "_overview": (
        "CRUD + layout + slugs. Tables ALWAYS need aggregation='none'. "
        "text_content is sanitized (no <script>/on* handlers). "
        "filter_field_add MUST be called on EACH data-component too (not only the FilterControlPanel), "
        "otherwise the filter selects values but does not actually filter data."
    ),
    "types_list": {
        "description": "List available component types",
        "examples": [{"title": "list", "call": "component_crud(action='types_list')"}],
    },
    "add": {
        "description": "Add a component to a report",
        "required": ["report_id", "component_type", "title", "dataset_id (except utility types)", "value_field (except utility types)"],
        "optional": [
            "dataset_name (вместо dataset_id)", "category_field", "aggregation",
            "position / x+y+w+h", "field_titles", "where_filter",
            "legend_visible", "legend_position", "labels_visible",
            "orientation", "bg_color", "stacking", "config_overrides", "preset",
        ],
        "examples": [
            {
                "title": "Bar chart",
                "call": "component_crud(action='add', report_id=35, component_type='HsBarAMchartsChart', title='Sales by Region', dataset_id=5, category_field='region', value_field='amount', aggregation='sum')",
            },
            {
                "title": "Table with Russian column names",
                "call": "component_crud(action='add', report_id=35, component_type='HsTableReactabularChart', title='Commands', dataset_id=5, value_field='object_name,command_name,title', value_fields_type='string', aggregation='none', field_titles={'object_name':'Объект', 'command_name':'Команда', 'title':'Заголовок'})",
            },
            {
                "title": "ComparisonChart UNPIVOT pattern (object|metric|value)",
                "call": "component_crud(action='add', report_id=35, component_type='HsComparisonChart', title='Compare', dataset_id=5, category_field='region', column_fields='metric_name', value_field='metric_value', aggregation='sum')",
                "notes": "Requires UNPIVOT dataset. Then update with config_overrides={'comparison.object1':'A', 'comparison.object2':'B'}.",
            },
        ],
    },
    "add_text_block": {
        "description": "Add HsTextBlock with HTML body (auto-sanitized).",
        "required": ["report_id", "title", "text_content"],
        "optional": ["position"],
        "examples": [{"title": "text block", "call": "component_crud(action='add_text_block', report_id=35, title='Summary', text_content='<div>...</div>', position={'x':0,'y':10,'w':12,'h':6})"}],
    },
    "add_chart_with_conclusion": {
        "description": "Add chart + text block pair with automatic positioning at bottom.",
        "required": ["report_id", "component_type", "title", "dataset_id", "value_field", "text_content"],
        "examples": [{"title": "chart + text", "call": "component_crud(action='add_chart_with_conclusion', report_id=35, component_type='HsBarAMchartsChart', title='...', dataset_id=5, category_field='...', value_field='...', text_content='<div>...</div>')"}],
    },
    "update": {
        "description": "Update component title/dataset/fields/aggregation and visual params",
        "required": ["report_id", "component_idx"],
        "tip_showtitle": "Если componentHeader дублирует подписи legend (например title='Sales' и в legend серия с тем же именем) — установите config_overrides={'showtitle':False} чтобы скрыть header. Top-level config.showtitle slug, default=True.",
        "examples": [
            {"title": "Level 1+ visuals", "call": "component_crud(action='update', report_id=35, component_idx=0, title='Sales', legend_visible=True, bg_color='#F5F5F5')"},
            {"title": "Level 2 flat slug overrides", "call": "component_crud(action='update', report_id=35, component_idx=0, config_overrides={'legend.fontSize':16, 'axes.categoryLabelAngle':45, 'visuals.columnWidth':60})"},
            {"title": "Per-column for tables", "call": "component_crud(action='update', report_id=35, component_idx=0, config_overrides={'columns.region.width':200, 'columns.amount.precision':2, 'columns.amount.suffix':' USD'})"},
            {"title": "Hide header to dedupe with legend", "call": "component_crud(action='update', report_id=35, component_idx=0, config_overrides={'showtitle':False})"},
            {"title": "Level 3 preset", "call": "component_crud(action='update', report_id=35, component_idx=0, preset='kpi')"},
        ],
    },
    "get": {
        "description": "Get component config by index",
        "required": ["report_id", "component_idx"],
    },
    "data": {
        "description": "Get component data (rows currently rendered)",
        "required": ["report_id", "component_idx"],
    },
    "delete": {
        "description": "Delete component",
        "required": ["report_id", "component_idx"],
    },
    "layout_update": {
        "description": "Update position/size for ALL breakpoints",
        "required": ["report_id", "component_idx"],
        "optional": ["x", "y", "w", "h", "z_index", "position"],
    },
    "layout_get_breakpoints": {
        "description": "Get layout positions per breakpoint (hd/lg/md/sm/xs/xxs)",
        "required": ["report_id", "component_idx"],
    },
    "layout_update_breakpoint": {
        "description": "Update layout for single breakpoint only",
        "required": ["report_id", "component_idx", "breakpoint", "x/y/w/h"],
    },
    "swap": {
        "description": "Swap two components",
        "required": ["report_id", "component_idx", "component_idx_2"],
    },
    "copy": {
        "description": "Deep-copy a component",
        "required": ["report_id", "component_idx"],
        "optional": ["target_report_id", "title"],
    },
    "list_slugs": {
        "description": "List config slugs (lazy: summary / drill-down / type filter). slug_category prefixes: "
                       "'search:color' (substring search), 'ui:legend' or 'ui:' (add UI label+panel section "
                       "per slug — OFF by default, costs tokens, request per component/category when needed).",
        "optional": ["component_type", "slug_category"],
    },
    "list_presets": {"description": "List available presets (minimal, presentation, dashboard, dark, print, kpi)"},
}


# =============================================================================
# component_filters
# =============================================================================
HELP_COMPONENT_FILTERS = {
    "_overview": (
        "Filter axis management + global filters. "
        "⚠️ After filter_field_add on a FilterControlPanel, repeat on EVERY data-component "
        "that should be filtered — otherwise dropdown lists values but data does not filter."
    ),
    "set_global_filter": {
        "description": "Set value on a FilterControlPanel (alias обязателен для НАСТОЯЩЕГО глобального фильтра — без него пишется только локальный cfg.selectedValue)",
        "required": ["report_id", "component_idx"],
        "optional": ["value_field (comma-separated значения; пусто = сброс выбора)", "alias (без него глобальный фильтр не активируется)"],
    },
    "reset_global_filters": {
        "description": "Reset all global filters on a report",
        "required": ["report_id"],
    },
    "filter_fields_list": {
        "description": "List fields on the component's filter axis",
        "required": ["report_id", "component_idx"],
    },
    "filter_field_add": {
        "description": "Add a field to component's filter axis (needed on FilterControlPanel AND each data component)",
        "required": ["report_id", "component_idx", "value_field", "alias", "field_type", "dataset_id"],
        "optional": ["depends_on (cascade parent alias)"],
        "examples": [{"title": "filter with cascade", "call": "component_filters(action='filter_field_add', report_id=35, component_idx=3, value_field='region', alias='Район', field_type='string', dataset_id=5, depends_on='Город')"}],
    },
    "filter_field_remove": {
        "description": "Remove a field from component's filter axis",
        "required": ["report_id", "component_idx", "value_field"],
    },
    "filter_set_cascade": {
        "description": "Set or remove cascade dependency between filters",
        "required": ["report_id", "alias"],
        "optional": ["depends_on (parent alias; опустить → снять каскад с фильтра alias)", "reset_mode", "reset_type"],
    },
    "filters_grid_layout": {
        "description": (
            "Равномерно распределить N компонентов по сетке cols×rows. "
            "Convenience поверх layout_update_breakpoint — заменяет ручное "
            "вычисление w для каждого breakpoint при паттерне 'фильтры в ряд'."
        ),
        "required": ["report_id", "config_overrides={component_indices:[int], cols:int}"],
        "optional": ["config_overrides.rows (default 1)", "config_overrides.y_start (default 0)", "config_overrides.h (default 3)"],
        "examples": [
            {
                "title": "4 фильтра в один ряд (hd: 60 cols ÷ 4 = 15 каждый)",
                "call": (
                    "component_filters(action='filters_grid_layout', "
                    "report_id=35, "
                    "config_overrides={'component_indices':[14,15,16,17], 'cols':4})"
                ),
            },
            {
                "title": "8 фильтров в 2×4 сетку",
                "call": (
                    "component_filters(action='filters_grid_layout', "
                    "report_id=35, config_overrides={"
                    "'component_indices':[10,11,12,13,14,15,16,17], "
                    "'cols':4, 'rows':2})"
                ),
            },
        ],
        "notes": "Применяется ко всем 6 breakpoints (hd/lg/md/sm/xs/xxs) — ширина пересчитывается автоматически по total_cols каждого breakpoint.",
    },
}


# =============================================================================
# component_axes
# =============================================================================
HELP_COMPONENT_AXES = {
    "_overview": "Calculated fields, pivot links, drill-down, TabsPanel buttons, PageContainer pages, conditional formatting, map geokeys.",
    "calc_fields_list": {"description": "List calculated fields", "required": ["report_id", "component_idx"]},
    "calc_field_add": {
        "description": "Add calculated field",
        "required": ["report_id", "component_idx", "calc_expression"],
        "optional": ["target_axis (default 'values')"],
    },
    "calc_field_update": {"description": "Update calc field", "required": ["report_id", "component_idx", "value_field", "calc_expression"]},
    "calc_field_remove": {"description": "Remove calc field", "required": ["report_id", "component_idx", "value_field"]},
    "page_list": {"description": "List PageContainer pages", "required": ["report_id", "component_idx"]},
    "page_add": {"description": "Add a page", "required": ["report_id", "component_idx", "title"]},
    "page_remove": {"description": "Remove a page", "required": ["report_id", "component_idx", "page_id"]},
    "page_rename": {"description": "Rename a page", "required": ["report_id", "component_idx", "page_id", "title"]},
    "pivot_link_set": {
        "description": "Set drill-through link on a pivot field",
        "required": ["report_id", "component_idx", "field_id", "target_url", "title"],
        "optional": ["link_target (default '_blank')"],
    },
    "pivot_link_remove": {"description": "Remove drill-through link", "required": ["report_id", "component_idx", "field_id"]},
    "drill_get": {"description": "Read drill-down config", "required": ["report_id", "component_idx"]},
    "drill_add_level": {"description": "Add a level to drill hierarchy", "required": ["report_id", "component_idx"]},
    "drill_delete_level": {"description": "Remove last level", "required": ["report_id", "component_idx"]},
    "drill_change_level": {"description": "Set field at a drill level", "required": ["report_id", "component_idx", "field_index", "field_id"]},
    "drill_toggle_date_range": {"description": "Toggle drillDateByRange", "required": ["report_id", "component_idx"]},
    "drill_set_field": {"description": "Set drill field mapping (table-only)", "required": ["report_id", "component_idx", "drill_category_id", "drill_direction", "drill_selected"]},
    "conditional_rule_add": {
        "description": "Add conditional formatting rule",
        "required": ["report_id", "component_idx", "config_overrides={field, operator, value, color, background, whole_row, bold}"],
    },
    "conditional_rule_list": {"description": "List rules", "required": ["report_id", "component_idx"]},
    "conditional_rule_delete": {"description": "Delete rule by index", "required": ["report_id", "component_idx", "field_index"]},
    "geodata_list": {"description": "List available GeoJSON files on portal"},
    "map_set_geokeys": {
        "description": "Гео-привязка карты. 3 режима: bubble | choropleth | МУЛЬТИСЛОЙ (цветные районы + отдельные точки + кластеры + подсказки в ОДНОЙ карте)",
        "required": ["report_id", "component_idx", "config_overrides"],
        "modes": {
            "bubble": "{latfield, lonfield} — круги на координатах",
            "choropleth": "{geo_type, geofield} — заливка полигонов по значению (geo_type из geodata_list)",
            "multilayer": "{geo_type, geofield, point_id_field, latfield, lonfield, tooltip_field?} — ОДНА карта: раскрашенные районы (sheet0) + отдельные точки на координатах (sheet1) + кластеры (вкл. map.markers.clustering=true) + подсказка деталей при наведении (опц. tooltip_field). Точка=строка → датасет должен иметь УНИКАЛЬНЫЙ id на строку (point_id_field) + lat/lon; для подсказки — текстовое поле (напр. конкат тип·тяжесть·жертвы).",
        },
        "example": "component_styling(action='map_set_geokeys', report_id=35, component_idx=0, config_overrides={'geo_type':'spb_districts.geojson.json','geofield':'NAME','point_id_field':'incident_id','latfield':'lat','lonfield':'lon','tooltip_field':'details'})",
    },
    "map_get_geokeys": {"description": "Get geokeys config", "required": ["report_id", "component_idx"]},
    "tabs_button_list": {"description": "List buttons in TabsPanel", "required": ["report_id", "component_idx"]},
    "tabs_button_add": {
        "description": "Add navigation button to TabsPanel",
        "required": ["report_id", "component_idx", "title"],
        "optional": ["config_overrides={link, fill_color, text_color, link_target}"],
    },
    "tabs_button_delete": {"description": "Delete button by index", "required": ["report_id", "component_idx", "field_index"]},
}


# =============================================================================
# component_styling
# =============================================================================
HELP_COMPONENT_STYLING = {
    "_overview": (
        "Conditional formatting, field sort, map geo-binding. "
        "See `component_crud(action='list_slugs')` for available config_overrides keys."
    ),
    "conditional_rule_add": {
        "description": "Add conditional formatting rule",
        "required": ["report_id", "component_idx", "config_overrides={field, operator, value, color, background, whole_row, bold}"],
    },
    "conditional_rule_list": {"description": "List rules", "required": ["report_id", "component_idx"]},
    "conditional_rule_delete": {"description": "Delete rule by index", "required": ["report_id", "component_idx", "field_index"]},
    "field_sort_set": {
        "description": "Set sort order on a field. ⭐ ЕДИНСТВЕННЫЙ надёжный способ задать сортировку категорий чарта — НЕ через SQL ORDER BY (фронт делает свою группировку поверх результата) и НЕ через config_overrides={'sort':...} (такой slug дропается валидатором).",
        "required": ["report_id", "component_idx", "value_field"],
        "optional": ["config_overrides={'order':'asc'|'desc'}"],
        "notes": "Сортировка корректна только на числовых полях (year:int). Для строковых полей (year_str:string) фронт сортирует лексикографически — используйте числовое поле в category_field.",
        "examples": [
            {"title": "year ASC", "call": "component_styling(action='field_sort_set', report_id=35, component_idx=23, value_field='year', config_overrides={'order':'asc'})"},
        ],
    },
    "geodata_list": {"description": "List available GeoJSON files on portal"},
    "map_set_geokeys": {
        "description": "Гео-привязка карты. 3 режима: bubble | choropleth | МУЛЬТИСЛОЙ (цветные районы + отдельные точки + кластеры + подсказки в ОДНОЙ карте)",
        "required": ["report_id", "component_idx", "config_overrides"],
        "modes": {
            "bubble": "{latfield, lonfield} — круги на координатах",
            "choropleth": "{geo_type, geofield} — заливка полигонов по значению (geo_type из geodata_list)",
            "multilayer": "{geo_type, geofield, point_id_field, latfield, lonfield, tooltip_field?} — ОДНА карта: раскрашенные районы (sheet0) + отдельные точки на координатах (sheet1) + кластеры (вкл. map.markers.clustering=true) + подсказка деталей при наведении (опц. tooltip_field). Точка=строка → датасет должен иметь УНИКАЛЬНЫЙ id на строку (point_id_field) + lat/lon; для подсказки — текстовое поле (напр. конкат тип·тяжесть·жертвы).",
        },
        "example": "component_styling(action='map_set_geokeys', report_id=35, component_idx=0, config_overrides={'geo_type':'spb_districts.geojson.json','geofield':'NAME','point_id_field':'incident_id','latfield':'lat','lonfield':'lon','tooltip_field':'details'})",
    },
    "map_get_geokeys": {"description": "Get geokeys config", "required": ["report_id", "component_idx"]},
}


# =============================================================================
# report_operations
# =============================================================================
HELP_REPORT = {
    "_overview": (
        "CRUD for reports + components_list + export (pdf/pptx) + variables/categories. "
        "clone copies all components, filters, variables. list is paginated (limit=50, offset=0)."
    ),
    "list": {
        "description": "List reports (paginated)",
        "optional": ["group_id", "limit", "offset"],
        "examples": [{"title": "page 1", "call": "report_operations(action='list', limit=50, offset=0)"}, {"title": "by group", "call": "report_operations(action='list', group_id=20)"}],
    },
    "get": {"description": "Get report (includes global_variables)", "required": ["report_id"]},
    "create": {"description": "Create report", "required": ["name", "caption", "group_id"], "optional": ["parent_id", "description", "ord", "remark"]},
    "update": {"description": "Update report", "required": ["report_id"], "optional": ["name", "caption", "group_id", "remark", "description", "ord", "global_filters"]},
    "delete": {"description": "Delete report", "required": ["report_id"]},
    "summary": {"description": "Get report text summary", "required": ["report_id"]},
    "components_list": {"description": "List report components", "required": ["report_id"]},
    "groups_list": {"description": "List report groups (paginated)", "optional": ["limit", "offset"]},
    "export": {
        "description": "Export report to file",
        "required": ["report_id"],
        "optional": ["format (pdf/png/pptx)", "page_size", "page_orientation", "output_dir", "filename", "timeout"],
    },
    "export_info": {"description": "Get export directory config"},
    "clone": {
        "description": "Clone report with all components/filters/variables",
        "required": ["report_id"],
        "optional": ["name", "group_id"],
        "examples": [{"title": "clone", "call": "report_operations(action='clone', report_id=35, name='Copy of X', group_id=20)"}],
    },
    "variables_list": {"description": "List globalVariables", "required": ["report_id"]},
    "variable_add": {"description": "Add variable", "required": ["report_id", "variable_name", "variable_value"]},
    "variable_update": {"description": "Update variable", "required": ["report_id", "variable_name", "variable_value"]},
    "variable_delete": {"description": "Delete variable", "required": ["report_id", "variable_name"]},
    "categories_list": {"description": "List globalCategories", "required": ["report_id"]},
    "category_add": {"description": "Add category", "required": ["report_id", "category_name", "category_selected", "category_options"]},
    "category_update": {"description": "Update category", "required": ["report_id", "category_name"], "optional": ["category_selected", "category_options"]},
    "category_delete": {"description": "Delete category", "required": ["report_id", "category_name"]},
    "get_options": {"description": "Get report grid options", "required": ["report_id"]},
    "update_options": {"description": "Update grid options", "required": ["report_id"], "optional": ["cell_mode", "allow_overlap_mode", "free_pane_movement", "no_gap_mode", "recalculated_cell_mode", "grouping_mode"]},
    "global_filters_list": {"description": "List all globalFilters", "required": ["report_id"]},
    "global_filter_delete": {"description": "Delete a global filter by name", "required": ["report_id", "variable_name"]},
}


# =============================================================================
# dataset_operations
# =============================================================================
HELP_DATASET = {
    "_overview": (
        "CRUD for datasets (semantic layer). ⚠️ field_aliases MUST be set BEFORE binding dataset to components — "
        "backend rejects alias changes on dataset fields already used in components (HTTP 400). "
        "Workflow: create dataset → set field_aliases → THEN add components. "
        "list is paginated (limit=50, offset=0). "
        "dataset_create_from_sql is RECOMMENDED over create (it validates SQL)."
    ),
    "list": {"description": "List datasets (paginated)", "optional": ["limit", "offset"]},
    "get": {
        "description": "Get dataset with full metadata",
        "required": ["dataset_id"],
        "notes": "total_rows=null означает 'не подсчитано' — backend лениво считает count, для свежесозданных датасетов всегда 0. Для актуального количества: dataset_query(\"SELECT COUNT(*) FROM <view>\").",
    },
    "fields_list": {"description": "List fields with types", "required": ["dataset_id"]},
    "create": {
        "description": "Create empty dataset; with sql it routes to dataset_create_from_sql (SQL IS validated; response includes fields[])",
        "required": ["name", "datasource_id"],
        "optional": ["caption", "sql"],
    },
    "update": {
        "description": "Update dataset (auto-validates SQL when query changes)",
        "required": ["dataset_id"],
        "optional": ["name", "caption", "datasource_id", "query", "rls", "query_rls", "field_aliases"],
        "examples": [
            {"title": "set aliases BEFORE binding", "call": "dataset_operations(action='update', dataset_id=5, field_aliases={'region':'Регион', 'amount':'Сумма'})"},
            {"title": "enable RLS", "call": "dataset_operations(action='update', dataset_id=5, rls=True, query_rls='user_id = :current_user_id')"},
        ],
    },
    "delete": {"description": "Delete dataset", "required": ["dataset_id"]},
}


# =============================================================================
# report_template (pointer for scaffold)
# =============================================================================
HELP_REPORT_TEMPLATE = {
    "_overview": (
        "Scaffold complete reports from presets (kpi_dashboard, ranking, comparison, factor_analysis, geo_analytics, simple). "
        "Actions: list, preview, scaffold. scaffold creates a new report with components pre-wired. "
        "Prefer scaffold over manual create+add when starting from a standard template."
    ),
}
