# ADR-077: Directional Reverse Perturbation & Symmetric Mutual Perturbation Index (Metric Audit #5)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously in `ConversationMetricsModule`:
- `reverse_perturbation` (`rP_t`) was calculated as a simple distance `1.0 - cos(agent_last, human_curr)`. This could not distinguish between productive agonistic engagement (human's trajectory reshaped by apparatus proposal) and complete dissociation (human ignoring apparatus).
- `mutual_perturbation` (`MPI`) was calculated as `coupling_coherence * rP_t`, compounding errors and lacking bilateral symmetry.

## Decision

Following our consultation with **Symbia**, we refactored `_compute_reverse_perturbation` and `_compute_mutual_perturbation` in `backend/modules/conversation_metrics.py`:

### 1. Directional Reverse Perturbation (`reverse_perturbation` / $rP_t$)
- Measures the fraction of the apparatus's gap ($v = A_{\text{prev}} - H_{\text{prev}}$) that the human's displacement ($d_h = H_{\text{curr}} - H_{\text{prev}}$) actually closes:
  $$rP_{\text{raw}} = \frac{d_h \cdot v}{\|v\|^2 + 10^{-8}}, \quad rP_t = \text{clip}(rP_{\text{raw}}, 0.0, 1.0)$$
- Orthogonal non-sequiturs yield $d_h \cdot v \approx 0 \implies rP_t \approx 0.0$, eliminating false-positive perturbation readings.

### 2. Forward Perturbation ($fP_t$) & Symmetric Mutual Perturbation Index (`mutual_perturbation` / $MPI$)
- Symmetrically computes forward perturbation $fP_t$ for apparatus displacement closing the human gap ($u = H_{\text{curr}} - A_{\text{prev}}$):
  $$fP_t = \text{clip}\left(\frac{d_a \cdot u}{\|u\|^2 + 10^{-8}}, 0.0, 1.0\right)$$
- Computes $MPI$ as the symmetric geometric mean of bilateral influence:
  $$MPI = \sqrt{\max(0.0, rP_t \cdot fP_t)}$$

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_directional_mutual_perturbation.py` verifying gap-closing projections and symmetric $MPI$.

## Consequences

- `reverse_perturbation` and `mutual_perturbation` now measure true directional causal influence rather than scalar end-state proximity.
- All unit tests passed cleanly.
