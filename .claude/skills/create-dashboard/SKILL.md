---
name: create-dashboard
description: Создаёт полноценный BI дашборд через MCP API ModusBI. Используйте когда пользователь просит "создать дашборд", "построить отчёт", "визуализировать данные". Исследует источник данных, создаёт датасеты, выбирает шаблон, делает scaffold + настройку компонентов + фильтры + стилизацию.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "2.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi, playwright
---

# Create Dashboard v2: Полный BI дашборд через MCP API

## Overview

Создаёт production-quality дашборд через ModusBI MCP Server (19 tools).

**Ключевые MCP-инструменты:**
- `report_template(action="scaffold")` — создание скелета из 6 шаблонов
- `component_crud` — CRUD, layout, slugs, presets
- `component_filters` — filter axis + global filters + cascade
- `component_axes` — calc fields, drill-down, pivot links, tabs buttons, conditional rules
- `component_styling` — conditional formatting, field sort, map geo-binding
- `dataset_create_from_sql` — SQL → датасет; aliases задаются следом через `dataset_operations(action="update")`
- `batch_operations` — массовое добавление компонентов

> Не уверены в параметрах? Вызовите `component_crud(action="help")` (или help для любого tool).

**6 шаблонов** (report_template tool):
| Шаблон | Описание | Компоненты | Прообраз |
|--------|----------|------------|----------|
| kpi_dashboard | 3 фильтра + 4 KPI + график + treemap + таблица | 10 | референсный KPI-дашборд |
| ranking | 2 фильтра + рейтинг + treemap + таблица + 2 bar | 7 | пример рейтинга (топ-N) |
| comparison | 2 фильтра + 4 KPI + stacked bar + pie + вывод + таблица | 10 | пример сравнения периодов |
| factor_analysis | 2 фильтра + 3 KPI + waterfall bar + таблица | 7 | пример факторного анализа |
| geo_analytics | 3 фильтра + 3 KPI + карта + график + таблица | 9 | пример геоаналитики |
| simple | Фильтр + график + таблица | 3 | — |

**Для каждого шаблона есть детальный скилл:**
- `/create-kpi-dashboard` — KPI-дашборд (метрики, тренд, карта, сводная таблица)
- `/create-ranking` — рейтинг (топ-N, treemap, drill-down)
- `/create-comparison` — сравнение двух периодов (KPI-дельты, stacked bar)
- `/create-factor-analysis` — факторный анализ (waterfall, 3 KPI, CF-таблица)
- `/create-geo-analytics` — геоаналитика (карта-хороплет, KPI, CF-таблица)
- `/create-simple-report` — базовый отчёт

---

## When to Use

- "Создай дашборд" / "построй отчёт" / "визуализируй данные"
- "KPI дашборд" / "рейтинг" / "сравни периоды" / "факторный анализ" / "покажи на карте"
- Нужен комплексный дашборд (не один график)

**Не использовать если:**
- Нужен только SQL → `/generate-sql`
- Нужен только анализ без визуализации → `/analyze-data`
- Нужно объяснить существующий график → `/explain-chart`

---

## Workflow (5 этапов)

### Этап 1: Понять данные и выбрать шаблон

```
# 1.1 Исследовать источник
mcp__postgres__query(sql="SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='...' AND table_name='...'")
mcp__postgres__query(sql="SELECT * FROM schema.table LIMIT 5")
mcp__postgres__query(sql="SELECT COUNT(*), MIN(date), MAX(date) FROM schema.table")

# 1.2 Выбрать шаблон
mcp__modusbi__report_template(action="list")
```

**Decision tree выбора шаблона:**
```
Что показываем?
├─ Мониторинг метрик + тренд + карта → kpi_dashboard
├─ Топ-N / рейтинг категорий        → ranking
├─ Сравнение двух периодов           → comparison
├─ Факторный / waterfall анализ      → factor_analysis
├─ Геоаналитика с картой             → geo_analytics
└─ Простой отчёт (график + таблица)  → simple
```

### Этап 2: Создать датасет(ы)

