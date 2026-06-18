#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – Launch All Services (Ubuntu)
# Starts backend + frontend in background.
# Usage: bash scripts/run_all.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${CYAN}Shutting down services...${NC}"
    if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
    fi
    if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
    fi
    wait 2>/dev/null || true
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${CYAN}=============================================================${NC}"
echo -e "${CYAN}  AAA – Starting All Services${NC}"
echo -e "${CYAN}=============================================================${NC}"
echo ""

# ── Start Backend ────────────────────────────────────────────
echo -e "[1/2] Starting Backend..."
bash "$SCRIPT_DIR/run_backend.sh" &
BACKEND_PID=$!
echo -e "      Backend PID: $BACKEND_PID"

# ── Start Frontend ───────────────────────────────────────────
echo -e "[2/2] Starting Frontend..."
bash "$SCRIPT_DIR/run_frontend.sh" &
FRONTEND_PID=$!
echo -e "      Frontend PID: $FRONTEND_PID"

echo ""
echo -e "${CYAN}=============================================================${NC}"
echo -e "${GREEN}  All services launched!${NC}"
echo -e "  Backend API:  http://127.0.0.1:8000"
echo -e "  Frontend:     http://localhost:5173"
echo -e "  Press Ctrl+C to stop all services."
echo -e "${CYAN}=============================================================${NC}"

# Wait for both processes
wait
