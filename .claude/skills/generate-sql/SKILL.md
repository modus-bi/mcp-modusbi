---
name: generate-sql
description: Генерирует оптимизированный SQL запрос для BI дашбордов с правильной сортировкой (ORDER BY), типами данных (::INTEGER), округлением (ROUND), техническими alias для MCP-датасетов и русскими подписями через field_aliases. Используйте когда пользователь просит SQL для топ-N, динамики, сравнений, или любых аналитических запросов для визуализации.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: sql-generation
    database: PostgreSQL
---

# Generate SQL: Правильные запросы для BI

## Overview

Этот skill генерирует SQL запросы оптимизированные для BI систем и дашбордов.

**Ключевые возможности:**
- 📊 30+ готовых паттернов (топ-N, time series, correlations)
- ✅ Автоматическое применение ORDER BY (для правильной сортировки графиков)
- 🔢 Правильные типы данных (::INTEGER для EXTRACT, ROUND для чисел)
- 🌍 Технические поля (`snake_case`) + русские подписи через `field_aliases`
- ⚡ Оптимизация (индексы, LIMIT, WHERE)
- ✔️ Валидация перед выполнением

**Опирается на:**
- Skill: `/sql-bi-expert` — 30+ SQL паттернов для BI
- Best practices из production опыта

---

## When to Use This Skill

Используй этот skill когда пользователь:

- ✅ Просит **SQL запрос** для данных
- ✅ Нужен запрос для **создания датасета**
- ✅ Спрашивает **"как написать SQL"** для задачи
- ✅ Упоминает **топ-N**, **динамика**, **группировка**
- ✅ Нужен запрос для **графика** (bar, line, pie)
- ✅ Просит **оптимизировать** существующий SQL

**Триггерные фразы:**
- "Напиши SQL для топ-10 клиентов"
- "Как получить динамику по месяцам?"
- "SQL для сравнения периодов"
- "Запрос для корреляции X и Y"

**Не использовать если:**
- ❌ Нужен полный дашборд (используй `/create-dashboard`)
- ❌ Нужен анализ данных (используй `/analyze-data`)
- ❌ SQL уже есть, нужно только выполнить

---

## 5 Критичных правил SQL для BI

### ❗ Правило #1: ВСЕГДА ORDER BY

**ПОЧЕМУ:** BI системы НЕ сохраняют порядок строк после агрегации!

```sql
-- ❌ ПЛОХО: порядок случайный
SELECT
  EXTRACT(HOUR FROM datetime) AS hour,
  COUNT(*) AS count
FROM accidents
GROUP BY EXTRACT(HOUR FROM datetime)
-- Графики: 15, 3, 22, 8... (хаос!)

-- ✅ ХОРОШО: правильный порядок
SELECT
  EXTRACT(HOUR FROM datetime)::INTEGER AS hour,
  COUNT(*) AS count
FROM accidents
GROUP BY EXTRACT(HOUR FROM datetime)
ORDER BY EXTRACT(HOUR FROM datetime)  -- ОБЯЗАТЕЛЬНО!
-- Графики: 0, 1, 2, ..., 23 (правильно!)
```

---

### ❗ Правило #2: ::INTEGER для EXTRACT

**ПОЧЕМУ:** EXTRACT возвращает numeric (1.0, 2.0) — некрасиво в графиках!

```sql
-- ❌ ПЛОХО: дробные числа
EXTRACT(HOUR FROM datetime) AS hour
-- Вернёт: 1.0, 2.0, 3.0

-- ✅ ХОРОШО: целые числа
EXTRACT(HOUR FROM datetime)::INTEGER AS hour
-- Вернёт: 1, 2, 3
```

---

### ❗ Правило #3: ROUND для чисел

**ПОЧЕМУ:** 23.456789% некрасиво!

```sql
-- ❌ ПЛОХО: много знаков
AVG(amount) AS avg_amount
SUM(delivered) / SUM(total) AS rate
-- Вернёт: 1234.56789, 0.876543

-- ✅ ХОРОШО: округлено
ROUND(AVG(amount::numeric), 2) AS avg_amount
ROUND(SUM(delivered)::numeric / SUM(total) * 100, 2) AS rate_pct
-- Вернёт: 1234.57, 87.65
```

