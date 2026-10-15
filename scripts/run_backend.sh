#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – Run Backend Server (Ubuntu)
# Handles all database migrations automatically.
# Usage: bash scripts/run_backend.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure uv is on PATH (common install locations + mise shims)
export PATH="$HOME/.local/share/mise/shims:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv not found. Run: bash scripts/setup.sh"
    exit 1
fi

# Ensure data directory exists
mkdir -p backend/data/backups
mkdir -p backend/data/uploads/research

# Enable automatic migrations (creates DB + applies all migrations on first run)
export AAA_RUN_MIGRATIONS=true

HOST="${AAA_SERVER_HOST:-0.0.0.0}"
PORT="${AAA_SERVER_PORT:-8499}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AAA Backend starting..."
echo "  Database: backend/data/aaa.db"
echo "  Migrations: $([ "${AAA_RUN_MIGRATIONS}" = "true" ] && echo "ENABLED" || echo "DISABLED")"
echo "  API: http://${HOST}:${PORT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

uv run python -m backend.main