```
# 2.1 Создать датасет из SQL
dataset_result = mcp__modusbi__dataset_create_from_sql(
  sql_query="SELECT region, category, SUM(amount) AS revenue, COUNT(*) AS orders FROM schema.table GROUP BY region, category ORDER BY SUM(amount) DESC",
  datasource_id=<ID>,    # НЕ хардкодить! Получить через datasource_operations(action="list")
  name="my_dataset",
  caption="Описание датасета"
)
dataset_id = dataset_result["dataset"]["id"]

# 2.2 Задать русские aliases ДО привязки датасета к компонентам
mcp__modusbi__dataset_operations(
  action="update",
  dataset_id=dataset_id,
  field_aliases={"region": {"alias": "Регион"}, "revenue": {"alias": "Выручка"}}
)
```

**Правила SQL для BI:**
- ORDER BY обязателен (иначе порядок случайный)
- ROUND(..., 2) для AVG и процентов
- Технические AS-имена полей в SQL; русские названия задавай через `field_aliases` / `field_titles`
- WHERE ... IS NOT NULL для фильтра пустых
- Используй технические имена полей (region, не "Регион")

### Этап 3: Scaffold + настройка компонентов

```
# 3.1 Scaffold (создаёт report + все компоненты за 1 вызов)
result = mcp__modusbi__report_template(
  action="scaffold",
  template="kpi_dashboard",
  dataset_id=<ID>,
  name="Мой дашборд",
  group_id=20
)
report_id = result["report_id"]

# 3.2 КРИТИЧНО: Обновить КАЖДЫЙ data-компонент с реальными полями
# scaffold ставит value_field="value" (placeholder) и dataset_id на компоненте,
# но НЕ на полях внутри осей — надо явно обновить через update

# kpi_dashboard indices: 0-2 filters, 3-6 KPI, 7 chart, 8 treemap, 9 table.

# KPI
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  dataset_id=<ID>, value_field="revenue", aggregation="sum"
)

# Chart
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=7,
  dataset_id=<ID>, category_field="month", value_field="revenue",
  aggregation="sum"
)

# Table — ВАЖНО: value_fields_type="string", aggregation="none"
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=9,
  dataset_id=<ID>, value_field="region,category,revenue,orders",
  value_fields_type="string", aggregation="none",
  field_titles={"region": "Регион", "revenue": "Выручка"}
)
```

### Этап 4: Фильтры (ОБЯЗАТЕЛЬНО для production-quality)

Все референсные отчёты имеют фильтры. Это критично для UX.

#### Паттерн A: Раздельные фильтры (РЕКОМЕНДУЕТСЯ)

На референсных production-отчётах каждый фильтр — **отдельный HsFilterControlPanel** с 1 полем. Это даёт горизонтальную раскладку и профессиональный внешний вид.

```
# 4.1 Создать отдельные фильтры (1 поле = 1 компонент)
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsFilterControlPanel",
  title="Фильтры", value_field="region",
  dataset_id=<ID>,
  x=0, y=0, w=16, h=3
)
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsFilterControlPanel",
  title="Фильтры", value_field="category",
  dataset_id=<ID>,
  x=16, y=0, w=16, h=3
)
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsFilterControlPanel",
  title="Фильтры", value_field="period",
  dataset_id=<ID>,
  x=32, y=0, w=16, h=3
)

# 4.2 Стилизовать каждый фильтр (рамка + белый фон)
for filter_idx in [<IDX_1>, <IDX_2>, <IDX_3>]:
  mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=filter_idx,
    config_overrides={
      "outline.enabled": true, "outline.width": 1,
      "outline.color": "rgba(179,179,179,1)",
      "bgColor": "rgba(255,255,255,1)",
      "margin.l": 5, "margin.r": 5, "margin.t": 0, "margin.b": 0
    })

# 4.3 HD breakpoint — 5 фильтров в строку (60 cols):
# Filter 1: x=0,  y=0, w=12, h=3
# Filter 2: x=12, y=0, w=12, h=3
# Filter 3: x=24, y=0, w=12, h=3
# Filter 4: x=36, y=0, w=12, h=3
# Filter 5: x=48, y=0, w=12, h=3

# 4.4 ОБЯЗАТЕЛЬНО: filter_field_add на КАЖДОМ data-компоненте (chart/table/KPI/map), не только на фильтре!
# Иначе dropdown показывает значения, но данные НЕ фильтруются.
# ⚠️ КРИТИЧНО: alias ДОЛЖЕН СОВПАДАТЬ с alias на FilterControlPanel/глобальном фильтре, иначе
#    линковка не сработает (напр. панель «Вид ДТП», а на графике поле получит дефолтный alias
#    «Категория ДТП» → фильтр не применится). Передавай alias ЯВНО и ОДИНАКОВО везде.
for data_idx in [<все idx графиков/таблиц/KPI/карт>]:
  mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=data_idx,
    dataset_id=<ID>, value_field="category", alias="Вид ДТП", field_type="string")  # alias == как на панели!

# 4.5 ОБЯЗАТЕЛЬНО: z-index CSS-фикс (иначе dropdown фильтра рендерится ПОД соседними компонентами).
# style_operations update ЗАМЕНЯЕТ весь CSS → сначала GET, потом merge.
mcp__modusbi__style_operations(action="update", report_id=<ID>,
  css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; }")  # + существующий CSS
```

