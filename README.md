# ModusBI MCP Server

MCP (Model Context Protocol) сервер для интеграции LLM-клиентов (ИИ-ассистентов) с аналитическим порталом ModusBI.

> ⚠️ **Важно перед использованием.** Операции над отчётами, датасетами и компонентами применяются
> сразу и **необратимы** — встроенной отмены, истории правок или отката изменений нет. Безопасность
> доступов при работе с ИИ-ассистентом (креденшалы портала, права учётной записи, prompt-injection) —
> **полностью на стороне пользователя**. Перед работой прочитайте **[DISCLAIMER.md](DISCLAIMER.md)**.
>
> ℹ️ **Одна учётная запись портала = один сеанс.** Заведите для MCP **отдельного пользователя портала**:
> если сервер работает под той же учёткой, под которой вы сами зашли в браузер, один из сеансов будет
> завершён («выкинет»). Подробнее — [DISCLAIMER.md](DISCLAIMER.md).

> **С чего начать — по вашей роли:**
>
> - **Аналитик / Пользователь** — работать с отчётами через ассистента: от «подключить готовый сервер и пользоваться» до «строить дашборды» → [подключение](docs/start/connect.md) · [руководство](docs/start/analyst.md)
> - **DevOps** — развернуть и эксплуатировать сервер → [установка из исходников](docs/start/for-devops.md)
> - **Разработчик** — дорабатывать сервер (слаги, билдеры, инструменты) → [руководство разработчика](docs/start/developer.md)
> - **Тестировщик** — проверять отрисовку отчётов → [руководство тестировщика](docs/start/tester.md)
>
> Полный маршрут по ролям — [docs/start/](docs/start/README.md); общая карта документации — [docs/README.md](docs/README.md).

## Быстрый старт

```bash
# Установка зависимостей
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Настройка для локального запуска из shell
# Сервер читает env vars напрямую; .env автоматически не загружается.
export MODUSBI_URL=https://your-portal.modusbi.ru
export MODUSBI_USERNAME=your_user
export MODUSBI_PASSWORD=your_password

# Запуск: readonly по умолчанию
python -m app.server
```

Для Claude Desktop / Cursor / Claude Code обычно не нужны shell `export`:
задайте эти переменные в `mcpServers.*.env`, как показано ниже.

### Запуск через готовый бинарник (без установки Python)

Для большинства пользователей это проще, чем ставить Python и зависимости.

