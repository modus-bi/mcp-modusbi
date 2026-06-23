---
name: dq-profiler
description: Профилирование качества данных и выработка DQM-правил. Полный цикл - от анализа до дашборда. Этап A - профилирование (полнота, уникальность, энтропия), Этап B - генерация DQM-правил валидации (NOT NULL, format, range, FK), Этап C - эталонные значения (Золотые записи), Этап D - DQ-метрики и дашборд. Используйте когда нужно проверить качество данных, выработать правила валидации, создать DQ-дашборд.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: data-quality
    mcp-servers: postgres, modusbi, playwright
---

# DQ Profiler: Профилирование качества данных и DQM-правила

## Overview

Этот skill проводит полное профилирование качества данных и вырабатывает DQM-правила:

- **Этап A:** Профилирование — полнота, уникальность, формат, энтропия, дубли
- **Этап B:** Выработка DQM-правил — NOT NULL, regex, range, FK, бизнес-логика
- **Этап C:** Эталоны — канонические значения для «Золотых записей»
- **Этап D:** Метрики — DQ-датасеты и дашборд через modusbi-mcp
- **Этап E:** Визуальная верификация DQ-дашборда через playwright

**Результат:** DQ Score, список DQM-правил с SQL, DQ-дашборд.

**Опирается на:**
- Skill: `/analyze-data` — глубокий анализ данных
- Skill: `/sql-bi-expert` — SQL паттерны
- Skill: `/create-dashboard` — создание дашборда
- Skill: `/data-analyst-expert` — Level 4 выводы

---

## When to Use This Skill

Используй этот skill когда пользователь:

- Просит **"проверить качество данных"** или **"профилировать таблицу"**
- Хочет **"найти дубли"** или **"проверить полноту"**
- Нужно **"выработать DQM-правила"** для справочника
- Говорит про **"DQ Score"**, **"Data Quality"**, **"качество НСИ"**
- Просит **"создать дашборд качества данных"**
- Упоминает **"энтропию"**, **"консистентность"**, **"валидность"**
- Нужен **"анализ справочника контрагентов"** из учётной системы

**Не использовать если:**
- Нужен только SQL (используй `/generate-sql`)
- Нужен только анализ без DQ-контекста (используй `/analyze-data`)
- Нужен только дашборд без профилирования (используй `/create-dashboard`)

---

## Standard Workflow

### Этап A: Профилирование

**Цель:** Понять текущее состояние данных.

#### A.1 Получить схему таблицы

```sql
-- Структура таблицы
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = '{table_name}'
ORDER BY ordinal_position;
```

#### A.2 Базовая статистика

```sql
-- Полнота (Completeness)
SELECT
    '{column}' AS field,
    COUNT(*) AS total_rows,
    COUNT("{column}") AS non_null,
    COUNT(*) - COUNT("{column}") AS null_count,
    ROUND(COUNT("{column}")::numeric / COUNT(*) * 100, 1) AS completeness_pct
FROM {table_name};
```

```sql
-- Полнота всех полей сразу
SELECT 'total_rows' AS metric, COUNT(*)::text AS value FROM {table}
UNION ALL
SELECT column_name, ROUND(COUNT(column_name)::numeric / COUNT(*) * 100, 1)::text
FROM {table}
GROUP BY column_name  -- Этот SQL надо генерировать динамически
```

#### A.3 Уникальность (Uniqueness)

```sql
-- Уникальность по полю
SELECT
    '{column}' AS field,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT "{column}") AS unique_values,
    COUNT(*) - COUNT(DISTINCT "{column}") AS duplicate_values,
    ROUND(COUNT(DISTINCT "{column}")::numeric / NULLIF(COUNT("{column}"), 0) * 100, 1) AS uniqueness_pct
FROM {table_name}
WHERE "{column}" IS NOT NULL;
```

#### A.4 Формат и валидность (Validity)

```sql
-- Проверка формата ИНН (10 или 12 цифр)
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE inn ~ '^\d{10}$' OR inn ~ '^\d{12}$') AS valid_inn,
    ROUND(
        COUNT(*) FILTER (WHERE inn ~ '^\d{10}$' OR inn ~ '^\d{12}$')::numeric
        / NULLIF(COUNT(inn), 0) * 100, 1
    ) AS validity_pct
FROM {table_name}
WHERE inn IS NOT NULL;

-- Проверка формата email
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE email ~* '^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$') AS valid_email,
    ROUND(
        COUNT(*) FILTER (WHERE email ~* '^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$')::numeric
        / NULLIF(COUNT(email), 0) * 100, 1
    ) AS validity_pct
FROM {table_name}
WHERE email IS NOT NULL;

-- Проверка формата телефона (+7XXXXXXXXXX)
SELECT
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE phone ~ '^\+7\d{10}$') AS valid_phone
FROM {table_name}
WHERE phone IS NOT NULL;
```

