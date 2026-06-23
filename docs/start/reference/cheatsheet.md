<!-- GENERATED from derived: SLUG_SCHEMA + component_crud (_creatable) + server.py; edit there, then run scripts/gen_public_docs.py -->
<!-- регенерируется scripts/gen_public_docs.py -->

# Шпаргалка

Слагов: **365** · создаваемых типов: **28** · инструментов: **19** · промптов: **10** · версия фронта: **3.15.3**.

## Частые задачи → слаги

| Задача | Слаги |
|---|---|
| Заголовок / подписи | `showtitle` `subtitle` `truncateTitle` |
| Легенда | `legend.visible` `legend.position` `legend.fontSize` |
| Оси | `axes.valueTitle` `axes.categoryTitle` `axes.valueGrid` `axes.categoryLabels` |
| Фон и рамка | `bgColor` `outline.enabled` `outline.color` `outline.width` |
| Отступы | `margin.l` `margin.r` `margin.t` `margin.b` |
| Цвета / палитра | `data.baseColor` `data.colorStep` |
| Подписи значений | `labels.visible` |

## Частые действия инструментов

- **`instance_operations`** — `list`, `get_active`
- **`report_operations`** — `help`, `list`, `get`, `create`, `update`, `delete`, `summary`, `components_list` …
- **`dataset_operations`** — `help`, `list`, `get`, `fields_list`, `create`, `update`, `delete`
- **`component_crud`** — `help`, `types_list`, `get`, `add`, `add_text_block`, `add_chart_with_conclusion`, `update`, `delete` …
- **`component_filters`** — `help`, `set_global_filter`, `reset_global_filters`, `filter_fields_list`, `filter_field_add`, `filter_field_remove`, `filter_set_cascade`, `filters_grid_layout`
- **`component_axes`** — `help`, `calc_fields_list`, `calc_field_add`, `calc_field_update`, `calc_field_remove`, `page_list`, `page_add`, `page_remove` …
- **`component_styling`** — `help`, `conditional_rule_add`, `conditional_rule_list`, `conditional_rule_delete`, `field_sort_set`, `geodata_list`, `map_set_geokeys`, `map_get_geokeys`
- **`datasource_operations`** — `list`, `get`, `tables_list`, `table_fields`, `check_connection`, `create`, `update`, `delete`
- **`style_operations`** — `classes_list`, `examples_list`, `get`, `update`, `validate`, `apply_theme`
- **`reportgroup_operations`** — `list`, `get`, `create`, `update`, `delete`, `move`
- **`data_export_operations`** — `component_csv`, `component_xlsx`, `info`
- **`batch_operations`** — `components_add`, `components_delete`, `layouts_update`, `styles_apply`, `reports_export`

## Типы компонентов (создаются через MCP)

`Area`, `Audioplayer`, `Bar`, `Bubble`, `Comparison`, `FilterControl`, `HierarchicalFilter`, `Iframe`, `Image`, `Line`, `MapLeaflet`, `PageContainer`, `ParallelCoords`, `Pie`, `Pivot`, `Radar`, `Speedometer`, `Stock`, `Subheader`, `Sunburst`, `SwitchControl`, `TableReactabular`, `Tabs`, `TextBlock`, `Tilemap`, `TotalsPanel`, `TreeGraph`, `TreeMap`.

Полный список технических типов — `component_crud(action="types_list")` (28 создаваемых).

## Базовые шаги создания отчёта

1. `report_operations(action="create", ...)` — создать отчёт.
2. `dataset_operations(action="create", ...)` — подготовить семантический слой.
3. `component_crud(action="add", ...)` — добавить компонент.
4. `component_filters(action="filter_field_add", ...)` — связать фильтры.
5. `style_operations(action="update", ...)` — применить CSS отчёта.

Быстрый путь — готовые шаблоны: `report_template(action="list")` → `report_template(action="scaffold", template=...)`.
