---
name: sql-bi-expert
description: "SQL for BI Expert: генерация правильных SQL для BI с ORDER BY, типами, округлением и русскими названиями. Используйте когда нужно сгенерировать SQL для создания датасета, написать запрос для графика/таблицы, подготовить данные для визуализации, создать агрегацию с правильной сортировкой."
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# SQL for BI Expert: Правильные запросы для аналитики и дашбордов

> Skill для генерации правильных SQL запросов для BI систем с фокусом на визуализацию

## Назначение

Используй этот skill когда нужно:
- Сгенерировать SQL для создания датасета
- Написать запрос для графика/таблицы
- Подготовить данные для визуализации
- Создать агрегацию с правильной сортировкой
- Обеспечить правильные типы и форматы

## КРИТИЧНЫЕ ПРАВИЛА для BI SQL

### Правило #1: ВСЕГДА используй ORDER BY

**ПОЧЕМУ:** BI системы НЕ сохраняют порядок строк после агрегации!

**Плохо:**
```sql
SELECT
  EXTRACT(HOUR FROM datetime) AS hour,
  COUNT(*) AS count
FROM accidents
GROUP BY EXTRACT(HOUR FROM datetime)
-- Графики будут в случайном порядке: 15, 3, 22, 8...
```

**Хорошо:**
```sql
SELECT
  EXTRACT(HOUR FROM datetime)::INTEGER AS hour,
  COUNT(*) AS count
FROM accidents
GROUP BY EXTRACT(HOUR FROM datetime)
ORDER BY EXTRACT(HOUR FROM datetime)
-- Графики в правильном порядке: 0, 1, 2, ..., 23
```

**Примеры обязательной сортировки:**
```sql
-- Часы суток
ORDER BY hour                    -- 0-23

-- Месяцы
ORDER BY month                   -- 1-12

-- Дни недели
ORDER BY CASE
  WHEN day = 'Понедельник' THEN 1
  WHEN day = 'Вторник' THEN 2
  ...
END

-- Топ-N (ВСЕГДА с LIMIT!)
ORDER BY COUNT(*) DESC LIMIT 15

-- Хронология
ORDER BY date ASC/DESC
```

---

### Правило #2: Используй ::INTEGER для EXTRACT

**ПОЧЕМУ:** EXTRACT возвращает numeric (может быть 1.0, 2.0), что плохо для графиков!

**Плохо:**
```sql
EXTRACT(HOUR FROM datetime) AS hour
-- Вернёт: 1.0, 2.0, 3.0 (дробные числа)
-- На графике: некрасиво, лишние десятичные знаки
```

**Хорошо:**
```sql
EXTRACT(HOUR FROM datetime)::INTEGER AS hour
-- Вернёт: 1, 2, 3 (целые числа)
-- На графике: красиво
```

**Для всех EXTRACT:**
```sql
EXTRACT(HOUR FROM dt)::INTEGER AS hour
EXTRACT(DOW FROM dt)::INTEGER AS day_of_week
EXTRACT(MONTH FROM dt)::INTEGER AS month
EXTRACT(YEAR FROM dt)::INTEGER AS year
```

---

### Правило #3: ROUND для процентов и средних

**ПОЧЕМУ:** 23.456789012% некрасиво в дашбордах!

**Плохо:**
```sql
SELECT
  region,
  AVG(amount) AS avg_amount,
  SUM(delivered) / SUM(total) AS delivery_rate
-- Вернёт: 1234.56789012, 0.876543210
```

**Хорошо:**
```sql
SELECT
  region,
  ROUND(AVG(amount::numeric), 2) AS avg_amount,
  ROUND(SUM(delivered)::numeric / SUM(total) * 100, 2) AS delivery_rate_pct
-- Вернёт: 1234.57, 87.65
```

