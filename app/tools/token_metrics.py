"""Core token measurement logic for the MCP tool surface.

Functions here are pure (no argparse, no file I/O) — thin scripts in
`scripts/` call them and handle CLI/output concerns.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

from .token_counter import count_tokens, count_tokens_json, tokenizer_backend
from .. import __version__ as _PKG_VERSION


# =============================================================================
# FLOWS — common tool-call sequences with realistic fixture responses.
# Each flow: list of (tool_name, args_dict, fixture_key).
# fixture_key starts with "__live:" → call live helper instead.
# =============================================================================

FIXTURE_RESPONSES: dict[str, Any] = {
    "report_operations.create": {
        "success": True,
        "report_id": 42,
        "message": "Report created successfully",
    },
    "dataset_operations.create": {
        "success": True,
        "dataset_id": 5,
        "message": "Dataset created",
    },
    "component_crud.add": {
        "success": True,
        "component_idx": 0,
        "component_type": "HsBarAMchartsChart",
        "report_id": 42,
    },
    "style_operations.update": {
        "success": True,
        "message": "CSS updated",
    },
    "datasource_operations.list": {
        "success": True,
        "count": 5,
        "datasources": [
            {"id": i, "name": f"datasource_{i}", "type": "postgres"}
            for i in range(1, 6)
        ],
    },
    "datasource_operations.tables_list": {
        "success": True,
        "datasource_id": 1,
        "tables": [
            {"name": f"schema.table_{i}", "columns_count": 8}
            for i in range(20)
        ],
    },
    "sql_query_validate.validate": {
        "valid": True,
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "region", "type": "string"},
            {"name": "amount", "type": "numeric"},
        ],
    },
    "dataset_query.query": {
        "success": True,
        "dataset_id": 5,
        "rows_count": 10,
        "fields": ["id", "region", "amount"],
        "rows": [[i, f"Region_{i}", 1000 * i] for i in range(10)],
    },
    "report_operations.list": {
        "success": True,
        "count": 30,
        "reports": [
            {"id": i, "name": f"Report_{i}", "group_id": 1}
            for i in range(1, 31)
        ],
    },
    "report_operations.export": {
        "success": True,
        "file_path": "/tmp/report_42.pdf",
        "size_bytes": 523_450,
    },
    "component_crud.bogus_action": {
        "success": False,
        "error": "Unknown action: bogus_action",
        "available_actions": [
            "help", "types_list", "get", "add", "update", "delete",
            "layout_update", "layout_update_breakpoint", "swap",
            "list_slugs", "list_presets",
        ],
        "hint": "Use action='help' to see full action list with examples",
    },
}


FLOWS: dict[str, list[tuple[str, dict, str]]] = {
    "create_dashboard": [
        ("report_operations",
         {"action": "create", "name": "Test Dashboard", "group_id": 1},
         "report_operations.create"),
        ("dataset_operations",
         {"action": "create", "datasource_id": 1, "name": "sales",
          "sql": "SELECT region, SUM(amount) AS amount FROM sales GROUP BY region"},
         "dataset_operations.create"),
        ("component_crud",
         {"action": "add", "report_id": 42,
          "component_type": "HsBarAMchartsChart", "dataset_id": 5,
          "category_field": "region", "value_field": "amount",
          "title": "Sales by region", "x": 0, "y": 0, "w": 30, "h": 12},
         "component_crud.add"),
        ("component_crud",
         {"action": "add", "report_id": 42,
          "component_type": "HsPieAMchartsChart", "dataset_id": 5,
          "category_field": "region", "value_field": "amount",
          "title": "Share by region", "x": 30, "y": 0, "w": 30, "h": 12},
         "component_crud.add"),
        ("style_operations",
         {"action": "update", "report_id": 42,
          "css": ".hsGridPanel { border-radius: 8px !important; }"},
         "style_operations.update"),
    ],
    "query_data": [
        ("datasource_operations", {"action": "list"},
         "datasource_operations.list"),
        ("datasource_operations",
         {"action": "tables_list", "datasource_id": 1},
         "datasource_operations.tables_list"),
        ("sql_query_validate",
         {"sql_query": "SELECT id, region, amount FROM sales LIMIT 10"},
         "sql_query_validate.validate"),
        ("dataset_query", {"dataset_id": 5, "limit": 10},
         "dataset_query.query"),
    ],
    "export_report": [
        ("report_operations", {"action": "list"},
         "report_operations.list"),
        ("report_operations",
         {"action": "export", "report_id": 42},
         "report_operations.export"),
    ],
    "debug_unknown_action": [
        ("component_crud", {"action": "bogus_action"},
         "component_crud.bogus_action"),
        ("component_crud", {"action": "help"},
         "__live:help_component_crud"),
    ],
    "help_deep_dive": [
        ("component_crud", {"action": "help"},
         "__live:help_component_crud"),
        ("dataset_operations", {"action": "help"},
         "__live:help_dataset"),
        ("report_operations", {"action": "help"},
         "__live:help_report"),
        ("component_crud",
         {"action": "list_slugs", "slug_category": "legend"},
         "__live:list_slugs_legend"),
        ("component_crud", {"action": "types_list"},
         "__live:types_list"),
    ],
}


def _get_live_response(fixture_key: str) -> dict[str, Any]:
    """Resolve `__live:*` fixture keys by calling real helpers (offline)."""
    assert fixture_key.startswith("__live:")
    kind = fixture_key[len("__live:"):]

    try:
        from .help_texts import (
            _help, HELP_COMPONENT_CRUD, HELP_DATASET, HELP_REPORT,
        )
    except Exception:
        return {"success": False, "error": "help_texts import failed"}

    if kind == "help_component_crud":
        return _help(None, HELP_COMPONENT_CRUD)
    if kind == "help_dataset":
        return _help(None, HELP_DATASET)
    if kind == "help_report":
        return _help(None, HELP_REPORT)
    if kind == "list_slugs_legend":
        try:
            from .component_crud import _list_slugs
            return _list_slugs(category="legend")
        except Exception:
            return {"success": True, "category": "legend",
                    "slugs": ["legend.position", "legend.visible"]}
    if kind == "types_list":
        try:
            from .config_schema import CHART_TYPE_MAP
            return {"success": True, "count": len(CHART_TYPE_MAP),
                    "types": sorted(CHART_TYPE_MAP.keys())}
        except Exception:
            return {"success": True, "count": 0, "types": []}
    return {}


def measure_flow(
    flow_name: str,
    steps: list[tuple[str, dict, str]],
    *,
    tokenizer: str = "cl100k_base",
) -> dict[str, Any]:
    """Measure token cost of a scripted flow (request + response bytes)."""
    step_details = []
    total_req = 0
    total_resp = 0
    for tool_name, args, fixture_key in steps:
        req_payload = {"name": tool_name, "arguments": args}
        req_tok = count_tokens_json(req_payload, tokenizer=tokenizer)

        if fixture_key.startswith("__live:"):
            resp = _get_live_response(fixture_key)
        else:
            resp = FIXTURE_RESPONSES.get(fixture_key, {})
        resp_tok = count_tokens_json(resp, tokenizer=tokenizer)

        step_details.append({
            "tool": tool_name,
            "action": args.get("action", "(no-action)"),
            "request_tokens": req_tok,
            "response_tokens": resp_tok,
            "step_total": req_tok + resp_tok,
        })
        total_req += req_tok
        total_resp += resp_tok

    return {
        "flow": flow_name,
        "step_count": len(steps),
        "total_request_tokens": total_req,
        "total_response_tokens": total_resp,
        "total_flow_tokens": total_req + total_resp,
        "steps": step_details,
    }


def measure_all_flows(*, tokenizer: str = "cl100k_base") -> dict[str, Any]:
    """Measure every flow in FLOWS and return aggregated report."""
    flows = {}
    grand = 0
    for name, steps in FLOWS.items():
        r = measure_flow(name, steps, tokenizer=tokenizer)
        flows[name] = r
        grand += r["total_flow_tokens"]
    return {"flows": flows, "grand_total": grand, "tokenizer": tokenizer}


# =============================================================================
# HELP-ACTION SAVINGS — compare thin docstring vs full (pre-refactor) size.
# =============================================================================


def _help_maps() -> dict[str, dict]:
    """Return mapping of tool name → HELP_* dict."""
    from .help_texts import (
        HELP_COMPONENT_CRUD, HELP_COMPONENT_FILTERS, HELP_COMPONENT_AXES,
        HELP_COMPONENT_STYLING, HELP_REPORT, HELP_DATASET, HELP_REPORT_TEMPLATE,
    )
    return {
        "component_crud": HELP_COMPONENT_CRUD,
        "component_filters": HELP_COMPONENT_FILTERS,
        "component_axes": HELP_COMPONENT_AXES,
        "component_styling": HELP_COMPONENT_STYLING,
        "report_operations": HELP_REPORT,
        "dataset_operations": HELP_DATASET,
        "report_template": HELP_REPORT_TEMPLATE,
    }


def _inline_help_text(help_map: dict) -> str:
    """Render a HELP_* dict as text the way it would have lived inline in a
    docstring before the help-action refactor.

    Uses plain text formatting (not JSON indent=2) to match the original
    docstring style — otherwise 'full' would be inflated vs reality.
    """
    parts = []
    for action, detail in help_map.items():
        parts.append(f"\n--- action: {action} ---")
        if isinstance(detail, dict):
            for k, v in detail.items():
                if isinstance(v, (list, tuple)):
                    parts.append(f"  {k}:")
                    for item in v:
                        parts.append(f"    - {item}")
                elif isinstance(v, dict):
                    parts.append(f"  {k}:")
                    for ik, iv in v.items():
                        parts.append(f"    {ik}: {iv}")
                else:
                    parts.append(f"  {k}: {v}")
        else:
            parts.append(f"  {detail}")
    return "\n".join(parts)


def measure_help_savings(mcp, *, tokenizer: str = "cl100k_base") -> dict[str, Any]:
    """Compare thin docstring (current) vs full (help content inlined).

    Returns per-tool breakdown + totals.
    """
    tools = _list_tools_snapshot(mcp)
    help_map = _help_maps()

    per_tool: dict[str, Any] = {}
    total_thin = 0
    total_full = 0

    for tool_name, hm in help_map.items():
        tool = tools.get(tool_name)
        if tool is None:
            continue
        thin_desc = tool.description or ""
        thin_tok = count_tokens(thin_desc, tokenizer=tokenizer)
        full_desc = thin_desc + _inline_help_text(hm)
        full_tok = count_tokens(full_desc, tokenizer=tokenizer)
        savings = full_tok - thin_tok
        per_tool[tool_name] = {
            "thin_tokens": thin_tok,
            "full_tokens": full_tok,
            "savings_tokens": savings,
            "savings_pct": round(100 * savings / full_tok, 1) if full_tok else 0.0,
        }
        total_thin += thin_tok
        total_full += full_tok

    total_savings = total_full - total_thin
    return {
        "tokenizer": tokenizer,
        "per_tool": per_tool,
        "totals": {
            "thin": total_thin,
            "full": total_full,
            "savings": total_savings,
            "savings_pct": round(100 * total_savings / total_full, 1) if total_full else 0.0,
        },
    }

# Tool → category. Keep in sync with docs/token-usage/README trend.
CATEGORIES: dict[str, tuple[str, ...]] = {
    "component": (
        "component_crud", "component_filters", "component_axes",
        "component_styling",
    ),
    "dataset": (
        "dataset_operations", "dataset_create_from_sql", "dataset_query",
    ),
    "report": ("report_operations", "report_template"),
    "query": (
        "query_batch", "sql_query_validate", "preflight_check_datasource",
    ),
    "infra": (
        "batch_operations", "data_export_operations", "security_operations",
        "style_operations", "reportgroup_operations",
    ),
    "admin": ("instance_operations", "datasource_operations"),
}


def _list_tools_snapshot(mcp) -> dict[str, Any]:
    """Safely snapshot the tool inventory via private APIs.

    Wrapped in try/except to survive FastMCP internal renames.
    """
    try:
        return dict(mcp._tool_manager._tools)
    except Exception:
        return {}


def _list_prompts_snapshot(mcp) -> dict[str, Any]:
    try:
        return dict(mcp._prompt_manager._prompts)
    except Exception:
        return {}


def _select_tool_names(
    tools: dict[str, Any],
    tool_names: Iterable[str] | None,
) -> tuple[list[str], list[str]]:
    if tool_names is None:
        return sorted(tools), []
    requested = set(tool_names)
    selected = sorted(name for name in tools if name in requested)
    missing = sorted(requested - set(tools))
    return selected, missing


def measure_surface(
    mcp,
    *,
    tokenizer: str = "cl100k_base",
    tool_names: Iterable[str] | None = None,
    profile_name: str = "all_tools",
) -> dict[str, Any]:
    """Measure token cost of the entire MCP tool/prompt surface.

    Returns a fully-structured dict. No I/O — caller is responsible for
    saving/printing.
    """
    tools = _list_tools_snapshot(mcp)
    prompts = _list_prompts_snapshot(mcp)
    selected_tool_names, missing_tool_names = _select_tool_names(
        tools, tool_names
    )

    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokenizer": tokenizer,
        "tokenizer_backend": tokenizer_backend(tokenizer),
        "version": os.environ.get("MCP_VERSION") or _PKG_VERSION,
        "tool_profile": {
            "name": profile_name,
            "tool_count": len(selected_tool_names),
            "tool_names": selected_tool_names,
            "missing_tools": missing_tool_names,
        },
    }

    # 1. Instructions
    instr = getattr(mcp, "instructions", None) or ""
    report["instructions"] = {
        "chars": len(instr),
        "tokens": count_tokens(instr, tokenizer=tokenizer),
    }

    # 2. Per-tool breakdown
    per_tool: dict[str, Any] = {}
    for name in selected_tool_names:
        tool = tools[name]
        name_tok = count_tokens(name, tokenizer=tokenizer)
        desc_tok = count_tokens(tool.description or "", tokenizer=tokenizer)
        schema_tok = count_tokens_json(tool.parameters, tokenizer=tokenizer)
        ann_tok = 0
        ann = getattr(tool, "annotations", None)
        if ann is not None:
            try:
                ann_tok = count_tokens_json(ann.model_dump(), tokenizer=tokenizer)
            except Exception:
                ann_tok = 0
        total = name_tok + desc_tok + schema_tok + ann_tok
        per_tool[name] = {
            "name_tokens": name_tok,
            "description_tokens": desc_tok,
            "schema_tokens": schema_tok,
            "annotations_tokens": ann_tok,
            "total": total,
        }
    report["per_tool"] = per_tool
    report["total_tools_tokens"] = sum(t["total"] for t in per_tool.values())

    # === Real tools/list envelope ===
    # sum-of-parts is useful for per-tool comparison, but the actual
    # JSON-RPC response includes array/object wrappers and field keys
    # ("name":, "description":, "inputSchema":, "annotations":).
    # This is the cost the LLM client actually pays in its context.
    tools_list_entries = []
    for name in selected_tool_names:
        tool = tools[name]
        entry: dict[str, Any] = {
            "name": name,
            "description": tool.description or "",
            "inputSchema": tool.parameters or {},
        }
        ann = getattr(tool, "annotations", None)
        if ann is not None:
            try:
                entry["annotations"] = ann.model_dump(exclude_none=True)
            except Exception:
                pass
        tools_list_entries.append(entry)
    envelope = {"tools": tools_list_entries}
    report["tools_list_envelope"] = {
        "compact_tokens": count_tokens_json(
            envelope, tokenizer=tokenizer, compact=True
        ),
        "indented_tokens": count_tokens_json(
            envelope, tokenizer=tokenizer, compact=False
        ),
    }

    # 3. Per-$defs (Pydantic models) breakdown
    defs_tokens: dict[str, int] = {}
    for name in selected_tool_names:
        tool = tools[name]
        defs = (tool.parameters or {}).get("$defs") or {}
        for model_name, model_schema in defs.items():
            tok = count_tokens_json(model_schema, tokenizer=tokenizer)
            # Avoid double-counting — record max across tools (same model
            # shows up in multiple tool schemas).
            defs_tokens[model_name] = max(defs_tokens.get(model_name, 0), tok)
    report["defs_tokens"] = dict(
        sorted(defs_tokens.items(), key=lambda kv: -kv[1])
    )
    # total_defs_tokens is informational (sum of per-model MAX across tools).
    # It is NOT added to grand_total — schema_tokens already includes $defs
    # expansion per tool.
    report["total_defs_tokens"] = sum(defs_tokens.values())

    # 4. Per-prompt breakdown
    per_prompt: dict[str, Any] = {}
    for name, prompt in sorted(prompts.items()):
        name_tok = count_tokens(name, tokenizer=tokenizer)
        desc_tok = count_tokens(prompt.description or "", tokenizer=tokenizer)
        args_list = []
        for a in (prompt.arguments or []):
            try:
                args_list.append(a.model_dump())
            except Exception:
                args_list.append({"name": getattr(a, "name", "?")})
        args_tok = count_tokens_json(args_list, tokenizer=tokenizer)
        per_prompt[name] = {
            "name_tokens": name_tok,
            "description_tokens": desc_tok,
            "arguments_tokens": args_tok,
            "total": name_tok + desc_tok + args_tok,
        }
    report["per_prompt"] = per_prompt
    report["total_prompts_tokens"] = sum(p["total"] for p in per_prompt.values())

    # 5. Per-category
    per_cat: dict[str, Any] = {}
    for cat, tool_names in CATEGORIES.items():
        included = [t for t in tool_names if t in per_tool]
        total = sum(per_tool[t]["total"] for t in included)
        per_cat[cat] = {"count": len(included), "tokens": total}
    # Catch un-categorized
    categorized = {n for names in CATEGORIES.values() for n in names}
    uncategorized = [n for n in per_tool if n not in categorized]
    if uncategorized:
        per_cat["_uncategorized"] = {
            "count": len(uncategorized),
            "tokens": sum(per_tool[n]["total"] for n in uncategorized),
            "names": uncategorized,
        }
    report["per_category"] = per_cat

    # 6. Grand total + context-window share
    grand = (
        report["instructions"]["tokens"]
        + report["total_tools_tokens"]
        + report["total_prompts_tokens"]
    )
    report["grand_total_tokens"] = grand
    report["pct_of_200k_context"] = round(grand / 2000, 2)

    return report


def client_profile_specs() -> dict[str, dict[str, Any]]:
    """Token measurement profiles for known client/loading modes."""
    from .profiles import DEFERRED_TOOLS, HOT_TOOLS

    all_tools = tuple(sorted(HOT_TOOLS | DEFERRED_TOOLS))
    hot_tools = tuple(sorted(HOT_TOOLS))
    deferred_tools = tuple(sorted(DEFERRED_TOOLS))
    return {
        "anthropic_main_tools": {
            "title": "Anthropic Tool Search — main tools",
            "tokenizer": "cl100k_base",
            "tool_set": "HOT_TOOLS",
            "tool_names": hot_tools,
            "note": (
                "Local cl100k proxy for Claude; exact Anthropic API count "
                "requires ANTHROPIC_API_KEY."
            ),
        },
        "openai_main_tools": {
            "title": "OpenAI Agents Tool Search — main tools",
            "tokenizer": "o200k_base",
            "tool_set": "HOT_TOOLS",
            "tool_names": hot_tools,
            "note": "OpenAI-style local tokenizer for GPT-4o/GPT-5 era models.",
        },
        "anthropic_deferred_tools": {
            "title": "Anthropic — deferred tools on demand",
            "tokenizer": "cl100k_base",
            "tool_set": "DEFERRED_TOOLS",
            "tool_names": deferred_tools,
            "note": "Loaded only when Tool Search selects advanced tools.",
        },
        "openai_deferred_tools": {
            "title": "OpenAI — deferred tools on demand",
            "tokenizer": "o200k_base",
            "tool_set": "DEFERRED_TOOLS",
            "tool_names": deferred_tools,
            "note": "Loaded only when Tool Search selects advanced tools.",
        },
        "other_clients_full": {
            "title": "Other/classic clients — full MCP surface",
            "tokenizer": "cl100k_base",
            "tool_set": "HOT_TOOLS + DEFERRED_TOOLS",
            "tool_names": all_tools,
            "note": (
                "Clients that ignore `_meta` defer hints receive all "
                "19 tools upfront."
            ),
        },
    }


def measure_client_profiles(mcp) -> dict[str, dict[str, Any]]:
    """Measure provider/tool-set profiles used in token-usage docs."""
    profiles: dict[str, dict[str, Any]] = {}
    for profile_id, spec in client_profile_specs().items():
        surface = measure_surface(
            mcp,
            tokenizer=spec["tokenizer"],
            tool_names=spec["tool_names"],
            profile_name=profile_id,
        )
        profiles[profile_id] = {
            "title": spec["title"],
            "tokenizer": spec["tokenizer"],
            "tokenizer_backend": surface.get("tokenizer_backend"),
            "tool_set": spec["tool_set"],
            "tool_names": list(spec["tool_names"]),
            "tool_count": len(spec["tool_names"]),
            "note": spec["note"],
            "surface": surface,
        }
    return profiles


def format_client_profiles_markdown(
    profiles: dict[str, dict[str, Any]],
) -> str:
    """Render a compact provider/tool-set profile table."""
    lines = [
        "## Client/tool-set profiles",
        "",
        "| Profile | Tokenizer | Backend | Tool set | Tools | Envelope compact | Envelope indented | Sum-of-parts |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for _, profile in profiles.items():
        surface = profile["surface"]
        env = surface.get("tools_list_envelope", {})
        lines.append(
            f"| {profile['title']} | `{profile['tokenizer']}` | "
            f"`{profile.get('tokenizer_backend', '?')}` | "
            f"`{profile['tool_set']}` | {profile['tool_count']} | "
            f"{env.get('compact_tokens', 0):,} | "
            f"{env.get('indented_tokens', 0):,} | "
            f"{surface.get('grand_total_tokens', 0):,} |"
        )
    lines += [
        "",
        "Notes:",
        "- Anthropic numbers are local `cl100k_base` proxy counts; exact `messages/count_tokens` requires a live Anthropic API key.",
        "- OpenAI numbers use local `o200k_base`; if the backend column says `approx-ru-fallback`, tiktoken data was unavailable.",
        "- Other/classic clients ignore `_meta` defer hints and therefore receive the full 19-tool surface upfront.",
        "- Sum-of-parts is analytical and includes shared server instructions/prompts for each profile; compare envelope columns for tools/list cost.",
    ]
    return "\n".join(lines)


def format_surface_markdown(report: dict[str, Any]) -> str:
    """Render the surface report as a human-readable markdown string."""
    env = report.get("tools_list_envelope", {})
    profile = report.get("tool_profile", {})
    lines = [
        f"# Token Usage Report ({report['tokenizer']})",
        "",
        f"- **Version:** `{report['version']}`",
        f"- **Timestamp:** {report['timestamp']}",
        f"- **Tokenizer backend:** `{report.get('tokenizer_backend', '?')}`",
        f"- **Tool profile:** `{profile.get('name', 'all_tools')}` "
        f"({profile.get('tool_count', len(report.get('per_tool', {})))} tools)",
        "",
        "## What the LLM actually spends per request (tools/list envelope)",
        "",
        f"- **Compact JSON:** {env.get('compact_tokens', 0):,} tokens "
        f"(Claude/OpenAI-style API serialization — realistic minimum)",
        f"- **Indented JSON:** {env.get('indented_tokens', 0):,} tokens "
        f"(maximum if client pretty-prints)",
        "",
        "Every conversation turn pays this envelope cost. All other numbers "
        "below are **analytical breakdowns** — useful for comparing tools, "
        "but not additive to the envelope.",
        "",
        "## Analytical breakdown (per-tool sum)",
        "",
        f"- **Grand total (sum-of-parts):** {report['grand_total_tokens']:,} tokens "
        f"({report['pct_of_200k_context']}% of 200K Claude context)",
        f"- Instructions: {report['instructions']['tokens']:,} tokens "
        f"({report['instructions']['chars']} chars)",
        f"- All tools (sum): {report['total_tools_tokens']:,} tokens",
        f"- All prompts: {report['total_prompts_tokens']:,} tokens",
        f"- All $defs (Pydantic models): {report['total_defs_tokens']:,} tokens",
        "",
        "## Top-10 heaviest tools",
        "",
        "| Tool | Total | Description | Schema | Annotations |",
        "|------|-------|-------------|--------|-------------|",
    ]
    top = sorted(report["per_tool"].items(),
                 key=lambda kv: -kv[1]["total"])[:10]
    for name, d in top:
        lines.append(
            f"| `{name}` | {d['total']:,} | {d['description_tokens']} | "
            f"{d['schema_tokens']} | {d['annotations_tokens']} |"
        )
    lines += ["", "## Per-category", "",
              "| Category | Tools | Tokens |",
              "|----------|-------|--------|"]
    for cat, data in sorted(report["per_category"].items(), key=lambda kv: -kv[1]["tokens"]):
        lines.append(f"| {cat} | {data['count']} | {data['tokens']:,} |")
    if report["defs_tokens"]:
        lines += ["", "## Pydantic models ($defs)", "",
                  "| Model | Tokens |", "|-------|--------|"]
        for model_name, tok in list(report["defs_tokens"].items())[:15]:
            lines.append(f"| `{model_name}` | {tok:,} |")
    return "\n".join(lines)
