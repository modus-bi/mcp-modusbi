# ModusBI MCP Server — Установка

Вы получили готовый бинарник. Python не нужен.

> ⚠️ **Перед установкой.** ИИ-ассистент получит доступ к порталу под переданной учётной записью;
> операции записи **необратимы** (отмены/истории нет). Безопасность доступов — на стороне пользователя.
> См. [../DISCLAIMER.md](../DISCLAIMER.md). По умолчанию сервер стартует в `readonly`.

Бинарник под вашу ОС/архитектуру скачайте со страницы
[Releases](https://github.com/modus-bi/mcp-modusbi/releases) (релиз `v1.0.0`). Рядом лежит файл
`<binary>.sha256` — проверьте загрузку: `sha256sum -c modusbi-mcp-server.sha256` (Linux/macOS) или
`CertUtil -hashfile modusbi-mcp-server.exe SHA256` (Windows).

## 1. Положите файл

**Linux / macOS:**
```bash
cp modusbi-mcp-server /usr/local/bin/
chmod +x /usr/local/bin/modusbi-mcp-server
```

**Windows:**
```
Скопируйте modusbi-mcp-server.exe в C:\Tools\
```

## 2. Откройте конфиг вашего AI-клиента

| Клиент | Файл конфига |
|--------|-------------|
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Cursor | `.cursor/mcp.json` в корне проекта |
| Claude Code | `.mcp.json` в корне проекта |

## 3. Вставьте — подставив свои логин, пароль и URL портала

> ⚠️ **Важно про режимы.** Сервер по умолчанию запускается в **readonly** (с версии 1.0.0). Без явного `--readwrite` запросы на создание / изменение / удаление будут отклоняться с сообщением «требует режим: readwrite». Это сделано как safety-default для автономных AI-агентов. Выберите режим, который вам нужен — см. блок «Режимы запуска» ниже.

**Linux / macOS — read-only (просмотр):**
```json
{
  "mcpServers": {
    "modusbi": {
      "command": "/usr/local/bin/modusbi-mcp-server",
      "args": ["--readonly"],
      "env": {
        "MODUSBI_URL": "https://your-portal.modusbi.ru",
        "MODUSBI_USERNAME": "your_login",
        "MODUSBI_PASSWORD": "your_password"
      }
    }
  }
}
```

**Linux / macOS — read-write (создание/изменение отчётов):**
```json
{
  "mcpServers": {
    "modusbi": {
      "command": "/usr/local/bin/modusbi-mcp-server",
      "args": ["--readwrite"],
      "env": {
        "MODUSBI_URL": "https://your-portal.modusbi.ru",
        "MODUSBI_USERNAME": "your_login",
        "MODUSBI_PASSWORD": "your_password"
      }
    }
  }
}
```

**Windows — read-write:**
```json
{
  "mcpServers": {
    "modusbi": {
      "command": "C:\\Tools\\modusbi-mcp-server.exe",
      "args": ["--readwrite"],
      "env": {
        "MODUSBI_URL": "https://your-portal.modusbi.ru",
        "MODUSBI_USERNAME": "your_login",
        "MODUSBI_PASSWORD": "your_password"
      }
    }
  }
}
```

## 4. Перезапустите клиент

Полностью закройте и откройте заново (не просто свернуть).

---

## Режимы запуска (флаги `--*`)

Передаются в `"args"` массив — флагами CLI бинарника.

| Флаг | Что делает | Когда использовать |
|------|-----------|--------------------|
| `--readonly` | Только просмотр: list / get / summary / *_list / validate / export. Все CRUD блокируются. | Аналитика, дашборды для просмотра, демо-окружения. **Default since 1.0.0** — если флага нет, ставится автоматически. |
| `--readwrite` | Полный доступ: create / update / delete + readonly. | AI-агент создаёт / правит отчёты, датасеты, компоненты. **Без этого флага write-операции отклоняются.** |
| `--demo` | readonly + rate limits. | Публичные демо, песочницы. |
| `--security-ceiling` | Жёсткий потолок security mode (никогда не позволит сделать менее строго). Default `readwrite` (нет потолка). Может также задаваться через env var `MODUSBI_SECURITY_CEILING`. | Production: ставь `readonly` — пользователь не сможет случайно запустить `--readwrite` (он будет downgraded). |
| `--transport stdio` | Транспорт stdio (default) — диалог через stdin/stdout. | Стандарт для Claude Desktop / Cursor / Claude Code. |
| `--transport http` | Транспорт HTTP. | Кастомные интеграции (не для AI-клиентов из таблицы выше). |
| `--log-level INFO` | Уровень логов в stderr (`DEBUG` / `INFO` / `WARNING` / `ERROR`, default `INFO`). | `DEBUG` — для расследования проблем. |
| `--log-format text` | Формат логов: `text` (default, человекочитаемый) или `json` (одна строка = один JSON-объект, готовый для ELK / Loki / Datadog). | `json` — для production с агрегаторами логов. |

### Как работает `--security-ceiling`

Финальный режим = **более строгий** из (CLI-флага, ceiling). Строгость: `readonly` (2) > `demo` (1) > `readwrite` (0).

| `--readwrite/--demo/--readonly` (CLI) | `--security-ceiling` | Финальный режим |
|---|---|---|
| `--readwrite` | `readwrite` (default) | `readwrite` |
| `--readwrite` | `demo` | `demo` ⚠ downgraded |
| `--readwrite` | `readonly` | `readonly` ⚠ downgraded |
| `--demo` | `readwrite` | `demo` |
| `--readonly` | любой | `readonly` |

Используй для prod-серверов где надо гарантировать что никто не запустит write-режим:

```json
"args": ["--readwrite", "--security-ceiling", "readonly"]
```

Сервер запустится в `readonly` (потолок выигрывает) и в stderr будет warning о downgrade.

**Режимы взаимоисключающие.** Если переданы и `--readonly`, и `--readwrite` — приоритет у `--readwrite` (потом `--demo`, потом `--readonly`). Чтобы гарантировать жёсткий потолок безопасности, используйте `--security-ceiling readonly` независимо от других флагов.

---

## Что подставлять в `"env"`

| Поле | Обязательно | Что писать | Пример |
|------|:---:|-----------|--------|
| `MODUSBI_URL` | да | Адрес вашего портала ModusBI | `https://portal.modusbi.ru` |
| `MODUSBI_USERNAME` | да | Ваш логин в портале | `ivanov` |
| `MODUSBI_PASSWORD` | да | Ваш пароль | `myP@ssw0rd` |
| `MODUSBI_INSTANCE_NAME` | нет | Метка для логов (default: `default`) | `prod` |
| `MODUSBI_SECURITY_CEILING` | нет | Потолок security mode (см. раздел про `--security-ceiling` выше) | `readonly` |

Блок `"env"` — это всё что нужно. Клиент сам передаёт эти значения серверу при запуске.

---

## Multiple portals (multi-tenant сценарий)

Сервер работает в модели **один процесс = один портал**. Чтобы работать с несколькими порталами одновременно, настройте **несколько записей** в `mcpServers` — каждую со своими env vars:

```json
{
  "mcpServers": {
    "modusbi-dev": {
      "command": "/usr/local/bin/modusbi-mcp-server",
      "args": ["--readwrite"],
      "env": {
        "MODUSBI_URL": "https://your-portal.modusbi.ru",
        "MODUSBI_USERNAME": "your_dev_login",
        "MODUSBI_PASSWORD": "your_dev_password",
        "MODUSBI_INSTANCE_NAME": "dev"
      }
    },
    "modusbi-prod": {
      "command": "/usr/local/bin/modusbi-mcp-server",
      "args": ["--readonly", "--security-ceiling", "readonly"],
      "env": {
        "MODUSBI_URL": "https://portal.modusbi.ru",
        "MODUSBI_USERNAME": "your_prod_login",
        "MODUSBI_PASSWORD": "your_prod_password",
        "MODUSBI_INSTANCE_NAME": "prod"
      }
    }
  }
}
```

ИИ-агент видит **два сервера** (`mcp__modusbi-dev__*` и `mcp__modusbi-prod__*`) как два независимых набора инструментов и сам выбирает к какому обращаться. Никаких переключений внутри процесса — это паттерн всех остальных MCP-серверов в типичной установке (jira, plane, postgres, github и т.д.).

**Заметка про ресурсы:** PyInstaller-бинарь занимает ~150 MB RSS на процесс. Для 2-3 порталов это нормально; для 5+ — рассмотрите запуск из исходников (`python -m app.server`, ~56 MB на процесс) или `--onedir` PyInstaller для shared mmap.

**Копирование между порталами:** делается LLM-side через два tool-call к разным `mcpServers`. **Атомарность не гарантируется** — между read и write возможен failure → orphan'ы; LLM также вручную переписывает `dataset_id`/`report_id`/foreign keys. Для критичных миграций используйте export через `data_export_operations` + ручной импорт.

---

## Проверка локально

После установки можно убедиться что бинарник запускается:

```bash
# Покажет список флагов
modusbi-mcp-server --help

# Запустит с подробными логами в stderr (Ctrl-C чтобы выйти)
MODUSBI_URL=https://your-portal.modusbi.ru \
MODUSBI_USERNAME=your_login \
MODUSBI_PASSWORD=your_password \
  modusbi-mcp-server --readonly --log-level DEBUG
```

---

## Production: structured-логи и security

### JSON-логи для агрегаторов (ELK / Loki / Datadog)

```json
"args": ["--readwrite", "--log-format", "json", "--log-level", "INFO"]
```

В stderr будет одна строка = один JSON-объект:
```json
{"ts":"2026-05-04T16:12:48","level":"WARNING","logger":"app.server","msg":"Server started in READWRITE mode — destructive actions enabled."}
```

Удобно подключать через filebeat / promtail / vector — без regex-парсинга.

### Что сервер защищает автоматически

- **Секреты в логах.** Все исключения проходят через `mask_sensitive()` —
  стираются Go-runtime traces (`goroutine N [running]`), пути `*.go:NNN`,
  имена БД-схем / relations / constraints, префиксы `pq:`. Внутренние
  детали портала не утекают в выводы tool-call'ов.
- **Datasource credentials.** При `datasource_operations(action="get")` /
  `list` сервер возвращает только `id, name, caption, form, description` —
  технические поля `db_host / db_port / db_name / db_schema / db_user /
  db_url` фильтруются на выходе. (Сам `db_password` бэкенд не отдаёт ни
  при каких условиях — речь именно про hostname/user/url, чтобы LLM не
  смог при prompt-injection экспортировать их в сторонний endpoint.)
- **Авто-перевыпуск токена.** Если бэкенд вернул `401 Unauthorized`,
  клиент молча перевыпускает токен и повторяет запрос один раз. Никакой
  ручной re-login не требуется при долгих сессиях.
- **Валидация URL при старте.** `MODUSBI_URL` проверяется на корректность
  схемы (`http://` / `https://`) и хост — некорректное значение даёт
  понятную ошибку `lifespan` вместо неинформативного network error.
- **HTTP-пул переиспользуется.** Один `httpx.AsyncClient` с keepalive на
  весь процесс — TLS-handshake не повторяется на каждый tool-call,
  заметно быстрее на длинных сессиях.

## Если не работает

| Симптом | Что делать |
|---------|-----------|
| Клиент не видит сервер | Путь к файлу должен быть абсолютный. Перезапустите клиент полностью |
| `Authentication failed` | Проверьте логин/пароль — попробуйте зайти в портал через браузер |
| `Connection refused` | Проверьте сеть. Если через VPN — включён ли VPN? |
| AI-агент жалуется «требует режим: readwrite» | В `"args"` нет `--readwrite`. Добавьте и перезапустите клиент |
| `Unknown action` / странные ошибки в одном tool | Проверьте `--log-level DEBUG` в stderr — там будет подробный traceback |
| Не запускается (Linux) | `chmod +x modusbi-mcp-server`. Нужен Ubuntu 20.04+ или аналог |
| Не запускается (Windows) | Антивирус может блокировать — добавьте исключение |
