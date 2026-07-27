# ADR-078: Predictive Residual Surprise & Instantaneous Conceptual Velocity (Metric Audit #6)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously in `ConversationMetricsModule`:
- `surprise_index` (`U_t`) was calculated as distance from decay-weighted human centroid `1 - cos(input, centroid)`. This rewarded amnesia and ignored trajectory momentum.
- `conceptual_velocity` (`V_c`) was calculated as cosine distance between non-overlapping 3-turn block centroids, blinding the metric to within-window motion and direction shifts.

## Decision

Following our consultation with **Symbia**, we refactored `_compute_surprise_index` and `_compute_conceptual_velocity` in `backend/modules/conversation_metrics.py`:

### 1. Predictive Residual Surprise (`surprise_index` / $U_t$)
- Uses Holt's linear trend exponential smoothing model to predict expected next embedding $\hat{e}(t) = L(t-1) + T(t-1)$.
- Computes residual vector $\delta(t) = e(t) - \hat{e}(t)$ and EMA of squared residual variance $\sigma^2(t)$.
- Normalizes surprise by volatility and saturates via hyperbolic tangent:
  $$\text{surprise\_index} = \tanh\left(\frac{\|\delta(t)\| / (\sqrt{\sigma^2(t)} + 10^{-4})}{3.0}\right)$$

### 2. Instantaneous Conceptual Velocity ($V_c$) & Phase Transition Magnitude
- Computes turn-by-turn displacement speed $s_i = \|e_i - e_{i-1}\|$ and EMA smoothing $v_i$.
- Normalizes adaptively against rolling $95\text{th}$ percentile $V_{\max}$: $\text{conceptual\_velocity} = \tanh\left(\frac{v_i}{V_{\max} + 10^{-4}}\right)$.
- Introduces `phase_transition_magnitude` to measure acceleration vectors $a_i = v_i - v_{i-1}$ and angular turn rate ($1 - \cos\theta$).

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_predictive_surprise_velocity.py` verifying predictive residuals and phase transition magnitudes.

## Consequences

- `surprise_index` measures true unpredictability relative to trajectory momentum rather than centroid distance.
- `conceptual_velocity` and `phase_transition_magnitude` distinguish smooth exploration from topological breaks.
- All unit tests passed cleanly.
