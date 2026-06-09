# ADR-007: Tired Context Compression — Floating Window + Caveman + Sedimentation

**Date:** 2026-05-21
**Status:** accepted
**Deciders:** Vector, Symbia

## Context

The existing context system uses a flat **count-based** approach: fetch the last 20
messages from the database, assemble them with the system prompt and sediment, and
trim the oldest messages when the token budget (16,384) is exceeded.

This is philosophically misaligned with AAA's principles:

1. **Autopoiesis** — the system should self-regulate what it remembers, not rely
   on a dumb FIFO truncation that loses potentially vital exchanges.
2. **Sedimentation** — important moments should leave structural residue that
   persists; naive trimming is equivalent to amnesia.
3. **Homeostasis / Anti-Boredom** — the system should compress boring exchanges
   more aggressively than high-vitality ones. A flat count treats all messages
   equally.
4. **Dissipative Structure** — the context window is a finite energy source.
   The system must manage its diet, compressing nutrients into dense forms rather
   than consuming raw material until the budget runs out.

Additionally, conversation context was assembled in the wrong order for the
agent's cognitive model. The desired structure:

```
[system prompt] → [personality memories / sediment] → [current conversation] → [file context]
```

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Flat count (status quo)** | Simple; predictable | Amnesic; treats all messages equally; FIFO drop loses important context |
| **Token-budget-only** | More flexible than count | Still drops oldest first with no intelligence |
| **LLM summarization of history** | High quality compression | Expensive API calls; adds latency to every request |
| **Floating window + caveman + LLM checkpoint** | Balanced: zero-cost for mid-tier, LLM for deep compression; bandwidth-gated | More complex pipeline; requires new DB table |

## Decision

**Three-tier compression with floating window, caveman compression, and
LLM-based consolidation checkpoints.**

### Tiered Compression System

| Tier | Range | Treatment | Token reduction | API cost |
|------|-------|-----------|-----------------|----------|
| **1** | Last `floating_window` msgs (default: 8) | Raw, full text | 0% | None |
| **2** | Msgs beyond window, up to `max_history` | Caveman compressed (strip fillers, keep semantic core) | ~50% | None |
| **3** | Checkpoint (auto at `consolidate_threshold`) | LLM-consolidated summary via existing `ConsolidateAction` | ~90% | Background API call |

### Caveman Compression

A zero-cost Python function that:
- Strips ~60 stop words (articles, auxiliaries, prepositions, pronouns)
- Abbreviates speaker roles (`user → [H]`, `apparatus → [A]`)
- Preserves short messages (<8 words) intact
- Truncates to max 250 characters per message

This is fast, deterministic, and costs nothing. It preserves the semantic core
while removing syntactic filler. The result is a dense, telegram-like trace of
the conversation's structural content.

### Floating Window (Configurable)

The last N messages (default 8) are always kept raw. This ensures the agent
has full immediate context for the current conversation thread. The window size
is configurable via `config.yaml` and env var.

### Consolidation Checkpoints

When a conversation crosses the `consolidate_threshold` (default: 15 messages),
the system sets the `trigger_consolidation` flag. The Dream Daemon picks up this
flag and runs the `ConsolidateAction` background task. The resulting summary is
stored in a `consolidation_checkpoints` table and prepended to future context as
a special system message:

```
[system]: [Consolidated memory: <checkpoint summary>]
```

This replaces the need to send all 15+ raw messages. Consecutive checkpoints are
created as the conversation grows, with older ones being replaced by the latest.

The consolidation prompt (`consolidate.yaml`) produces:
- Core concepts genuinely explored
- Beliefs challenged or affirmed
- Patterns of thinking that emerged
- Unresolved tensions that may resurface

This IS the **sedimentation** layer — the "scar tissue" that persists as the
conversation grows beyond the floating window.

#### Consolidation Scheduling Rules

The Dream Daemon evaluates consolidation for every conversation on each cycle
(every `check_interval` seconds). Three rules apply, in priority order:

