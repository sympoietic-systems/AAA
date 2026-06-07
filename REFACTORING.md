# Backend Refactoring Plan

**Branch**: `refactor/backend-modularity`
**Date**: 2026-06-07
**Goal**: Decompose monolithic backend files into modular, maintainable units following Python conventions.

---

## Current State

| Metric | Value |
|--------|-------|
| `storage/repository.py` | 2,517 lines — 10 repos + helpers in 1 file |
| `api/routes.py` | 2,003 lines — 35+ endpoints + business logic |
| `core/daemon.py` | 1,721 lines |
| `main.py` lifespan | 370+ lines wiring everything |
| `storage/database.py` | 580 lines migration in one function |
| All `__init__.py` | Empty (no public API surfaces) |
| Code duplication | Identical `__init__`/`_conn()` pattern in all 10 repos |

---

## Phase 1: Split Monolithic Repository

**Goal**: One repository class per file. Zero logic changes. Eliminate boilerplate via `BaseRepository`.

### Target Structure

```
backend/storage/
├── __init__.py                 # Re-exports
├── connection.py               # ConnectionTracker, with_connection, _get_tracked_connection
├── database.py                 # Schema + migrations
├── models.py                   # Dataclasses (unchanged)
├── row_mappers.py              # All _row_to_* functions
└── repositories/
    ├── __init__.py             # Re-exports
    ├── base.py                 # BaseRepository (eliminates duplicate __init__/_conn)
    ├── conversation.py         # ConversationRepository
    ├── message.py              # MessageRepository
    ├── error_log.py            # ErrorLogRepository
    ├── metrics.py              # MetricsRepository
    ├── perception_sediment.py  # PerceptionSedimentRepository
    ├── consolidation.py        # ConsolidationCheckpointRepository
    ├── memory_node.py          # MemoryNodeRepository
    ├── belief.py               # BeliefRepository
    ├── semantic_knot.py        # SemanticKnotRepository
    └── note.py                 # NoteRepository
```

### Key Changes
- `repository.py` becomes a backward-compat re-export shim
- All imports throughout codebase continue working unchanged
- `BaseRepository` eliminates ~100 lines of duplicate boilerplate

---

## Phase 2: Split Monolithic Routes

**Goal**: One route file per domain. Zero logic changes in this phase.

### Target Structure

```
backend/api/
├── __init__.py
├── schemas.py                # Pydantic models (unchanged)
├── router.py                 # Main router including sub-routers
├── deps.py                   # verify_password, shared dependencies
└── routes/
    ├── __init__.py
    ├── chat.py               # POST /chat
    ├── auth.py               # GET /auth/verify
    ├── agent.py              # GET /agent
    ├── beliefs.py            # GET /beliefs
    ├── history.py            # GET /history, /messages/{id}/thinking, /messages/{id}/context
    ├── conversations.py      # CRUD, generate-title
    ├── tokens.py             # GET /tokens
    ├── health.py             # GET /health
    ├── skills.py             # GET /skills
    ├── scheduler.py          # GET /scheduler/status
    ├── metrics.py            # GET /metrics
    ├── background.py         # POST /background
    ├── errors.py             # GET /errors
    ├── files.py              # File upload/download/delete/reprocess/summary
    ├── daemon.py             # GET /daemon/status, POST /daemon/trigger
    ├── notes.py              # Note CRUD
    ├── sediment.py           # Sediment injection endpoints
    ├── tags.py               # Tag management
    └── memory_nodes.py       # GET /memory-nodes
```

---

## Phase 3: Extract Services Layer

**Goal**: Move business logic from routes into dedicated service classes. Routes become thin wrappers.

### Target Structure

```
backend/services/
├── __init__.py
├── chat.py          # ChatService
├── belief.py        # BeliefService
├── conversation.py  # ConversationService
├── file.py          # FileService
├── metrics.py       # MetricsService
├── note.py          # NoteService
├── sediment.py      # SedimentService
├── title.py         # TitleService
├── semantic_knot.py # SemanticKnotService
├── consolidation.py # ConsolidationService
├── daemon.py        # DaemonService
└── health.py        # HealthService
```

---

## Phase 4: Refactor main.py Lifespan

**Goal**: Break 370-line lifespan into focused factory functions.

### Extracted Functions
- `_init_database()` — DB init + repo creation
- `_init_embedder()` — Embedder creation
- `_init_providers()` — LLM + structural + vision + background providers
- `_init_context_collector()` — Context collector
- `_init_conversation_metrics()` — Metrics module
- `_init_sedimentation()` — Sedimentation retrieval
- `_init_diffractive_retrieval()` — Diffractive retrieval
- `_init_belief_engine()` — Belief metabolism
- `_init_perception()` — Perception module
- `_init_web_retrieval()` — Web retrieval
- `_register_skills()` — All 13 skill registrations
- `_wire_pipeline()` — Pipeline + app.state wiring
- `_start_background_services()` — Scheduler + daemon

Also: Merge `_create_llm_provider()` and `_create_provider_from_config()` (80% duplicate).

---

## Phase 5: Extract Database Migrations

**Goal**: Replace monolithic `init_db()` with numbered migration files + runner.

```
backend/storage/migrations/
├── __init__.py
├── runner.py             # MigrationRunner
├── 001_initial_schema.py
├── 002_conversation_metrics.py
├── 003_perception_sediment.py
├── 004_perception_files.py
├── 005_consolidation_checkpoints.py
├── 006_perception_log.py
├── 007_exogenous_stream.py
├── 008_belief_system.py
├── 009_semantic_knots.py
├── 010_conversation_notes.py
├── 011_sediment_injections.py
├── 012_conversation_tags.py
├── 013_memory_nodes.py
├── 014_belief_tensions.py
└── 015_somatic_state.py
```

Each migration: `up(conn)` function. Runner tracks applied in `_migrations` table.

---

## Phase 6: Standardize Public APIs

**Goal**: Every package has explicit re-exports for clean single-line imports.

Example:
```python
# Before
from backend.storage.repository import MessageRepository
from backend.storage.models import Message

# After
from backend.storage import MessageRepository, Message
```

---

## Phase 7: Typed AppState Container

**Goal**: Replace `getattr(state, "x_repo", None)` with typed `dataclass`.

```python
@dataclass
class AppState:
    config: dict
    agent_name: str = "symbia"
    message_repo: MessageRepository
    error_repo: ErrorLogRepository
    # ... all 20+ attributes typed
```

---

## Risk Assessment

| Phase | Risk | Test Impact | Rollback |
|-------|------|-------------|----------|
| 1: Split repository | Low | Update imports only | Keep old file as re-export shim |
| 2: Split routes | Low-Medium | No change (API endpoints) | Keep old router as re-export |
| 3: Service layer | Medium | Add service unit tests | Phase 2 routes still work |
| 4: Main.py refactor | Medium | Integration tests cover startup | Compare state before/after |
| 5: Migration extract | Medium | Schema tests (same SQL) | Old init_db() as fallback |
| 6: __init__.py | Very Low | Zero impact | Additive only |
| 7: AppState | Low | Zero impact (type annotations) | Dataclass wrapper only |

---

## Verification Per Phase

```bash
# Run full test suite
pytest backend/tests/ -v

# Lint
ruff check backend/

# Health check
curl http://localhost:8000/api/health
```

---

## Conventions

- **Python naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Imports**: stdlib → third-party → local (in that order)
- **Private members**: prefixed with `_`
- **File size**: target under 500 lines, max 750
- **Function size**: target under 50 lines
- **Type hints**: on all public methods
