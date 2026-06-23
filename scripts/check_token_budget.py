"""Compare latest token snapshot against budget.yml.

Exit codes:
    0 — within budget (WARN on >10% vs previous snapshot)
    3 — budget violation

Usage:
    python scripts/check_token_budget.py
    python scripts/check_token_budget.py --budget other/budget.yml
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--budget", default="docs/token-usage/budget.yml")
    parser.add_argument("--snapshots", default="docs/token-usage")
    args = parser.parse_args()

    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. `pip install pyyaml`.", file=sys.stderr)
        return 2

    budget_path = Path(args.budget)
    if not budget_path.exists():
        print(f"ERROR: budget not found: {budget_path}", file=sys.stderr)
        return 2
    budget = yaml.safe_load(budget_path.read_text()) or {}

    snaps = []
    for _p in sorted(Path(args.snapshots).glob("*.json")):
        try:
            _d = json.loads(_p.read_text())
        except Exception:
            continue
        # Only token-surface snapshots (skip ui_meta_cost.json and other
        # schema_version=1 artifacts that have no "surface" block).
        if _d.get("schema_version") == 1 and "surface" in _d:
            snaps.append(_p)
    if not snaps:
        print("No snapshots yet — skipping budget check.")
        return 0

    latest = json.loads(snaps[-1].read_text())
    surface = latest["surface"].get("total_tools_tokens", 0)
    env = latest["surface"].get("tools_list_envelope", {})
    env_compact = env.get("compact_tokens", 0)
    env_indented = env.get("indented_tokens", 0)

    violations: list[str] = []
    if (lim := budget.get("tools_list_envelope_compact_max")) and env_compact > lim:
        violations.append(
            f"tools/list envelope (compact): {env_compact:,} > {lim:,}")
    if (lim := budget.get("tools_list_envelope_indented_max")) and env_indented > lim:
        violations.append(
            f"tools/list envelope (indented): {env_indented:,} > {lim:,}")
    if (lim := budget.get("surface_total_max")) and surface > lim:
        violations.append(f"surface_total: {surface:,} > {lim:,}")

    for fname, fdata in latest.get("flows", {}).items():
        lim = (budget.get("flows") or {}).get(f"{fname}_max")
        if lim and fdata["total_flow_tokens"] > lim:
            violations.append(f"flow.{fname}: {fdata['total_flow_tokens']:,} > {lim:,}")

    for cat, cdata in latest["surface"].get("per_category", {}).items():
        lim = (budget.get("categories") or {}).get(f"{cat}_max")
        if lim and cdata["tokens"] > lim:
            violations.append(f"category.{cat}: {cdata['tokens']:,} > {lim:,}")

    profile_limits = budget.get("client_profiles") or {}
    for profile_id, profile in latest.get("client_profiles", {}).items():
        limits = profile_limits.get(profile_id) or {}
        surface_report = profile.get("surface") or {}
        env = surface_report.get("tools_list_envelope", {})
        env_compact = env.get("compact_tokens", 0)
        env_indented = env.get("indented_tokens", 0)
        surface_total = surface_report.get("total_tools_tokens", surface_report.get("grand_total_tokens", 0))
        if (lim := limits.get("tools_list_envelope_compact_max")) and env_compact > lim:
            violations.append(
                f"client_profiles.{profile_id}.compact: {env_compact:,} > {lim:,}"
            )
        if (lim := limits.get("tools_list_envelope_indented_max")) and env_indented > lim:
            violations.append(
                f"client_profiles.{profile_id}.indented: {env_indented:,} > {lim:,}"
            )
        if (lim := limits.get("surface_total_max")) and surface_total > lim:
            violations.append(
                f"client_profiles.{profile_id}.surface: {surface_total:,} > {lim:,}"
            )

    # Growth warning (not fatal) — compare only with compatible schema_version=1 snapshots
    if len(snaps) >= 2:
        for prev_path in reversed(snaps[:-1]):
            prev = json.loads(prev_path.read_text())
            if prev.get("schema_version") != 1 or "surface" not in prev:
                continue
            prev_total = prev["surface"].get("total_tools_tokens", 0)
            if prev_total:
                delta_pct = 100 * (surface - prev_total) / prev_total
                if abs(delta_pct) >= 10:
                    sign = "+" if delta_pct > 0 else ""
                    print(f"WARN: surface changed {sign}{delta_pct:.1f}% vs {prev_path.name} "
                          f"({prev_total:,} → {surface:,})")
            break

    print(f"Latest snapshot: {snaps[-1].name}")
    print(f"  tools/list envelope (compact):  {env_compact:,} tokens")
    print(f"  tools/list envelope (indented): {env_indented:,} tokens")
    print(f"  Surface sum-of-parts:           {surface:,} tokens")
    print(f"  Flows total:                    {latest.get('flows_grand_total', 0):,} tokens")
    if latest.get("client_profiles"):
        print("  Client/tool-set profiles:")
        for profile_id, profile in latest["client_profiles"].items():
            surface_report = profile.get("surface") or {}
            profile_env = surface_report.get("tools_list_envelope", {})
            print(
                f"    - {profile_id}: "
                f"{profile_env.get('compact_tokens', 0):,} compact / "
                f"{surface_report.get('total_tools_tokens', 0):,} sum"
            )

    if violations:
        print("\nBUDGET VIOLATIONS:")
        for v in violations:
            print(f"  - {v}")
        return 3

    print("  [OK] Within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
