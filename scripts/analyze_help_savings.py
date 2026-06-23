"""CLI wrapper — analyze token savings from help-action refactor.

Usage:
    python scripts/analyze_help_savings.py
    python scripts/analyze_help_savings.py --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

for _v in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD",
           "MODUSBI_PROD_USERNAME", "MODUSBI_PROD_PASSWORD"):
    os.environ.setdefault(_v, "stub")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.server import mcp  # noqa: E402
from app.tools.token_metrics import measure_help_savings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze help-action token savings.")
    parser.add_argument("--json", help="Save JSON report")
    parser.add_argument(
        "--tokenizer", default="cl100k_base",
        choices=["cl100k_base", "o200k_base", "approx-ru", "approx-en"],
    )
    args = parser.parse_args()

    r = measure_help_savings(mcp, tokenizer=args.tokenizer)
    print(f"# Help-Action Savings ({r['tokenizer']})\n")
    print(f"  {'Tool':<26} {'Thin':>6} {'Full':>6} {'Saves':>6} {'%':>6}")
    print("  " + "-" * 56)
    for name, d in sorted(r["per_tool"].items(), key=lambda kv: -kv[1]["savings_tokens"]):
        print(f"  {name:<26} {d['thin_tokens']:>6} {d['full_tokens']:>6} "
              f"{d['savings_tokens']:>6} {d['savings_pct']:>5}%")
    t = r["totals"]
    print("  " + "-" * 56)
    print(f"  {'TOTAL':<26} {t['thin']:>6} {t['full']:>6} "
          f"{t['savings']:>6} {t['savings_pct']:>5}%")

    if args.json:
        Path(args.json).write_text(json.dumps(r, ensure_ascii=False, indent=2))
        print(f"\nJSON saved to {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
