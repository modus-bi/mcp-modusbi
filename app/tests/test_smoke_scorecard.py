"""Smoke tests — MCP Scorecard compliance.

Verifies: stdout purity, Pydantic models in JSON Schema, Field descriptions
on all params, FastMCP instructions, ToolAnnotations, destructive markers,
readonly-by-default mode.
"""
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from app.server import mcp, SERVER_INSTRUCTIONS
from app.tools.param_docs import CANONICAL
from app.tools.schemas import (
    SelectField, WhereClause, GroupClause, OrderClause,
    BatchQuerySpec, BatchQueryParams,
    ComponentSpec, LayoutSpec, ReportGroupOptions,
)


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

    # === Секция 1: stdout purity ===
    section("stdout purity (subprocess run)")
    py = sys.executable
    repo_root = Path(__file__).resolve().parents[2]
    # Dummy creds so the lifespan env-check passes and the server actually starts
    # (auth fails gracefully as a warning). Without these the server exits on missing
    # MODUSBI_* env in credless CI → empty stdout → JSON parse errors in the handshake.
    smoke_env = {**os.environ, "MODUSBI_URL": "https://example.com",
                 "MODUSBI_USERNAME": "smoke", "MODUSBI_PASSWORD": "smoke"}
    try:
        result = subprocess.run(
            [py, "-u", "-m", "app.server", "--readonly"],
            cwd=str(repo_root), capture_output=True, timeout=5, env=smoke_env,
        )
        out_b, err_b = result.stdout, result.stderr
    except subprocess.TimeoutExpired as e:
        # Server stays alive waiting on stdin — expected; capture partial output.
        out_b, err_b = e.stdout or b"", e.stderr or b""
    check("stdout is empty when no stdin activity",
          out_b == b"",
          detail=f"got {len(out_b)} bytes")
    check("stderr contains log lines",
          b"Server started" in err_b or b"Security mode" in err_b)

    # JSON-RPC handshake check — every stdout line must parse as JSON
    proc = await asyncio.create_subprocess_exec(
        py, "-m", "app.server", "--readonly",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(repo_root), limit=2 * 1024 * 1024, env=smoke_env,
    )
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    for m in msgs:
        proc.stdin.write((json.dumps(m) + "\n").encode())
    await proc.stdin.drain()
    init_resp = await asyncio.wait_for(proc.stdout.readline(), timeout=3)
    tools_resp = await asyncio.wait_for(proc.stdout.readline(), timeout=3)
    try:
        proc.terminate()
        await asyncio.wait_for(proc.wait(), timeout=1)
    except Exception:
        proc.kill()

    check("initialize response is valid JSON-RPC",
          json.loads(init_resp).get("id") == 1)
    check("tools/list response is valid JSON-RPC",
          json.loads(tools_resp).get("id") == 2)
    init_result = json.loads(init_resp)["result"]
    check("initialize response includes instructions",
          len(init_result.get("instructions", "")) > 500)

    # === Секция 2: Pydantic models via $defs ===
    section("Pydantic models in JSON Schema")
    TARGETS = {
        "dataset_query": ["select", "where", "group", "order"],
        "query_batch": ["queries"],
        "batch_operations": ["components", "layouts"],
        "reportgroup_operations": ["group_options"],
    }
    for tool_name, params in TARGETS.items():
        t = mcp._tool_manager._tools[tool_name]
        schema = t.parameters
        for p in params:
            info = schema["properties"].get(p, {})
            alts = info.get("anyOf") or [info]
            has_ref = False
            for alt in alts:
                if "$ref" in alt:
                    has_ref = True
                if alt.get("type") == "array":
                    items = alt.get("items", {})
                    if "$ref" in items:
                        has_ref = True
            check(f"{tool_name}.{p} references a Pydantic model via $ref", has_ref)

    # Strict models reject extras
    try:
        SelectField(name="x", bogus="y")
        check("SelectField rejects extras", False)
    except Exception:
        check("SelectField rejects extras", True)
    try:
        WhereClause(name="x", op="=", value=1, bogus="y")
        check("WhereClause rejects extras", False)
    except Exception:
        check("WhereClause rejects extras", True)

    # Soft models accept extras
    c = ComponentSpec(component_type="HsBar", title="t", custom_slug="allowed")
    check("ComponentSpec accepts extras (soft)",
          c.model_dump(exclude_none=True).get("custom_slug") == "allowed")
    g = ReportGroupOptions(icon="x", custom_key="y")
    check("ReportGroupOptions accepts extras (soft)",
          g.model_dump(exclude_none=True).get("custom_key") == "y")

    # WhereClause.value supports list (for 'in')
    w = WhereClause(name="region", op="in", value=["Moscow", "SPb"])
    check("WhereClause.value accepts list for 'in'", w.value == ["Moscow", "SPb"])

    # === Секция 3: Field descriptions on every param ===
    section("Field descriptions coverage")
    missing = []
    for name, t in sorted(mcp._tool_manager._tools.items()):
        for p, info in (t.parameters or {}).get("properties", {}).items():
            if not isinstance(info, dict):
                continue
            if info.get("description"):
                continue
            is_enum = bool(info.get("enum"))
            for alt in (info.get("anyOf") or []) + (info.get("allOf") or []):
                if alt.get("enum"):
                    is_enum = True
            if "$ref" in info:
                is_enum = True
            if not is_enum:
                missing.append(f"{name}.{p}")
    check("0 params without description (non-enum)",
          len(missing) == 0,
          detail=f"{len(missing)} missing: {missing[:3]}")
    check("CANONICAL dict has ≥ 50 canonical entries",
          len(CANONICAL) >= 50,
          detail=f"got {len(CANONICAL)}")

    # === Секция 4: Server-level instructions ===
    section("Server-level instructions")
    check("mcp.instructions is set", bool(mcp.instructions))
    check("instructions length >= 500",
          len(mcp.instructions) >= 500,
          detail=f"got {len(mcp.instructions)}")
    check("instructions mention workflow / workflow",
          "workflow" in mcp.instructions.lower())
    check("instructions mention readonly default",
          "readonly" in mcp.instructions.lower())

    # === Секция 5: Readonly-by-default ===
    section("Readonly-by-default CLI")
    def _boot_stderr(argv: list, tmo: float = 5) -> str:
        """Start server, close stdin to make it exit, capture stderr."""
        try:
            result = subprocess.run(
                argv, cwd=str(repo_root), capture_output=True, timeout=tmo,
            )
            return result.stderr.decode("utf-8", "replace")
        except subprocess.TimeoutExpired as e:
            # stderr might still have useful content
            return (e.stderr or b"").decode("utf-8", "replace")

    stderr = _boot_stderr([py, "-u", "-m", "app.server"])
    check("default boot logs READONLY mode",
          "READONLY" in stderr.upper())
    stderr = _boot_stderr([py, "-u", "-m", "app.server", "--readwrite"])
    check("--readwrite boot logs READWRITE with destructive warning",
          "READWRITE" in stderr.upper() and "DESTRUCTIVE" in stderr.upper())

    # === Секция 6: Destructive markers in docstrings ===
    section("Destructive markers")
    # instance_operations is read-only (only list/get_active).
    DESTRUCTIVE_TOOLS = {
        "report_operations", "component_crud",
        "dataset_operations", "reportgroup_operations", "style_operations",
        "security_operations", "batch_operations",
        "datasource_operations", "component_filters", "component_axes",
        "component_styling", "report_template",
    }
    kw = re.compile(
        r"destructive|irreversible|cannot be undone|permanently|deletes|removes|warning|overwrites",
        re.IGNORECASE,
    )
    for tname in DESTRUCTIVE_TOOLS:
        desc = mcp._tool_manager._tools[tname].description or ""
        check(f"{tname} has ⚠ marker", "⚠" in desc)
        keywords = set(k.lower() for k in kw.findall(desc))
        check(f"{tname} has ≥ 2 destructive keywords",
              len(keywords) >= 2,
              detail=f"found {keywords}")

    # === Секция 7: ToolAnnotations ===
    section("ToolAnnotations")
    # instance_operations is read-only too (only list/get_active).
    RO = {"dataset_query", "query_batch", "sql_query_validate",
          "preflight_check_datasource", "data_export_operations",
          "instance_operations"}
    for name, t in mcp._tool_manager._tools.items():
        ann = t.annotations
        check(f"{name}.annotations set", ann is not None)
        if name in RO:
            check(f"{name} is readOnlyHint=True",
                  ann and ann.readOnlyHint is True)
            check(f"{name} is idempotentHint=True",
                  ann and ann.idempotentHint is True)
        else:
            check(f"{name} is destructiveHint=True",
                  ann and ann.destructiveHint is True)
        check(f"{name} is openWorldHint=True",
              ann and ann.openWorldHint is True)

    # === Секция 7b: Scorecard CI artifacts ===
    section("Scorecard CI artifacts")
    repo = Path(__file__).resolve().parents[2]
    check("scripts/run_scorecard.sh exists and is executable",
          (repo / "scripts/run_scorecard.sh").exists())
    check("scripts/scorecard_summary.py exists",
          (repo / "scripts/scorecard_summary.py").exists())
    baseline_json = repo / "docs/scorecard/2026-06-22.json"
    check("docs/scorecard baseline JSON exists", baseline_json.exists())
    if baseline_json.exists():
        baseline = json.loads(baseline_json.read_text())
        total = baseline.get("scorecard", {}).get("total_score", {})
        check("baseline score >= 90", total.get("value", 0) >= 90,
              detail=f"got {total.get('value')}")

    # === Секция 8: Invariants ===
    section("Invariants")
    check("tool count == 19",
          len(mcp._tool_manager._tools) == 19,
          detail=f"got {len(mcp._tool_manager._tools)}")
    check("prompt count == 10",
          len(mcp._prompt_manager._prompts) == 10,
          detail=f"got {len(mcp._prompt_manager._prompts)}")

    # === Секция 9: Scorecard-style self-checks ===
    section("Scorecard self-checks")
    # weak_input_schema — no generic keys with underconstrained object schemas
    GENERIC_KEYS = {"input", "payload", "data", "body", "request", "params",
                    "parameters", "options", "query", "filter", "command"}
    flagged = []
    for tname, t in mcp._tool_manager._tools.items():
        for pname, info in (t.parameters or {}).get("properties", {}).items():
            if pname not in GENERIC_KEYS:
                continue
            ptype = info.get("type")
            if not isinstance(ptype, str):
                # Could be flagged — check if this is Pydantic-modeled through $ref
                alts = info.get("anyOf") or []
                has_ref = any("$ref" in a for a in alts)
                if not has_ref:
                    flagged.append(f"{tname}.{pname}")
    check("0 generic_input_keys params with weak schema",
          len(flagged) == 0,
          detail=f"flagged: {flagged}")

    # Tool names are not overly generic
    GENERIC_TOOL_NAMES = {"do_it", "execute", "run", "perform", "action", "tool", "call"}
    for tname in mcp._tool_manager._tools:
        check(f"{tname} is not overly generic",
              tname.lower() not in GENERIC_TOOL_NAMES)

    # === Секция 9: No regression from base smoke ===
    section("No regression from base smoke")
    for script in ("test_smoke_tools_load", "test_smoke_schema_enums"):
        r = subprocess.run(
            [py, "-m", f"app.tests.{script}"],
            cwd=str(repo_root), capture_output=True, timeout=60,
        )
        check(f"{script} still passes", r.returncode == 0,
              detail=f"rc={r.returncode}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
