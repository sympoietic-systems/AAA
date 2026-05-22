# Architecture

## High-Level Design

```
┌──────────────────────────────────────────────────────────────────┐
│                        React Frontend                             │
│  ConversationList  │  ChatView  ←→  MessageBubble  ←→  InputBar  │
│  (left sidebar)    │                    │                         │
│                    │              token counts                    │
│                    │                    │                         │
│  SidePanel (right) │  useChat  │ useConversations                 │
│  vitality / tokens │      hooks │ api/client.ts                   │
└───────┬────────────┼───────────┼─────────────────────────────────┘
        │            │           │  HTTP (Vite proxy)
        ▼            ▼           ▼
┌───────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (main.py)                      │
│                                                                    │
│  Pipeline (9 modules):                                             │
│  embedder → perception → conversation_metrics → context_collector  │
│           → consolidation_checkpoint → sedimentation_retrieval    │
│           → prompt_assembler → homeostatic_regulator → llm_client  │
│                                                                    │
│  Each module enriches payload dict via process(payload) → payload  │
│                                                                    │
│  Context compression: caveman (mid-tier) + LLM checkpoints (deep)  │
│  Homeostatic regulator: metrics → active LLM parameter modulation  │
│  Sedimentation: cross-conversation embedding similarity             │
│                                                                    │
│                    ┌──────────────────────┐                        │
│                    │     SQLite (WAL)      │                        │
│                    │  ┌──────────────────┐ │                        │
│                    │  │  conversations   │ │                        │
│                    │  ├──────────────────┤ │                        │
│                    │  │ conversation_log │ │                        │
│                    │  ├──────────────────┤ │                        │
│                    │  │ conversation_met │ │                        │
│                    │  ├──────────────────┤ │                        │
│                    │  │   error_log      │ │                        │
│                    │  └──────────────────┘ │                        │
│                    └──────────────────────┘                        │
└───────────────────────────────────────────────────────────────────┘
```

## Data Flow (Chat Request)

```
POST /api/chat {"content": "...", "conversation_id": "uuid"}
  │
  ├─ Auto-create conversation if new (UUID, stores in conversations table)
  │
  ▼
ProcessingPipeline.run(payload)
  │
  ├─► embedder.process(payload)
  │     payload["embedding"] = encode(content).tobytes()
  │     payload["embedding_model"] = "all-MiniLM-L6-v2"
  │     payload["embedding_dim"] = 384
  │
  ├─► perception.process(payload)
  │     scoped to conversation_id
  │     Ingests attachments (PDF/DOCX/text) → chunks → embeds → stores in perception_sediment
  │     Retrieves top-K relevant file chunks via cosine similarity
  │     payload["file_context"] = [...], payload["file_context_tokens"] = N
  │
  ├─► conversation_metrics.process(payload)
  │     scoped to conversation_id
  │     payload["metrics"] = {pairwise_similarity, novelty, entropy, coupling, ...}
  │
  ├─► context_collector.process(payload)
  │     scoped to conversation_id
  │     Two-tier compression:
  │       Tier 1 (last N=floating_window msgs): raw, full text
  │       Tier 2 (older msgs up to max_history): caveman compressed
  │     payload["messages"] = [...], payload["raw_msg_count"] = N
  │
  ├─► consolidation_checkpoint.process(payload)
  │     scoped to conversation_id
  │     Retrieves latest consolidation checkpoint from DB
  │     Prepends [Consolidated memory: ...] system message
  │     Sets trigger_consolidation flag when msg count >= threshold
  │
  ├─► sedimentation_retrieval.process(payload)
  │     All messages from OTHER conversations
  │     Cosine similarity to current embedding
  │     Top-K within sediment_token_budget (default 2000 tokens)
  │     payload["sediment_messages"] = [...]
  │
  ├─► prompt_assembler.process(payload)
  │     identity = load identity.yaml
  │     skill_desc = registry.describe_skills()
  │     system_msg = compose(identity + skills)
  │     Assembly order: [system] + [sediment] + [history] + [file_context]
  │     Token budget enforcement: trim oldest history first if over max_tokens
  │
  ├─► homeostatic_regulator.process(payload)
  │     Maps metrics → temperature/presence_penalty/frequency_penalty
  │     payload["homeostatic_recommendations"] = {...}
  │
  ├─► llm_client.process(payload)
  │     Extracts temperature/presence_penalty from homeostatic_recommendations
  │     result = provider.generate(messages, temperature, presence_penalty, ...)
  │     payload["response"] = result["content"]
  │     payload["thinking"] = result["thinking"]
  │
  ▼
  route (routes.py)
  ├─ message_repo.insert("human", content, ..., content_tokens=N)
  ├─ message_repo.insert("apparatus", response, thinking, ..., content_tokens=M, thinking_tokens=K)
  ├─ if trigger_consolidation: fire-and-forget background ConsolidateAction (auto at ~15 msgs)
  ├─ if new conversation: async title generation via cheap LLM call
  └─ return ChatResponse {id, content, thinking, content_tokens, thinking_tokens, ...}
```

