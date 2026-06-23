"""CLI wrapper for app.tools.token_metrics.measure_surface.

Usage:
    python scripts/measure_tokens.py                       # markdown to stdout
    python scripts/measure_tokens.py --json out.json       # save JSON
    python scripts/measure_tokens.py --tokenizer o200k_base
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Stub portal env vars so server module imports cleanly.
for _v in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD",
           "MODUSBI_PROD_USERNAME", "MODUSBI_PROD_PASSWORD"):
    os.environ.setdefault(_v, "stub")

# Make repo importable when run as a plain script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.server import mcp  # noqa: E402
from app.tools.token_metrics import (  # noqa: E402
    format_client_profiles_markdown,
    format_surface_markdown,
    measure_client_profiles,
    measure_surface,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure token cost of the MCP tool surface.")
    parser.add_argument("--json", help="Save full JSON report to this path")
    parser.add_argument(
        "--tokenizer", default="cl100k_base",
        choices=["cl100k_base", "o200k_base", "approx-ru", "approx-en"],
    )
    parser.add_argument(
        "--profiles",
        action="store_true",
        help="Also print Anthropic/OpenAI/rest tool-set profile measurements.",
    )
    args = parser.parse_args()

    report = measure_surface(mcp, tokenizer=args.tokenizer)
    print(format_surface_markdown(report))

    profiles = None
    if args.profiles:
        profiles = measure_client_profiles(mcp)
        print()
        print(format_client_profiles_markdown(profiles))

    if args.json:
        payload = report
        if profiles is not None:
            payload = {"surface": report, "client_profiles": profiles}
        Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2)
        )
        print(f"\nJSON saved to {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
