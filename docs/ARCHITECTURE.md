# Architecture

## High-Level Design

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Frontend                             │
│  ChatView  ←→  MessageBubble (markdown)  ←→  InputBar (> prompt) │
│  SidePanel (pipeline/skills)                                      │
│       │  useChat hook  │  api/client.ts                           │
└───────┼────────────────┼─────────────────────────────────────────┘
        │                │  HTTP (Vite proxy)
        ▼                ▼
┌───────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (main.py)                      │
│                                                                    │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │ Embedder     │  │ ContextCollector │  │ PromptAssemb  │  │ LLMClient          │  │
│  │ Module       │  │ Module           │  │ Module        │  │ Module             │  │
│  │              │  │                  │  │               │  │                    │  │
│  │ embed_text() │  │ get_recent(N)    │  │ identity.yaml │  │ generate(msgs)     │  │
│  │ → BLOB       │  │ → messages[]     │  │ + skills → sys│  │ → {content,think}  │  │
│  └──────┬───────┘  └────────┬─────────┘  └───────┬───────┘  └─────────┬──────────┘  │
│         │                   │                     │                    │             │
│         └───────────────────┼─────────────────────┼────────────────────┘             │
│                             │                     │                                  │
│                    ┌────────▼─────────────────────▼─────────┐                       │
│                    │         Personality (identity.yaml)     │                       │
│                    └────────────────────────────────────────┘                       │
│                             │                                     │
│                    ┌────────▼────────┐                            │
│                    │  SQLite (WAL)    │                            │
│                    │  ┌────────────┐  │                            │
│                    │  │conversation │  │                            │
│                    │  │    _log     │  │                            │
│                    │  ├────────────┤  │                            │
│                    │  │ error_log   │  │                            │
│                    │  └────────────┘  │                            │
│                    └─────────────────┘                            │
└───────────────────────────────────────────────────────────────────┘
```

## Data Flow (Chat Request)

```
POST /api/chat {"content": "What is life?"}
  │
  ▼
ProcessingPipeline.run(initial_payload)
  │
  ├─► embedder.process(payload)
  │     payload["embedding"] = encode("What is life?").tobytes()
  │     payload["embedding_model"] = "all-MiniLM-L6-v2"
  │     payload["embedding_dim"] = 384
  │
  ├─► context_collector.process(payload)
  │     recent = message_repo.get_recent(limit=20)
  │     payload["messages"] = [
  │       {"role": "user", "content": "previous msg"},
  │       {"role": "assistant", "content": "previous reply"},
  │       {"role": "user", "content": "What is life?"},
  │     ]
  │
  ├─► prompt_assembler.process(payload)
  │     identity = load identity.yaml
  │     skills_desc = registry.describe_skills()
  │     system_msg = compose(identity + skills)
  │     payload["messages"].insert(0, {"role": "system", "content": system_msg})
  │
  ├─► llm_client.process(payload)
  │     result = provider.generate(messages, temperature=0.7, ...)
  │     payload["response"] = result["content"]
  │     payload["thinking"] = result["thinking"]  // if thinking mode
  │
  ▼
  route (routes.py)
  ├─ message_repo.insert("human", content, embedding, agent_id="Symbia", ...)
  ├─ message_repo.insert("apparatus", response, thinking, embedding, agent_id="Symbia", ...)
  └─ return ChatResponse {id, content, thinking, ...}
```

## Database Schema

### `conversation_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `timestamp` | DATETIME | Default CURRENT_TIMESTAMP |
| `agent_id` | TEXT | Agent identity from `identity.yaml` (e.g., `"Symbia"`) — multi-agent support |
| `speaker` | TEXT | `human` or `apparatus` |
| `content` | TEXT | Raw message text (re-embeddable) |
| `thinking` | TEXT | Chain-of-thought reasoning (nullable) |
| `embedding` | BLOB | float32 vector, 384 × 4 = 1536 bytes |
| `embedding_model` | TEXT | `all-MiniLM-L6-v2` (tracked for migration) |
| `embedding_dim` | INTEGER | 384 (validates BLOB size) |

### `error_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `timestamp` | DATETIME | Default CURRENT_TIMESTAMP |
| `module` | TEXT | `embedder`, `llm_client`, `api`, etc. |
| `error_type` | TEXT | Exception class name |
| `error_message` | TEXT | Exception message |
| `traceback` | TEXT | Full traceback |
| `context` | TEXT | JSON: what was being processed |

## Module System

### ModuleRegistry / SkillRegistry

Lazy-initialized registry mapping names to module factories. `SkillRegistry`
extends `ModuleRegistry` with metadata for skill discovery.

