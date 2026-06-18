#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – Run MCP Server (for IDE integration)
# Connects to the online backend at aaa.sokaris.link by default.
# Override with: AAA_API_BASE=http://localhost:8499/api
# Usage: bash scripts/run_mcp.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv not found. Run: bash scripts/setup.sh"
    exit 1
fi

# Point to online instance by default — override for local dev
: "${AAA_API_BASE:=http://aaa.sokaris.link/api}"

# If password is set, pass it so MCP can authenticate
if [ -n "${AAA_PASSWORD:-}" ]; then
    echo "[INFO] AAA_PASSWORD detected — MCP requests will include auth"
fi

export AAA_API_BASE
uv run python backend/mcp_server.py