#### A.5 Энтропия Шеннона

```sql
-- Энтропия поля (информативность)
-- Высокая энтропия = много уникальных грязных значений
WITH freq AS (
    SELECT "{column}", COUNT(*) AS cnt
    FROM {table_name}
    WHERE "{column}" IS NOT NULL
    GROUP BY "{column}"
),
probs AS (
    SELECT cnt::numeric / SUM(cnt) OVER () AS p
    FROM freq
)
SELECT
    '{column}' AS field,
    ROUND(-SUM(p * LN(p) / LN(2))::numeric, 2) AS entropy_bits,
    COUNT(*) AS distinct_values
FROM probs;
```

**Интерпретация энтропии:**
| Энтропия | Значение |
|----------|----------|
| < 2 бит | Низкая: мало вариантов (пол, статус) — норма |
| 2-5 бит | Средняя: разумное разнообразие (город, категория) |
| > 5 бит | Высокая: много уникальных значений — возможно грязные данные |
| = log2(N) | Максимальная: все значения уникальны |

#### A.6 Поиск дубликатов

```sql
-- Точные дубли по ключевому полю
SELECT "{key_field}", COUNT(*) AS cnt
FROM {table_name}
WHERE "{key_field}" IS NOT NULL
GROUP BY "{key_field}"
HAVING COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 20;

-- Near-duplicates (Levenshtein distance)
SELECT
    a.id AS id_a,
    b.id AS id_b,
    a.name AS name_a,
    b.name AS name_b,
    levenshtein(LOWER(a.name), LOWER(b.name)) AS distance
FROM {table_name} a
JOIN {table_name} b ON a.id < b.id
WHERE levenshtein(LOWER(a.name), LOWER(b.name)) <= 3
  AND LENGTH(a.name) > 3
ORDER BY distance
LIMIT 50;
```

#### A.7 DQ Score (формула)

```
DQ Score = w1 * Completeness + w2 * Uniqueness + w3 * Validity + w4 * Consistency

Стандартные веса:
  w1 = 0.30 (Completeness — полнота)
  w2 = 0.25 (Uniqueness — уникальность)
  w3 = 0.25 (Validity — валидность формата)
  w4 = 0.20 (Consistency — консистентность)
```

```sql
-- Расчёт DQ Score
WITH metrics AS (
    SELECT
        ROUND(AVG(completeness)::numeric, 1) AS avg_completeness,
        ROUND(AVG(uniqueness)::numeric, 1) AS avg_uniqueness,
        ROUND(AVG(validity)::numeric, 1) AS avg_validity,
        ROUND(AVG(consistency)::numeric, 1) AS avg_consistency
    FROM (
        -- Подзапросы для каждой метрики по полям
        ...
    ) field_metrics
)
SELECT
    ROUND(
        avg_completeness * 0.30 +
        avg_uniqueness * 0.25 +
        avg_validity * 0.25 +
        avg_consistency * 0.20
    , 1) AS dq_score
FROM metrics;
```

---

### Этап B: Выработка DQM-правил

**Цель:** На основе профилирования предложить правила валидации.

#### B.1 Типы DQM-правил

| Тип правила | Описание | Пример SQL |
|-------------|----------|------------|
| **NOT NULL** | Обязательные поля | `WHERE inn IS NULL` |
| **Format (regex)** | Формат значения | `WHERE inn !~ '^\d{10,12}$'` |
| **Range** | Диапазон значений | `WHERE amount < 0 OR amount > 1e9` |
| **FK (ссылочная целостность)** | Ссылка на справочник | `WHERE region_id NOT IN (SELECT id FROM regions)` |
| **Business Logic** | Бизнес-правила | `WHERE total != qty * price` |
| **Uniqueness** | Уникальность ключа | `GROUP BY inn HAVING COUNT(*) > 1` |
| **Timeliness** | Актуальность | `WHERE updated_at < NOW() - INTERVAL '90 days'` |
| **Cross-field** | Кросс-поля | `WHERE kpp IS NOT NULL AND inn IS NULL` |

