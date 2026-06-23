---
name: create-comparison
description: Создаёт дашборд сравнения двух периодов с KPI-дельтами, stacked bar и структурой (pie + детальная таблица). Применять для план-факт, YoY/MoM, «этот период vs прошлый».
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "2.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# Comparison Dashboard: Сравнение периодов

## Целевая структура

**10 компонентов, scaffold "comparison":**
- 2x HsFilterControlPanel — раздельные фильтры (категория, подкатегория)
- 4x HsTotalsPanelV2 — KPI 2x2: Текущий / Прошлый / Дельта % / Дельта абс.
- HsBarAMchartsChart — stacked bar (текущий vs прошлый по категориям)
- HsPieAMchartsChart — структура текущего периода
- HsTextBlock — пояснение/выводы
- HsTableReactabularChart — детализация с conditional formatting

**ВАЖНО:** Scaffold уже включает 2 фильтра сверху (idx 0,1). Нужно обновить поля и добавить filter_field_add на data-компоненты.

**Ключевые паттерны:**
- Два периода для сравнения (даты или переменные)
- 4 KPI в 2x2 layout (w=24 each): текущий / прошлый / дельта % / дельта абс.
- Grouped/stacked bar для visual comparison
- Pie для структуры
- TextBlock для пояснений

---

## When to Use

- "Сравни периоды" / "план-факт" / "YoY/MoM" / "дельта"
- Данные имеют 2 временных среза (этот месяц vs прошлый)
- Нужны: дельты абсолютные и процентные

---

## Workflow

### Шаг 1: Датасет с двумя периодами

```
mcp__modusbi__dataset_create_from_sql(
  sql_query="
    SELECT
      category,
      SUM(CASE WHEN date BETWEEN '2024-01-01' AND '2024-03-31' THEN amount ELSE 0 END) AS current_period,
      SUM(CASE WHEN date BETWEEN '2023-01-01' AND '2023-03-31' THEN amount ELSE 0 END) AS prev_period,
      SUM(CASE WHEN date BETWEEN '2024-01-01' AND '2024-03-31' THEN amount ELSE 0 END) -
      SUM(CASE WHEN date BETWEEN '2023-01-01' AND '2023-03-31' THEN amount ELSE 0 END) AS delta_abs,
      ROUND(
        (SUM(CASE WHEN date BETWEEN '2024-01-01' AND '2024-03-31' THEN amount ELSE 0 END)::numeric /
         NULLIF(SUM(CASE WHEN date BETWEEN '2023-01-01' AND '2023-03-31' THEN amount ELSE 0 END), 0) - 1) * 100
      , 1) AS delta_pct
    FROM schema.table
    GROUP BY category
    ORDER BY SUM(CASE WHEN date BETWEEN '2024-01-01' AND '2024-03-31' THEN amount ELSE 0 END) DESC
  ",
  datasource_id=<ID>,
  name="comparison_data"
)
```

### Шаг 2: Scaffold

```
mcp__modusbi__report_template(
  action="scaffold",
  template="comparison",
  dataset_id=<DS>,
  name="Сравнение периодов",
  group_id=<GROUP_ID>
)
# Создаст 10 компонентов:
# idx=0,1: Фильтры; idx=2,3,4,5: KPI 2x2; idx=6: StackedBar; idx=7: Pie; idx=8: TextBlock; idx=9: Table
```

### Шаг 3: Обновить фильтры и компоненты

