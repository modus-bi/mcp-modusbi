"""Canonical parameter descriptions — single source of truth for @mcp.tool() signatures.

These strings are used as `Field(description=...)` text for parameters that repeat
across multiple tools. Keeping them in one module ensures consistent wording and
makes it easy to refine descriptions in one place.

Descriptions are written in English (international standard for MCP tools) and
kept concise — one line each, focused on what to pass and where to get it.
"""

CANONICAL: dict[str, str] = {
    # === Identifiers ===
    "report_id": "Numeric ID of the report (e.g. 35). Use report_operations(action='list') to list IDs.",
    "dataset_id": "Numeric ID of the dataset (e.g. 5). Use dataset_operations(action='list') to list IDs.",
    "datasource_id": "Numeric ID of the datasource connection (NOT driver type, e.g. 3). Use datasource_operations(action='list').",
    "component_idx": "Zero-based index of component in the report (0 = first component).",
    "group_id": "Numeric ID of the report group (folder). Use reportgroup_operations(action='list') to list IDs.",
    "field_id": "String identifier of a field within a component (assigned when the field is added).",
    "page_id": "Numeric ID of a page inside a multi-page component (TabsPanel/PageContainer).",
    "field_index": "Zero-based index of an item (rule / button / field) within its list.",

    # === Names / Captions ===
    "name": "Short technical name (latin, lower_snake_case). Shown in listings and used as internal identifier.",
    "caption": "Human-readable label shown in the UI (supports Cyrillic/Unicode).",
    "dataset_name": "Human-readable name of the dataset to bind to the component (resolved via fuzzy match).",
    "title": "Human-readable component title shown in the UI header.",
    "alias": "Human-readable label for a filter field (Russian/Unicode supported, e.g. 'Регион').",
    "description": "Optional free-form description shown in the UI / listings.",
    "remark": "Optional free-form remark/note attached to the entity.",

    # === Layout ===
    "x": "Grid column of the component's left edge (0..59 for HD breakpoint).",
    "y": "Grid row of the component's top edge. Auto-calculated if omitted.",
    "w": "Width in grid columns. Typical: filter=10..15, KPI=15, chart=30, table=60.",
    "h": "Height in grid rows. Typical: filter=3, KPI=6, chart=12, table=18.",
    "breakpoint": "Screen-size breakpoint for layout: hd (>=1200), lg (992-1199), md (768-991), sm (576-767), xs (<576), xxs.",
    "ord": "Sort order / position index within a list (integer, 0-based).",
    "parent_id": "Numeric ID of the parent entity (0 = root).",
    "previous_group_id": "Numeric ID of the group after which to place this group when moving (for ordering).",

    # === Data fields ===
    "value_field": "Dataset field name used as main value/metric (e.g. 'amount').",
    "category_field": "Dataset field name used as category/dimension (e.g. 'region').",
    "row_fields": "Comma-separated dataset fields for pivot rows (e.g. 'region,city').",
    "column_fields": "Comma-separated dataset fields for pivot columns (e.g. 'year,quarter').",
    "size_field": "Dataset field used for bubble size in BubbleChart (numeric).",
    "target_axis": "Axis to attach a calculated field to: 'values', 'categories', 'rows', 'columns'.",

    # === Visual ===
    "component_type": "Component class name, e.g. 'HsBarAMchartsChart' (chart), 'HsTotalsPanelV2' (KPI), 'HsTableReactabularChart' (table), 'HsTextBlock' (text). Use component_crud(action='types_list') for full list.",
    "text_content": "HTML text content for HsTextBlock components (sanitized; no <script> tags allowed).",
    "legend_visible": "Show or hide the chart legend (true/false).",
    "legend_position": "Position of the chart legend: 'top', 'bottom', 'left', or 'right'.",
    "labels_visible": "Show or hide value labels on chart elements (true/false).",
    "bg_color": "Background color in rgba() or hex format, e.g. 'rgba(255,255,255,1)' or '#FFFFFF'.",
    "slug_category": "For list_slugs: filter by category (e.g. 'legend', 'margin', 'data') OR search by substring with 'search:' prefix (e.g. 'search:color'). Prepend 'ui:' to add UI metadata (ui_label/ui_section — the control name & panel section from the frontend) to each slug, e.g. 'ui:legend' or 'ui:' (whole component) or 'ui:search:color'. UI metadata is OFF by default (it adds ~70% tokens); request it only when you need the panel labels for one component/category. Use list_slugs() without category to discover categories. For get: pass 'raw' to include config_raw (full raw component config).",

    # === Query / pagination ===
    "limit": "Maximum number of rows/items to return.",
    "offset": "Row/item offset for pagination (0-based).",
    "query": "SQL query string for the dataset's semantic layer.",
    "rls": "Enable or disable Row Level Security on the dataset (true/false).",
    "query_rls": "RLS filter SQL using ':current_user_id' placeholder, e.g. 'user_id = :current_user_id'.",

    # === Component overrides ===
    "config_overrides": "Flat slug overrides dict; see component_crud(action='list_slugs') for keys.",

    # === Export ===
    "output_dir": "Absolute path to export output dir (fallback: MODUSBI_EXPORT_DIR env var or ~/Downloads/modusbi_exports).",
    "filename": "Output file name without extension (extension is added based on format).",
    "format": "Data export format: 'csv' or 'xlsx' (data_export_operations — фактический формат определяется action component_csv/component_xlsx). Для экспорта отчётов в 'pdf'/'png'/'pptx' — report_operations(action='export')/batch reports_export (свой format).",

    # === Filter axis ===
    "field_type": "Dataset field type for filter binding: 'string', 'number', 'date', 'datetime', or 'boolean'.",
    "depends_on": "Alias of the parent filter this cascade filter depends on (dropdown values are filtered by parent selection).",
    "reset_type": "Reset trigger for dependent filter: 'always' (the only value supported by the frontend).",

    # === Calculated fields ===
    "calc_expression": "Calculated field expression using dataset field names (e.g. 'amount * 1.2' or 'SUM(amount) / COUNT(id)').",

    # === Drill-through / drill-down ===
    "target_url": "Absolute URL template for pivot drill-through links (supports {field} placeholders).",
    "drill_category_id": "String ID of the drill-down category (level identifier in the hierarchy).",
    "drill_direction": "Drill direction: 'drilldown' (go deeper) or 'drillup' (go back one level).",
    "drill_selected": "Selected value to pass when drilling (context from the clicked row/bar).",

    # === Security ===
    "enabled": "Enable (true) or disable (false) the feature on the target entity.",
    "rls_query": "Row Level Security filter SQL using ':current_user_id' placeholder.",

    # === Style ===
    "css": "CSS text to apply. For style_operations(update) this REPLACES all existing CSS — GET current CSS first and merge.",
    "category": "Category filter. For classes_list: 'all', 'header', 'selectors', 'components', 'tables', 'charts', 'maps', 'pivot', 'filters', 'grid', 'page_container', 'icons', 'text_block', 'mui', 'scrollbar'. For examples_list the set DIFFERS (e.g. 'headers' not 'header', plus 'colors', 'animations', 'specific_component'). Pass 'all' or call the action without category to see its valid keys.",

    # === Variables / categories (report_operations) ===
    "variable_name": "Name of the report variable (key used in SQL templates as :variable_name).",
    "variable_value": "Value(s) for the report variable. Single value or list of strings.",
    "category_name": "Name of a report category (globalCategory) used for cross-component filtering.",
    "category_selected": "Currently selected option within a report category.",
    "category_options": "List of available options for a report category.",

    # === Report options (report_operations) ===
    "page_size": "Paper size for export: 'A4', 'A3', 'Letter', etc.",
    "page_orientation": "Page orientation for export: 'portrait' or 'landscape'.",
    "timeout": "Timeout in seconds for long-running operations (e.g. export, large queries).",
    "cell_mode": "Grid cell sizing mode for the report layout (e.g. 'fixed', 'auto').",
    "allow_overlap_mode": "Allow components to overlap in the grid (true/false).",
    "free_pane_movement": "Allow free (non-snapping) component movement in the grid (true/false).",
    "no_gap_mode": "Remove gaps between grid cells (true/false).",
    "recalculated_cell_mode": "Recalculate cell sizes dynamically on resize (true/false).",
    "grouping_mode": "Enable grouping mode in the report grid (true/false).",

    # === Report group ===
    "menu": "Show this report group in the main navigation menu (true/false).",
    "is_extended": "Mark the group as extended (with additional metadata, true/false).",
    "options": "Optional dict of group-specific options (JSON object).",
    "image": "Optional URL or base64-encoded image used as the group icon.",

    # === Datasource ===
    "table_name": "Database table name (without schema prefix).",
    "schema": "Database schema name (default 'public' for PostgreSQL).",

    # === Dataset query ===
    "select": "List of fields to select, each as {'name':'field', 'aggr':'sum|avg|min|max|count'}.",
    "where": (
        "List of filter conditions, each as {'name':'field', 'op':..., 'value':...}. "
        "Working ops: =, !=, <, >, <=, >=, like, is, is not. "
        "'is'/'is not' with value omitted produce IS [NOT] NULL. "
        "'in' is NOT supported by the portal (HTTP 400) — use repeated '=' conditions with logicOr:1 instead."
    ),
    "group": "List of grouping fields, each as {'name':'field'}.",
    "order": "List of ordering entries, each as {'name':'field', 'dir':'asc|desc'}.",
    "variables": "Map of SQL variable name to list of values for :variable substitution (e.g. {'region':['Moscow']}).",
    "queries": "List of batch queries, each as {'id':'unique_id', 'params':{select/where/group/order/...}}.",

    # === SQL validation / dataset_create_from_sql ===
    "sql_query": "SQL query string (used for validation or dataset creation).",

    # === Batch operations ===
    "report_ids": "List of numeric report IDs for bulk operations.",
    "components": "List of component specs to add in bulk. Each dict follows component_crud(add) signature.",
    "layouts": "List of layout specs to update in bulk. Each dict: {'component_idx':int, 'x':int, 'y':int, 'w':int, 'h':int}.",
    "indices": "List of zero-based component indices to delete in bulk.",

    # === Data export ===
    "include_subtotals": "Include subtotal rows in the exported data (true/false).",
    "include_totals": "Include a grand total row in the exported data (true/false).",

    # === Report template ===
    "template": "Template name: 'kpi_dashboard', 'ranking', 'comparison', 'factor_analysis', 'geo_analytics', or 'simple'.",
}