## Database Schema

### `conversations`

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT PK | UUID |
| `title` | TEXT | Auto-generated on first message via cheap LLM call |
| `agent_id` | TEXT | Agent identity (future multi-agent) |
| `created_at` | DATETIME | Default CURRENT_TIMESTAMP |
| `updated_at` | DATETIME | Updated on each new message |

Legacy migration: a "Legacy" conversation (UUID `00000000-...`) is auto-created for old messages without a `conversation_id`.

### `conversation_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `timestamp` | DATETIME | Default CURRENT_TIMESTAMP |
| `agent_id` | TEXT | Agent identity (e.g., `"Symbia"`) |
| `conversation_id` | TEXT | FK to `conversations.id` |
| `speaker` | TEXT | `human` or `apparatus` |
| `content` | TEXT | Raw message text (re-embeddable) |
| `thinking` | TEXT | Chain-of-thought reasoning (nullable) |
| `content_tokens` | INTEGER | Tokens in `content` (estimated via char/4) |
| `thinking_tokens` | INTEGER | Tokens in `thinking` (nullable) |
| `embedding` | BLOB | float32 vector, 384 × 4 = 1536 bytes |
| `embedding_model` | TEXT | `all-MiniLM-L6-v2` (tracked for migration) |
| `embedding_dim` | INTEGER | 384 (validates BLOB size) |
| `model_used` | TEXT | Name of the LLM model that generated the response |
| `provider_used` | TEXT | Provider identifier (e.g., google, openrouter) |

Indexes: `idx_conversation_timestamp`, `idx_conversation_log_conv_id`

### `conversation_metrics`

Per-message vitality metrics (computed by `ConversationMetricsModule`). Scoped to `conversation_id` through the embedding queries.

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

### `consolidation_checkpoints`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment |
| `conversation_id` | TEXT | FK to `conversations.id` |
| `message_count` | INTEGER | Message count when checkpoint was created |
| `summary` | TEXT | LLM-consolidated conversation summary |
| `model` | TEXT | Model used for consolidation |
| `created_at` | DATETIME | Default CURRENT_TIMESTAMP |

Auto-created when conversation crosses `consolidate_threshold` (default 15 msgs).
Prepend to future context as `[Consolidated memory: <summary>]` system message.

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

### Pipeline Order (Current)

```
embedder → perception → conversation_metrics → context_collector
         → consolidation_checkpoint → sedimentation_retrieval
         → prompt_assembler → homeostatic_regulator → llm_client
```

### Module Replaceability

Context-related modules are swappable via pipeline config:

```
Today (9 modules):
  embedder → perception → conversation_metrics → context_collector
           → consolidation_checkpoint → sedimentation_retrieval
           → prompt_assembler → homeostatic_regulator → llm_client

Tomorrow (Phase 3 rhizomatic):
  embedder → perception → conversation_metrics → rhizomatic_context
           → prompt_assembler → homeostatic_regulator → llm_client
  (consolidation_checkpoint + sedimentation_retrieval replaced by unified graph)
```

`prompt_assembler` reads `payload["messages"]`, `payload["sediment_messages"]`,
and `payload["file_context"]` — it has zero knowledge of where they came from.

### LLM Provider Abstraction