**Правила округления:**
- Деньги: 2 знака → `1234.57 ₽`
- Проценты: 1-2 знака → `87.7%`
- Большие числа: 0 знаков → `12345`
- Коэффициенты: 3 знака → `0.876`

---

### ❗ Правило #4: Технические AS + русские подписи через field_aliases

**ПОЧЕМУ:** MCP-компоненты ссылаются на поля датасета по имени. В SQL держим стабильные технические имена, а русские легенды задаём после создания датасета через `dataset_operations(action="update", field_aliases=...)`.

```sql
-- ❌ ПЛОХО для MCP: русские поля в датасете
SELECT
  region AS "Регион",
  SUM(amount) AS "Выручка (₽)"
FROM sales
GROUP BY region

-- ✅ ХОРОШО: технические имена для binding
SELECT
  region AS region,
  SUM(amount) AS revenue
FROM sales
GROUP BY region
-- Потом: field_aliases={"region": {"alias": "Регион"}, "revenue": {"alias": "Выручка (₽)"}}
```

**Best practices:**
```sql
AS region                      -- Простое поле
AS revenue                     -- Метрика
AS delivery_days               -- Единицы в alias через field_aliases
AS revenue_without_vat         -- Контекст в техническом имени
```

---

### ❗ Правило #5: NULL handling

```sql
-- ❌ ПЛОХО: NULL ломает графики
SELECT region, SUM(amount)
FROM sales
GROUP BY region
-- NULL регион попадёт в результат!

-- ✅ ХОРОШО: фильтруем NULL
SELECT region AS region, SUM(amount) AS amount_sum
FROM sales
WHERE region IS NOT NULL
GROUP BY region
```

---

## SQL Patterns (готовые шаблоны)

### Pattern 1: Top-N (топ)

```sql
-- Топ-10 регионов по продажам
SELECT
  region AS region,
  SUM(amount) AS revenue,
  COUNT(*) AS order_count,
  ROUND(AVG(amount::numeric), 2) AS avg_order_value
FROM sales
WHERE date >= '2024-01-01'
  AND region IS NOT NULL
GROUP BY region
ORDER BY SUM(amount) DESC  -- Сортировка!
LIMIT 10                    -- Ограничение!
```

**Обязательно:**
- ✅ ORDER BY (иначе порядок случайный)
- ✅ LIMIT (для контроля количества)
- ✅ WHERE IS NOT NULL

---

### Pattern 2: Time Series (динамика)

```sql
-- Продажи по месяцам за 2024
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(amount) AS revenue,
  COUNT(*) AS order_count,
  ROUND(AVG(amount::numeric), 2) AS avg_order_value
FROM sales
WHERE date >= '2024-01-01' AND date < '2025-01-01'
GROUP BY DATE_TRUNC('month', date)
ORDER BY DATE_TRUNC('month', date)  -- Хронологический порядок!
```

**Варианты группировки:**
```sql
DATE_TRUNC('hour', timestamp)   -- По часам
DATE_TRUNC('day', date)          -- По дням
DATE_TRUNC('week', date)         -- По неделям
DATE_TRUNC('month', date)        -- По месяцам
DATE_TRUNC('quarter', date)      -- По кварталам
DATE_TRUNC('year', date)         -- По годам
```

---

### Pattern 3: Year-over-Year Comparison

```sql
-- Сравнение 2024 vs 2023
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(amount) AS revenue_current,
  LAG(SUM(amount), 12) OVER (ORDER BY DATE_TRUNC('month', date)) AS revenue_previous,
  ROUND(
    ((SUM(amount) - LAG(SUM(amount), 12) OVER (ORDER BY DATE_TRUNC('month', date)))
     / LAG(SUM(amount), 12) OVER (ORDER BY DATE_TRUNC('month', date)) * 100)::numeric,
    2
  ) AS yoy_growth_pct
FROM sales
WHERE date >= '2023-01-01'
GROUP BY DATE_TRUNC('month', date)
ORDER BY DATE_TRUNC('month', date)
```

