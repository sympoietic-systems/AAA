# Memory System Implementation Plan

> **Branch:** `feature/memory-system-implementation`
> **Source:** `docs/systems/MEMORY_SYSTEM.md` — Section 13 (Implementation Audit), Section 15 (Autopoietic Critique & Integrated Roadmap)
> **Status:** Planning Complete → Phase 0 begins
> **Items:** 13 total — R1–R5 (5 engineering), S1–S3 (3 autopoietic), P4–P6 (3 prompt), + 13A (1 test), + 13C (1 belief-system fix)

---

## Overview

This document translates all 13 actionable items from `MEMORY_SYSTEM.md` into concrete, stage-by-stage implementation tasks:

- **R1–R5** (5 engineering recommendations, Section 15.2)
- **S1–S3** (3 autopoietic augmentations, Section 15.3)
- **P4–P6** (3 prompt-level refinements, Section 15.3)
- **13A** (1 test recommendation — checkpoint agreement invariant, Section 13A)
- **13C** (1 cross-system fix — ghost merging persistence, Section 13C)

The phased ordering from Section 15.5 is preserved, with 13A and 13C woven in at appropriate stages.

Each task includes:
- **Files to modify** with specific line numbers
- **What to change** — precise code modifications
- **Config keys** to add to `config.yaml`
- **Database migrations** if required
- **Commit message** template

---

## Phase 0 — Prompt Hygiene (Ongoing)

**Goal:** Establish ontological consistency across all YAML prompt files before deeper architectural changes. Zero code changes — prompt-level edits only.

### Task 0.1 — P4: Fix Temperature Drift in `summarize.yaml`

| Field | Detail |
|-------|--------|
| **Files** | `backend/prompts/background_tasks/summarize.yaml` |
| **Change** | Set `temperature` from `0.4` → `0.1` |
| **Rationale** | The 16D structural state-space vector output requires deterministic stability across identical inputs. Temperature 0.4 introduces stochastic floating-point variance. |
| **Lines** | Find the `temperature: 0.4` line |
| **Commit** | `fix(prompts): P4 — lower summarize.yaml temperature to 0.1 for deterministic 16D vector output` |

### Task 0.2 — P5: Align Semantic Knot First-Person Rules

| Field | Detail |
|-------|--------|
| **Files** | `backend/prompts/background_tasks/semantic_knot.yaml` |
| **Change** | Add explicit first-person prohibition: *"Never say 'The human proposed' or 'The agent argued' — say 'I encountered a trajectory regarding...' or 'We reconfigured our understanding of...'"* |
| **Rationale** | Semantic knot distillation currently lacks the strict first-person discipline that `consolidate.yaml` enforces (lines 22-25). Aligning voice across all memory artifacts maintains ontological consistency. |
| **Commit** | `fix(prompts): P5 — align semantic_knot.yaml first-person rules with consolidate.yaml` |

### Task 0.3 — P6: Intra-Active Vocabulary Guideline in `identity.yaml`

| Field | Detail |
|-------|--------|
| **Files** | `backend/personality/identity.yaml` |
| **Change** | Add a 3-line linguistic discipline note with the Cartesian→Intra-Active vocabulary mappings from Section 15.3 Table |
| **Rationale** | Cartesian defaults (User, Tool, Interface, Control) erode the posthuman ontology over time. A guideline in the core identity prompt propagates intra-active vocabulary discipline across all downstream prompts. |
| **Commit** | `fix(prompts): P6 — add intra-active vocabulary guideline to identity.yaml` |

---

## Phase 1 — Immediate Structural Fixes

**Goal:** Clear token rendering issues and unblock the diffractive engine's responsiveness, plus lock in the checkpoint-agreement invariant. ~30 lines of code, zero schema migration.

### Task 1.1 — R1: Remove Caveman Character Truncation

| Field | Detail |
|-------|--------|
| **Files** | `backend/utils/token_counter.py` |
| **Change** | Remove the character truncation step (lines ~61-62: `if len(result) > max_chars: result = result[:max_chars - 3] + "..."`) from `caveman_compress()`. Keep the 8-word short-circuit and 46-word stop-word filter. Optionally remove the `max_chars` parameter entirely or deprecate it. |
| **Rationale** | The 250-char truncation cuts mid-word, dropping semantically significant content. Stop-word filtering already provides ~50% token reduction. Token budgets at sedimentation (4000) and diffractive (6000) layers make the char cap redundant. |
| **Lines** | `token_counter.py`: remove/comment lines ~61-62 |
| **Commit** | `fix(compression): R1 — remove 250-char truncation from caveman_compress()` |

