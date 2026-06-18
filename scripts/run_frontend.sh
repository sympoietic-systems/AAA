#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – Build & Serve Frontend (production, no HMR)
# Usage: bash scripts/run_frontend.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

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

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "[INFO] Installing frontend dependencies..."
    npm install
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AAA Frontend — building production bundle..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
npm run build

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AAA Frontend — serving on http://0.0.0.0:5173"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
npx vite preview --host --port 5173
