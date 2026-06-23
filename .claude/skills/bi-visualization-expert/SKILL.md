---
name: bi-visualization-expert
description: "BI Visualization Expert: выбор правильного типа графика, настройка компонентов и layout дашборда. Используйте когда нужно выбрать тип графика для данных, настроить компоненты дашборда, спроектировать layout отчёта, применить best practices визуализации."
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: modusbi, playwright
---

# BI Visualization Expert: Правильный выбор и настройка графиков

> Skill для выбора типа визуализации и правильной настройки компонентов дашборда

## Назначение

Используй этот skill когда нужно:
- Выбрать тип графика для данных
- Настроить компоненты дашборда
- Спроектировать layout отчёта
- Применить best practices визуализации
- Создать effective dashboard
- Верифицировать layout и отрисовку через playwright (скриншоты)

## Матрица выбора типа графика

### Вопрос: "Какие данные визуализируем?"

| Тип данных | Задача | Рекомендуемый график |
|------------|--------|---------------------|
| **Одна категория + число** | Сравнение | Bar Chart (столбчатая) |
| **Время + число** | Тренд | Line Chart (линейный) |
| **Категории + доли** | Пропорции | Pie Chart (круговая) |
| **Много полей** | Детали | Table (таблица) |
| **Несколько чисел** | KPI | Totals Panel (панель) |
| **Категория + время** | Динамика по группам | Stacked Area/Line |
| **Две числовые переменные** | Корреляция | Scatter Plot |
| **География** | Региональное распределение | Map / Choropleth |

---

## Типы графиков: когда что использовать

### 1. Bar Chart (HsBarAMchartsChart) — столбчатая диаграмма

**Используй когда:**
- Сравниваешь категории (регионы, товары, менеджеры)
- Топ-N (топ-10 клиентов, лучшие продукты)
- Категорий 3-15 (не слишком мало, не слишком много)

**НЕ используй когда:**
- Динамика по времени (используй Line Chart)
- Слишком много категорий (>20 — используй Table)
- Пропорции/доли (используй Pie Chart)

**Пример:**
```python
mcp__modusbi__component_crud(
  action="add",
  component_type="HsBarAMchartsChart",
  title="Топ-10 регионов по продажам",
  dataset_id=342,
  category_field="region",       # X-axis (категории)
  value_field="revenue",         # Y-axis (значения)
  aggregation="sum",             # Агрегация
  x=0, y=0, w=24, h=8             # 48-col grid: half-width chart
)
```

**Best practices:**
- Сортируй по убыванию (самый большой слева)
- Используй горизонтальную если названия длинные
- Limit 10-15 категорий максимум
- Добавь data labels для точных значений

---

### 2. Line Chart (HsLineAMchartsChart) — линейный график

**Используй когда:**
- Динамика по времени (продажи по месяцам)
- Тренды (рост/падение)
- Несколько линий для сравнения (план/факт, регионы)

**НЕ используй когда:**
- Категории без временной последовательности
- Пропорции (используй Pie)

**Пример:**
```javascript
component_crud(
  action: "add",
  component_type: "HsLineAMchartsChart",
  title: "Динамика продаж по месяцам",
  dataset_id: 342,
  category_field: "month",        // X-axis (ОБЯЗАТЕЛЬНО ORDER BY!)
  value_field: "revenue",         // Y-axis
  aggregation: "sum"
)
```

**Best practices:**
- ВСЕГДА ORDER BY date в SQL (иначе линия будет ломаной!)
- Используй несколько линий для сравнения (факт vs план)
- Добавь markers для важных точек
- Smooth line для трендов (если много шума)

---

### 3. Pie Chart (HsPieAMchartsChart) — круговая диаграмма

**Используй когда:**
- Показать доли/пропорции (% от целого)
- Категорий 3-7 (не более!)
- Нужно показать "из чего состоит"

**НЕ используй когда:**
- Много категорий (>7 — нечитаемо)
- Тренды (используй Line)
- Сравнение абсолютных значений (используй Bar)

**Пример:**
```javascript
component_crud(
  action: "add",
  component_type: "HsPieAMchartsChart",
  title: "Распределение продаж по категориям",
  dataset_id: 342,
  category_field: "category",
  value_field: "revenue_pct",     // Проценты!
  aggregation: "sum"
)
```

**Best practices:**
- Limit 5-7 категорий (группируй остальное в "Прочие")
- Сортируй от большего к меньшему (clockwise)
- Используй контрастные цвета
- Добавь проценты на сегменты

**SQL для Pie Chart:**
```sql
SELECT
  category AS category,
  ROUND(SUM(amount)::numeric / SUM(SUM(amount)) OVER () * 100, 1) AS share_pct
FROM sales
GROUP BY category
ORDER BY SUM(amount) DESC
LIMIT 7
```

---

### 4. Table (HsTableReactabularChart) — таблица

**Используй когда:**
- Много полей (5+)
- Нужны детали (не агрегированные данные)
- Точные числа важны
- Нужна возможность поиска/фильтрации

**НЕ используй когда:**
- Нужно показать тренд (используй график)
- Сравнение категорий (используй Bar)

**Пример:**
```javascript
component_crud(
  action: "add",
  component_type: "HsTableReactabularChart",
  title: "Детализация заказов",
  dataset_id: 342,
  value_field: "date,client,product,amount,status",  // Несколько полей!
  value_fields_type: "string",    // Все как string (для таблицы)
  aggregation: "none",            // Нет агрегации (raw data)
  field_titles: {                 // Человекочитаемые заголовки
    "date": "Дата",
    "client": "Клиент",
    "product": "Товар",
    "amount": "Сумма (₽)",
    "status": "Статус"
  }
)
```

**Best practices:**
- Limit 100-200 строк (пагинация)
- Сортировка по дате (newest first)
- Форматирование чисел (запятые для тысяч)
- Подсветка важных значений (conditional formatting)

---

### 5. Totals Panel (HsTotalsPanelV2) — панель KPI

