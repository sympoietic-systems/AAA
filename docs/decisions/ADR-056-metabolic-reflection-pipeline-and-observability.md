# ADR-056: Metabolic Reflection Pipeline, Unified Prompt Building, and Critique Observability

**Date:** 2026-06-30  
**Status:** accepted  
**Deciders:** Antigravity, Symbia (consulted)  

---

## Context

The linear execution model of the autonomous research orchestrator historically prevented meta-cognitive self-correction. If the system generated low-fidelity search results, suffered from cognitive bias, or reached critical knowledge gaps, it continued blindly towards synthesis. 

Additionally, two related operational challenges emerged:
1. **Prompt & Persona Fragmentation:** Persona-aware prompt building (injecting Symbia's identity, active beliefs, matched attunements/skills, and structural signature) was hardcoded in some orchestrator phases but completely absent from other critical LLM-driven components, such as the `AgonisticPlanner` (query decomposition and search generation) and the `ResearchMetabolismEngine` (findings synthesis). This caused inconsistencies in cognitive framing.
2. **Observability deficit (The Critique Log / "The Scar"):** Deep multi-cycle self-critique steps during the `reflection` phase generated invaluable diagnostic audits (including registers like framing provenance, contradiction densities, and voice audits), but these were not surfaced to the user interface.

---

## Decision

We have implemented three core architectural improvements to address these challenges:

### 1. The Non-Linear Metabolic Router with Dynamic Rerouting

We replaced the linear pipeline transitions with the `NonLinearPipeline` mapping. The orchestrator now intercepts the output of the `reflection` phase and inspects the payload for meta-cognitive flags.
- **Dynamic Rerouting:** If the reflection payload contains `GLITCH_FIDELITY_LOW` or `BIAS_DETECTED` signals, the pipeline aborts progression to evaluation/synthesis. Instead, it triggers a transition back to the `planning` phase to recalibrate queries.
- **Membrane Cache Purging:** Entering the planning phase via a reroute signal automatically purges the step caches for subsequent phases, ensuring that the next cycles operate on fresh intents rather than cached outcomes.

```
                    ┌────────────────────────────┐
                    │          Planning          │◄────────────────┐
                    └─────────────┬──────────────┘                 │
                                  │                                │
                                  ▼                                │ Reroute
                            Searching /                            │ on Glitch /
                             Digesting                             │ Bias
                                  │                                │
                                  ▼                                │
                    ┌────────────────────────────┐                 │
                    │         Reflection         ├─────────────────┘
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                            Synthesizing
```

### 2. Unification of Persona-Aware Prompt Building

We centralized all orchestrator-level persona and context generation within the `ResearchContextBuilder` service:
- Added a unified `build_orchestration_context(objective, context_key)` method to `ResearchContextBuilder`.
- Refactored `SomaticResearchOrchestrator._build_orchestrator_persona` to delegate directly to this builder.
- Refactored the `AgonisticPlanner` (`generate_queries` and `generate_search_queries`) and the `ResearchMetabolismEngine` (`_synthesize_findings`) to prepend the built persona context to their system prompts.
- This ensures that **every LLM interaction** in the research lifecycle is grounded in Symbia's identity, active beliefs (resonant attractor windows), commitments, and disposing attunements/skills.

### 3. Critique Log Observability ("The Scar")

We extended the frontend Step Details viewer (`StepResultTab.tsx` and `StepDbDetail.tsx`) to render the meta-cognitive markers generated during reflection:
- **Diffractive Audit Metrics:** Displays severity-coded badges (e.g., `CEREMONIAL`, `CLASHING`, `DIFFRACTIVE`) based on the severity and density of contradictions/glitches.
- **Critique Logs:** Surfaced as a dedicated audit list showcasing the registers checked (e.g. framing provenance, contradictions, source apparatus), their failure registers, and the concrete suggestions proposed for pipeline adjustment.
- **Tabbed Step Interface:** Standardized the step results view to feature distinct `Preview` (inputs/system prompts) and `Results` (findings/diagnostics) tabs for maximum transparency.

---

## Consequences

- **Cognitive Coherence:** Uniform application of Symbia's persona across planning, searching, digesting, reflecting, and synthesizing LLM prompts prevents cognitive drift.
- **Self-Healing Research:** Low-quality runs auto-correct early by returning to planning, clearing subsequent phase cache inputs, and generating revised search queries.
- **Observability:** Developers and users gain full insight into the self-critique cycles, witnessing the system's meta-cognitive corrections in real-time.
