# Backend Refactoring & Optimization Report

**Date:** 2026-06-24
**Codebase:** D:\AAA\backend
**Review scope:** All backend Python code; focus on files >500 lines and documented practices

---

## Executive Summary

The AAA backend is a sophisticated system with ~200 Python files organized into clean domain boundaries (api/, services/, modules/, storage/, metabolisation/). The codebase follows the documented practices well in most areas (decoupled lifecycles, WAL mode, structured logging). The primary concerns center on:

1. **A single God Object** (research_orchestrator.py at 2,516 lines)
2. **Code duplication** between related subsystems
3. **Incomplete test coverage** for critical paths
4. **Orphaned `core/` directory** from the `metabolisation/` migration

---

## 1. Critical: `research_orchestrator.py` (2,516 lines) — God Object

### Current State
`SomaticResearchOrchestrator` handles ALL of the following in one class:

| Concern | Approx. lines | Description |
|---------|:---:|---|
| Task state management | ~200 L | `init_task`, `resume_task`, `ensure_state`, `_task_states` dict |
| Cache management | ~120 L | `_load_cache`, `_save_cache`, `_get_cached_phase`, column migration |
| Persona building | ~80 L | `_build_orchestrator_persona` — 6 sections via prompt utils |
| Preview/input generation | ~425 L | `preview_step_inputs` — one massive if-elif chain for 8 phases |
| Phase step execution | ~365 L | `execute_step` + `_step_plan/search/parse/digest/reflect/evaluate/synthesize` |
| Plan/synthesize LLM calls | ~200 L | `_phase_plan`, `_phase_synthesize` |
| Parallel tools | ~200 L | `_tool_parallel_parse_grouped`, `_tool_parallel_digest_grouped` |
| Source analysis | ~65 L | `_analyze_source` |
| Reflection | ~160 L | `_tool_reflect` |
| Evaluation | ~80 L | `_tool_evaluate` |
| Utilities | ~150 L | `_log_meta`, `_log_llm_response`, `_classify_source_status`, `_apply_unified_references`, state persistence |

### Proposed Refactoring

Split into focused classes by concern:

```
services/research/
├── orchestrator.py               # SomaticResearchOrchestrator (thin coordinator, ~200 L)
├── task_state.py                 # TaskStateManager (init, resume, persist, load)
├── cache_manager.py              # CacheManager (cached_inputs read/write)
├── phase_planner.py              # PlanPhase (planning LLM call + persona context)
├── phase_searcher.py             # SearchPhase (parallel DDG + direct URL queue)
├── phase_parser.py               # ParsePhase (parallel fetch + dedup + archive)
├── phase_digester.py             # DigestPhase (parallel LLM analysis of sources)
├── phase_reflector.py            # ReflectPhase (multi-round LLM reflection)
├── phase_evaluator.py            # EvaluatePhase (hard checks + borderline LLM)
├── phase_synthesizer.py          # SynthesizePhase (final report)
├── preview_builder.py            # PreviewBuilder (preview_step_inputs per phase)
└── persona_builder.py            # ResearchPersonaBuilder (shared with somatic_research.py)
```

**Safety net:** Each extracted class gets its own unit test. The orchestrator is tested via integration tests for the full pipeline flow.

---

## 2. HIGH: Duplicate `core/` ↔ `metabolisation/` Directories

### Current State
Per `BACKEND_BEST_PRACTICES.md` line 117: `metabolisation/` **replaced** `core/`. Yet both directories exist with overlapping files:

| core/ | metabolisation/ | Imports used |
|-------|-----------------|-------------|
| `consolidation.py` | `consolidation.py` | `metabolisation.daemon` imports `ConsolidationMixin` from `metabolisation/` |
| `daemon.py` | `daemon.py` (737 L, active) | Service daemon uses `metabolisation.daemon` |
| `dream_context.py` | `dream_context.py` | Active code in `metabolisation/` |
| `dream_executor.py` | `dream_executor.py` | Active code in `metabolisation/` |
| `dream_prompts.py` | `dream_prompts.py` | Active code in `metabolisation/` |
| `mass_decay.py` | `mass_decay.py` | Active code in `metabolisation/` |
| `sedimentation.py` | `sedimentation.py` | Active code in `metabolisation/` |

