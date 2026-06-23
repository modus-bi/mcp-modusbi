---
name: explain-chart
description: Объясняет график и генерирует Level 4 бизнес-вывод с actionable рекомендациями. Используйте когда пользователь просит "объясни график", "что это значит", "какие выводы", "что делать". Автоматически получает данные компонента, анализирует паттерны, формулирует рекомендации с quantified impact, добавляет текстовый блок к дашборду.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: modusbi, playwright
---

# Explain Chart: Объяснение графика с выводами

## Overview

Этот skill объясняет что показывает график и формулирует **Level 4 вывод** (prescriptive analytics):
- Получает данные из компонента дашборда
- Анализирует паттерны и тренды
- Проверяет statistical significance (если применимо)
- Формулирует драйверы роста и зоны риска
- Генерирует actionable рекомендации с impact оценкой
- Добавляет текстовый блок к дашборду
- Делает скриншот графика через playwright для визуальной верификации

**Результат:** График с профессиональным бизнес-выводом рядом.

**4 уровня выводов:**
- Level 1: Дескриптивный ("продажи 156M") ❌
- Level 2: Аналитический ("рост 12%") 🟡
- Level 3: Инсайты ("рост за счёт X") ✅
- Level 4: Рекомендации ("действие 1,2,3 → +4.5M") ⭐ **ЦЕЛЬ**

---

## When to Use This Skill

Используй этот skill когда пользователь:

- ✅ Просит **"объяснить"** график/данные
- ✅ Спрашивает **"что это значит"**
- ✅ Хочет **"сделать выводы"** из графика
- ✅ Спрашивает **"что с этим делать"**
- ✅ Нужны **рекомендации** на основе viz
- ✅ Просит **"добавить комментарий"** к графику

**Триггерные фразы:**
- "Объясни этот график"
- "Что показывает динамика?"
- "Какие выводы из данных?"
- "Что делать с этими результатами?"
- "Добавь текстовый вывод"

**Не использовать если:**
- ❌ Нужно создать новый график (используй `/create-dashboard`)
- ❌ Нужен анализ исходных данных (используй `/analyze-data`)
- ❌ Нужен только SQL (используй `/generate-sql`)

---

## Standard Workflow

### Шаг 1: Получить данные компонента

```python
# Получить данные из существующего компонента
component_data = mcp__modusbi__component_crud(action="data",
    report_id=REPORT_ID,
    component_idx=0,
    limit=100  # Ограничить количество строк
)

# Структура ответа (РЕАЛЬНАЯ — component_crud action="data"):
{
  "success": true,
  "caption": "...", "dataset_id": 531,
  "columns": ["region", "revenue", "orders"],   # имена колонок
  "rows": [                                       # СЛОВАРИ {колонка: значение}, НЕ позиционные списки!
    {"region": "Москва", "revenue": 45200000, "orders": 1234},
    {"region": "СПб",    "revenue": 32100000, "orders": 987}
  ],
  "total_rows": 10, "limited": false
}
# Доступ ТОЛЬКО по имени колонки: row["revenue"], НЕ row[1].
# total = sum(r["revenue"] for r in rows); peak = max(rows, key=lambda r: r["revenue"]).
```

---

### Шаг 2: Анализировать данные

**Определить тип анализа:**

```python
# По типу компонента:
if component_type == "HsLineAMchartsChart":
    analysis_type = "trend"  # Тренд, динамика
elif component_type == "HsBarAMchartsChart":
    analysis_type = "comparison"  # Сравнение категорий
elif component_type == "HsPieAMchartsChart":
    analysis_type = "distribution"  # Распределение
elif component_type == "HsTableReactabularChart":
    analysis_type = "details"  # Детали (обычно не нужен вывод)

# Анализ по типу:
if analysis_type == "trend":
    # Проверить:
    # - Направление тренда (рост/падение/стабильно)
    # - Скорость изменения (% г/г, м/м)
    # - Аномалии (резкие скачки)
    # - Сезонность

elif analysis_type == "comparison":
    # Проверить:
    # - Топ-3 (лидеры)
    # - Bottom-3 (аутсайдеры)
    # - Распределение (равномерное/неравномерное)
    # - Outliers (выбросы)

elif analysis_type == "distribution":
    # Проверить:
    # - Концентрация (топ-N дают X%)
    # - Long tail (много мелких)
    # - Balance (равномерное/неравномерное)
```

