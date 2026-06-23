---
name: statistical-analysis
description: "Statistical Analysis Expert: статистические методы для BI аналитики. Используйте когда нужно проверить статистическую значимость, провести A/B тест, найти корреляции между метриками, выявить аномалии (outliers), сделать прогноз на основе данных, интерпретировать p-value и confidence intervals."
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: postgres, modusbi
---

# Statistical Analysis Expert: Статистические методы для аналитики

## 🎯 Назначение

Используй этот skill когда нужно:
- Проверить статистическую значимость результатов
- Провести A/B тест
- Найти корреляции между метриками
- Выявить аномалии (outliers)
- Сделать прогноз на основе данных

## 📊 Статистические тесты: когда что использовать

### Выбор правильного теста

| Задача | Тест | SQL/Python |
|--------|------|-----------|
| Сравнить две группы (средние) | t-test | `t.test()` или SQL |
| Сравнить >2 групп | ANOVA | `anova()` |
| Связь категорий | Chi-squared | SQL + вычисление |
| Корреляция числовых | Pearson | `CORR()` в SQL |
| Корреляция рангов | Spearman | Python |
| A/B тест пропорций | z-test | Формула |

---

## 🔬 Корреляционный анализ

### Pearson Correlation в SQL

```sql
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

**Интерпретация r (correlation coefficient):**
```
 1.0       Идеальная положительная
 0.9-1.0   Очень сильная положительная ✅
 0.7-0.9   Сильная положительная ✅
 0.5-0.7   Средняя 🟡
 0.3-0.5   Слабая 🟡
 0.0-0.3   Очень слабая/нет ❌
-0.3-0.0   Очень слабая отрицательная ❌
-0.5--0.3  Слабая отрицательная
-0.7--0.5  Средняя отрицательная
-0.9--0.7  Сильная отрицательная ✅
-1.0--0.9  Очень сильная отрицательная ✅
-1.0       Идеальная отрицательная
```

**Пример вывода:**
```
Корреляция доставки и NPS: r = -0.72

Интерпретация:
✅ СИЛЬНАЯ отрицательная связь
✅ Статистически значимая (sample size: 5,234)

Slope: -0.68
→ Каждый день задержки → -0.68 пункта NPS

Практический вывод:
Доставка за 1-2 дня (сейчас 4.2) → улучшение NPS с 7.2 до 8.7
```

---

### Correlation Matrix (множественные корреляции)

```sql
-- Корреляция между всеми числовыми полями
SELECT
  'delivery_days vs nps' AS pair_name,
  CORR(delivery_days, nps_score) AS r
FROM orders

UNION ALL

SELECT
  'price vs conversion',
  CORR(price, conversion_rate)
FROM products

UNION ALL

SELECT
  'rating vs repeat_purchase',
  CORR(rating, repeat_purchase_rate)
FROM customers

ORDER BY ABS(r) DESC  -- Сортировка по силе связи
```

---

## 🧪 A/B Testing

### Chi-squared test для пропорций

**Задача:** Сравнить конверсию двух вариантов

**SQL для сбора данных:**
```sql
SELECT
  variant AS variant,
  COUNT(*) AS impression_count,
  SUM(clicked) AS click_count,
  ROUND(SUM(clicked)::numeric / COUNT(*) * 100, 2) AS ctr_pct
FROM ab_test
WHERE experiment = 'button_color_2024_12'
GROUP BY variant
```

**Результаты:**
```
Вариант A (красная): 3,456 показов, 287 кликов, CTR 8.3%
Вариант B (синяя):   3,512 показов, 245 кликов, CTR 7.0%
```

**Chi-squared вычисление:**
```python
from scipy.stats import chi2_contingency

# Contingency table
data = [
    [287, 3456-287],  # A: клики, не клики
    [245, 3512-245]   # B: клики, не клики
]

chi2, p_value, dof, expected = chi2_contingency(data)

print(f"Chi-squared: {chi2:.2f}")
print(f"p-value: {p_value:.4f}")
print(f"Статистически значимо: {p_value < 0.05}")
```

**Интерпретация:**
```
Chi-squared: 12.34
p-value: 0.0004