#### B.2 Формат вывода правила

Для каждого правила генерируется:

```markdown
### Правило DQM-001: Обязательность ИНН

| Параметр | Значение |
|----------|----------|
| **ID** | DQM-001 |
| **Тип** | NOT NULL |
| **Поле** | inn |
| **Описание** | ИНН обязателен для юридических лиц |
| **Приоритет** | CRITICAL |
| **Порог** | 0% нарушений (zero tolerance) |

**SQL-проверка:**
```sql
SELECT
    'DQM-001' AS rule_id,
    'NOT_NULL' AS rule_type,
    'inn' AS field_name,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE inn IS NULL AND entity_type = 'legal') AS violations,
    ROUND(
        COUNT(*) FILTER (WHERE inn IS NULL AND entity_type = 'legal')::numeric
        / NULLIF(COUNT(*), 0) * 100, 1
    ) AS violation_pct,
    CASE
        WHEN COUNT(*) FILTER (WHERE inn IS NULL AND entity_type = 'legal') = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS status
FROM contractors;
```

**Ожидаемый результат:** 0 нарушений (100% заполненность ИНН для юрлиц).
```

#### B.3 Типичные правила для справочника контрагентов

| # | Правило | Тип | SQL условие нарушения | Приоритет |
|---|---------|-----|-----------------------|-----------|
| DQM-001 | ИНН обязателен | NOT NULL | `inn IS NULL` | CRITICAL |
| DQM-002 | Формат ИНН | Format | `inn !~ '^\d{10}$' AND inn !~ '^\d{12}$'` | CRITICAL |
| DQM-003 | Формат ОГРН | Format | `ogrn !~ '^\d{13}$' AND ogrn !~ '^\d{15}$'` | HIGH |
| DQM-004 | Формат телефона | Format | `phone !~ '^\+7\d{10}$'` | MEDIUM |
| DQM-005 | Формат email | Format | `email !~* '^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'` | MEDIUM |
| DQM-006 | Уникальность ИНН | Uniqueness | `GROUP BY inn HAVING COUNT(*) > 1` | CRITICAL |
| DQM-007 | Название не пустое | NOT NULL | `name IS NULL OR TRIM(name) = ''` | CRITICAL |
| DQM-008 | Актуальность | Timeliness | `updated_at < NOW() - INTERVAL '365 days'` | HIGH |
| DQM-009 | Регион из справочника | FK | `region_id NOT IN (SELECT id FROM regions)` | HIGH |
| DQM-010 | Адрес не пустой | NOT NULL | `address IS NULL OR TRIM(address) = ''` | MEDIUM |

#### B.4 Сводный SQL для всех правил

```sql
-- Сводная таблица нарушений по всем DQM-правилам
SELECT
    'DQM-001' AS rule_id, 'NOT_NULL' AS type, 'inn' AS field,
    COUNT(*) FILTER (WHERE inn IS NULL) AS violations
FROM contractors
UNION ALL
SELECT
    'DQM-002', 'FORMAT', 'inn',
    COUNT(*) FILTER (WHERE inn IS NOT NULL AND inn !~ '^\d{10}$' AND inn !~ '^\d{12}$')
FROM contractors
UNION ALL
SELECT
    'DQM-006', 'UNIQUENESS', 'inn',
    (SELECT COUNT(*) FROM (
        SELECT inn FROM contractors WHERE inn IS NOT NULL
        GROUP BY inn HAVING COUNT(*) > 1
    ) dup)
FROM contractors
LIMIT 1;
-- ... и т.д. для каждого правила
```

---

### Этап C: Эталонные значения

**Цель:** Предложить канонические формы для «Золотых записей».

#### C.1 Частотный анализ

```sql
-- Самые частые варианты написания (кандидаты в эталоны)
SELECT
    "{field}",
    COUNT(*) AS frequency,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 1) AS pct
FROM {table_name}
WHERE "{field}" IS NOT NULL
GROUP BY "{field}"
ORDER BY COUNT(*) DESC
LIMIT 20;
```

#### C.2 Нормализация

| Исходное | Эталон (Золотая запись) | Правило |
|----------|------------------------|---------|
| "ООО Ромашка" | "ООО «Ромашка»" | Кавычки-ёлочки |
| "ромашка ООО" | "ООО «Ромашка»" | ОПФ в начало |
| "О.О.О. РОМАШКА" | "ООО «Ромашка»" | Убрать точки, caps |
| "OOO Romashka" | "ООО «Ромашка»" | Транслитерация |