#### Паттерн B: Единый фильтр (простые отчёты)

```
# Один FilterControlPanel с несколькими полями (вертикальная раскладка)
mcp__modusbi__component_crud(action="add", report_id=<ID>,
  component_type="HsFilterControlPanel",
  title="Фильтры", value_field="placeholder",
  dataset_id=<ID>,
  x=0, y=0, w=48, h=3
)
# Добавить поля фильтров
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="region", alias="Регион", field_type="string"
)
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="category", alias="Категория", field_type="string"
)
# Удалить placeholder поле "value"
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value"
)
```

#### Каскадные зависимости (для обоих паттернов)
```
mcp__modusbi__component_filters(action="filter_set_cascade", report_id=<ID>,
  alias="city",           # дочерний фильтр
  depends_on="region"      # родительский фильтр
)
```

> `reset_mode` принимает `min`/`max` (schema и handler синхронизированы), `reset_type` — `always`.

### Этап 5: Стилизация и финализация

```
# 5.1 Visual customization через config_overrides (339 slug)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=7,
  config_overrides={
    "legend.visible": true,
    "legend.position": "top-center",
    "labels.visible": true,
    "stacking": "normal"
  }
)

# 5.2 Presets (6 готовых стилей)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  preset="kpi"  # minimal, presentation, dashboard, dark, print, kpi
)

# 5.3 Conditional formatting (таблицы/pivot)
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=9,
  config_overrides={
    "field": "delta_pct",
    "operator": "<",
    "value": 0,
    "color": "#ffffff",
    "background": "#f44336",
    "whole_row": false
  }
)

# 5.4 Сортировка графиков/таблиц
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=7,
  value_field="revenue", config_overrides={"order": "desc"}
)

# 5.5 CSS стилизация отчёта (report-level, НЕ компоненты)
mcp__modusbi__style_operations(
  action="update", report_id=<ID>,
  css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; } .panelTitle { color: #1a5276; font-weight: 700; }"
)

# 5.6 Очистка orphan global_filters (если фильтр переделывали)
# Посмотреть все глобальные фильтры:
mcp__modusbi__report_operations(action="global_filters_list", report_id=<ID>)
# Удалить лишний:
mcp__modusbi__report_operations(action="global_filter_delete", report_id=<ID>, variable_name="old_filter")
```

---

## Critical Lessons (из опыта создания дашбордов)

### 1. dataset_id binding

scaffold ставит `dataset_id` на уровне компонента, но поля внутри axes получают `dataset_id: null`.
**Решение:** всегда делать `component_crud(action="update", dataset_id=...)` для КАЖДОГО data-компонента после scaffold.

### 2. Агрегация

- **Charts**: aggregation="sum" (или avg/count). aggregation="none" вызывает GROUP BY SQL ошибки!
- **Tables**: aggregation="none" + value_fields_type="string" для raw data

### 3. Grid width = 48 (lg breakpoint)

Стандартная сетка w=48 (48-col grid, lg breakpoint). HD breakpoint = 60 cols. Все позиции x/y/w/h в шаблонах используют 48-col grid.

### 4. FilterControlPanel

- **Production-паттерн**: 1 фильтр = 1 отдельный FilterControlPanel (горизонтально)
- **Стилизация**: outline.enabled=true, outline.width=1, outline.color="rgba(179,179,179,1)", bgColor="rgba(255,255,255,1)"
- Нужен dataset_id через update
- filter_field_add для каждого dropdown (паттерн B)
- Удалить placeholder "value" через filter_field_remove
- field_type="string" для обычных dropdowns

### 5. Компоненты без данных

HsTextBlock, HsPageContainer, HsSubheaderComponent, HsImagePanel, HsFilterControlPanel — НЕ требуют value_field/dataset_id при scaffold.