✅ СТАТИСТИЧЕСКИ ЗНАЧИМО (p < 0.05)

Вывод:
Красная кнопка конвертит на 18.6% лучше (8.3% vs 7.0%)
С вероятностью 99.96% это НЕ случайность

Практический impact:
• +41 клик/день
• +1,230 конверсий/месяц
• +456K ₽ revenue/месяц (при среднем чеке 370₽)

РЕШЕНИЕ: Раскатать красную кнопку на весь сайт
```

---

## 📈 Прогнозирование (Forecasting)

### Simple Linear Regression

**SQL:**
```sql
-- Тренд продаж (линейная регрессия)
SELECT
  ROUND(REGR_SLOPE(revenue, month_number)::numeric, 2) AS "Slope (рост/месяц)",
  ROUND(REGR_INTERCEPT(revenue, month_number)::numeric, 2) AS "Intercept",
  ROUND(REGR_R2(revenue, month_number)::numeric, 3) AS "R² (качество модели)"
FROM (
  SELECT
    EXTRACT(MONTH FROM date)::INTEGER AS month_number,
    SUM(amount) AS revenue
  FROM sales
  WHERE date >= '2024-01-01'
  GROUP BY month_number
) AS monthly
```

**Интерпретация R²:**
```
R² = 0.95  → Модель объясняет 95% вариации (отлично!)
R² = 0.70  → 70% (хорошо)
R² = 0.40  → 40% (средне, много шума)
R² = 0.10  → 10% (плохо, модель не подходит)
```

**Прогноз:**
```
Slope: 1.2M ₽/месяц (ежемесячный рост)
Intercept: 12.5M ₽ (базовый уровень)

Прогноз на январь 2025 (месяц 13):
Revenue = 12.5M + 1.2M × 13 = 28.1M ₽

С учётом R² = 0.85:
Доверительный интервал: 28.1M ± 2.8M (95% CI)
→ Ожидается: 25.3M - 30.9M ₽
```

---

### Time Series Decomposition

**Компоненты временного ряда:**
1. **Trend** (тренд) — долгосрочное направление
2. **Seasonality** (сезонность) — повторяющиеся паттерны
3. **Noise** (шум) — случайные колебания

**SQL для сезонности:**
```sql
-- Сезонные коэффициенты по месяцам
WITH monthly_avg AS (
  SELECT AVG(revenue) AS overall_avg FROM monthly_sales
)
SELECT
  month AS month,
  AVG(revenue) AS avg_revenue,
  ROUND(AVG(revenue) / (SELECT overall_avg FROM monthly_avg), 2) AS seasonal_factor
FROM monthly_sales
GROUP BY month
ORDER BY month
```

**Результат:**
```
Январь: 0.85 (на 15% ниже среднего)
...
Декабрь: 1.45 (на 45% выше среднего)
```

**Прогноз с сезонностью:**
```
Базовый прогноз: 20M ₽
Сезонный коэффициент февраля: 0.85
Скорректированный прогноз: 20M × 0.85 = 17M ₽
```

---

## 🎯 Outlier Detection (поиск аномалий)

### Метод 1: Z-score (стандартные отклонения)

```sql
WITH stats AS (
  SELECT
    AVG(daily_revenue) AS mean,
    STDDEV(daily_revenue) AS std
  FROM daily_sales
  WHERE date >= NOW() - INTERVAL '90 days'
)
SELECT
  date AS date,
  daily_revenue AS revenue,
  ROUND((daily_revenue - mean) / NULLIF(std, 0), 2) AS z_score
FROM daily_sales, stats
WHERE date >= NOW() - INTERVAL '30 days'
  AND ABS((daily_revenue - mean) / NULLIF(std, 0)) > 2