#### C.3 SQL для сопоставления

```sql
-- Группировка похожих записей
SELECT
    UPPER(REGEXP_REPLACE(name, '[^а-яА-Яa-zA-Z0-9]', '', 'g')) AS normalized,
    ARRAY_AGG(DISTINCT name) AS variants,
    COUNT(DISTINCT name) AS variant_count,
    COUNT(*) AS total_records
FROM {table_name}
WHERE name IS NOT NULL
GROUP BY UPPER(REGEXP_REPLACE(name, '[^а-яА-Яa-zA-Z0-9]', '', 'g'))
HAVING COUNT(DISTINCT name) > 1
ORDER BY total_records DESC
LIMIT 30;
```

---

### Этап D: Метрики и дашборд

**Цель:** Создать DQ-дашборд через modusbi-mcp.

#### D.1 SQL для DQ-датасета

```sql
-- Основной DQ-датасет
SELECT
    rule_id,
    rule_type,
    field_name,
    total_rows,
    violations,
    ROUND(violations::numeric / NULLIF(total_rows, 0) * 100, 1) AS violation_pct,
    CASE
        WHEN violations = 0 THEN 'PASS'
        WHEN violations::numeric / NULLIF(total_rows, 0) < 0.05 THEN 'WARNING'
        ELSE 'FAIL'
    END AS status,
    priority
FROM dq_check_results
ORDER BY
    CASE priority WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
    violations DESC;
```

#### D.2 Компоненты DQ-дашборда

```
┌────────────────────────────────────────────────┐
│ KPI: DQ Score 67% | Completeness 78% |         │ y=0, h=6
│       Uniqueness 92% | Validity 54%            │
├───────────────────────┬────────────────────────┤
│ Bar Chart:            │ Text Block:            │ y=6, h=16
│ Нарушения по правилам │ Level 4 вывод:         │
│ (DQM-001..DQM-010)   │ драйверы, риски,       │
│                       │ рекомендации           │
├───────────────────────┼────────────────────────┤
│ Pie Chart:            │ Table:                 │ y=22, h=10
│ Распределение ошибок  │ Топ-20 записей-        │
│ по типам              │ нарушителей            │
└───────────────────────┴────────────────────────┘
```

**Workflow создания:**

```python
# 1. Датасет для DQ Score
dataset_result = mcp__modusbi__dataset_create_from_sql(
    sql_query="SELECT rule_id, rule_type, field_name, violations, violation_pct, status, priority ...",
    datasource_id=<datasource_id>,
    name="dq_profile_{table_name}"
)
dataset_id = dataset_result["dataset"]["id"]

# 2. Отчёт
report_id = mcp__modusbi__report_operations(action="create", name="DQ Dashboard: {table_name}", group_id=<group_id>)

# 3. KPI Panel
mcp__modusbi__component_crud(action="add", report_id=report_id, component_type="HsTotalsPanelV2",
    value_field="dq_score,completeness,uniqueness,validity",
    x=0, y=0, w=48, h=6)

# 4. Bar Chart + Conclusion
mcp__modusbi__component_crud(action="add_chart_with_conclusion", report_id=report_id,
    component_type="HsBarAMchartsChart",
    category_field="rule_id", value_field="violations",
    text_content="<div>..Level 4 вывод..</div>",
    h=16)

# 5. Pie + Table
mcp__modusbi__component_crud(action="add", report_id=report_id, component_type="HsPieAMchartsChart", ...)
mcp__modusbi__component_crud(action="add", report_id=report_id, component_type="HsTableReactabularChart", ...)
```

