# ModusBI MCP Server — Сборка бинарника

> ⚠️ Действия ассистента на портале **необратимы** (нет отмены/истории), а безопасность доступов
> при работе с LLM — на стороне пользователя. См. [../DISCLAIMER.md](../DISCLAIMER.md).

## Требования

- Python 3.10+
- pip
- ~500 MB свободного места

## Сборка

```bash
cd build
python build.py
```

Или платформенные скрипты:

```bash
# Linux
./build_linux.sh

# Windows
build_windows.bat
```

Результат — один файл в папке версии `dist/<version>/<os>-<arch>/`:
- Linux:   `build/dist/1.0.0/linux-x86_64/modusbi-mcp-server`
- Windows: `build/dist/1.0.0/windows-x86_64/modusbi-mcp-server.exe`
- macOS:   `build/dist/1.0.0/darwin-arm64/modusbi-mcp-server`

Рядом кладётся `<binary>.sha256` для проверки загрузки. Номер версии берётся из `app/__init__.py`
(`__version__`). Бинарники не коммитятся (в `.gitignore`) — публикуются в
[GitHub Releases](https://github.com/modus-bi/mcp-modusbi/releases) (tag `v1.0.0`).

## Опции сборки

```bash
python build.py --clean    # очистить артефакты перед сборкой
python build.py --check    # только проверить зависимости
```

## Что включается в бинарник

- Весь Python-код `app/`
- Зависимости: `mcp`, `httpx`, `pydantic` + транзитивные
- Промпт-шаблоны: инлайн в `app/prompts.py` (отдельные `.md` не бандлятся)

Конфиг сервера читается из env vars при запуске (MODUSBI_URL, USERNAME,
PASSWORD) — никаких файлов конфигурации в бинарь не упаковывается.

Бинарник собирается для текущей ОС. Для Windows — собирайте на Windows, для Linux — на Linux.

## Проверка собранного бинарника

```bash
BIN=dist/1.0.0/linux-x86_64/modusbi-mcp-server   # путь под свою ОС/арх

# Список флагов
"$BIN" --help

# Проверка контрольной суммы
sha256sum -c "$BIN.sha256"

# Smoke-старт в readonly с логами
MODUSBI_URL=https://your-portal.modusbi.ru \
MODUSBI_USERNAME=your_login \
MODUSBI_PASSWORD=your_password \
  "$BIN" --readonly --log-level DEBUG
```

Успех — в stderr появится `Server started in READONLY mode`. Ctrl-C для выхода.

## Запуск из исходников (без сборки)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Read-only (default since 1.0.0)
python -m app.server --readonly

# Read-write (для create / update / delete)
python -m app.server --readwrite

# Demo (readonly + rate limits)
python -m app.server --demo
```

> ℹ️ Рекомендуемая entry-point — `python -m app.server`. Короткая форма `python -m app` тоже работает (см. `app/__main__.py`).

### Зависимости (requirements.txt)

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `mcp` | >=1.22.0 | FastMCP SDK |
| `httpx` | >=0.27.0 | Async HTTP клиент |
| `pydantic` | >=2.0.0 | Валидация данных |

## Что обновлять в spec при добавлении новых модулей

Файл `modusbi_mcp.spec` хранит список `hiddenimports` — PyInstaller обычно
автоматически их подхватывает по статическому анализу `from .tools.X
import Y`, но для надёжности любые новые модули в `app/tools/`,
`app/core/` стоит явно перечислять.

Текущий список включает все модули проекта (см. spec). При добавлении
нового модуля:

1. Добавить его в `hiddenimports` в `modusbi_mcp.spec`.
2. Пересобрать (`python build.py --clean`).
3. Проверить что бинарь стартует с `--help` и `--readonly`.

## Запуск тестов перед сборкой

```bash
# Быстрый общий smoke (запускает базовые smoke каскадом)
# env-vars нужны: smoke-агрегатор стартует subprocess `python -m app.server`,
# который без MODUSBI_URL/USERNAME/PASSWORD сходит с ошибкой credentials.
MODUSBI_URL=http://localhost MODUSBI_USERNAME=x MODUSBI_PASSWORD=x \
  python3 -m app.tests.test_smoke_token_usage

# Точечные unit-тесты (без env-vars, не нужен портал)
python3 -m app.tests.test_mask_sensitive       # 12 OK
python3 -m app.tests.test_security_modes       # 31 OK
python3 -m app.tests.test_builders             # 84 OK (28 типов × 3)
python3 -m app.tests.test_config_schema        # 30 OK
python3 -m app.tests.test_token_refresh        # 20 OK
python3 -m app.tests.test_manager_lifecycle    # 14 OK

# BI-расширения — 12 новых тестовых файлов
python3 -m app.tests.test_dataset_operations         # 13 OK
python3 -m app.tests.test_dataset_post_write_verify  # 10 OK
python3 -m app.tests.test_filter_field_alias         # 22 OK
python3 -m app.tests.test_global_filters_rebuild     # 18 OK
python3 -m app.tests.test_set_global_filter          # 19 OK
python3 -m app.tests.test_unsupported_params         # 30 OK
python3 -m app.tests.test_filters_grid_layout        # 33 OK
python3 -m app.tests.test_builder_alias_map          # 15 OK
python3 -m app.tests.test_series_field               # 24 OK
python3 -m app.tests.test_chart_expand_basecolor     # 25 OK
python3 -m app.tests.test_donut_slugs                # 38 OK
python3 -m app.tests.test_slugs_search               # 18 OK
python3 -m app.tests.test_conditional_strings        # 14 OK
python3 -m app.tests.test_apply_theme                # 23 OK
python3 -m app.tests.test_scaffold_filters_grid      # 13 OK
python3 -m app.tests.test_kpi_multiline              # 22 OK
```

Если что-то падает — не пересобирайте бинарь. Tests-первыми правило.

## RSS / память

| Запуск | Память | Когда брать |
|--------|--------|-------------|
| PyInstaller `--onefile` | ~150 MB RSS на процесс | Дистрибуция конечному пользователю — один файл, чтобы положить и запустить |
| PyInstaller `--onedir` | ~70 MB RSS (shared mmap) | DevOps на сервере с 5+ порталами в одной machine |
| Из исходников (`python -m app.server`) | ~56 MB RSS | Разработка / debug / любые multi-portal сценарии где есть Python в окружении |
