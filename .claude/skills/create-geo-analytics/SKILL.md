---
name: create-geo-analytics
description: Создаёт дашборд геоаналитики с картой, KPI и таблицей с conditional formatting. Референс — типовой геодашборд (раздельные фильтры, KPI, хороплет/bubble-карта, bar по территориям, стилизованная таблица).
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "2.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# Geo Analytics Dashboard: Геоаналитика

## Референс: типовой геодашборд «Показатели по территориям»

**Целевая структура (9 компонентов, scaffold "geo_analytics"):**
- 3x HsFilterControlPanel — раздельные фильтры (регион, категория, тип)
- 3x HsTotalsPanelV2 — KPI (всего / средний балл / итого значение)
- HsMapLeafletChart — карта территорий (bubble или choropleth)
- HsBarAMchartsChart — горизонтальный bar по территориям
- HsTableReactabularChart — детализация с conditional formatting

**ВАЖНО:** Scaffold уже включает 3 фильтра сверху (idx 0,1,2). Нужно обновить поля и добавить filter_field_add на data-компоненты.

**Ключевые паттерны:**
- Карта с геопривязкой: bubble (круги на lat/lng) или choropleth (GeoJSON полигоны)
- Bar chart рядом с картой для территориального сравнения
- Conditional formatting с процентными индикаторами
- CSS-стилизация: зелёный header таблицы

---

## When to Use

- "Геоаналитика" / "карта" / "по территориям" / "по регионам"
- Данные имеют: географическое измерение (region, lat/lng) + метрики
- Нужна карта + KPI + детализация по территориям

---

## Workflow

### Шаг 1: Датасет с географией

```
mcp__modusbi__dataset_create_from_sql(
  sql_query="
    SELECT
      region,
      category,
      latitude AS lat,
      longitude AS lng,
      COUNT(*) AS total_count,
      SUM(value) AS total_value,
      ROUND(AVG(score::numeric), 1) AS avg_score
    FROM schema.table
    WHERE region IS NOT NULL
    GROUP BY region, category, latitude, longitude
    ORDER BY COUNT(*) DESC
  ",
  datasource_id=<ID>,
  name="geo_data",
  caption="Геоаналитика по территориям"
)
```

### Шаг 2: Scaffold

```
mcp__modusbi__report_template(
  action="scaffold",
  template="geo_analytics",
  dataset_id=<DS>,
  name="Геоаналитика",
  group_id=<GROUP_ID>
)
# Создаст 9 компонентов:
# idx=0,1,2: Фильтры; idx=3,4,5: KPI; idx=6: Map; idx=7: Bar; idx=8: Table
```

### Шаг 3: Обновить фильтры и геопривязку

```
# === idx=0,1,2: Фильтры (созданы scaffold) — обновить поля ===
# Фильтр 1 → Регион
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=0,
  dataset_id=<DS>, value_field="region")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="region", alias="Регион", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")

# Фильтр 2 → Категория
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=1,
  dataset_id=<DS>, value_field="category")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=1,
  value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=1,
  value_field="value")

# Фильтр 3 → Тип (или другое измерение)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=2,
  dataset_id=<DS>, value_field="type")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=2,
  value_field="type", alias="Тип", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=2,
  value_field="value")

# Стилизация фильтров
for filter_idx in [0, 1, 2]:
  mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=filter_idx,
    config_overrides={"outline.enabled": true, "outline.width": 1,
      "outline.color": "rgba(179,179,179,1)", "bgColor": "rgba(255,255,255,1)",
      "margin.l": 5, "margin.r": 5})
```

### Шаг 4: Геопривязка карты + Обновить компоненты

