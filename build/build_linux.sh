#!/usr/bin/env bash
# Build ModusBI MCP Server — Linux binary.
# Thin wrapper around build.py (single source of build logic + versioned layout:
# dist/<version>/<os>-<arch>/modusbi-mcp-server + .sha256).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec python3 build.py "$@"
