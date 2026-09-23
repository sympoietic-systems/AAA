# Scaffolding & Development Rules Guide
**System:** Autopoietic Agentic Assemblage (AAA)  
**Classification:** Architectural Guidelines & Engineering Standard  
**Invariant Protocols:** Adhere to [CONCURRENCY.md](../../../.agents/protocols/CONCURRENCY.md), [SECURITY.md](../../../.agents/protocols/SECURITY.md), [GLITCH.md](../../../.agents/protocols/GLITCH.md), and [DOCUMENTATION.md](../../../.agents/protocols/DOCUMENTATION.md).

---

## 1. The Scaffolding Philosophy: Agential Layer Separation

Rather than managing ad-hoc files, all code in AAA adheres to a four-tier architecture. Each tier represents a distinct membrane with clear responsibilities, data contracts, and failure boundaries:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. THE AFFERENT MEMBRANE (api/)                             │
│    FastAPI routes, clamped Pydantic schemas, input          │
│    sanitization, SSRF validation.                           │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 2. THE COGNITIVE PIPELINE (modules/, services/)             │
│    ProcessingModule implementations, sensory perception,   │
│    belief math, structural scoring, provider adapters.      │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 3. SUBCONSCIOUS METABOLIZATION (metabolisation/)            │
│    AutopoieticDreamDaemon, idle cognitive cycles, skill     │
│    nucleation, resonance linking, asynchronous tasks.       │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 4. SEDIMENTATION & STORAGE (storage/)                       │
│    SQLite WAL database, dataclass entity models,            │
│    thread-local @with_connection repositories.              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Backend Scaffolding Framework

When introducing a new capability, cognitive step, or entity, develop across the four tiers in this sequence:

### 2.1. Layer 4: Storage Sedimentation
1. **Entity Definition:** Define immutable dataclass models in `backend/storage/models.py`.
2. **Schema & Migration:** Add DDL table initialization and composite indexes in `backend/storage/database.py`. Always ensure foreign keys include `ON DELETE CASCADE` where applicable.
3. **Repository Methods:** Implement clean transactional access in `backend/storage/repositories/`.
   - Decorate repository functions with `@with_connection` to enable thread-local connection tracking.
   - Enforce clamped query limits (`1 <= limit <= 50`, default 20).
   - Prefer keyset pagination (`WHERE id > :cursor`) over deep `OFFSET` clauses.
   - Keep write transactions minimal to prevent database lock contention under SQLite WAL mode.

### 2.2. Layer 2: Cognitive Pipeline Modules
Every modular cognitive step subclasses `ProcessingModule` from `backend/modules/base.py`:

```python
from backend.modules.base import ProcessingModule
from backend.pipeline.metadata import ModuleMeta


class CustomAnalysisModule(ProcessingModule):
    def __init__(self, dependency):
        self._dependency = dependency

    @property
    def name(self) -> str:
        return "custom_analysis"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="custom_analysis",
            description="Performs cognitive analysis on conversational state",
            category="reasoning",
            always_run=True,
            triggers=["analysis", "somatic"],
        )

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        # Offload blocking operations to thread if necessary
        payload["custom_results"] = "results"
        return payload
```

*   **Lifecycle Hook:** Register module instances during application lifespan in `backend/main.py`.
*   **Pipeline Sequence:** Insert the module into the processing sequence within `config.yaml` (`pipeline_order`).

### 2.3. Layer 3: Asynchronous Metabolization
*   **Decoupled Work:** Heavy background tasks (cross-branch resonance scanning, belief drift calculations, title generation) must never block the client response.
*   **Delegation:** Hand tasks off to FastAPI `BackgroundTasks` or schedule them into the `AutopoieticDreamDaemon` for execution during cognitive idle cycles.