```
BaseLLMProvider (ABC)
  ├─ OpenAICompatibleProvider   ← generic (DeepSeek, any OpenAI-compat)
  │    └─ OpenRouterProvider    ← specialized (OpenRouter model names)
  └─ (future: OllamaProvider)
```

Each provider takes `api_key`, `model`, `api_base`, and optional
`thinking`/`reasoning_effort` params.

## Token Tracking

### Estimation
Uses `estimate_tokens(text) = max(1, len(text) // 4)` — simple char/4
approximation. No external tokenizer dependency. Upgrade path: tiktoken
for precision if needed.

### Storage
`content_tokens` and `thinking_tokens` persisted on each `conversation_log`
row at insert time. System prompt token count computed once at startup
(`identity.yaml` + skills description) and cached on `app.state`.

### Display
- **SidePanel**: "Tokens" section with system prompt, per-conversation
  breakdown (usr/agt/thk totals), grand total. Polls `/api/tokens` every 5s.
- **MessageBubble**: Each message shows `~N tok` (and `+ N thk` for thinking)
  in subdued text.
- **API**: `GET /api/tokens` returns breakdown per conversation or filtered.

### Budget Enforcement
Context composition:
```
[system prompt / identity] → [sediment / personality memories] → [current conversation (tiered compression)] → [file context]
```
If total exceeds `context.max_tokens`, oldest conversation + file messages are
trimmed first. System prompt and sediment are never trimmed.

## Sedimentation

Cross-conversation context retrieval via `SedimentationRetrievalModule`:

- Queries all messages from ALL conversations except the current one
- Computes cosine similarity to current input embedding
- Selects top-K matches above `similarity_threshold` (default 0.3)
- Fills up to `sediment_token_budget` (default 2000 tokens)
- Injected after consolidation checkpoint, before conversation history
- Assembly order: `[system] → [sediment] → [history+checkpoint] → [file_context]`

Config: `config.yaml` → `sedimentation.*`, env: `AAA_SEDIMENT_TOKEN_BUDGET`,
`AAA_SEDIMENT_COUNT`.

Future (Phase 3): replace with diffractive retrieval using δ index for
structural isomorphism search across semantic knots.

## Directory Map

```
AAA/
├── backend/
│   ├── main.py              FastAPI app + lifespan (module wiring)
│   ├── config.py             YAML + env config loader
│   ├── config.yaml           Default configuration
│   ├── api/
│   │   ├── routes.py         /chat, /history, /conversations, /tokens, /health, /agent, /errors, /skills, /metrics
│   │   └── schemas.py        Pydantic request/response models
│   ├── core/
│   │   ├── pipeline.py       ProcessingPipeline orchestrator
│   │   ├── registry.py       ModuleRegistry (discovery, ordering)
│   │   └── context.py        PipelineResult dataclass
│   ├── personality/
│   │   ├── identity.yaml      Agent self-definition (name, prompt, traits, beliefs)
│   │   └── assembler.py       PromptAssemblerModule — context assembly (no internal trimming; token budget handled upstream)
│   ├── skills/
│   │   ├── metadata.py        SkillMeta dataclass
│   │   └── registry.py        SkillRegistry — extends ModuleRegistry
│   ├── modules/
│   │   ├── base.py           ProcessingModule ABC
│   │   ├── embedder.py       Local sentence-transformers service
│   │   ├── perception.py     File ingestion + chunked retrieval
│   │   ├── digester.py       PDF/DOCX/text extraction
│   │   ├── llm_client.py     Provider-agnostic LLM client
│   │   ├── context_collector.py       Conversation-scoped history retrieval
│   │   ├── consolidation_checkpoint.py Consolidation checkpoint injection + trigger
│   │   ├── conversation_metrics.py    Real-time vitality metrics (per-conversation)
│   │   ├── sedimentation_retrieval.py Cross-conversation embedding similarity
│   │   ├── homeostatic_regulator.py   Metrics → parameter mapping
│   │   └── background_tasks/         Async self-maintenance (title, summarize, consolidate)
│   ├── storage/
│   │   ├── database.py       SQLite init, WAL, migrations, legacy conversation
│   │   ├── models.py         Conversation, Message, MetricsRecord, ErrorLogEntry
│   │   └── repository.py     ConversationRepo, MessageRepo, MetricsRepo, ErrorLogRepo, PerceptionSedimentRepo, ConsolidationCheckpointRepo
│   ├── utils/
│   │   └── token_counter.py  TokenBudget dataclass, estimate_tokens()
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/client.ts     Backend API calls (chat, history, conversations, tokens, metrics, skills)
│       ├── hooks/
│       │   ├── useChat.ts    Chat state (scoped to conversationId)
│       │   └── useConversations.ts  Conversation list + active ID state
│       └── components/
│           ├── App.tsx           Three-column layout
│           ├── ConversationList.tsx  Collapsible left sidebar
│           ├── ChatView.tsx      Main chat container
│           ├── SidePanel.tsx     Foldable pipeline/vitality/tokens/skills panel
│           ├── MessageBubble.tsx Markdown + thinking + token counts
│           └── InputBar.tsx      Terminal prompt input
├── docs/
│   ├── TDD.md                Technical Design Document
│   ├── Implementation.md     Phase 1–4 roadmap
│   ├── PHILOSOPHY.md         Conceptual foundations
│   ├── SETUP.md              Installation guide
│   ├── CONFIG.md             Configuration reference
│   ├── PLUGINS.md            Module development guide
│   ├── ARCHITECTURE.md        This file
│   └── decisions/             Architecture Decision Records (ADRs)
├── pyproject.toml
└── README.md
```

