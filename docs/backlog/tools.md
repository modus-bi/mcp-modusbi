# Backlog: инструменты

Открытые пункты по инструментам и их действиям. Статусы как в [backlog компонентов](components.md). Все инструменты работают; ниже — ограничения и неоднозначности.

| Пункт | Статус |
|---|---|
| dataset_query: фильтр op='in' генерирует невалидный SQL ('field' in 'val' без скобок/списка) | поведение неизвестно |
| query_batch: пакетный маршрут возвращает пусто (заглушка GetRecordsetDataBatch); рабочая реализация в .old не мигрирована | нет настройки |
| dataset_operations: update query — silent no-op, нет post-write verify для изменений запроса | поведение неизвестно |
| reportgroup_operations: move в несуществующего родителя — HTTP 500 с FK-ошибкой вместо чистого 400 | поведение неизвестно |
| component_crud: get отдаёт 6-ключевой whitelist без raw config; ground-truth только через browser-fetch | не отображается |
| component_crud: update series_field/column_fields — silent ignore без предупреждения | нет настройки |
| component_crud: приоритет явной палитры над baseColor-default (bar/line/area) не подтверждён live | не проверено |
| component_axes: 17/25 actions не прогнаны live (page_*, pivot_link_remove, drill_delete_level, tabs_button_*, map_set_geokeys) | не проверено |
| component_filters: reset_mode/reset_type — enum schema vs impl расходятся, недопустимые значения молча null | поведение неизвестно |
| component_filters: filter_field_add берёт name, не alias из dataset | поведение неизвестно |
| component_filters: globalFilters не пересоздаются при изменении alias | поведение неизвестно |
| component_filters: set_global_filter — параметр alias игнорируется | поведение неизвестно |
| component_styling: field_sort_set порядок series/legend для multi-series — рецепт не подтверждён | не проверено |
| batch_operations: reports_export при недоступном рендер-сервисе — причина (env vs код) не разделена | не проверено |
| report_operations: export PDF/PNG/PPTX — требует live-проверки при поднятом рендер-сервисе | не проверено |
| datasource_operations: строгий READ-ONLY (create/update/delete блокируются, только web UI) — не проверено live | не проверено |
| relationship_operations: информативный ответ о неподдержке (HTTP 406) — не проверено | не проверено |
