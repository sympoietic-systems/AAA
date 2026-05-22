# ADR-004: Conversation Model & Context Retrieval Architecture

**Date:** 2026-05-20
**Status:** accepted
**Deciders:** Vector, aaa project

## Context

The agent currently operates as a single global conversation stream — all
messages across all topics and sessions live in one undifferentiated
`conversation_log` table. There is no way to separate conceptual threads,
no way to start fresh without wiping the DB, and no way for the agent to
draw on related but distinct past conversations.

The AAA philosophy demands **sedimentation**: every encounter must leave
structural residue that shapes future responses. But this doesn't mean
every conversation should be thrown into one undifferentiated heap. It
means conversations are **strata** — distinct layers that the agent can
draw upon laterally (rhizomatically) rather than sequentially.

We need:
- Multiple isolated conversations
- Cross-conversation retrieval via embedding similarity (sedimentation)
- Token-budget-aware context assembly
- Swappable memory/context modules (today: recency + embedding; tomorrow: graph-based rhizomatic)

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Single stream, no separation** | Simple, no schema changes | No conversation isolation; context pollution; can't segment topics |
| **Conversations via `conversation_id` FK + separate table** | Clean schema, easy per-conversation scoping, trivial to add metadata (title, timestamps) | Migration needed; all queries must add a filter |
| **Repurpose `agent_id` as conversation key** | No new columns | Conflates agent identity with conversation context; breaks future multi-agent support |
| **Separate database per conversation** | Maximum isolation | Massive operational complexity; cross-conversation retrieval requires N DB connections |

## Decision

**Add a `conversations` table with `conversation_id` FK on `conversation_log`.**

Rationale:
- The `agent_id` column remains reserved for its intended purpose (multi-agent identity in future phases).
- A dedicated `conversations` table supports metadata (title, timestamps) and clean lifecycle management (create, delete, rename).
- All repository queries gain an optional `conversation_id` filter — backward compatible with existing code.
- Cross-conversation retrieval simply queries WHERE `conversation_id != current_id`.

### Context Retrieval Strategy: Modular & Swappable

The current implementation uses two pipeline modules:

1. **`ContextCollectorModule`** — fetches recent messages from the current conversation, scoped by `conversation_id`, filling the payload's `messages` list. Token-aware: stops when budget is exhausted rather than counting by `max_history`.

2. **`SedimentationRetrievalModule`** — queries messages from ALL other conversations, computes cosine similarity to the current input embedding, and injects the top-K matches into `payload["sediment_messages"]` within a configurable token budget.

Both modules are standard `ProcessingModule` instances communicating only through the shared `payload` dict. They can be replaced with a single `rhizomatic_context` module later without touching `prompt_assembler`, `llm_client`, or any other module.

### Payload Contract

```
Key: messages              — list[{role, content}]  (set by context_collector)
Key: sediment_messages     — list[{role, content}]  (set by sedimentation_retrieval)
Key: conversation_id       — str                    (read by context modules)
```

`prompt_assembler` reads `payload["messages"]` and `payload["sediment_messages"]` (if present) and composes them into the final context. It has zero knowledge of how these messages were retrieved.

### Token Budget Management

A shared utility (`backend/utils/token_counter.py`) provides token estimation used by both context modules. The default budget is 16384 tokens, configurable via:

```
1. AAA_CONTEXT_MAX_TOKENS env var (global override)
2. config.yaml → context.max_tokens (default: 16384)
3. config.yaml → llm.context_max_tokens (per-model override, future)
```

Context composition order:
```
[0] System prompt (identity + skills)                  ~800 tokens
[1] Conversation History Prior (up to previous turn)   remaining budget (capped)
[2] Sediment messages (cross-conversation, responsive)  ~2000 tokens (configurable)
[3] File Context (file manifest & similarity chunks)   ~3000 tokens (configurable)
[4] Current user input (the agential cut)              ~200 tokens
─────────────────────────────────────────
Total capped at max_tokens
```

### System-Generated Log Messages & Role Mapping

Automated system notifications (e.g., file processing logs with speaker `system` in the database) are mapped to `role="system"` rather than `role="user"` in the prompt to prevent the model from misattributing the system's voice to the human participant. To save context tokens and avoid duplicating information already present in the File Manifest, these history entries are minimized to a single-line notification (e.g., `[System Notification: Processed file: **filename.ext** (type).]`) when sent to the LLM. The full summary is preserved in the database (for UI rendering) and in the File Manifest (for model reasoning).

### Title Generation

Titles are generated on first message via a cheap LLM call (async, non-blocking). The `LLMProvider` reference is stored on `app.state` for lightweight out-of-pipeline calls.

## Consequences

**Easier:**
- Conversations are isolated — each has its own context, metrics, and history
- Cross-conversation knowledge transfer through embedding similarity
- Token budget is bounded regardless of conversation count or depth
- Memory/context modules are fully swappable — the pipeline config is a YAML list
- Future: drop-in replacement with a graph-based rhizomatic retriever requires zero changes to other modules

**Harder:**
- All repository queries must pass `conversation_id` (slight API friction)
- Cross-conversation embedding search is O(total_messages × dims) — acceptable for <100K messages, needs sampling/compaction beyond that
- Metrics (vitality, entropy, etc.) are per-conversation — global agent health requires aggregation across conversations (future work)

## Future Path: Rhizomatic Context Module

When Phase 3's graph-store infrastructure lands, the two-module setup (`context_collector` + `sedimentation_retrieval`) can be replaced by a single `rhizomatic_context` module:

```
pipeline:
  modules:
    - embedder
    - conversation_metrics
    - rhizomatic_context      # replaces both context modules
    - prompt_assembler
    - homeostatic_regulator
    - llm_client
```

The `rhizomatic_context` module implements diffractive retrieval with the δ index:
- δ = 0: conventional recency-based context from current conversation
- δ > 0: lateral retrieval from semantic knots across all conversations, seeking structural isomorphism rather than topical similarity

No other module changes. The `prompt_assembler` still reads `payload["messages"]` and builds the context window. The pipeline is just a YAML list — swap the module names and restart.