```
# === idx=6: Map — ПОРЯДОК ВАЖЕН ===
# 1) Привязать категорию к карте: category_field = ОДНО поле территории (region).
#    ⚠️ НЕ "region,lat,lng" через запятую! Это попадёт в SQL как одна колонка
#    `group by "region,lat,lng"` → ошибка "column does not exist". Координаты в category НЕ кладём.
#    lat/lng подставит map_set_geokeys (шаг 2) — фронт сам добавит MAX(lat)/MAX(lng) в запрос.
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=6,
  dataset_id=<DS>, category_field="region", value_field="total_count",
  aggregation="sum", title="Карта территорий")
# Центрирование/зум автоматические (autoCenter + Leaflet-bounds по точкам);
# слаги map.center.*/map.initialZoom фронт не читает (deprecated).

# 2) Затем геопривязка. Режим A: Bubble (круги на координатах) — РЕКОМЕНДУЕТСЯ, надёжно рендерится
#    ⚠️ ТРЕБОВАНИЕ: в датасете ДОЛЖНЫ быть числовые поля координат (lat/lng). Проверь через
#    dataset_query ПЕРЕД привязкой — если координат нет, bubble НЕ нарисует круги (пустая карта).
#    Эталон рабочего bubble — прод-отчёт 667 (DS с lat/lng).
mcp__modusbi__component_styling(action="map_set_geokeys", report_id=<ID>, component_idx=6,
  config_overrides={"latfield": "lat", "lonfield": "lng"})
# Режим B: Choropleth (раскраска полигонов GeoJSON) — только если НЕТ координат, но есть совпадающий GeoJSON:
#   - geo_type ОБЯЗАН быть ЗАДеплоенным справочником из geodata_list (action geodata_list).
#     Проверь наличие файла! Напр. spb_districts.geojson.json на your-portal = 404 (не задеплоен) → виснет.
#     Рабочий пример — ao.geojson.json (округа, эталон 667).
#   - Значения категории (region) ДОЛЖНЫ совпадать со свойством geofield внутри GeoJSON (напр. ABBREV).
#   - map_set_geokeys сам резолвит geodataId+datafield (без них фронт виснет на спиннере); вернёт
#     warning, если geo_type не найден в geodata — тогда НЕ choropleth, переключись на bubble.
# mcp__modusbi__component_styling(action="map_set_geokeys", report_id=<ID>, component_idx=6,
#   config_overrides={"geo_type": "ao.geojson.json", "geofield": "ABBREV"})
# Режим C: МУЛЬТИСЛОЙ (опц.) — цветные районы + ОТДЕЛЬНЫЕ точки событий + кластеры + подсказка при наведении.
#   Когда нужны и заливка районов по значению, И точки на реальных координатах в ОДНОЙ карте.
#   Требования к датасету: УНИКАЛЬНЫЙ id на строку (точка=строка, напр. ROW_NUMBER() AS incident_id) +
#   lat/lon + (опц.) текстовое поле деталей для подсказки (конкат тип·тяжесть·… AS details).
#   ⚠️ aggregation=none для сырых точек даёт HTTP 400 — нужен именно id-на-строку (GROUP BY id + MAX(lat/lon)).
#   Привязка карты: category_field=region (для районов), value_field=<метрика района>, aggregation=sum.
# mcp__modusbi__component_styling(action="map_set_geokeys", report_id=<ID>, component_idx=6,
#   config_overrides={"geo_type":"spb_districts.geojson.json","geofield":"NAME",
#     "point_id_field":"incident_id","latfield":"lat","lonfield":"lon","tooltip_field":"details"})
# Затем включить кластеры/подсказки:
# mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=6,
#   config_overrides={"map.markers.clustering":true,"map.markers.showValues":true,"map.markers.showTooltip":true})
#   Механизм: фронт рисует два «листа» (isSheetOne) — полигоны (sheet0) + точки (sheet1); подсказка точки
#   = поле с addToTooltip (tooltip_field пишет его сам). НЕ требует center-слагов: полигон-слой центрирует.

# === idx=3,4,5: KPI ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  dataset_id=<DS>, value_field="total_count", aggregation="sum",
  title="Всего записей", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=4,
  dataset_id=<DS>, value_field="avg_score", aggregation="avg",
  title="Средний балл", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=5,
  dataset_id=<DS>, value_field="total_value", aggregation="sum",
  title="Итого", preset="kpi")

# === idx=7: Bar Chart (горизонтальный, по территориям) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=7,
  dataset_id=<DS>, category_field="region", value_field="total_count",
  aggregation="sum", title="По территориям",
  config_overrides={"labels.visible": true, "legend.visible": false})

# === idx=8: Table ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=8,
  dataset_id=<DS>,
  value_field="region,category,total_count,total_value,avg_score",
  value_fields_type="string", aggregation="none",
  title="По территориям",
  field_titles={"region": "Регион", "category": "Категория", "total_count": "Кол-во", "total_value": "Значение", "avg_score": "Балл"})
```

