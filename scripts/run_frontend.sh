#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – Run Frontend Server (Dev with HMR or Production Preview)
# Usage:
#   bash scripts/run_frontend.sh dev      # Dev server with HMR (default)
#   bash scripts/run_frontend.sh preview  # Build bundle and serve preview
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Ensure mise and user local bins are in PATH
export PATH="$HOME/.local/share/mise/installs/node/26.8.1/bin:$HOME/.local/share/mise/shims:$HOME/.local/bin:$PATH"

# ── Detect Node.js ──────────────────────────────────────────
detect_node() {
    if command -v node &> /dev/null; then
        return 0
    fi
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        export NVM_DIR="$HOME/.nvm"
        . "$NVM_DIR/nvm.sh" 2>/dev/null || true
        if command -v node &> /dev/null; then return 0; fi
    fi
    for fnm_path in "$HOME/.local/share/fnm" "$HOME/.fnm" "/opt/fnm"; do
        if [ -d "$fnm_path" ]; then
            export PATH="$fnm_path:$PATH"
            eval "$(fnm env --use-on-cd 2>/dev/null || fnm env 2>/dev/null)" 2>/dev/null || true
            if command -v node &> /dev/null; then return 0; fi
        fi
    done
    return 1
}

if ! detect_node; then
    echo "[ERROR] Node.js not found. Run: bash scripts/setup.sh"
    exit 1
fi

cd "$FRONTEND_DIR"

# Install or sync deps if missing
if [ ! -d "node_modules" ] || [ ! -d "node_modules/rehype-sanitize" ]; then
    echo "[INFO] Installing missing frontend dependencies..."
    npm install --no-save || npm install || echo "[WARN] npm install failed; check file permissions in $FRONTEND_DIR"
fi

MODE="${1:-${AAA_FRONTEND_MODE:-dev}}"
PORT="${AAA_FRONTEND_PORT:-5174}"
HOST="${AAA_FRONTEND_HOST:-0.0.0.0}"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AAA Frontend [Mode: $MODE]"
echo "  Listening: http://${HOST}:${PORT}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$MODE" = "preview" ] || [ "$MODE" = "prod" ] || [ "$MODE" = "production" ]; then
    echo "  Building production bundle..."
    npm run build
    exec npx vite preview --host "$HOST" --port "$PORT"
else
    exec npx vite --host "$HOST" --port "$PORT"
fi
