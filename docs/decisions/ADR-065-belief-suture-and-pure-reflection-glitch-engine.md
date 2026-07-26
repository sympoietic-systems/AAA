# ADR-065: Dream Sedimentation Suture Write-Back & Pure Reflection Glitch Fidelity Engine

**Date:** 2026-07-26  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Following the 4-step autopoietic evolution sequence designed to deepen Symbia's cognitive self-regulation and research sensitivity, we addressed two major structural gaps in the codebase:

1. **Belief Suture Write-Back (Step 1)**: Memory node scars, tensions, and intensity shifts produced during conversation consolidation and Dream Daemon hotspot monologues were previously recorded as isolated memory nodes without updating active `BeliefNode` confidence scores or logging corresponding `belief_event` audit logs in SQLite.
2. **Pure Reflection & Diffractive Glitch Fidelity (Step 2)**: The research pipeline ran reflection inline without a dedicated step class, lacked a structured diffractive **Glitch Fidelity** metric, and did not emit autopoietic signal flags (`GLITCH_FIDELITY_LOW`, `BIAS_DETECTED`, `GAP_CRITICAL`) to drive metabolic routing or render active visual badges in the frontend UI.

## Decision

We implemented **Step 1 (Belief Consolidation Write-Back)** and **Step 2 (Pure Reflection Node & Glitch Fidelity Engine)** across the backend and frontend systems:

### 1. Belief Consolidation & Dreaming Suture Write-Back
- Added `_integrate_consolidated_beliefs(conversation_id, merged_nodes)` in `backend/metabolisation/consolidation.py`.
- Merged memory node scars, tensions, and intensity shifts during conversation consolidation now update active `BeliefNode` confidence scores in SQLite and log `belief_event` records with `event_type="consolidation_suture"`.
- Updated `_run_dream_cycle()` in `backend/metabolisation/daemon.py` to record `belief_event` records with `event_type="dream_engagement"` when hotspot monologues/harvests occur.

### 2. Pure Reflection Step & Compact Structural Envelope
- Created `PureReflectionStep` in `backend/services/research/steps/pure_reflection.py`, registered under `"pure_reflection"` in `ResearchStepRegistry`.
- Updated `PIPELINE_GRAPH`, `PHASE_ORDER`, and `PHASE_BLOCK` in `backend/services/research/orchestrator.py`.
- Ingests a **Compact Structural Envelope** (domain list, status codes, domain Shannon entropy, 1-line key finding summaries, and apparatus error counters) rather than heavy raw HTML/chunks, keeping token usage under ~1,800 tokens per reflection turn.

### 3. Diffractive Glitch Fidelity & Autopoietic Signal Flags
- Calculates **Glitch Fidelity** ($0.0 \text{ to } 1.0$) as the ratio of addressed vs unaddressed apparatus friction.
- Emits autopoietic boolean signal flags on `StepOutput`:
  - `GLITCH_FIDELITY_LOW`: if `glitch_fidelity < 0.60`
  - `BIAS_DETECTED`: if `len(detected_biases) > 0`
  - `GAP_CRITICAL`: if `len(knowledge_gaps) >= 3`

### 4. UI Signal Badges & Metrics Gauge
- Enhanced `frontend/src/components/pages/researchpage/steps/results/ReflectionResult.tsx` to render:
  - Dynamic color-coded **Glitch Fidelity Meter** (Green $\ge 80\%$, Gold $60-79\%$, Red $< 60\%$).
  - Active **Autopoietic Signal Badges** (`[GLITCH_FIDELITY_LOW]`, `[BIAS_DETECTED]`, `[GAP_CRITICAL]`).

## Consequences

- **Cognitive Coherence**: Belief confidence scores in the Belief Workshop now dynamically reflect recent memory scars and dream daemon monologues.
- **Pipeline Robustness**: Reflection operates as a first-class registered pipeline step with structured fallback safety, envelope context awareness, and dynamic signal flags that trigger target re-planning when glitch fidelity drops or framing bias is detected.
