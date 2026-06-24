# Setup Guide

> [!TIP]
> Are you a non-technical user or looking for the fastest path to get the agent up and running locally? 
> Read the [Easy Quickstart Guide](QUICKSTART_NON_TECHNICAL.md) first!

## Prerequisites

- **Python 3.11+** — [python.org](https://python.org) or `sudo apt install python3` (Ubuntu)
  - Python 3.14 is currently unsupported due to `crawl4ai` / `lxml` wheel incompatibility. The `.python-version` file pins 3.13 for `uv`.
- **Node.js 18+** — [nodejs.org](https://nodejs.org) or `nvm install --lts`
- **uv** (Python package manager) — installed automatically by setup scripts (`setup.sh` / `setup.bat`); see [uv install guide](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

### Automated

This installs all dependencies (`uv`, Python packages, Node.js + npm packages), configures the virtual environment, copies the configuration template (`.env`), and creates required data directories. Safe to re-run.

*   **macOS / Linux**:
    ```bash
    git clone <repo-url> aaa
    cd aaa
    bash scripts/setup.sh
    ```
*   **Windows**:
    ```powershell
    git clone <repo-url> aaa
    cd aaa
    .\scripts\setup.bat
    ```
    *(Or double-click `setup.bat` inside the `scripts` folder in Windows File Explorer)*

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
AAA_LLM_API_KEY=sk-or-v1-your-key-here
```
*   **Models**: Supports routing to all models on OpenRouter using the `openrouter_router/<model_id>` prefix in `AAA_LLM_MODELS`.
*   **Get Key**: [openrouter.ai/keys](https://openrouter.ai/keys).

### Option B — DeepSeek Direct

```bash
# .env
AAA_DEEPSEEK_API_KEY=sk-your-deepseek-key
```
*   **Models**: Supports routing directly to DeepSeek models (e.g. `deepseek-v4-pro`, `deepseek-v4-flash`) using the `deepseek_router/<model_id>` prefix.
*   **Get Key**: [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys).

### Option C — Google Gemini Direct

```bash
# .env
AAA_GOOGLE_API_KEY=AIzaSyYourGoogleStudioKeyHere
```
*   **Models**: Supports routing directly to Google Gemini models (e.g. `gemini-3.5-pro`, `gemini-3.1-pro`, `gemini-3.5-flash`, `gemini-3.1-flash`) using the `google_router/<model_id>` prefix.
*   **Get Key**: [aistudio.google.com](https://aistudio.google.com/).

### Multi-Provider Fallback & Router Prefixes

The system has an intelligent multi-provider pool with automatic fallback. If a model is rate-limited or fails, it falls back to the next model in your list. 

Define your prioritized models in the `AAA_LLM_MODELS` list (comma-separated), using the appropriate prefix for each model:

*   `google_router/` — Routes natively to Google's API (requires `AAA_GOOGLE_API_KEY`)
*   `deepseek_router/` — Routes natively to DeepSeek's API (requires `AAA_DEEPSEEK_API_KEY`)
*   `openrouter_router/` — Routes to OpenRouter (requires `AAA_LLM_API_KEY`)

**Example list configuration:**
```env
AAA_LLM_MODELS=google_router/gemini-3.5-pro,google_router/gemini-3.5-flash,deepseek_router/deepseek-v4-pro,openrouter_router/google/gemma-2-27b-it:free
```

### Optional: Thinking Mode

DeepSeek-v4-pro/v4-flash (and other reasoning models) support chain-of-thought:

```bash
AAA_LLM_THINKING=true
AAA_LLM_REASONING_EFFORT=high   # high | max
```

When enabled, the UI shows a collapsible `▶ thinking` section under responses.

## Agent Customization

Creating or customizing an agent involves defining their core identity, baseline beliefs, procedural skills, dynamic personality commitments/expertise, and task-specific prompts. 

All customization settings are managed via human-readable YAML configurations. For complete details and schema references, please read the [Agent Personality Customization Guide](CUSTOMIZE_PERSONALITY.md).

---

## Run

### Database & Migrations

The backend uses **SQLite** (`backend/data/aaa.db`). On first startup, the database is auto-created and all migrations are applied automatically when `AAA_RUN_MIGRATIONS=true` is set. This is enabled by default in the startup scripts below.

Migration files are in `backend/storage/migrations/` (custom runner — not Alembic). Each migration is idempotent and tracked in the `_migrations` table.

### 1. Database Seeding & Ingestion (one-time setup)

Before first run, you must check your configuration, run database migrations, and ingest the agent's personality files, baseline commitments, and initial skill configurations into the database.

> [!IMPORTANT]
> **Customizing the agent before seeding:**
> Seeding parses the YAML files in `config/personality/` (such as `seed_personality.yaml`, `seed_beliefs.yaml`, and `seed_skills.yaml`) and writes them directly to the database. If you wish to change the agent's default name, core commitments, baseline beliefs, or skills, modify those files **before** running the initialization script below. Refer to the [Agent Personality Customization Guide](CUSTOMIZE_PERSONALITY.md) for full instructions.

#### Recommended: Unified Agent Initialization Script
```bash
uv run python backend/scripts/initialize_agent.py
```
* **What it does**:
  1. **Validates Environment**: Checks that `.env` is present and contains valid (non-placeholder) API keys for at least one configured LLM provider.
  2. **Initializes Database**: Automatically creates the database (`data/aaa.db`) and runs all pending migrations.
  3. **Seeds Beliefs**: Loads foundational beliefs from `config/personality/seed_beliefs.yaml`.
  4. **Seeds Skills**: Loads procedural skills from `config/personality/seed_skills.yaml` (with structural properties) and creates belief bridges.
  5. **Seeds Dynamic Personality**: Seeds commitments, expertise nodes, and trait attractors from `config/personality/seed_personality.yaml`.
* **Flags**:
  * `--force`: Clears the database and runs a clean, complete re-seeding of all tables.
  * `--db <path>`: Specifies a custom database path (defaults to value in configuration).
  * `--ignore-env`: Bypasses the environment check (useful for offline seeding or development).

---

### Vector Management & Maintenance Utilities

To maintain vector integrity, the system provides utility scripts to validate, repair, and recalculate 16-dimensional signature vectors for skills and beliefs:

#### A. Local Vector Repair
```bash
uv run python backend/scripts/repair_vectors.py
```
* **Use Case**: Run this if database vectors become corrupt, empty, or incorrectly formatted (e.g. list formats in skill nodes instead of required schema dictionaries `{v16d: [...], v384d: []}`).
* **Mechanism**: Performs local LexiconScorer validation. If a node is missing its vector or is incorrectly formatted, it recalculates the 16D vector locally using `LexiconScorer` and updates the database row.

#### B. High-Fidelity LLM Vector Recalculation
```bash
uv run python backend/scripts/recalculate_autopoietic_vectors.py
```
* **Use Case**: Run this to upgrade the quality of seeded vectors to use full LLM-based scoring.
* **Mechanism**: Runs an asynchronous loop that reads every belief and skill in the database and recalculates its 16D structural vector using the configured `structural_llm` model pool.
* **Requirements**: Requires a valid LLM provider API key to be set in `.env` for the structural scorer pool. If a provider is not configured, it will fall back to empirical/lexicon scoring.

---

### 2. Start Services

**Option A — Scripts (development)**

*   **macOS / Linux**:
    ```bash
    # Start both backend + frontend (Ctrl+C to stop)
    bash scripts/run_all.sh

    # Or start individually:
    bash scripts/run_backend.sh    # → http://127.0.0.1:8499 (API docs at /docs)
    bash scripts/run_frontend.sh   # → http://localhost:5173
    ```

*   **Windows**:
    ```powershell
    # Start both backend + frontend (Ctrl+C to stop)
    .\scripts\run_all.bat

    # Or start individually:
    .\scripts\run_backend.bat
    .\scripts\run_frontend.bat
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
> agent-name
────────────────────────────────
AgentName v0.1.0 — type a message below.
> _                              ← your prompt
```

Type a message and press Enter. The agent should respond within a few seconds.

## Verify Endpoints (optional)

```bash
# Health check
curl http://127.0.0.1:8499/api/health

# Agent identity (name from identity.yaml)
curl http://127.0.0.1:8499/api/agent

# Chat
curl -X POST http://127.0.0.1:8499/api/chat \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello"}'

# History
curl http://127.0.0.1:8499/api/history?limit=10

# Skills / Pipeline
curl http://127.0.0.1:8499/api/skills
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
| Terminal freezes / Website hangs on Windows (waiting for Enter key) | Windows Command Prompt QuickEdit Mode can suspend console execution when you click inside the terminal window. Press **Enter** or **Esc** inside the terminal to resume it. We programmatically disable QuickEdit at startup now, but you can also disable it permanently by right-clicking the terminal title bar -> **Defaults** -> uncheck **QuickEdit Mode**. |