**Правила округления:**
```sql
-- Деньги: 2 знака
ROUND(amount::numeric, 2)  -- 1234.57

-- Проценты: 1-2 знака
ROUND(percent::numeric, 1)  -- 87.7%

-- Большие числа: 0 знаков
ROUND(COUNT(*)::numeric, 0)  -- 12345

-- Коэффициенты: 3-4 знака
ROUND(coefficient::numeric, 3)  -- 0.876
```

---

### Правило #4: Технические AS в SQL, русские названия через field_aliases

**ПОЧЕМУ:** текущий MCP связывает компоненты с полями датасета по стабильным техническим именам. Русские подписи, легенды и описания задаются после создания датасета через `dataset_operations(action="update", field_aliases=...)`.

**Плохо:**
```sql
SELECT
  region AS "Регион",
  SUM(amount) AS "Выручка (₽)",
  ROUND(AVG(margin::numeric), 2) AS "Средняя маржа (%)"
FROM sales
GROUP BY region
-- Поля датасета получают русские имена, их неудобно безопасно ссылать в MCP.
```

**Хорошо:**
```sql
SELECT
  region AS region,
  SUM(amount) AS revenue,
  ROUND(AVG(margin::numeric), 2) AS avg_margin
FROM sales
GROUP BY region
-- После dataset_create_from_sql:
-- dataset_operations(action="update", field_aliases={
--   "region": {"alias": "Регион"},
--   "revenue": {"alias": "Выручка (₽)"},
--   "avg_margin": {"alias": "Средняя маржа (%)"}
-- })
```

**Best practices для названий:**
```sql
-- Используй snake_case для SQL alias
AS region
AS revenue
AS delivery_days
AS margin_pct

-- Контекст можно оставить в техническом имени
AS revenue_without_vat
AS active_users_30d

-- Не используй русские AS в датасете MCP
AS "Выручка"    -- плохо для MCP-полей
AS revenue      -- хорошо
```

---

### Правило #5: NULL handling (обработка пустых значений)

**Проблема:** NULL в данных ломает графики и расчёты!

**Решения:**

```sql
-- 1. Фильтровать NULL
WHERE region IS NOT NULL

-- 2. Заменять на значение по умолчанию
COALESCE(region, 'Неизвестно') AS region
COALESCE(amount, 0) AS amount

-- 3. Отдельная категория
CASE
  WHEN region IS NULL THEN 'Нет данных'
  ELSE region
END AS region
```

**Для агрегаций:**
```sql
-- SUM игнорирует NULL (правильно)
SUM(amount)  -- NULL не считается

-- AVG игнорирует NULL (может быть неправильно!)
AVG(rating)  -- Считает только не-NULL

-- COUNT(*) считает все строки
-- COUNT(column) считает только не-NULL
COUNT(*) AS total_rows
COUNT(rating) AS rated_rows
```

---

## Паттерны SQL для типовых задач аналитики

### Pattern 1: Топ-N с правильной сортировкой

```sql
-- Топ-10 регионов по продажам
SELECT
  region AS region,
  COUNT(*) AS order_count,
  SUM(amount) AS revenue,
  ROUND(AVG(amount::numeric), 2) AS avg_order_value
FROM sales
WHERE date >= '2024-01-01'
  AND region IS NOT NULL
GROUP BY region
ORDER BY SUM(amount) DESC  -- Сортировка по выручке!
LIMIT 10                    -- Только топ-10
```

**Обязательно:**
- ORDER BY (иначе порядок случайный!)
- LIMIT (иначе может быть 1000 строк)
- WHERE region IS NOT NULL (фильтр NULL)
- ROUND для средних
- Технические AS (`region`, `revenue`) + русские подписи через `field_aliases`

---

### Pattern 2: Динамика по времени (time series)

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
-- По часам
DATE_TRUNC('hour', timestamp)

-- По дням
DATE_TRUNC('day', date)
-- или просто
date::DATE

-- По неделям
DATE_TRUNC('week', date)

-- По месяцам
DATE_TRUNC('month', date)

