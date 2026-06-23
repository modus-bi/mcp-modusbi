---
name: create-factor-analysis
description: Создаёт дашборд факторного анализа с waterfall-графиком, 3 KPI и таблицей с conditional formatting. Референс — типовой дашборд факторного анализа (декомпозиция изменения показателя по факторам), адаптированный под текущий scaffold.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "2.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# Factor Analysis Dashboard: Факторный анализ

## Референс: типовой дашборд факторного анализа

Прообраз — производственный дашборд факторного анализа: декомпозиция изменения
итогового показателя (между двумя периодами) на вклад отдельных факторов
(категорий) с waterfall-графиком и детальной таблицей. Ниже — обобщённый паттерн,
адаптированный под текущий scaffold; конкретные поля/метрики подставляются из
вашего датасета.

**Целевая структура (7 компонентов, scaffold "factor_analysis"):**
- 2x HsFilterControlPanel — раздельные фильтры (регион, тяжесть/категория)
- 3x HsTotalsPanelV2 — KPI (итого / изменение / сумма факторов)
- HsBarAMchartsChart — waterfall-подобный столбчатый график (факторы влияния)
- HsTableReactabularChart — детальная факторная таблица с conditional formatting

**ВАЖНО:** Scaffold уже включает 2 фильтра сверху. Нужно обновить поля и добавить filter_field_add на data-компоненты.

**Ключевые паттерны:**
- Waterfall chart: Сравнительный период → +Трафик → +Конверсия → +Ср.чек → -Маржинальность → = Период акции
- Таблица с conditional formatting (зелёный для положительных дельт, красный для отрицательных)
- Итоговая строка выделена цветом
- 3 KPI с индикаторами (стрелки вверх/вниз + цвет)

---

## When to Use

- "Факторный анализ" / "водопад" / "waterfall" / "декомпозиция"
- Нужно показать: как факторы влияют на итоговый показатель
- Данные: итог = фактор1 + фактор2 + ... + факторN

---

## Workflow

### Шаг 1: Датасет с факторами

```
# Факторный анализ: каждая строка = фактор с его вкладом
mcp__modusbi__dataset_create_from_sql(
  sql_query="
    SELECT
      category AS factor_name,
      SUM(current_value) AS current_total,
      SUM(prev_value) AS prev_total,
      SUM(current_value) - SUM(prev_value) AS delta_abs,
      ROUND((SUM(current_value)::numeric / NULLIF(SUM(prev_value), 0) - 1) * 100, 1) AS delta_pct
    FROM schema.factor_table
    GROUP BY category
    ORDER BY ABS(SUM(current_value) - SUM(prev_value)) DESC
  ",
  datasource_id=<ID>,
  name="factor_analysis"
)
```

### Шаг 2: Scaffold

```
mcp__modusbi__report_template(
  action="scaffold",
  template="factor_analysis",
  dataset_id=<DS>,
  name="Факторный анализ",
  group_id=<GROUP_ID>
)
# Создаст 7 компонентов:
# idx=0,1: Фильтры; idx=2,3,4: KPI; idx=5: Bar(waterfall); idx=6: Table
```

### Шаг 3: Обновить фильтры и компоненты

