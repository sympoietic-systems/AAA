# AAA — Autopoietic Agentic Assemblage

A closed-loop, self-regulating conversational AI agent. Modular pipeline,
local embeddings, persistent memory, and a terminal-style dark UI.

```
  ┌───────────────────────────────────────────────────┐
  │                    React UI                        │
  │              (terminal dark, markdown)             │
  └──────────────────────┬────────────────────────────┘
                         │  /api/chat
                         ▼
  ┌───────────────────────────────────────────────────┐
  │                 FastAPI Backend                    │
  │  ┌──────────┐  ┌───────────────┐  ┌────────────┐  │
  │  │ embedder │→│context_collect├→│ llm_client  │  │
  │  └──────────┘  └───────────────┘  └────────────┘  │
  │                      │                            │
  │              ┌───────▼────────┐                    │
  │              │  SQLite (WAL)  │                    │
  │              └────────────────┘                    │
  └───────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install dependencies
uv sync
cd frontend && npm install && cd ..

# 2. Set your API key
cp .env.example .env
# edit .env → set AAA_LLM_API_KEY (OpenRouter) or AAA_DEEPSEEK_API_KEY

# 3. Start backend (terminal 1)
uv run python -m backend.main

# 4. Start frontend (terminal 2)
cd frontend && npm run dev

# 5. Open http://localhost:5173
```

## Features

- **Agent-agnostic LLM** — OpenRouter, DeepSeek, or any OpenAI-compatible API
- **Local embeddings** — sentence-transformers, hot-swappable model
- **Persistent memory** — every message stored as raw text + vector
- **Thinking mode** — collapsible chain-of-thought for DeepSeek-v4
- **Modular pipeline** — reorder/extend modules via YAML config
- **Error persistence** — all failures logged with full traceback
- **Terminal dark UI** — monospace, markdown rendering, no bloat

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, httpx |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Database | SQLite (WAL mode) |
| Frontend | React 18, Vite, Tailwind CSS |
| Markdown | react-markdown + remark-gfm |
| Package mgmt | uv (Python), npm (JS) |

## Documentation

- [Philosophy](docs/PHILOSOPHY.md) — conceptual foundations
- [Setup Guide](docs/SETUP.md) — full installation walkthrough
- [Configuration Reference](docs/CONFIG.md) — all config.yaml + env vars
- [Plugin System](docs/PLUGINS.md) — how to build custom modules
- [Architecture](docs/ARCHITECTURE.md) — pipeline, data flow, design rationale
- [Technical Design Document](docs/TDD.md) — system specification
- [Implementation Roadmap](docs/Implementation.md) — Phase 1–4 plan

## Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| **1** | Embedding, DB, LLM API, chat UI | Done |
| **2** | Homeostatic Regulator (entropy) | Planned |
| **3** | Rhizomatic Memory (vector graph) | Planned |
| **4** | Foundational Memory (belief graph) | Planned |