---

### Шаг 3: Вычислить метрики

```python
# Для trend analysis:
total = sum(row[1] for row in rows)  # Общая сумма
growth_yoy = (current - year_ago) / year_ago * 100
drivers = find_top_contributors(data, top_n=3)

# Для comparison:
top_3 = sorted(rows, key=lambda r: r[1], reverse=True)[:3]
contribution_pct = [(r[0], r[1]/total*100) for r in top_3]

# Для correlation (если scatter plot):
r = calculate_correlation(x_values, y_values)
slope = calculate_slope(x_values, y_values)
```

---

### Шаг 4: Сформулировать Level 4 вывод

**Используй структуру из skill `/data-analyst-expert`:**

```python
conclusion = f"""
<div style="background: linear-gradient(135deg, #e3f2fd, #bbdefb);
            padding: 20px; border-radius: 10px;
            border-left: 5px solid #1976d2;">

<h2 style="color: #0d47a1;">📊 {chart_title.upper()}</h2>

<p style="font-size: 16px;">
    <strong>Главная метрика:</strong> {main_metric}
</p>

<h3 style="color: #1565c0;">ДРАЙВЕРЫ РОСТА</h3>
<ul style="line-height: 1.8;">
    <li><strong>{driver_1_name}</strong> — {driver_1_pct}% вклада ({driver_1_explanation})</li>
    <li><strong>{driver_2_name}</strong> — {driver_2_pct}% вклада ({driver_2_explanation})</li>
</ul>

<h3 style="color: #c62828;">⚠️ ЗОНЫ РИСКА</h3>
<ul style="line-height: 1.8;">
    <li><strong>{risk_1}</strong> — {risk_1_scale} ({risk_1_consequence})</li>
</ul>

<h3 style="color: #2e7d32;">💡 РЕКОМЕНДАЦИИ</h3>
<ol style="line-height: 1.8;">
    <li><strong>[{priority_1}]</strong> {action_1}<br/>
        Дедлайн: {deadline_1}, Impact: {impact_1}</li>
    <li><strong>[{priority_2}]</strong> {action_2}<br/>
        Дедлайн: {deadline_2}, Impact: {impact_2}</li>
</ol>

<p><strong>ПРОГНОЗ:</strong> {forecast}</p>

</div>
"""
```

---

### Шаг 5: Добавить текстовый блок к дашборду

```python
# Добавить текстовый блок справа от графика
mcp__modusbi__component_crud(action="add_text_block",
    report_id=report_id,
    title="Выводы",
    text_content=conclusion,
    x=24,  # Справа, если график слева на x=0, w=24 в 48-col grid
    y=component_y,  # Та же высота что график
    w=24,
    h=component_h  # Та же высота
)
```

**Альтернатива:** Обновить существующий текстовый блок
```python
mcp__modusbi__component_crud(action="update",
    report_id=report_id,
    component_idx=text_block_idx,
    text_content=new_conclusion
)
```

---

## Common Patterns

### Pattern 1: Trend Analysis (линейный график)

**User input:**
```
/explain-chart <report_id> 0
# Компонент 0 = Line chart "Динамика продаж"
```

**Analysis:**
```python
# 1. Получить данные
data = get_component_data(report_id, 0)
# [("Янв", 12.5M), ("Фев", 11.8M), ..., ("Дек", 18.2M)]

# 2. Вычислить метрики
total_2024 = sum(values)  # 156.7M
total_2023 = 140.2M  # Из прошлого года
growth_yoy = (156.7 - 140.2) / 140.2 * 100  # +11.8%

peak_month = max(data, key=lambda x: x[1])  # ("Дек", 18.2M)
low_month = min(data, key=lambda x: x[1])   # ("Фев", 11.8M)

# 3. Найти драйверы (детализация)
drivers = query("""
    SELECT category, SUM(amount) as revenue,
           ROUND((revenue_2024 - revenue_2023) / revenue_2023 * 100, 2) as growth
    FROM sales
    GROUP BY category
    ORDER BY growth DESC
    LIMIT 3
""")
# → Электроника +34%, Москва +28%, Онлайн +45%
```

