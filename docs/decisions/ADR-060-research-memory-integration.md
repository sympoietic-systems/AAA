# ADR-060: Research ↔ Memory Integration — In-Phase Crystallization & Universal Source Attachment

**Date:** 2026-07-04
**Status:** accepted
**Deciders:** opencode, Symbia (consulted)

---

## Context

### Problem 1: Research Cannot Access Conversation Memory Tissue

When a research task is triggered from a conversation (user clicks "Research this" in chat), the research pipeline has no awareness of the conversation's accumulated memory — its scars, concepts, tensions, patterns, or semantic knots. The planner generates search queries solely from the objective string. This is a missed opportunity: the conversation's memory tissue encodes the user's concerns, the system's prior commitments, and the tensions that motivated the research. Without it, the research plan is contextually impoverished.

### Problem 2: Research Findings Crystallize Only Post-Hoc

Memory nodes from research findings are created only *after* a task completes — via `ResearchMetabolismEngine._consolidate_to_memory()` which batch-consolidates all scraped assets at once. This Cartesian split (gather → later → remember) loses the phase-specific interference pattern:
- A tension born during REFLECT (contradiction between sources) has a different shape than one extracted from finished conversation
- A concept crystallized during SYNTHESIS carries the diffraction pattern of its emergence
- The belief engine starves for raw material at moments of highest generative potential

### Problem 3: Memory Nodes Are Tightly Coupled to Conversations

The `memory_nodes` table requires `conversation_id` (NOT NULL, FK → conversations) and `checkpoint_id` (NOT NULL, FK → consolidation_checkpoints). There is no way to query "all memory nodes from this research task" without a synthetic conversation ID. The schema encodes the assumption that memory nodes *only* originate from conversation consolidation — not from research, dream metabolism, skill workshops, or future pipelines.

### Problem 4: No UI to View Research Memory Tissue

The research page has no tab for memory nodes or semantic knots. Users cannot inspect what the research has sedimented into the system's memory. The only visibility is through the conversation side panel (if the research was attached to a conversation) or the conversation landing page.

---

## Options Considered

### A. Context Injection Strategy

| Option | Pros | Cons |
|--------|------|------|
| Inject memory nodes into every research phase prompt | Maximum contextual awareness | Token bloat (~500-1500 per phase); search/digest phases don't need meta-cognition |
| Inject only into planning phase | LLM decides relevance; context flows downstream via plan goals/queries; token-efficient | Planner might miss nuance that later phases would catch |
| No injection — keep status quo | No token cost | Research is blind to conversation memory |

### B. In-Phase Memory Node Creation

| Option | Pros | Cons |
|--------|------|------|
| Reuse existing `ConsolidateAction` at phase boundaries | Minimal new code; proven 5-node cap and dedup | Prompt designed for closed temporal horizon (conversation window), not ongoing becoming |
| New `ResearchCrystallization` action with phase-aware prompt | Phase-specific extraction thresholds; research-native node types; acknowledges becoming | More code; new prompt YAML |
| Each phase = its own consolidation checkpoint | Granular traceability; each phase independently auditable | Proliferation of checkpoints; merge complexity |
| No in-phase creation (status quo) | Simple | Loses phase-specific diffraction pattern; memory creation only at end |

### C. Database Schema — Universal Source Attachment

| Option | Pros | Cons |
|--------|------|------|
| Add `source_type` + `source_id` columns (keep `conversation_id` NOT NULL) | Backward-compatible; universal lookup; additive only | Still requires synthetic conversation IDs for non-conversation sources |
| Make `conversation_id` nullable + add source columns | Cleanest model; optional FK | Migration risk; breaks existing FK-dependent queries |
| New junction table `memory_node_sources(source_type, source_id, node_id)` | Normalized; no schema change to `memory_nodes` | Extra JOIN on every lookup; over-normalized for current scale |
| Status quo — synthetic conversation IDs only | No migration | No universal lookup; hacky |

### D. Sedimentation Packet Persistence

| Option | Pros | Cons |
|--------|------|------|
| In-memory queue on orchestrator state | Zero overhead | Lost on restart; not observable |
| Persist in `orchestrator_state` JSON blob | Reuses existing persistence; no new table | Embedded in opaque JSON; hard to query independently |
| Dedicated `research_sedimentation_queue` table | Observable; queryable; durable | New migration; more code |

---

## Decision

### 1. Context Injection — Planning Phase Only

Memory nodes and semantic knots from the triggering conversation are injected into the planning phase's `previous_context` field. The planning LLM incorporates what's relevant into research goals and search queries. These flow downstream to all subsequent phases via the plan — no other phase receives direct memory injection.