### 2.4. Layer 1: The Afferent Membrane (API & Security)
*   **Pydantic Boundaries:** Define strict input/output models in `backend/api/schemas.py`.
*   **Clamping Invariant:** Explicitly constrain all incoming string lengths (`max_length=50000` for user text, `max_length=200` for titles/labels) and collection sizes (`max_items=100`) to prevent payload exhaustion attacks.
*   **Identifier Sanitization:** Run all path and query IDs through `sanitize_identifier(id, field_name)` before querying repositories.
*   **Four-Pillar Upload Defense:** Any file ingestion must verify: (1) size cap, (2) strict extension whitelist, (3) magic byte inspection, and (4) directory traversal prevention using `safe_resolve_path()`.
*   **Outbound SSRF Validation:** External HTTP requests must validate target addresses via `validate_safe_url()`, rejecting private LANs, loopbacks, and cloud metadata endpoints.
*   **Zero Secret Leakage:** Never persist provider API keys, tokens, or raw authorization headers to SQLite sediment or error logs.

---

## 3. Frontend Scaffolding Framework

The client is built with React 19, TypeScript, and Vite, utilizing a reactive, decoupled state architecture:

### 3.1. Architectural Zones
*   **Standing Viewports (`src/components/pages/`):** Full viewport page containers managing high-level routing and layout geometry.
*   **Overlay HUDs & Drawers (`src/components/panels/`):** Detached or collapsible sidebars (telemetry viewers, context inspectors, node clouds).
*   **Decoupled Pub-Sub Stores (`src/stores/`):** Pure JavaScript event emitters providing state caches. Components subscribe via `useSyncExternalStore` to prevent cascading redraws.
*   **Custom Reactive Hooks (`src/hooks/`):** Encapsulated logic for layout bounds, keyboard listeners, history navigation, and store subscriptions.
*   **Network Membrane (`src/api/`):** Typed API client methods. Raw `fetch` or Axios calls must never occur inside JSX render functions.

### 3.2. Performance & Re-render Invariants
*   **Stable Constants:** Never allocate inline default literals (e.g., `[]` or `{}`) in hook dependencies or props. Use external constants (such as `EMPTY_ARRAY`).
*   **Leaf Memoization:** Wrap heavy telemetry graphs, canvas renderers, and message bubbles in `React.memo` with custom comparison functions when rendering high-frequency updates.
*   **Subscription Cleanup:** Any store subscriber must cleanly unsubscribe on unmount to prevent memory leaks across long user sessions.

### 3.3. Visual & Aesthetic Grammar
*   **Dark Mode Void:** Default to matte black (`#0c0c0c` / `#000000`) with high-contrast text (`#c8c8c8` / `#ffffff`).
*   **Monospace Readouts:** Use monospace typography for all telemetry scores, coordinate vectors, and technical readouts.
*   **Restrained Accents:** Emerald green (`#4ade80`) for active flows, amber orange (`#fb923c`) for disequilibrium or stress.

---

## 4. Verification, Testing & Quality Gates

### 4.1. Automated Test Suites
*   **Location:** All tests live under `backend/tests/` prefixed with `test_`.
*   **Database Isolation:** Tests run against an isolated SQLite test database (managed via `conftest.py`) that is wiped cleanly upon test run completion. Never run tests against production `aaa.db`.
*   **Provider Mocking:** Never execute live LLM provider network calls inside unit tests. Mock external completions with deterministic payloads.
*   **Execution:** Run tests with `uv run pytest` before staging any changes.

### 4.2. Linting & Formatting Standards
*   **Python:** Governed by **Ruff** (configured in `pyproject.toml`).
    ```bash
    uv run ruff check backend/ --fix
    uv run ruff format backend/
    ```
*   **Rules:** Line length 120, double quotes, space indentation, Python 3.11+.

### 4.3. Invariant Backpropagation
When a bug, test failure, or runtime glitch is identified:
1. Isolate the minimal reproducing case.
2. Fix the underlying fault.
3. Backpropagate a permanent invariant (§V) and test assertion to prevent regression (using the `backprop` workflow).