**Где скачать.** Откройте страницу релизов
[github.com/modus-bi/mcp-modusbi/releases](https://github.com/modus-bi/mcp-modusbi/releases)
(прямая ссылка на последнюю — [/releases/latest](https://github.com/modus-bi/mcp-modusbi/releases/latest)).
Выберите нужную версию (последняя — `v1.0.0`) и в её разделе **Assets** возьмите файл под свою ОС
(здесь `<версия>` — номер релиза) и соседний `.sha256`:

| ОС | Файл |
|---|---|
| Linux x86-64 | `modusbi-mcp-server-<версия>-linux-x86_64` |
| Windows x86-64 | `modusbi-mcp-server-<версия>-windows-x86_64.exe` |
| macOS (Apple Silicon) | `modusbi-mcp-server-<версия>-macos-arm64` |

**Как подключить.**

1. Скачайте файл под свою ОС и проверьте контрольную сумму по соседнему `.sha256` (как именно —
   в [подключении сервера](docs/start/connect.md), Шаг 1).
2. На Linux/macOS сделайте файл исполняемым: `chmod +x <файл>`.
3. Укажите **абсолютный путь** к бинарнику в `command` MCP-клиента вместо `python`:

```json
{
  "mcpServers": {
    "modusbi": {
      "command": "/абсолютный/путь/к/modusbi-mcp-server",
      "args": ["--readonly"],
      "env": {
        "MODUSBI_URL": "https://your-portal.example.com",
        "MODUSBI_USERNAME": "your_api_user",
        "MODUSBI_PASSWORD": "your_api_password"
      }
    }
  }
}
```

В Windows укажите путь к `modusbi-mcp-server.exe`. Установка и smoke-проверка бинарника —
[build/INSTALL.md](build/INSTALL.md), самостоятельная сборка — [build/BUILD.md](build/BUILD.md).

## Token Usage Observability

Видимость и бюджет потребления токенов tool-поверхностью для LLM-клиентов:

```bash
python scripts/measure_tokens.py                      # markdown в stdout
python scripts/measure_tokens.py --profiles           # Anthropic/OpenAI/rest profiles
python scripts/simulate_flows.py                       # 5 типичных flow
python scripts/analyze_help_savings.py                 # help-action savings
python scripts/snapshot_tokens.py --tag my-release     # snapshot + trend README
bash scripts/run_token_budget.sh                       # CI gate (budget.yml)
```

Snapshot'ы в `docs/token-usage/*.json`, trend-таблица в `docs/token-usage/README.md`, лимиты в `docs/token-usage/budget.yml`.

> Актуальный замер (детали — [docs/token-usage/README.md](docs/token-usage/README.md)): **17,277 tokens** compact `tools/list` envelope и **21,603 tokens** sum-of-parts. HOT-набор Tool Search: **7,390** (Anthropic) и **7,459** (OpenAI) compact tokens.

## MCP Scorecard (качество tools для LLM)

Сервер проверяется детерминированным скорбоардом [MCP-Scorecard](https://github.com/aak204/MCP-Scorecard).

```bash
bash scripts/run_scorecard.sh              # score >= 90, отчёт в .scorecard/
MIN_SCORE=95 bash scripts/run_scorecard.sh # поднять порог

# Человекочитаемое summary:
python scripts/scorecard_summary.py .scorecard/scorecard.json
```

Baseline отчёты сохраняются в `docs/scorecard/`. Текущий результат: **100/100** (0 findings во всех 4 категориях — Conformance, Security, Ergonomics, Metadata).

## Режимы безопасности

```bash
python -m app.server              # readonly (по умолчанию)
python -m app.server --readwrite  # разрешить create/update/delete
python -m app.server --demo       # readonly + query row/batch limits
python -m app.server --readonly   # явное readonly (эквивалент дефолта)
```

> ⚠️ **Дефолт безопасности:** режим по умолчанию — `readonly`, чтобы автономный LLM-клиент не мог случайно изменить данные. Для create/update/delete режим `--readwrite` нужно включать явно. Изменения **необратимы** (см. [DISCLAIMER.md](DISCLAIMER.md)).
>
> **Потолок безопасности** задаётся на процесс — флагом `--security-ceiling` или переменной окружения `MODUSBI_SECURITY_CEILING`. Для production используйте `--readonly --security-ceiling readonly`, чтобы заблокировать включение `--readwrite`.
>
> `--demo` добавляет ограничения на объём запросов (строки и пакеты).

## Интеграция с Claude Desktop

Добавьте в `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "modusbi": {
      "command": "python",
      "args": ["-m", "app.server"],
      "cwd": "/path/to/mcp",
      "env": {
        "MODUSBI_URL": "https://your-portal.example.com",
        "MODUSBI_USERNAME": "your_user",
        "MODUSBI_PASSWORD": "your_password",
        "MODUSBI_INSTANCE_NAME": "sandbox",
        "MODUSBI_SECURITY_CEILING": "readonly"
      }
    }
  }
}
```

## Структура проекта

```
mcp/
├── app/                        # Основной пакет MCP-сервера
│   ├── server.py               # FastMCP сервер
│   ├── prompts.py              # Prompt-шаблоны (инлайн, без .md)
│   ├── core/
│   │   ├── instances.py        # InstanceManager (один процесс = один портал)
│   │   ├── security.py         # SecurityMode
│   │   └── exceptions.py       # Исключения
│   ├── tools/                  # Реализация инструментов
│   └── tests/                  # Тесты
├── build/                      # Сборка бинарника (PyInstaller) — build/BUILD.md
├── docs/                       # Документация
├── .claude/                    # Скиллы и агенты для AI-клиентов
├── pyproject.toml              # Конфигурация проекта
├── requirements.txt            # Зависимости
├── requirements-dev.txt        # Dev-зависимости
├── .env.example                # Пример переменных окружения
├── .mcp.example.json           # Пример конфигурации MCP-клиента
└── .gitignore
```

## Документация

Полный навигатор — **[docs/README.md](docs/README.md)**. По разделам:

**С чего начать**
- [docs/start/](docs/start/README.md) — подключение сервера к ИИ-клиенту и установка из исходников (DevOps), режимы работы сервера
- [docs/architecture/concepts/](docs/architecture/concepts/what-is-mcp.md) — что такое MCP, протокол и RPC, архитектура, слаги/JSON, render-contract
- [docs/GLOSSARY.md](docs/GLOSSARY.md) — глоссарий терминов

**Handbook'и по ролям**
- [Аналитик / Пользователь](docs/start/analyst.md) · [Разработчик](docs/start/developer.md) · [Тестировщик](docs/start/tester.md)

**Справочники**
- [docs/architecture/tools/](docs/architecture/tools/README.md) — инструменты MCP и их actions ([подробный справочник](docs/architecture/tools/reference.md))
- [docs/architecture/components/](docs/architecture/components/README.md) — типы компонентов, JSON-конфиги, слаги, рецепты данных
- [docs/prompts/](docs/prompts/README.md) — встроенные промпт-сценарии
- [docs/skills/](docs/skills/README.md) — каталог скиллов по группам
- [docs/architecture/versioning/](docs/architecture/versioning/README.md) — соответствие слагов и совместимость версий

**Готовность и качество**
- [docs/architecture/readiness/](docs/architecture/readiness/README.md) — оценка готовности tools и компонентов, findings
- [docs/scorecard/](docs/scorecard/README.md) — MCP-Scorecard
- [docs/architecture/](docs/architecture/README.md) — экономия токенов, модель безопасности, слой данных, эксплуатация

**В корне репозитория**
- [app/README.md](app/README.md) — API инструментов · [app/PROMPTS.md](app/PROMPTS.md) — промпты
- [.claude/skills/README.md](.claude/skills/README.md) — каталог скиллов
- [MCP_SERVERS.md](MCP_SERVERS.md) — MCP-серверы для скиллов · [VERSIONING.md](VERSIONING.md) — версионирование
- [build/BUILD.md](build/BUILD.md) — сборка бинарника · [docs/start/releasing.md](docs/start/releasing.md) — выпуск релизов · [build/INSTALL.md](build/INSTALL.md) — установка бинарника
- [.env.example](.env.example), [.mcp.example.json](.mcp.example.json) — примеры конфигурации

## Лицензия

См. [LICENSE.docx](LICENSE.docx) — пользовательское соглашение (публичная оферта).