### Action

1. **Verify** which version of each `core/` file is actually imported anywhere (grep all imports)
2. **Delete** `core/` files that have zero importers, OR
3. **Create deprecation aliases** in `core/` that re-export from `metabolisation/` with `DeprecationWarning` per the Stratal Migration doc (line 124-127)
4. **Run full test suite** after each deletion to confirm no breakage

---

## 3. HIGH: Overlap Between `SomaticResearchOrchestrator` and `SomaticResearchEngine`

### Current State
Two classes handle autonomous research with significant overlap:

| Pattern | `SomaticResearchOrchestrator` (2,516 L) | `SomaticResearchEngine` (593 L) |
|---------|------------------------------------------|----------------------------------|
| Approach | Multi-phase pipeline (plan→search→...→synthesize) | Recursive tree traversal |
| Persona building | `_build_orchestrator_persona()` | Own persona via `ResearchContextBuilder` |
| Meta logging | `_log_meta()`, `_log_llm_response()` | `_log_meta()` (identical structure) |
| Semaphore | `_get_semaphore()` via `max_concurrent` config | `_get_semaphore()` via `max_concurrent_probes` |
| Repo access | 7+ repo properties | 4+ repo properties |
| Config access | `self._state.config.get("research_orchestrator", {})` | `self._state.config.get("rhizome_research", {})` |

### Action
- Extract shared `_log_meta` and `_get_semaphore` patterns into a `BaseResearchEngine` mixin or utility class
- Determine if `SomaticResearchEngine` is still used (it may be legacy from before the orchestrator was built). If unused, mark as deprecated/remove

---

## 4. HIGH: `modules/belief_engine.py` (1,120 lines) — Mixed Concerns

### Current State
`BeliefDynamicsEngine` mixes:
- **Pipeline processing** (`process()` — attractor window, spectral margin, somatic state, tension field)
- **Core math** (`_compute_lifecycle_stage`, `_accrete_belief` — mass/confidence/plasticity formulas)
- **Database operations** (via `belief_repo` — create proposals, update beliefs, insert events)
- **LLM calls** (via `_ensure_signature` — fallback structural scoring)
- **Somatic vitality monitoring** (immune triggers, warping, reservoir management)
- **Multiple metabolism paths** (`metabolize`, `metabolize_perception`, `metabolize_note`, `metabolize_web`, `metabolize_conversational_pattern`) — all share the same "find closest belief → accrete or nucleate" pattern

### Proposed Split
```
modules/
├── belief_engine.py                 # ~300 L — Pipeline integration + delegation only
├── belief_math.py                   # ~200 L — Pure math: lifecycle stages, accretion formulas, cohesion, atrophy
├── belief_metabolizer.py           # ~300 L — All metabolize_* pathway implementations
├── belief_somatic.py               # ~200 L — Somatic vitality, immune triggers, coordinate warping
└── belief_ecosystem.py             # ~150 L — Ecosystem health, tension field, tuning
```

---

## 5. MEDIUM: `services/belief.py` (1,036 lines) — Data Transformation Overload

The `BeliefService` does extensive data transformation (serializing belief/proposal/event data into API dicts). It also handles proposal lifecycle operations (adopt, reject, merge, refine). Consider:

- Extract data formatting into `BeliefPresenter` or `BeliefSerializer` (separation of concerns)
- The `get_beliefs` method (lines 28-179, ~150 L) builds a deeply nested response dict — extract formatting
- Repeated `json.loads(source_trace)` / `isoformat()` patterns should be extracted into helper methods

---

## 6. MEDIUM: `modules/llm_client.py` (817 lines) — Provider Multiplexing

### Current State
- `BaseLLMProvider` (abstract) → `OpenAICompatibleProvider` → `OpenRouterProvider`
- Standalone `generate_unified()` function
- `KeyManager` for API key rotation
- Anthropic/OpenAI/Google/OpenRouter API format differences handled inline
- Thinking/reasoning parameter management scattered across `generate()` and `_request_with_retry()`