-- По кварталам
DATE_TRUNC('quarter', date)

-- По годам
DATE_TRUNC('year', date)
```

---

### Pattern 3: Сравнение периодов (г/г, м/м)

```sql
-- Сравнение год к году
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

**Используй LAG/LEAD для сравнений:**
```sql
-- Предыдущее значение
LAG(value, 1) OVER (ORDER BY date)

-- Следующее значение
LEAD(value, 1) OVER (ORDER BY date)

-- Год назад (12 месяцев)
LAG(value, 12) OVER (ORDER BY date)

-- Месяц назад
LAG(value, 1) OVER (PARTITION BY year ORDER BY month)
```

---

### Pattern 4: Процентное распределение

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

**Window functions для процентов:**
```sql
-- Процент от общего
SUM(amount)::numeric / SUM(SUM(amount)) OVER () * 100

-- Процент от группы
SUM(amount)::numeric / SUM(SUM(amount)) OVER (PARTITION BY category) * 100

-- Накопительный процент (running total %)
SUM(SUM(amount)) OVER (ORDER BY region)::numeric / SUM(SUM(amount)) OVER () * 100
```

---

### Pattern 5: Скользящие средние (moving average)

```sql
-- Скользящее среднее за 7 дней
SELECT
  date AS date,
  SUM(amount) AS revenue,
  ROUND(
    AVG(SUM(amount)) OVER (
      ORDER BY date
      ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )::numeric,
    2
  ) AS ma7
FROM sales
GROUP BY date
ORDER BY date
```

**Варианты окон:**
```sql
-- 7 дней назад
ROWS BETWEEN 6 PRECEDING AND CURRENT ROW

-- 30 дней назад
ROWS BETWEEN 29 PRECEDING AND CURRENT ROW

-- 3 месяца назад
ROWS BETWEEN 2 PRECEDING AND CURRENT ROW  -- если GROUP BY month

-- Центрированное окно (+-3 дня)
ROWS BETWEEN 3 PRECEDING AND 3 FOLLOWING
```

---

### Pattern 6: Cohort Analysis (когортный анализ)

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
    c.cohort_month AS cohort_month,
    DATE_TRUNC('month', o.order_date) AS activity_month,
    EXTRACT(MONTH FROM AGE(o.order_date, c.cohort_month))::INTEGER AS months_since_reg,
    COUNT(DISTINCT o.user_id) AS active_users
  FROM cohorts c
  LEFT JOIN orders o ON c.user_id = o.user_id
  GROUP BY c.cohort_month, activity_month
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

## Semantic Layer: alias и описания

### НЕ используй русские AS в исходных полях!

**НЕПРАВИЛЬНО:**
```sql
SELECT region AS "Регион" FROM sales
-- Проблема: поле name = "Регион" (русское), ломает ссылки
```

**ПРАВИЛЬНО:**
```sql
SELECT region FROM sales
-- В БД: name = "region"
-- Потом через modusbi-mcp:
mcp__modusbi__dataset_operations(
  action="update",
  field_aliases={
    "region": {
      "alias": "Регион",              # Для легенд
      "description": "Географический регион РФ"  # Для LLM
    }
  }
)
```

### Финальный SELECT для визуализации в MCP

**Даже в финальном SELECT лучше сохранять технические имена:**
```sql
SELECT
  region AS region,
  COUNT(*) AS accident_count,
  SUM(dead_count) AS dead_count
FROM accidents
GROUP BY region
```

**Но лучше:**
1. Сохранить оригинальные имена в датасете
2. Задать alias через API (field_aliases)
3. LLM будет использовать правильные имена

---

## Типы данных для BI

### Обеспечивай правильные типы

