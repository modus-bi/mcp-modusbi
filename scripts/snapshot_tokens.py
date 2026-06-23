"""Orchestrator — take full token snapshot and save to docs/token-usage/.

Usage:
    python scripts/snapshot_tokens.py
    python scripts/snapshot_tokens.py --tag v3.1.0
    python scripts/snapshot_tokens.py --out-dir /tmp/out
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

for _v in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD",
           "MODUSBI_PROD_USERNAME", "MODUSBI_PROD_PASSWORD"):
    os.environ.setdefault(_v, "stub")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.server import mcp  # noqa: E402
from app.tools.token_metrics import (  # noqa: E402
    FLOWS, format_client_profiles_markdown, measure_client_profiles,
    measure_surface, measure_flow, measure_help_savings,
)


def build_snapshot(tokenizer: str, tag: str | None) -> dict:
    snapshot: dict = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tag": tag,
        "mcp_version": os.environ.get("MCP_VERSION", "unknown"),
        "tokenizer": tokenizer,
        "surface": measure_surface(mcp, tokenizer=tokenizer),
        "client_profiles": measure_client_profiles(mcp),
        "flows": {},
        "help_savings": measure_help_savings(mcp, tokenizer=tokenizer),
    }
    grand = 0
    for name, steps in FLOWS.items():
        r = measure_flow(name, steps, tokenizer=tokenizer)
        snapshot["flows"][name] = r
        grand += r["total_flow_tokens"]
    snapshot["flows_grand_total"] = grand
    return snapshot


def update_trend_readme(out_dir: Path) -> None:
    """Rebuild docs/token-usage/README.md from all snapshots."""
    snapshots = []
    for p in sorted(out_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            # Only token-surface snapshots (other schema_version=1 artifacts,
            # e.g. ui_meta_cost.json, lack a "surface" block).
            if data.get("schema_version") == 1 and "surface" in data:
                snapshots.append((p, data))
        except Exception:
            continue

    if not snapshots:
        return

    def envelope(s):
        return s["surface"].get("tools_list_envelope", {})

    def sum_of_parts(s):
        return s["surface"].get("total_tools_tokens", 0)

    lines = [
        "# Token Usage — Historical Trend",
        "",
        "Auto-generated from `docs/token-usage/*.json` snapshots.",
        "Updated by `scripts/snapshot_tokens.py`.",
        "",
        "Key metric: **envelope (compact)** — tokens, которые `tools/list` забирает на каждый",
        "запрос LLM-клиента. Sum-of-parts — сумма по инструментам (аналитическая, без JSON-RPC-обёртки).",
        "",
        "## Trend (last 20 snapshots)",
        "",
        "| Дата | MCP | Тег | Envelope (compact) | Sum-of-parts |",
        "|------|-----|-----|------------------:|------------:|",
    ]
    for _, s in snapshots[-20:]:
        date = s["timestamp"][:10]
        env = envelope(s).get("compact_tokens", 0)
        tag = s.get("tag") or ""
        lines.append(
            f"| {date} | `{s.get('mcp_version', '?')}` | {tag} | **{env:,}** | {sum_of_parts(s):,} |"
        )

    # Latest snapshot detail
    _, latest = snapshots[-1]
    env = envelope(latest)
    lines += [
        "",
        f"## Latest Snapshot — {latest['timestamp'][:10]}",
        "",
        f"- **MCP Version:** `{latest.get('mcp_version', '?')}`",
        f"- **Tokenizer:** {latest['tokenizer']}",
        f"- **Tokenizer backend:** `{latest['surface'].get('tokenizer_backend', '?')}`",
        "",
        "### Real cost per request (tools/list envelope)",
        "",
        f"- **Compact JSON:** {env.get('compact_tokens', 0):,} tokens",
        f"- **Indented JSON:** {env.get('indented_tokens', 0):,} tokens",
        "",
        "### Analytical breakdown",
        "",
        f"- Sum-of-parts (per-tool summed): {sum_of_parts(latest):,} tokens",
        "",
        "### Top-10 heaviest tools",
        "",
        "| Tool | Total tokens |",
        "|------|--------------|",
    ]
    top10 = sorted(latest["surface"]["per_tool"].items(),
                   key=lambda kv: -kv[1]["total"])[:10]
    for name, data in top10:
        lines.append(f"| `{name}` | {data['total']:,} |")

    if latest.get("client_profiles"):
        lines += ["", format_client_profiles_markdown(latest["client_profiles"])]

    (out_dir / "README.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot full token metrics.")
    parser.add_argument("--tag", help="Optional tag (e.g. 'v3.1.0')")
    parser.add_argument("--tokenizer", default="cl100k_base",
                        choices=["cl100k_base", "o200k_base", "approx-ru", "approx-en"])
    parser.add_argument("--out-dir", default="docs/token-usage")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot = build_snapshot(args.tokenizer, args.tag)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"{date_str}.json"
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"Snapshot saved: {out_path}")

    update_trend_readme(out_dir)
    print(f"Trend README updated: {out_dir / 'README.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
