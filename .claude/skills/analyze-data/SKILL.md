---
name: analyze-data
description: Проводит глубокий анализ данных с проверкой гипотез, поиском корреляций и формированием бизнес-выводов Level 4 (prescriptive analytics). Используйте когда пользователь просит "проанализировать", "найти причину", "проверить гипотезу", "понять почему". Автоматически исследует данные через postgres-mcp, создаёт визуализацию через modusbi-mcp, генерирует actionable рекомендации с quantified impact.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi, playwright
---

# Analyze Data: Глубокий анализ с выводами

## Overview

Этот skill проводит комплексный анализ данных и формулирует **Level 4 выводы** (prescriptive analytics) — не просто "что произошло", а "что делать" с quantified impact оценкой.

**Ключевые возможности:**
- 🔍 Исследование сырых данных (PostgreSQL/ClickHouse через postgres-mcp)
- 📊 Проверка гипотез с statistical significance
- 📈 Поиск корреляций и паттернов
- 🎯 Root Cause Analysis (поиск главной причины)
- 💡 Формулирование actionable рекомендаций
- 📉 Quantified impact оценка (в деньгах/времени)
- 📸 Визуальная верификация результатов через playwright (скриншоты дашбордов)


---

## When to Use This Skill

Используй этот skill когда пользователь:

- ✅ Просит **"проанализировать"** данные/метрики
- ✅ Спрашивает **"почему"** метрика изменилась
- ✅ Хочет **"найти причину"** падения/роста
- ✅ Просит **"проверить гипотезу"** (A влияет на B?)
- ✅ Спрашивает **"что с этим делать"**
- ✅ Нужны **рекомендации** на основе данных
- ✅ Упоминает **"корреляция"**, **"тренд"**, **"паттерн"**

**Триггерные фразы:**
- "Почему упали продажи в Q3?"
- "Найди причину падения конверсии"
- "Проверь: снегопад влияет на ДТП?"
- "Что делать с оттоком клиентов?"
- "Проанализируй корреляцию доставки и NPS"

---

## Standard Workflow (6 этапов)

### Этап 1: Исследование данных (postgres-mcp)

**Если источник — таблица PostgreSQL:**

```python
# 1.1 Получить схему таблицы
schema = postgres_mcp.describe_table("sales")
# → Поля: date, region, amount, category, ...

# 1.2 Примеры данных (spot-check!)
sample = postgres_mcp.query("""
    SELECT * FROM sales
    WHERE date >= '2024-10-01'
    LIMIT 10
""")

# 1.3 Базовая статистика
stats = postgres_mcp.query("""
    SELECT
        COUNT(*) as total_rows,
        MIN(date) as period_start,
        MAX(date) as period_end,
        SUM(amount) as total_revenue,
        COUNT(DISTINCT region) as regions
    FROM sales
    WHERE date >= '2024-01-01'
""")
```

**Важно:** Всегда делай spot-check данных перед анализом! 

---

### Этап 2: Формулирование гипотез (Root Cause Analysis)

**4 категории гипотез**:

1. **Продуктовая** (изменения в продукте):
   ```sql
   -- Проверить: не было ли релиза/бага?
   SELECT date, COUNT(*) as orders
   FROM sales
   GROUP BY date
   ORDER BY date
   -- Ищем резкие изменения
   ```

2. **Рыночная** (конкуренты, тренды):
   ```sql
   -- Проверить: падение везде или только у нас?
   SELECT region, SUM(amount) as revenue,
          LAG(SUM(amount), 1) OVER (PARTITION BY region ORDER BY month) as prev_month
   FROM sales
   GROUP BY region, month
   ```

3. **Пользовательская** (изменение аудитории):
   ```sql
   -- Проверить: новые когорты vs старые
   SELECT cohort, AVG(ltv) as ltv
   FROM customers
   GROUP BY cohort
   ```

4. **Внешняя** (сезонность, события):
   ```sql
   -- Проверить: сезонный паттерн?
   SELECT month, AVG(revenue) as avg_revenue
   FROM monthly_sales
   GROUP BY month
   ORDER BY month
   ```