> ✅ **CF на статусах PASS/FAIL/WARN — работает напрямую**
> `=` и `~` (contains) поддерживают строковое value без `float()` coerce.
> ```python
> # SQL может содержать status как строку — numeric rank больше не нужен
> component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=<table>,
>   config_overrides={"field": "status", "operator": "=", "value": "FAIL",
>     "background": "#ffcdd2", "color": "#b71c1c"})  # FAIL = красный
> component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=<table>,
>   config_overrides={"field": "status", "operator": "=", "value": "WARN",
>     "background": "#fff9c4", "color": "#f57f17"})  # WARN = жёлтый
> # Substring match (например, "критич" в названии правила):
> component_styling(action="conditional_rule_add", report_id=<ID>, component_idx=<table>,
>   config_overrides={"field": "rule_type", "operator": "~", "value": "критич",
>     "background": "#ff0000"})
> ```
> Поддерживаемые операторы (проверено в коде фронта): `>, >=, <, <=, =, ~`
> (плюс алиасы `gt/gte/lt/lte/eq/contains`). НЕ работают: `!=`, regex,
> starts_with, in — MCP вернёт явный error с workaround'ом.
> Numeric rank колонка `priority` в SQL остаётся полезной для **range
> запросов** (e.g. `priority > 2`), но для точного совпадения по строке
> больше не требуется.

---

### Этап E: Визуальная верификация DQ-дашборда (playwright)

После создания DQ-дашборда проверь через скриншот:

```python
# 1. Открыть DQ-дашборд
browser_navigate(f"${MODUSBI_URL}/report/{report_id}")

# 2. Подождать рендеринг
browser_evaluate("await new Promise(r => setTimeout(r, 3000))")

# 3. Скриншот всего дашборда
browser_take_screenshot(name=f"dq_dashboard_{table_name}")

# 4. Проверить:
# - KPI Panel: DQ Score, Completeness, Uniqueness, Validity видны
# - Bar Chart: нарушения по правилам отсортированы DESC
# - Pie Chart: распределение ошибок по типам корректно
# - Table: топ-20 записей-нарушителей читаема
# - Text Block: Level 4 вывод с рекомендациями на месте

# 5. Скриншот KPI-панели отдельно (для отчёта)
browser_take_screenshot(
    name=f"dq_score_{table_name}",
    selector=".hs-component:first-child"
)
```

**Если проблемы:**
- DQ Score не рендерится → проверить агрегацию (sum vs avg) в KPI panel
- Bar Chart пустой → проверить что SQL для DQ-датасета вернул данные
- Цвета не семантические → PASS=зелёный, WARNING=жёлтый, FAIL=красный

---

## Output Format

### Финальный отчёт DQ Profiler

```markdown
# DQ Profile: {table_name}

## Общий DQ Score: {score}%

| Метрика | Значение | Статус |
|---------|----------|--------|
| Completeness | 78% | WARNING |
| Uniqueness | 92% | PASS |
| Validity | 54% | FAIL |
| Consistency | 85% | PASS |

## Топ-проблемы
1. Формат телефонов: 46% невалидных
2. Пустые ИНН: 22% NULL
3. Дубли по названию: 8%

## DQM-правила (сгенерированные)
[Таблица правил с SQL]

## Эталонные значения
[Таблица нормализации]

## DQ-дашборд
Report ID: {id}
URL: https://bi.company.com/report/{id}
```

---

## DQ Dimensions Reference

### 6 измерений качества данных (ISO 8000 / DAMA DMBOK)

| Dimension | Описание | Как считать | SQL-паттерн |
|-----------|----------|-------------|-------------|
| **Completeness** | Полнота: все ли поля заполнены | % NOT NULL | `COUNT(field) / COUNT(*)` |
| **Uniqueness** | Уникальность: нет ли дублей | % DISTINCT | `COUNT(DISTINCT field) / COUNT(field)` |
| **Validity** | Валидность: соответствие формату | % regex match | `COUNT(*) FILTER (WHERE field ~ pattern)` |
| **Accuracy** | Точность: соответствие реальности | Сверка с эталоном | `JOIN reference ON key` |
| **Consistency** | Консистентность: согласованность | Кросс-проверки | `WHERE a.field != b.field` |
| **Timeliness** | Актуальность: свежесть данных | Возраст записи | `WHERE updated_at < threshold` |

---

## Best Practices

1. **Начинай с Completeness** — это самое простое и часто самое полезное
2. **Формат важнее содержания** — если ИНН не 10/12 цифр, он точно неправильный
3. **Энтропия показывает грязь** — высокая энтропия в поле "Город" = много вариантов написания
4. **DQM-правила утверждает человек** — ИИ предлагает, data steward утверждает
5. **Пороги зависят от бизнеса** — 95% completeness может быть OK для адреса, но не для ИНН
6. **Мониторинг > разовый аудит** — метрики должны обновляться при каждом ETL-прогоне
7. **Градация приоритетов** — CRITICAL (нарушение закона) > HIGH (финансовый риск) > MEDIUM (неудобство)