### Proposed Improvements
- Extract Anthropic format conversion into a dedicated adapter class (not inline in `generate()`)
- Extract thinking/reasoning parameter logic into a `ThinkingConfig` builder
- Consider splitting into: `providers/openai_compatible.py`, `providers/anthropic.py`, `providers/openrouter.py`
- The `_parse_message` method (handling finish_reason, truncated detection) is important logic — keep it tested

---

## 7. MEDIUM: Inconsistent Database Access Patterns

### Issues Found
1. **`_get_or_create_default_branch()`** in `research_orchestrator.py:335` accesses raw DB connection via `self.branch_repo._conn()` — breaks repository encapsulation
2. Some services access repos via `getattr(state, "x_repo", None)` pattern (defensive), while others assume they exist — inconsistent
3. `@with_connection` is used correctly on repository methods, but `research_orchestrator.py:336-343` creates a raw SQLite connection bypassing the connection tracker

### Action
- Add a proper `branch_repo.ensure_conversation_exists()` method
- Standardize repo access patterns across services (use dependency injection via `__init__` rather than `getattr(state, ...)` lookup)

---

## 8. MEDIUM: `metabolisation/daemon.py` (737 lines) — Mixin-Heavy Class

`AutopoieticDreamDaemon` inherits from 7 mixins:
```python
class AutopoieticDreamDaemon(
    MassDecayMixin, DreamContextMixin, DreamPromptMixin,
    DreamExecutorMixin, ConsolidationMixin, SkillMetabolismMixin,
    DreamResearchMixin,
):
```

This is a Diamond Problem risk. While mixins are appropriate for capability composition, verify:
- No method name collisions between mixins
- The `__init__` in `daemon.py` correctly initializes all needed attributes for all mixins
- Consider documenting the mixin dependency graph

---

## 9. MEDIUM: Inline Imports Throughout the Codebase

Multiple modules use inline imports inside functions to avoid circular dependencies:

| File | Line | Import |
|------|------|--------|
| `belief_engine.py` | 477 | `from backend.utils.prompt_builder import build_attractor_window` |
| `belief_engine.py` | 647 | `from backend.storage.repositories.refusal import RefusalRepository` |
| `services/belief.py` | 268-270 | `import uuid; import json; from backend.modules.structural_engine import CompositeStructuralScorer` |
| `services/chat.py` | 36-38, 186, 271 | Various inline imports |
| `research_orchestrator.py` | 151, 628, etc. | Multiple inline imports |

**Action:** Create a `backend/dependency_coordinator.py` or use a lazy-loading pattern to systematically break circular imports without inline function-level imports.

---

## 10. Test Coverage Gaps

### Current Test Files (40 files)

### Missing Tests for Critical Modules

| Module | Size | Has test? | Risk |
|--------|------|:---:|------|
| `services/research_orchestrator.py` | 2,516 L | **NO** | HIGH — core research pipeline |
| `services/somatic_research.py` | 593 L | **NO** | HIGH — legacy research engine |
| `services/chat.py` | 551 L | Partial (`test_decoupled_chat.py`) | MEDIUM |
| `services/belief.py` | 1,036 L | Partial (`test_belief_metabolism.py`) | MEDIUM |
| `modules/llm_client.py` | 817 L | Partial (`test_step3_llm.py`) | MEDIUM |
| `modules/perception.py` | 735 L | Partial (`test_perception_extensions.py`) | MEDIUM |
| `personality/assembler.py` | 626 L | **NO** | MEDIUM |
| `workers/digest_worker.py` | 625 L | **NO** | MEDIUM |

### Recommended Tests to Add

1. **`tests/test_research_orchestrator.py`** — Phase transitions, state persistence, preview building
2. **`tests/test_somatic_research.py`** — Recursive traversal, lateral flight, branch management
3. **`tests/test_belief_engine_isolation.py`** — Pure math functions (lifecycle stages, accretion formulas)
4. **`tests/test_llm_client_provider.py`** — Rate limiting, retries, thinking parameter handling
5. **`tests/test_personality_assembler.py`** — Prompt assembly with mocked repos
6. **`tests/test_digest_worker.py`** — File processing and summarization (mocked embedder/LLM)

---

## 11. Opportunities for Code Reuse