ORDER BY ABS((daily_revenue - mean) / NULLIF(std, 0)) DESC
```

**Интерпретация:**
```
|Z| > 3: Экстремальный outlier (99.7% вероятность аномалии)
|Z| > 2: Значительный outlier (95% вероятность)
|Z| > 1.5: Возможный outlier (проверить)
```

**Пример вывода:**
```
15 ноября: 45M ₽ (Z-score: 4.2)
→ Экстремальный outlier (+340% от среднего)
→ Причина: Крупная сделка "Газпром"
→ Тип: Позитивный, разовый
→ Действие: Мониторить (не включать в базовые расчёты)
```

---

### Метод 2: IQR (Interquartile Range)

```sql
WITH percentiles AS (
  SELECT
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY amount) AS q1,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY amount) AS q3
  FROM orders
)
SELECT
  order_id,
  amount,
  CASE
    WHEN amount < q1 - 1.5 * (q3 - q1) THEN 'Low outlier'
    WHEN amount > q3 + 1.5 * (q3 - q1) THEN 'High outlier'
    ELSE 'Normal'
  END AS outlier_status
FROM orders, percentiles
WHERE amount < q1 - 1.5 * (q3 - q1)
   OR amount > q3 + 1.5 * (q3 - q1)
ORDER BY ABS(amount - (q1 + q3)/2) DESC
LIMIT 20
```

---

## 📊 Confidence Intervals (доверительные интервалы)

### 95% CI для среднего

```python
from scipy import stats
import numpy as np

data = [...]  # Ваши данные

mean = np.mean(data)
std_err = stats.sem(data)  # Standard error
ci = stats.t.interval(
    confidence=0.95,
    df=len(data)-1,
    loc=mean,
    scale=std_err
)

print(f"Среднее: {mean:.2f}")
print(f"95% CI: [{ci[0]:.2f}, {ci[1]:.2f}]")
```

**Интерпретация:**
```
Средний чек: 1,234 ₽
95% CI: [1,187, 1,281]

Вывод:
С вероятностью 95% истинное среднее находится в диапазоне 1,187-1,281 ₽

Практическое применение:
Прогноз выручки:
• 10,000 заказов × 1,187₽ = 11.87M ₽ (пессимистичный)
• 10,000 заказов × 1,281₽ = 12.81M ₽ (оптимистичный)
• Диапазон: 11.87M - 12.81M ₽
```

---

## 🎯 Sample Size: достаточно ли данных?

### Минимальные требования

| Анализ | Минимальный sample size |
|--------|------------------------|
| Простое среднее | n > 30 |
| Сравнение групп (t-test) | n > 30 в каждой группе |
| Корреляция | n > 30 точек |
| A/B тест (конверсия 3%) | n > 1,000 в каждом варианте |
| Regression | n > 10 × количество предикторов |
| Cohort analysis | n > 100 в когорте |

**Проверка перед анализом:**
```sql
SELECT COUNT(*) AS sample_size FROM data WHERE ...

-- Если < минимума:
"⚠️ НЕДОСТАТОЧНО ДАННЫХ

Sample size: {n}
Минимум для надёжных выводов: {минимум}

Рекомендация: Собрать больше данных или использовать более широкий период"
```

---

## 🧮 Стандартная ошибка и значимость

### Standard Error (SE)

```sql
-- Стандартная ошибка среднего
SELECT
  ROUND(STDDEV(amount) / SQRT(COUNT(*)), 2) AS "Standard Error"
FROM orders
```

**Зачем нужна:**
```
Среднее: 1,234 ₽
SE: 45 ₽

→ Истинное среднее скорее всего в пределах 1,234 ± 45 ₽
→ Чем меньше SE, тем точнее оценка
```

---

### P-value интерпретация

```
p < 0.001  → Очень сильная значимость (***) ✅
p < 0.01   → Сильная значимость (**) ✅
p < 0.05   → Значимо (*) ✅
p < 0.10   → Граничное (†) 🟡
p ≥ 0.10   → Не значимо ❌
```

**Пример вывода:**
```
A/B тест: Красная vs Синяя кнопка
p-value: 0.0004

✅ СТАТИСТИЧЕСКИ ЗНАЧИМО (p < 0.001, ***)

