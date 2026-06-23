---
name: create-simple-report
description: Создаёт простой отчёт с фильтрами, одним графиком и таблицей (3 компонента). Самый быстрый шаблон для быстрой визуализации данных.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "2.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# Simple Report: Быстрый отчёт

## Структура (3 компонента)

- HsFilterControlPanel — панель фильтров (1-3 поля)
- HsBarAMchartsChart — основной график (bar/line/pie — зависит от данных)
- HsTableReactabularChart — таблица с детальными данными

**Ключевые паттерны:**
- Минимальная компоновка — фильтр сверху, график посередине, таблица снизу
- Full-width layout (w=48 для всех, 48-col grid lg breakpoint)
- Подходит для быстрого прототипа или одно-метрикового отчёта
- Можно расширять: добавить KPI, второй график, conditional formatting

---

## When to Use

- "Простой отчёт" / "быстрый дашборд" / "один график + таблица"
- Данные имеют 1-2 категории + 1-2 метрики
- Не нужны вкладки, карта, сложная навигация
- Быстрый прототип для демонстрации

---

## Workflow

### Шаг 1: Исследовать данные

```
# Структура таблицы
mcp__postgres__query(sql="SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='...' AND table_name='...'")

# Пример данных
mcp__postgres__query(sql="SELECT * FROM schema.table LIMIT 10")

# Определить:
# - Категориальное поле (для оси X графика и фильтров)
# - Числовое поле (для значений графика)
# - Дополнительные поля (для таблицы)
```

### Шаг 2: Создать датасет

```
mcp__modusbi__dataset_create_from_sql(
  sql_query="
    SELECT
      category,
      COUNT(*) AS total_count,
      SUM(amount) AS total_amount,
      ROUND(AVG(amount::numeric), 2) AS avg_amount
    FROM schema.table
    GROUP BY category
    ORDER BY SUM(amount) DESC
  ",
  datasource_id=<ID>,
  name="simple_data",
  caption="Данные для отчёта"
)
```

### Шаг 3: Scaffold

```
mcp__modusbi__report_template(
  action="scaffold",
  template="simple",
  dataset_id=<DS>,
  name="Название отчёта",
  group_id=<GROUP_ID>
)
# Создаст: FilterPanel(idx=0) + BarChart(idx=1) + Table(idx=2)
```

### Шаг 4: Фильтры

#### Паттерн A: Раздельные фильтры (РЕКОМЕНДУЕТСЯ для 2+ полей)

```
# Удалить scaffold-фильтр (единый)
mcp__modusbi__component_crud(action="delete", report_id=<ID>, component_idx=0)

# Каждый фильтр — отдельный HsFilterControlPanel (горизонтально)
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsFilterControlPanel", title="Фильтры",
  value_field="category", dataset_id=<DS>, x=0, y=0, w=16, h=3)
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsFilterControlPanel", title="Фильтры",
  value_field="subcategory", dataset_id=<DS>, x=16, y=0, w=16, h=3)

# После add — индексы фильтров сдвинулись! Например: idx=0 (category), idx=1 (subcategory)
# idx=2: BarChart (бывший idx=1), idx=3: Table (бывший idx=2)
# Уточнить индексы через: report_operations(action="components_list", report_id=<ID>)

# ОБЯЗАТЕЛЬНО: filter_field_add на FilterControlPanel (правильный тип и alias)
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")  # убрать placeholder

mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=1,
  value_field="subcategory", alias="Подкатегория", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=1,
  value_field="value")  # убрать placeholder

# КРИТИЧНО: filter_field_add на КАЖДОМ data-компоненте (иначе фильтр не применяется к данным!)
# BarChart (idx=2) и Table (idx=3) — оба должны знать о фильтрах
for data_idx in [2, 3]:
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    value_field="subcategory", alias="Подкатегория", field_type="string", dataset_id=<DS>)

# Стилизация каждого (рамка + белый фон)
for idx in [0, 1]:
  mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=idx,
    config_overrides={"outline.enabled": true, "outline.width": 1,
      "outline.color": "rgba(179,179,179,1)", "bgColor": "rgba(255,255,255,1)",
      "margin.l": 5, "margin.r": 5})
```

#### Паттерн B: Единый фильтр (1 поле, самый простой)

```
# idx=0: FilterControlPanel — привязать к датасету
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=0,
  dataset_id=<DS>)

# Добавить поля фильтров
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="category", alias="Категория", field_type="string")

# Удалить placeholder
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")

# ВАЖНО: filter_field_add на КАЖДОМ data-компоненте (не только FilterControlPanel!)
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=1,
  value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=2,
  value_field="category", alias="Категория", field_type="string", dataset_id=<DS>)

# idx=1: BarChart — основной график
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=1,
  dataset_id=<DS>, category_field="category", value_field="total_amount",
  aggregation="sum", title="По категориям",
  config_overrides={"labels.visible": true, "legend.visible": false})

# idx=2: Table — детализация
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=2,
  dataset_id=<DS>,
  value_field="category,total_count,total_amount,avg_amount",
  value_fields_type="string", aggregation="none",
  title="Детальные данные",
  field_titles={"category": "Категория", "total_count": "Кол-во", "total_amount": "Сумма", "avg_amount": "Среднее"})
```

