---
name: create-kpi-dashboard
description: Создаёт KPI дашборд с мониторингом метрик, трендом, картой и таблицей. Применять для мониторинга метрик: KPI-группы, каскадные фильтры, тренд, карта, сводная таблица.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "3.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# KPI Dashboard: Мониторинг метрик с детализацией

## Целевая структура (референсный KPI-дашборд «Динамика показателей»)

**Целевая структура (10 компонентов, scaffold "kpi_dashboard"):**
- 3x HsFilterControlPanel — раздельные фильтры (категория, тяжесть, регион)
- 4x HsTotalsPanelV2 — KPI (2 ряда по 2, w=24 каждый)
- HsBarAMchartsChart — тренд по месяцам (разноцветный, с фильтрацией)
- HsTreeMap — региональная структура
- HsTableReactabularChart — детализация с фильтрацией

**ВАЖНО:** PageContainer НЕ используется. Scaffold уже включает 3 фильтра.

---

## When to Use

- "KPI дашборд" / "мониторинг метрик" / "динамика показателей"
- Нужны: крупные числа + тренд + региональная разбивка + детализация
- Данные имеют: временное измерение + категории + метрики

---

## КРИТИЧЕСКИЕ ПРАВИЛА (из реального опыта)

### 1. DATE поля нельзя использовать как category в BarChart
BarChart показывает "undefined" на оси X для DATE полей. Всегда конвертируй:
```sql
TO_CHAR(DATE_TRUNC('month', datetime), 'YYYY-MM') AS month_text
```

### 2. Для фильтрации графика — ОТДЕЛЬНЫЙ датасет с полями фильтров
Датасет графика ДОЛЖЕН содержать те же поля, что и фильтры (category, region, severity...).
Иначе фильтры не влияют на график. GROUP BY должен включать эти поля.

### 3. filter_field_add — ВСЕГДА передавай dataset_id и alias явно
```
filter_field_add(..., alias="Русское название", dataset_id=<DS_ID>)
```
Без dataset_id поле получит dataset_id: null и сломает компонент. Без alias фильтр будет показывать техническое имя поля.

### 4. aggregation при update
Если передаёшь `aggregation=""` (пустая строка) — существующее значение сохраняется. Если нужно поменять — передай явно `aggregation="sum"` и т.п.

### 5. HsMapLeafletChart — требует map_set_geokeys после добавления
После add/scaffold карта не показывает данные без геопривязки.
Вызови `component_styling(action="map_set_geokeys", ..., config_overrides={"latfield": "lat", "lonfield": "lng"})` для bubble-режима (круги на координатах).
Если в датасете нет lat/lng — **используй HsTreeMap** (показывает структуру по регионам).

### 6. Layout: используй layout_update_breakpoint для HD
HD grid = 60 колонок. layout_update ставит одинаковые w/h для ВСЕХ breakpoints.
```
layout_update_breakpoint(breakpoint="hd", x=0, y=0, w=60, h=12)
```

### 7. FilterControlPanel — два паттерна
- **Раздельные** (production): 1 фильтр = 1 компонент, горизонтально, с outline. См. Шаг 3.
- **Единый**: h>=9 для 4+ фильтров (каждый dropdown ~2 grid units + padding).

### 8. Scaffold + update НЕ ДОБАВЛЯЕТ поля в axes
`update` не меняет categories/values axes. Для правильной настройки:
- Удали scaffold-компонент (`delete`)
- Создай заново через `add` с правильными `category_field`, `value_field`

---

## Workflow

### Шаг 1: Исследование данных

```
# Узнать структуру таблицы
mcp__postgres__query(sql="SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='...' AND table_name='...'")

# Узнать уникальные значения категорий
mcp__postgres__query(sql="SELECT DISTINCT category FROM schema.table LIMIT 20")

# Определить:
# - Временное поле (date/datetime/timestamp)
# - Категориальные поля (region, category, type, severity)
# - Числовые метрики (amount, count, dead_count, injured_count)
```

### Шаг 2: Создать ДВА датасета

**Датасет A — основной** (для KPI, TreeMap, таблицы, фильтров):
```
dataset_create_from_sql(
  sql_query="
    SELECT
      region,
      category,
      severity,
      COUNT(*) AS event_count,
      SUM(metric_1) AS total_metric_1,
      SUM(metric_2) AS total_metric_2
    FROM schema.table
    GROUP BY 1, 2, 3
    ORDER BY 1
  ",
  datasource_id=<ID>,
  name="kpi_main"
)
```

