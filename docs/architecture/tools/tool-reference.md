<!-- GENERATED from app/server.py (живая интроспекция FastMCP mcp.list_tools); edit there, then run scripts/gen_public_docs.py -->
<!-- регенерируется scripts/gen_public_docs.py -->

# Справочник инструментов

Инструменты MCP-сервера ModusBI — это RPC-методы протокола JSON-RPC (Model Context Protocol). Снаружи интерфейс — JSON-RPC; при обращении к порталу сервер использует HTTP-вызовы вида action/command (не чистый REST).

Всего инструментов: **19**. Многие инструменты диспетчеризуют поведение по параметру `action` — ниже перечислены реальные значения `action` из схемы инструмента.

## `batch_operations`

Batch operations for multiple objects at once.

**Действия (`action`):**

`components_add`, `components_delete`, `layouts_update`, `styles_apply`, `reports_export`.

**Параметры:** `components`, `css`, `format`, `indices`, `layouts`, `output_dir`, `report_id`, `report_ids`.

## `component_axes`

Calc fields, PageContainer pages, pivot drill-through links, drill-down hierarchy,

**Действия (`action`):**

`help`, `calc_fields_list`, `calc_field_add`, `calc_field_update`, `calc_field_remove`, `page_list`, `page_add`, `page_remove`, `page_rename`, `pivot_link_set`, `pivot_link_remove`, `drill_get`, `drill_add_level`, `drill_delete_level`, `drill_change_level`, `drill_toggle_date_range`, `drill_set_field`, `tabs_button_list`, `tabs_button_add`, `tabs_button_delete`, `conditional_rule_add`, `conditional_rule_list`, `conditional_rule_delete`, `geodata_list`, `map_set_geokeys`, `map_get_geokeys`.

**Параметры:** `calc_expression`, `component_idx`, `config_overrides`, `dataset_id`, `drill_category_id`, `drill_direction`, `drill_selected`, `field_id`, `field_index`, `link_target`, `page_id`, `report_id`, `target_axis`, `target_url`, `title`, `value_field`.

## `component_crud`

Component CRUD + layout + slug introspection.

**Действия (`action`):**

`help`, `types_list`, `get`, `add`, `add_text_block`, `add_chart_with_conclusion`, `update`, `delete`, `data`, `copy`, `layout_update`, `layout_get_breakpoints`, `layout_update_breakpoint`, `swap`, `list_slugs`, `list_presets`.

**Параметры:** `aggregation`, `bg_color`, `breakpoint`, `category_field`, `column_fields`, `component_idx`, `component_idx_2`, `component_type`, `config_overrides`, `dataset_id`, `dataset_name`, `field_titles`, `h`, `info_fields`, `labels_visible`, `legend_position`, `legend_visible`, `limit` ….

## `component_filters`

Filter axis + global filter + cascade + grid layout management.

**Действия (`action`):**

`help`, `set_global_filter`, `reset_global_filters`, `filter_fields_list`, `filter_field_add`, `filter_field_remove`, `filter_set_cascade`, `filters_grid_layout`.

**Параметры:** `alias`, `component_idx`, `config_overrides`, `dataset_id`, `depends_on`, `field_type`, `report_id`, `reset_mode`, `reset_type`, `value_field`.

## `component_styling`

Conditional formatting, field sorting, map geo-binding (subset of component_axes).

**Действия (`action`):**

`help`, `conditional_rule_add`, `conditional_rule_list`, `conditional_rule_delete`, `field_sort_set`, `geodata_list`, `map_set_geokeys`, `map_get_geokeys`.

**Параметры:** `component_idx`, `config_overrides`, `field_index`, `report_id`, `value_field`.

## `data_export_operations`

Data export operations for components (CSV/Excel).

**Действия (`action`):**

`component_csv`, `component_xlsx`, `info`.

**Параметры:** `component_idx`, `filename`, `format`, `include_subtotals`, `include_totals`, `limit`, `output_dir`, `report_id`.

## `dataset_create_from_sql`

Create dataset from SQL — VALIDATES SQL, infers field types, builds semantic layer in one call.

**Параметры:** `caption`, `datasource_id`, `name`, `sql_query`.

## `dataset_operations`

CRUD for datasets (semantic layer on top of datasources).

**Действия (`action`):**

`help`, `list`, `get`, `fields_list`, `create`, `update`, `delete`.

**Параметры:** `caption`, `dataset_id`, `datasource_id`, `field_aliases`, `limit`, `name`, `offset`, `rls`, `sql`, `sql_rls`.

## `dataset_query`

Query data from a dataset (semantic model).

**Параметры:** `dataset_id`, `group`, `limit`, `order`, `select`, `variables`, `where`.

## `datasource_operations`

Read-only operations for data sources (database connections).

**Действия (`action`):**

`list`, `get`, `tables_list`, `table_fields`, `check_connection`, `create`, `update`, `delete`.

**Параметры:** `datasource_id`, `limit`, `offset`, `schema`, `table_name`.

## `instance_operations`

Get information about the configured portal instance.

**Действия (`action`):**

`list`, `get_active`.

## `preflight_check_datasource`

Preflight check: verify datasource can actually execute queries.

**Параметры:** `datasource_id`.

## `query_batch`

Execute multiple queries on a dataset in a single request.

**Параметры:** `dataset_id`, `queries`.

## `report_operations`

CRUD for reports + components_list + export (pdf/png/pptx) + variables/categories + clone.

**Действия (`action`):**

`help`, `list`, `get`, `create`, `update`, `delete`, `summary`, `components_list`, `groups_list`, `export`, `export_info`, `variables_list`, `variable_add`, `variable_update`, `variable_delete`, `categories_list`, `category_add`, `category_update`, `category_delete`, `get_options`, `update_options`, `clone`, `global_filters_list`, `global_filter_delete`.

**Параметры:** `allow_overlap_mode`, `caption`, `category_name`, `category_options`, `category_selected`, `cell_mode`, `description`, `filename`, `format`, `free_pane_movement`, `global_filters`, `group_id`, `grouping_mode`, `limit`, `name`, `no_gap_mode`, `offset`, `ord` ….

## `report_template`

Report template operations: list available templates, preview layouts, scaffold reports.

**Действия (`action`):**

`list`, `preview`, `scaffold`.

**Параметры:** `category_field`, `dataset_id`, `group_id`, `name`, `report_id`, `template`, `value_field`.

## `reportgroup_operations`

CRUD operations for report groups (folders for organizing reports).

**Действия (`action`):**

`list`, `get`, `create`, `update`, `delete`, `move`.

**Параметры:** `caption`, `group_id`, `group_options`, `image`, `is_extended`, `limit`, `menu`, `name`, `offset`, `parent_id`, `previous_group_id`.

## `security_operations`

Manage Row Level Security (RLS) for datasets.

**Действия (`action`):**

`status`, `enable`, `disable`, `update_filter`, `list_enabled`, `test`.

**Параметры:** `dataset_id`, `enabled`, `rls_query`.

## `sql_query_validate`

Validate SQL query and get result fields structure.

**Параметры:** `datasource_id`, `sql_query`.

## `style_operations`

CSS styling operations for reports.

**Действия (`action`):**

`classes_list`, `examples_list`, `get`, `update`, `validate`, `apply_theme`.

**Параметры:** `category`, `css`, `kpi_icons`, `mode`, `report_id`, `theme`.
