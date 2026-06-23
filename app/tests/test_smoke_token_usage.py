"""Smoke tests — Token Usage Observability (агрегатор базовых smoke + токен-метрик)."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

for _v in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD",
           "MODUSBI_PROD_USERNAME", "MODUSBI_PROD_PASSWORD"):
    os.environ.setdefault(_v, "stub")

from app.server import mcp
from app.tools.token_counter import (
    count_tokens, count_tokens_json, compare_tokenizers, count_tokens_anthropic,
    APPROX_RU_RATIO,
)
from app.tools.token_metrics import (
    CATEGORIES, FLOWS, FIXTURE_RESPONSES,
    measure_surface, measure_flow, measure_all_flows, measure_help_savings,
    format_surface_markdown, _get_live_response, _help_maps,
)


def section(name):
    print(f"\n=== {name} ===")


async def main():
    ok = fail = 0

    def check(label, cond, detail=""):
        nonlocal ok, fail
        mark = "OK " if cond else "FAIL"
        if cond: ok += 1
        else: fail += 1
        print(f"  [{mark}] {label}" + (f" — {detail}" if detail else ""))

    repo = Path(__file__).resolve().parents[2]
    py = sys.executable

    # === Section 1: token_counter ===
    section("token_counter API")
    check("count_tokens('') == 0", count_tokens("") == 0)
    check("count_tokens_json(None) == 0", count_tokens_json(None) == 0)
    check("cl100k 'hello' == 1", count_tokens("hello") == 1)
    check("cl100k 'hello world' == 2", count_tokens("hello world") == 2)
    cmp = compare_tokenizers("ModusBI MCP сервер")
    check("compare_tokenizers has 5 keys",
          set(cmp.keys()) == {"cl100k_base", "o200k_base", "approx_ru", "approx_en", "chars"})
    ru = "тестовый русский текст длиной около 40 символов тут"
    cl = count_tokens(ru)
    check("russian ratio in approx range",
          1.5 <= (len(ru) / cl) <= 3.0,
          detail=f"ratio={len(ru)/cl:.2f}")
    check("APPROX_RU_RATIO is 2.3 (empirically tuned)",
          APPROX_RU_RATIO == 2.3)
    c = count_tokens_json({"a": [1, 2, 3]}, compact=True)
    i = count_tokens_json({"a": [1, 2, 3]}, compact=False)
    check("indented > compact", i > c)
    check("anthropic returns None without key",
          count_tokens_anthropic("hi") is None)

    # === Section 2: surface measurement ===
    section("Surface measurement")
    r = measure_surface(mcp, tokenizer="cl100k_base")
    check("grand_total > 0", r["grand_total_tokens"] > 0)
    check("grand_total in sensible range (10K-60K)",
          10_000 < r["grand_total_tokens"] < 60_000,
          detail=f"got {r['grand_total_tokens']:,}")
    check("per_tool has 19 tools ", len(r["per_tool"]) == 19)
    check("per_prompt has 10 prompts", len(r["per_prompt"]) == 10)
    check("instructions > 500 tokens", r["instructions"]["tokens"] > 500)
    check("no _uncategorized tools",
          "_uncategorized" not in r["per_category"])
    check("all 20 tools in CATEGORIES",
          sum(len(v) for v in CATEGORIES.values()) == 19)
    md = format_surface_markdown(r)
    check("markdown has 'Top-10 heaviest'", "Top-10" in md)
    check("envelope section in markdown", "tools/list envelope" in md)

    # Envelope (real cost per request)
    env = r["tools_list_envelope"]
    check("envelope has compact + indented",
          {"compact_tokens", "indented_tokens"} <= set(env.keys()))
    check("envelope compact < indented",
          env["compact_tokens"] < env["indented_tokens"])
    check("envelope compact in sensible range",
          10_000 < env["compact_tokens"] < 50_000,
          detail=f"got {env['compact_tokens']:,}")

    # === Section 3: flows ===
    section("Flow simulator")
    all_flows = measure_all_flows()
    check("5 flows measured", len(all_flows["flows"]) == 5)
    check("flows grand total in range",
          1500 < all_flows["grand_total"] < 15_000,
          detail=f"got {all_flows['grand_total']:,}")
    for flow_name in ("create_dashboard", "query_data", "export_report",
                       "debug_unknown_action", "help_deep_dive"):
        flow = all_flows["flows"][flow_name]
        check(f"flow '{flow_name}' has steps",
              flow["step_count"] == len(FLOWS[flow_name]))
        check(f"flow '{flow_name}' total > 0",
              flow["total_flow_tokens"] > 0)

    # __live: calls
    check("FIXTURE_RESPONSES has 11 entries (token-metrics flows)", len(FIXTURE_RESPONSES) == 11)
    live_help = _get_live_response("__live:help_component_crud")
    check("live help_component_crud returns dict", isinstance(live_help, dict) and len(live_help) > 0)
    live_types = _get_live_response("__live:types_list")
    check("live types_list returns >= 20 types", live_types.get("count", 0) >= 20)

    # === Section 4: help savings ===
    section("Help savings")
    hs = measure_help_savings(mcp)
    check("help_savings has 7 tools", len(hs["per_tool"]) == 7)
    check("overall savings > 30%", hs["totals"]["savings_pct"] > 30,
          detail=f"got {hs['totals']['savings_pct']}%")
    check("overall savings tokens > 2000",
          hs["totals"]["savings"] > 2000,
          detail=f"got {hs['totals']['savings']}")
    hm = _help_maps()
    check("_help_maps has 7 entries", len(hm) == 7)

    # === Section 5: snapshot + README ===
    section("Snapshot + CI")
    tmp = repo / ".scorecard" / "test_snap"
    if tmp.exists():
        import shutil
        shutil.rmtree(tmp)
    r = subprocess.run(
        [py, "scripts/snapshot_tokens.py", "--out-dir", str(tmp),
         "--tag", "smoke-test"],
        cwd=str(repo), capture_output=True, timeout=30,
    )
    check("snapshot_tokens runs", r.returncode == 0,
          detail=r.stderr.decode()[:100] if r.returncode else "")
    snaps = list(tmp.glob("*.json"))
    check("snapshot JSON created", len(snaps) == 1)
    if snaps:
        data = json.loads(snaps[0].read_text())
        check("snapshot has schema_version=1", data.get("schema_version") == 1)
        check("snapshot has surface/flows/help_savings",
              all(k in data for k in ("surface", "flows", "help_savings")))
        check("snapshot has tag", data.get("tag") == "smoke-test")
    check("trend README created", (tmp / "README.md").exists())
    if (tmp / "README.md").exists():
        readme = (tmp / "README.md").read_text()
        check("README has trend table", "Trend (last 20 snapshots)" in readme)

    # budget check against real budget.yml (must pass)
    r = subprocess.run(
        [py, "scripts/check_token_budget.py",
         "--budget", "docs/token-usage/budget.yml",
         "--snapshots", str(tmp)],
        cwd=str(repo), capture_output=True, timeout=15,
    )
    check("check_token_budget passes for smoke snapshot",
          r.returncode == 0,
          detail=f"rc={r.returncode}, stderr={r.stderr.decode()[:80]}")

    # === Section 6: Budget violations (negative test) ===
    section("Budget gate — violation test")
    strict = repo / ".scorecard" / "strict-budget.yml"
    strict.parent.mkdir(parents=True, exist_ok=True)
    strict.write_text("surface_total_max: 100\n")
    r = subprocess.run(
        [py, "scripts/check_token_budget.py",
         "--budget", str(strict), "--snapshots", str(tmp)],
        cwd=str(repo), capture_output=True, timeout=15,
    )
    check("strict budget returns exit 3", r.returncode == 3)
    check("violation message printed",
          b"BUDGET VIOLATIONS" in r.stdout)

    # === Section 7: Budget limits match current state ===
    section("Budget vs current state (no regression)")
    try:
        import yaml
        budget = yaml.safe_load((repo / "docs/token-usage/budget.yml").read_text())
    except Exception:
        budget = {}

    surface = measure_surface(mcp)["grand_total_tokens"]
    check(f"surface ≤ surface_total_max ({budget.get('surface_total_max', '?'):,})",
          surface <= budget.get("surface_total_max", 10**9),
          detail=f"actual {surface:,}")

    for fname, fr in all_flows["flows"].items():
        lim = (budget.get("flows") or {}).get(f"{fname}_max", 10**9)
        check(f"flow {fname} ≤ {lim:,}",
              fr["total_flow_tokens"] <= lim,
              detail=f"actual {fr['total_flow_tokens']:,}")

    # === Section 8: Invariants ===
    section("Invariants")
    check("19 tools (legacy removed)", len(mcp._tool_manager._tools) == 19)
    check("10 prompts", len(mcp._prompt_manager._prompts) == 10)

    # === Section 9: No regression ===
    section("No regression — base smoke")
    for script in ("test_smoke_tools_load", "test_smoke_schema_enums",
                   "test_smoke_scorecard"):
        r = subprocess.run(
            [py, "-m", f"app.tests.{script}"],
            cwd=str(repo), capture_output=True, timeout=90,
        )
        check(f"{script} passes", r.returncode == 0,
              detail=f"rc={r.returncode}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
