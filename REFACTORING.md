# Backend Refactoring

**Branch**: `refactor/backend-modularity` → merged to `main`
**Date**: 2026-06-07
**Status**: Complete

---

## Results

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| Largest single file | 2,517 lines (`repository.py`) | 573 lines (`perception_sediment.py`) | -78% |
| `database.py` | 659 lines | 57 lines | -91% |
| `main.py` | 663 lines | 516 lines | -22% |
| Backend files | 95 | 168 | +73 files, each single-responsibility |
| Duplicate `__init__`/`_conn()` | 10x copy-paste | Eliminated via `BaseRepository` | -100 lines |
| Duplicate provider factories | 2 (80% overlap) | 1 | Consolidated |
| `__init__.py` with re-exports | 0 | 7 packages | Enables single-line imports |
| Duplicate `cosine_similarity()` | 2 files | 1 shared utility | DRY |
| Inline imports inside functions | 58 | 0 | Module-level imports |
| Hardcoded upload paths | 5 files | 1 constant | Centralized |
| Route handler business logic | Inline | Delegated to 13 services | Thin routes |
| Test regressions | — | 0 | 22 pass / 33 pre-existing env failures |
| Backend starts | ✓ | ✓ | All 15 migrations, 13 pipeline modules, 5 background actions verified |

## Final Architecture

```
backend/
├── api/
│   ├── __init__.py           # Schema re-exports
│   ├── schemas.py            # Pydantic models
│   ├── router.py             # Main router (includes all sub-routers)
│   ├── deps.py               # verify_password, shared dependencies
│   ├── helpers.py            # _parse_chat_request, _insert_system_message, _build_response_attachments
│   └── routes/               # 20 domain route files (one per endpoint group)
│       ├── __init__.py       # Backward-compat service re-exports
│       ├── chat.py           # POST /chat (36 lines)
│       ├── beliefs.py        # GET /beliefs
│       ├── conversations.py  # CRUD + title generation
│       ├── files.py          # Upload/download/delete/reprocess/summary
│       ├── history.py        # GET /history, messages/{id}/thinking, messages/{id}/context
│       ├── metrics.py        # GET /metrics
│       ├── notes.py          # Note CRUD + metabolism
│       ├── sediment.py       # Sediment injection endpoints
│       ├── tags.py           # Tag management
│       └── ... (10 more)
├── services/                 # Business logic layer
│   ├── __init__.py           # Re-exports all services
│   ├── chat.py               # ChatService — pipeline orchestration
│   ├── belief.py             # BeliefService
│   ├── conversation.py       # ConversationService
│   ├── file.py               # FileService
│   ├── metrics.py            # MetricsService
│   ├── note.py               # NoteService
│   ├── sediment.py           # SedimentService
│   ├── title.py              # TitleService
│   ├── semantic_knot.py      # SemanticKnotService
│   ├── consolidation.py      # ConsolidationService
│   ├── daemon.py             # DaemonService
│   ├── health.py             # HealthService
│   └── skill.py              # SkillService
├── storage/
│   ├── __init__.py           # Model + repository re-exports
│   ├── models.py             # All dataclasses
│   ├── database.py           # get_db_path, get_connection, init_db (57 lines)
│   ├── connection.py         # ConnectionTracker, with_connection, _get_tracked_connection
│   ├── row_mappers.py        # All _row_to_* functions
│   ├── repositories/
│   │   ├── __init__.py       # Re-exports with __all__
│   │   ├── base.py           # BaseRepository (eliminates boilerplate)
│   │   ├── belief.py
│   │   ├── consolidation.py
│   │   ├── conversation.py
│   │   ├── error_log.py
│   │   ├── memory_node.py
│   │   ├── message.py
│   │   ├── metrics.py
│   │   ├── note.py
│   │   ├── perception_sediment.py
│   │   └── semantic_knot.py
│   └── migrations/
│       ├── __init__.py       # MigrationRunner + run_all_migrations
│       ├── m001_initial_schema.py
│       ├── m002_conversation_log_extensions.py
│       ├── m003_metrics_extensions.py
│       ├── m004_perception_sediment.py
│       ├── m005_structural_signatures.py
│       ├── m006_perception_files.py
│       ├── m007_consolidation_checkpoints.py
│       ├── m008_perception_log.py
│       ├── m009_exogenous_stream.py
│       ├── m010_belief_system.py
│       ├── m011_semantic_knots.py
│       ├── m012_conversation_notes.py
│       ├── m013_sediment_and_tags.py
│       ├── m014_memory_nodes.py
│       └── m015_belief_tensions.py
├── core/
│   ├── __init__.py
│   ├── pipeline.py           # ProcessingPipeline
│   ├── daemon.py             # AutopoieticDreamDaemon
│   ├── scheduler.py          # Background startup scheduler
│   ├── context.py            # PipelineResult
│   └── app_state.py          # Typed AppState dataclass
├── app_factory/
│   └── __init__.py           # register_all() — skill registration factory
├── modules/                  # 13 pipeline modules (unchanged)
├── utils/
│   ├── __init__.py           # Re-exports
│   ├── token_counter.py      # estimate_tokens
│   ├── similarity.py         # cosine_similarity (shared)
│   └── filesystem.py         # UPLOAD_DIR, get_upload_path, to_utc
└── main.py                   # Slim factory-orchestrated startup (516 lines)
```

## Backward Compatibility

All old import paths continue to work via re-export shims:

```python
# Both work
from backend.storage.repository import MessageRepository   # old
from backend.storage import MessageRepository              # new
from backend.storage.repositories import MessageRepository   # explicit
```

## Bug Fixes Included

| Bug | Location | Fix |
|-----|----------|-----|
| `_store_daemon_metrics` dead code | `core/daemon.py` | Extracted orphaned function body into proper standalone function. Was unreachable after `return ""` in `_extract_human_summary`, would cause `NameError` if daemon metrics path was reached |