**Используй когда:**
- Нужно показать ключевые метрики (KPI)
- Один или несколько больших чисел
- Сравнение с baseline (план/факт, прошлый период)

**Пример:**
```javascript
component_crud(
  action: "add",
  component_type: "HsTotalsPanelV2",
  title: "Ключевые показатели",
  dataset_id: 342,
  value_field: "revenue,margin,orders",  // Несколько метрик
  aggregation: "sum"  // ОДНА агрегация (enum: sum/avg/max/min/count/none) на ВСЕ value-поля.
                      // Разные агрегации по метрикам — через предагрегацию в SQL датасета.
)
```

**Best practices:**
- 3-5 метрик максимум (не перегружай)
- Крупный шрифт (48-72px)
- Цвет для статуса (зелёный=хорошо, красный=плохо)
- Добавь change indicator (up 12% vs прошлый месяц)

---

### 6. Area Chart (HsAreaAMchartsChart) — диаграмма с областями

**Используй когда:**
- Динамика по времени + показать объём
- Stacked area: несколько категорий показать вместе
- Акцент на накопительный эффект

**Пример:**
```javascript
component_crud(
  action: "add",
  component_type: "HsAreaAMchartsChart",
  title: "Структура продаж по категориям",
  dataset_id: 342,
  category_field: "month",
  value_field: "electronics,clothing,food",  // Несколько областей
  aggregation: "sum"
)
```

---

## Layout: Grid System (48 колонок)

### Правила позиционирования

```
Grid: 48 колонок на `lg` breakpoint, 60 колонок на `hd`.

Стандартные ширины:
- Full width: w=48 (вся ширина)
- Half: w=24 (половина)
- Third: w=16 (треть)
- Quarter: w=12 (четверть)

Высота (h):
- KPI panel: h=4-6
- График: h=8-12
- Таблица: h=10-16
```

### Типовые layouts

**Layout 1: KPI + 2 графика + таблица**
```
+----------------------------+
| KPI Panel (w=48, h=6)      | y=0
+-------------+--------------+
| Chart 1     | Chart 2      | y=6
| (w=24, h=8) | (w=24, h=8)  |
+-------------+--------------+
| Table (w=48, h=12)         | y=14
+----------------------------+
```

**Код:**
```python
// KPI
{"x": 0, "y": 0, "w": 48, "h": 6}

// Chart 1 (слева)
{"x": 0, "y": 6, "w": 24, "h": 8}

// Chart 2 (справа)
{"x": 24, "y": 6, "w": 24, "h": 8}

// Table (внизу)
{"x": 0, "y": 14, "w": 48, "h": 12}
```

---

**Layout 2: Chart + Conclusion (автопозиционирование)**

```javascript
// Используй add_chart_with_conclusion для автоматического layout!
component_crud(
  action: "add_chart_with_conclusion",
  component_type: "HsBarAMchartsChart",
  title: "График",
  text_content: "<div>Вывод...</div>",
  h: 16  // Общая высота
)

// Результат:
// График: {x: 0, y: auto, w: 24, h: 16}
// Текст:  {x: 24, y: auto, w: 24, h: 16}
```

**Автоматическое y:**
```python
def get_next_y_position(report_id: int) -> int:
    """Найти свободное место внизу дашборда"""
    components = get_components(report_id)
    if not components:
        return 0
    return max(c.y + c.h for c in components)
```

---

## Цветовые схемы

### Стандартные палитры

**Корпоративная (синяя):**
```css
.header { background: #1976d2; }
.accent { color: #42a5f5; }
.chart-line { stroke: #1976d2; }
```

**Для презентации (контрастная):**
```css
.header { background: #1565c0; color: white; }
.positive { color: #4caf50; }  /* Зелёный для роста */
.negative { color: #f44336; }  /* Красный для падения */
```

**Для печати (ч/б):**
```css
.chart-line { stroke: #000000; stroke-width: 2px; }
.background { background: white; }
.text { color: #333333; }
```

---

### Семантические цвета (используй правильно!)