**Датасет B — для графика** (с month_text + полями фильтров):
```
dataset_create_from_sql(
  sql_query="
    SELECT
      TO_CHAR(DATE_TRUNC('month', datetime), 'YYYY-MM') AS month_text,
      category,
      severity,
      region,
      COUNT(*) AS event_count,
      SUM(metric_1) AS total_metric_1
    FROM schema.table
    WHERE datetime >= '2020-01-01'
    GROUP BY 1, 2, 3, 4
    ORDER BY 1
  ",
  datasource_id=<ID>,
  name="kpi_chart"
)
```

### Шаг 3: Scaffold + обновить фильтры

```
# Scaffold создаёт: 3 фильтра + 4 KPI (2x2) + BarChart + TreeMap + Table
mcp__modusbi__report_template(
  action="scaffold", template="kpi_dashboard",
  dataset_id=<DS_A>, name="KPI Dashboard", group_id=<GID>
)
# Запомнить report_id

# idx=0,1,2: Фильтры (уже созданы scaffold) — обновить поля
# Фильтр 1 → Категория
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=0,
  dataset_id=<DS_A>, value_field="category")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=0,
  value_field="category", alias="Категория", field_type="string", dataset_id=<DS_A>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=0,
  value_field="value")

# Фильтр 2 → Тяжесть
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=1,
  dataset_id=<DS_A>, value_field="severity")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=1,
  value_field="severity", alias="Тяжесть", field_type="string", dataset_id=<DS_A>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=1,
  value_field="value")

# Фильтр 3 → Регион
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=2,
  dataset_id=<DS_A>, value_field="region")
mcp__modusbi__component_filters(action="filter_field_add", report_id=<ID>, component_idx=2,
  value_field="region", alias="Регион", field_type="string", dataset_id=<DS_A>)
mcp__modusbi__component_filters(action="filter_field_remove", report_id=<ID>, component_idx=2,
  value_field="value")

# Стилизация фильтров
for filter_idx in [0, 1, 2]:
  mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=filter_idx,
    config_overrides={
      "outline.enabled": true, "outline.width": 1,
      "outline.color": "rgba(179,179,179,1)",
      "bgColor": "rgba(255,255,255,1)",
      "margin.l": 5, "margin.r": 5
    })
```

### Шаг 4: Обновить KPI (idx=3,4,5,6 — 2x2 layout, w=24)

```
# KPI 1 (idx=3)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=3,
  dataset_id=<DS_A>, value_field="event_count", aggregation="sum", title="Всего событий")
# KPI 2 (idx=4)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=4,
  dataset_id=<DS_A>, value_field="total_metric_1", aggregation="sum", title="Метрика 1")
# KPI 3 (idx=5)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=5,
  dataset_id=<DS_A>, value_field="total_metric_2", aggregation="sum", title="Метрика 2")
# KPI 4 (idx=6)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=6,
  dataset_id=<DS_A>, value_field="event_count", aggregation="avg", title="Среднее")

# Добавить фильтры к КАЖДОМУ KPI (ВАЖНО: dataset_id явно!)
for kpi_idx in [3, 4, 5, 6]:
  filter_field_add(component_idx=kpi_idx, value_field="category", alias="Категория", dataset_id=<DS_A>)
  filter_field_add(component_idx=kpi_idx, value_field="severity", alias="Тяжесть", dataset_id=<DS_A>)
  filter_field_add(component_idx=kpi_idx, value_field="region", alias="Регион", dataset_id=<DS_A>)
```

### Шаг 5: Добавить график (BarChart на датасете B)

```
# ВАЖНО: используем датасет B (с month_text и полями фильтров)
component_crud(action="add", report_id=<ID>,
  component_type="HsBarAMchartsChart", title="Динамика по месяцам",
  dataset_id=<DS_B>, category_field="month_text", value_field="event_count",
  aggregation="sum")

# Layout: вся ширина
layout_update_breakpoint(breakpoint="hd", x=0, y=12, w=60, h=12)

# Стилизация: разноцветные столбцы
component_crud(action="update", report_id=<ID>, component_idx=<CHART>,
  aggregation="sum",  # ОБЯЗАТЕЛЬНО повторить, иначе сбросится на max!
  config_overrides={
    "style.autoColor": "palette"   # ✅ единственный рабочий путь к разноцветным столбцам (verified ok на bar)
    # ⚠️ render-dead на bar (НЕ использовать): visuals.colorPalette="pal_2018", gradient (рисуется только на KPI/totals),
    #    visuals.columnBorderRadius (rx не применяется). Градиент — на HsTotalsPanelV2.
  })

# Фильтры (используем dataset_id датасета B!)
filter_field_add(component_idx=<CHART>, value_field="category", alias="Категория", dataset_id=<DS_B>)
filter_field_add(component_idx=<CHART>, value_field="severity", alias="Тяжесть", dataset_id=<DS_B>)
filter_field_add(component_idx=<CHART>, value_field="region", alias="Регион", dataset_id=<DS_B>)
```