---

### Этап 3: Проверка гипотез (Statistical Analysis)

**Для каждой гипотезы:**

```python
# 1. Собрать данные
data = postgres_mcp.query(hypothesis_sql)

# 2. Вычислить статистику
if analysis_type == "correlation":
    r = postgres_mcp.query("""
        SELECT CORR(x, y) as r, COUNT(*) as n
        FROM data
    """)
    # r = -0.72, n = 5,234

    # 3. Проверить significance
    # |r| > 0.7 → strong correlation
    # n > 30 → sufficient sample

    # 4. Интерпретация
    interpretation = f"""
    Корреляция: r = {r:.2f} ({'сильная' if abs(r) > 0.7 else 'средняя'})
    Sample size: {n:,} ✅ (достаточно для выводов)

    Практический вывод:
    Каждая единица X изменения → {slope:.2f} изменение Y
    """

elif analysis_type == "comparison":
    # t-test or ANOVA
    ...
```

**Check (обязательно!):**
- [ ] Sample size достаточен (n > 30 минимум, лучше >100)
- [ ] p-value < 0.05 (statistical significance)
- [ ] Effect size >10% (practical significance)
- [ ] Confounding factors проверены

---

### Этап 4: Визуализация (modusbi-mcp)

```python
# 4.1 Создать датасет с правильным SQL
dataset_result = mcp__modusbi__dataset_create_from_sql(
    sql_query="""
        SELECT
            region,
            SUM(amount) AS revenue,
            ROUND(AVG(margin::numeric), 2) AS margin_pct
        FROM sales
        WHERE date >= '2024-01-01'
          AND region IS NOT NULL
        GROUP BY region
        ORDER BY SUM(amount) DESC  -- ОБЯЗАТЕЛЬНО для правильной сортировки!
        LIMIT 10
    """,
    datasource_id=27,
    name="sales_by_region_2024"
)
dataset_id = dataset_result["dataset"]["id"]

# Aliases задаются отдельным update ДО привязки датасета к компонентам
mcp__modusbi__dataset_operations(
    action="update",
    dataset_id=dataset_id,
    field_aliases={
        "region": {"alias": "Регион"},
        "revenue": {"alias": "Выручка (руб.)"},
        "margin_pct": {"alias": "Маржа (%)"}
    }
)

# 4.2 Создать дашборд с графиком + выводом
mcp__modusbi__component_crud(action="add_chart_with_conclusion",
    report_id=report_id,
    component_type="HsBarAMchartsChart",  # Выбор типа из @bi-visualization-expert
    title="Топ-10 регионов по продажам",
    dataset_id=dataset_id,
    category_field="region",  # ТЕХНИЧЕСКОЕ имя (не "Регион"!)
    value_field="revenue",    # ТЕХНИЧЕСКОЕ имя
    text_content=level4_narrative  # Вывод (см. этап 5)
)
```

**Важно:** Используй ТЕХНИЧЕСКИЕ названия полей (из SQL), не aliases!

---

### Этап 5: Формулирование Level 4 вывода

**Обязательная структура** (из skill `/data-analyst-expert`):

```markdown
## АНАЛИЗ: [название]

**Главная метрика:** [число] ([изменение] к [baseline])

### КЛЮЧЕВЫЕ НАБЛЮДЕНИЯ
• [наблюдение 1 с цифрами]
• [наблюдение 2 с цифрами]
• [наблюдение 3 с цифрами]

### ДРАЙВЕРЫ РОСТА
1. [Фактор] — [вклад %] ([объяснение почему])
2. [Фактор] — [вклад %] ([объяснение])
3. [Фактор] — [вклад %] ([объяснение])

### ЗОНЫ РИСКА
• [Проблема] — [масштаб] ([последствия в ₽/времени])
• [Проблема] — [масштаб] ([последствия])

### ПРИОРИТЕТНЫЕ ДЕЙСТВИЯ

**[КРИТИЧНО]** [Конкретное действие, не общее!]
   Дедлайн: [реалистичная дата, не "скоро"]
   Impact: [количественно: сколько ₽ или человеко-часов]
   Ответственный: [команда/роль]

**[ВЫСОКИЙ]** [Действие 2]
   Дедлайн: [дата]
   Impact: [количественно]

**[СРЕДНИЙ]** [Действие 3]
   Дедлайн: [дата]
   Impact: [количественно]

### ПРОГНОЗ
[Что будет если выполнить рекомендации] → [quantified outcome]
```

