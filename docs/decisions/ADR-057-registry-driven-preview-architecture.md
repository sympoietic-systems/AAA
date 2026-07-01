# ADR-057: Decoupled and Registry-Driven Research Step Preview Architecture

**Date:** 2026-07-01  
**Status:** accepted  
**Deciders:** Antigravity, Symbia (consulted)  

---

## Context

Historically, the `SomaticResearchOrchestrator` contained a monolithic and highly complex method, `preview_step_inputs`, responsible for compiling prompts, system personas, and formats for all 9 phases of the autonomous research pipeline. 

This monolithic design introduced several critical challenges:
1. **High Coupling & Code Bloat:** Any modification to the prompts, state rehydration, or presentation layer of an individual research phase (e.g. consolidation or evaluation) required editing `orchestrator.py`, which swelled to over 1,300 lines.
2. **Context Fragmentation:** Phase execution logic lived in separate class files under `backend/services/research/steps/`, while phase preview logic for the exact same steps resided inside the orchestrator. This split created code duplication and logic drift.
3. **Registry Bypass:** The orchestrator already utilized the `ResearchStepRegistry` to load step processors during execution (`execute()`), but bypassed it during step previews (`preview_step_inputs()`).

---

## Decision

We have decoupled the step preview logic from the `SomaticResearchOrchestrator` and migrated it to a registry-driven architecture where each step defines its own prompt compilation:

1. **Step-Level Preview Contract:** Every class implementing `BaseResearchStep` now implements a `preview()` method with the standard signature:
   ```python
   async def preview(self, orch, envelope: StepEnvelope, state: dict) -> dict:
   ```
2. **Orchestrator Delegation:** The orchestrator's monolithic `preview_step_inputs` method has been refactored to delegate directly to the step classes via the registry:
   ```python
   envelope = self.reconstruct_step_input(task_id, s, phase)
   step_obj = ResearchStepRegistry.get_step(phase)
   result = await step_obj.preview(self, envelope, s)
   ```
   This ensures that the orchestrator is no longer concerned with phase-specific prompt structures, database fetches, or formats.
3. **State Re-hydration and Parity:** Each step's `preview()` method utilizes the same data-rehydration logic (e.g., querying past step result histories from the database) as its `execute()` method. This ensures that the generated system and user prompts are structurally identical to what will be run.
4. **Complete Cleanups:** The monolithic code block in `orchestrator.py` and its helper `_preview_plan_inputs` have been permanently deleted.

---

## Consequences

- **Separation of Concerns:** Prompt definition, context building, and formatting are now fully self-contained within each phase's step class module.
- **Maintainability:** Modifying a research step (e.g., adding dynamic queries or tweaking system prompt templates) only requires editing the step's specific file under `backend/services/research/steps/`.
- **Zero API or Frontend Changes:** The public API endpoint `/api/research/tasks/{task_id}/preview/{phase}` and its underlying orchestrator contract are preserved without changes, meaning the frontend step preview UI works out of the box.
- **Improved Code Quality:** Eliminated over 500 lines of monolithic code from `orchestrator.py`, lowering complexity and improving test readability.