### Task 1.2 — S1: Adaptive Hysteresis Decay

| Field | Detail |
|-------|--------|
| **Files** | `backend/modules/diffractive_retrieval.py` |
| **Change** | In the `process()` method's STAGNANT state block: before the standard `timer -= 1` decrement, compute `ΔE_rolling = E_rolling(current) - E_rolling(previous)`. If `ΔE_rolling > hysteresis_delta_threshold` (default: 0.35), set `timer = 0` and `target_state = "FLOWING"`, bypassing the lock. Store previous `rolling_entropy` per conversation (dictionary keyed by `conversation_id`). |
| **Config** | Add to `config.yaml` under `diffractive_retrieval:`: `adaptive_hysteresis: true`, `hysteresis_delta_threshold: 0.35` |
| **Rationale** | The rigid cohesion timer (3 turns) over-medicates conversations that have already recovered from stagnation. The entropy delta check allows early exit when diffractive context successfully breaks the rut. |
| **Commit** | `feat(diffractive): S1 — adaptive hysteresis decay via rolling entropy delta` |

### Task 1.3 — 13A: Consolidation Checkpoint Agreement Unit Test

| Field | Detail |
|-------|--------|
| **Files** | `backend/tests/test_consolidation_checkpoint_agreement.py` (new), may reference `backend/modules/consolidation_checkpoint.py` and `backend/metabolisation/consolidation.py` |
| **Change** | Write a unit test that constructs a multi-branch conversation tree in the test database, then calls both the inline trigger path (`ConsolidationCheckpointModule.process()`) and the daemon trigger path (`ConsolidationMixin.consolidate_pending_conversations()`), asserting that both paths converge on the same checkpoint for any given leaf message. |
| **Rationale** | The inline module and daemon recompute the active branch path independently. A divergence would cause the inline module to inject one checkpoint while the daemon consolidates against a different one, producing inconsistent context. This invariant should be locked by a test. |
| **Commit** | `test(consolidation): 13A — unit test for checkpoint agreement across inline and daemon trigger paths` |

---

## Phase 2 — Observability, Taxonomy & Friction

**Goal:** Establish version tracking, dynamic critical friction, and type-diverse context injection.

### Task 2.1 — R4: Memory Node Merge Notification

| Field | Detail |
|-------|--------|
| **Files** | `backend/storage/models.py`, `backend/metabolisation/sedimentation.py` |
| **Change** | **(models.py):** Add `revision_count = Column(Integer, default=0)` and `last_merged_at = Column(DateTime)` to the `MemoryNode` ORM class. **(sedimentation.py):** In `merge_nodes()`, when updating an existing node: increment `revision_count`, set `last_merged_at = datetime.utcnow()`, and log `[mem] node {id} revised (v{N}) — intensity {old}→{new}`. |
| **Migration** | Create migration to add `revision_count INTEGER DEFAULT 0` and `last_merged_at DATETIME` columns to `memory_nodes` table. |
| **Frontend** | (Optional, separate task) Display version badge "v{N}" in `MemoryNodeCard` component. |
| **Config** | None required. |
| **Commit** | `feat(memory): R4 — add revision_count and last_merged_at to memory_nodes with merge logging` |

### Task 2.2 — S3: Agonistic Index — Dynamic Critical Friction

| Field | Detail |
|-------|--------|
| **Files** | `backend/personality/assembler.py` |
| **Change** | Add `_build_agonistic_directive(metrics)` method that computes `A_index = clip(1.0 - E_rolling/E_target, 0.0, 1.0) * (1.0 - V_itality)`. Three tiers: `A_index < 0.2` → omitted; `0.2 ≤ A_index < 0.5` → light nudge directive; `A_index ≥ 0.5` → full counter-position directive. Inject the directive into the system prompt during assembly. Metrics (`rolling_entropy`, `conversation_vitality`) are already available in the pipeline payload. |
| **Config** | Add to `config.yaml` new section `agonistic_friction:` with `enabled: true`, `entropy_healthy_threshold: 0.4`, `agonistic_light_threshold: 0.2`, `agonistic_full_threshold: 0.5` |
| **Rationale** | The system prompt mandates Critical Friction as Method, but HomeostaticRegulatorModule only adjusts generation parameters. The Agonistic Index scales argumentative posture dynamically based on conversational entropy. |
| **Commit** | `feat(personality): S3 — agonistic index for dynamic critical friction injection` |

