"""
Literal type aliases for `action` parameters across all MCP tools.

Exporting these as typing.Literal makes FastMCP emit JSON Schema `enum`,
which lets strict LLM providers (GigaChat, OpenAI) reject invalid actions
and gives Claude/GPT a precise list to choose from.

Grouped per tool. Keep in sync with each tool's dispatcher `match action:`.
"""
from typing import Literal


# --- instance_operations (2: read-only) ---
InstanceAction = Literal["list", "get_active"]


# --- report_operations (23) ---
ReportAction = Literal[
    "help",
    "list", "get", "create", "update", "delete", "summary",
    "components_list", "groups_list",
    "export", "export_info",
    "variables_list", "variable_add", "variable_update", "variable_delete",
    "categories_list", "category_add", "category_update", "category_delete",
    "get_options", "update_options",
    "clone",
    "global_filters_list", "global_filter_delete",
]


# --- dataset_operations (6 + help) ---
DatasetAction = Literal[
    "help",
    "list", "get", "fields_list", "create", "update", "delete",
]


# --- component_crud (15 + help) ---
ComponentCrudAction = Literal[
    "help",
    "types_list", "get", "add", "add_text_block", "add_chart_with_conclusion",
    "update", "delete", "data", "copy",
    "layout_update", "layout_get_breakpoints", "layout_update_breakpoint",
    "swap",
    "list_slugs", "list_presets",
]


# --- component_filters (7 + help) ---
ComponentFiltersAction = Literal[
    "help",
    "set_global_filter", "reset_global_filters",
    "filter_fields_list", "filter_field_add", "filter_field_remove",
    "filter_set_cascade",
    "filters_grid_layout",  # равномерное распределение N фильтров
]


# --- component_axes (25 + help) ---
ComponentAxesAction = Literal[
    "help",
    "calc_fields_list", "calc_field_add", "calc_field_update", "calc_field_remove",
    "page_list", "page_add", "page_remove", "page_rename",
    "pivot_link_set", "pivot_link_remove",
    "drill_get", "drill_add_level", "drill_delete_level", "drill_change_level",
    "drill_toggle_date_range", "drill_set_field",
    "tabs_button_list", "tabs_button_add", "tabs_button_delete",
    "conditional_rule_add", "conditional_rule_list", "conditional_rule_delete",
    "geodata_list", "map_set_geokeys", "map_get_geokeys",
]


# --- component_styling (7 + help) ---
ComponentStylingAction = Literal[
    "help",
    "conditional_rule_add", "conditional_rule_list", "conditional_rule_delete",
    "field_sort_set",
    "geodata_list", "map_set_geokeys", "map_get_geokeys",
]


# --- component_operations (legacy, full 47 + help) ---
ComponentAction = Literal[
    "help",
    "types_list", "get", "add", "add_text_block", "add_chart_with_conclusion",
    "update", "delete", "data", "copy", "swap",
    "layout_update", "layout_get_breakpoints", "layout_update_breakpoint",
    "list_slugs", "list_presets",
    "set_global_filter", "reset_global_filters",
    "filter_fields_list", "filter_field_add", "filter_field_remove", "filter_set_cascade",
    "calc_fields_list", "calc_field_add", "calc_field_update", "calc_field_remove",
    "page_list", "page_add", "page_remove", "page_rename",
    "pivot_link_set", "pivot_link_remove",
    "drill_get", "drill_add_level", "drill_delete_level", "drill_change_level",
    "drill_toggle_date_range", "drill_set_field",
    "tabs_button_list", "tabs_button_add", "tabs_button_delete",
    "conditional_rule_add", "conditional_rule_list", "conditional_rule_delete",
    "field_sort_set",
    "geodata_list", "map_set_geokeys", "map_get_geokeys",
]


# --- datasource_operations (5) ---
DatasourceAction = Literal[
    "list", "get", "tables_list", "table_fields", "check_connection",
    # write operations return "not_supported" — keep for schema completeness
    "create", "update", "delete",
]


# --- style_operations (6) ---
StyleAction = Literal[
    "classes_list", "examples_list", "get", "update", "validate",
    "apply_theme",  # brand-pack CSS из 5-цветной темы
]


# --- reportgroup_operations (6) ---
ReportGroupAction = Literal[
    "list", "get", "create", "update", "delete", "move",
]


# --- data_export_operations (3) ---
DataExportAction = Literal[
    "component_csv", "component_xlsx", "info",
]


# --- batch_operations (5) ---
BatchAction = Literal[
    "components_add", "components_delete",
    "layouts_update", "styles_apply", "reports_export",
]


# --- report_template (3) ---
ReportTemplateAction = Literal[
    "list", "preview", "scaffold",
]


# --- security_operations (6) ---
SecurityAction = Literal[
    "status", "enable", "disable", "update_filter", "list_enabled", "test",
]
