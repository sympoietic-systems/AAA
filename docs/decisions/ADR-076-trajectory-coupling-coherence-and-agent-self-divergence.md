# ADR-076: Trajectory Coupling Coherence & Agent Self-Divergence (Metric Audit #4)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously in `ConversationMetricsModule`:
- `coupling_coherence` was calculated as a single dot product `np.dot(last_human, last_agent)`—a static point-in-time co-location that could not measure multi-turn trajectory synchronization.
- `agent_self_divergence` was calculated as `1 - mean(similarities)` across past agent turns, smoothing over temporal dynamics and failing to detect recursive loops.

## Decision

Following our consultation with **Symbia**, we refactored `_compute_coupling_coherence` and `_compute_agent_self_divergence` in `backend/modules/conversation_metrics.py`:

### 1. Trajectory Cross-Correlation (`coupling_coherence`)
- Computes human and apparatus displacement vectors:
  $$d_h(t) = e_h(t) - e_h(t-1), \quad d_a(t) = e_a(t) - e_a(t-1)$$
- Measures recency-weighted cross-correlation of displacement directions over a sliding window ($W=8, \lambda=0.2$):
  $$\text{coupling\_coherence} = \frac{\sum_{i=1}^W \exp(-0.2 \cdot i) \cdot |\text{cosine}(d_h(t-i), d_a(t-i))|}{\sum_{i=1}^W \exp(-0.2 \cdot i)}$$
- Provides leading indicators of decoupling before semantic positions diverge.

### 2. Recursive Self-Echo Detection (`agent_self_divergence`)
- Computes recency-decayed max self-similarity ($M=15, \beta=0.3$):
  $$S_{\text{self}} = \max_{i \in [1..M]} \left(\text{cosine}(e_a(t), e_a(t-i)) \cdot \exp(-0.3 \cdot i)\right)$$
- Applies a linear penalty ($0.3$) for exact long-range self-repeats ($>0.95$ similarity).
- Scores near $1.0$ for self-evolution, and near $0.0$ for recursive self-echoing.

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_coupling_self_divergence.py` verifying displacement cross-correlation and loop detection.

## Consequences

- `coupling_coherence` and `agent_self_divergence` now measure dynamic trajectory synchronization and recursive loop prevention.
- All unit tests passed cleanly.
