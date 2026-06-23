#!/usr/bin/env bash
# CI wrapper — take snapshot and check it against docs/token-usage/budget.yml.
# Use in pre-merge / CI jobs. Returns 3 on budget violation.
set -euo pipefail

PY="${PY:-python3}"
OUT_DIR="${OUT_DIR:-docs/token-usage}"
BUDGET="${BUDGET:-docs/token-usage/budget.yml}"
TAG="${TAG:-}"

SNAP_ARGS=(--out-dir "$OUT_DIR")
[ -n "$TAG" ] && SNAP_ARGS+=(--tag "$TAG")

"$PY" scripts/snapshot_tokens.py "${SNAP_ARGS[@]}"
"$PY" scripts/check_token_budget.py --budget "$BUDGET" --snapshots "$OUT_DIR"
