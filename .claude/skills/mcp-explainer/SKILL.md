---
name: mcp-explainer
description: Reference-скилл по архитектуре MCP (Model Context Protocol). Объясняет что такое MCP, как работает, чем лучше REST API для ИИ. Содержит примеры postgres-mcp и modusbi-mcp, mermaid-диаграммы, сравнительные таблицы. Используйте когда нужно объяснить MCP, подготовить слайды про архитектуру, описать мульти-агентную систему.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: architecture
---

# MCP Explainer: Архитектура Model Context Protocol

## Overview

Reference-скилл для объяснения MCP в контексте:
- Презентаций и докладов
- Технической документации
- Слайдов про архитектуру мульти-агента
- Сравнения с REST API подходом

**Источники:** этот скилл самодостаточен (ключевые тезисы инлайн ниже). Актуальная архитектура —
`docs/handbook/03-architecture.md` и `docs/handbook/01-overview.md`.

---

## When to Use This Skill

Используй как reference когда нужно:

- Объяснить **что такое MCP** и зачем он нужен
- Описать **архитектуру мульти-агента** (GigaChat + GPT + Claude)
- Подготовить **слайды про MCP** для презентации
- Сравнить **MCP vs REST API** для ИИ-интеграций
- Объяснить как **postgres-mcp** и **modusbi-mcp** работают

---

## Что такое MCP

**MCP (Model Context Protocol)** — открытый стандарт (Anthropic, 2024) для подключения LLM к внешним данным и инструментам.

### Ключевые концепции

| Термин | Что это | Аналогия |
|--------|---------|----------|
| **MCP Protocol** | Спецификация (документ, не код) | HTTP спецификация |
| **MCP SDK** | Библиотека кода (Python/TS/Go) | requests, axios |
| **MCP Client** | Компонент внутри Host App | Браузер |
| **MCP Server** | Ваш сервис с tools | Веб-сервер |
| **Host Application** | IDE или приложение с LLM | Chrome + DevTools |
| **Tool** | Функция, которую LLM может вызвать | REST endpoint |
| **Resource** | Данные, которые LLM может прочитать | GET endpoint |

### Главная идея

```
LLM НЕ может сама выполнить код.
LLM генерирует только ТЕКСТ.

MCP даёт LLM возможность ВЫЗЫВАТЬ функции:
  User: "Покажи продажи"
  LLM → MCP → SQL query → данные → LLM → ответ пользователю

Без MCP:
  User: "Покажи продажи"
  LLM: "Вот вам код: SELECT * FROM sales... Выполните его сами"
```

---

## Архитектура MCP

### Компоненты

```
┌─────────────────────────────────────────────────────┐
│  HOST APP (Claude Desktop / VS Code / ваше приложение)  │
│  ┌──────────┐    ┌──────────────┐                      │
│  │ LLM      │◄──►│ MCP Client   │                      │
│  │ (Claude) │    │ (встроен)    │                      │
│  └──────────┘    └──────┬───────┘                      │
└─────────────────────────┼──────────────────────────────┘
                          │ JSON-RPC (stdio/HTTP/SSE)
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ postgres │ │ modusbi  │ │ jira     │
        │ -mcp     │ │ -mcp     │ │ -mcp     │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             ▼            ▼            ▼
        PostgreSQL    ModusBI API    Jira API
```

### Последовательность вызовов

```
1. Host запускается → читает конфиг → стартует MCP-серверы
2. Client → Server: tools/list (какие инструменты есть?)
3. Server → Client: [{name: "query_db", inputSchema: {...}}, ...]
4. Host добавляет описание tools в system prompt LLM
5. User: "Покажи продажи"
6. LLM решает: "подходит tool query_db"
7. Client → Server: tools/call {name: "query_db", arguments: {sql: "SELECT..."}}
8. Server выполняет SQL → возвращает данные
9. Client → LLM: результат
10. LLM формирует ответ пользователю
```

