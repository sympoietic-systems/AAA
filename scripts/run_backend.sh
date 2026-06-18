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

# Ensure uv is on PATH (common install locations)
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if ! command -v uv &> /dev/null; then
    echo "[ERROR] uv not found. Run: bash scripts/setup.sh"
    exit 1
fi

# Ensure data directory exists
mkdir -p backend/data/backups
mkdir -p backend/data/uploads/research

# Enable automatic migrations (creates DB + applies all 39 migrations on first run)
export AAA_RUN_MIGRATIONS=true

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AAA Backend starting..."
echo "  Database: backend/data/aaa.db"
echo "  Migrations: $([ "${AAA_RUN_MIGRATIONS}" = "true" ] && echo "ENABLED" || echo "DISABLED")"
echo "  API: http://127.0.0.1:8499"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

uv run python -m backend.main