**Вывод:**
```markdown
📊 ДИНАМИКА ПРОДАЖ 2024

Выручка: 156.7M ₽ (+11.8% г/г, выше плана на 3%)

КЛЮЧЕВЫЕ НАБЛЮДЕНИЯ:
• Пик в декабре (18.2M, +45% м/м) — сезонность + Black Friday
• Спад в феврале (11.8M, -8% м/м) — типичный сезонный минимум
• Стабильный рост апрель-ноябрь (+1.2M среднемесячно)

ДРАЙВЕРЫ РОСТА:
1. Электроника — +34% (вклад 67%)
2. Москва — +28% (вклад 23%)
3. Онлайн — +45% (вклад 10%)

ЗОНЫ РИСКА:
• Одежда — -5% (потеря 2.3M ₽)
• Сибирь — -12% (потеря 5.2M ₽, клиент Газпром ушёл)

РЕКОМЕНДАЦИИ:
[КРИТИЧНО] Расширить ассортимент электроники (Q1 2025)
   Impact: +3-4M ₽ дополнительно

[ВЫСОКИЙ] Решить проблему Одежда: новый поставщик
   Impact: остановить -2.3M кровотечение

ПРОГНОЗ: Выполнение рекомендаций → 18% рост в Q1 (vs 12% текущий)
```

---

### Pattern 2: Comparison Analysis (столбчатая диаграмма)

**User input:**
```
/explain-chart <report_id> 2
# Компонент 2 = Bar chart "Топ-10 регионов"
```

**Analysis:**
```python
# 1. Данные
data = [
    ("Москва", 45.2M, 34%),
    ("СПб", 32.1M, 24%),
    ("Казань", 12.3M, 9%),
    ...
]

# 2. Метрики
top_3_contribution = sum(pct for _, _, pct in data[:3])  # 67%
concentration = "Высокая" if top_3_contribution > 60 else "Средняя"

# 3. Сравнение
if growth_rates_available:
    fastest_growing = max(data, key=lambda x: x.growth)
    declining = [d for d in data if d.growth < 0]
```

**Вывод:**
```markdown
📊 РЕГИОНАЛЬНОЕ РАСПРЕДЕЛЕНИЕ

Топ-3 региона: 67% выручки (концентрация высокая ⚠️)

ЛИДЕРЫ:
• Москва — 45.2M ₽ (34%, +28% г/г)
• СПб — 32.1M ₽ (24%, +15% г/г)
• Казань — 12.3M ₽ (9%, +89% г/г) — быстрый рост!

ЗОНЫ РИСКА:
• Высокая концентрация (топ-1 = 34%) — риск зависимости
• Сибирь -12% — потеря клиента

РЕКОМЕНДАЦИИ:
[ВЫСОКИЙ] Диверсифицировать: снизить долю Москвы до <25%
   Развивать регионы 4-10
   Impact: снижение риска

[СРЕДНИЙ] Масштабировать успех Казани (+89%) на другие регионы
   Impact: потенциал +5-7M ₽ если повторить в 3 регионах
```

---

## Best Practices

### 1. Адаптируй вывод под тип графика

| Тип графика | Фокус вывода |
|-------------|-------------|
| **Line Chart** | Тренд (рост/падение), скорость изменения, аномалии, прогноз |
| **Bar Chart** | Лидеры, аутсайдеры, концентрация, распределение |
| **Pie Chart** | Доли, концентрация, баланс |
| **Table** | Обычно вывод не нужен (данные говорят сами) |

### 2. Всегда количественно

**Все метрики в цифрах:**

❌ Плохо: "Москва лидирует"
✅ Хорошо: "Москва 45.2M ₽ (34% от общей)"

❌ Плохо: "Сильный рост"
✅ Хорошо: "Рост +28% г/г (+10M ₽)"

### 3. Сравнивай с baseline