Вывод:
С вероятностью >99.9% разница в CTR НЕ случайна.
Красная кнопка действительно лучше.
```

---

## 📉 Распределения

### Проверка нормальности

**Визуально:**
```sql
-- Гистограмма для проверки
SELECT
  FLOOR(amount / 1000) * 1000 AS "Bucket",
  COUNT(*) AS "Frequency"
FROM orders
GROUP BY FLOOR(amount / 1000)
ORDER BY "Bucket"
```

**Если распределение НЕ нормальное:**
- ❌ НЕ используй mean (используй median)
- ❌ НЕ используй std (используй IQR)
- ❌ НЕ используй t-test (используй Mann-Whitney)

---

### Skewness (асимметрия)

```
Skewness > 0: Правый хвост (много малых значений, редкие большие)
              Пример: доходы населения, размер заказов

Skewness < 0: Левый хвост (редкие малые, много больших)

Skewness ≈ 0: Симметричное (близко к нормальному)
```

**Что делать если skewed:**
```sql
-- Логарифмическое преобразование
SELECT
  LOG(amount + 1) AS log_amount  -- +1 чтобы избежать LOG(0)
FROM orders
-- Теперь может стать более симметричным
```

---

## 🎯 Statistical Significance vs Practical Significance

### Важно понимать разницу!

**Пример 1: Статистически значимо, но не практично**
```
A/B тест:
• Вариант A: CTR 3.00%
• Вариант B: CTR 3.02%
• Разница: +0.02% (относительно +0.67%)
• p-value: 0.03 (статистически значимо!)

Sample size: 100,000 (огромная выборка)

Вывод:
✅ Статистически значимо
❌ НЕ практически значимо

+0.02% CTR = +20 кликов/100K показов
ROI: ничтожный, не стоит внедрять

РЕШЕНИЕ: Оставить A (нет смысла менять)
```

---

**Пример 2: Практично, но не статистически значимо**
```
A/B тест:
• Вариант A: CTR 3.0%
• Вариант B: CTR 4.5%
• Разница: +50% (!)
• p-value: 0.12 (НЕ значимо)

Sample size: 150 (маленькая выборка)

Вывод:
❌ НЕ статистически значимо
✅ Практически значимо (если подтвердится)

РЕШЕНИЕ:
Продолжить тест до sample size 1,000+
Потенциал большой, но нужно больше данных
```

---

## 🔮 Прогнозирование: методы

### 1. Moving Average (скользящее среднее)

**Простое:**
```sql
SELECT
  date,
  revenue,
  ROUND(AVG(revenue) OVER (
    ORDER BY date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  )::numeric, 2) AS "MA7"
FROM daily_sales
ORDER BY date
```

**Для прогноза:**
```
Последние 7 дней MA: 2.3M ₽/день
Прогноз на завтра: ~2.3M ₽
```

**Проблема:** Не учитывает тренд и сезонность!

---

### 2. Linear Trend (линейный тренд)

```sql
-- Используй REGR_SLOPE и REGR_INTERCEPT
WITH trend AS (
  SELECT
    REGR_SLOPE(revenue, day_number) AS slope,
    REGR_INTERCEPT(revenue, day_number) AS intercept
  FROM (
    SELECT
      ROW_NUMBER() OVER (ORDER BY date) AS day_number,
      revenue
    FROM daily_sales
    WHERE date >= '2024-01-01'
  ) AS numbered
)
SELECT
  slope * 365 + intercept AS forecast_day_365,
  slope * 366 + intercept AS forecast_day_366
FROM trend
```

---

### 3. Сезонная декомпозиция (advanced)

**Формула:**
```
Forecast = Trend × Seasonal Factor × Random Component

