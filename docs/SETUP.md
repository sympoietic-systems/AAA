# Setup Guide

## Prerequisites

- **Python 3.11+** — [python.org](https://python.org) or `winget install Python.Python.3.11`
- **Node.js 18+** — [nodejs.org](https://nodejs.org) or `winget install OpenJS.NodeJS.LTS`
- **uv** (Python package manager) — `pip install uv` or `winget install uv`

## Installation

```bash
# Clone (if you haven't already)
git clone <repo-url> aaa
cd aaa

# Python dependencies
uv sync

# Frontend dependencies
cd frontend
npm install
cd ..
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

Start the backend (terminal 1):

```bash
uv run python -m backend.main
# → Uvicorn running on http://127.0.0.1:8000
# → API docs at http://127.0.0.1:8000/docs
```

Start the frontend (terminal 2):

```bash
cd frontend
npm run dev
# → Vite running on http://localhost:5173
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
| `401 Unauthorized` on chat | Check `.env` API key is set and valid |
| `Illegal header value b'Bearer '` | API key is empty — the `${AAA_LLM_API_KEY}` in config.yaml resolves to `""` |
| Embedding download stalls | First run downloads `all-MiniLM-L6-v2` (~90 MB). Once cached, `offline: true` (default) skips HuggingFace entirely on subsequent runs. Set `HF_HUB_ENABLE_HF_TRANSFER=1` for faster first download. |
| Frontend blank page | Run `cd frontend && npm install && npm run dev` |
| `uv` not found | `pip install uv` or see [uv install guide](https://docs.astral.sh/uv/getting-started/installation/) |
