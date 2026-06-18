# Setup Guide

## Prerequisites

- **Python 3.11+** — [python.org](https://python.org) or `sudo apt install python3` (Ubuntu)
  - Python 3.14 is currently unsupported due to `crawl4ai` / `lxml` wheel incompatibility. The `.python-version` file pins 3.13 for `uv`.
- **Node.js 18+** — [nodejs.org](https://nodejs.org) or `nvm install --lts`
- **uv** (Python package manager) — installed automatically by `setup.sh`; see [uv install guide](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

### Automated (Ubuntu — recommended)

```bash
# Clone and run the one-shot setup script
git clone <repo-url> aaa
cd aaa
bash scripts/setup.sh
```

This installs all dependencies (`uv`, Python packages, Node.js + npm packages) and creates required data directories. Safe to re-run.

### Manual

```bash
git clone <repo-url> aaa
cd aaa

# Python dependencies
uv sync

# Frontend dependencies
cd frontend
npm install
cd ..

# Create runtime directories
mkdir -p backend/data/backups backend/data/uploads/research
```

## API Key Setup

Copy the example env file and fill in your keys:

```bash
cp .env.example .env
```

### Option A — OpenRouter (recommended, multi-provider)

```bash
# .env
AAA_LLM_PROVIDER=openrouter
AAA_LLM_API_KEY=sk-or-v1-your-key-here
```

Get a key at [openrouter.ai/keys](https://openrouter.ai/keys).

### Option B — DeepSeek Direct

```bash
# .env
AAA_LLM_PROVIDER=deepseek
AAA_DEEPSEEK_API_KEY=sk-your-deepseek-key
```

Get a key at [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys).

### Optional: Thinking Mode

DeepSeek-v4-pro/v4-flash supports chain-of-thought reasoning:

```bash
AAA_LLM_THINKING=true
AAA_LLM_REASONING_EFFORT=high   # high | max
```

When enabled, the UI shows a collapsible `▶ thinking` section under responses.

## Run

### Database & Migrations

The backend uses **SQLite** (`backend/data/aaa.db`). On first startup, the database is auto-created and all migrations are applied automatically when `AAA_RUN_MIGRATIONS=true` is set. This is enabled by default in the startup scripts below.

Migration files are in `backend/storage/migrations/` (custom runner — not Alembic). Each migration is idempotent and tracked in the `_migrations` table.

### 1. Seed Foundational Beliefs & Skills (one-time setup)

Before first run, seed Symbia's core philosophical commitments and procedural skills into the database:

```bash
# Seed beliefs
uv run python backend/scripts/seed_beliefs.py
# → Seeds 8 foundational beliefs (glitch-as-voice, anti-hci, etc.)
# → Safe to run multiple times — skips if authored beliefs already exist
# → Use --force to re-seed alongside existing beliefs

# Seed skills
uv run python backend/scripts/seed_skills.py
# → Seeds baseline dispositions and on-demand capabilities
# → Safe to run multiple times — skips if skills already exist by default
# → Use --force to overwrite/reset database skills to seed defaults
```

Beliefs are defined in `backend/personality/seed_beliefs.yaml` and skills in `backend/personality/seed_skills.yaml`. Format:

```yaml
beliefs:
  - id: "belief-label"
    statement: "The belief statement text."
    category: "foundational"   # foundational | ontological | methodological
    confidence: 0.90           # 0.0–1.0
```

Categories map to ontological mass: foundational=1.5, ontological=1.2, methodological=1.0.

After seeding, beliefs live in the database and evolve through the belief lifecycle. They are **not** injected from the YAML into system prompts — the attractor window handles that dynamically.

### 2. Start Services

**Option A — Scripts (development)**

```bash
# Start both backend + frontend (Ctrl+C to stop)
bash scripts/run_all.sh

# Or start individually:
bash scripts/run_backend.sh    # → http://127.0.0.1:8000 (API docs at /docs)
bash scripts/run_frontend.sh   # → http://localhost:5173
```

**Option B — PM2 (production / server deployment, recommended for Ubuntu)**

```bash
# One-time PM2 install
npm install -g pm2

# Start both services
bash scripts/pm2.sh start

# Auto-restart on server reboot
pm2 startup
pm2 save

# Monitor
pm2 monit         # real-time dashboard
pm2 logs          # all logs
pm2 logs aaa-backend   # backend only
pm2 logs aaa-frontend  # frontend only

# Restart individual service without touching the other
pm2 restart aaa-backend
pm2 restart aaa-frontend
```

Each service runs as a separate PM2 app for independent monitoring, logging, and restart control. Configuration is in `ecosystem.config.cjs`.

**Option C — Raw (manual)**

```bash
# Terminal 1 — Backend
uv run python -m backend.main

# Terminal 2 — Frontend
cd frontend && npm run dev
```

The frontend proxies `/api` requests to the backend automatically.

## Verify

Open `http://localhost:5173`. You should see:

```
> symbia
────────────────────────────────
Symbia v0.1.0 — type a message below.
> _                              ← your prompt
```

Type a message and press Enter. The agent should respond within a few seconds.

## Verify Endpoints (optional)

```bash
# Health check
curl http://127.0.0.1:8000/api/health

# Agent identity (name from identity.yaml)
curl http://127.0.0.1:8000/api/agent

# Chat
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello"}'

# History
curl http://127.0.0.1:8000/api/history?limit=10

# Skills / Pipeline
curl http://127.0.0.1:8000/api/skills
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'backend'` | Run from project root: `cd aaa && uv run python -m backend.main` |
| `uv` not found | `pip install uv` or run `bash scripts/setup.sh` |
| `Node.js` not found | Install via nvm: `curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh \| bash` then run `bash scripts/setup.sh` |
| `401 Unauthorized` on chat | Check `.env` API key is set and valid |
| `Illegal header value b'Bearer '` | API key is empty — the `${AAA_LLM_API_KEY}` in config.yaml resolves to `""` |
| Embedding download stalls | First run downloads `all-MiniLM-L6-v2` (~90 MB). Once cached, `offline: true` (default) skips HuggingFace entirely on subsequent runs. Set `HF_HUB_ENABLE_HF_TRANSFER=1` for faster first download. |
| Frontend blank page | Run `cd frontend && npm install && npm run dev` |
| Database errors / missing tables | Ensure `AAA_RUN_MIGRATIONS=true` is set (enabled by default in all startup scripts). To reset: delete `backend/data/aaa.db` and restart. |
| PM2: command not found | `npm install -g pm2` then ensure `~/.npm-global/bin` or npm's global bin is on `PATH` |
| PM2: service crashes on startup | Check logs: `pm2 logs aaa-backend --lines 50`. Ensure `.env` has valid API keys and `uv sync` has been run. |