### Шаг 6: Добавить TreeMap (вместо карты)

```
component_crud(action="add", report_id=<ID>,
  component_type="HsTreeMap", title="По регионам",
  dataset_id=<DS_A>, category_field="region", value_field="event_count",
  aggregation="sum")

# Layout: левая половина
layout_update_breakpoint(breakpoint="hd", x=0, y=24, w=30, h=14)

# Фильтры
filter_field_add(component_idx=<TREEMAP>, value_field="category", alias="Категория", dataset_id=<DS_A>)
filter_field_add(component_idx=<TREEMAP>, value_field="severity", alias="Тяжесть", dataset_id=<DS_A>)
```

### Шаг 7: Добавить таблицу

```
component_crud(action="add", report_id=<ID>,
  component_type="HsTableReactabularChart", title="Детализация",
  dataset_id=<DS_A>,
  value_field="region,category,severity,event_count,total_metric_1,total_metric_2",
  value_fields_type="string", aggregation="none",
  field_titles={
    "region": "Регион", "category": "Категория",
    "event_count": "Кол-во", "total_metric_1": "Метрика 1"
  })

# Layout: правая половина
layout_update_breakpoint(breakpoint="hd", x=30, y=24, w=30, h=14)

# Фильтры
filter_field_add(component_idx=<TABLE>, value_field="category", alias="Категория", dataset_id=<DS_A>)
filter_field_add(component_idx=<TABLE>, value_field="severity", alias="Тяжесть", dataset_id=<DS_A>)
filter_field_add(component_idx=<TABLE>, value_field="region", alias="Регион", dataset_id=<DS_A>)
```

### Шаг 8: Сортировка, Conditional formatting, CSS, Cleanup

```
# Сортировка графика по убыванию
mcp__modusbi__component_styling(action="field_sort_set", report_id=<ID>, component_idx=<CHART>,
  value_field="event_count", config_overrides={"order": "desc"}
)

# Conditional formatting на таблице (красный для низких, зелёный для высоких)
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=<TABLE>,
  config_overrides={"field": "event_count", "operator": ">=", "value": 100,
    "background": "#c8e6c9", "color": "#1b5e20"})
mcp__modusbi__component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=<TABLE>,
  config_overrides={"field": "event_count", "operator": "<", "value": 10,
    "background": "#ffcdd2", "color": "#b71c1c"})

# CSS стилизация отчёта (report-level)
mcp__modusbi__style_operations(action="update", report_id=<ID>,
  css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; } .panelTitle { color: #1a5276; font-weight: 700; } .hs-table-header { background: #1565c0 !important; color: white !important; }")

# Очистка orphan global_filters (если фильтры переделывали)
mcp__modusbi__report_operations(action="global_filters_list", report_id=<ID>)
mcp__modusbi__report_operations(action="global_filter_delete", report_id=<ID>, variable_name="old_filter_name")
```

### Шаг 9: Проверка в браузере

```
# Открыть в Playwright MCP
browser_navigate(url="${MODUSBI_URL}/report/<ID>")
browser_wait_for(text=["Детализация"])
browser_take_screenshot()

# Проверить фильтр
browser_click(ref=<filter_combobox>)
# Выбрать значение
# Проверить что ВСЕ компоненты обновились
```

---

## Layout (ASCII) — 48-col grid (lg breakpoint)

```
+--------------------------------------------------+ 48 cols
| [Категория ▼]  | [Тяжесть ▼]  | [Регион ▼]     |  h=3, w=16 each
+------------------------+-------------------------+ y=3
|     KPI #1 (w=24)      |     KPI #2 (w=24)       |  h=3
+------------------------+-------------------------+ y=6
|     KPI #3 (w=24)      |     KPI #4 (w=24)       |  h=3
+------------------------+-------------------------+ y=9
|           BarChart (w=48) — динамика по месяцам    | h=7
+------------------------+-------------------------+ y=16
|   TreeMap (w=24)       |   Table (w=24)           | h=8
+------------------------+-------------------------+ y=24
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
  field_titles={"region": "Регион", "category": "Категория", "event_count": "Кол-во", "total_metric_1": "Метрика 1"})
```

**3. Легенды графиков (field_aliases на датасете):**
```
dataset_operations(action="update", dataset_id=Y,
  field_aliases={"region": {"alias": "Регион"}, "event_count": {"alias": "Кол-во событий"}})
```