**HTML форматирование:**
```html
<div style="background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            padding: 20px; border-radius: 10px;
            border-left: 5px solid #1976d2;">
    <h2 style="color: #0d47a1;">📊 [ЗАГОЛОВОК]</h2>
    [Вывод по структуре выше]
</div>
```

**Цвета:**
- 🟢 #4caf50 — позитив (рост, success)
- 🔴 #f44336 — риск (падение, alert)
- 🔵 #1976d2 — нейтрально (информация)

---

### Этап 6: Визуальная верификация (playwright)

⚠️ SINGLE-SESSION: выполняй ПОСЛЕ всех modusbi API-операций (этапы 1-5) — НЕ чередуй браузер и API
(switch сбрасывает сессию). Креды для логина — из `.env` (MODUSBI_E2E_*), не инлайн.
⚠️ Имена tools ниже — иллюстративные; реальные: `mcp__playwright__browser_navigate(url=...)`,
`mcp__playwright__browser_evaluate(...)`, `mcp__playwright__browser_take_screenshot(...)`.

После создания визуализаций проверь результат через скриншот:

```python
# 1. Открыть дашборд с результатами анализа
browser_navigate(f"${MODUSBI_URL}/report/{report_id}")

# 2. Подождать рендеринг графиков
browser_evaluate("await new Promise(r => setTimeout(r, 3000))")

# 3. Скриншот для верификации
browser_take_screenshot(name=f"analysis_dashboard_{report_id}")

# 4. Проверить визуально:
# - Графики отрисовались (не пустые)
# - Данные корректны (сортировка, масштаб осей)
# - Текстовый блок с выводом читаемый
# - Layout не перекрывается
# - Цвета семантически верные (зелёный=позитив, красный=негатив)

# 5. При необходимости — скриншот конкретного компонента
browser_take_screenshot(
    name="correlation_scatter",
    selector=".hs-chart-container:nth-child(2)"  # Второй график
)
```

**Если проблемы:**
- График пустой → проверить dataset_id и SQL
- Данные не сортированы → добавить ORDER BY в SQL
- Компоненты наложились → пересчитать position (x, y, w, h)

---

## Common Patterns

### Pattern 1: Проверка одной гипотезы

**User input:**
```
/analyze-data dtp.accidents "снегопад влияет на тяжесть ДТП?"
```

**Workflow:**
```python
# 1. Данные
result = postgres_mcp.query("""
    SELECT
        weather_condition AS weather_condition,
        COUNT(*) AS accident_count,
        ROUND(AVG(injured_count)::numeric, 2) AS avg_injured_count
    FROM dtp.accidents
    WHERE weather_condition IS NOT NULL
    GROUP BY weather_condition
    ORDER BY AVG(injured_count) DESC
""")

# 2. Статистический тест (ANOVA для >2 групп)
# [вычисление F-statistic, p-value]

# 3. Визуализация
dataset = mcp__modusbi__dataset_create_from_sql(...)
component = mcp__modusbi__component_crud(action="add_chart_with_conclusion", ...)

# 4. Вывод
"""
✅ ГИПОТЕЗА ПОДТВЕРЖДЕНА

Снегопад увеличивает тяжесть ДТП на 23%:
• При снегопаде: 1.40 раненых/ДТП
• В ясную погоду: 1.14 раненых/ДТП

Статистически значимо: p < 0.001 (ANOVA)
Sample size: 56,671 ДТП

РЕКОМЕНДАЦИЯ:
[КРИТИЧНО] Усилить патрулирование при снегопаде на участках:
- КАД (км 15-25)
- Выборгское шоссе
- Пулковское шоссе

Impact: Потенциально -50 раненых/зиму
"""
```