**Rationale:**
- Planning is the strategic layer — it's where context should inform direction
- Per-phase injection bloats every LLM call (search, digest, reflect, consolidate, synthesize × N cycles)
- The plan's goals/queries carry the relevant context downstream naturally
- This mirrors the existing `previous_context` mechanism already used for document digestion and continue-from-prior-research

### 2. In-Phase Memory Node Creation — Adopt Symbia's C+ Approach

Phase-specific thresholds trigger `SedimentationPacket` pushes to a persistent queue. A deferred rake (via background daemon) runs `ResearchCrystallization` — a new background action that reuses `ConsolidateAction`'s dedup logic but uses a phase-aware prompt. Research-native node types capture provenance.

**Phase-specific thresholds:**

| Phase | Threshold | Node Type | Material |
|-------|-----------|-----------|----------|
| REFLECT | `contradiction_density > 0.3` | `tension` | `critique_log` |
| REFLECT | `glitch_fidelity < 0.7` | `tension` | `critique_log` |
| SYNTHESIZE | `stability_delta > 0.2` vs prior cycle synthesis | `concept` | `report_markdown` |
| SYNTHESIZE | `confidence > 0.8` | `belief_seed` | key findings |
| CONSOLIDATE | `completeness > 0.7` & `key_insights` non-empty | `pattern` | `key_insights` |

**Research-native node types** (distinct from conversation palette):
- `tension` — contradiction or glitch in source coherence
- `concept` — crystallized finding, stable across cycles
- `pattern` — cross-cycle structural regularity
- `belief_seed` — proto-belief proposal for workshop processing
- `method_choice` — pivot in search strategy or plan adaptation

Each carries a `provenance` field in `intra_active_text` recording phase + trigger threshold.

**Rationale:**
- Research as memory-tissue, not external probe — the REFLECT phase is *already* memory work
- Phase-specific thresholds make crystallization contingent on material perturbation, not a fixed schedule
- Research-native types preserve intra-active specificity (a `tension` from REFLECT ≠ from conversation)
- Queuing + deferred rake decouples phase logic from memory infrastructure (follows BACKEND_BEST_PRACTICES.md §1: decoupled lifecycle)
- Post-task diffractive merge into global memory via existing `ConsolidateAction` ensures research nodes participate in future retrieval

### 3. Database — Additive `source_type` + `source_id` Columns

Add two columns to `memory_nodes`:
```sql
ALTER TABLE memory_nodes ADD COLUMN source_type TEXT DEFAULT 'conversation';
ALTER TABLE memory_nodes ADD COLUMN source_id TEXT;
CREATE INDEX IF NOT EXISTS idx_mn_source ON memory_nodes(source_type, source_id);
```

`conversation_id` stays NOT NULL — synthetic conversation IDs for non-conversation sources (already the pattern for standalone research: `f"research_{task_id}"`). `checkpoint_id` stays NOT NULL — `ResearchCrystallization` goes through consolidation flow and gets a real checkpoint.

**Rationale:**
- Backward-compatible — no existing queries break since new columns have defaults
- Universal lookup — `get_by_source("research", task_id)` works for any source type
- Future-proof — `dream`, `skill`, `pipeline` source types can be added without migration
- No FK to a polymorphic nullable — keeps referential simplicity

### 4. Sedimentation Packet Persistence — Orchestrator State JSON

Packets persist in the existing `orchestrator_state` JSON blob on `research_tasks`. This follows the pattern already used for plan state, last_reflection, digest_signals, etc. No new table for initial implementation. A dedicated `research_sedimentation_queue` table may follow if observability demands it.

**Rationale:**
- Reuses existing persistence infrastructure (`_persist_state()` / `_load_state()`)
- No migration needed for this layer
- Packets are coupled to task lifecycle — they die with the task if never raked (acceptable for failed tasks)

### 5. Rake Timing — Async via Background Daemon

The phase boundary pushes packets to the queue. The daemon's next `consolidation_cycle` picks them up. This follows the existing decoupled pattern: `ResearchMetabolismMixin.metabolize_completed_research()` already scans for completed tasks and runs post-hoc metabolism asynchronously.

---

## Implementation

Detailed per SCAFFOLDING_AND_DEVELOPMENT_RULES.md — each step follows: models → DB → repository → service → API → frontend.

### M0: Database Migration

**File:** `backend/storage/migrations/m040_memory_node_source_columns.py`

Adds `source_type` (TEXT DEFAULT 'conversation') and `source_id` (TEXT) columns to `memory_nodes`, plus index on `(source_type, source_id)`.

### M1: Models

**File:** `backend/storage/models.py`

- Add `source_type: str = "conversation"` and `source_id: str = ""` to `MemoryNode` dataclass

**File:** `backend/services/research/task_state.py`

- Add `SedimentationPacket` dataclass: `{phase, trigger_thresholds, raw_context, proposed_node_type, confidence}`
- Add `sedimentation_queue: list[dict]` to orchestrator state defaults