```sql
-- Целые числа
COUNT(*)::INTEGER
EXTRACT(HOUR FROM dt)::INTEGER

-- Числа с плавающей точкой (для расчётов)
AVG(amount::numeric)
SUM(amount)::numeric / SUM(total)::numeric

-- Проценты (умножить на 100!)
ROUND((part::numeric / total) * 100, 2) AS percent

-- Даты (не timestamp для группировки!)
DATE_TRUNC('day', timestamp)::DATE

-- Строки (для категорий)
region::TEXT
```

---

## Фильтрация данных

### WHERE vs HAVING

**WHERE** — фильтр ДО агрегации:
```sql
SELECT region, SUM(amount)
FROM sales
WHERE date >= '2024-01-01'  -- Фильтр строк
GROUP BY region
```

**HAVING** — фильтр ПОСЛЕ агрегации:
```sql
SELECT region, SUM(amount) as revenue
FROM sales
GROUP BY region
HAVING SUM(amount) > 1000000  -- Фильтр групп
```

**Пример комбинации:**
```sql
SELECT
  region AS region,
  SUM(amount) AS revenue
FROM sales
WHERE date >= '2024-01-01'           -- Только 2024
  AND amount > 0                      -- Положительные суммы
  AND region IS NOT NULL              -- Не NULL
GROUP BY region
HAVING SUM(amount) > 1000000          -- Выручка >1M
ORDER BY SUM(amount) DESC
LIMIT 10
```

---

## Продвинутые паттерны

### Pattern 7: Cumulative (накопительный итог)

```sql
-- Running total (нарастающий итог)
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(amount) AS monthly_revenue,
  SUM(SUM(amount)) OVER (
    ORDER BY DATE_TRUNC('month', date)
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_revenue
FROM sales
WHERE date >= '2024-01-01'
GROUP BY DATE_TRUNC('month', date)
ORDER BY DATE_TRUNC('month', date)
```

---

### Pattern 8: Pivot (развёртка данных)

```sql
-- Продажи по регионам и категориям (crosstab)
SELECT
  region AS region,
  SUM(CASE WHEN category = 'Электроника' THEN amount ELSE 0 END) AS electronics_revenue,
  SUM(CASE WHEN category = 'Одежда' THEN amount ELSE 0 END) AS clothes_revenue,
  SUM(CASE WHEN category = 'Продукты' THEN amount ELSE 0 END) AS food_revenue,
  SUM(amount) AS total_revenue
FROM sales
WHERE date >= '2024-01-01'
GROUP BY region
ORDER BY SUM(amount) DESC
```

---

### Pattern 9: Percentiles (перцентили)

```sql
-- Распределение времени доставки
SELECT
  'p50 (медиана)' AS metric,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_days) AS days_value
FROM orders

UNION ALL

SELECT 'p95', PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY delivery_days)
FROM orders

UNION ALL

SELECT 'p99', PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY delivery_days)
FROM orders

ORDER BY days_value
```

**Результат:**
```
p50: 2.3 дня (половина быстрее)
p95: 5.7 дней (95% быстрее)
p99: 8.2 дней (проблемы у 1%)
```

---

### Pattern 10: Correlation (корреляция)

```sql
-- Корреляция между временем доставки и NPS
SELECT
  ROUND(CORR(delivery_days, nps_score)::numeric, 3) AS correlation,
  COUNT(*) AS sample_size
FROM orders
WHERE delivery_days IS NOT NULL
  AND nps_score IS NOT NULL
```

**Интерпретация:**
```
r = -0.72  -> Сильная отрицательная (доставка вверх -> NPS вниз)
r = 0.45   -> Средняя положительная
r = 0.12   -> Слабая (почти нет связи)
```

---

## Оптимизация для больших данных

### 1. Используй индексы (в WHERE и JOIN)

```sql
-- Плохо: full table scan
SELECT * FROM sales WHERE EXTRACT(YEAR FROM date) = 2024

-- Хорошо: использует индекс
SELECT * FROM sales WHERE date >= '2024-01-01' AND date < '2025-01-01'
```