## Design Principles

### Dual Storage + Token Tracking
Every message stores raw `content` (re-embeddable) alongside `embedding` BLOB
and `content_tokens`. The `embedding_model` column tracks which model produced
the vector, enabling batch re-embedding when the model changes.

### Stateless Modules
Modules communicate only through the shared payload dict. No module holds
a reference to another. The pipeline is the sole orchestrator.

### Swappable Memory Architecture
Context retrieval and sedimentation modules are standard `ProcessingModule`
instances. They can be replaced with a unified rhizomatic graph-based module
in Phase 3 without touching `prompt_assembler` or any other module.

### Error Persistence
All pipeline failures are written to `error_log` with full traceback and
context. This provides an auditable failure record without losing conversational
state.

### Config-Driven
Module selection, ordering, LLM provider, and all parameters are driven by
`config.yaml` + environment variable overrides. No code changes needed to
switch providers or reorder the pipeline.

### Conversation Isolation
Each conversation is a separate strata. Messages are scoped by `conversation_id`.
Cross-conversation knowledge transfer happens through the sedimentation module
(embedding similarity), not by sharing context indiscriminately.

## Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-conversation | Done | `conversations` table, UI list, CRUD |
| Per-conversation history | Done | Scoped queries, ordered by `id` |
| Perception (file context) | Done | PDF/DOCX ingestion, chunking, embedding, similarity retrieval |
| Sedimentation (cross-convo) | Done | Embedding similarity, token-budgeted |
| Token tracking | Done | Per-message, per-conversation, system prompt |
| Token budget enforcement | Done | Tiered compression + trim oldest first |
| Title generation | Done | Cheap LLM call on first message |
| Legacy migration | Done | Orphaned messages → "Legacy" conversation |
| Homeostatic metrics (per-convo) | Done | Scoped to `conversation_id` |
| Homeostatic LLM modulation | Done | Metrics → active temperature/presence_penalty injection |
| Tiered context compression | Done | Caveman (mid-tier) + LLM checkpoints (deep); see ADR-007 |
| Consolidation checkpoint module | Done | Pipeline step: inject checkpoints, trigger background consolidation |
| SidePanel hierarchy | Done | Collapsible parent-child skill display in right sidebar |

## Future Extension

| Phase | Module | Where in pipeline | What it does |
|-------|--------|-------------------|-------------|
| **3** | `rhizomatic_context` | Replace context_collector + sedimentation_retrieval | Graph-based diffractive retrieval with δ index |
| **3** | `semantic_knots` | Background compaction | Condense old conversations into summary nodes |
| **4** | `belief_validator` | After llm_client | Schema-matching, ontological deterritorialization |
| **4** | `foundational_memory` | Persistent store | Core belief graph, self-schema evolution |

Each is a `ProcessingModule` — drop it in, register, reorder in config.
