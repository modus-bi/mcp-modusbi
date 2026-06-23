---
name: create-ranking
description: Создаёт рейтинговый дашборд с топ-N, treemap, стилизованным заголовком и таблицей с drill-down. Применять для ранжирования категорий (регионы, филиалы, товары) по числовым метрикам.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "2.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# Ranking Dashboard: Рейтинг и топ-N анализ

## Целевая структура

**7 компонентов (scaffold "ranking"):**
- 2x HsFilterControlPanel — раздельные фильтры (группа, подкатегория)
- HsBarAMchartsChart — Топ-N горизонтальный bar chart
- HsTreeMap — визуализация пропорций
- HsTableReactabularChart — детальная таблица рейтинга
- 2x HsBarAMchartsChart — сравнительные графики (stacked + horizontal)

**ВАЖНО:** Scaffold уже включает 2 фильтра сверху (idx 0,1). Нужно обновить поля и добавить filter_field_add на data-компоненты.

**Ключевые паттерны:**
- Множество графиков разного типа на одном экране
- TreeMap для визуализации пропорций
- Conditional formatting в таблице (цветные ячейки %)
- Сортировка по убыванию — критично для рейтинга!

---

## When to Use

- "Рейтинг" / "топ-N" / "сравнение категорий" / "ранжирование"
- Данные содержат: категории + числовые метрики для ранжирования
- Нужен визуально богатый дашборд с несколькими видами графиков

---

## Workflow

### Шаг 1: Создать датасет

```
mcp__modusbi__dataset_create_from_sql(
  sql_query="
    SELECT
      category AS group_name,
      subcategory,
      COUNT(*) AS total_count,
      SUM(value) AS total_value,
      ROUND(AVG(score::numeric), 2) AS avg_score
    FROM schema.table
    GROUP BY category, subcategory
    ORDER BY COUNT(*) DESC
  ",
  datasource_id=<ID>,
  name="ranking_data",
  caption="Датасет для рейтинга"
)
```

### Шаг 2: Scaffold

```
mcp__modusbi__report_template(
  action="scaffold",
  template="ranking",
  dataset_id=<DATASET_ID>,
  name="Рейтинг",
  group_id=<GROUP_ID>
)
# Создаст 7 компонентов:
# idx=0,1: Фильтры; idx=2: Bar(h); idx=3: TreeMap; idx=4: Table; idx=5: Stacked Bar; idx=6: Horizontal Bar
```

### Шаг 3: Обновить фильтры и компоненты

```
# === idx=0,1: Фильтры (созданы scaffold) — обновить поля ===
# Фильтр 1 → Группа
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=0,
  dataset_id=<DS>, value_field="group_name")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="group_name", alias="Группа", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")

# Фильтр 2 → Подкатегория
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=1,
  dataset_id=<DS>, value_field="subcategory")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=1,
  value_field="subcategory", alias="Подкатегория", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=1,
  value_field="value")

# Стилизация фильтров
for filter_idx in [0, 1]:
  mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=filter_idx,
    config_overrides={"outline.enabled": true, "outline.width": 1,
      "outline.color": "rgba(179,179,179,1)", "bgColor": "rgba(255,255,255,1)",
      "margin.l": 5, "margin.r": 5})

# === idx=2: Bar Chart Топ-N (горизонтальная) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=2,
  dataset_id=<DS>, category_field="group_name", value_field="total_count",
  aggregation="sum", title="Топ по количеству",
  config_overrides={"labels.visible": true, "legend.visible": false})

# === idx=3: TreeMap ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  dataset_id=<DS>, category_field="group_name", value_field="total_value",
  size_field="total_value", aggregation="sum",
  title="Структура по значению")

# === idx=4: Таблица рейтинга (full width) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=4,
  dataset_id=<DS>, value_field="group_name,subcategory,total_count,total_value,avg_score",
  value_fields_type="string", aggregation="none",
  title="Детальный рейтинг",
  field_titles={"group_name": "Группа", "subcategory": "Подкатегория", "total_count": "Кол-во", "total_value": "Значение", "avg_score": "Средний балл"})

# === idx=5: Stacked Bar (сравнение 1) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=5,
  dataset_id=<DS>, category_field="group_name", value_field="total_count",
  aggregation="sum", title="Сравнение по подкатегориям",
  config_overrides={"stacking": "normal", "legend.visible": true})

# === idx=6: Horizontal Bar (сравнение 2) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=6,
  dataset_id=<DS>, category_field="group_name", value_field="avg_score",
  aggregation="avg", title="Средний балл по группам",
  config_overrides={"labels.visible": true})
```

### Шаг 4: filter_field_add на КАЖДОМ data-компоненте

```
# ВАЖНО: filter_field_add на КАЖДОМ data-компоненте (bar, treemap, table, stacked bar)
for data_idx in [2, 3, 4, 5, 6]:
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="group_name", alias="Группа", field_type="string", dataset_id=<DS>)
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="subcategory", alias="Подкатегория", field_type="string", dataset_id=<DS>)
```

### Шаг 5: Conditional formatting на таблице

```
# Выделить высокие значения зелёным
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=4,
  config_overrides={"field": "avg_score", "operator": ">=", "value": 80,
    "background": "#c8e6c9", "color": "#1b5e20"})

# Выделить низкие значения красным
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=4,
  config_overrides={"field": "avg_score", "operator": "<", "value": 50,
    "background": "#ffcdd2", "color": "#b71c1c"})
```

### Шаг 6: Сортировка, CSS, Cleanup

```
# Сортировка bar chart по значению (убывание — для рейтинга критично!)
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=2,
  value_field="total_count", config_overrides={"order": "desc"}
)

# CSS стилизация отчёта (report-level)
mcp__modusbi__style_operations(action="update", report_id=<ID>,
  css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; } .panelTitle { color: #1a5276; font-weight: 700; } .hs-table-header { background: #1565c0 !important; color: white !important; }")

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
filter_field_add(report_id=X, component_idx=N, value_field="group_name", alias="Группа", field_type="string", dataset_id=Y)
```

**2. Столбцы таблицы (field_titles):**
```
component_crud(action="update", report_id=X, component_idx=N,
  field_titles={"group_name": "Группа", "total_count": "Кол-во", "total_value": "Значение", "avg_score": "Средний балл"})
```

**3. Легенды графиков (field_aliases на датасете):**
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"group_name": {"alias": "Группа"}, "total_count": {"alias": "Кол-во"}})
```

**4. Global filters:** имя глобального фильтра = alias из первого filter_field_add. Используй русский alias!

---

## Layout (ASCII) — 48-col grid (lg breakpoint)

```
+--------------------------------------------------+ 48 cols
| [Группа ▼]             | [Подкатегория ▼]        |  h=3, w=24 each
+------------------------+-------------------------+
|   Bar Chart Top-N      |       Treemap            |  h=7, w=24 each
+------------------------+-------------------------+
|          Table (full width, drill-down)            |  h=8, w=48
+------------------------+-------------------------+
|  Stacked Bar Chart     |    Horizontal Bar         |  h=6, w=24 each
+------------------------+-------------------------+
```