---

## MCP vs REST API

### Проблема REST API для ИИ

| Аспект | REST API | MCP |
|--------|----------|-----|
| **LLM знает endpoints?** | Нет, нужен "клей" | Да, из tools/list |
| **Стандарт описания** | Swagger/OpenAPI (не для LLM) | inputSchema (для LLM) |
| **Интеграция** | Писать парсер для каждого API | Единый протокол |
| **Vendor lock-in** | Код привязан к API формату | Один сервер для всех LLM |
| **Цепочки вызовов** | Ручная оркестрация | LLM сама планирует |
| **Discovery** | Нужно знать URLs заранее | tools/list автоматически |

### Формула масштабирования

```
Без MCP: N клиентов x M сервисов = N*M интеграций
С MCP:   N клиентов + M серверов = N+M компонентов

Пример:
5 LLM (Claude, GPT, Gemini, GigaChat, YandexGPT)
10 сервисов (DB, Jira, Git, BI, Email, ...)

Без MCP: 5 x 10 = 50 интеграций
С MCP:   5 + 10 = 15 компонентов (3x экономия)
```

---

## Пример: как устроен MCP Server

### Минимальный сервер (Python, FastMCP)

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool()
def get_users(limit: int = 10) -> list:
    """Get list of users"""
    return db.query("SELECT * FROM users LIMIT %s", [limit])

mcp.run()
```

### Что делает декоратор `@mcp.tool()`

1. Читает имя функции → `name: "get_users"`
2. Читает docstring → `description: "Get list of users"`
3. Читает типы параметров → `inputSchema: {limit: {type: "integer"}}`
4. Регистрирует в реестре tools

### Как LLM узнаёт про tools

```
LLM сама по себе НЕ знает про MCP!

Host App при запуске:
1. Запускает MCP Server как subprocess
2. Спрашивает tools/list
3. Получает JSON с описанием tools
4. Добавляет описание tools в system prompt LLM

Теперь LLM "видит" в промпте:
"У тебя есть tools: get_users(limit: int) - Get list of users"
И решает когда их использовать.
```

---

## Конкретные MCP-серверы проекта

### postgres-mcp

**Что делает:** Подключается к PostgreSQL, выполняет SQL запросы.

**Tools:**
- `query(sql)` — выполнить SELECT
- `describe_table(table_name)` — получить схему таблицы
- `list_tables()` — список таблиц

**Использование в проекте:**
- Профилирование данных: анализ типов, NULL%, распределений
- NL2SQL: пользователь говорит "покажи дубли" → ИИ генерирует SQL
- DQ-проверки: проверка полноты, уникальности, формата

### modusbi-mcp

**Что делает:** Управляет дашбордами, отчётами, компонентами в Модус:Аналитический портал.

**Tools:**
- `instance_operations(action)` — информация о текущем портале
- `report_operations(action)` — CRUD отчётов
- `reportgroup_operations(action)` — группы отчётов
- `component_crud(action)` — CRUD компонентов (графики, таблицы, KPI)
- `component_filters(action)` — фильтры и cascade
- `component_axes(action)` — drill-down, calc fields, pivot links
- `component_styling(action)` — conditional formatting, maps
- `dataset_operations(action)` — управление датасетами
- `dataset_create_from_sql(sql)` — создать датасет из SQL
- `dataset_query(dataset_id)` — получить данные датасета
- `query_batch(queries)` — выполнить несколько readonly-запросов
- `sql_query_validate(sql)` — проверить SQL до создания датасета
- `style_operations(action)` — CSS темизация и apply_theme
- `report_template(action)` — список/scaffold готовых шаблонов
- `datasource_operations(action)` — список и управление источниками данных
- `preflight_check_datasource(datasource_id)` — глубокая проверка datasource
- `batch_operations(action)` — batch-действия с компонентами/экспортом
- `data_export_operations(action)` — экспорт данных компонента
- `security_operations(action)` — Row Level Security

**Использование в проекте:**
- Создание дашбордов DQ-метрик
- Визуализация результатов профилирования
- Мониторинг качества данных в реальном времени

---

## Мульти-агентная архитектура

### Архитектура проекта Модус

```
┌────────────────────────────────────────────────┐
│           ПОЛЬЗОВАТЕЛЬ (аналитик / DQ-инженер)    │
└─────────────────────┬──────────────────────────┘
                      │ естественный язык
                      ▼
