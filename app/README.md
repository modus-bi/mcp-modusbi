# ModusBI MCP Server

MCP (Model Context Protocol) сервер для интеграции LLM-клиентов с аналитическим порталом ModusBI.

## Текущее состояние

| Область | Актуально на 2026-06-04 |
|---|---|
| Public MCP tools | 19 tools в `app/server.py` |
| Component model | `component_operations` больше не public MCP tool; это внутренний dispatcher для split tools |
| Split component tools | `component_crud`, `component_filters`, `component_axes`, `component_styling` |
| Visual config schema | 339 slug в `SLUG_SCHEMA`, 28 локальных `CHART_TYPE_MAP` mapping |
| Portal model | Один процесс = один портал; multi-portal через несколько `mcpServers` entries |
| Default security mode | `readonly`; write-операции требуют явный `--readwrite` |

## Установка

```bash
pip install -r requirements.txt
```

Скомпилированный бинарь: `build/dist/<version>/<os>-<arch>/modusbi-mcp-server[.exe]` после сборки (например `build/dist/1.0.0/linux-x86_64/`). Подробности в [../build/BUILD.md](../build/BUILD.md) и [../build/INSTALL.md](../build/INSTALL.md).

## Запуск

```bash
python -m app.server                         # readonly по умолчанию
python -m app.server --readwrite             # разрешить create/update/delete
python -m app.server --demo                  # readonly + query row/batch limits
python -m app.server --readonly              # явное readonly
python -m app.server --log-format json       # structured logs в stderr
```

Для production используйте hard ceiling:

```bash
python -m app.server --readonly --security-ceiling readonly
```

## Конфигурация

Сервер читает env vars при старте. `.env` автоматически не загружается.

| Env var | Обязательно | Описание |
|---|:---:|---|
| `MODUSBI_URL` | да | URL портала ModusBI |
| `MODUSBI_USERNAME` | да | Логин |
| `MODUSBI_PASSWORD` | да | Пароль |
| `MODUSBI_INSTANCE_NAME` | нет | Метка инстанса для логов и `instance_operations` |
| `MODUSBI_SECURITY_CEILING` | нет | Потолок режима: `readonly`, `demo`, `readwrite` |
| `MODUSBI_EXPORT_DIR` | нет | Каталог локальных экспортов |
| `MODUSBI_LOG_FORMAT` | нет | `text` или `json` |

Multi-portal сценарии решаются на уровне MCP-клиента: несколько `mcpServers` entries, каждая со своими env vars.

## Public MCP Tools

| # | Tool | Actions | Назначение |
|---:|---|---:|---|
| 1 | `instance_operations` | 2 | Информация о текущем single-instance портале |
| 2 | `report_operations` | 24 | Отчёты: CRUD, summary, export, variables/categories/options/global filters |
| 3 | `dataset_operations` | 7 | Семантический слой: CRUD и поля датасета |
| 4 | `component_crud` | 16 | Компоненты: add/update/delete/get/data/layout/slugs/presets |
| 5 | `component_filters` | 8 | Фильтры, global filters, cascade, grid layout |
| 6 | `component_axes` | 26 | Calc fields, pages, drill-down, pivot links, tabs, часть map/CF actions |
| 7 | `component_styling` | 8 | Conditional formatting, sort, map geokeys |
| 8 | `datasource_operations` | 8 | Источники данных: list/get/tables/fields/check; write-actions возвращают unsupported |
| 9 | `dataset_query` | function | SQL-like запрос к датасету |
| 10 | `query_batch` | function | Несколько `dataset_query` одним вызовом |
| 11 | `sql_query_validate` | function | Проверка SQL перед созданием датасета |
| 12 | `dataset_create_from_sql` | function | Создать датасет из SQL и метаданных |
| 13 | `preflight_check_datasource` | function | Глубокая проверка datasource перед работой |
| 14 | `style_operations` | 6 | Report CSS, validation, examples, `apply_theme` |
| 15 | `reportgroup_operations` | 6 | Папки/группы отчётов |
| 16 | `data_export_operations` | 3 | CSV/XLSX экспорт данных компонента и info |
| 17 | `batch_operations` | 5 | Batch add/delete/layout/style/report export |
| 18 | `report_template` | 3 | `list`, `preview`, `scaffold` готовых шаблонов |
| 19 | `security_operations` | 6 | Row Level Security status/enable/disable/update/test |

### Component split

`component_operations` не вызывается клиентом напрямую. Агент должен выбирать один из public split tools:

| Нужно сделать | Tool |
|---|---|
| Добавить/обновить/удалить компонент, поменять layout, получить данные | `component_crud` |
| Добавить поля фильтрации, выставить значение фильтра, cascade | `component_filters` |
| Calc fields, pages, drill-down, tabs, pivot link | `component_axes` |
| Conditional formatting, sort, map geokeys | `component_styling` |

Пример:

```python
component_crud(
    action="add",
    report_id=585,
    component_type="HsBarAMchartsChart",
    title="Продажи по регионам",
    dataset_id=3,
    category_field="region",
    value_field="sales",
    aggregation="sum",
    x=0,
    y=0,
    w=24,
    h=10,
)
```

## Report Templates

`report_template` умеет scaffold-ить готовые отчёты:

| Template | Компонентов | Состав |
|---|---:|---|
| `kpi_dashboard` | 10 | 3 filters, 4 KPI, chart, treemap, table |
| `ranking` | 7 | 2 filters, top-N bar, treemap, table, 2 comparison bar charts |
| `comparison` | 10 | 2 filters, 4 KPI, stacked bar, pie, text, table |
| `factor_analysis` | 7 | 2 filters, 3 KPI, bar, table |
| `geo_analytics` | 9 | filters, KPI, map, chart/table |
| `simple` | 3 | filter, chart, table |

## Режимы безопасности

| Операция | readonly | readwrite | demo |
|---|:---:|:---:|:---:|
| Read/list/get/summary/validate | да | да | да |
| Create/update/delete/add/remove/move | нет | да | нет |
| SQL-like read query | да | да | да, row/batch limits |
| Export | да | да | да; per-hour export limit currently not enforced |
| Batch write operations | нет | да | нет |
| RLS write actions | нет | да | нет |

`--security-ceiling readonly` жёстко блокирует write даже при случайном `--readwrite`.

## Интеграция с Claude Desktop

```json
{
  "mcpServers": {
    "modusbi-prod-readonly": {
      "command": "/usr/local/bin/modusbi-mcp-server",
      "args": ["--readonly", "--security-ceiling", "readonly"],
      "env": {
        "MODUSBI_URL": "https://your-portal.modusbi.ru",
        "MODUSBI_USERNAME": "your_login",
        "MODUSBI_PASSWORD": "your_password",
        "MODUSBI_INSTANCE_NAME": "prod"
      }
    }
  }
}
```

Запуск из исходников:

```json
{
  "command": "/path/to/mcp/.venv/bin/python",
  "args": ["-m", "app.server", "--readonly", "--security-ceiling", "readonly"],
  "cwd": "/path/to/mcp"
}
```

## Prompts

Сервер также регистрирует 10 MCP prompts: `create_dashboard`, `style_report`, `query_data`, `export_report`, `analyze_dataset`, `customize_component`, `add_filters`, `add_conditional_formatting`, `manage_variables`, `create_report_from_template`.

Документация prompt-сценариев лежит в [../docs/prompts/README.md](../docs/prompts/README.md).

## Структура app

```text
app/
├── server.py                    # FastMCP server, tools, prompts, CLI
├── core/
│   ├── instances.py             # Single-instance portal manager + HTTP pool
│   ├── security.py              # SecurityMode + check_action + ceiling
│   ├── exceptions.py            # Error helpers and masking
│   └── validation.py            # URL/HTML validation helpers
├── tools/
│   ├── action_types.py          # Literal action enums for schema
│   ├── component_crud.py        # Component CRUD/layout/data
│   ├── component_filters.py     # Filter/globalFilter/cascade helpers
│   ├── component_axes.py        # Split wrapper for axes actions
│   ├── component_operations.py  # Internal dispatcher, not public MCP tool
│   ├── config_schema.py         # 339 slug registry + CHART_TYPE_MAP
│   ├── report_template.py       # Scaffold templates
│   ├── query_execute.py         # dataset_query/query_batch/sql validation
│   ├── export_data.py           # Component data export
│   └── *_operations.py          # Report, dataset, style, RLS, batch, groups
├── prompts.py                   # Built-in @mcp.prompt definitions
└── tests/                       # Smoke/unit tests
```
> Сборка бинаря — в `build/` (корень репозитория); документация промпт-сценариев — в `docs/prompts/`.

## Дополнительная документация

- [../README.md](../README.md) — быстрый старт проекта.
- [PROMPTS.md](PROMPTS.md) — документация промптов.
- [../.claude/skills/README.md](../.claude/skills/README.md) — каталог скиллов: готовые сценарии работы.
- [../MCP_SERVERS.md](../MCP_SERVERS.md) — необходимые MCP-серверы для скиллов.

## Лицензия

Proprietary © ModusBI