```python
# ВСЕГДА давай контекст:

# ❌ Плохо:
"Выручка 156M ₽"

# ✅ Хорошо:
"Выручка 156M ₽ (+12% г/г, выше плана на 3%)"

# ✅ Ещё лучше:
"Выручка 156M ₽
 • +12% г/г (140M → 156M)
 • Выше плана на 3% (план 152M)
 • Выше бенчмарка на 5% (индустрия +7%)"
```

### 4. Приоритизируй рекомендации

**Используй:**
- **[КРИТИЧНО]** — требует немедленных действий, большой impact
- **[ВЫСОКИЙ]** — важно, заметный impact
- **[СРЕДНИЙ]** — желательно, небольшой impact

**Пример:**
```markdown
[КРИТИЧНО] Фикс payment gateway (каждый день -40K ₽)
[ВЫСОКИЙ] Оптимизация сайта (impact +850K/мес)
[СРЕДНИЙ] A/B тест цен (impact +150K/мес)
```

---

## Examples

### Example 1: Line Chart (тренд)

**Input:**
```
/explain-chart <report_id> 0
```

**Data:**
```
Month     Revenue
------    --------
2024-01   12.5M
2024-02   11.8M
...
2024-12   18.2M
```

**Analysis:**
```python
trend = "рост"  # Декабрь > Январь
growth_yoy = +12%
peak = ("Декабрь", 18.2M)
drivers = query_drivers()  # Электроника +34%, Москва +28%
```

**Output:**
```markdown
📊 ДИНАМИКА ПРОДАЖ 2024

Выручка: 156.7M ₽ (+12% г/г)

КЛЮЧЕВЫЕ НАБЛЮДЕНИЯ:
• Пик в декабре (18.2M) — сезонность + Black Friday
• Стабильный рост апрель-ноябрь
• Спад в феврале (сезонный минимум)

ДРАЙВЕРЫ РОСТА:
1. Электроника — +34% г/г (вклад 67% общего роста)
2. Москва — +28% г/г (вклад 23%)

ЗОНЫ РИСКА:
• Одежда -5% (потеря 2.3M ₽)
• Зависимость от одной категории (67% роста)

РЕКОМЕНДАЦИИ:
[КРИТИЧНО] Расширить электронику: новые SKU, больше брендов
   Impact: +3-4M ₽ в Q1 2025

[ВЫСОКИЙ] Диверсифицировать: развивать другие категории
   Снизить зависимость от топ-1 (67% → <50%)

ПРОГНОЗ: Продолжение тренда → 175M ₽ в 2025 (+12% г/г)
```

---

### Example 2: Bar Chart (сравнение)

**Input:**
```
/explain-chart <report_id> 1
```

**Data:**
```
Region      Revenue    Share
-------     --------   -----
Москва      45.2M      34%
СПб         32.1M      24%
Казань      12.3M      9%
...
```

**Output:**
```markdown
📊 ТОП-10 РЕГИОНОВ

Топ-3: 67% выручки (высокая концентрация ⚠️)

ЛИДЕРЫ:
• Москва 45.2M (34%) — открытие 5 магазинов дало +28%
• СПб 32.1M (24%) — стабильный рост +15%
• Казань 12.3M (9%) — рекорд +89% (новый клиент)

ЗОНЫ РИСКА:
• Концентрация топ-1 (34%) — риск зависимости
• Сибирь -12% — потеря Газпрома (-5.2M)

РЕКОМЕНДАЦИИ:
[ВЫСОКИЙ] Диверсификация: развивать регионы 4-10
   Цель: топ-1 <25% (сейчас 34%)
   Impact: снижение риска

[СРЕДНИЙ] Масштабировать модель Казани (+89%)
   Повторить в Уфе, Самаре, Екатеринбурге
   Impact: +5-7M если успех
```

---

## Визуальная верификация (playwright)

После добавления текстового блока с выводом, сделай скриншот для проверки:

