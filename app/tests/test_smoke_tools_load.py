"""Smoke tests — verify all tools load and help actions work."""
import asyncio
import sys
from app.server import (
    mcp,
    component_crud,
    component_filters,
    component_axes,
    component_styling,
    report_operations,
    dataset_operations,
)
from app.core.exceptions import error_response
from app.core.validation import sanitize_html
from app.tools.help_texts import _help, HELP_COMPONENT_CRUD, HELP_REPORT


def section(name):
    print(f"\n=== {name} ===")


async def main():
    ok = 0
    fail = 0

    def check(label, cond, detail=""):
        nonlocal ok, fail
        mark = "OK " if cond else "FAIL"
        if cond:
            ok += 1
        else:
            fail += 1
        print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))

    section("Tool registry")
    tools = mcp._tool_manager._tools
    check("19 tools registered", len(tools) == 19, f"got {len(tools)}")

    expected_tools = {
        "instance_operations", "report_operations", "dataset_operations",
        "component_crud", "component_filters", "component_axes", "component_styling",
        "datasource_operations", "dataset_query", "query_batch",
        "sql_query_validate", "dataset_create_from_sql",
        "preflight_check_datasource", "style_operations",
        "reportgroup_operations", "data_export_operations", "batch_operations",
        "report_template", "security_operations",
    }
    missing = expected_tools - set(tools.keys())
    extra = set(tools.keys()) - expected_tools
    check("All expected tools present", not missing and not extra,
          f"missing={missing} extra={extra}")
    check("relationship_operations removed", "relationship_operations" not in tools)
    check("component_operations (legacy) removed", "component_operations" not in tools)

    section("Help actions")
    tests = [
        ("component_crud", component_crud, {"action": "help"}, "actions"),
        ("component_crud[add]", component_crud, {"action": "help", "slug_category": "add"}, "examples"),
        ("component_filters", component_filters, {"action": "help"}, "actions"),
        ("component_axes", component_axes, {"action": "help"}, "actions"),
        ("component_styling", component_styling, {"action": "help"}, "actions"),
        ("report_operations", report_operations, {"action": "help"}, "actions"),
        ("report_operations[clone]", report_operations, {"action": "help", "name": "clone"}, "examples"),
        ("dataset_operations", dataset_operations, {"action": "help"}, "actions"),
    ]
    for name, fn, kwargs, key in tests:
        try:
            r = await fn(**kwargs)
            check(f"{name} help", r.get("success") is True and (key in r))
        except Exception as e:
            check(f"{name} help", False, str(e))

    section("Help — unknown action rejection")
    r = await component_crud(action="help", slug_category="nonexistent_action")
    check("unknown action returns success=False",
          r.get("success") is False and "available_actions" in r)

    section("error_response helper")
    r = error_response("boom", hint="try again", details="trace", foo=1)
    check("error_response structure",
          r == {"success": False, "error": "boom", "hint": "try again",
                "details": "trace", "foo": 1})

    section("sanitize_html")
    bad = '<p>ok</p><script>evil()</script><img src=x onerror="alert(1)"><a href="javascript:bad()">x</a>'
    clean = sanitize_html(bad)
    check("no <script>", "<script>" not in clean)
    check("no onerror", "onerror" not in clean.lower())
    check("javascript: neutralized", "javascript:" not in clean.lower())
    check("sanitize None returns None", sanitize_html(None) is None)
    check("sanitize empty returns empty", sanitize_html("") == "")

    section("HELP map structure")
    r = _help(None, HELP_COMPONENT_CRUD)
    check("HELP_COMPONENT_CRUD has overview", bool(r.get("overview")))
    check("HELP_COMPONENT_CRUD has >=10 actions", len(r.get("actions", [])) >= 10)
    r = _help("add", HELP_COMPONENT_CRUD)
    check("HELP_COMPONENT_CRUD[add] has examples",
          r.get("success") is True and r.get("examples"))

    section("Docstring sizes")
    # Budgets accommodate the required destructive-action markers
    # (⚠️ DESTRUCTIVE, irreversible, cannot be undone, permanently
    # deletes/removes). The Metadata category scans docstrings by regex for
    # these keywords, so they must stay inline.
    expected = {
        "component_crud": 1500,
        "component_filters": 1200,
        "component_axes": 2100,
        "component_styling": 1000,
        "report_operations": 1500,
        "dataset_operations": 1300,
        "dataset_create_from_sql": 1500,
    }
    total = 0
    for name, max_chars in expected.items():
        t = tools.get(name)
        if not t:
            check(f"{name} exists", False)
            continue
        size = len(t.fn.__doc__ or "")
        total += size
        check(f"{name} docstring <= {max_chars} chars", size <= max_chars,
              f"size={size}")
    check("Total big-7 docstrings < 10000 chars", total < 10000, f"total={total}")

    section("Deprecated refs cleanup")
    from app.tools import builders, config_schema
    check("HsPivotOrbChart not in CHART_TYPE_MAP",
          "HsPivotOrbChart" not in config_schema.CHART_TYPE_MAP)
    check("HsPivotMdxChart not in CHART_TYPE_MAP",
          "HsPivotMdxChart" not in config_schema.CHART_TYPE_MAP)
    import app.tools.query_execute as qe
    check("parse_sql_column_aliases removed",
          not hasattr(qe, "parse_sql_column_aliases"))
    check("wrap_with_sort_preservation removed",
          not hasattr(qe, "wrap_with_sort_preservation"))

    section("Prompts load")
    from app.prompts import get_prompts
    p = get_prompts()
    check("10 prompts load", len(p) == 10, f"got {len(p)}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
