# Scaffolding & Development Rules Guide
**System:** Autopoietic Agentic Assemblage (AAA)  
**Classification:** Architectural Guidelines & Engineering Standard

---

## 1. Directory Structure & System Layout

As the AAA codebase grows, maintaining a strict separation of concerns is critical for stability and scaling. The repository is organized as follows:

```
AAA/
├── .agents/                    # Agent skills and runtime configurations
├── docs/                       # Architectural decisions (ADRs) and specs
│   └── decisions/              # System-wide Architecture Decision Records
├── backend/                    # FastAPI Backend Application
│   ├── api/                    # Routers, path definitions, and request schemas
│   │   ├── routes.py           # Core routes for endpoints (/chat, /history, /beliefs, etc.)
│   │   └── schemas.py          # Pydantic schemas validating payloads
│   ├── core/                   # Lifespan, pipeline orchestrator, and registry
│   │   ├── pipeline.py         # Pipeline runner executing sequential modules
│   │   ├── registry.py         # Skill registry resolving module arrays
│   │   └── scheduler.py        # Background task scheduler and recovery loop
│   ├── modules/                # Core processing modules (the "engine" components)
│   │   ├── base.py             # Interface definition for ProcessingModule
│   │   ├── belief_engine.py    # Somatic warping, attractors, and belief metabolism
│   │   ├── structural_engine.py# Lexicon & structural signature scorer
│   │   └── ...                 # Other modules (perception, web, client, etc.)
│   ├── storage/                # SQLite database and SQL repository mappings
│   │   ├── database.py         # Database initializer, table creation, WAL configuration
│   │   ├── models.py           # Dataclass entity models
│   │   └── repository.py       # SQL transaction scripts & data query mappings
│   └── tests/                  # Backend unit, integration, and flow test suites
└── frontend/                   # Vite + React + TypeScript Frontend
    ├── src/
    │   ├── api/                # Axios instances & API request definitions
    │   ├── components/         # Reusable React components
    │   │   ├── ChatView.tsx    # Scrollable chat window and status indicators
    │   │   ├── SidePanel.tsx   # Control interface for somatic meters & logs
    │   │   └── ...             # Visual elements and SVGs
    │   ├── hooks/              # Custom React hooks (polling, scroll containment)
    │   ├── App.tsx             # Root layout and context propagation
    │   ├── index.css           # Global themes & Tailwind CSS directives
    │   └── main.tsx            # React application entry point
    └── vite.config.ts          # Build configuration and proxy overrides
```

---

## 2. Backend Scaffolding Rules

To add a new feature or processing step, follow the sequential implementation pattern:

### 2.1. Database Entity Expansion
1. **Define Dataclass**: Add the data entity to [backend/storage/models.py](file:///d:/01_GIT/AAA/backend/storage/models.py).
2. **Create Database Table**: Update the initialization DDL in [backend/storage/database.py](file:///d:/01_GIT/AAA/backend/storage/database.py). Ensure the query uses standard types and indexes. Set up foreign keys with `ON DELETE CASCADE` if applicable.
3. **Extend Repository**: Add clean SQLite transaction methods to [backend/storage/repository.py](file:///d:/01_GIT/AAA/backend/storage/repository.py). Use context managers for connection safety to prevent lock contention.

> [!IMPORTANT]
> The SQLite database must run with Write-Ahead Logging (WAL) enabled: `PRAGMA journal_mode=WAL;`. Always wrap modifications in explicit transactions to prevent concurrent read/write locks.

### 2.2. Creating a Processing Module (Skill)
All modular pipeline steps must subclass `ProcessingModule` defined in [backend/modules/base.py](file:///d:/01_GIT/AAA/backend/modules/base.py).

```python
from backend.modules.base import ProcessingModule
from backend.skills.metadata import SkillMeta

class CustomAnalysisModule(ProcessingModule):
    def __init__(self, some_dependency):
        self._dep = some_dependency

    @property
    def name(self) -> str:
        return "custom_analysis"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="custom_analysis",
            description="Performs custom cognitive analysis on conversational state",
            category="reasoning",
            always_run=True,
            triggers=["analysis", "somatic"],
        )

    def validate(self) -> bool:
        # Check dependencies / system status
        return True

    async def process(self, payload: dict) -> dict:
        # Process context, inject fields, modify payload
        payload["custom_results"] = "results"
        return payload
```

*   **Registration**: Register the new module in the FastAPI lifespan manager within [backend/main.py](file:///d:/01_GIT/AAA/backend/main.py).
*   **Pipeline Ordering**: Position the module in the processing pipeline sequence under the `pipeline_order` list in `config.yaml`.

### 2.3. Route and Payload Validation Schema
*   **Pydantic Schema**: Define strict payload and response structures in [backend/api/schemas.py](file:///d:/01_GIT/AAA/backend/api/schemas.py).
*   **FastAPI Route**: Place API route definitions in [backend/api/routes.py](file:///d:/01_GIT/AAA/backend/api/routes.py). Always inject the state parameters via `request.app.state` instead of using global dependencies.
*   **Timezones**: Use `datetime.now(timezone.utc)` for setting timestamps to maintain consistent timezone-aware formatting. For database queries expecting UTC strings, use `.replace(tzinfo=None)` safely if compared against database fields.

---

## 3. Frontend Scaffolding Rules

### 3.1. Directory Conventions
*   `frontend/src/components/`: Modular UI widgets. Break large elements (like SidePanel or ChatView) into sub-components (e.g. `BeliefAttractorCard`, `SomaticMeter`) when they exceed 1000 lines of code.
*   `frontend/src/hooks/`: Move persistent side effects, polling routines, and layout calculations (such as automatic message window scrolling) into clean custom hooks.
*   `frontend/src/api/`: All network queries should be located here. Do not make raw fetch/axios calls directly inside visual render components.

### 3.2. Styling & Theme System
AAA utilizes Tailwind CSS v4 alongside custom HSL color definitions in [frontend/src/index.css](file:///d:/01_GIT/AAA/frontend/src/index.css).

*   **Dark Mode First**: The system defaults to dark mode (`#0c0c0c` background, `#c8c8c8` text color).
*   **Color Theme Palette**:
    *   **Primary Active Elements**: Use vibrant green (`#4ade80` / `emerald-400`) or specific homeostatic statuses (Flowing/Consolidating/Disrupted).
    *   **Monospace Defaults**: Use the custom `--font-mono` defined variables for technical readouts, telemetry graphs, and logs.
*   **Animations**: Implement micro-animations (`transition-all duration-300`, hover scaling) to visually highlight autopoietic changes (such as slider adjustments, belief warping, or state transitions).

---

## 4. Testing Standards

*   **Location**: All test scripts must be written in the [backend/tests/](file:///d:/01_GIT/AAA/backend/tests/) directory and prefixed with `test_`.
*   **Database Isolation**: Always instantiate mock/temporary database connections (e.g. SQLite `:memory:` or temp test files) within test fixtures. A global `conftest.py` is configured to automatically force test database path to `data/aaa_test.db` and delete it upon test completion to ensure the production database (`aaa.db`) is never modified or polluted by tests.
*   **LLM Provider Mocking**: Do not trigger real LLM completions inside standard unit tests. Create mock completions containing expected mock JSON fields (e.g., `opacity_map`, `interference_score`) to assert state changes.
*   **Running Tests**: Propose `uv run pytest` or `pytest backend/tests/` to execute the full test suite. Make sure all unit, routing, and database tests pass before committing.

---

## 5. Architectural Consistency & Documentation

### 5.1. Writing Architectural Decisions (ADR)
When making architectural modifications, additions to external APIs, or changes to state-tracking math:
1. Create a new markdown file in [docs/decisions/](file:///d:/01_GIT/AAA/docs/decisions/) matching the format `ADR-NNN-slug.md`.
2. Follow the template defined in [docs/decisions/README.md](file:///d:/01_GIT/AAA/docs/decisions/README.md).
3. Update the table of contents in the decisions folder index.

### 5.2. Code Comments and Docstrings
Maintain high inline documentation density. Define the purpose of each function, class parameters, returned values, and mathematical logic equations (such as cybernetic feedback equations or somatic coordinate adjustments).