### 2. LIMIT ВСЕГДА для топ-N

```sql
-- НЕ ДЕЛАЙ ТАК (вернёт миллион строк!)
SELECT region, SUM(amount)
FROM sales
GROUP BY region
ORDER BY SUM(amount) DESC

-- ДЕЛАЙ ТАК
SELECT region, SUM(amount)
FROM sales
GROUP BY region
ORDER BY SUM(amount) DESC
LIMIT 15  -- Только топ-15
```

### 3. Подзапросы vs JOIN

**Для фильтрации — используй EXISTS:**
```sql
-- Быстрее для больших таблиц
SELECT *
FROM clients c
WHERE EXISTS (
  SELECT 1 FROM orders o
  WHERE o.client_id = c.id
    AND o.date >= '2024-01-01'
)
```

---

## Антипаттерны (чего избегать)

### SELECT * в production

```sql
-- Плохо
SELECT * FROM sales  -- Вернёт все 50 колонок!

-- Хорошо
SELECT id, date, amount, region FROM sales
```

### Неэффективные подзапросы

```sql
-- Плохо (выполнится N раз!)
SELECT
  region,
  (SELECT AVG(amount) FROM sales) AS avg_all
FROM sales
GROUP BY region

-- Хорошо (выполнится 1 раз)
WITH avg_all AS (
  SELECT AVG(amount) AS avg FROM sales
)
SELECT
  region,
  (SELECT avg FROM avg_all) AS avg_all
FROM sales
GROUP BY region
```

### DISTINCT без понимания

```sql
-- Плохо (медленно + возможно неправильно)
SELECT DISTINCT region FROM sales

-- Хорошо (если нужен список уникальных)
SELECT region FROM sales GROUP BY region

-- Ещё лучше (если нужно с агрегацией)
SELECT region, COUNT(*) FROM sales GROUP BY region
```

---

## Best Practices для BI SQL

### 1. Всегда добавляй фильтр даты

```sql
-- Хорошо: ограничиваем период
WHERE date >= '2024-01-01' AND date < '2025-01-01'

-- Плохо: весь архив (может быть 10 лет данных!)
-- Нет WHERE date
```

### 2. Проверяй EXPLAIN ANALYZE

```sql
EXPLAIN ANALYZE
SELECT region, SUM(amount)
FROM sales
WHERE date >= '2024-01-01'
GROUP BY region;

-- Смотри:
-- Execution Time: должно быть <1000ms
-- Rows: сколько строк обработано
-- Index Scan vs Seq Scan (индекс лучше)
```

### 3. Используй CTE для читаемости

```sql
-- Хорошо (читаемо)
WITH monthly_sales AS (
  SELECT
    DATE_TRUNC('month', date) AS month,
    region,
    SUM(amount) AS revenue
  FROM sales
  WHERE date >= '2024-01-01'
  GROUP BY DATE_TRUNC('month', date), region
),
region_totals AS (
  SELECT region, SUM(revenue) AS total
  FROM monthly_sales
  GROUP BY region
)
SELECT
  ms.month AS month,
  ms.region AS region,
  ms.revenue AS revenue,
  ROUND(ms.revenue::numeric / rt.total * 100, 2) AS region_share_pct
FROM monthly_sales ms
JOIN region_totals rt ON ms.region = rt.region
ORDER BY ms.month, ms.revenue DESC
```

---

## Обработка специфичных типов данных

### Работа с JSON

```sql
-- Извлечение из JSON
SELECT
  data->>'name' AS name,
  (data->>'age')::INTEGER AS age,
  data->'address'->>'city' AS city
FROM users
WHERE data->>'status' = 'active'
```

### Работа с arrays

```sql
-- Развернуть массив
SELECT
  id,
  UNNEST(tags) AS tag
FROM products

-- Фильтр по массиву
WHERE 'electronics' = ANY(tags)

-- Размер массива
ARRAY_LENGTH(tags, 1) AS tags_count
```

