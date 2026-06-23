"""Tool classification: hot (always loaded) vs deferred (Tool Search).

Marks advanced tools with `_meta["*/defer_loading"]` so clients with Tool
Search (Anthropic API + tool_search_tool_regex_2025*, OpenAI Agents SDK)
can exclude them from the initial context window and load on-demand.

Clients without Tool Search ignore `_meta` per MCP spec — they see all
19 tools as before. Backward-compatible.

## Classification rationale

The list was derived from real usage in `.claude/skills/create-*/SKILL.md`
and `app/prompts/*.md` (the canonical "create a dashboard" workflow):

- 8 tools appear in 7 of 8 create-* skills → HOT
- 11 tools appear in ≤ 1 create-* skill → DEFERRED

`component_styling`, `dataset_create_from_sql`, `report_template` and
`style_operations` stay HOT because every create-* skill uses them
(styling, dataset bootstrap, template scaffolding, report-level CSS).
Demoting them to deferred would force a Tool Search round-trip on every
create flow.

`dataset_query` stays in DEFERRED because it is verify/analyze flow
only — it is not invoked when *building* a dashboard.
"""
from __future__ import annotations


HOT_TOOLS: frozenset[str] = frozenset({
    "report_operations",        # entry point for most workflows
    "dataset_operations",       # CRUD + alias setup before binding components
    "dataset_create_from_sql",  # semantic-layer bootstrap, used by every create-skill
    "report_template",          # scaffold from kpi/ranking/comparison/... templates
    "component_crud",           # add/update/delete components, layout
    "component_filters",        # filters + cascade filterBy
    "component_styling",        # conditional formatting, map colors, visual params
    "style_operations",         # report-level CSS themes
})

DEFERRED_TOOLS: frozenset[str] = frozenset({
    # Read flows (verify/analyze, not create)
    "dataset_query",
    "query_batch",
    "sql_query_validate",

    # Advanced component configuration
    "component_axes",                # calc fields, drill-down, pages, tabs

    # Bulk / admin
    "batch_operations",
    "reportgroup_operations",        # folders
    "security_operations",           # RLS
    "instance_operations",           # portal info (read-only)

    # Datasource lifecycle
    "datasource_operations",
    "preflight_check_datasource",

    # Export
    "data_export_operations",
})


# `_meta` keys used by clients with Tool Search. Multiple keys ship at
# once because the spec is still evolving; unknown keys are ignored.
DEFER_META: dict[str, bool] = {
    "anthropic/defer_loading": True,
    "openai/defer_loading": True,
}


# Self-check invariants — run at import time so misconfiguration is
# loud, not silent.
assert HOT_TOOLS.isdisjoint(DEFERRED_TOOLS), \
    f"HOT/DEFERRED overlap: {HOT_TOOLS & DEFERRED_TOOLS}"
assert len(HOT_TOOLS) == 8, f"expected 8 hot tools, got {len(HOT_TOOLS)}"
assert len(DEFERRED_TOOLS) == 11, f"expected 11 deferred tools, got {len(DEFERRED_TOOLS)}"
assert len(HOT_TOOLS | DEFERRED_TOOLS) == 19, \
    f"expected 19 total, got {len(HOT_TOOLS | DEFERRED_TOOLS)}"