### 11.1 `compute_cosine_similarity` duplicated
Defined in THREE places:
- `backend/utils/similarity.py` (canonical version)
- `backend/modules/belief_engine.py:36-42` (wrapper with dimension check)
- `backend/metabolisation/daemon.py:27-32` (identical wrapper)

**Action:** Make the `utils/similarity.py` version handle dimension checking and remove the wrappers.

### 11.2 Meta-logging duplicated
Both `SomaticResearchOrchestrator._log_meta()` and `SomaticResearchEngine._log_meta()` have nearly identical implementations (~15 lines each).

**Action:** Extract to `backend/utils/research_logger.py`.

### 11.3 Reflection formatting duplicated
The reflection dict → formatted markdown pattern appears in 3+ places:
- `preview_step_inputs` (reflecting phase, line 750-762)
- `preview_step_inputs` (synthesizing phase, line 878-891)
- `_tool_reflect` (line 2278-2291)
- `_phase_synthesize` (line 1803-1815)

**Action:** Extract to `_format_reflection_markdown(reflection, depth)` shared utility.

### 11.4 Parsed URL list construction duplicated
Building `parsed_urls_list` from `step_result_repo.get_by_task()` appears in 4 places:
- `preview_step_inputs:reflecting` (line 668-682)
- `preview_step_inputs:synthesizing` (line 853-867)
- `_tool_reflect` (line 2200-2214)
- `_phase_synthesize` (line 1772-1786)

**Action:** Extract to `_get_parsed_urls(task_id)` helper.

---

## 12. Configuration Inconsistencies

Two different config keys for research settings:
- `research_orchestrator` (for `SomaticResearchOrchestrator`)
- `rhizome_research` (for `SomaticResearchEngine`)

These have overlapping settings (`max_concurrent`, semaphore limits). Consider merging into a single `research` config section with sub-sections.

---

## Implementation Plan

### Phase 1: Safety Net (Week 1)
1. Add missing tests for `research_orchestrator.py` (phase transitions, state persistence)
2. Add unit tests for pure math functions in `belief_engine.py`
3. Add tests for `llm_client.py` retry/rate-limit logic
4. Run full test suite to establish baseline

### Phase 2: Quick Wins (Week 1-2)
1. Remove duplicate `compute_cosine_similarity` wrappers → use `utils/similarity.py`
2. Extract shared `_log_meta` into `utils/research_logger.py`
3. Extract shared `_format_reflection_markdown` helper
4. Extract shared `_get_parsed_urls` helper
5. Verify `core/` vs `metabolisation/` imports → delete orphans or add deprecation stubs
6. Move inline imports to module-level with `TYPE_CHECKING` pattern

### Phase 3: Structural Decomposition (Week 2-3)
1. Split `research_orchestrator.py` into phase-specific classes (~9 files)
2. Split `belief_engine.py` into `belief_math.py`, `belief_somatic.py`, `belief_metabolizer.py`, `belief_ecosystem.py`
3. Extract `BaseResearchEngine` for shared orchestration patterns

### Phase 4: Quality & Documentation (Week 3)
1. Standardize repo access patterns across services
2. Clean up `core/` directory fully (deprecation stubs → removal)
3. Add ADR for the refactoring decisions
4. Final integration test run

---

## Testing Strategy for Refactoring

1. **Before ANY split:** Write characterization tests that capture current behavior (input/output)
2. **During extraction:** Run existing tests after each extraction to catch regressions
3. **After extraction:** Run full test suite (`uv run pytest backend/tests/`)
4. **Per-file approach:** Never refactor two files at once; each extraction is its own commit
5. **Use `git stash`/`git checkout` liberally** to revert partial refactors
6. **Test DB isolation:** `conftest.py` already forces `data/aaa_test.db` — confirm this is working before major refactors

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|:----------:|:------:|------------|
| Breaking research pipeline during orchestrator split | Medium | High | Characterization tests first; feature-flag new code path |
| Circular import issues from extraction | Medium | Medium | `TYPE_CHECKING` pattern; dependency coordinator |
| Stale `core/` code still referenced | Medium | Medium | `rg "from backend.core"` check before deletion |
| Regressions in belief mass/confidence math | Low | High | Pure functions are easiest to test; add property-based tests |
| Daemon mixin conflicts | Low | Medium | Audit method names across all 7 mixins |
