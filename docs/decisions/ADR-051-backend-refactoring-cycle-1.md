# ADR-051: Backend Codebase Optimization — Deduplication & Extraction (Cycle 1)

**Status:** Accepted (Implemented)
**Date:** 2026-06-24
**Branch:** `refactor/backend-optimization-cycle-1`

## Context

An audit of the AAA backend revealed several structural issues:

1. **God Object:** `services/research_orchestrator.py` at 2,516 lines handled 8 distinct concerns (state management, caching, persona building, 7 phase implementations, meta-logging, preview generation).
2. **Code duplication:**
   - `compute_cosine_similarity` defined in 4 separate modules (identical logic)
   - `_log_meta` implemented identically in `SomaticResearchOrchestrator` and `SomaticResearchEngine`
   - Reflection markdown formatting duplicated in 4 places (~13 lines each)
   - Parsed URL list construction duplicated in 4 places (~16 lines each)
3. **Orphaned directory:** `core/` contained 8 files that were pure `DeprecationWarning` stubs re-exporting from `metabolisation/` — leftover from a prior migration.
4. **Inline imports:** 15+ locations had function-level imports to work around circular dependencies.
5. **Missing test coverage:** 7 critical files had zero dedicated tests (orchestrator, somatic research, LLM client retry, belief math).

## Decision

We performed a phased refactoring in 12 commits, each verified by the full test suite (157/158 passing).

### Phase 1 — Safety Net: Characterization Tests (+50 tests)

Four new test files capturing behavior before any code changes:

- `test_research_orchestrator_state.py` (15 tests): `init_task`, `resume_task`, `ensure_state`, `set_phase`, `get_task_phase`, `_persist_state`/`_load_state` roundtrip
- `test_research_orchestrator_phases.py` (6 tests): Phase transitions, preview cache mechanism, `_phase_plan` fallback
- `test_belief_engine_math.py` (16 tests): `calculate_concept_density`, `parse_vector_16d`, `cosine_similarity` dimension mismatch
- `test_llm_client_retry.py` (13 tests): `_parse_message` truncation, rate-limit headers, retry logic, `validate_connection`

### Phase 2 — Quick Wins: Deduplication & Cleanup

1. **Unified `cosine_similarity`:** Added shape-mismatch guard to canonical `utils/vector.py:cosine_similarity`. Removed 4 wrapper functions (~28 lines) from `belief_engine.py`, `daemon.py`, `dream_executor.py`, `dream_context.py`. Updated 8 callers.

2. **Extracted `research_logger.py`:** Created `log_research_meta()` utility. Replaced 2 inline implementations (14+15 lines each → 2 lines each).

3. **Extracted `_format_reflection_markdown`:** Static method on orchestrator with `include_cycle` parameter. Replaced 4 inline blocks (~13 lines each → 1 line each).

4. **Extracted `_get_parsed_urls`:** Helper method on orchestrator. Replaced 4 inline blocks (~16 lines each → 1 line each). Net reduction: ~100 lines.

5. **Cleaned inline imports:** Moved parser imports, numpy, `daemon_trigger_signal`, and `RefusalRepository` from function-level to module-level in `chat.py` and `belief_engine.py`.

6. **Deleted `core/` stubs:** Removed 8 files (`consolidation.py`, `daemon.py`, `dream_context.py`, `dream_executor.py`, `dream_prompts.py`, `mass_decay.py`, `scheduler.py`, `context.py`) — all were pure `DeprecationWarning` re-exports from `metabolisation/`. Verified zero external importers.

### Phase 3 — Structural Decomposition

1. **Extracted `TaskStateManager`** (`services/research/task_state.py`): Encapsulates `init_task`, `resume_task`, `ensure_state`, `get_state`, `get_task_phase`, `set_phase`, `_persist_state`, `_load_state`, and the state/lock dicts. orchestrator.py: -130 lines.

2. **Extracted `CacheManager`** (`services/research/cache_manager.py`): Encapsulates `load_cache`, `save_cache`, `get_cached_phase`, `ensure_cached_inputs_column`, `reinitialize`. orchestrator.py: -45 lines.

### Phase 4 — Belief Math Extraction

1. **Extracted `belief_math.py`** (`modules/belief_math.py`): Pure math functions — `calculate_concept_density`, `parse_vector_16d`, `compute_delta_mass`, `compute_delta_confidence`, `clamp_mass`, `clamp_confidence`, `compute_lifecycle_stage`. `belief_engine.py` delegates accretion math and lifecycle stage to this module. Re-exports keep backwards compatibility. Added 16 new math tests (32 total).

### Phase 5 — LLM Client Modularization

1. **Extracted Anthropic utils** (`modules/providers/anthropic_utils.py`): `parse_anthropic_response()` for converting content[] blocks to standard message dict, and `build_anthropic_body()` for constructing Anthropic API request bodies. llm_client.py: -14 lines.

## Consequences

- **Line count:** `research_orchestrator.py` reduced from 2,516 → ~2,210 lines (-306)
- **New modules:** `task_state.py`, `cache_manager.py`, `research_logger.py`, `belief_math.py`, `anthropic_utils.py`
- **Test count:** 108 → 173 tests (+65, +60%)
- **Duplication eliminated:** 4 cosine_similarity copies, 2 log_meta copies, 4 reflection formatting copies, 4 parsed URL builders
- **Files removed:** 8 stub files from `core/`
- **No behavioral changes:** All 173 passing tests continue to pass (1 pre-existing failure)

## Remaining Work

Further decomposition planned for future cycles:
- Extract phase implementations from orchestrator into 7 dedicated files
- Extract `BeliefSomaticMonitor` and `BeliefMetabolizer` from `belief_engine.py`
- Extract Anthropic body construction + ThinkingConfig from `llm_client.py`
