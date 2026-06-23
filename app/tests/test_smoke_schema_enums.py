"""Smoke tests — verify JSON Schema enums, Field descriptions,
and missing_params helper with structured error shape."""
import asyncio
import sys

from app.server import mcp
from app.core.exceptions import missing_params
from app.tools.component_operations import component_operations, _conditional_rule_add
from app.tools.dataset_operations import dataset_operations
from app.tools.report_operations import report_operations
from app.tools.reportgroup_operations import reportgroup_operations
from app.tools.datasource_operations import datasource_operations
from app.tools.security_operations import security_operations
from app.tools.style_operations import style_operations
from app.tools.batch_operations import batch_operations
from app.tools.report_template import report_template
from app.tools.export_data import export_operations


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

    section("JSON Schema: action enum on 14 tools")
    expected_with_enum = {
        "instance_operations", "report_operations", "dataset_operations",
        "component_crud", "component_filters", "component_axes",
        "component_styling",
        "datasource_operations", "style_operations", "reportgroup_operations",
        "data_export_operations", "batch_operations", "report_template",
        "security_operations",
    }
    for name in expected_with_enum:
        t = mcp._tool_manager._tools.get(name)
        schema = t.parameters
        action_prop = schema.get("properties", {}).get("action", {})
        # Pydantic may wrap in allOf/$ref; enum might be at top or in $defs
        enum = action_prop.get("enum")
        if not enum:
            refs = action_prop.get("allOf") or []
            for ref in refs:
                if "$ref" in ref:
                    ref_path = ref["$ref"].split("/")[-1]
                    enum = schema.get("$defs", {}).get(ref_path, {}).get("enum")
                    break
        check(f"{name} action enum present", bool(enum),
              f"len={len(enum) if enum else 0}")

    section("JSON Schema: enum length sanity")
    sanity = {
        "component_crud": 16,
        "component_filters": 8,  # + filters_grid_layout
        "component_axes": 26,
        "report_operations": 24,
        "dataset_operations": 7,
    }
    for name, expected_len in sanity.items():
        t = mcp._tool_manager._tools.get(name)
        schema = t.parameters
        action_prop = schema.get("properties", {}).get("action", {})
        enum = action_prop.get("enum")
        if not enum:
            refs = action_prop.get("allOf") or []
            for ref in refs:
                if "$ref" in ref:
                    ref_path = ref["$ref"].split("/")[-1]
                    enum = schema.get("$defs", {}).get(ref_path, {}).get("enum")
                    break
        check(f"{name} enum len == {expected_len}",
              enum and len(enum) == expected_len,
              f"got {len(enum) if enum else 0}")

    section("JSON Schema: Field(description=) on critical params")
    t = mcp._tool_manager._tools["component_crud"]
    schema = t.parameters
    for pname in ("report_id", "component_idx", "config_overrides"):
        p = schema["properties"].get(pname, {})
        desc = p.get("description")
        if not desc:
            for alt in p.get("anyOf") or []:
                desc = alt.get("description") or desc
        check(f"component_crud.{pname} has description",
              bool(desc and len(desc) > 10))

    section("JSON Schema: Literal enums on value params")
    t = mcp._tool_manager._tools["component_crud"]
    schema = t.parameters
    agg = schema["properties"].get("aggregation", {})
    enum = agg.get("enum") or []
    check("aggregation enum has sum/avg/max/min/count/none",
          set(["sum", "avg", "max", "min", "count", "none"]).issubset(set(enum)))

    preset = schema["properties"].get("preset", {})
    enum = preset.get("enum") or (preset.get("anyOf") and preset["anyOf"][0].get("enum")) or []
    check("preset enum has kpi/minimal/dashboard",
          set(["kpi", "minimal", "dashboard"]).issubset(set(enum)))

    section("missing_params helper shape")
    r = missing_params(["a", "b"], tool="component_crud", action="add",
                      example="component_crud(action='add', ...)")
    check("missing_params returns success=False", r.get("success") is False)
    check("missing_params has missing list", r.get("missing") == ["a", "b"])
    check("missing_params has hint", "hint" in r and "help" in r["hint"])
    check("missing_params has example", "example" in r)

    section("Pydantic surfaces ALL type errors at once")
    from pydantic import ValidationError as _VE
    t = mcp._tool_manager._tools["component_crud"]
    model_cls = t.fn_metadata.arg_model
    errs = []
    try:
        model_cls.model_validate({
            "action": "bogus_action",
            "aggregation": "bogus_agg",
            "preset": "bogus_preset",
        })
    except _VE as e:
        errs = e.errors()
    check("Pydantic reports all 3 invalid Literal values", len(errs) >= 3,
          f"got {len(errs)} errors")
    bad_locs = {'.'.join(str(x) for x in err["loc"]) for err in errs}
    check("All 3 invalid params reported (action, aggregation, preset)",
          {"action", "aggregation", "preset"}.issubset(bad_locs))

    section("require() reports ALL missing at once with expected_types")
    r = await component_operations(client=None, action="page_rename")
    check("page_rename (4 required) lists all 4 missing",
          set(r.get("missing", [])) == {"report_id", "component_idx", "page_id", "title"})
    check("page_rename returns expected_types for each",
          isinstance(r.get("expected_types"), dict) and
          set(r["expected_types"].keys()) == {"report_id", "component_idx", "page_id", "title"})

    r = await component_operations(client=None, action="page_rename", report_id=35, component_idx=0)
    check("page_rename with 2/4 provided lists only the 2 missing",
          set(r.get("missing", [])) == {"page_id", "title"})
    check("expected_types narrows to missing only",
          set(r.get("expected_types", {}).keys()) == {"page_id", "title"})

    r = await component_operations(client=None, action="update", report_id=35)
    check("update with report_id provided reports only component_idx missing",
          r.get("missing") == ["component_idx"])

    section("Dispatchers return structured errors, no NameError")
    cases = [
        ("component_operations.get",
         lambda: component_operations(client=None, action="get")),
        ("dataset_operations.get",
         lambda: dataset_operations(client=None, action="get")),
        ("report_operations.get",
         lambda: report_operations(client=None, action="get")),
        ("reportgroup_operations.create",
         lambda: reportgroup_operations(client=None, action="create")),
        ("datasource_operations.get",
         lambda: datasource_operations(client=None, action="get")),
    ]
    for label, call in cases:
        try:
            r = await call()
            has_missing = isinstance(r.get("missing"), list) and len(r["missing"]) > 0
            check(f"{label} returns structured missing_params",
                  r.get("success") is False and has_missing)
        except Exception as e:
            check(f"{label} runs without exception", False, f"{type(e).__name__}: {e}")

    section("require() migrated into all 10 dispatchers + inner validators")
    migration_checks = [
        ("security_operations.update_filter",
         lambda: security_operations(client=None, action="update_filter"),
         {"dataset_id", "rls_query"}),
        ("style_operations.update",
         lambda: style_operations(client=None, action="update", css=".x{}"),
         {"report_id"}),
        ("batch_operations.components_add",
         lambda: batch_operations(client=None, action="components_add"),
         {"report_id", "components"}),
        ("batch_operations.reports_export",
         lambda: batch_operations(client=None, action="reports_export"),
         {"report_ids"}),
        ("report_template.scaffold",
         lambda: report_template(client=None, action="scaffold"),
         {"template"}),
        ("export_data.component_csv",
         lambda: export_operations(client=None, action="component_csv"),
         {"report_id", "component_idx"}),
        ("component_operations.layout_update_breakpoint partial",
         lambda: component_operations(client=None, action="layout_update_breakpoint", report_id=35),
         {"component_idx", "breakpoint"}),
        ("component_operations.field_sort_set",
         lambda: component_operations(client=None, action="field_sort_set"),
         {"report_id", "component_idx", "value_field"}),
    ]
    for label, call, expected_missing in migration_checks:
        try:
            r = await call()
            actually_missing = set(r.get("missing", []))
            ok_flag = (r.get("success") is False
                       and actually_missing == expected_missing
                       and isinstance(r.get("expected_types"), dict)
                       and set(r["expected_types"].keys()) == expected_missing
                       and r.get("example"))
            check(f"{label}: correct missing + expected_types + example", ok_flag,
                  f"got missing={actually_missing}, expected={expected_missing}")
        except Exception as e:
            check(f"{label} runs cleanly", False, f"{type(e).__name__}: {e}")

    section("Inner validators also aggregate errors")
    r = await _conditional_rule_add(client=None, report_id=35, component_idx=0,
                                     rule_config={"field": "amount"})
    check("conditional_rule_add rule_config partial → lists missing operator + value",
          set(r.get("missing", [])) == {"operator", "value"})
    check("rule validator returns expected_types for missing keys",
          set(r.get("expected_types", {}).keys()) == {"operator", "value"})

    section("Example field populated for key add/create dispatch errors")
    r = await component_operations(client=None, action="add",
                                    component_type="HsBarAMchartsChart")
    check("component_operations.add missing → example includes HsBar...",
          "example" in r and "HsBarAMchartsChart" in r["example"])
    r = await dataset_operations(client=None, action="create")
    check("dataset_operations.create missing → example includes SQL",
          "example" in r and "SELECT" in r["example"])

    section("No regression from base smoke")
    # Re-run key  checks inline
    from app.core.validation import sanitize_html
    check("sanitize_html still strips <script>",
          "<script>" not in (sanitize_html("<p>x</p><script>bad()</script>") or ""))
    check("Total tool count is 19 (legacy component_operations removed)",
          len(mcp._tool_manager._tools) == 19)

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
