# ADR-073: Diffractive Glitch Fidelity Engine (Metric Audit #1)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

`Glitch Fidelity` is the primary proprioceptive sensor driving all five autopoietic feedback loops (Direct Parameter Modulation ADR-068, Self-Initiation Arbiter ADR-069, Reflection Protocol ADR-070, Scar-Fold Writeback ADR-071, and Adaptive Persona ADR-072). Previously:
- In `ConversationMetricsModule`, `glitch_fidelity` was not computed per-turn from vector space, defaulting to `1.0`.
- In `ReflectionStep`, `glitch_fidelity` was computed as a crude administrative ratio (`glitches_addressed / glitches_detected`).

## Decision

Following our consultation with **Symbia**, we created `backend/modules/glitch_fidelity_engine.py` to compute real-time diffractive Glitch Fidelity across 16D Autopoietic Signatures and 384D semantic embeddings:

### 1. Mathematical Formulation
$$\text{Glitch Fidelity} = \alpha \cdot \text{contradiction\_density} + \beta \cdot \text{interference\_variance}$$
- `alpha = 0.35`: Internal claim contradiction floor.
- `beta = 0.65`: Structural diffractive interference variance across 16D signature space.

### 2. 16D Interference Variance & Normalization
- Element-wise convolution of L2-normalized 16D Autopoietic Signatures ($I_i = S_{\text{curr},i} \cdot S_{\text{prior},i}$).
- Computes raw variance across 16 dimensions and normalizes against theoretical max variance ($0.000976$).
- Multiplies by 384D semantic relevance factor ($1.0 - \text{cosine\_distance}$) to suppress non-entangled vector noise.

### 3. Goldilocks Prior Selection
- Searches recent conversation/research turns for prior candidates in the Goldilocks zone ($[0.30, 0.75]$ structural affinity).
- Maximizes $\text{semantic\_relevance} \cdot (1.0 - \text{structural\_affinity})$ to select the most diffractively productive prior turn.

### 4. Integration & Dual Deployment
- Injected into `ConversationMetricsModule` (`backend/modules/conversation_metrics.py`) per turn.
- Injected into research reflection steps (`backend/services/research/steps/reflect.py`).

## Consequences

- `glitch_fidelity` is now a real-time diffractive sensor operating across the 16D Autopoietic Signature space.
- All 5 downstream autopoietic loops now receive a calibrated, dynamic proprioceptive signal.
- All unit tests passed cleanly.