**4. Global filters:** имя глобального фильтра = alias из первого filter_field_add. Используй русский alias!

---

## Стиль «BI-эталон» (иконки + спарклайн + gauge) — ТОЛЬКО data-bound

Вид как в реальных BI (icon-кружок + крупное значение + подпись + спарклайн-тренд),
но значения ВСЕГДА из датасета. **НЕ строить KPI статическим HTML/HsTextBlock** — данные
должны течь и реагировать на фильтры. HsTextBlock допустим только для декора/вёрстки, не для метрик.

### Плитка KPI
native HsTotalsPanelV2, `value_field` + `where_filter` (напр. период=N для «текущего» значения),
слаги: `visuals.value.font.size` (≈2.3), `visuals.value.color`, `subtitle`, `outline.enabled/width/color`.

### Иконки-кружки-бейджи в углу карточки — через report-CSS (эмодзи в заголовке = tofu □, НЕ использовать)
Портал грузит **Material Icons** (FontAwesome НЕ активен). Бейдж в правом верхнем углу — `::before`
на САМОЙ грид-ячейке `#panel_<idx>` (= индекс компонента). ⚠️ НЕ на `.titleText` (там `::before`
привязывается к узкому inline-боксу и в углу НЕ рендерится). Ячейка = .react-grid-item, у неё
inline `position:absolute` + `overflow:visible` → надёжный контейнер для абсолютного `::before`:
```css
#panel_0::before { position:absolute; top:10px; right:12px; z-index:10; pointer-events:none;
  font-family:'Material Icons'; content:'paid'; font-size:19px; line-height:34px; text-align:center;
  width:36px; height:36px; border-radius:50%; background:#eaf1fe; color:#2563eb; border:1.5px solid #2563eb; }
/* и так на каждую KPI-плитку: #panel_1::before {content:'trending_up'; ...} и т.д. */
```
⛔ НЕ задавать `.hsGridPanel { position:relative !important }` — это та же .react-grid-item, её inline
`position:absolute` перебьётся `!important` → сетка рассыпается «лесенкой». Сплошной фон+обводка
контрастнее полупрозрачного rgba(.12) (иначе кружок почти не виден).
Лигатуры: paid, trending_up, track_changes, show_chart, person, check_circle, verified_user, vpn_key, link, schedule.
Карточный вид всех панелей: `.hsGridPanel { border-radius:14px; box-shadow:0 4px 14px rgba(15,23,42,.07); }`.

### Спарклайн под плиткой (нативного sparkline в KPI НЕТ)
Отдельный HsLineAMchartsChart, слаги: `axes.categoryLabels=false`, `axes.valueLabels=false`,
`axes.categoryGrid=false`, `axes.valueGrid=false`, `visuals.smoothing=true` → чистая линия-тренд.

### Gauge — HsSpeedometerV2AMcharts (поля value + threshold).

### ⚠️ ГЛАВНОЕ: раскладка KPI не должна «ехать» (staircase)
Сетка зависит от ширины окна: cols **hd=60, lg=48**, md=40, sm=30… `layout_update` пишет w/x
ОДИНАКОВО во все breakpoints — поэтому 5 плиток w12 хороши на hd (5×12=60), но на lg (48) 5-я
вылетает за край → react-grid вертикально компактит «лесенкой» с пустотами.
**ФИКС:** для каждого breakpoint, где не делится, задать отдельно —
`layout_update_breakpoint(breakpoint="lg", w=9, x=0/9/18/27/36)` (5×9=45≤48). Каждый ряд
заполнять полностью/одинаково по x — иначе компакция подтянет плитки в пустые слоты соседних рядов.
Проверять раскладку в браузере на ДВУХ ширинах (≈1280=lg и ≈1680=hd).

---

## Checklist

- [ ] Два датасета: A (основной), B (для графика с month_text + filter fields)
- [ ] FilterControlPanel: h>=9, все нужные фильтры
- [ ] 4 KPI: aggregation="sum", filter fields с dataset_id
- [ ] BarChart: на датасете B, category_field=month_text, aggregation="sum"
- [ ] BarChart: style.autoColor="palette" (разноцветный)
- [ ] BarChart: filter fields с dataset_id датасета B
- [ ] TreeMap (НЕ MapLeaflet): category_field=region, aggregation="sum"
- [ ] Table: value_fields_type="string", aggregation="none"
- [ ] ВСЕ data-компоненты: filter_field_add с ЯВНЫМ dataset_id
- [ ] Layout: layout_update_breakpoint(breakpoint="hd") для каждого компонента
- [ ] Проверка в браузере: фильтр меняет ВСЕ компоненты