Пример:
Базовый тренд февраля: 20M ₽
Сезонный коэффициент февраля: 0.85 (на 15% ниже среднего)
Прогноз: 20M × 0.85 = 17M ₽
```

**SQL для сезонных коэффициентов:**
```sql
WITH monthly_avg AS (
  SELECT
    EXTRACT(MONTH FROM date) AS month,
    AVG(revenue) AS month_avg
  FROM monthly_sales
  GROUP BY EXTRACT(MONTH FROM date)
),
overall_avg AS (
  SELECT AVG(revenue) AS overall FROM monthly_sales
)
SELECT
  month AS month,
  ROUND(month_avg / overall, 2) AS seasonal_factor
FROM monthly_avg, overall_avg
ORDER BY month
```

---

## 🎯 Практические кейсы

### Кейс 1: Проверка гипотезы с корреляцией

**Гипотеза:** "Погода влияет на количество ДТП"

**Шаг 1: Данные**
```sql
SELECT
  weather_condition AS weather_condition,
  COUNT(*) AS accident_count,
  ROUND(AVG(injured_count)::numeric, 2) AS avg_injured_count,
  ROUND(AVG(dead_count)::numeric, 2) AS avg_dead_count
FROM accidents
WHERE weather_condition IS NOT NULL
GROUP BY weather_condition
ORDER BY COUNT(*) DESC
```

**Шаг 2: Статистический тест**
```python
# ANOVA для сравнения >2 групп
from scipy.stats import f_oneway

clear = data[data.weather == 'Ясно'].injured
rain = data[data.weather == 'Дождь'].injured
snow = data[data.weather == 'Снег'].injured

F, p = f_oneway(clear, rain, snow)
print(f"F-statistic: {F:.2f}, p-value: {p:.4f}")
```

**Шаг 3: Вывод**
```
F-statistic: 89.34
p-value: <0.0001

✅ СТАТИСТИЧЕСКИ ЗНАЧИМО

Результаты:
• Ясно: 1.14 раненых/ДТП
• Дождь: 1.28 раненых/ДТП (+12%)
• Снег: 1.40 раненых/ДТП (+23%)

Вывод:
Погодные условия КРИТИЧНО влияют на тяжесть ДТП.
Снегопад увеличивает тяжесть на 23% (p < 0.001).

РЕКОМЕНДАЦИЯ:
Усилить патрулирование при снегопаде на опасных участках:
- КАД (км 15-25)
- Выборгское шоссе

Потенциальный эффект: -50 раненых/зиму
```

---

### Кейс 2: A/B тест с малой выборкой

**Проблема:** Sample size недостаточен

**Данные:**
```
Вариант A: 87 показов, 12 кликов (13.8% CTR)
Вариант B: 93 показов, 8 кликов (8.6% CTR)

p-value: 0.18 (НЕ значимо)
```

**Вывод:**
```
❌ НЕДОСТАТОЧНО ДАННЫХ

Текущий sample size: 87 + 93 = 180
Для достоверного вывода при CTR ~10% нужно: 1,000+ на вариант

Разница выглядит большой (+60% относительно), но может быть случайной.

РЕКОМЕНДАЦИЯ:
Продолжить тест до 2,000 total (1,000 на вариант)
ETA: 10-14 дней при текущем трафике

Preliminary observation: A кажется лучше, но рано делать вывод
```

---

## 📈 Regression Analysis (регрессионный анализ)

### Multiple Linear Regression

**Задача:** Понять что влияет на продажи

```python
from sklearn.linear_model import LinearRegression
import pandas as pd

# Данные
df = pd.read_sql("SELECT price, marketing_spend, season, sales FROM products", conn)

# Модель
X = df[['price', 'marketing_spend', 'season']]
y = df['sales']

model = LinearRegression()
model.fit(X, y)

# Коэффициенты
print(f"Intercept: {model.intercept_:.2f}")
for feature, coef in zip(X.columns, model.coef_):
    print(f"{feature}: {coef:.2f}")

# R²
print(f"R²: {model.score(X, y):.3f}")
```

**Результат:**
```
Intercept: 10,000 (базовый уровень продаж)
price: -150 (каждый +1₽ цены → -150 продаж)
marketing_spend: +0.8 (каждый +1₽ маркетинга → +0.8 продаж)
season: +2,000 (сезонный эффект)