```
# === idx=0,1: Фильтры (созданы scaffold) — обновить поля ===
# Фильтр 1 → Регион (или другое измерение данных)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=0,
  dataset_id=<DS>, value_field="region")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="region", alias="Регион", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")

# Фильтр 2 → Тяжесть/Категория
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=1,
  dataset_id=<DS>, value_field="severity")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=1,
  value_field="severity", alias="Тяжесть", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=1,
  value_field="value")

# Стилизация фильтров
for filter_idx in [0, 1]:
  mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=filter_idx,
    config_overrides={"outline.enabled": true, "outline.width": 1,
      "outline.color": "rgba(179,179,179,1)", "bgColor": "rgba(255,255,255,1)",
      "margin.l": 5, "margin.r": 5})

# === idx=2..4: KPI (сдвиг +2 из-за фильтров) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=2,
  dataset_id=<DS>, value_field="current_total", aggregation="sum",
  title="Итого (текущий)", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  dataset_id=<DS>, value_field="delta_abs", aggregation="sum",
  title="Изменение", preset="kpi")
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=4,
  dataset_id=<DS>, value_field="delta_pct", aggregation="avg",
  title="Сумма факторов", preset="kpi")

# === idx=5: Bar Chart (waterfall-style) ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=5,
  dataset_id=<DS>, category_field="factor_name", value_field="delta_abs",
  aggregation="sum", title="Факторы влияния",
  config_overrides={"labels.visible": true, "legend.visible": false})

# === idx=6: Table с факторами ===
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=6,
  dataset_id=<DS>,
  value_field="factor_name,current_total,prev_total,delta_abs,delta_pct",
  value_fields_type="string", aggregation="none",
  title="Детали по факторам",
  field_titles={"factor_name": "Фактор", "current_total": "Текущий", "prev_total": "Прошлый", "delta_abs": "Дельта", "delta_pct": "Дельта %"})
```

### Шаг 4: filter_field_add на data-компоненты + Conditional formatting

```
# filter_field_add на КАЖДОМ data-компоненте (KPI, bar, table)
# idx=2,3,4: KPI; idx=5: bar; idx=6: table
for data_idx in [2, 3, 4, 5, 6]:
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="region", alias="Регион", field_type="string", dataset_id=<DS>)
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="severity", alias="Тяжесть", field_type="string", dataset_id=<DS>)

# Conditional formatting на таблице (idx=6): зелёный для +, красный для -
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=6,
  config_overrides={"field": "delta_abs", "operator": ">", "value": 0,
    "background": "#c8e6c9", "color": "#1b5e20"})
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=6,
  config_overrides={"field": "delta_abs", "operator": "<", "value": 0,
    "background": "#ffcdd2", "color": "#b71c1c"})
```

> ✅ **conditional_rule_add: строковое value работает**
> Операторы `=` и `~` (contains) принимают строку — `factor='critical'`
> работает без numeric rank колонки:
> ```python
> component_styling(action="conditional_rule_add", ...,
>   config_overrides={"field":"factor","operator":"=","value":"critical",
>     "background":"#dc3545","color":"#ffffff"})
> ```
> Поддерживаемые: `>, >=, <, <=, =, ~` (`contains`). НЕ работают `!=`,
> regex, starts_with, in. Numeric rank всё ещё нужен для range-запросов
> (`factor_rank >= 3`).

### Шаг 5: Сортировка, CSS, Cleanup

```
# Сортировка waterfall bar по абсолютной дельте
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=5,
  value_field="delta_abs", config_overrides={"order": "desc"}
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
filter_field_add(report_id=X, component_idx=N, value_field="factor_name", alias="Фактор", field_type="string", dataset_id=Y)
```

**2. Столбцы таблицы (field_titles):**
```
component_crud(action="update", report_id=X, component_idx=N,
  field_titles={"factor_name": "Фактор", "current_total": "Текущий", "delta_abs": "Дельта"})
```

**3. Легенды графиков (field_aliases на датасете):**
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"factor_name": {"alias": "Фактор"}, "delta_abs": {"alias": "Дельта"}})
```

**4. Global filters:** имя глобального фильтра = alias из первого filter_field_add. Используй русский alias!

---

## Layout (ASCII) — 48-col grid (lg breakpoint)

```
+--------------------------------------------------+ 48 cols
| [Регион ▼]              | [Тяжесть ▼]            |  h=3, w=24 each
+-------------+-------------+----------------------+
|  KPI Total  |   KPI Δ     |   KPI Factor Sum     |  h=3, w=16 each
+-------------+-------------+----------------------+
|          Waterfall / Bar Chart (factors)          |  h=8
+--------------------------------------------------+
|          Table (factor details + CF)              |  h=8
+--------------------------------------------------+
```