---

### Pattern 2: Root Cause Analysis (поиск причины)

**User input:**
```
/analyze-data sales_2024 "почему упали продажи в Q3 на 12%?"
```

**Workflow:**
```python
# 1. Проверить гипотезы по категориям

# Гипотеза 1: Конкретный регион?
by_region = postgres_mcp.query("""
    SELECT region,
           SUM(CASE WHEN quarter = 'Q3' THEN amount END) as q3,
           SUM(CASE WHEN quarter = 'Q2' THEN amount END) as q2,
           ROUND((q3 - q2) / q2 * 100, 2) as change_pct
    FROM sales_2024
    GROUP BY region
    HAVING change_pct < -10
""")
# → Найдено: Сибирь -13.6%

# Гипотеза 2: Конкретный клиент в Сибири?
by_client = postgres_mcp.query("""
    SELECT client, SUM(amount) as revenue
    FROM sales_2024
    WHERE region = 'Сибирь' AND quarter = 'Q3'
    GROUP BY client
    ORDER BY revenue DESC
""")
# → "Газпром": 0 ₽ (было 5.2M/квартал) ✅ ПРИЧИНА!

# 2. Quantify impact
impact = 5.2M / total_revenue  # 13% от региона, 3.3% от общей

# 3. Визуализация + вывод
# [создать дашборд с графиками по регионам и клиентам]

# 4. Вывод Level 4
"""
ROOT CAUSE: Потеря клиента "Газпром" в регионе Сибирь

Impact:
• -5.2M ₽/квартал
• -13% от региона
• -3.3% от общей выручки

Equivalent: Нужно найти 150 средних клиентов для компенсации

ДЕЙСТВИЯ:
[КРИТИЧНО] Найти замену крупному клиенту в Сибири
   Дедлайн: до 15 февраля
   Impact: восстановление 5.2M ₽/квартал
   Ответственный: отдел продаж Сибирь

[ВЫСОКИЙ] Диверсифицировать портфель (снизить зависимость от топ-3)
   Target: Топ-1 клиент <15% выручки (сейчас 23%)
   Impact: снижение риска

ПРОГНОЗ: Без действий → Q4 тоже -12%. С действиями → возврат к росту в Q1 2025.
"""
```

---

### Pattern 3: Correlation Analysis (корреляции)

**User input:**
```
/analyze-data orders "корреляция времени доставки и NPS"
```

**Workflow:**
```python
# 1. Вычислить корреляцию
corr_result = postgres_mcp.query("""
    SELECT
        ROUND(CORR(delivery_days, nps_score)::numeric, 3) AS r,
        COUNT(*) AS n,
        ROUND(REGR_SLOPE(nps_score, delivery_days)::numeric, 3) AS slope
    FROM orders
    WHERE delivery_days IS NOT NULL
      AND nps_score IS NOT NULL
""")
# → r = -0.72, n = 5,234, slope = -0.68

# 2. Проверка:
# - |r| > 0.7 → СИЛЬНАЯ корреляция ✅
# - n > 30 → достаточно данных ✅
# - Scatter plot визуально подтверждает линейную зависимость

# 3. Интерпретация (из skill /statistical-analysis):
interpretation = f"""
Корреляция: r = -0.72 (сильная отрицательная)
Slope: -0.68
→ Каждый день задержки → -0.68 пункта NPS

Текущая ситуация:
• Средняя доставка: 4.2 дня
• Средний NPS: 7.2

Целевая ситуация:
• Доставка 1-2 дня → NPS ~8.7
• Улучшение: +1.5 пункта

Business impact:
• +1.5 NPS → +12% retention (по бенчмаркам)
• 10,000 клиентов × 12% × 8,500₽ LTV = +10.2M ₽/год
"""

# 4. Визуализация
# [Scatter plot: delivery_days (X) vs NPS (Y) + regression line]

# 5. Вывод Level 4
"""
✅ КОРРЕЛЯЦИЯ ПОДТВЕРЖДЕНА

Время доставки КРИТИЧНО влияет на NPS (r=-0.72, p<0.001).

Каждый день задержки → -0.68 пункта NPS
Текущее: 4.2 дня, NPS 7.2
Целевое: 1-2 дня, NPS 8.7 (+1.5)

ДЕЙСТВИЯ:
[КРИТИЧНО] Оптимизировать логистику: SLA 1-2 дня
   Текущее: 4.2 дня среднее
   Цель: <2 дней для 80% заказов
   Дедлайн: март 2025
   Impact: +1.5 NPS → +12% retention → +10.2M ₽/год

[ВЫСОКИЙ] Проактивное уведомление при задержке >3 дней
   Impact: Снизить негативные reviews на 40%

ПРОГНОЗ: Достижение SLA → NPS 8.7 → industry leader
"""
```

