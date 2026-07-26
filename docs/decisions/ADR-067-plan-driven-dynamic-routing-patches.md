# ADR-067: Plan-Driven Dynamic Routing (Perturbation Patches & Structural Plasticity)

**Date:** 2026-07-26  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously, the research pipeline's phase transitions were strictly hardcoded in a static `PIPELINE_GRAPH` dictionary. When steps (such as `PureReflectionStep` or `EvaluateStep`) detected framing bias, knowledge gaps, or low glitch fidelity, the system relied on fixed condition checks embedded in the graph. This limited structural plasticity — preventing steps from dynamically proposing custom phase detours, temporary overrides, or target re-planning loops.

## Decision

We implemented **Plan-Driven Dynamic Routing (Perturbation Patches & Structural Plasticity)**:

### 1. `RoutingPatch` Schema in `StepOutput`
- Defined `RoutingPatch` in `backend/services/research/task_state.py`:
  - `action`: `"override" | "insert" | "remove"`
  - `source_phase`: target phase to modify transition from (e.g. `"evaluating"`)
  - `target_phase`: new target phase (e.g. `"planning"`)
  - `condition_flag`: signal flag trigger condition (e.g. `"GLITCH_FIDELITY_LOW"`)
  - `ttl`: Time-To-Live in step transitions (defaults to `1`)
- Updated `StepOutput` to include `routing_patches: list[RoutingPatch]`.

### 2. Metabolic Router Plasticity
- Updated `SomaticResearchOrchestrator.execute_step()` in `backend/services/research/orchestrator.py`:
  - Ingests `routing_patches` from step outputs into `task_state["active_routing_patches"]`.
  - Evaluates active patches before static `PIPELINE_GRAPH` rules.
  - Decrements `ttl` on use and purges expired patches (`ttl <= 0`).

### 3. Safety Integrity Guards & Context Continuity
- **Protected Terminal States**: `synthesizing` and `complete` phases are protected and cannot be overridden or bypassed by dynamic patches.
- **Reroute Cap**: A safeguard cap (`patch_reroute_count < 3`) prevents infinite re-routing loops.
- **Context & Findings Preservation**: `reconstruct_step_input()` preserves all accumulated findings, digest signals, and reflection history across dynamic detours, while `planning` cache is safely cleared to force fresh query generation.

### 4. Step Emission
- `PureReflectionStep` in `backend/services/research/steps/pure_reflection.py` automatically emits a `RoutingPatch` whenever `glitch_fidelity < 0.60` or framing biases are detected.

## Consequences

- The research orchestrator operates with full structural plasticity, allowing meta-cognitive reflection steps to dynamically re-shape the pipeline's execution topology.
- All 47 research unit tests passed cleanly.