### Шаг 5 (опционально): Расширение

```
# Добавить KPI сверху
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsTotalsPanelV2",
  title="Всего", value_field="total_amount",
  dataset_id=<DS>, aggregation="sum", preset="kpi",
  x=0, y=0, w=16, h=3)

# Сменить тип графика на Line (для динамики)
# — просто используй category_field с временным полем (month, date)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=1,
  dataset_id=<DS>, category_field="month", value_field="total_amount",
  aggregation="sum", title="Динамика")

# Сменить на Pie
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsPieAMchartsChart",
  title="Структура", value_field="total_amount",
  dataset_id=<DS>, category_field="category", aggregation="sum",
  x=24, y=3, w=24, h=10)

# Conditional formatting на таблице
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=2,
  config_overrides={"field": "total_amount", "operator": ">=", "value": 1000,
    "background": "#c8e6c9", "color": "#1b5e20"})

# Сортировка графика по значению
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=1,
  value_field="total_amount", config_overrides={"order": "desc"}
)

# CSS стилизация отчёта (report-level)
# ОБЯЗАТЕЛЬНО включить z-index для фильтров — иначе dropdown скрывается за компонентами!
mcp__modusbi__style_operations(action="update", report_id=<ID>,
  css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; } .panelTitle { color: #1a5276; font-weight: 700; }")

# Очистка orphan global_filters (если фильтры переделывали)
mcp__modusbi__report_operations(action="global_filters_list", report_id=<ID>)
mcp__modusbi__report_operations(action="global_filter_delete", report_id=<ID>, variable_name="old_filter")
```

---

## Layout (ASCII) — 48-col grid (lg breakpoint)

```
+--------------------------------------------------+
| [Категория ▼]    [Filter 2 ▼]                    |  h=3, w=16 each
+--------------------------------------------------+
|            Main Chart (bar/line/pie)              |  h=10, w=48
+--------------------------------------------------+
|            Table (detail data)                    |  h=14, w=48
+--------------------------------------------------+
```

---

## Русские названия (ОБЯЗАТЕЛЬНО)

Все пользовательские подписи ДОЛЖНЫ быть на русском: фильтры, столбцы таблиц, легенды графиков.

**1. Фильтры (filter_field_add):** ВСЕГДА передавать `alias="Русское название"`:
```
# На FilterControlPanel и на КАЖДОМ data-компоненте — одинаковый alias!
filter_field_add(report_id=X, component_idx=N, value_field="category", alias="Категория", field_type="string", dataset_id=Y)
```

**КРИТИЧНО:** Если FilterControlPanel создан с `value_field="category"` через `add`, бэкенд **автоматически** добавляет поле с alias=техническое имя ("category"). Последующий `filter_field_add` вернёт "Field already exists" и **не изменит alias**!
**Обязательный паттерн для FilterControlPanel:**
```
# 1. Сначала УДАЛИТЬ автоматически добавленное поле
filter_field_remove(report_id=X, component_idx=N, value_field="category")
# 2. Затем ДОБАВИТЬ с русским alias
filter_field_add(report_id=X, component_idx=N, value_field="category", alias="Категория", field_type="string", dataset_id=Y)
```

**2. Столбцы таблицы (field_titles):**
```
component_crud(action="update", report_id=X, component_idx=N,
  field_titles={"category": "Категория", "total_count": "Кол-во", "total_amount": "Сумма"})
```

**3. Легенды графиков (field_aliases на датасете):**
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"category": {"alias": "Категория"}, "total_amount": {"alias": "Сумма"}})
```

**4. Global filters:** имя глобального фильтра = alias из первого filter_field_add. Используй русский alias!

---

## Checklist

- [ ] Датасет создан с правильными полями
- [ ] Scaffold выполнен (template="simple")
- [ ] FilterControlPanel обновлён с dataset_id
- [ ] Поля фильтров: СНАЧАЛА filter_field_remove (удалить автоматически созданное), ПОТОМ filter_field_add с alias=русский, field_type="string"
- [ ] **filter_field_add на BarChart (data-компонент!)** — фильтр применяется к данным
- [ ] **filter_field_add на Table (data-компонент!)** — фильтр применяется к данным
- [ ] BarChart имеет category_field + value_field + aggregation="sum"
- [ ] Table имеет value_fields_type="string", aggregation="none"
- [ ] field_titles заданы для таблицы (русские названия)