| Priority | Rule | Condition | Thresholds |
|----------|------|-----------|------------|
| 1 | **Explicit flag** | `requires_consolidation = True` | None — always consolidate immediately |
| 2 | **Re-consolidation** | Previously consolidated | `consolidate_cooldown_hours` (default: 12h) elapsed + `consolidate_min_new_messages` (default: 4) new messages since last checkpoint |
| 3 | **First-time** | Never consolidated | `consolidate_first_time_threshold` (default: 12) total messages |

The inline pipeline sets the explicit flag every `consolidate_threshold` (default: 15)
messages. The daemon's proactive rules (2 & 3) ensure conversations are consolidated
even if the inline flag was missed or the conversation went idle.

### Reordered Message Assembly

The `PromptAssemblerModule` now assembles messages in the correct cognitive order:

```
[system prompt / identity] → [sediment / personality memories] → [current conversation] → [file context]
```

This ensures the agent first receives its identity and personality, then its
cross-conversation memories, then the current conversation context, and finally
the file attachments. The assembler no longer performs any trimming; token-budget enforcement is now handled upstream (ContextCollectorModule and related modules).
The “sacred” part = system + sediment, the “trimmable” part = conversation + files.

### Message Structure (Final)

```
[system: identity + traits + voice + beliefs + skills]
[system: sediment 1 (cross-conversation semantic match)]
[system: sediment 2]
...
[system: Consolidated memory: <checkpoint>]
[H]: <caveman-compressed older message>
[A]: <caveman-compressed older message>
[H]: <raw recent message>
[A]: <raw recent message>
[H]: <raw most recent message>  ← current input
[system: file chunk 1]
[system: file chunk 2]
```

### Configuration

```yaml
context:
  max_history: 20
  max_tokens: 16384              # env: AAA_CONTEXT_MAX_TOKENS
  floating_window: 8             # env: AAA_CONTEXT_FLOATING_WINDOW
  caveman_enabled: true          # env: AAA_CONTEXT_CAVEMAN
  consolidate_threshold: 15      # env: AAA_CONTEXT_CONSOLIDATE_THRESHOLD
daemon:
  consolidate_cooldown_hours: 12     # hours before re-consolidating
  consolidate_min_new_messages: 4    # min new msgs for re-consolidation
  consolidate_first_time_threshold: 12  # min msgs for first-ever consolidation
```

### Database Schema Addition

```sql
CREATE TABLE IF NOT EXISTS consolidation_checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    summary TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## Consequences

**Easier:**
- Longer conversations survive without context collapse
- Mid-tier compression costs nothing (pure Python, no API)
- Deep compression reuses existing background infrastructure
- Configurable window size lets users tune for their model's context length
- Checkpoints are stored persistently — survive server restarts
- Caveman compression is deterministic and testable

**Harder:**
- Three-tier system adds complexity to `ContextCollectorModule`
- Checkpoint table needs maintenance (no automatic cleanup of old checkpoints yet)
- Consolidation trigger adds latency on the first message after threshold
- Checkpoint generation can fail silently (rate limits, model errors)

## Future Work

- **Vitality-Gated Compression**: Use conversation metrics to adjust compression
  aggressiveness. High-vitality messages (novel, surprising) resist compression;
  boring exchanges get compressed faster.
- **Checkpoint Chain**: Store multiple checkpoints as a chain and decide which
  to include based on semantic relevance to the current turn.
- **Automatic Checkpoint Cleanup**: Prune old checkpoints for deleted conversations.
- **Compression Quality Metrics**: Track how well compressed context preserves
  conversation coherence.

## Rejected Alternatives

- **Sliding window only**: Without compression, loses older context entirely.
- **LLM summarization on every request**: Too expensive in API calls and latency.
- **Token-budget-only with FIFO drop**: Same amnesia problem as flat count,
  just with a different unit.