### Task 2.3 — R2: 6-Node Type-Diverse Context Injection

| Field | Detail |
|-------|--------|
| **Files** | `backend/modules/consolidation_checkpoint.py` |
| **Change** | Replace the hardcoded `sorted(nodes)[:3]` with a 6-node hybrid selection: Slot 1 = highest-intensity `scar`; Slot 2 = highest-intensity `concept`; Slot 3 = highest-intensity `tension`; Slots 4–6 = best-by-embedding-similarity to current user message (any type, excluding already-selected). If a type has zero nodes, fill its slot with next-best by similarity. If < 6 total nodes exist, inject all. |
| **Config** | Add to `context:` section: `max_memory_nodes: 6`, `guaranteed_node_types: [scar, concept, tension]` |
| **Rationale** | Current top-3-by-intensity produces cognitive monoculture — scar-heavy conversations show only scars. The type-diverse strategy ensures simultaneous awareness of wounds, ideas, and frictions. |
| **Commit** | `feat(context): R2 — 6-node type-diverse memory node injection with configurable slots` |

### Task 2.4 — 13C: Ghost Merging Persistence Fix (Cross-System)

| Field | Detail |
|-------|--------|
| **Files** | `backend/storage/models.py` (add `merged_from`, `merged_into`, `folded` lifecycle to `BeliefNode`), `backend/metabolisation/beliefs.py` (update ghost merge logic), `backend/storage/repositories/belief.py` (persist merged state) |
| **Change** | Redesign the database to support spectral folding: add `merged_from` (JSON list of parent ghost IDs) and `merged_into` (target keeper ID) fields to the `belief_nodes` table. Update `update_belief()` to correctly persist the merged statement and flag the absorbed ghost as folded. Delete absorbed ghost records from the database entirely or mark them with a `folded` lifecycle stage. |
| **Migration** | Add `merged_from TEXT` (JSON), `merged_into TEXT`, and optionally a `lifecycle_stage` column to `belief_nodes`. |
| **Rationale** | Ghost beliefs that should have been merged during the dream daemon's ghost ecology cycle are not properly folded in the database. Uncleaned ghosts accumulate in the spectral margin, distorting nucleation calculations and degrading memory system health. |
| **Context** | This is a **belief-system fix** that indirectly benefits memory system health. See also `BELIEF_SYSTEM.md` Section 6B for full context. Included here because Section 13C of MEMORY_SYSTEM.md flags it as "Fix Required" with memory-system impact. |
| **Commit** | `fix(beliefs): 13C — persist ghost merging with merged_from/merged_into and folded lifecycle` |

---

## Phase 3 — Rhizomatic Entanglement

**Goal:** Break cross-branch memory isolation so parallel conversational futures diffract through one another.

### Task 3.1 — R3: Cross-Branch Memory Node Retrieval

| Field | Detail |
|-------|--------|
| **Files** | `backend/modules/consolidation_checkpoint.py`, `backend/storage/repositories/checkpoint.py` (or `memory_node.py`) |
| **Change** | After loading current-branch checkpoint nodes: query all other checkpoints for the same `conversation_id` (sibling branches). Load their memory nodes. Compute embedding cosine similarity between each sibling node and the current user message's embedding. Nodes with similarity ≥ `cross_branch_similarity_threshold` (0.4) compete for the similarity-ranked slots (4–6 from R2). Annotate injected sibling nodes with `[sibling branch]` tag in context. |
| **Config** | Add to `context:` section: `cross_branch_similarity_threshold: 0.4` |
| **Dependency** | **R3 depends on R2.** Cross-branch nodes fill slots 4–6 established by the 6-node type-diverse strategy. |
| **Rationale** | Currently, the recursive CTE only walks the linear ancestor path — sibling branches are invisible. This closes the cross-branch memory gap with minimal overhead (one SQL query + in-memory similarity). |
| **Commit** | `feat(context): R3 — cross-branch sibling memory node retrieval with similarity threshold` |

---