### Шаг 5: filter_field_add + Conditional formatting + CSS

```
# filter_field_add на КАЖДОМ data-компоненте
# idx=3,4,5: KPI; idx=6: map; idx=7: bar; idx=8: table
for data_idx in [3, 4, 5, 6, 7, 8]:
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="region", alias="Регион", field_type="string", dataset_id=<DS>)
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="type", alias="Тип", field_type="string", dataset_id=<DS>)

# Conditional formatting на таблице (idx=8)
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=8,
  config_overrides={"field": "avg_score", "operator": ">=", "value": 90,
    "background": "#c8e6c9", "color": "#1b5e20"})
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=8,
  config_overrides={"field": "avg_score", "operator": "<", "value": 50,
    "background": "#ffcdd2", "color": "#b71c1c"})

# Сортировка bar chart по значению
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=7,
  value_field="total_count", config_overrides={"order": "desc"})

# CSS стилизация отчёта (report-level)
mcp__modusbi__style_operations(action="update", report_id=<ID>,
  css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; } .hs-table-header { background: #2e7d32 !important; color: white !important; } .panelTitle { font-weight: 700; color: #1a5276; }")

# Очистка orphan global_filters
mcp__modusbi__report_operations(action="global_filters_list", report_id=<ID>)
mcp__modusbi__report_operations(action="global_filter_delete", report_id=<ID>, variable_name="old_filter")
```

---

## Русские названия (ОБЯЗАТЕЛЬНО)

Все пользовательские подписи ДОЛЖНЫ быть на русском: фильтры, столбцы таблиц, легенды графиков.

**1. Фильтры (filter_field_add):** ВСЕГДА передавать `alias="Русское название"`:
```
# На FilterControlPanel и на КАЖДОМ data-компоненте — одинаковый alias!
filter_field_add(report_id=X, component_idx=N, value_field="region", alias="Регион", field_type="string", dataset_id=Y)
```

**2. Столбцы таблицы (field_titles):**
```
component_crud(action="update", report_id=X, component_idx=N,
  field_titles={"region": "Регион", "category": "Категория", "total_count": "Кол-во", "avg_score": "Балл"})
```

**3. Легенды графиков (field_aliases на датасете):**
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"region": {"alias": "Регион"}, "total_count": {"alias": "Кол-во"}})
```

**4. Global filters:** имя глобального фильтра = alias из первого filter_field_add. Используй русский alias!

---

## Layout (ASCII) — 48-col grid (lg breakpoint)

```
+--------------------------------------------------+ 48 cols
| [Регион ▼]  | [Категория ▼]  | [Тип ▼]          |  h=3, w=16 each
+-------------+-------------+----------------------+
|   KPI #1    |   KPI #2    |       KPI #3         |  h=3, w=16 each
+-------------+-------------+----------------------+
|  Map (bubble/choropleth)  | Bar Chart (h)         |  h=10, w=24 each
+------------------------+-------------------------+
|           Table (by territory + CF)               |  h=8, w=48
+--------------------------------------------------+
```
