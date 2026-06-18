#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – Run Frontend Dev Server (Ubuntu)
# Usage: bash scripts/run_frontend.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# ── Detect Node.js ──────────────────────────────────────────
# Try: direct node, nvm, fnm (in that order)
detect_node() {
    if command -v node &> /dev/null; then
        return 0
    fi

    # nvm
    if [ -s "$HOME/.nvm/nvm.sh" ]; then
        export NVM_DIR="$HOME/.nvm"
        . "$NVM_DIR/nvm.sh" 2>/dev/null || true
        if command -v node &> /dev/null; then
            return 0
        fi
    fi

    # fnm (common locations)
    for fnm_path in "$HOME/.local/share/fnm" "$HOME/.fnm" "/opt/fnm"; do
        if [ -d "$fnm_path" ]; then
            export PATH="$fnm_path:$PATH"
            eval "$(fnm env --use-on-cd 2>/dev/null || fnm env 2>/dev/null)" 2>/dev/null || true
            if command -v node &> /dev/null; then
                return 0
            fi
        fi
    done
    return 1
}

if ! detect_node; then
    echo "[ERROR] Node.js not found. Install via nvm or fnm, then run: bash scripts/setup.sh"
    echo "  Quick install: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash"
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if node_modules exist
if [ ! -d "node_modules" ]; then
    echo "[INFO] node_modules not found, running npm install..."
    npm install
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AAA Frontend starting..."
echo "  Local:   http://localhost:5173"
echo "  Network: http://0.0.0.0:5173"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

npm run dev -- --host