```
# === idx=0,1: Фильтры (созданы scaffold) — обновить поля ===
# Фильтр 1 → Категория
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=0,
  dataset_id=<DS>, value_field="category")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")

# Фильтр 2 → Подкатегория (или другое измерение)
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

# === idx=2..5: KPI 2x2 (сдвиг +2 из-за фильтров) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=2,
  dataset_id=<DS>, value_field="current_period", aggregation="sum",
  title="Текущий период", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  dataset_id=<DS>, value_field="prev_period", aggregation="sum",
  title="Прошлый период", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=4,
  dataset_id=<DS>, value_field="delta_pct", aggregation="avg",
  title="Дельта (%)", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=5,
  dataset_id=<DS>, value_field="delta_abs", aggregation="sum",
  title="Дельта (абс.)", preset="kpi")

# === idx=6: Stacked Bar (текущий vs прошлый) ===
# СТЕК = stacking="normal" (валидные значения: none/normal/percent; "stacked" НЕ принимается)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=6,
  dataset_id=<DS>, category_field="category", value_field="current_period,prev_period",
  aggregation="sum", title="Сравнение по категориям",
  stacking="normal", legend_visible=true, labels_visible=true)

# === idx=7: Pie (структура текущего периода) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=7,
  dataset_id=<DS>, category_field="category", value_field="current_period",
  aggregation="sum", title="Структура текущего периода")

# === idx=8: TextBlock (пояснение) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=8,
  text_content="<h3>Комментарий</h3><p>Добавьте пояснение к сравнению периодов</p>")

# === idx=9: Table ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=9,
  dataset_id=<DS>, value_field="category,current_period,prev_period,delta_abs,delta_pct",
  value_fields_type="string", aggregation="none",
  title="Детализация",
  field_titles={"category": "Категория", "current_period": "Текущий", "prev_period": "Прошлый", "delta_abs": "Дельта", "delta_pct": "Дельта %"})
```

### Шаг 4: filter_field_add на data-компоненты + Conditional formatting

```
# filter_field_add на КАЖДОМ data-компоненте (KPI, bar, pie, table)
# idx=2,3,4,5: KPI; idx=6: bar; idx=7: pie; idx=9: table
for data_idx in [2, 3, 4, 5, 6, 7, 9]:
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="subcategory", alias="Подкатегория", field_type="string", dataset_id=<DS>)

# Conditional formatting: красный для отрицательных дельт
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=9,
  config_overrides={"field": "delta_pct", "operator": "<", "value": 0,
    "background": "#ffcdd2", "color": "#b71c1c"})
# Зелёный для положительных
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=9,
  config_overrides={"field": "delta_pct", "operator": ">", "value": 0,
    "background": "#c8e6c9", "color": "#1b5e20"})
```

> ✅ **conditional_rule_add: строковое value работает**
> Операторы `=` и `~` (contains) принимают строку напрямую — без numeric
> rank workaround:
> ```python
> component_styling(action="conditional_rule_add", ...,
>   config_overrides={"field":"status","operator":"=","value":"critical",
>     "background":"#ff0000"})
> ```
> Поддерживаемые операторы (проверено в коде фронта): `>, >=, <, <=, =, ~`
> (плюс `gt/gte/lt/lte/eq/contains`). НЕ работают: `!=`, regex,
> starts_with, in — MCP вернёт error с подсказкой workaround'а.
> Numeric rank полезен только для range-запросов (`priority >= 3`).

### Шаг 5: Сортировка, CSS, Cleanup

```
# Сортировка bar chart по дельте (убывание)
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=6,
  value_field="current_period", config_overrides={"order": "desc"}
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
filter_field_add(report_id=X, component_idx=N, value_field="category", alias="Категория", field_type="string", dataset_id=Y)
```

**2. Столбцы таблицы (field_titles):**
```
component_crud(action="update", report_id=X, component_idx=N,
  field_titles={"category": "Категория", "current_period": "Текущий период", "delta_pct": "Дельта %"})
```

**3. Легенды графиков (field_aliases на датасете):**
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"current_period": {"alias": "Текущий период"}, "prev_period": {"alias": "Прошлый период"}})
```

**4. Global filters:** имя глобального фильтра = alias из первого filter_field_add. Используй русский alias!

---

## Layout (ASCII) — 48-col grid (lg breakpoint)

```
+--------------------------------------------------+ 48 cols
| [Категория ▼]          | [Подкатегория ▼]         |  h=3, w=24 each
+------------------------+-------------------------+
|   KPI curr (w=24)      |   KPI prev (w=24)       |  h=3
+------------------------+-------------------------+
|   KPI Δ% (w=24)        |   KPI Δ abs (w=24)      |  h=3
+------------------------+-------------------------+
|  Stacked Bar (current)  |     Pie Chart           |  h=7
+------------------------+-------------------------+
|       Text Block (description)                    |  h=3
+--------------------------------------------------+
|          Table (category detail + CF)             |  h=8
+--------------------------------------------------+
```
