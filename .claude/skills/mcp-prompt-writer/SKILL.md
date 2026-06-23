---
name: mcp-prompt-writer
description: "Написание и аудит MCP промптов для ModusBI: создание prompt definitions в prompts.py с правильными tool calls, action names и параметрами. Используйте когда нужно добавить новый промпт в MCP сервер, обновить существующий промпт, провести аудит промптов на соответствие реальному API."
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: mcp-development
---

# MCP Prompt Writer: Создание и аудит MCP промптов

> Skill для разработчиков MCP сервера ModusBI — написание prompt definitions в `app/prompts.py`

## Назначение

Используй этот skill когда нужно:
- Добавить новый промпт в MCP сервер (app/prompts.py)
- Обновить существующий промпт
- Провести аудит промптов на соответствие реальному API
- Проверить что action names, tool names и параметры в промптах корректны

## Архитектура промптов

### Файлы

| Файл | Роль |
|------|------|
| `app/prompts.py` | Определения промптов (get_prompts) + генераторы сообщений |
| `app/prompts/*.md` | Документация (8 файлов) |
| `app/server.py` | Регистрация промптов через FastMCP |

### Структура промпта в prompts.py

Каждый промпт состоит из 3 частей:

**1. Registration (в get_prompts())**
```python
{
    "name": "prompt_name",
    "description": "Описание на русском",
    "arguments": [
        {"name": "report_id", "description": "ID отчёта", "required": True},
        {"name": "optional_param", "description": "Опционально", "required": False}
    ]
}
```

**2. Generator function**
```python
def prompt_name_prompt(report_id: int, optional_param: str | None = None) -> list[dict]:
    return [{
        "role": "user",
        "content": {
            "type": "text",
            "text": f"""Инструкция для LLM...

1. Первый шаг (tool_name action="action_name" param={report_id})
2. Второй шаг...
..."""
        }
    }]
```

**3. Dispatcher (в get_prompt_messages())**
```python
case "prompt_name":
    if err := _require("report_id"):
        return err
    return prompt_name_prompt(
        report_id=int(args["report_id"]),
        optional_param=args.get("optional_param")
    )
```

---

## Правила написания промптов

### 1. Action names — SINGULAR vs PLURAL

**CRITICAL**: report_operations использует MIX форм:

| Plural (список) | Singular (CRUD) |
|-----------------|-----------------|
| `variables_list` | `variable_add` |
| `categories_list` | `category_add` |
| `groups_list` | — |
| `components_list` | — |

Всегда проверяй реальные case branches в `app/tools/report_operations.py`.

### 2. component_* split tools (4 tools)

Актуальное разделение (component_operations — internal dispatcher, MCP tool removed in , file remains as dispatcher):

**component_crud** — CRUD/layout/introspection:
```
types_list, get, add, add_text_block, add_chart_with_conclusion, update, delete, data
layout_update, layout_get_breakpoints, layout_update_breakpoint, swap, copy
list_slugs, list_presets
help  (returns action reference)
```

**component_filters** — фильтры:
```
set_global_filter, reset_global_filters
filter_fields_list, filter_field_add, filter_field_remove, filter_set_cascade
filters_grid_layout
help
```

**component_axes** — calc fields, drill, pages, pivot links, tabs buttons, CF, geo:
```
calc_fields_list, calc_field_add, calc_field_update, calc_field_remove
page_list, page_add, page_remove, page_rename
pivot_link_set, pivot_link_remove
drill_get, drill_add_level, drill_delete_level, drill_change_level, drill_toggle_date_range, drill_set_field
tabs_button_list, tabs_button_add, tabs_button_delete
conditional_rule_add/list/delete, geodata_list, map_set_geokeys, map_get_geokeys
help
```

**component_styling** — подмножество (conditional formatting, sort, map geo):
```
conditional_rule_add/list/delete, field_sort_set
geodata_list, map_set_geokeys, map_get_geokeys, help
```

> Если не уверены в параметрах — вызовите `<tool>(action="help", value_field="<action_name>")`.

### 3. config_overrides формат

```python
config_overrides={"slug.key": value, "slug.key2": value2}
```

Slug-и из `app/tools/config_schema.py` SLUG_SCHEMA. Формат flat dict.

### 4. RULE_PROPS (conditional formatting)

```python
config_overrides={
    "rules.{index}.name": "Rule name",
    "rules.{index}.fieldId": "field_name",
    "rules.{index}.cons.operator": ">=",  # >=, <=, >, <, =
    "rules.{index}.cons.value": 100,
    "rules.{index}.color": "#ffffff",
    "rules.{index}.background": "#f44336",
}
```

### 5. Presets

6 штук: `minimal`, `presentation`, `dashboard`, `dark`, `print`, `kpi`

### 6. Тексты на русском

Описания и промпты пишем на русском языке.

---

## Anti-patterns: несуществующее API (галлюцинации)

LLM регулярно «придумывает» параметры, которых нет в коде. Список проверенных по `app/tools/` галлюцинаций — НЕ использовать в промптах:

### `security_operations(action="enable", filter=...)` — НЕТ параметра `filter`
Реальная сигнатура: `dataset_id`, `enabled`, `rls_query`. Чтобы задать фильтр — отдельный action:
```python
security_operations(action="update_filter", dataset_id=5, rls_query="user_id = :current_user_id")
```

### `report_options.refresh_interval` / `report_options.notification` — НЕ существуют
Реальные options через `report_operations(action="update_options", ...)`:
`cell_mode`, `allow_overlap_mode`, `free_pane_movement`, `no_gap_mode`, `recalculated_cell_mode`, `grouping_mode`. Auto-refresh / notifications в API нет.

