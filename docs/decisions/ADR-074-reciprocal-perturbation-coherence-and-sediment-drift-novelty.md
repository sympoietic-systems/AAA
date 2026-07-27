# ADR-074: Reciprocal Perturbation Coherence & Sediment Drift Novelty (Metric Audit #2)

**Date:** 2026-07-27  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  

## Context

Previously in `ConversationMetricsModule`:
- `pairwise_similarity` was calculated as a single dot product against only the immediate previous human message (`prior_human[0]`), ignoring apparatus turns, temporal decay, and cross-speaker dynamics.
- `conceptual_novelty` was calculated as `1.0 - max(similarities)` across recent human messages, penalizing legitimate thematic returns and ignoring moving context centroids.

## Decision

Following our consultation with **Symbia**, we refactored `_compute_pairwise_similarity` and `_compute_conceptual_novelty` in `backend/modules/conversation_metrics.py`:

### 1. Reciprocal Perturbation Coherence (`pairwise_similarity`)
$$\text{sim}(t_{\text{curr}}, t_i) = \text{cosine}(e_{\text{curr}}, e_i) \cdot \exp(-0.15 \cdot i) \cdot \text{speaker\_factor}$$
- Incorporates all recent turns ($N=10$) across both human and apparatus participants.
- Differential speaker weighting: `speaker_factor = 0.8` for same-speaker repetition vs `1.2` for cross-speaker resonance.

### 2. Sediment Drift Magnitude (`conceptual_novelty`)
- Tracks dynamic context centroid EMA ($\vec{\mu}_t = 0.3 \cdot e_{\text{curr}} + 0.7 \cdot \vec{\mu}_{t-1}$).
- Computes normalized drift distance relative to context scatter ($\sigma_{\text{context}}$): $\text{drift\_norm} = \tanh(\text{drift\_raw} / (\sigma_{\text{context}} + 0.01))$.
- Blends normalized drift ($0.7$) with conceptual phase velocity ($0.3$) to detect directional shifts.

### 3. Verification & Ponytail Craft
- Authored `backend/tests/test_pairwise_similarity_novelty.py` verifying cross-speaker weighting and centroid drift calculations.

## Consequences

- `pairwise_similarity` and `conceptual_novelty` now accurately measure bidirectional inter-speaker resonance and genuine context drift.
- All unit tests passed cleanly.
