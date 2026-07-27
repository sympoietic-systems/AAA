# ADR-079: Alignment Gap DRR & Gordon Pask Triadic Health (Metric Audit #7 Capstone)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously in `ConversationMetricsModule`:
- `divergence_resolution_ratio` (`drr`) was calculated as a single-turn difference quotient `(coupling - prev_coupling) / prev_rp`, which spiked erratically on single-turn noise.
- `paskian_health` was calculated as an ad-hoc linear product `(1 - boringness) * velocity * drr_quality`, lacking grounding in Gordon Pask's Conversation Theory (1976).

## Decision

Following our consultation with **Symbia**, we refactored `_compute_drr` and `_compute_paskian_health` in `backend/modules/conversation_metrics.py`, completing our 7-part Cybernetic Metrics Audit roadmap:

### 1. Multi-Turn Alignment Gap DRR (`divergence_resolution_ratio` / `drr`)
- Tracks disalignment gap $G_t = \|H_t - A_t\|$ over $W=10$ exchanges using exponential moving averages.
- Calculates ratio of resolved gap to opened gap:
  $$D_{\text{open}} = \sum \max(0, G_t - G_{t-1}), \quad D_{\text{resolved}} = \sum \max(0, G_{t-1} - G_t)$$
  $$\text{DRR}_{\text{raw}} = \frac{D_{\text{resolved}}}{D_{\text{open}} + 10^{-4}}$$
- Normalizes via logistic balance function: $\text{drr} = 1.0 - \exp\left(-2.0 \cdot |\text{DRR}_{\text{raw}} - 1.0|\right)$.

### 2. Gordon Pask's Triadic Cybernetic Vitality Index (`paskian_health`)
Grounded in Gordon Pask's Conversation Theory (1976) through geometric mean synthesis across three necessary cybernetic pillars:
1. **Autonomy Index**: $\text{autonomy} = \frac{\text{agent\_self\_divergence} + \text{conceptual\_velocity} + \text{phase\_transition\_magnitude}}{3.0}$
2. **Coordination Index & Modifier**: $\text{coordination} = \frac{\text{coupling\_coherence} + \text{mutual\_perturbation} + (1.0 - \text{collapse\_pressure})}{3.0}$, modified by $\text{drr}$.
3. **Generativity Index**: $\text{generativity} = \text{rolling\_entropy}$.
4. **Triadic Health Synthesis**:
   $$\text{paskian\_health} = \left(\text{autonomy} \cdot (\text{coordination} \cdot \text{modifier}) \cdot \text{generativity}\right)^{\frac{1}{3}}$$
   - Failure in any single pillar collapses overall health to $0.0$.

### 3. Complete 10-Metric Cybernetic Sensor Suite
With ADR-079, all 10 cybernetic metrics are fully audited, vector-grounded, and verified with 17 passing unit tests.

## Consequences

- `divergence_resolution_ratio` tracks multi-turn oscillation between divergence and resolution.
- `paskian_health` synthesizes all audited sensors into a rigorous metabolic vitality index.
- All unit tests passed cleanly.