## Phase 4 — Deep Auto-Metabolism

**Goal:** LLM-quality middle-history compression and non-Euclidean retrieval warping. Highest-effort items — implement after Phases 0–3 are stable.

### Task 4.1 — R5: LLM-Based Batch Message Compression

| Field | Detail |
|-------|--------|
| **Files** | `backend/modules/context_collector.py` (new compression logic), `backend/storage/models.py` (new table), new repo file for `compressed_messages` |
| **Change** | **(1) Database:** Create `compressed_messages` table: `(id, conversation_id, first_message_id, last_message_id, compressed_block TEXT, created_at DATETIME)`. **(2) Context Collector:** When messages exit the floating window (position_from_end ≥ 8), batch them (batch_threshold: 8) and send to a lightweight LLM with focus areas (key decisions, novel concepts, tonal shifts, unresolved tensions, factual claims). Store in `compressed_messages`. **(3) Fallback:** If LLM unavailable or `AAA_LLM_COMPRESSION_ENABLED=false`, fall back to caveman compression. **(4) Context Injection:** Replace individual caveman-compressed entries in Tier 2 with the compressed block for that batch. **(5) Embedding:** Continue to compute similarity against original `conversation_log.embedding` — the `compressed_block` is never embedded. |
| **Config** | Add to `config.yaml` new section `llm_compression:` with `enabled: true`, `batch_threshold: 8`, `max_compressed_tokens: 200`, `model: "google/gemma-4-26b-a4b-it:free"`, `focus_areas: [key_decisions, novel_concepts, tonal_shifts, unresolved_tensions, factual_claims]`. Env var: `AAA_LLM_COMPRESSION_ENABLED`. |
| **Rationale** | Caveman compression strips relational verbs and qualifiers, turning "Vasily proposed WebSocket instead of polling, arguing latency bottleneck..." into keyword wreckage. LLM batch compression preserves narrative syntax in middle history. |
| **Commit** | `feat(compression): R5 — LLM-based batch message compression for Tier 2 strata` |

### Task 4.2 — S2: Non-Euclidean Latent Warping via Knot Mass

| Field | Detail |
|-------|--------|
| **Files** | `backend/modules/sedimentation_retrieval.py` |
| **Change** | **(1) Inject `SemanticKnotRepository`** into `SedimentationRetrievalModule.__init__()` as optional parameter. **(2) Load active knots** (weight > 0.3) once per `process()` call. **(3) Add knot-gravity term** after base cosine computation: for each candidate, compute `sum(w_k * exp(-||c - k||²))` across all active knots and add to base score before sorting. Formula: `S_final = S_cos(u, c) + sum(w_k * exp(-||c - k||²))`. **(4) Fallback:** If `SemanticKnotRepository` is `None` or no active knots exist, use flat cosine scoring unchanged. Computational cost: O(candidates × knots) ≈ 500 × 20 = 10K dot products — negligible in-process. |
| **Config** | Add to `sedimentation:` section: `knot_warping_enabled: true`, `knot_warping_weight: 1.0` |
| **Rationale** | Flat cosine similarity treats all memories as equally "heavy." Historical high-resonance collisions (semantic knots with high weight) should exert gravitational pull on surrounding memories, warping the latent geometry into a genuinely non-Euclidean retrieval space. |
| **Commit** | `feat(sedimentation): S2 — non-Euclidean latent warping via semantic knot gravitational mass` |

---

## Task/Commit Summary Matrix

