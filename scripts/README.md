# Scripts

Эта папка содержит рабочие утилиты MCP-сервера: token observability, budget checks,
MCP Scorecard и wire-level проверки. Скрипты рассчитаны на запуск из
корня репозитория.

## Быстрый старт

| Задача | Команда |
|---|---|
| Измерить token surface MCP tools | `python scripts/measure_tokens.py` |
| Измерить Anthropic/OpenAI/rest profiles | `python scripts/measure_tokens.py --profiles` |
| Посчитать токены типовых flow | `python scripts/simulate_flows.py` |
| Оценить экономию help-action | `python scripts/analyze_help_savings.py` |
| Сделать snapshot в `docs/token-usage/` | `python scripts/snapshot_tokens.py --tag <tag>` |
| Проверить budget по последнему snapshot | `python scripts/check_token_budget.py` |
| Snapshot + budget check одной командой | `bash scripts/run_token_budget.sh` |
| Запустить MCP Scorecard | `bash scripts/run_scorecard.sh` |
| Сжать scorecard JSON в markdown summary | `python scripts/scorecard_summary.py .scorecard/scorecard.json` |
| Проверить tool wire metadata | `python scripts/verify_tool_wire.py` |

## Token Usage

| Файл | Назначение | Основной output |
|---|---|---|
| `measure_tokens.py` | Измеряет размер MCP tool surface и схем. | Markdown в stdout, optional JSON через `--json`; `--profiles` добавляет Anthropic/OpenAI/rest разрезы. |
| `simulate_flows.py` | Считает token cost для типовых сценариев tool calls. | Markdown в stdout, optional JSON через `--json`. |
| `analyze_help_savings.py` | Сравнивает экономию после help-action refactor. | Markdown в stdout, optional JSON через `--json`. |
| `snapshot_tokens.py` | Делает датированный snapshot и обновляет индекс. | `docs/token-usage/YYYY-MM-DD.json`, `docs/token-usage/README.md`. |
| `check_token_budget.py` | Сверяет последний snapshot с budget config. | Exit `0` OK, `2` config/deps issue, `3` budget violation. |
| `run_token_budget.sh` | CI-friendly wrapper для snapshot + budget check. | Те же файлы snapshot и статус budget check. |

Примечания:

- Token scripts подставляют минимальные `MODUSBI_*` env vars, чтобы импортировать
  server surface без реального подключения к порталу.
- Для exact tokenizer-замеров установите optional group `tokens`: `pip install -e ".[tokens]"`.
- Для `check_token_budget.py` нужен `PyYAML`; для `cl100k_base`/`o200k_base`
  нужен `tiktoken`. Если BPE cache недоступен, отчёт явно покажет
  `approx-ru-fallback`.
- `run_token_budget.sh` поддерживает env vars `PY`, `OUT_DIR`, `BUDGET`, `TAG`.

## MCP Scorecard

| Файл | Назначение | Важные детали |
|---|---|---|
| `run_scorecard.sh` | Запускает MCP Scorecard против сервера в readonly mode. | Может скачать `MCP-Scorecard`, если он не установлен локально. |
| `scorecard_summary.py` | Формирует короткий markdown summary из scorecard JSON. | По умолчанию читает `.scorecard/scorecard.json`. |

Локальные результаты Scorecard пишутся в `.scorecard/` и не являются исходными
данными репозитория. Исторический baseline для тестов и сравнения живет отдельно в
`docs/scorecard/`.

## Wire / MCP Verification

| Файл | Назначение | Статус |
|---|---|---|
| `verify_tool_wire.py` | Проверяет wire-level свойства: количество tools, `_meta` hints, HOT/DEFERRED разделение и базовые tool calls. | Диагностический скрипт. Если stdio/list-tools harness не отвечает, результат считается inconclusive и требует отдельного разбора окружения. |

## Артефакты

| Путь | Тип | Комментарий |
|---|---|---|
| `.scorecard/` | Generated local output | Можно чистить после backup; baseline хранится в `docs/scorecard/`. |
| `docs/token-usage/*.json` | Tracked snapshots | Нужны для истории token budget и сравнения по времени. |
| `docs/token-usage/README.md` | Generated tracked summary | Обновляется `snapshot_tokens.py`. |
| `scripts/__pycache__/` | Python cache | Можно удалять. |