---

### Pattern 4: Percentage Distribution

```sql
-- Доли регионов в общей выручке
SELECT
  region AS region,
  SUM(amount) AS revenue,
  ROUND(
    SUM(amount)::numeric / SUM(SUM(amount)) OVER () * 100,
    2
  ) AS share_pct
FROM sales
WHERE date >= '2024-01-01'
GROUP BY region
ORDER BY SUM(amount) DESC
```

---

### Pattern 5: Correlation

```sql
-- Корреляция доставки и NPS
SELECT
  ROUND(CORR(delivery_days, nps_score)::numeric, 3) AS correlation,
  COUNT(*) AS sample_size,
  ROUND(REGR_SLOPE(nps_score, delivery_days)::numeric, 3) AS slope,
  ROUND(REGR_INTERCEPT(nps_score, delivery_days)::numeric, 3) AS intercept
FROM orders
WHERE delivery_days IS NOT NULL
  AND nps_score IS NOT NULL
  AND delivery_days > 0
```

**Интерпретация:**
- r > 0.7: сильная корреляция
- slope: изменение Y на единицу X
- Нужен sample size >30

---

### Pattern 6: Cohort Analysis

```sql
-- Retention по месяцам регистрации
WITH cohorts AS (
  SELECT
    user_id,
    DATE_TRUNC('month', registration_date) AS cohort_month
  FROM users
),
activities AS (
  SELECT
    c.cohort_month,
    EXTRACT(MONTH FROM AGE(o.order_date, c.cohort_month))::INTEGER AS months_since_reg,
    COUNT(DISTINCT o.user_id) AS active_users
  FROM cohorts c
  LEFT JOIN orders o ON c.user_id = o.user_id
  GROUP BY c.cohort_month, months_since_reg
),
cohort_sizes AS (
  SELECT cohort_month, COUNT(*) AS cohort_size
  FROM cohorts
  GROUP BY cohort_month
)
SELECT
  a.cohort_month AS cohort_month,
  a.months_since_reg AS months_since_reg,
  ROUND(a.active_users::numeric / cs.cohort_size * 100, 1) AS retention_pct
FROM activities a
JOIN cohort_sizes cs ON a.cohort_month = cs.cohort_month
WHERE a.months_since_reg <= 12
ORDER BY a.cohort_month, a.months_since_reg
```

---

## Common Patterns

### Pattern: User asks for "топ-10 клиентов"

**Input:**
```
/generate-sql "топ-10 клиентов по выручке за 2024"
```

**Output:**
```sql
SELECT
  client AS client,
  SUM(amount) AS revenue,
  COUNT(*) AS order_count,
  ROUND(AVG(amount::numeric), 2) AS avg_order_value
FROM sales
WHERE date >= '2024-01-01' AND date < '2025-01-01'
  AND client IS NOT NULL
GROUP BY client
ORDER BY SUM(amount) DESC
LIMIT 10
```

**Применённые правила:**
- ✅ ORDER BY SUM(amount) DESC
- ✅ LIMIT 10
- ✅ ROUND для среднего
- ✅ Технические AS + русские подписи через `field_aliases`
- ✅ WHERE IS NOT NULL

---

### Pattern: User asks for "динамика по месяцам"

**Input:**
```
/generate-sql "динамика выручки по месяцам за 2024 с сравнением год к году"
```

**Output:**
```sql
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(amount) AS revenue_current,
  LAG(SUM(amount), 12) OVER (ORDER BY DATE_TRUNC('month', date)) AS revenue_previous,
  ROUND(
    ((SUM(amount) - LAG(SUM(amount), 12) OVER (ORDER BY DATE_TRUNC('month', date)))
     / NULLIF(LAG(SUM(amount), 12) OVER (ORDER BY DATE_TRUNC('month', date)), 0) * 100)::numeric,
    2
  ) AS yoy_growth_pct
FROM sales
WHERE date >= '2023-01-01'
GROUP BY DATE_TRUNC('month', date)
ORDER BY DATE_TRUNC('month', date)  -- ОБЯЗАТЕЛЬНО!
```