---

## Best Practices

### 1. Всегда проверяй данные (spot-check)


Проводите ручные spot-проверки данных, не полагаясь слепо на инструменты

```python
# ❌ НЕ делай так:
data = query(complex_sql)
# Сразу анализируешь → можешь пропустить проблемы

# ✅ Делай так:
data = query(complex_sql)
print(f"Sample (first 10 rows):\n{data.head(10)}")
print(f"Stats: n={len(data)}, nulls={data.isnull().sum()}")
# Проверил данные → потом анализируешь
```

### 2. Понимай взаимосвязи метрик


Понимать взаимосвязи между метриками (если что-то растет, что-то должно снижаться)

**Пример:**
```python
# Если CAC (стоимость привлечения) вырос на 40%
# А количество клиентов выросло только на 10%
# → Эффективность маркетинга УПАЛА!

# Всегда смотри на ОТНОШЕНИЯ метрик, не только абсолютные значения
```

### 3. Baseline и сезонность

**Не сравнивай январь с декабрем!** (сезонность)

```sql
-- ❌ ПЛОХО: Month-over-month (м/м)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) as prev_month
-- Январь vs Декабрь = сезонный спад (не проблема!)

-- ✅ ХОРОШО: Year-over-year (г/г)
SELECT month, revenue,
       LAG(revenue, 12) OVER (ORDER BY month) as year_ago
-- Январь 2025 vs Январь 2024 = честное сравнение
```

### 4. Sample Size Validation

**Минимальные требования:**

| Анализ | Минимум |
|--------|---------|
| Простое среднее | n > 30 |
| Корреляция | n > 30 (лучше >100) |
| t-test (сравнение групп) | n > 30 в каждой |
| A/B тест (конверсия ~3%) | n > 1,000 в каждом варианте |
| Regression | n > 10 × количество предикторов |

```python
# Проверка перед анализом
if sample_size < minimum_required:
    return f"""
    ⚠️ НЕДОСТАТОЧНО ДАННЫХ

    Sample size: {sample_size}
    Минимум: {minimum_required}

    Рекомендация: Собрать больше данных или расширить период анализа
    """
```

### 5. Quantify Everything

**Все impact оценки в цифрах:**

❌ Плохо: "Это сильно повлияет на выручку"
✅ Хорошо: "Impact: +5.2M ₽/квартал (+13% от региона)"

❌ Плохо: "Сэкономит много времени"
✅ Хорошо: "Impact: -2 часа/день × 5 аналитиков × 22 дня = -220 ч/мес"

---

## Examples

### Example 1: Анализ падения конверсии

**Input:**
```
/analyze-data ecommerce "падение конверсии с 3.2% до 2.1%"
```