```python
# 1. Открыть отчёт в браузере
browser_navigate(f"${MODUSBI_URL}/report/{report_id}")

# 2. Подождать загрузку компонентов
browser_evaluate("await new Promise(r => setTimeout(r, 3000))")

# 3. Скриншот графика с выводом
browser_take_screenshot(name=f"chart_explanation_{report_id}")

# 4. Проверить визуально:
# - Текстовый блок рядом с графиком (не наложился)
# - Вывод читаемый (шрифт, контраст)
# - HTML-форматирование отрендерилось корректно
# - Цвета семантически правильные (зелёный=рост, красный=риск)
```

**Если проблемы:**
- Текст наложился → обновить position (x, y, w, h)
- HTML не рендерится → проверить экранирование в text_content
- Шрифт мелкий → увеличить h компонента

---

## Troubleshooting

### Issue: Данные не загружаются

**Symptom:** Ошибка при получении данных

**Solution:**
```python
# Проверь:
# 1. report_id правильный?
reports = mcp__modusbi__report_operations(action="list")
print(f"Available reports: {[r.id for r in reports]}")

# 2. component_idx правильный?
components = mcp__modusbi__report_operations(
    action="components_list",
    report_id=report_id
)
print(f"Components: {[(i, c.title) for i, c in enumerate(components)]}")

# 3. Компонент имеет данные?
data = mcp__modusbi__component_crud(action="data", report_id=report_id, component_idx=component_idx)
if data.rows_count == 0:
    print("⚠️ Компонент пустой! Проверь датасет и SQL")
```

---

### Issue: Вывод слишком общий

**Symptom:** "Продажи выросли. Это хорошо."

**Solution:**
Используй чек-лист Level 4:

- [ ] Есть главная метрика + контекст?
- [ ] Есть драйверы с % вклада?
- [ ] Есть зоны риска?
- [ ] Есть 3 конкретных действия (не "улучшить")?
- [ ] У каждого действия есть дедлайн и impact?
- [ ] Есть прогноз?

Если хоть одного нет → вывод неполный!

---

### Issue: Нет места для текстового блока

**Symptom:** График занимает всю ширину (w=48)

**Solution:**
```python
# Вариант 1: Уменьшить график
mcp__modusbi__component_crud(action="layout_update",
    report_id=report_id,
    component_idx=0,
    w=24  # Было 48 -> стало 24 (половина)
)

# Теперь есть место справа (x=24) для текста

# Вариант 2: Текст ПОД графиком
mcp__modusbi__component_crud(action="add_text_block",
    report_id=report_id,
    title="Выводы",
    text_content=conclusion,
    x=0,
    y=graph_y + graph_h,  # Под графиком
    w=48,
    h=12
)
```

---

## Reference Documentation

- **/data-analyst-expert** — Структура Level 4 выводов, SMART рекомендации
- **/statistical-analysis** — Интерпретация корреляций, p-value
- **/bi-visualization-expert** — Типы графиков и их особенности

---

## Important Notes

### Level 4 = actionable рекомендации

**Не останавливайся на описании данных!**

```
Level 1: "График показывает продажи. Декабрь самый высокий."
         ❌ Бесполезно

Level 2: "Продажи 156M (+12% г/г). Пик в декабре."
         🟡 Лучше, но что дальше?

Level 3: "Рост 12% за счёт Электроники (+34%) и Москвы (+28%)"
         ✅ Хорошо, но что ДЕЛАТЬ?

Level 4: "Рост 12% → Действие 1: расширить Электронику → +3M ₽
                    → Действие 2: инвестировать в онлайн → +2M ₽
                    → Прогноз: 18% рост в Q1"
         ⭐ ЦЕЛЬ! Actionable!
```

### Quantified Impact обязателен

```
❌ "Это улучшит показатели"
✅ "+5.2M ₽/квартал"

❌ "Сэкономит время"
✅ "-2 часа/день = 220 часов/месяц = 660K ₽"

❌ "Увеличит retention"
✅ "+12% retention → +10.2M ₽ LTV за год"
```

---

**Sources:**
- [Agent Skills Specification](https://agentskills.io/specification)
- [Data Analyst Skills Guide](https://habr.com/ru/articles/988818/)
- [K-Dense-AI Scientific Skills](https://github.com/K-Dense-AI/claude-scientific-skills)
- [Claude Code Skills](https://code.claude.com/docs/ru/skills)