**Применённые правила:**
- ✅ ORDER BY для хронологии
- ✅ LAG(, 12) для year-over-year
- ✅ NULLIF для защиты от деления на 0
- ✅ ROUND для процентов

---

## Best Practices

### 1. Выбор правильной агрегации

| Задача | Агрегация | SQL |
|--------|-----------|-----|
| Сумма | SUM | `SUM(amount)` |
| Среднее | AVG | `ROUND(AVG(amount::numeric), 2)` |
| Количество | COUNT | `COUNT(*)` |
| Уникальные | COUNT DISTINCT | `COUNT(DISTINCT client_id)` |
| Максимум | MAX | `MAX(amount)` |
| Минимум | MIN | `MIN(amount)` |

### 2. WHERE vs HAVING

```sql
-- WHERE — фильтр ДО агрегации (строки)
WHERE date >= '2024-01-01'

-- HAVING — фильтр ПОСЛЕ агрегации (группы)
HAVING SUM(amount) > 1000000

-- Комбинация:
SELECT region, SUM(amount) as revenue
FROM sales
WHERE date >= '2024-01-01'      -- Фильтр строк
  AND amount > 0
GROUP BY region
HAVING SUM(amount) > 1000000    -- Фильтр групп
```

### 3. Window Functions для сравнений

```sql
-- LAG (предыдущее значение)
LAG(value, 1) OVER (ORDER BY date)      -- Прошлый период
LAG(value, 12) OVER (ORDER BY month)    -- Год назад

-- LEAD (следующее значение)
LEAD(value, 1) OVER (ORDER BY date)

-- Running total (накопительный итог)
SUM(value) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)

-- Percent of total
SUM(amount)::numeric / SUM(SUM(amount)) OVER () * 100
```

### 4. Оптимизация для больших данных

```sql
-- ✅ ХОРОШО: ограничиваем период
WHERE date >= '2024-01-01' AND date < '2025-01-01'

-- ✅ ХОРОШО: используем индексы
WHERE indexed_field = value

-- ✅ ХОРОШО: LIMIT для топ-N
LIMIT 10

-- ❌ ПЛОХО: весь архив
-- Нет WHERE date

-- ❌ ПЛОХО: SELECT *
SELECT *  -- Вернёт все 50 колонок!

-- ❌ ПЛОХО: коррелированный подзапрос
SELECT (SELECT ... FROM ... WHERE parent.id = child.id)
```

### 5. NULL Handling

```sql
-- Фильтровать NULL
WHERE region IS NOT NULL

-- Заменять на default
COALESCE(region, 'Неизвестно') AS region

-- Отдельная категория
CASE
  WHEN region IS NULL THEN 'Нет данных'
  ELSE region
END AS region

-- Безопасное деление
ROUND(numerator::numeric / NULLIF(denominator, 0), 2)
```

---

## Examples

### Example 1: Топ-N с процентами

**Input:**
```
/generate-sql "топ-10 товаров по выручке с процентом от общей"
```

**Output:**
```sql
SELECT
  product AS product,
  SUM(amount) AS revenue,
  COUNT(*) AS sales_count,
  ROUND(
    SUM(amount)::numeric / SUM(SUM(amount)) OVER () * 100,
    2
  ) AS share_pct
FROM sales
WHERE date >= '2024-01-01'
  AND product IS NOT NULL
GROUP BY product
ORDER BY SUM(amount) DESC
LIMIT 10
```

---

### Example 2: Moving Average

**Input:**
```
/generate-sql "выручка по дням с скользящим средним за 7 дней"
```

**Output:**
```sql
SELECT
  date::DATE AS day,
  SUM(amount) AS revenue,
  ROUND(
    AVG(SUM(amount)) OVER (
      ORDER BY date::DATE
      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )::numeric,
    2
  ) AS ma7
FROM sales
WHERE date >= '2024-01-01'
GROUP BY date::DATE
ORDER BY date::DATE
```

---

### Example 3: Funnel Conversion

