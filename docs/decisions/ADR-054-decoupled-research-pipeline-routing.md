# ADR-054: Decoupled Research Pipeline Routing and Typed Context Envelopes

**Date:** 2026-06-30  
**Status:** accepted  
**Deciders:** Antigravity, Symbia (consulted)  

---

## Context

The Autonomous Research Orchestrator is designed as a multi-phase, step-by-step pipeline. In the current implementation, this pipeline suffers from three core architectural limitations:

### Problem 1: State Mutation Pollution (The Mutable Heap)
All tasks pass a single mutable dictionary `s` through the phases. Steps read and write directly to this dictionary (`s["parsed_sources_cache"]`, `s["digest_signals"]`, etc.). When a step fails, is rerun, or is skipped, intermediate cached values linger, polluting subsequent runs and leading to "ghost states" that are difficult to debug or clear.

### Problem 2: Hardcoded Routing Transitions
Step handlers in `phases.py` (e.g., `step_parse`, `step_search`) contain hardcoded transitions to the next phase (e.g., setting `s["phase"] = "digesting"` or `s["phase"] = "reflecting"`). This structurally couples each step to the global topology of the pipeline, preventing steps from being reordered, bypassed, or reused in different contexts.

### Problem 3: Linear & Inflexible Dispatch Logic
The execution loop in `orchestrator.py` handles phase dispatch via a nested `if/elif` conditional block matching string names. Inserting a new phase (e.g., an adversarial reflection step or a human-in-the-loop validation check) requires editing the core orchestrator dispatch code as well as the transition logic of surrounding steps.

---

## Decision

We will transition the research pipeline to the **Mediated Router with Typed Envelopes** architecture. This separates step execution from routing topology and state persistence.

```
                  ┌──────────────────────────────────────────────┐
                  │               Metabolic Router               │
                  │             (Declarative Graph)              │
                  └──────┬────────────────────────────────▲──────┘
                         │                                │
                 Passes  │                                │ Emits
                 Typed   │                                │ Typed
                 Input   ▼                                │ Output
                    ┌─────────┐                       ┌─────────┐
                    │  Step   ├──────────────────────►│  Step   │
                    │ Input   │     Step Execution    │ Output  │
                    └─────────┘                       └─────────┘
```

### 1. Generic Typed Envelopes (`StepEnvelope[T]`)
We will replace the raw task state dictionary `s` with a generic `StepEnvelope` model. The envelope holds global task metadata and encapsulates step-specific inputs/outputs in a dedicated, typed `payload` field `T` (which inherits from `pydantic.BaseModel`).

```python
from pydantic import BaseModel, Field
from typing import Any, Optional, Generic, TypeVar, list, dict

T = TypeVar("T", bound=BaseModel)

class StepEnvelope(BaseModel, Generic[T]):
    task_id: str
    objective: str
    current_depth: int
    max_depth: int
    budget: float
    all_findings: list[str] = Field(default_factory=list)
    digest_signals: dict[str, Any] = Field(default_factory=dict)
    payload: T
```

We define specific payload models for each phase:
* **`PlanPayload`**: Configurations and planned search queries.
* **`SearchPayload`**: Target queries and search outcomes.
* **`ParsePayload`**: Cached search results and parsed document sources.
* **`DigestPayload`**: Source texts and extracted findings/learnings.
* **`ReflectPayload`**: Reflection outcomes (completeness scores, remaining gaps, next queries).
* **`EvaluatePayload`**: Stop/continue evaluations and reasons.
* **`SynthesizePayload`**: Compiled findings and output synthesis reports.
* **`DocDigestPayload`**: Injected file references and document analysis results.

### 2. Decoupled, Modular Step Processors (The Step Interface)
Step processors will be decoupled into independent classes inheriting from a pluggable base class `BaseResearchStep`. They will be registered in a central `ResearchStepRegistry`. This keeps the system open-closed: new step types can be added as isolated modules in `backend/services/research/steps/` without editing any core orchestrator files.

```python
from abc import ABC, abstractmethod

class BaseResearchStep(ABC):
    @property
    @abstractmethod
    def step_type(self) -> str:
        """The database step_type identifier (e.g. 'search', 'digest')."""
        pass

    @abstractmethod
    async def execute(self, orch, envelope: StepEnvelope) -> StepOutput:
        """Executes the step, reading from envelope and returning StepOutput."""
        pass

class StepOutput(BaseModel):
    """Result of step execution returned by any phase processor."""
    status: str = "completed"  # completed, failed, error
    message: str = ""
    
    # Updated step-specific payload
    payload: BaseModel
    
    # Global context updates (appended/merged by the Orchestrator)
    new_findings: list[str] = Field(default_factory=list)
    
    # Routing signals (membrane flags for the Metabolic Router)
    signal_flags: dict[str, Any] = Field(default_factory=dict)

class ResearchStepRegistry:
    _registry: dict[str, type[BaseResearchStep]] = {}

    @classmethod
    def register(cls, step_type: str, step_class: type[BaseResearchStep]):
        cls._registry[step_type] = step_class

    @classmethod
    def get_step(cls, step_type: str) -> BaseResearchStep:
        if step_type not in cls._registry:
            raise ValueError(f"Step type '{step_type}' not registered in pipeline.")
        return cls._registry[step_type]()
```