### Работа с датами и временем

```sql
-- Части даты
EXTRACT(YEAR FROM date)::INTEGER AS year
EXTRACT(MONTH FROM date)::INTEGER AS month
EXTRACT(DAY FROM date)::INTEGER AS day
EXTRACT(HOUR FROM timestamp)::INTEGER AS hour
EXTRACT(DOW FROM date)::INTEGER AS day_of_week  -- 0=Sunday, 6=Saturday

-- Форматирование
TO_CHAR(date, 'YYYY-MM-DD') AS date_label
TO_CHAR(date, 'Month YYYY') AS month_label
TO_CHAR(timestamp, 'HH24:MI:SS') AS time_label

-- Интервалы
date + INTERVAL '7 days'
date - INTERVAL '1 month'
NOW() - INTERVAL '90 days'

-- Возраст
AGE(NOW(), birth_date) AS age
EXTRACT(YEAR FROM AGE(NOW(), birth_date))::INTEGER AS age_years
```

---

## Валидация SQL для BI

### Чек-лист перед выполнением

**Проверь:**
- [ ] Есть ORDER BY (если важен порядок)
- [ ] Есть LIMIT (для топ-N или больших таблиц)
- [ ] ::INTEGER для EXTRACT (чистые числа)
- [ ] ROUND для AVG и процентов (не более 2 знаков)
- [ ] Технические AS-имена (`snake_case`); русские подписи через `dataset_operations(field_aliases=...)`
- [ ] WHERE date (ограничить период)
- [ ] IS NOT NULL (фильтр пустых)
- [ ] GROUP BY соответствует SELECT (нет ошибок)

**Performance:**
- [ ] Нет SELECT * (только нужные поля)
- [ ] Используются индексы (WHERE на indexed поля)
- [ ] Нет коррелированных подзапросов
- [ ] EXPLAIN time <1000ms

---

## Библиотека готовых запросов

### Запрос 1: Basic aggregation

```sql
-- Агрегация с группировкой
SELECT
  {category_field} AS category_value,
  COUNT(*) AS count_value,
  SUM({value_field}) AS sum_value,
  ROUND(AVG({value_field}::numeric), 2) AS avg_value,
  MIN({value_field}) AS min_value,
  MAX({value_field}) AS max_value
FROM {table}
WHERE {date_field} >= '{start_date}'
  AND {category_field} IS NOT NULL
GROUP BY {category_field}
ORDER BY SUM({value_field}) DESC
LIMIT 20
```

---

### Запрос 2: Time series with YoY comparison

```sql
SELECT
  DATE_TRUNC('month', {date_field}) AS month,
  SUM({value_field}) AS current_value,
  LAG(SUM({value_field}), 12) OVER (ORDER BY DATE_TRUNC('month', {date_field})) AS previous_year_value,
  ROUND(
    ((SUM({value_field}) - LAG(SUM({value_field}), 12) OVER (ORDER BY DATE_TRUNC('month', {date_field})))
     / NULLIF(LAG(SUM({value_field}), 12) OVER (ORDER BY DATE_TRUNC('month', {date_field})), 0) * 100)::numeric,
    2
  ) AS yoy_growth_pct
FROM {table}
WHERE {date_field} >= NOW() - INTERVAL '24 months'
GROUP BY DATE_TRUNC('month', {date_field})
ORDER BY DATE_TRUNC('month', {date_field})
```

---

### Запрос 3: Distribution analysis

```sql
-- Квантили и распределение
SELECT
  'Минимум' AS metric,
  MIN({value_field}) AS value
FROM {table}

UNION ALL
SELECT 'p25', PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {value_field})
FROM {table}

UNION ALL
SELECT 'Медиана (p50)', PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {value_field})
FROM {table}

UNION ALL
SELECT 'p75', PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {value_field})
FROM {table}

UNION ALL
SELECT 'p95', PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY {value_field})
FROM {table}

UNION ALL
SELECT 'Максимум', MAX({value_field})
FROM {table}

UNION ALL
SELECT 'Среднее', ROUND(AVG({value_field}::numeric), 2)
FROM {table}

ORDER BY value
```