**Input:**
```
/generate-sql "воронка продаж с конверсией между этапами"
```

**Output:**
```sql
WITH funnel AS (
  SELECT
    stage,
    stage_order,
    COUNT(*) AS count
  FROM user_funnel
  WHERE date >= '2024-01-01'
  GROUP BY stage, stage_order
)
SELECT
  stage AS stage,
  count AS count_value,
  LAG(count) OVER (ORDER BY stage_order) AS previous_stage_count,
  ROUND(
    count::numeric / NULLIF(LAG(count) OVER (ORDER BY stage_order), 0) * 100,
    1
  ) AS conversion_pct
FROM funnel
ORDER BY stage_order
```

---

## Troubleshooting

### Issue: Неправильная сортировка

**Symptom:** Графики в хаотичном порядке

**Причина:** Нет ORDER BY

**Solution:**
```sql
-- Добавь ORDER BY соответствующий задаче:

-- Для топ-N:
ORDER BY SUM(amount) DESC LIMIT 10

-- Для времени:
ORDER BY DATE_TRUNC('month', date)

-- Для часов:
ORDER BY hour

-- Для дней недели (понедельник первый):
ORDER BY CASE
  WHEN day = 'Понедельник' THEN 1
  WHEN day = 'Вторник' THEN 2
  ...
END
```

---

### Issue: Division by zero

**Symptom:** ERROR: division by zero

**Solution:**
```sql
-- ❌ ПЛОХО: может упасть
percent = part / total * 100

-- ✅ ХОРОШО: защита от 0
percent = ROUND(
  part::numeric / NULLIF(total, 0) * 100,
  2
)
```

---

### Issue: Дробные числа в категориях

**Symptom:** Час = 1.0, 2.0, 3.0 (некрасиво)

**Solution:**
```sql
-- ❌ ПЛОХО:
EXTRACT(HOUR FROM dt) AS hour

-- ✅ ХОРОШО:
EXTRACT(HOUR FROM dt)::INTEGER AS hour
```

---

## Validation Checklist

Перед выполнением SQL проверь:

**Syntax:**
- [ ] Запрос валиден (нет SQL errors)
- [ ] Все поля существуют
- [ ] GROUP BY соответствует SELECT

**BI Requirements:**
- [ ] ORDER BY есть (если важен порядок)
- [ ] LIMIT есть (для больших результатов)
- [ ] ::INTEGER для EXTRACT
- [ ] ROUND для чисел с плавающей точкой
- [ ] Технические AS-имена; русские подписи через `field_aliases`

**Performance:**
- [ ] WHERE date ограничивает период
- [ ] Нет SELECT *
- [ ] Используются индексы

**Data Quality:**
- [ ] IS NOT NULL фильтры
- [ ] NULLIF для деления
- [ ] COALESCE для defaults

---

## Quick Reference

### Типовые запросы (копипаст-ready)

**Топ-N:**
```sql
SELECT {category}, SUM({value})
FROM {table}
WHERE {date} >= '{start}' AND {category} IS NOT NULL
GROUP BY {category}
ORDER BY SUM({value}) DESC
LIMIT {N}
```

**Time series:**
```sql
SELECT DATE_TRUNC('{period}', {date}), SUM({value})
FROM {table}
WHERE {date} >= '{start}'
GROUP BY DATE_TRUNC('{period}', {date})
ORDER BY DATE_TRUNC('{period}', {date})
```

**Comparison:**
```sql
SELECT {category},
       SUM(CASE WHEN {condition_A} THEN {value} END) AS "A",
       SUM(CASE WHEN {condition_B} THEN {value} END) AS "B"
FROM {table}
GROUP BY {category}
ORDER BY "B" DESC
```

---

## Reference Documentation

- **/sql-bi-expert** — 30+ паттернов SQL, детальные правила
- **/bi-visualization-expert** — Какой SQL для какого типа графика
- **/statistical-analysis** — SQL для стат. тестов

---

**Sources:**
- [Agent Skills Specification](https://agentskills.io/specification)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQL Best Practices for BI](https://github.com/K-Dense-AI/claude-scientific-skills)
