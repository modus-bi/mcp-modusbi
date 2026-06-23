# MCP-серверы для скиллов

> ⚠️ **Перед практической работой** прочитайте [DISCLAIMER.md](DISCLAIMER.md): изменения на портале необратимы (нет отмены/истории), безопасность доступов при работе с LLM — на стороне пользователя.

Скиллы и агенты этого репозитория вызывают инструменты разных MCP-серверов. Здесь — **какие серверы нужны**
и **каким скиллам**. Конфиг — в вашем MCP-клиенте (`.mcp.json` / `claude_desktop_config.json`); готовый шаблон —
[.mcp.example.json](.mcp.example.json). Учётные данные — из `.env` (см. [.env.example](.env.example)).

> **Минимум для старта:** только `modusbi`. Остальные серверы нужны лишь отдельным группам скиллов (UI-тесты, аналитика из БД).

## Серверы

| Сервер | Обязателен? | Зачем | Команда (см. .mcp.example.json) |
|---|---|---|---|
| **modusbi** | ✅ да | ядро — все BI-скиллы (создание/настройка отчётов, запросы, экспорт) | `python -m app.server --readonly` (для записи — `--readwrite`) |
| **playwright** | опц. | визуальная верификация компонентов, проба палитры | `npx @playwright/mcp@latest --headless` |
| **postgres** | опц. | аналитические скиллы, тянущие данные напрямую из БД | `npx pg-mcp-server --transport stdio` |

## Какому скиллу что нужно

| Группа скиллов | modusbi | playwright | postgres |
|---|:--:|:--:|:--:|
| **Создание отчётов** (create-dashboard/kpi/ranking/comparison/factor/geo/simple, add-navigation-panel) | ✅ | | опц.¹ |
| **Аналитика/выводы** (analyze-data, bi-visualization-expert, explain-chart, dq-profiler, sql-bi-expert) | ✅ | | опц.¹ |
| **UI-тесты портала** (modusbi-e2e) | ✅ | ✅ | |
| **Визуальная верификация** (component-visual-verify, portal-component-probe, component-deep-settings) | ✅ | ✅ | |

¹ `postgres` — только если скилл тянет данные напрямую из БД (иначе данные идут через `modusbi`-инструменты).

## Переменные окружения (`.env`)

| Переменная | Для кого | Назначение |
|---|---|---|
| `MODUSBI_URL`, `MODUSBI_USERNAME`, `MODUSBI_PASSWORD` | сервер `modusbi` | подключение к порталу (API-юзер) |
| `MODUSBI_E2E_LOGIN`, `MODUSBI_E2E_PASSWORD` | UI-тест скиллы | вход в веб-интерфейс (browser-юзер) |
| `DATABASE_URL` | сервер `postgres` | подключение к БД для аналитики |

> Сервер `modusbi` получает переменные из блока `env` своей записи в MCP-клиенте (`.mcp.json`). UI-тест скиллы
> читают `MODUSBI_E2E_*` из `.env` перед browser-логином. Реальные `.env` / `.mcp.json` — в `.gitignore`.
