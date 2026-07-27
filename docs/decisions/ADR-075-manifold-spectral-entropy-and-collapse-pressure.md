# ADR-075: Manifold Spectral Entropy & Collapse Pressure Index (Metric Audit #3)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously in `ConversationMetricsModule`:
- `rolling_entropy` was calculated as a scalar variance of dot-product similarity pairs across consecutive turns. This 1D proxy could not distinguish between a 2-pole oscillation and genuine multi-dimensional semantic exploration.
- `boringness` was calculated as $(1 - \text{rP}_t) \cdot (1 - \text{prev\_mpi})$, an affective label that double-counted perturbation and ignored entropy/novelty failure modes.

## Decision

Following our consultation with **Symbia**, we refactored `_compute_rolling_entropy` and `_compute_collapse_pressure` in `backend/modules/conversation_metrics.py`:

### 1. Manifold Spectral Entropy (`rolling_entropy`)
1. **Centered Embedding Matrix**: $E = [\vec{e}_1, \vec{e}_2, \dots, \vec{e}_K] \in \mathbb{R}^{384 \times K}$, centered by subtracting mean embedding $\bar{\mu}_E$.
2. **Gram Matrix Eigendecomposition**: $C' = \frac{1}{K} \bar{E}^T \bar{E} \in \mathbb{R}^{K \times K}$.
3. **Shannon Entropy & Normalization**:
   $$H_{\text{raw}} = -\sum_{i=1}^K p_i \ln(p_i), \quad \text{rolling\_entropy} = \frac{H_{\text{raw}}}{\ln(K)}$$
   - Scores near $1.0$ when embeddings span $K$ independent dimensions, and near $0.0$ on 1D collapse.

### 2. Collapse Pressure Index (`collapse_pressure` / `boringness`)
- Renamed from `boringness` to `collapse_pressure` to name the cybernetic structural condition rather than an affective label.
- Triadic factorization of independent failure modes:
  $$\text{perturbation\_failure} = 1.0 - \sqrt{\max(0.0, \text{rP}_t \cdot \text{prev\_mpi})}$$
  $$\text{collapse\_pressure} = \text{perturbation\_failure} \cdot (1.0 - \text{rolling\_entropy}) \cdot (1.0 - \text{conceptual\_novelty})$$
- Retained `boringness` key in payload for backward compatibility.

### 3. Self-Initiation Arbiter Trigger Integration
- Updated `SelfInitiationArbiterModule` to trigger spontaneous sediment gratings when `collapse_pressure > 0.70`.

## Consequences

- `rolling_entropy` measures the true effective dimensionality of semantic space.
- `collapse_pressure` detects structurally stagnating equilibrium death basins.
- All unit tests passed cleanly.