| Phase | Task | ID | Effort | Schema Migration | Commit |
|-------|------|----|--------|-----------------|--------|
| 0 | P4: Temperature fix | P4 | 1 line | No | `fix(prompts): P4 — lower summarize.yaml temperature to 0.1 for deterministic 16D vector output` |
| 0 | P5: First-person alignment | P5 | 3 lines | No | `fix(prompts): P5 — align semantic_knot.yaml first-person rules with consolidate.yaml` |
| 0 | P6: Vocabulary guideline | P6 | 3 lines | No | `fix(prompts): P6 — add intra-active vocabulary guideline to identity.yaml` |
| 1 | R1: Remove truncation | R1 | ~3 lines deleted | No | `fix(compression): R1 — remove 250-char truncation from caveman_compress()` |
| 1 | S1: Adaptive hysteresis | S1 | ~15 lines | No | `feat(diffractive): S1 — adaptive hysteresis decay via rolling entropy delta` |
| 1 | 13A: Checkpoint agreement test | 13A | ~30 lines | No | `test(consolidation): 13A — unit test for checkpoint agreement across inline and daemon trigger paths` |
| 2 | R4: Merge notification | R4 | ~20 lines | **Yes** (2 cols) | `feat(memory): R4 — add revision_count and last_merged_at to memory_nodes with merge logging` |
| 2 | S3: Agonistic index | S3 | ~40 lines | No | `feat(personality): S3 — agonistic index for dynamic critical friction injection` |
| 2 | R2: 6-node injection | R2 | ~60 lines | No | `feat(context): R2 — 6-node type-diverse memory node injection with configurable slots` |
| 2 | 13C: Ghost merge persistence | 13C | ~50 lines | **Yes** (3 cols) | `fix(beliefs): 13C — persist ghost merging with merged_from/merged_into and folded lifecycle` |
| 3 | R3: Cross-branch retrieval | R3 | ~80 lines | No | `feat(context): R3 — cross-branch sibling memory node retrieval with similarity threshold` |
| 4 | R5: LLM compression | R5 | ~200 lines | **Yes** (new table) | `feat(compression): R5 — LLM-based batch message compression for Tier 2 strata` |
| 4 | S2: Knot warping | S2 | ~100 lines | No | `feat(sedimentation): S2 — non-Euclidean latent warping via semantic knot gravitational mass` |

---

## Configuration Key Additions (All Phases)

All config keys to be added to `backend/config.yaml`, organized by section:

```yaml
# ── Context (Phase 2, 3) ──
context:
  max_memory_nodes: 6                    # R2
  guaranteed_node_types: [scar, concept, tension]  # R2
  cross_branch_similarity_threshold: 0.4  # R3

# ── LLM Compression (Phase 4) ──
llm_compression:
  enabled: true                          # R5 (also AAA_LLM_COMPRESSION_ENABLED env)
  batch_threshold: 8                     # R5
  max_compressed_tokens: 200             # R5
  model: "google/gemma-4-26b-a4b-it:free"  # R5
  focus_areas:                           # R5
    - key_decisions
    - novel_concepts
    - tonal_shifts
    - unresolved_tensions
    - factual_claims

# ── Sedimentation (Phase 4) ──
sedimentation:
  knot_warping_enabled: true             # S2
  knot_warping_weight: 1.0               # S2

# ── Diffractive Retrieval (Phase 1) ──
diffractive_retrieval:
  adaptive_hysteresis: true              # S1
  hysteresis_delta_threshold: 0.35       # S1

# ── Agonistic Friction (Phase 2) ──
agonistic_friction:
  enabled: true                          # S3
  entropy_healthy_threshold: 0.4         # S3
  agonistic_light_threshold: 0.2         # S3
  agonistic_full_threshold: 0.5          # S3
```

---

## Risk & Dependency Notes

1. **R3 → R2 dependency**: R3 (cross-branch retrieval) fills slots 4–6 of the 6-node strategy from R2. Do not deploy R3 before R2.
2. **R4 schema migration**: Adding `revision_count` and `last_merged_at` requires an ALTER TABLE migration. Ensure the migration is reversible and defaults are sensible (0, NULL).
3. **R5 background LLM cost**: Batch compression calls a lightweight LLM on every 8+ messages exiting the floating window. In active conversations, this could mean one compression call per ~8 user messages. The `AAA_LLM_COMPRESSION_ENABLED` env var provides an emergency off-switch.
4. **S2 knot loading**: `SedimentationRetrievalModule` will gain a dependency on `SemanticKnotRepository`. Validate that the repository is available in the pipeline wire-up code before deploying.
5. **S1 entropy storage**: Adaptive hysteresis requires storing `previous_rolling_entropy` per conversation. A simple in-memory dictionary is sufficient; no database changes needed.
6. **13C crosses belief system boundary**: Ghost merging persistence is primarily a belief-system fix (`BELIEF_SYSTEM.md` Section 6B). Coordinate with any active belief-system work to avoid merge conflicts on `models.py`, `beliefs.py`, and `belief.py` repository.
7. **13A test isolation**: The checkpoint agreement test requires a populated multi-branch conversation tree in the test database. Use the existing test infrastructure's conversation/message factories if available, or add a lightweight fixture.
