"""Human-readable markdown summary of MCP-Scorecard JSON report.

Usage:
    python scripts/scorecard_summary.py [path/to/scorecard.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import Counter


def main(argv: list[str]) -> int:
    path = Path(argv[1] if len(argv) > 1 else ".scorecard/scorecard.json")
    if not path.exists():
        print(f"ERROR: scorecard report not found at {path}")
        return 2

    data = json.loads(path.read_text())
    sc = data.get("scorecard", {})
    findings = data.get("findings", [])
    inventory = data.get("inventory", {})

    total = sc.get("total_score", {})
    score = total.get("value", "?")
    max_score = total.get("max", 100)
    print(f"# MCP Scorecard Report — {path.name}")
    print()
    print(f"**Score:** {score}/{max_score}")
    tool_count = inventory.get("tool_count") or inventory.get("total_tools") or len(inventory.get("tools", [])) or "?"
    print(f"**Tools discovered:** {tool_count}")
    print()

    cats = sc.get("category_scores", {})
    for cat, info in cats.items():
        print(f"- **{cat}:** {info.get('score', '?')}/{info.get('max_score', 100)} "
              f"(findings: {info.get('finding_count', 0)}, penalty: {info.get('penalty_points', 0)})")
    print()

    sev = Counter(f.get("severity", "?") for f in findings)
    print(f"**Findings:** {sev.get('error', 0)} error · "
          f"{sev.get('warning', 0)} warning · {sev.get('info', 0)} info")
    print()

    for bucket in ("conformance", "security", "ergonomics", "metadata"):
        bf = [f for f in findings if f.get("bucket") == bucket]
        if not bf:
            continue
        print(f"## {bucket.title()} ({len(bf)} findings)")
        print()
        by_id: dict[str, list] = {}
        for f in bf:
            by_id.setdefault(f.get("id", "?"), []).append(f)
        for fid, flist in by_id.items():
            first = flist[0]
            sevs = Counter(f.get("severity") for f in flist)
            sev_str = " · ".join(f"{s}:{c}" for s, c in sevs.items())
            print(f"- **{fid}** — {first.get('title', '')} ({sev_str})")
            tools = sorted({f.get("tool") for f in flist if f.get("tool")})
            if tools:
                print(f"  - Tools: {', '.join(f'`{t}`' for t in tools)}")
            if first.get("rationale"):
                print(f"  - {first['rationale']}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