### 6. Русские названия (ОБЯЗАТЕЛЬНО)

Все пользовательские подписи ДОЛЖНЫ быть на русском: фильтры, столбцы таблиц, легенды графиков.

**Фильтры (FilterControlPanel):** ВСЕГДА передавать `alias="Русское название"` при `filter_field_add`:
```
# ✅ ПРАВИЛЬНО — русский alias
filter_field_add(report_id=X, component_idx=N, value_field="region", alias="Регион", field_type="string", dataset_id=Y)

# ❌ НЕПРАВИЛЬНО — alias по умолчанию = имя поля (английское)
filter_field_add(report_id=X, component_idx=N, value_field="region")
```
Alias должен совпадать у FilterControlPanel и у ВСЕХ data-компонентов — иначе global_filter не свяжется!

**Столбцы таблицы:** передавать `field_titles` при add/update:
```
component_crud(action="update", report_id=X, component_idx=N,
  field_titles={"region": "Регион", "dtp_count": "Кол-во ДТП", "dead_count": "Погибших"})
```

**Легенды графиков:** задать alias в датасете через `field_aliases`:
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"region": {"alias": "Регион"}, "dtp_count": {"alias": "Кол-во ДТП"}})
```

**Global filters:** глобальный фильтр получает имя из `alias` первого filter_field_add. Если alias = "region" → фильтр называется "region". Если alias = "Регион" → фильтр называется "Регион".

---

## Component Type Reference

| Тип | Назначение | Ключевые params |
|-----|-----------|----------------|
| HsTotalsPanelV2 | KPI число | value_field, aggregation, preset="kpi" |
| HsBarAMchartsChart | Столбчатая | category_field, value_field, `config_overrides={"orientation":"h"|"v"}`, stacking |
| HsLineAMchartsChart | Линейная | category_field, value_field (несколько через запятую) |
| HsPieAMchartsChart | Круговая | category_field, value_field |
| HsTableReactabularChart | Таблица | value_field (через запятую), value_fields_type="string", aggregation="none" |
| HsTreeMap | Treemap | category_field, value_field, size_field |
| HsMapLeafletChart | Карта | value_field, затем map_set_geokeys (bubble: latfield/lonfield, choropleth: geo_type/geofield). ⚠️ map.center.lat/lng — render-dead (auto-fit перекрывает), центр через геоданные, не слагом |
| HsFilterControlPanel | Фильтры | dataset_id, затем filter_field_add |
| HsPageContainer | Табы | page_add для вкладок |
| HsSubheaderComponent | Заголовок | title, config_overrides |
| HsTextBlock | Текст | text_content (HTML) |
| HsPivotChart | Сводная | row_fields, column_fields, value_field |
| HsComparisonChart | Сравнение 2 объектов | UNPIVOT DS (объект\|показатель\|значение), category_field=объект, column_fields=показатель, value_field=значение. config_overrides: comparison.object1/object2 |
| HsTreeGraph | Граф GoJS | category_field=id (INTEGER!), value_field="parent_id,label,measure", aggregation="" |

---

## Quick Reference: Размеры — 48-col grid (lg breakpoint)

```
Grid: w=48 (lg breakpoint), HD: w=60

--- Паттерн A: Раздельные фильтры (production) ---
Filter (каждый): x=N*16, y=0, w=16, h=3  (48-col grid, 3 фильтра)
HD breakpoint:   x=N*12, y=0, w=12, h=3   (HD 60, до 5 фильтров)

--- Паттерн B: Единый фильтр (simple) ---
FilterPanel:     x=0, y=0,  w=48, h=3

KPI (4 в ряд):  x=0, y=3,  w=12, h=3  (каждый)
Chart (full):    x=0, y=6,  w=48, h=7
Chart (half):    x=0, y=6,  w=24, h=7
Map:             x=0, y=13, w=24, h=8
Table:           x=24,y=13, w=24, h=8
Table (full):    x=0, y=13, w=48, h=8
Tabs:            x=0, y=0,  w=48, h=3
```

---

## Datasource Discovery (НЕ хардкодить!)

```
# Найти доступные источники
mcp__modusbi__datasource_operations(action="list")

# Проверить подключение
mcp__modusbi__preflight_check_datasource(datasource_id=<ID>)

# Найти существующие датасеты
mcp__modusbi__dataset_operations(action="list")
```