┌────────────────────────────────────────────────┐
│  HOST APP (Claude Code / Cursor / VS Code)     │
│                                                │
│  LLM: Claude Opus 4.6 (основной)              │
│       GigaChat (для русского NLP)              │
│       GPT-4 (fallback)                         │
│                                                │
│  MCP Client (встроен)                          │
└─────────────────────┬──────────────────────────┘
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ postgres │ │ modusbi  │ │ jira     │
   │ -mcp     │ │ -mcp     │ │ -mcp     │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        ▼            ▼            ▼
   PostgreSQL   ModusBI API   Jira Cloud
   (хранилище)  (BI-портал)   (задачи)
```

### Model-agnostic подход

MCP-серверы не зависят от конкретной LLM:
- Один и тот же `modusbi-mcp` работает с Claude, GPT, GigaChat
- Переключение LLM не требует изменения серверов
- Каждая LLM имеет свои сильные стороны:
  - Claude: длинный контекст, structured output
  - GigaChat: русский язык, российские реалии
  - GPT-4: широкая база знаний

---

## Для слайдов презентации

### Слайд "Что такое MCP" (простой)

**Месседж:** MCP = USB для ИИ

```
Как USB: один разъём → подключай любые устройства
Как MCP: один протокол → подключай ИИ к любым данным

USB:  Компьютер ──USB── Принтер, Камера, Телефон...
MCP:  LLM ──MCP── БД, API, Файлы, Дашборды...
```

### Слайд "Зачем бизнесу MCP"

| Без MCP | С MCP |
|---------|-------|
| Каждая интеграция = свой код | Один протокол для всего |
| Привязка к конкретной LLM | Работает с любой LLM |
| Недели на интеграцию | Часы на подключение |
| N x M интеграций | N + M компонентов |

### Слайд "Как ИИ работает с данными через MCP"

```
1. Аналитик: "Проверь качество справочника контрагентов"
2. LLM → postgres-mcp: SELECT column_name, data_type FROM information_schema...
3. LLM → postgres-mcp: SELECT COUNT(*), COUNT(DISTINCT inn), ... FROM contractors
4. LLM анализирует → находит: 12% дублей, 23% пустых ИНН
5. LLM → modusbi-mcp: создать дашборд с метриками DQ
6. Аналитик видит: готовый дашборд за 3 минуты
```

### Слайд "Цепочка вызовов в MCP"

```
User: "Создай дашборд качества данных"

LLM планирует цепочку:
  1. postgres-mcp → получить схему таблицы
  2. postgres-mcp → проанализировать данные (полнота, дубли)
  3. modusbi-mcp  → создать датасет с SQL
  4. modusbi-mcp  → создать отчёт
  5. modusbi-mcp  → добавить KPI панель
  6. modusbi-mcp  → добавить графики
  7. modusbi-mcp  → добавить выводы

Результат: 7 tool-вызовов, 3 минуты, готовый дашборд
```

---

## Ключевые сообщения для презентации

1. **MCP = открытый стандарт, не vendor lock-in**
2. **LLM сама выбирает какие tools вызвать** (не hardcoded логика)
3. **Один MCP-сервер работает с любой LLM** (model-agnostic)
4. **Готовые серверы: 1000+ в каталогах** (smithery.ai, mcphub.io)
5. **Безопасность: серверы локальные**, контроль доступа на уровне Host
6. **Цепочки вызовов: LLM сама строит pipeline** из отдельных tools
