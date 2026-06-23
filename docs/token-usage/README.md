# Token Usage — Historical Trend

Auto-generated from `docs/token-usage/*.json` snapshots.
Updated by `scripts/snapshot_tokens.py`.

Key metric: **envelope (compact)** — tokens, которые `tools/list` забирает на каждый
запрос LLM-клиента. Sum-of-parts — сумма по инструментам (аналитическая, без JSON-RPC-обёртки).

## Trend (last 20 snapshots)

| Дата | MCP | Тег | Envelope (compact) | Sum-of-parts |
|------|-----|-----|------------------:|------------:|
| 2026-06-22 | `1.0.0` | v1.0.0 | **17,277** | 21,603 |

## Latest Snapshot — 2026-06-22

- **MCP Version:** `1.0.0`
- **Tokenizer:** cl100k_base
- **Tokenizer backend:** `tiktoken:cl100k_base`

### Real cost per request (tools/list envelope)

- **Compact JSON:** 17,277 tokens
- **Indented JSON:** 22,707 tokens

### Analytical breakdown

- Sum-of-parts (per-tool summed): 21,603 tokens

### Top-10 heaviest tools

| Tool | Total tokens |
|------|--------------|
| `batch_operations` | 2,840 |
| `component_crud` | 2,430 |
| `dataset_query` | 1,826 |
| `query_batch` | 1,826 |
| `report_operations` | 1,738 |
| `reportgroup_operations` | 1,411 |
| `component_axes` | 1,390 |
| `style_operations` | 1,181 |
| `report_template` | 973 |
| `component_filters` | 916 |

## Client/tool-set profiles

| Profile | Tokenizer | Backend | Tool set | Tools | Envelope compact | Envelope indented | Sum-of-parts |
|---|---|---|---|---:|---:|---:|---:|
| Anthropic Tool Search — main tools | `cl100k_base` | `tiktoken:cl100k_base` | `HOT_TOOLS` | 8 | 7,390 | 9,531 | 11,169 |
| OpenAI Agents Tool Search — main tools | `o200k_base` | `tiktoken:o200k_base` | `HOT_TOOLS` | 8 | 7,459 | 9,504 | 10,841 |
| Anthropic — deferred tools on demand | `cl100k_base` | `tiktoken:cl100k_base` | `DEFERRED_TOOLS` | 11 | 9,890 | 13,185 | 14,574 |
| OpenAI — deferred tools on demand | `o200k_base` | `tiktoken:o200k_base` | `DEFERRED_TOOLS` | 11 | 10,031 | 13,154 | 14,247 |
| Other/classic clients — full MCP surface | `cl100k_base` | `tiktoken:cl100k_base` | `HOT_TOOLS + DEFERRED_TOOLS` | 19 | 17,277 | 22,707 | 23,673 |

Notes:
- Anthropic numbers are local `cl100k_base` proxy counts; exact `messages/count_tokens` requires a live Anthropic API key.
- OpenAI numbers use local `o200k_base`; if the backend column says `approx-ru-fallback`, tiktoken data was unavailable.
- Other/classic clients ignore `_meta` defer hints and therefore receive the full 19-tool surface upfront.
- Sum-of-parts is analytical and includes shared server instructions/prompts for each profile; compare envelope columns for tools/list cost.