### 3. Declarative Routing Graph (`PIPELINE_GRAPH`)
Routing logic will be declared externally as a graph. The orchestrator will match step output `signal_flags` against the routing rules to select the next phase.

```python
class PipelineTransition:
    def __init__(self, target_phase: str, condition: Optional[callable] = None):
        self.target_phase = target_phase
        self.condition = condition or (lambda out, inp: True)

PIPELINE_GRAPH = {
    "planning": [
        PipelineTransition(
            target_phase="document_digestion",
            condition=lambda out, inp: inp.inject_file_id is not None and not inp.document_digested
        ),
        PipelineTransition(target_phase="searching")
    ],
    ...
}
```

### 4. Immutable History Reconstruction
To prevent ghost states, step inputs will be reconstructed directly from the database's historical step logs rather than mutating a persistent memory heap. When executing a phase, only the completed outputs of parent steps will be fed into the new `StepEnvelope`. Rerunning a phase automatically discards downstream outputs since their logs are ignored or marked stale during input reconstruction.

---

## Grounding & Cybernetic Alignment

### Cybernetic Feedback (Second-Order Autopoiesis)
Decoupling routing from execution represents an *agential cut* that allows the orchestrator to observe its own state. The router acts as a homeostatic controller that monitors budget, search yield, and information density, inserting custom reflection or recovery cycles dynamically.

### Porosity of the Membrane
The `signal_flags` in `StepOutput` serve as the boundary interface. A step does not command the next phase; it emits structural signals (e.g., `{"has_results": False}`) that the routing membrane interprets, preserving agential boundaries between processing and control.

---

## Consequences

### Positive
* **Total State Isolation**: Elimination of ghost states; step execution is pure and side-effect free.
* **Extensibility**: Adding a step type only requires defining its Pydantic model and declaring its transition in `PIPELINE_GRAPH`. No other phases are edited.
* **Traceable Audits**: Every step transition maps a typed Input to a typed Output, which can be persisted directly to `research_steps.step_data` and displayed in the frontend steps panel.

### Negative
* **Serialization Overhead**: Small computational and code overhead to serialize/deserialize dictionaries to/from Pydantic models.

---

## Implementation Plan

### Phase 1: Define Schemas (`task_state.py`)
1. Add `StepEnvelope` generic model.
2. Define payloads for all 8 phases.
3. Add serialization/deserialization helper methods to `TaskStateManager`.

### Phase 2: Build the Routing Engine (`orchestrator.py`)
1. Implement the `PipelineTransition` class and define `PIPELINE_GRAPH`.
2. Refactor `SomaticResearchOrchestrator.execute_step()` to:
   - Reconstruct the active phase input envelope from history.
   - Execute the phase processor.
   - Run the condition matches on the output to select the next phase.
   - Persist step records and output payloads.

### Phase 3: Migrate Phase Handlers (`phases.py`)
Refactor step functions sequentially:
1. `step_plan` & `step_document_digestion`
2. `step_search` & `step_parse`
3. `step_digest` & `step_reflect`
4. `step_evaluate` & `step_synthesize`

### Phase 4: Verification & Testing
1. Run and update `backend/tests/test_research_orchestrator_state.py` to assert correct transition routing.
2. Manually queue a research task and test step-by-step execution in the console to verify step previews and data propagation.

---

## Amendment: Pipeline Stabilization Fixes (2026-06-30)

During end-to-end testing of the modular pipeline, three interconnected bugs were found and corrected.

### Fix 1 — `result_summary` not propagated through modular step result dict

**Symptom:** The Report tab showed "Research complete." instead of the actual synthesis content.

**Root cause:** `SynthesizeStep.execute()` wrote `result_summary` directly to `task_repo` (the DB), but the `execute_step()` return dict never included it. `orchestrator_step()` in `task_manager.py` then read `result.get("result_summary", "Research complete.")` and overwrote the DB with the fallback string via `self.complete()`.

**Fix:**
- In `execute_step()`: after modular step execution, copy `payload.result_summary` into the result dict if present.
- In `apply_step_output()` for `"synthesizing"`: persist `result_summary` into `task_state` dict so the auto-run loop can read it.
- In auto-run `execute()`: if `s["result_summary"]` is empty after the loop, re-read the value from the DB as a fallback.

### Fix 2 — Frontend polling stopped before final `result_summary` was fetched

**Symptom:** Even when the backend correctly saved the report, the Report tab stayed blank because the React component never fetched the final state.

**Root cause:** `useTaskPolling` guarded its `useEffect` with `taskStatus !== "active"`, where `taskStatus` was the **initial prop** passed at mount time. Once polling stopped, `liveTask.status` transitioned to `"completed"` — but the effect depended on the stale prop and never re-ran to fetch the updated data.