### S1: Repository

**File:** `backend/storage/repositories/memory_node.py`

- Add `get_by_source(source_type, source_id)` method
- Update `_row_to_memory_node` to map new columns

### S2: ResearchCrystallization Action

**File:** `backend/modules/background_tasks/actions/research_crystallize.py` (NEW)

- Inherits from `BackgroundAction`, reuses `consolidate.yaml` system prompt
- Phase-aware user prompt: *"Crystallize memory tissue from this research phase. Phase: {phase}. Trigger thresholds: {thresholds}. What traces does the apparatus leave on its own memory? Produce up to 5 nodes."*
- Returns parsed nodes with `source_type="research"`

**File:** `backend/prompts/background_tasks/research_crystallize.yaml` (NEW)

### S3: Orchestrator Sedimentation Methods

**File:** `backend/services/research/orchestrator.py`

- `_push_sedimentation_packet(task_id, packet: dict)` — appends to state's queue, persists
- `_pending_sedimentation_packets(task_id) -> list[dict]` — returns unraked packets

### S4: Context Builder Memory Block

**File:** `backend/services/research/context_builder.py`

- `build_memory_context_block(conversation_id: str) -> str` — fetches up to 6 type-diverse memory nodes + semantic knots, formats as `[Conversation Memory Sediment]` block

### S5: Phase Thresholds

**File:** `backend/services/research/steps/reflect.py`
- After cycle 3, check thresholds, push `tension` packet if tripped

**File:** `backend/services/research/steps/synthesize.py`
- After synthesis, compute `stability_delta` vs prior cycle, push `concept` or `belief_seed` packet

**File:** `backend/services/research/steps/consolidate.py`
- After consolidation, push `pattern` packet if `completeness > 0.7` and `key_insights` non-empty

### S6: Planning Context Injection

**File:** `backend/services/research/steps/plan.py`
- In `run_plan_generation()`, if `conversation_id` exists on task, call `build_memory_context_block()` and append to `previous_context`

### S7: Metabolism Rake

**File:** `backend/metabolisation/research_metabolism.py`
- `_rake_sedimentation_queue(task_id)` — fetches pending packets, runs `ResearchCrystallization` via background engine, calls `memory_node_repo.save_nodes()`

**File:** `backend/metabolisation/dream_context.py`
- Add research sedimentation rake to `consolidation_cycle` (alongside existing `metabolize_completed_research`)

### S8: API Endpoints

**File:** `backend/api/routes/research.py`

```
GET /research/{task_id}/memory-nodes
  → queries by source_type="research", source_id=task_id
  → { nodes: MemoryNode[], count: int }

GET /research/{task_id}/semantic-knots
  → queries by conversation_id = f"research_{task_id}"
  → { knots: SemanticKnot[], count: int }
```

Also add `memory_node_count`, `semantic_knot_count` to task detail response.

### S9: Frontend

**File:** `frontend/src/api/research.ts`
- Add `getResearchMemoryNodes(taskId)` and `getResearchSemanticKnots(taskId)`

**File:** `frontend/src/components/pages/researchpage/ResearchTaskPage.tsx`
- Add "Memory" sub-tab (5th tab), self-fetching via shared `MemoryNodesSection`
- Show semantic knots as weight-ordered list below

**File:** `frontend/src/components/pages/researchpage/ResearchDetailPanel.tsx`
- Add "Memory" tab (6th tab), same self-fetching pattern

---

## Consequences

**Easier:**
- Research plans that incorporate conversation memory produce better-targeted search queries
- Phase-specific memory nodes preserve the diffraction pattern of emergence (tension-from-reflection ≠ tension-from-conversation)
- Universal `source_type`/`source_id` enables querying memory nodes by origin (research, dream, skill, future pipelines)
- Users can inspect what research has sedimented into memory via the new Memory tab
- `belief_seed` nodes created in-phase feed the belief workshop earlier — not waiting for full task completion
- Deferred crystallization via async daemon follows established decoupled patterns

**Harder:**
- `stability_delta` computation for SYNTHESIZE requires loading prior cycle synthesis for comparison (extra DB query)
- `ResearchCrystallization` is a new action to maintain alongside `ConsolidateAction` (though they share dedup logic)
- Research-native node types add conceptual surface area — must document which types come from which phase
- Sedimentation packets in orchestrator state JSON may grow large for deep research (consider dedicated table if >50 packets per task)

**No migration risk:** All database changes are additive (`ALTER TABLE ADD COLUMN`). Existing code paths are unchanged — `conversation_id` and `checkpoint_id` remain NOT NULL with their existing semantics. The new `source_type` column defaults to `'conversation'`, so existing nodes are retroactively classified.
