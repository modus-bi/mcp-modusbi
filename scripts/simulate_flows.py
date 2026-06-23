"""CLI wrapper — simulate common tool-call flows (offline, fixture-based).

Usage:
    python scripts/simulate_flows.py
    python scripts/simulate_flows.py --json out.json
    python scripts/simulate_flows.py --tokenizer o200k_base
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

from app.tools.token_metrics import FLOWS, measure_flow  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate token cost of common tool-call flows.")
    parser.add_argument("--json", help="Save JSON report")
    parser.add_argument(
        "--tokenizer", default="cl100k_base",
        choices=["cl100k_base", "o200k_base", "approx-ru", "approx-en"],
    )
    args = parser.parse_args()

    print(f"Flow simulation ({args.tokenizer}):\n")
    print(f"  {'Flow':<24} {'Steps':>5} {'Req':>6} {'Resp':>7} {'Total':>7}")
    print("  " + "-" * 53)
    report: dict = {"tokenizer": args.tokenizer, "flows": {}}
    grand = 0
    for name, steps in FLOWS.items():
        r = measure_flow(name, steps, tokenizer=args.tokenizer)
        report["flows"][name] = r
        grand += r["total_flow_tokens"]
        print(f"  {name:<24} {r['step_count']:>5} "
              f"{r['total_request_tokens']:>6} "
              f"{r['total_response_tokens']:>7} "
              f"{r['total_flow_tokens']:>7}")
    print("  " + "-" * 53)
    print(f"  {'TOTAL':<24} {'':>5} {'':>6} {'':>7} {grand:>7}")
    report["grand_total"] = grand

    if args.json:
        Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(f"\nJSON saved to {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