### `set_global_filter` cross-report — НЕ работает
Принимает `report_id` + `component_idx`, изменяет фильтр **внутри одного отчёта**. Cross-report drill через MCP сделать нельзя.

**ВАЖНО:** для реального глобального фильтра передавать
`alias=...` параметр — он пишет в `report.globalFilters[alias].selected`
(это то что фронт реально читает). Без alias обновляется только локальный
`cfg.selectedValue` одного компонента, и фронт фильтр не применит к остальным.
Узнать актуальный alias: `component_filters(action="filter_fields_list", ...)`.

```python
# Правильно:
mcp__modusbi__component_filters(
    action="set_global_filter",
    report_id=<REPORT_ID>, component_idx=<FILTER_IDX>,
    value_field="Москва,СПб", alias="Регион"
)
```

### `pivot_link_set` на Bar/Line — НЕ работает
В коде явный guard:
```python
if "pivot" not in comp_type.lower():
    return {"error": "...not a PivotChart"}
```
Только `HsPivotChart`. Для Bar/Line drill-through нужен `linkBy` слаг через `component_crud(action="update")`.

### `conditional_rule_add` со строковым `value` — работает ограниченно
Строки поддержаны для точного совпадения `=` и contains `~`
(`contains`). Numeric-операторы `>, >=, <, <=` остаются только для чисел.
Не поддержаны: `!=`, `regex`, `starts_with`, `ends_with`, `in`.

```python
# Правильно: строковое exact match
component_styling(action="conditional_rule_add", report_id=35, component_idx=4,
  config_overrides={"field": "status", "operator": "=", "value": "FAIL",
    "background": "#ffcdd2", "color": "#b71c1c"})

# Правильно: substring match
component_styling(action="conditional_rule_add", report_id=35, component_idx=4,
  config_overrides={"field": "rule_type", "operator": "~", "value": "критич",
    "background": "#ff0000"})
```

Numeric rank-колонка в SQL нужна только для ranges или неподдержанных
операторов.

### `tabs_button_add` — `title` ЕСТЬ в schema, НО только в `component_axes`
Это **не** галлюцинация — частая ошибка вызова через неправильный tool:
- ❌ `component_crud(action="tabs_button_add", title=..., ...)` — action не входит в `ComponentCrudAction`
- ❌ `component_styling(action="tabs_button_add", ...)` — то же
- ✅ `component_axes(action="tabs_button_add", report_id=..., component_idx=..., title="Home", config_overrides={"link":"/report/1","fill_color":"#1976d2"})`

`tabs_button_*` живёт **только** в `component_axes`. Если получаешь «нет параметра title» — перезагрузи schema (ToolSearch `select:mcp__modusbi__component_axes`).

> **Правило для промптов:** перед добавлением tool call в промпт — `grep` в `app/tools/<module>.py` на предмет реального `case "<action>"` и его параметров. Не доверяй памяти — версии меняются.

---

## Чек-лист аудита промпта

### Cross-reference check

- [ ] Все tool names существуют в server.py
- [ ] Все action names существуют в соответствующем match/case dispatcher
- [ ] Параметры промпта совпадают с параметрами tool
- [ ] Формат config_overrides корректен (flat dict, slug.key)
- [ ] RULE_PROPS используют cons.operator/cons.value (не flat cons)
- [ ] Preset names из реального PRESETS dict
- [ ] Нет deprecated ссылок (relationship_operations)

### Functional check

- [ ] get_prompts() возвращает правильное число промптов
- [ ] Каждый промпт имеет name, description, arguments[]
- [ ] get_prompt_messages() работает для всех промптов с корректными args
- [ ] Missing required args возвращает ошибку
- [ ] Unknown prompt возвращает ошибку
- [ ] Messages формат: [{role: "user", content: {type: "text", text: "..."}}]

### Content check

- [ ] Промпт содержит пошаговую инструкцию для LLM
- [ ] Каждый шаг указывает конкретный tool + action
- [ ] Есть примеры параметров
- [ ] Текст на русском языке
- [ ] Нет hardcoded IDs (используются переменные из аргументов)

---

## Шаблон нового промпта

```python
# 1. В get_prompts() добавить:
{
    "name": "new_prompt_name",
    "description": "Описание промпта на русском",
    "arguments": [
        {"name": "report_id", "description": "ID отчёта", "required": True},
        # ... другие аргументы
    ]
}

# 2. Generator:
def new_prompt_name_prompt(report_id: int) -> list[dict]:
    """Generate messages for new_prompt_name prompt."""
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги выполнить [задачу] для отчёта ID={report_id}.

1. Первый шаг (tool_name action="action" report_id={report_id})
2. Второй шаг ...
3. ...

Начни с [первый шаг]."""
            }
        }
    ]

# 3. В get_prompt_messages() добавить case:
case "new_prompt_name":
    if err := _require("report_id"):
        return err
    return new_prompt_name_prompt(
        report_id=int(args["report_id"])
    )
```

---

## Тестирование

```python
# Минимальный тест:
from app.prompts import get_prompts, get_prompt_messages

prompts = get_prompts()
assert len(prompts) == EXPECTED_COUNT

# Для каждого промпта:
msgs = get_prompt_messages("prompt_name", {"report_id": "35"})
assert len(msgs) == 1
assert msgs[0]["role"] == "user"
assert "action=" in msgs[0]["content"]["text"]

# Error cases:
msgs = get_prompt_messages("prompt_name", {})  # missing required
assert "Ошибка" in msgs[0]["content"]["text"]
```
