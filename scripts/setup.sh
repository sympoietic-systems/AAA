#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – First-Time Setup (macOS / Linux)
# Run this once to install all Python, frontend, and system dependencies.
# Usage: bash scripts/setup.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# Resolve project root (one level above scripts/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}=============================================================${NC}"
echo -e "${CYAN}  AAA – First-Time macOS / Linux Setup${NC}"
echo -e "${CYAN}=============================================================${NC}"
echo ""

# ── 1. Check Python ─────────────────────────────────────────
echo -e "${YELLOW}[1/5] Checking Python 3.11+ ...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[FAIL] python3 not found.${NC}"
    echo -e "  - Ubuntu/Linux: run 'sudo apt install python3 python3-pip'"
    echo -e "  - macOS: run 'brew install python' or download from https://python.org"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "  Found Python ${PY_VERSION}"

PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo -e "${RED}[FAIL] Python 3.11+ required, found ${PY_VERSION}${NC}"
    exit 1
fi
echo -e "${GREEN}  [OK]${NC}"

# ── 2. Install uv ────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Installing uv package manager ...${NC}"
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}[FAIL] uv installation failed. Install manually: curl -LsSf https://astral.sh/uv/install.sh | sh${NC}"
        exit 1
    fi
    echo -e "${GREEN}  [OK] uv installed${NC}"
else
    echo -e "${GREEN}  [OK] uv already installed: $(uv --version)${NC}"
fi

# ── 3. Install Python dependencies ───────────────────────────
echo -e "${YELLOW}[3/5] Installing Python dependencies (uv sync) ...${NC}"
uv sync
echo -e "${GREEN}  [OK]${NC}"

# ── 4. Install Node.js & frontend deps ───────────────────────
echo -e "${YELLOW}[4/5] Setting up frontend ...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "  Node.js not found. Installing via nvm..."
    export NVM_DIR="$HOME/.nvm"
    if [ ! -s "$NVM_DIR/nvm.sh" ]; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
    fi
    [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
    nvm install --lts
    nvm use --lts
fi
echo -e "  Node: $(node --version)"
echo -e "  npm:  $(npm --version)"

cd "$PROJECT_ROOT/frontend"
npm install
cd "$PROJECT_ROOT"
echo -e "${GREEN}  [OK]${NC}"

# ── 5. Create directories & .env check ───────────────────────
echo -e "${YELLOW}[5/5] Preparing runtime directories ...${NC}"
mkdir -p backend/data/backups
mkdir -p backend/data/uploads/research
echo -e "${GREEN}  [OK] data/ directories created${NC}"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}  [!] No .env file found. Copying from .env.example — please edit it!${NC}"
        cp .env.example .env
    else
        echo -e "${RED}  [!] No .env or .env.example found. Create .env manually with required API keys.${NC}"
    fi
else
    echo -e "${GREEN}  [OK] .env exists${NC}"
fi

echo ""
echo -e "${CYAN}=============================================================${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo ""
echo -e "  Start backend:   ${CYAN}bash scripts/run_backend.sh${NC}"
echo -e "  Start frontend:  ${CYAN}bash scripts/run_frontend.sh${NC}"
echo -e "  Start all:       ${CYAN}bash scripts/run_all.sh${NC}"
echo ""
echo -e "  Backend API:     http://127.0.0.1:8499"
echo -e "  Frontend:        http://localhost:5173"
echo -e "${CYAN}=============================================================${NC}"
