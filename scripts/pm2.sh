#!/bin/bash
# ─────────────────────────────────────────────────────────────
# AAA – PM2 Management Helper
# Usage:
#   bash scripts/pm2.sh start          # start both apps
#   bash scripts/pm2.sh stop           # stop both apps
#   bash scripts/pm2.sh restart        # restart both apps
#   bash scripts/pm2.sh status         # show status
#   bash scripts/pm2.sh logs           # show live logs
#   bash scripts/pm2.sh logs-backend   # backend logs only
#   bash scripts/pm2.sh logs-frontend  # frontend logs only
#   bash scripts/pm2.sh delete         # remove from PM2
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="$PROJECT_ROOT/ecosystem.config.cjs"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

# Ensure PM2 is available
if ! command -v pm2 &> /dev/null; then
    echo "[ERROR] pm2 not found. Install with: npm install -g pm2"
    exit 1
fi

if [ ! -f "$CONFIG" ]; then
    echo "[ERROR] ecosystem.config.cjs not found at $CONFIG"
    exit 1
fi

CMD="${1:-status}"

case "$CMD" in
    start)
        echo -e "${CYAN}Starting AAA services via PM2...${NC}"
        pm2 start "$CONFIG"
        pm2 save
        echo ""
        echo -e "${GREEN}Both services started.${NC}"
        echo "  Backend:  http://127.0.0.1:8499"
        echo "  Frontend: http://localhost:5173"
        echo "  Monitor:  pm2 monit"
        pm2 status
        ;;
    stop)
        pm2 stop "$CONFIG"
        pm2 save
        echo -e "${GREEN}Services stopped.${NC}"
        ;;
    restart)
        pm2 restart "$CONFIG"
        echo -e "${GREEN}Services restarted.${NC}"
        ;;
    status)
        pm2 status
        ;;
    logs)
        pm2 logs --timestamp
        ;;
    logs-backend)
        pm2 logs aaa-backend --timestamp
        ;;
    logs-frontend)
        pm2 logs aaa-frontend --timestamp
        ;;
    delete)
        pm2 delete "$CONFIG"
        pm2 save
        echo -e "${GREEN}Services removed from PM2.${NC}"
        ;;
    *)
        echo "Usage: bash scripts/pm2.sh {start|stop|restart|status|logs|logs-backend|logs-frontend|delete}"
        exit 1
        ;;
esac