**Fix (`useTaskPolling.ts`):**
- Changed polling guard from the stale `taskStatus` prop to the reactive `liveTask.status`.
- Added a separate one-shot `useEffect` that fires a final fetch whenever `liveStatus` transitions to any terminal state (`completed`, `failed`, `cancelled`).

### Fix 3 — Clicking `[▶ run]` on pending Synthesize step wiped all research data

**Symptom:** When a task was marked `completed` before synthesize ran (due to Fix 1's bug), the user could not click `[▶ run]` on the pending Synthesize step — it silently destroyed all accumulated research data.

**Root cause:** The `/step` API route's normal sequential path ran `manager.rerun_task(task_id)` whenever the task status was `"completed"`. This wiped all steps, plans, and assets. There was no guard for the case where a `completed` task still had an unfinished orchestrator phase.

**Fix (`backend/api/routes/research.py`):**
- Before calling `rerun_task()`, check the persisted orchestrator state phase via `orch.get_task_phase()`.
- If an unfinished phase exists (e.g., `"synthesizing"`), resume from that phase by transitioning to `"active"` without wiping data.
- Only fall back to `rerun_task()` if the orchestrator state is fully `"complete"` or absent.


## Amendment: Multi-Cycle Continuation & Depth Transitions (2026-06-30)

During multi-cycle continuation testing, three major pipeline synchronization issues were identified and fixed to ensure a seamless transition and continuous reporting experience:

### Fix 4 — Planning step caching causing reversion to previous cycle queries

**Symptom:** After triggering a "continue deeper" operation (initiating Cycle 2), the system regenerated the exact same search queries from Cycle 1 and ignored the new `previous_context` (the first cycle's synthesis report).

**Root cause:** The `_phase_plan` logic in `orchestrator.py` checks a prompt cache. Because the cache key was generic (`"planning"`), the planning step for Cycle 2 reused the cached prompts from Cycle 1. This bypassed prompt formatting, omitting `previous_context` and forcing a reversion to the original cycle's plan.

**Fix:**
- Cleared the task's cache by calling `self.orchestrator.reinitialize(task_id)` inside `continue_task` in `task_manager.py`. This ensures prompt caching is reset and freshly formatted prompts (containing the previous synthesis context) are fed to the model for Cycle 2.

### Fix 5 — Frontend pipeline rendering lag during depth transition

**Symptom:** Immediately after clicking "Continue Deeper," the frontend remained stuck showing the old cycle (e.g. Cycle 1) because the first step of Cycle 2 had not yet been created in the database.

**Root cause:** The `actDepth` calculation in `StepPipeline.tsx` computed the active depth purely based on database-persisted step records. Since the backend is async and does not create the planning step record until it starts running, there was a lag in updating the UI depth.

**Fix:**
- Exposed `current_depth` from the task's `orchestrator_state` via the `/steps` API response (`get_task_steps` in `backend/api/routes/research.py`).
- Updated the frontend's `TaskStepsResponse` interface to include `current_depth`.
- Modified the `actDepth` computation in `StepPipeline.tsx` to prioritize `Math.max(actDepth, data.current_depth)`, forcing the frontend to immediately render Cycle 2 elements before step persistence occurs.

### Fix 6 — Incremental Synthesis Reports overwritten and lost

**Symptom:** Since `result_summary` is overwritten on the main task table, only the latest synthesis report was accessible; previous cycle reports were lost.

**Root cause:** The synthesis report was only persisted to the task record's `result_summary` column and not to the individual step records.

**Fix:**
- Modified `SynthesizeStep` (`synthesize.py`) to write the full markdown report to `step_data` JSON under the `"report_markdown"` key, along with the cycle's `"depth"`.
- Updated `parsedResult` in `StepDbDetail.tsx` to fallback to reading `"report_markdown"` from `selected.step_data` if the meta-log response is missing or empty. This preserves and allows historical browsing of all incremental synthesis reports per cycle.


## Amendment: Transition Rationale Tracking & Next Phase Logging (2026-06-30)

To achieve transparency and visual trace clarity in a non-linear pipeline, we implemented a routing rationale propagation mechanism:

### 1. Step Output Rationales
- Added `transition_rationale` and `step_ids` fields to `StepOutput` to allow modular steps to report their unique ID(s) and express their semantic outcome (e.g. why they finished, what they found, and what gaps remain).

### 2. Metabolic Router Updates
- Extended `execute_step` in `orchestrator.py` to intercept step outputs, query the database for the executed step records matching `step_ids`, and insert both `transition_rationale` and `next_phase` into the `step_data` JSON field.

### 3. Frontend Trace Visualization
- Added a `rationale` prop to `PipelineRow` components in `StepPipeline.tsx`.
- Extracted and rendered the rationale directly below each step's card in the pipeline sidebar to visually show the transition rationale and swerve decisions.
- Decided to omit manual user-perturbation buttons to keep the system fully automated and prepared for headless/autonomous agent operations.