---

### Запрос 4: Outlier detection (поиск выбросов)

```sql
WITH stats AS (
  SELECT
    AVG({value_field}) AS mean,
    STDDEV({value_field}) AS std
  FROM {table}
  WHERE {date_field} >= '{start_date}'
)
SELECT
  {id_field},
  {category_field} AS category,
  {value_field} AS value,
  ROUND(({value_field} - stats.mean) / stats.std, 2) AS z_score
FROM {table}, stats
WHERE {date_field} >= '{start_date}'
  AND ABS(({value_field} - stats.mean) / stats.std) > 2  -- Outliers: |z| > 2
ORDER BY ABS(({value_field} - stats.mean) / stats.std) DESC
LIMIT 20
```

---

### Запрос 5: Funnel conversion

```sql
-- Воронка с конверсией между этапами
WITH funnel AS (
  SELECT
    stage,
    stage_order,
    COUNT(*) AS count
  FROM user_funnel
  GROUP BY stage, stage_order
)
SELECT
  stage AS stage,
  count AS count_value,
  LAG(count) OVER (ORDER BY stage_order) AS previous_stage_count,
  ROUND(
    count::numeric / NULLIF(LAG(count) OVER (ORDER BY stage_order), 0) * 100,
    2
  ) AS conversion_pct
FROM funnel
ORDER BY stage_order
```

---

## Примеры для разных типов графиков

### Bar Chart (столбчатая диаграмма)

**Требования:**
- category_field: категория (регион, товар)
- value_field: числовое значение
- ORDER BY value DESC (сортировка по значению)
- LIMIT 10-15 (не более)

```sql
SELECT
  region AS region,
  SUM(amount) AS revenue
FROM sales
WHERE date >= '2024-01-01'
GROUP BY region
ORDER BY SUM(amount) DESC
LIMIT 10
```

---

### Line Chart (линейный график)

**Требования:**
- x_axis: дата/время (обязательно ORDER BY!)
- y_axis: числовое значение
- Несколько линий: PIVOT или multiple value fields

```sql
SELECT
  DATE_TRUNC('month', date) AS month,
  SUM(amount) AS revenue,
  COUNT(*) AS order_count
FROM sales
WHERE date >= '2024-01-01'
GROUP BY DATE_TRUNC('month', date)
ORDER BY DATE_TRUNC('month', date)  -- ОБЯЗАТЕЛЬНО!
```

---

### Pie Chart (круговая диаграмма)

**Требования:**
- category: категория
- value: числовое (обычно процент или сумма)
- ORDER BY value DESC
- LIMIT 5-8 (не более, иначе нечитаемо)

```sql
SELECT
  category AS category,
  SUM(amount) AS revenue,
  ROUND(SUM(amount)::numeric / SUM(SUM(amount)) OVER () * 100, 1) AS share_pct
FROM sales
WHERE date >= '2024-01-01'
GROUP BY category
ORDER BY SUM(amount) DESC
LIMIT 7
```

---

### Table (таблица)

**Требования:**
- Выбирай только нужные колонки (не SELECT *)
- Сортировка по главному полю
- LIMIT 100-200 (таблицы не должны быть огромными в дашборде)

```sql
SELECT
  date::DATE AS order_date,
  client AS client,
  product AS product,
  amount AS amount,
  status AS status
FROM orders
WHERE date >= '2024-12-01'
ORDER BY date DESC, amount DESC
LIMIT 100
```

---

## Debugging SQL для BI

### Частые проблемы и решения

