#!/usr/bin/env bash
# Run MCP-Scorecard (https://github.com/aak204/MCP-Scorecard) on the local server.
# Usage:
#   bash scripts/run_scorecard.sh              # run with defaults, fail if score < 90
#   MIN_SCORE=80 bash scripts/run_scorecard.sh # override threshold
#   OUT_DIR=/tmp/sc bash scripts/run_scorecard.sh
set -euo pipefail

SCORECARD_DIR="${SCORECARD_DIR:-$HOME/.local/mcp-scorecard}"
SCORECARD_REF="${SCORECARD_REF:-v1.0.0}"  # pin, can be overridden
MIN_SCORE="${MIN_SCORE:-90}"
OUT_DIR="${OUT_DIR:-./.scorecard}"
PY="${PY:-python3}"

mkdir -p "$OUT_DIR"

if [ ! -d "$SCORECARD_DIR" ]; then
    echo "Installing MCP-Scorecard ($SCORECARD_REF) into $SCORECARD_DIR..."
    git clone --depth 1 --branch "$SCORECARD_REF" \
        https://github.com/aak204/MCP-Scorecard.git "$SCORECARD_DIR"
    (cd "$SCORECARD_DIR" && "$PY" -m venv .venv && .venv/bin/pip install -q -e .)
fi

# Explicit version check — warn if deviating from pinned ref.
ACTUAL_REF="$(cd "$SCORECARD_DIR" && git describe --tags --always 2>/dev/null || echo 'unknown')"
if [ "$ACTUAL_REF" != "$SCORECARD_REF" ]; then
    echo "WARN: scorecard at $SCORECARD_DIR is $ACTUAL_REF, expected $SCORECARD_REF" >&2
fi

SCORECARD_BIN="$SCORECARD_DIR/.venv/bin/mcp-scorecard"

# Stub credentials — readonly mode doesn't authenticate, but env vars must resolve.
export MODUSBI_URL="${MODUSBI_URL:-https://example.com}"
export MODUSBI_USERNAME="${MODUSBI_USERNAME:-stub}"
export MODUSBI_PASSWORD="${MODUSBI_PASSWORD:-stub}"
export MODUSBI_PROD_USERNAME="${MODUSBI_PROD_USERNAME:-stub}"
export MODUSBI_PROD_PASSWORD="${MODUSBI_PROD_PASSWORD:-stub}"

# Run in readonly mode — scorecard scans tool surface, no real API calls.
"$SCORECARD_BIN" scan \
    --min-score "$MIN_SCORE" \
    --json-out "$OUT_DIR/scorecard.json" \
    --sarif "$OUT_DIR/scorecard.sarif" \
    --cmd "$PY" -m app.server --readonly

echo ""
echo "Scorecard artifacts:"
echo "  $OUT_DIR/scorecard.json"
echo "  $OUT_DIR/scorecard.sarif"
