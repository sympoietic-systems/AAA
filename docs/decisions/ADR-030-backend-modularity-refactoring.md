# ADR-030: Backend Modularity Refactoring

**Date:** 2026-06-07
**Status:** accepted
**Deciders:** Interlocutor

## Context

The backend had accumulated technical debt common in rapidly-developed systems:

| File | Lines | Problem |
|------|-------|---------|
| `storage/repository.py` | 2,517 | 14 repository classes + helpers in one file |
| `api/routes.py` | 2,003 | 35+ endpoints with inline business logic |
| `core/daemon.py` | 1,523 | All dreamer logic in one file |
| `storage/database.py` | 659 | 580-line monolithic `init_db()` with 15 cumulative try/except migrations |
| `main.py` | 663 | Single 370-line `lifespan()` wiring everything |

Additional code quality issues:
- 10 repositories copy-pasted identical `__init__` and `_conn()` boilerplate (~100 lines of duplication)
- Route handlers contained business logic (belief computation, structural scoring, title generation, semantic knot compaction)
- Two near-duplicate LLM provider factory functions in `main.py` (80% overlap)
- 42 `getattr(state, "x_repo", None)` occurrences across 14 files
- All `__init__.py` files were empty (no public API surfaces)
- Duplicate `cosine_similarity()` in `belief_engine.py` and `diffractive_retrieval.py`
- `"backend/data/uploads/"` hardcoded in 5 separate files
- Unreachable dead code: `_store_daemon_metrics` function body after `return ""` in `_extract_human_summary` (would cause `NameError` if daemon metrics path was reached)

## Decision

Execute a 7-phase decomposition following the proven frontend refactoring pattern (SidePanel: 2,300 → 377 lines + 14 sub-components):

### Phase 1: Split `repository.py`
- Extract `ConnectionTracker`/`with_connection` → `storage/connection.py`
- Extract all `_row_to_*` functions → `storage/row_mappers.py`
- One repository per file in `storage/repositories/` (10 files)
- Create `BaseRepository` ABC to eliminate duplicate `__init__`/`_conn()` (~100 lines saved)
- `repository.py` retained as backward-compat re-export shim

### Phase 2: Split `routes.py`
- One route file per domain in `api/routes/` (21 files)
- Routes become thin — parse requests, call services, return responses

### Phase 3: Extract Services Layer
- 13 service classes in `backend/services/`:
  `ChatService`, `BeliefService`, `ConversationService`, `FileService`,
  `MetricsService`, `NoteService`, `SedimentService`, `TitleService`,
  `SemanticKnotService`, `ConsolidationService`, `DaemonService`,
  `HealthService`, `SkillService`
- Route handlers now delegate to service methods (routes average ~30 lines)

### Phase 4: Refactor `main.py` Lifespan
- Break 370-line lifespan into 12 focused factory functions
- Merge 2 duplicate provider factories into 1
- Result: `main.py` 663 → 516 lines with clear orchestration

### Phase 5: Extract Database Migrations
- Replace monolithic `init_db()` with `MigrationRunner` + 15 numbered migration files
- Each migration has `up(conn)` function; runner tracks applied migrations in `_migrations` table
- `database.py`: 659 → 57 lines

### Phase 6: Standardize `__init__.py` Public APIs
- 7 packages populated with re-exports
- Enables clean imports: `from backend.storage import MessageRepository, BeliefNode`

### Phase 7: Typed `AppState` Container
- Replace `getattr(state, "x", None)` with typed dataclass in `core/app_state.py`

### Post-refactoring Polish
- Fix `_store_daemon_metrics` dead code (critical runtime bug)
- Deduplicate `cosine_similarity()` → shared `utils/similarity.py`
- Create `utils/filesystem.py` with `UPLOAD_DIR`, `get_upload_path()`, `ensure_upload_dir()`, `to_utc()`
- Extract `_register_skills()` from `main.py` → `app_factory/__init__.py`
- Fix 58 inline imports (module-level instead of inside functions)
- Populate empty `__init__.py` for `background_tasks/actions/`

## Consequences

**Positive:**
- Largest file: 2,517 → 573 lines (78% reduction)
- `database.py`: 659 → 57 lines (91% reduction)
- Files increased from 95 to 168 — each with clear single responsibility
- Repository boilerplate eliminated via `BaseRepository`
- Two duplicate provider factories consolidated to one
- Service layer provides natural extension points for future features (e.g., dynamic skills)
- Migration system enables idempotent, tracked, numbered migrations
- All old import paths work via backward-compat shims
- Zero test regressions (22 pass / 33 pre-existing env failures identical to baseline)
- Backend starts correctly with all 13 pipeline modules, 15 migrations, 5 background actions, daemon, and scheduler

**Architecture after refactoring:**
```
backend/
├── api/           routes/ (20 domain files) + schemas + helpers
├── services/      13 service classes
├── storage/       repositories/ (10 files) + migrations/ (15 files)
├── core/          pipeline, daemon, scheduler, AppState
├── app_factory/   skill registration factory
├── modules/       13 processing modules
├── utils/         similarity, filesystem, token_counter
└── main.py        slim 516-line factory-orchestrated startup
```

**Negative:**
- More files to navigate (168 vs. 95) — mitigated by consistent patterns and re-exports
- Import path changes require awareness (mitigated by backward-compat shims)

## Alternatives Considered

- **Option 1: Do nothing** — Technical debt would compound as dynamic skills, belief extensions, and new modules are added. The frontend just completed the same journey successfully.
- **Option 2: Refactor after dynamic skills** — Would make the skill system harder to implement on a monolithic backend and require deeper changes later.
- **Option 3: Full rewrite** — Unnecessary; the code is well-structured, just poorly organized. Decomposition preserves all logic and API contracts.