**Проблема 1: Неправильная сортировка**
```sql
-- Не работает: ORDER BY в подзапросе игнорируется
SELECT * FROM (
  SELECT region, SUM(amount)
  FROM sales
  GROUP BY region
  ORDER BY SUM(amount) DESC  -- Игнорируется!
) AS subquery

-- Работает: ORDER BY в финальном SELECT
SELECT region, revenue
FROM (
  SELECT region, SUM(amount) AS revenue
  FROM sales
  GROUP BY region
) AS subquery
ORDER BY revenue DESC  -- Работает
```

**Проблема 2: Division by zero**
```sql
-- Может упасть если total = 0
SELECT part / total * 100

-- Безопасно
SELECT
  ROUND(part::numeric / NULLIF(total, 0) * 100, 2)
```

**Проблема 3: Агрегация без GROUP BY**
```sql
-- Ошибка!
SELECT region, SUM(amount)
FROM sales
-- Забыли GROUP BY region

-- Правильно
SELECT region, SUM(amount)
FROM sales
GROUP BY region
```

---

## MCP Integration: Генерация SQL через LLM

### Промпт для генерации BI SQL

```python
def generate_bi_sql(question: str, table: str, schema: dict) -> str:
    """
    Генерирует SQL для BI дашборда с учётом всех best practices
    """
    prompt = f"""
    Сгенерируй PostgreSQL запрос для BI дашборда.

    Таблица: {table}
    Схема: {json.dumps(schema)}
    Вопрос: {question}

    ОБЯЗАТЕЛЬНЫЕ ТРЕБОВАНИЯ:

    1. ORDER BY если нужна сортировка (часы, месяцы, топ-N)
    2. ::INTEGER для EXTRACT(HOUR/MONTH/...)
    3. ROUND(..., 2) для AVG и процентов
    4. Технические AS-имена (`snake_case`); русские подписи задаются через dataset_operations(field_aliases)
    5. WHERE для фильтра по дате
    6. IS NOT NULL для фильтра пустых
    7. LIMIT для топ-N

    Примеры:

    Вопрос: "Топ-10 регионов"
    SELECT
      region AS region,
      SUM(amount) AS revenue
    FROM sales
    WHERE date >= '2024-01-01'
    GROUP BY region
    ORDER BY SUM(amount) DESC
    LIMIT 10

    Вопрос: "Динамика по месяцам"
    SELECT
      DATE_TRUNC('month', date) AS month,
      SUM(amount) AS revenue
    FROM sales
    WHERE date >= '2024-01-01'
    GROUP BY DATE_TRUNC('month', date)
    ORDER BY DATE_TRUNC('month', date)

    Теперь для вопроса: {question}
    """

    return llm.generate(prompt, temperature=0.1)  # Low temp для точности
```

---

## Quick Validation Checklist

Перед созданием датасета из SQL проверь:

**Syntax:**
- [ ] Запрос валиден (не будет SQL error)
- [ ] Все поля существуют в таблице
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

## Шаблоны для типовых задач

### Top-N анализ
```sql
SELECT {category}, SUM({value})
FROM {table}
WHERE {date} >= '{start}'
  AND {category} IS NOT NULL
GROUP BY {category}
ORDER BY SUM({value}) DESC
LIMIT {N}
```

### Time series
```sql
SELECT DATE_TRUNC('{period}', {date}), SUM({value})
FROM {table}
WHERE {date} >= '{start}'
GROUP BY DATE_TRUNC('{period}', {date})
ORDER BY DATE_TRUNC('{period}', {date})
```

### Comparison
```sql
SELECT
  {category},
  SUM(CASE WHEN {date} >= '{period1_start}' AND {date} < '{period1_end}'
      THEN {value} END) AS period_1_value,
  SUM(CASE WHEN {date} >= '{period2_start}' AND {date} < '{period2_end}'
      THEN {value} END) AS period_2_value
FROM {table}
GROUP BY {category}
ORDER BY period_2_value DESC
```

---

*Используй этот skill для генерации правильных SQL запросов для BI дашбордов*