| Цвет | Значение | Использование |
|------|----------|---------------|
| Зелёный (#4caf50) | Позитив, рост | Revenue up, targets met |
| Красный (#f44336) | Негатив, падение | Revenue down, alerts |
| Синий (#1976d2) | Нейтрально, информация | Headers, main color |
| Жёлтый (#ffc107) | Внимание, warning | Approaching limits |
| Оранжевый (#ff9800) | Средний приоритет | Moderate risks |
| Серый (#757575) | Неактивно, второстепенно | Disabled, secondary |

**Пример использования:**
```html
<div style="color: #4caf50;">+12% рост</div>
<div style="color: #f44336;">-8% падение</div>
<div style="color: #ff9800;">Близко к лимиту</div>
```

---

## Dashboard Layout Principles

### Принцип 1: F-Pattern (F-паттерн чтения)

Пользователи читают дашборд **F-образно:**
1. Сверху слева -> направо (горизонтально)
2. Вниз по левому краю (вертикально)
3. Снова вправо (второй горизонтальный проход)

**Оптимальное размещение:**
```
+-----------------------------+
| 1. KPI (САМОЕ ВАЖНОЕ)       | <- Первый взгляд
+--------------+--------------+
| 2. Главный   | 4. Допол-    |
|    график    |    нительный | <- Второй взгляд
+--------------+--------------+
| 5. Детали (таблица)         | <- Третий взгляд
+-----------------------------+

Приоритет:
1 > 2 > 4 > 5
```

---

### Принцип 2: Visual Hierarchy (визуальная иерархия)

**Размер = важность:**

```
KPI (самое важное):     w=48, h=6  (полная ширина)
Главные графики:        w=24, h=10 (половина ширины)
Второстепенные графики: w=16, h=8  (треть ширины)
Детали (таблица):       w=48, h=12 (полная ширина, внизу)
```

**Группировка:**
```
Связанные компоненты рядом:
- "Продажи" и "Маржа" -> side by side
- "План" и "Факт" -> side by side
- "Топ товары" и "Детали по товарам" -> один под другим
```

---

### Принцип 3: Whitespace (воздух между элементами)

**НЕ делай плотно:**
```
Плохо:
+------+------+------+
|Chart1|Chart2|Chart3|  <- Всё слиплось
+------+------+------+
```

**Делай с отступами:**
```
Хорошо:
+------+  +------+  +------+
|Chart1|  |Chart2|  |Chart3|  <- Есть воздух
+------+  +------+  +------+
```

**Реализация:**
```python
# Используй w=23 вместо w=24 для отступа
{"x": 0, "y": 0, "w": 23, "h": 8}   # Chart 1
{"x": 24, "y": 0, "w": 23, "h": 8}  # Chart 2 (есть gap 1 колонка)
```

---

## Настройка компонентов: Best Practices

### Bar Chart Settings

```javascript
{
  component_type: "HsBarAMchartsChart",
  title: "Краткий заголовок (3-5 слов)",
  dataset_id: 342,

  // Поля (используй ТЕХНИЧЕСКИЕ названия из датасета!)
  category_field: "region",      // НЕ "Регион", а "region"
  value_field: "revenue",        // НЕ "Выручка", а "revenue"

  // Агрегация
  aggregation: "sum",  // sum, avg, count, min, max

  // Позиция в MCP задаётся отдельными параметрами x/y/w/h:
  // x: 0, y: 0, w: 24, h: 8  // 48-col grid, половина ширины
}
```

**Важно:**
- `category_field` и `value_field` — **ТЕХНИЧЕСКИЕ** имена (из SQL)
- "Регион" (alias) задаётся через `field_aliases` в датасете
- LLM должен использовать оригинальные имена полей!

---

### Line Chart Settings

```javascript
{
  component_type: "HsLineAMchartsChart",
  title: "Динамика по месяцам",
  dataset_id: 342,

  category_field: "month",       // X-axis (ДОЛЖЕН быть ORDER BY!)
  value_field: "revenue",        // Y-axis

  // Для нескольких линий
  value_field: "revenue,orders", // Через запятую

  aggregation: "sum"
}
```

**Чек-лист:**
- [ ] SQL имеет ORDER BY по category_field
- [ ] category_field — дата/время для трендов
- [ ] Не более 3-5 линий (иначе нечитаемо)

---

### Table Settings

```javascript
{
  component_type: "HsTableReactabularChart",
  title: "Детализация",
  dataset_id: 342,

  // Несколько полей через запятую
  value_field: "date,client,product,amount,status",

  // Тип полей (важно!)
  value_fields_type: "string",  // Все как строки для таблицы

  // Без агрегации (показать raw data)
  aggregation: "none",

  // Человекочитаемые заголовки
  field_titles: {
    "date": "Дата",
    "client": "Клиент",
    "product": "Товар",
    "amount": "Сумма (₽)",
    "status": "Статус"
  },

  // Limit в SQL (не более 200 строк)
  limit: 100
}
```

---

### Totals Panel Settings

```javascript
{
  component_type: "HsTotalsPanelV2",
  title: "KPI",
  dataset_id: 342,

  // Несколько метрик
  value_field: "revenue,orders,clients",

  // aggregation — единый enum на все поля. count_distinct НЕ поддерживается MCP:
  // делай COUNT(DISTINCT ...) в SQL датасета, затем aggregation: "max" (по готовой колонке).
  aggregation: "sum"
}
```

---

## Создание текстовых блоков (выводы)

### HTML структура для выводов

**Шаблон:**
```html
<div style="
  background: linear-gradient(135deg, #e3f2fd, #bbdefb);
  padding: 20px;
  border-radius: 10px;
  border-left: 5px solid #1976d2;
  font-family: 'Segoe UI', Arial, sans-serif;
">

<h2 style="color: #0d47a1; margin-top: 0;">
  ЗАГОЛОВОК ВЫВОДА
</h2>

<p style="font-size: 16px; line-height: 1.6;">
  <strong>Главная метрика:</strong> 156.7M руб (+12% г/г)
</p>

<h3 style="color: #1565c0;">ДРАЙВЕРЫ РОСТА</h3>
<ul style="line-height: 1.8;">
  <li><strong>Электроника</strong> — +34% (вклад 67%)</li>
  <li><strong>Москва</strong> — +28% (вклад 23%)</li>
</ul>

<h3 style="color: #c62828;">ЗОНЫ РИСКА</h3>
<ul style="line-height: 1.8;">
  <li><strong>Одежда</strong> — -5% (потеря 2.3M руб)</li>
</ul>

<h3 style="color: #2e7d32;">РЕКОМЕНДАЦИИ</h3>
<ol style="line-height: 1.8;">
  <li><strong>[КРИТИЧНО]</strong> Найти замену Газпром -> +5.2M руб/мес</li>
  <li><strong>[ВЫСОКИЙ]</strong> Расширить Электронику -> +3-4M руб</li>
</ol>

</div>
```

---

### Цветовые схемы для выводов

**Позитивный (рост, success):**
```html
<div style="background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
            border-left: 5px solid #4caf50;">
  <h2 style="color: #2e7d32;">ГИПОТЕЗА ПОДТВЕРЖДЕНА</h2>
  ...
</div>
```

**Негативный (риск, alert):**
```html
<div style="background: linear-gradient(135deg, #ffebee, #ffcdd2);
            border-left: 5px solid #f44336;">
  <h2 style="color: #c62828;">ПРОБЛЕМА ОБНАРУЖЕНА</h2>
  ...
</div>
```

**Нейтральный (информация):**
```html
<div style="background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            border-left: 5px solid #1976d2;">
  <h2 style="color: #0d47a1;">АНАЛИЗ</h2>
  ...
</div>
```

---

## Выбор визуализации: Decision Tree

```
Что хочешь показать?
|
+- Сравнить категории
|  +- Категорий <15 -> Bar Chart
|  +- Категорий >15 -> Table
|
+- Показать тренд
|  +- Одна линия -> Line Chart
|  +- Несколько линий -> Line Chart (multiple)
|  +- Накопительный -> Area Chart (stacked)
|
+- Показать пропорции
|  +- Категорий 3-7 -> Pie Chart
|  +- Категорий >7 -> Bar Chart (horizontal)
|
+- Показать детали
|  +- Поля <5 -> Table (compact)
|  +- Поля >5 -> Table (full width)
|
+- Показать KPI
|  +- Метрик 1-3 -> Totals Panel (large)
|  +- Метрик 4-6 -> Totals Panel (grid)
|
+- Показать корреляцию
   +- Scatter Plot (если доступен)
   +- Line Chart (две линии)
```

---

## Чек-лист создания компонента

### Перед созданием графика проверь:

**Данные:**
- [ ] Датасет создан и содержит нужные поля
- [ ] SQL имеет ORDER BY (если важен порядок)
- [ ] SQL имеет LIMIT (для топ-N)
- [ ] Поля имеют правильные типы (INTEGER, numeric)
- [ ] NULL значения обработаны

**Настройки:**
- [ ] component_type правильный для задачи
- [ ] title краткий и понятный (3-5 слов)
- [ ] category_field и value_field — ТЕХНИЧЕСКИЕ имена
- [ ] aggregation соответствует задаче
- [ ] position не перекрывает другие компоненты

**Layout:**
- [ ] x, y, w, h в пределах grid (`lg`: x=0..47, `hd`: x=0..59)
- [ ] w + x <= 48 для `lg` и <= 60 для `hd`
- [ ] h адекватен для типа (таблица выше, KPI ниже)

---

## Примеры готовых дашбордов

### Dashboard 1: Executive Dashboard (для руководства)

```
Компоненты:
1. KPI Panel (сверху): Revenue, Margin, Orders
   {x: 0, y: 0, w: 48, h: 6}

2. Line Chart (динамика): Revenue by month
   {x: 0, y: 6, w: 32, h: 10}

3. Text Block (выводы):
   {x: 32, y: 6, w: 16, h: 10}

4. Bar Chart (топ): Top 10 regions
   {x: 0, y: 16, w: 24, h: 10}

5. Pie Chart (распределение): Category split
   {x: 24, y: 16, w: 24, h: 10}

Стиль:
- Крупные цифры (48px для KPI)
- Минимум деталей (руководству не нужен noise)
- Акцент на ключевые метрики
```

---

### Dashboard 2: Operational Dashboard (для менеджеров)

```
Компоненты:
1. KPI Panel: Daily/Weekly/Monthly targets
   {x: 0, y: 0, w: 48, h: 4}

2. Line Chart: Sales trend (30 days)
   {x: 0, y: 4, w: 24, h: 8}

3. Bar Chart: Top managers
   {x: 24, y: 4, w: 24, h: 8}

4. Table: Recent orders (last 50)
   {x: 0, y: 12, w: 48, h: 14}

Стиль:
- Обновление real-time (или частое)
- Подсветка отклонений (красный/зелёный)
- Drill-down возможность
```

---

### Dashboard 3: Analytical Dashboard (для аналитиков)

```
Компоненты:
1. Line Chart: Main metric over time
   {x: 0, y: 0, w: 32, h: 10}

2. Text Block: Analysis & insights
   {x: 32, y: 0, w: 16, h: 10}

3. Bar Chart: Breakdown by dimension 1
   {x: 0, y: 10, w: 16, h: 10}

4. Bar Chart: Breakdown by dimension 2
   {x: 16, y: 10, w: 16, h: 10}

5. Scatter Plot: Correlation
   {x: 32, y: 10, w: 16, h: 10}

6. Table: Detailed data
   {x: 0, y: 20, w: 48, h: 12}

Стиль:
- Много деталей (аналитикам нужны подробности)
- Возможность экспорта (CSV/Excel)
- Интерактивные фильтры
```

---

## Визуальная верификация (playwright)

После создания дашборда проверь layout и отрисовку через скриншот:

```python
# 1. Открыть дашборд
browser_navigate(f"${MODUSBI_URL}/report/{report_id}")

# 2. Подождать рендеринг всех компонентов
browser_evaluate("await new Promise(r => setTimeout(r, 3000))")

# 3. Полный скриншот дашборда
browser_take_screenshot(name=f"dashboard_layout_{report_id}")

# 4. Проверить по чек-листу:
# - Все компоненты отрисовались (не пустые)
# - Layout корректный (нет наложений, whitespace на месте)
# - F-pattern соблюдён (KPI сверху, детали внизу)
# - Цвета семантически верные
# - Текст читаемый (заголовки, подписи осей)

# 5. Скриншот конкретного компонента (если нужна детализация)
browser_take_screenshot(
    name="kpi_panel_check",
    selector=".hs-component:first-child"
)
```

**Типичные проблемы при верификации:**

| Проблема | Симптом на скриншоте | Решение |
|----------|---------------------|---------|
| Наложение компонентов | Элементы перекрываются | Пересчитать y, h позиции |
| Пустой график | Белый прямоугольник | Проверить dataset_id, SQL |
| Обрезанные подписи | Текст вылезает за рамки | Увеличить h или использовать horizontal bar |
| Мелкие KPI | Цифры не читаются | Увеличить h до 6-8 |

---

## Антипаттерны визуализации

### Неправильный тип графика

**Проблема: Pie chart с 20 категориями**
```
Нечитаемо! Слишком много сегментов.

Решение:
- Топ-7 категорий + "Прочие"
- Или используй Bar Chart (horizontal)
```

**Проблема: Line chart для категорий**
```
"Продажи по регионам" через Line Chart — линия между регионами нелогична!

Решение: Bar Chart
```

---

### Слишком много на одном дашборде

**Плохо:**
```
15 графиков на одном дашборде
-> Информационный перегруз
-> Пользователь не знает куда смотреть
```

**Хорошо:**
```
5-7 компонентов максимум:
- 1 KPI panel
- 2-3 главных графика
- 1-2 второстепенных
- 1 таблица деталей
```

**Правило 7+-2:**
Человек может удержать в фокусе **7+-2** элемента.
Больше 9 компонентов -> разбивай на несколько дашбордов.

---

### Неправильные масштабы осей

**Проблема: Y-axis не начинается с 0**
```
Bar Chart с Y от 90 до 100:
-> Визуально выглядит как огромная разница
-> На самом деле разница 10%

Решение: Y-axis от 0 (или явно укажи если нет)
```

**Проблема: Разные масштабы для сравнения**
```
График 1: Revenue (0-100M)
График 2: Revenue (50-60M)
-> Визуально несравнимо!

Решение: Одинаковые масштабы для сравнимых графиков
```

---

### Conditional formatting на текстовом поле

Операторы `=` и `~` (contains) работают на строках напрямую.

```python
# ✅ Работает: точное совпадение по строке
component_styling(action="conditional_rule_add", report_id=N, component_idx=I,
  config_overrides={"field":"status","operator":"=","value":"FAIL",
    "background":"#f44336", "color":"#ffffff"})

# ✅ Substring match через '~' (contains)
component_styling(action="conditional_rule_add", report_id=N, component_idx=I,
  config_overrides={"field":"name","operator":"~","value":"критич",
    "background":"#ff0000"})
```

**Поддерживаемые операторы** (поведение фронтенда):
- `>, <, >=, <=` — numeric только (строка коэрцится в число)
- `=` — numeric или string (фронт сам различает)
- `~` (alias `contains`) — substring match через `.includes()`

**НЕ работают** (фронт не имеет в switch):
- `!=` — даёт явную error с подсказкой «дублировать правило»
- `regex`, `starts_with`, `ends_with`, `in` — нужен numeric rank workaround в SQL

**Numeric rank workaround** (только для unsupported операторов):
```sql
SELECT *, CASE status
  WHEN 'FAIL' THEN 3 WHEN 'WARN' THEN 2 WHEN 'PASS' THEN 1
END AS status_rank FROM dq_results
```
```python
component_styling(action="conditional_rule_add", ...,
  config_overrides={"field":"status_rank","operator":">=","value":3,
    "background":"#ffcdd2","color":"#b71c1c"})  # ranges запросы
```

### Сортировка категорий чарта — ТОЛЬКО через field_sort_set

**Проблема: годы / месяцы хаотичные в bar/line несмотря на ORDER BY в SQL**

Фронт ModusBI делает свою группировку поверх результата SQL — `ORDER BY` игнорируется. `config_overrides={"sort":"asc"}` дропается валидатором.

```python
# ❌ Не работает: фронт перетасует данные
SELECT year, SUM(amount) FROM t GROUP BY year ORDER BY year ASC
```

**Решение: `component_styling(action="field_sort_set", ...)`**

```python
component_styling(
    action="field_sort_set",
    report_id=N, component_idx=I,
    value_field="year",                          # имя поля категории
    config_overrides={"order": "asc"}            # 'asc' | 'desc'
)
```

Сортировка **корректна только на числовых полях** (`year:int`, `month_num:int`). Для `year_str:string` фронт сортирует лексикографически — используйте числовое поле в `category_field`.

### Дублирование title + legend — `showtitle: false`

**Проблема: над чартом показано имя ('Sales'), и в legend та же подпись серии**

Компонент рисует `.componentHeader` с `title`, а под ним legend с теми же подписями value_field — дублирование.

```python
# Скрыть header чтобы остался только legend
component_crud(action="update", report_id=N, component_idx=I,
               config_overrides={"showtitle": False})
```

Top-level slug `config.showtitle: bool`, default=True. Не задокументирован в большинстве help-вызовов — но валидный.

---

## Adaptive Design: дашборд для разных устройств

### Desktop (основной)

```
Grid: 48 колонок (`lg`)
Ширина: 1920px

Компоненты:
- KPI: w=48 (full width)
- Charts: w=24 (2 в ряд)
- Tables: w=48 (full width)
```

### Tablet (если нужна адаптация)

```
Grid: 24 колонки (половина `lg`)

Компоненты:
- KPI: w=24 (full)
- Charts: w=24 (1 в ряд, друг под другом)
```

### Mobile (обычно не нужно для BI)

```
BI дашборды редко смотрят на mobile.
Если нужно -> создавай отдельный "мобильный дашборд":
- Только KPI
- Простые графики
- Минимум деталей
```

---

## Специализированные визуализации

### Heatmap (тепловая карта)

**Используй для:**
- Correlation matrix (корреляции между метриками)
- Cohort analysis (retention по когортам)
- Time patterns (активность по часам x дням недели)

**SQL для heatmap:**
```sql
-- Активность по часам и дням недели
SELECT
  EXTRACT(DOW FROM timestamp)::INTEGER AS day_of_week,
  EXTRACT(HOUR FROM timestamp)::INTEGER AS hour,
  COUNT(*) AS activity
FROM events
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY day_of_week, hour
ORDER BY day_of_week, hour
```

---

### Funnel Chart (воронка)

**Используй для:**
- Conversion funnel (лид -> квал -> оффер -> сделка)
- User journey (регистрация -> активация -> покупка)

**SQL для funnel:**
```sql
SELECT
  stage AS stage,
  stage_order,
  COUNT(*) AS count_value,
  LAG(COUNT(*)) OVER (ORDER BY stage_order) AS prev_stage,
  ROUND(COUNT(*)::numeric / LAG(COUNT(*)) OVER (ORDER BY stage_order) * 100, 1) AS conversion_pct
FROM funnel
GROUP BY stage, stage_order
ORDER BY stage_order
```

---

### Gauge Chart (спидометр)

**Используй для:**
- Progress к цели (выполнение плана)
- Single metric с min/max/target

**Пример:**
```javascript
{
  type: "GaugeChart",
  value: 87,        // Текущее значение
  min: 0,
  max: 100,
  target: 100,      // Целевое значение
  ranges: [
    {from: 0, to: 70, color: "red"},      // Плохо
    {from: 70, to: 90, color: "yellow"},  // Средне
    {from: 90, to: 100, color: "green"}   // Хорошо
  ]
}
```

---

## Визуализация по типам анализа

### Trend Analysis -> Line Chart

```
Задача: Показать динамику
График: Line Chart
X-axis: Время (месяц/день)
Y-axis: Метрика
Best practice: Добавить trendline, MA (скользящее среднее)
```

### Comparison Analysis -> Bar Chart

```
Задача: Сравнить категории
График: Bar Chart (horizontal если названия длинные)
X-axis: Категория
Y-axis: Значение
Best practice: Сортировка DESC, топ-10
```

### Distribution Analysis -> Histogram / Box Plot

```
Задача: Показать распределение
График: Histogram (если доступен)
Альтернатива: Table с percentiles (p25, p50, p75, p95)
```

### Correlation Analysis -> Scatter Plot

```
Задача: Показать связь двух метрик
График: Scatter Plot
X-axis: Метрика 1
Y-axis: Метрика 2
Best practice: Добавить regression line (линия тренда)
```

### Composition Analysis -> Pie Chart / Stacked Bar

```
Задача: Показать из чего состоит
График: Pie Chart (если категорий <7)
Альтернатива: Stacked Bar Chart (если категорий >7)
```

---

## Расширенные возможности компонентов

### Multi-series chart через `series_field`

Раньше для multi-series (например, 4 категории × 6 лет) приходилось
копировать шаблонный chart с настроенной series-осью. Теперь можно
прямо:

```python
component_crud(action="add", component_type="HsBarAMchartsChart",
  title="Поголовье по категориям × годам",
  dataset_id=N, category_field="year", series_field="product",
  value_field="heads", aggregation="sum")
```

Frontend строит N серий через distinct values поля `series_field`.
Поддерживается на bar / line / area / stock chart. На остальных типах
вернёт warning (используйте `column_fields` для pivot/comparison).

### Растянуть chart по контейнеру

⚠️ `expandH`/`expandV` — **render-dead на bar** (config пишется, но фронт не растягивает
plot-область; подтверждено браузером). Растягивание задаётся **размером grid-ячейки** компонента
(`w`/`h` в layout), а НЕ через config_overrides.

### Default baseColor для bars

Builder теперь ставит `config.baseColor='#1F77B4'` (matplotlib classic
blue) на bar/line/area, чтобы bars не рендерились пустыми (`#FFFFFF`
на белом фоне). Override:
```python
config_overrides={"data.baseColor": "#1B7B45"}  # ваш бренд-цвет
```

### Donut / pie с центральной суммой

6 новых slugs для HsPieAMchartsChart:

```python
component_crud(action="add", component_type="HsPieAMchartsChart", ...,
  config_overrides={
    "showDonut": True,                                       # пончик с innerRadius=60%
    "summEnabled": True, "summFontSize": 36,                 # сумма в центре (размер работает)
    # ⚠️ summColor — render-dead (цвет суммы фронт не применяет), не использовать
    "labelsTemplate": "[[categories]] — [[percents]]%",      # шаблон подписей секторов
    "radius": 85,                                            # % радиуса
  })
```
Переменные `labelsTemplate`: `[[percents]] [[value]] [[title]] [[categories]] [[tooltip]]`.

### Поиск slug-ов по подстроке

```python
# Все slugs со словом "color" применимые к bar:
component_crud(action="list_slugs", component_type="HsBarAMchartsChart",
  slug_category="search:color")
# → outline.color, bgColor, legend.bgColor, balloon.fontColor, …

# Все donut-related slugs:
component_crud(action="list_slugs", slug_category="search:donut")
# → showDonut
```

### Карты Leaflet через MCP

`HsMapLeafletChart` создаётся через API и **работает полностью**:

```python
# Bubble-маркеры (точки на координатах из lat/lng в данных):
component_crud(action="add", report_id=N, component_type="HsMapLeafletChart",
  title="Карта ДТП", dataset_id=DS,
  category_field="region", value_field="dtp_count", aggregation="sum")
component_styling(action="map_set_geokeys", report_id=N, component_idx=I,
  config_overrides={"latfield": "lat", "lonfield": "lng"})

# Choropleth (заливка регионов из GeoJSON):
component_styling(action="geodata_list")  # узнать доступные GeoJSON
component_styling(action="map_set_geokeys", report_id=N, component_idx=I,
  config_overrides={"geo_type": "ao.geojson.json", "geofield": "ABBREV"})
```

### apply_theme — единый brand-pack CSS

```python
# 5-цветная тема генерит ~150 строк CSS (header, charts, filter, table,
# modal, scrollbar). 'merge' (default) — добавит к существующему CSS;
# 'replace' — затрёт.
style_operations(action="apply_theme", report_id=N,
  theme={
    "primary":   "#1B7B45",   # бренд-цвет (зелёный)
    "secondary": "#E8F5E9",
    "bg":        "#FFFFFF",
    "accent":    "#FF6B35",
    "text":      "#1A1A1A",
  },
  mode="merge")
```

### KPI с подзаголовком и info-строками

HsTotalsPanelV2 нативно поддерживает 3 типа value-полей через
`axes.values.fields[].valueType`:
- `value` — главное число (главный показатель)
- `subheader` — подзаголовок-строка под значением (доп. метрика)
- `info` — произвольная info-строка с опц. title

```python
# Главное число + подзаголовок + 2 info-строки в одной KPI карточке:
component_crud(action="add", component_type="HsTotalsPanelV2",
  title="Продажи Q4", report_id=N, dataset_id=DS,
  category_field="month", value_field="revenue", aggregation="sum",
  subheader_field="growth_pct",                    # подзаголовок
  info_fields="avg_check,total_orders")            # 2 info-строки
```

Frontend сам распределит fields по соответствующим визуальным slot'ам.

### KPI с картинкой / иконкой

⚠️ **HsTotalsPanelV2 НЕ имеет нативного icon-slot.** В рендере KPI нет
полей iconUrl/imageUrl и нет произвольного HTML — только CSS-обходы.

**Решение 1: `apply_theme` с `kpi_icons` (рекомендуется).**
```python
style_operations(action="apply_theme", report_id=N,
  theme={"primary":"#1B7B45", ...},
  kpi_icons={
    "0": "https://cdn.example.com/icons/sales.svg",
    "1": {"url": "data:image/svg+xml;base64,PHN2Zw==...",
          "size": "48px", "position": "top 8px right 8px"},
    "2": "/uploads/icon-orders.png",
  },
  mode="merge")
# → генерит CSS .react-grid-item[data-i="0"] .hsTotalsPanelV2 .componentBody {
#       background-image: url(...); background-position: top 12px right 12px;
#       background-size: 32px; padding-right: 56px;
#     }
```

**Решение 2: иконки через report-CSS `::before` (ПРОВЕРЕНО, рекомендуется).**
Портал грузит **Material Icons** (FontAwesome НЕ активен). Надёжный хук — стабильный id
грид-ячейки `#panel_<idx>` (= индекс компонента), заголовок плитки = `.caption > .titleText`.
Иконка-кружок без картинок-URL, лигатурой:
```python
style_operations(action="update", report_id=N, css="""
#panel_0::before { position:absolute; top:10px; right:12px; z-index:10; pointer-events:none;
  font-family:'Material Icons'; content:'paid'; font-size:19px; line-height:34px; text-align:center;
  width:36px; height:36px; border-radius:50%;
  background:#eaf1fe; color:#2563eb; border:1.5px solid #2563eb; }
""")
# ⚠️ ::before вешать на грид-ячейку #panel_<idx> (overflow:visible, position:absolute от RGL),
#    НЕ на .titleText (там не рендерится в углу). И НЕ задавать .hsGridPanel{position:relative!important}
#    — перебьёт inline position:absolute у .react-grid-item → сетка «лесенкой».
# Лигатуры: paid, trending_up, track_changes, show_chart, person,
#           check_circle, verified_user, vpn_key, link, schedule
```

⚠️ **HsTextBlock — только для ДЕКОРА/вёрстки, НЕ для значений KPI.** Значения KPI ВСЕГДА
data-bound (native HsTotalsPanelV2 на датасете) — чтобы данные текли и реагировали на фильтры.
Зашивать число в HTML (`<h2>$1.2M</h2>`) НЕЛЬЗЯ: это статичная «картинка», не BI.
Полный data-bound стиль-рецепт (KPI + иконки + спарклайн + gauge) — см. скилл `create-kpi-dashboard`.

**Решение 3: CSS-only (низкоуровневый workaround).**
```python
style_operations(action="update", report_id=N, css="""
.hsReport [data-component='3'] .hsTotalsPanelV2 .componentBody {
  background-image: url('https://...');
  background-position: top 12px right 12px;
  background-size: 32px;
  background-repeat: no-repeat;
}
""")
```

### Что НЕ работает в KPI (даже через MCP)

Эмпирически проверено по коду фронта:
- ❌ Sparkline (мини-график в карточке) — только в `HsTableReactabularChart`
- ❌ Custom HTML / innerHTML внутри KPI render
- ❌ Background image нативно (только сплошной backgroundColor)
- ❌ Multiple charts в одной KPI карточке

Альтернатива — **CustomChart3 «Групповая панель показателей»** —
отдельный плагин с поддержкой иконок. Не поддерживается через
`component_crud(action='add')`, нужен ручной монтаж через
`report_operations(action='update')`.

---

## Продвинутые техники

### Multiple Axes (несколько осей)

**Когда использовать:**
- Две метрики с разными масштабами (Revenue: млн, Orders: тысячи)

**Пример:**
```javascript
{
  type: "HsLineAMchartsChart",
  value_field: "revenue,orders",
  aggregation: "sum",  // единый enum на все поля (per-metric агрегацию — через SQL датасета)
  axes: {
    revenue: {position: "left", label: "Выручка (руб)"},
    orders: {position: "right", label: "Заказов (шт)"}
  }
}
```

---

### Conditional Formatting (условное форматирование)

**Для таблиц:**
```javascript
{
  type: "HsTableReactabularChart",
  conditional_formatting: [
    {
      field: "revenue",
      condition: "> 1000000",
      style: {background: "#e8f5e9", color: "#2e7d32"}  // Зелёный для >1M
    },
    {
      field: "margin",
      condition: "< 10",
      style: {background: "#ffebee", color: "#c62828"}  // Красный для <10%
    }
  ]
}
```

---

### Drill-down (углубление)

**Концепция:**
```
Дашборд 1 (высокоуровневый):
"Продажи по регионам" (Bar Chart)
-> Клик на "Москва"
-> Переход на Дашборд 2

Дашборд 2 (детальный):
"Продажи Москва: по магазинам, товарам, менеджерам"
```

**Реализация через фильтры:**
```javascript
// Дашборд 1
{
  component_type: "HsBarAMchartsChart",
  category_field: "region",
  on_click: {
    action: "filter",
    target_dashboard: REPORT_ID,   // id целевого дашборда детализации
    filter_field: "region"
  }
}
```

---

## Стандартные размеры компонентов

### Рекомендации по высоте (h)

```javascript
// KPI Panel
h: 4-6   (компактно, только цифры)

// Charts (графики)
h: 8-12  (стандартная высота)

// Charts с легендой
h: 10-14 (нужно место для legend)

// Tables (небольшие)
h: 10-12 (10-15 строк)

// Tables (полные)
h: 14-20 (20-50 строк)

// Text blocks (выводы)
h: 8-16  (зависит от объёма текста)
```

---

### Рекомендации по ширине (w)

```javascript
// Full width (заголовки, таблицы)
w: 48

// Half (два графика рядом)
w: 24

// Third (три графика рядом)
w: 16

// Quarter (четыре маленьких KPI)
w: 12

// График + Текст (add_chart_with_conclusion)
График: w: 24, Текст: w: 24
```

---

## Готовые шаблоны компонентов

### Template 1: Chart with Conclusion

```javascript
component_crud(
  action: "add_chart_with_conclusion",
  report_id: REPORT_ID,
  component_type: "HsBarAMchartsChart",
  title: "Топ-10 регионов по продажам",
  dataset_id: 342,
  category_field: "region",
  value_field: "revenue",
  aggregation: "sum",
  text_content: `
    <div style="background: linear-gradient(135deg, #e3f2fd, #bbdefb);
                padding: 20px; border-radius: 10px; border-left: 5px solid #1976d2;">
      <h2 style="color: #0d47a1;">ВЫВОДЫ</h2>
      <p>Топ-3 региона дают 67% выручки...</p>
      <h3 style="color: #2e7d32;">РЕКОМЕНДАЦИИ</h3>
      <ol>
        <li>Усилить маркетинг в регионах 4-10</li>
        <li>Диверсифицировать риски топ-3</li>
      </ol>
    </div>
  `,
  h: 16  // Общая высота
)

// Автоматически создаст:
// График: {x: 0, y: auto, w: 24, h: 16}
// Текст:  {x: 24, y: auto, w: 24, h: 16}
```

---

### Template 2: KPI Panel

```javascript
component_crud(
  action: "add",
  component_type: "HsTotalsPanelV2",
  title: "Ключевые показатели",
  dataset_id: 342,
  value_field: "revenue,margin,orders,clients",
  aggregation: "sum",  // единый enum на все поля; разные/distinct — предагрегация в SQL датасета
  x: 0,
  y: 0,
  w: 48,
  h: 6
)
```

---

### Template 3: Time Series with Comparison

```javascript
component_crud(
  action: "add",
  component_type: "HsLineAMchartsChart",
  title: "Динамика продаж: 2024 vs 2023",
  dataset_id: 342,
  category_field: "month",
  value_field: "revenue_2024,revenue_2023",  // Две линии
  aggregation: "sum",
  x: 0,
  y: 6,
  w: 32,
  h: 10
)
```

---

## Когда использовать add_chart_with_conclusion

### Критерии

**Используй когда:**
- График требует объяснения (что это значит)
- Нужны рекомендации на основе данных
- Сложный анализ (пользователь может не понять)
- Prescriptive analytics (что делать)

**НЕ используй когда:**
- График очевиден (простой KPI panel)
- Нет выводов (просто показать данные)
- Места мало (w < 24 для пары)

### Примеры

**Хороший use case:**
```
График: "Корреляция времени доставки и NPS"
Вывод: "Каждый день задержки -> -0.7 NPS.
        Рекомендация: SLA 1-2 дня -> +1.5 NPS -> +12% retention"

-> add_chart_with_conclusion
```

**Плохой use case:**
```
График: "Продажи сегодня"
Вывод: "Продажи сегодня 2.3M"

-> Просто показать число, не нужен вывод
-> Используй Totals Panel
```

---

## Color Palettes для разных тем

### Корпоративная (синяя)

```css
/* Primary */
--primary: #1976d2;
--primary-light: #42a5f5;
--primary-dark: #0d47a1;

/* Accent */
--accent: #ff9800;

/* Background */
--bg: #fafafa;
--bg-card: #ffffff;

/* Text */
--text-primary: #212121;
--text-secondary: #757575;

/* Semantic */
--success: #4caf50;
--warning: #ffc107;
--error: #f44336;
```

---

### Презентация (контрастная)

```css
/* High contrast для проектора */
--primary: #0d47a1;      /* Тёмно-синий */
--accent: #ff5722;       /* Яркий оранжевый */
--bg: #ffffff;           /* Белый фон */
--text: #000000;         /* Чёрный текст */

/* Charts */
--chart-1: #1976d2;
--chart-2: #f44336;
--chart-3: #4caf50;
--chart-4: #ff9800;
```

---

### Печать (чёрно-белая)

```css
/* Grayscale для печати */
--primary: #212121;
--secondary: #757575;
--bg: #ffffff;

/* Charts (оттенки серого) */
--chart-1: #212121;
--chart-2: #616161;
--chart-3: #9e9e9e;

/* Borders для разделения */
border: 1px solid #000000;
```

---

## Best Practices Summary

### DO (делай)

- **Выбирай правильный тип графика** для типа данных
- **Сортируй данные** (ORDER BY в SQL!)
- **Ограничивай количество** (LIMIT, топ-N)
- **Используй цвет семантически** (зелёный=рост, красный=падение)
- **Добавляй выводы** к графикам (text blocks с рекомендациями)
- **Группируй связанное** (sales chart + sales table рядом)
- **Оставляй whitespace** (не всё впритык)
- **Приоритезируй layout** (важное вверху слева)

### DON'T (не делай)

- **Не перегружай** дашборд (максимум 7-9 компонентов)
- **Не используй 3D** (тяжело читать, искажает данные)
- **Не используй слишком много цветов** (максимум 5-7)
- **Не делай pie chart** с >7 категориями
- **Не забывай про ORDER BY** в SQL!
- **Не используй SELECT *** без необходимости
- **Не перекрывай компоненты** (проверяй x, y, w, h)

---

## Финальный чек-лист дашборда

### Перед публикацией проверь:

**Данные:**
- [ ] Все компоненты показывают данные (нет ошибок)
- [ ] Графики в правильном порядке (ORDER BY)
- [ ] Числа правильно округлены (ROUND)
- [ ] Названия понятные через `field_aliases`, SQL-поля остаются техническими

**Визуализация:**
- [ ] Типы графиков подходят для данных
- [ ] Количество компонентов адекватно (5-9)
- [ ] Цвета семантически правильные
- [ ] Layout логичный (важное вверху)

**UX:**
- [ ] Заголовки понятные (без жаргона)
- [ ] Единицы измерения указаны (руб, шт, %)
- [ ] Есть выводы/рекомендации (text blocks)
- [ ] Whitespace между компонентами

**Performance:**
- [ ] Дашборд загружается <3 сек
- [ ] Нет огромных таблиц (>200 строк)
- [ ] Нет тяжёлых SQL (timeout <10 сек)

---

*Используй этот skill для создания effective BI dashboards*