R²: 0.78 (модель объясняет 78% вариации)

Практический вывод:
ROI маркетинга: 0.8 (каждый рубль → 0.8₽ дохода)
→ Убыточно! Оптимизировать или сократить бюджет
```

---

## 🎯 Формулирование статистических выводов

### Структура вывода

```markdown
## СТАТИСТИЧЕСКИЙ АНАЛИЗ: [название]

**Гипотеза:** [что проверяли]

**Данные:**
• Sample size: [n]
• Период: [даты]
• Метод: [тест/анализ]

**Результаты:**
• Метрика: [значение]
• Статистика: [t/F/chi²/r] = [число]
• p-value: [число]
• Эффект: [effect size]

**Статистический вывод:**
[Подтверждена/Опровергнута] (p [</>] 0.05)

**Практический вывод:**
[Интерпретация в бизнес-терминах]
[Quantified impact]

**Рекомендация:**
[Что делать на основе результатов]
```

---

### Пример: полный статистический вывод

```
## A/B ТЕСТ: Цвет CTA кнопки

**Гипотеза:** Красная кнопка конвертит лучше синей

**Данные:**
• Sample size: 7,123 (A: 3,456, B: 3,667)
• Период: 1-15 декабря 2024
• Метод: Chi-squared test

**Результаты:**
• CTR A (красная): 8.3% (287/3,456)
• CTR B (синяя): 6.7% (245/3,667)
• Разница: +1.6 п.п. (относительно +23.9%)
• Chi²: 12.34
• p-value: 0.0004

**Статистический вывод:**
✅ ГИПОТЕЗА ПОДТВЕРЖДЕНА (p < 0.001, ***)

С вероятностью >99.9% красная кнопка конвертит лучше.
Это НЕ случайность.

**Практический вывод:**
Impact:
• +1.6 п.п. CTR
• На 100K показов/месяц: +1,600 кликов
• При конверсии 5%: +80 заказов
• При среднем чеке 5,000₽: +400K ₽ revenue/месяц

ROI:
• Стоимость внедрения: 50K ₽ (дизайн + разработка)
• Payback: 4 дня (!)

**Рекомендация:**
[КРИТИЧНО] Раскатать красную кнопку на весь сайт
Дедлайн: до конца декабря (не терять revenue)
```

---

## 🧪 Cheat Sheet: Статистические формулы

### Базовые метрики

```sql
-- Mean (среднее)
AVG(value)

-- Median (медиана)
PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value)

-- Mode (мода) - самое частое значение
SELECT value, COUNT(*) as freq
FROM data
GROUP BY value
ORDER BY freq DESC
LIMIT 1

-- Standard Deviation (стандартное отклонение)
STDDEV(value)

-- Variance (дисперсия)
VARIANCE(value)
```

---

### Корреляция

```sql
-- Pearson correlation
CORR(x, y)

-- Regression (slope, intercept, R²)
REGR_SLOPE(y, x)
REGR_INTERCEPT(y, x)
REGR_R2(y, x)
```

---

### Перцентили

```sql
-- Quartiles
PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY value) AS q1
PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY value) AS q2  -- median
PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY value) AS q3

-- Deciles
PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY value) AS p10
PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY value) AS p90
```

---

## ✅ Финальный чек-лист

Перед статистическим выводом проверь:

**Данные:**
- [ ] Sample size достаточен (>30 минимум)
- [ ] Нет пропусков (NULL) в критичных полях
- [ ] Outliers проверены и обработаны
- [ ] Период адекватен (учтена сезонность)

**Анализ:**
- [ ] Правильный тест для типа данных
- [ ] Assumptions теста выполнены
- [ ] p-value вычислен (если применимо)
- [ ] Effect size оценён (практическая значимость)

**Вывод:**
- [ ] Статистический вывод (значимо/не значимо)
- [ ] Практический вывод (что это значит)
- [ ] Quantified impact (сколько денег/времени)
- [ ] Рекомендация (что делать)

---

*Используй этот skill для статистически корректного анализа данных в BI*
