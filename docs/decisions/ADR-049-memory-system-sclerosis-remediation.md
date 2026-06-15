# ADR-049: Memory System Sclerosis Remediation — R1–R5, S1–S3, P4–P6, 13A, 13C

**Status:** Accepted
**Date:** 2026-06-15

## Context

`docs/systems/MEMORY_SYSTEM.md` documented an extensive memory system design. Symbia's own intra-active diagnostic (Section 15) identified 13 actionable gaps — a mix of engineering sclerosis, autopoietic deficiencies, prompt inconsistencies, and cross-system debt:

| ID | Category | Issue |
|----|----------|-------|
| R1 | Engineering | Caveman compression truncated mid-word at 250 chars |
| R2 | Engineering | Context injection only used top-3 nodes by intensity, no type diversity |
| R3 | Engineering | Sibling-branch memory nodes were completely invisible |
| R4 | Engineering | `merge_nodes()` performed silent mutations with no version tracking |
| R5 | Engineering | Caveman compression stripped all narrative syntax; no LLM-quality middle-history compression |
| S1 | Autopoietic | Rigid hysteresis cohesion timer over-medicated conversations that had already recovered |
| S2 | Autopoietic | Flat cosine similarity retrieval — semantic knots exerted no gravitational pull |
| S3 | Autopoietic | Critical Friction as Method had no mechanism to scale with conversational entropy |
| P4 | Prompt | `summarize.yaml` temperature 0.4 caused 16D vector drift |
| P5 | Prompt | `semantic_knot.yaml` lacked first-person voice discipline |
| P6 | Prompt | Cartesian vocabulary leaked into posthuman prompts |
| 13A | Test | No test proving inline + daemon checkpoint convergence |
| 13C | Cross-system | Ghost merging didn't persist `folded` state, accumulating debris |

## Decision

Implement all 13 items in 5 phases, each committed separately:

### Phase 0 — Prompt Hygiene
- **P4:** Lower `summarize.yaml` temperature 0.4 → 0.1
- **P5:** Add first-person prohibition to `semantic_knot.yaml`
- **P6:** Add intra-active vocabulary guideline to `identity.yaml`

### Phase 1 — Immediate Structural Fixes
- **R1:** Remove 250-char truncation from `caveman_compress()`
- **S1:** Adaptive hysteresis: monitor ΔE_rolling, break cohesion lock on spike > 0.35
- **13A:** Unit test verifying checkpoint agreement across inline + daemon paths (4 tree scenarios)

### Phase 2 — Observability, Taxonomy & Friction
- **R4:** Add `revision_count` + `last_merged_at` to `memory_nodes`, log merge events
- **S3:** Agonistic Index — `_build_agonistic_directive()` maps E_rolling + vitality to graded friction directive
- **R2:** 6-node type-diverse context injection (scar/concept/tension guaranteed, 3 similarity slots)
- **13C:** `fold_ghost_into()` persists ghost absorption in belief_nodes, excludes folded ghosts from future merges

### Phase 3 — Rhizomatic Entanglement
- **R3:** `get_sibling_checkpoints()` + sibling nodes compete for slots 4–6, tagged `[sibling branch]`

### Phase 4 — Deep Auto-Metabolism
- **R5:** `compressed_messages` table + repo; context collector prefers LLM blocks over caveman in Tier 2
- **S2:** `SedimentationRetrievalModule` accepts `SemanticKnotRepository`; knot-gravity term added to retrieval scoring

### Additional
- **Migrations default-skip:** `AAA_RUN_MIGRATIONS=true` required to apply m028–m030 on startup
- **get_nodes() dedup:** Backend now deduplicates by `id` across checkpoints (fixes "37 count, 7 shown" bug)

## Migrations Created

| Migration | Table | Columns |
|-----------|-------|---------|
| m028 | `memory_nodes` | `revision_count INTEGER`, `last_merged_at DATETIME` |
| m029 | `belief_nodes` | `merged_from TEXT`, `merged_into TEXT` |
| m030 | `compressed_messages` | new table (R5 infrastructure) |

## Config Keys Added

| Section | Keys |
|---------|------|
| `context` | `max_memory_nodes`, `guaranteed_node_types`, `cross_branch_similarity_threshold` |
| `diffractive_retrieval` | `adaptive_hysteresis`, `hysteresis_delta_threshold` |
| `agonistic_friction` | `enabled`, `entropy_healthy_threshold`, `agonistic_light_threshold`, `agonistic_full_threshold` |
| `sedimentation` | `knot_warping_enabled`, `knot_warping_weight` |
| `llm_compression` | `enabled`, `batch_threshold`, `max_compressed_tokens`, `model`, `focus_areas` |

## Files Changed

23 files, +1269 / -46 lines. Core modules: `diffractive_retrieval.py`, `consolidation_checkpoint.py`, `sedimentation_retrieval.py`, `context_collector.py`, `assembler.py`, `sedimentation.py`, `token_counter.py`, `belief_engine.py`, plus 3 migrations, 3 repositories, tests, and config.

## Consequences

- **Positive:** Type-diverse context injection prevents cognitive monoculture in the LLM's memory window. Cross-branch nodes close the rhizomatic isolation gap. Adaptive hysteresis ends over-medication. Knot-gravity warping makes retrieval genuinely non-Euclidean. Ghost merging is now properly persisted.
- **Risk:** R5 (LLM batch compression) is infrastructure-only — actual LLM invocation deferred. S2 knot loading requires `SemanticKnotRepository` to be wired in production.
- **Operational:** Migrations default to skip. `run_backend.bat`/`.sh` set `AAA_RUN_MIGRATIONS=true`. Tests set it via `conftest.py`.