```
register(name, factory)         ──►  stores lambda/constructor
register_with_meta(n, f, meta)  ──►  register + attach SkillMeta
resolve_pipeline([...])         ──►  returns ordered [Module, Module, ...]
validate_all()                  ──►  {name: bool} health status
list_always_on()                ──►  modules with always_run=True
find_by_trigger(text)           ──►  matches input against trigger keywords
```

### ProcessingPipeline

Runs modules sequentially, halting on first error.

```
pipeline.run(payload) → PipelineResult
  ├─ status: "ok" | "error"
  ├─ payload: enriched dict
  ├─ module_outputs: {name: output_dict}
  └─ errors: [{module, error_type, error_message}]
```

On error: calls `error_handler(module_name, exception, payload)` which
writes to the `error_log` table, then halts the pipeline.

### LLM Provider Abstraction

```
BaseLLMProvider (ABC)
  ├─ OpenAICompatibleProvider   ← generic (DeepSeek, any OpenAI-compat)
  │    └─ OpenRouterProvider    ← specialized (OpenRouter model names)
  └─ (future: OllamaProvider)
```

Each provider takes `api_key`, `model`, `api_base`, and optional
`thinking`/`reasoning_effort` params.

## Directory Map

```
AAA/
├── backend/
│   ├── main.py              FastAPI app + lifespan (module wiring)
│   ├── config.py             YAML + env config loader
│   ├── config.yaml           Default configuration
│   ├── api/
│   │   ├── routes.py         /chat, /history, /health, /agent, /errors, /skills
│   │   └── schemas.py        Pydantic request/response models
│   ├── core/
│   │   ├── pipeline.py       ProcessingPipeline orchestrator
│   │   ├── registry.py       ModuleRegistry (discovery, ordering)
│   │   └── context.py        PipelineResult dataclass
│   ├── personality/
│   │   ├── identity.yaml      Agent self-definition (name, prompt, traits, beliefs)
│   │   └── assembler.py       PromptAssemblerModule — composes system prompt
│   ├── skills/
│   │   ├── metadata.py        SkillMeta dataclass
│   │   └── registry.py        SkillRegistry — extends ModuleRegistry
│   ├── modules/
│   │   ├── base.py           ProcessingModule ABC
│   │   ├── embedder.py       Local sentence-transformers service
│   │   ├── llm_client.py     Provider-agnostic LLM client
│   │   └── context_collector.py  History formatting
│   ├── storage/
│   │   ├── database.py       SQLite init, WAL, migrations
│   │   ├── models.py         Message, ErrorLogEntry dataclasses
│   │   └── repository.py     CRUD for conversation_log, error_log
│   └── tests/                Per-step test files
├── frontend/
│   └── src/
│       ├── api/client.ts     Backend API calls
│       ├── hooks/useChat.ts  Chat state management
│       └── components/
│           ├── ChatView.tsx  Main chat container
│           ├── SidePanel.tsx Foldable pipeline/skills panel (right on desktop, bottom on mobile)
│           ├── MessageBubble.tsx  Markdown + thinking display
│           └── InputBar.tsx  Terminal prompt input
├── docs/
│   ├── TDD.md                Technical Design Document
│   ├── Implementation.md     Phase 1–4 roadmap
│   ├── SETUP.md              Installation guide
│   ├── CONFIG.md             Configuration reference
│   ├── PLUGINS.md            Module development guide
│   ├── ARCHITECTURE.md        This file
│   └── decisions/             Architecture Decision Records (ADRs)
├── pyproject.toml
└── README.md
```

## Design Principles

### Dual Storage
Every message stores raw `content` (re-embeddable) alongside `embedding` BLOB.
The `embedding_model` column tracks which model produced the vector, enabling
batch re-embedding when the model changes.

### Stateless Modules
Modules communicate only through the shared payload dict. No module holds
a reference to another. The pipeline is the sole orchestrator.

### Error Persistence
All pipeline failures are written to `error_log` with full traceback and
context. This provides an auditable failure record without losing conversational
state.

### Config-Driven
Module selection, ordering, LLM provider, and all parameters are driven by
`config.yaml` + environment variable overrides. No code changes needed to
switch providers or reorder the pipeline.

## Extension for Phase 2–4

Future modules plug into the same pipeline:

| Phase | Module | Where in pipeline | What it does |
|-------|--------|-------------------|-------------|
| **2** | `entropy_regulator` | After embedder | Computes cosine similarity, mutates `temperature`/`penalty` |
| **3** | `sedimentation_engine` | After context_collector | Vector/graph queries, d-index retrieval |
| **4** | `belief_validator` | After llm_client | Schema-matching, belief recalibration |

Each is a `ProcessingModule` — drop it in, register, reorder in config.