**Output:**
```markdown
## ROOT CAUSE ANALYSIS: Падение конверсии

**Главная метрика:** Конверсия 2.1% (было 3.2%, падение -34%)

### НАЙДЕНО 5 ПРИЧИН

[КРИТИЧНО] Банковская оплата: 15% отказов (было 3%)
• Начало: 12 декабря
• Причина: Проблема процессинга Сбербанка
• Impact: -0.7% конверсии = -1.2M ₽/месяц

[ВЫСОКИЙ] Скорость сайта: >3 сек загрузка
• 67% bounce rate (vs 35% при <2 сек)
• Impact: -0.5% конверсии = -850K ₽/месяц

[СРЕДНИЙ] Повышение цен на 8%
• Эластичность: -1.5
• Impact: -0.2% конверсии

### ПРИОРИТЕТНЫЕ ДЕЙСТВИЯ

**[КРИТИЧНО]** Подключить резервный payment gateway (Тинькофф)
   Дедлайн: СЕГОДНЯ (каждый день -40K ₽)
   Impact: восстановление 0.7% конверсии = 1.2M ₽/мес
   Ответственный: DevOps + Финансы

**[ВЫСОКИЙ]** Оптимизация фронтенда (CDN, lazy loading)
   Дедлайн: 2 недели
   Impact: 0.5% конверсии = 850K ₽/мес
   Бюджет: 300K ₽
   ROI: окупается за 11 дней

ПРОГНОЗ:
Фикс критичных (1-2) → возврат к 3.0% конверсии за 2 недели
→ восстановление 2M ₽/месяц
```

---

### Example 2: Cohort Analysis

**Input:**
```
/analyze-data users "retention по когортам регистрации"
```

**Output:**
```sql
-- SQL для cohort analysis
WITH cohorts AS (
    SELECT user_id,
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
    SELECT cohort_month, COUNT(*) AS size
    FROM cohorts
    GROUP BY cohort_month
)
SELECT
    a.cohort_month AS cohort_month,
    a.months_since_reg AS months_since_reg,
    ROUND(a.active_users::numeric / cs.size * 100, 1) AS retention_pct
FROM activities a
JOIN cohort_sizes cs ON a.cohort_month = cs.cohort_month
WHERE a.months_since_reg <= 12
ORDER BY a.cohort_month, a.months_since_reg
```

**Вывод:**
```markdown
## COHORT ANALYSIS: Retention

Лучшая когорта: Январь 2024 (retention 42% в месяц 12)
Худшая когорта: Июль 2024 (retention 14%)

ПАТТЕРН: Критический период 15-20 месяцев
• Увольняется 34% лучших сотрудников
• Без карьерного роста

ДЕЙСТВИЯ:
[КРИТИЧНО] Карьерные треки для 12-18 месяцев
   Impact: -10% текучести = сохранить 10 чел/год = 15M ₽ экономии
```

---

## Troubleshooting

### Issue: Недостаточно данных

**Symptom:** Sample size <30

**Solution:**
```python
if sample_size < minimum:
    return f"""
    ⚠️ НЕДОСТАТОЧНО ДАННЫХ

    Sample size: {sample_size}
    Минимум для надёжных выводов: {minimum}

    Опции:
    1. Расширить период анализа (вместо 1 месяца → 3 месяца)
    2. Агрегировать данные (вместо по дням → по неделям)
    3. Объединить малые группы (вместо 20 категорий → топ-10 + "Прочие")
    """
```

---

### Issue: Correlation без causation

**Symptom:** r высокий, но связь нелогична

**Solution:**
Проверь confounding factors (третьи переменные):

```python
# Корреляция мороженого и утоплений: r = 0.89
# НО: третий фактор — температура!

# Проверка:
partial_corr = control_for(temperature)
# → r становится ~0.1 (связи нет!)

# Вывод: "Ложная корреляция, обусловлена температурой"
```

---

### Issue: Statistical significance, но не practical

**Symptom:** p < 0.05, но effect size <1%

**Solution:**
```python
if p_value < 0.05 and effect_size < 0.01:
    return """
    ✅ Статистически значимо
    ❌ НЕ практически значимо

    Разница слишком мала для бизнес-impact.

    Рекомендация: Не внедрять (ROI низкий)
    """
```

---

## Reference Documentation

Детальные правила и методологии в SKILL:

- **/data-analyst-expert** — Level 4 выводы, RCA, SMART рекомендации
- **/sql-bi-expert** — SQL паттерны для BI (ORDER BY, типы, округление)
- **/statistical-analysis** — Статистические тесты, корреляции, p-value
- **/bi-visualization-expert** — Выбор типа графика, layout

---

## Important Notes


1. **Аналитическая интуиция** — разумные предположения при ограниченной информации
2. **Spot-проверки** — не слепо доверять инструментам
3. **Взаимосвязи метрик** — если X растёт, понимать что должно происходить с Y
4. **Baseline понимание** — учёт сезонности и ожидаемых значений

### Statistical Rigor

- Sample size >30 (минимум), >100 (желательно)
- p-value <0.05 для статистической значимости
- Effect size >10% для практической значимости
- Confounding factors всегда проверяем

### Level 4 = Цель

**Не останавливайся на Level 2-3!**

- Level 2: "Продажи выросли на 12%" ❌
- Level 4: "Действие 1,2,3 → прогноз +4.5M ₽" ✅

---

## DQ Profiling: Анализ качества данных

Когда пользователь просит проанализировать **качество данных**, **справочник**, **НСИ** или упоминает **DQ/DQM** — используй эту секцию дополнительно к основному workflow.

### DQ-метрики для анализа

| Метрика | SQL-паттерн | Описание |
|---------|-------------|----------|
| **Completeness** | `COUNT(field) / COUNT(*)` | % заполненных значений |
| **Uniqueness** | `COUNT(DISTINCT field) / COUNT(field)` | % уникальных значений |
| **Validity** | `COUNT(*) FILTER (WHERE field ~ pattern)` | % соответствия формату |
| **Timeliness** | `COUNT(*) FILTER (WHERE updated_at > threshold)` | % актуальных записей |

### Расчёт энтропии Шеннона

Энтропия показывает «грязность» поля: высокая энтропия в поле «Город» = много вариантов написания одного и того же.

```sql
WITH freq AS (
    SELECT "{field}", COUNT(*) AS cnt
    FROM {table} WHERE "{field}" IS NOT NULL GROUP BY "{field}"
),
probs AS (
    SELECT cnt::numeric / SUM(cnt) OVER () AS p FROM freq
)
SELECT ROUND(-SUM(p * LN(p) / LN(2))::numeric, 2) AS entropy_bits FROM probs;
```

### Генерация DQM-правил

На основе результатов профилирования **предложи DQM-правила валидации**:

| Тип правила | Когда предлагать | Формат |
|-------------|------------------|--------|
| **NOT NULL** | Completeness < 95% для ключевых полей | `WHERE field IS NULL` |
| **Format (regex)** | Validity < 90% | `WHERE field !~ '^pattern$'` |
| **Range** | Есть выбросы, min/max неадекватны | `WHERE field < min OR field > max` |
| **FK** | Есть ссылочные поля | `WHERE fk NOT IN (SELECT id FROM ref)` |
| **Uniqueness** | Uniqueness < 99% для ключей | `GROUP BY key HAVING COUNT(*) > 1` |
| **Business Logic** | Кросс-поля | `WHERE part1 + part2 != total` |

**Формат вывода правила:**
```
Правило: DQM-{N}: {Описание}
Тип: {NOT_NULL | FORMAT | RANGE | FK | UNIQUENESS | BUSINESS}
Поле: {field_name}
SQL: {SELECT ... WHERE нарушение}
Приоритет: {CRITICAL | HIGH | MEDIUM}
Порог: {0% | 5% | 10%} нарушений
```

### DQ-scorecard

Итоговая таблица (генерировать в конце DQ-анализа):

```
DQ Score = 0.30 * Completeness + 0.25 * Uniqueness + 0.25 * Validity + 0.20 * Consistency

Формула: weighted average по всем полям
Целевой: 90%+ для production
```

**Связь:** Для полного DQ-профилирования используй `/dq-profiler`.

---
