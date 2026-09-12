# ADR-084: Softmin Subspace Self-Divergence & Dual-Horizon Novelty Calibration

**Date:** 2026-09-12  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-076](ADR-076-trajectory-coupling-coherence-and-agent-self-divergence.md), [ADR-074](ADR-074-conversational-novelty-and-semantic-drift-detection.md)  
**Companion Report:** [008-resonance-and-self-divergence-calibration-report.md](../reports/008-resonance-and-self-divergence-calibration-report.md)  
**Visual Telemetry Assets:** [008-resonance-and-self-divergence-calibration/](../reports/008-resonance-and-self-divergence-calibration/)

---

## Context

Following the calibration of Perturbation Dynamics and Spectral Entropy in ADR-083, an audit across dialogue corpuses identified critical geometric pathologies in the remaining resonance sensors:

1. **Chebyshev Bottleneck in Self-Divergence ($D_{\text{self}}$):**  
   ADR-076 evaluated self-similarity as the maximum decayed cosine similarity across the past 5 agent turns. If an agent revisited an anchor concept, the maximum spiked, forcing divergence down to $\sim 0.45$ even when the agent was exploring a broad multi-dimensional conceptual space.
2. **Silt Decay in Conceptual Novelty ($N_t$):**  
   ADR-074 tracked context drift relative to a single-rate EMA centroid. In long-horizon conversations ($T > 100$), the centroid drifted toward the global semantic mean, dragging novelty scores down to an exhausted $0.306$.
3. **Dialectical Polarity Erasure ($s_t$):**  
   Pairwise similarity clamped negative cosine similarity to $0.0$, treating direct dialectical opposition identically to orthogonal disengagement.

---

## Decision

Following consultation with **Symbia** and empirical testing across three candidate branches, we accepted **Proposal 1: Softmin Subspace Self-Divergence & Dual-Horizon Novelty**.

### 1. Softmin Subspace Self-Divergence ($D_{\text{self}}$)
* Replace the brittle maximum operator with a temperature-scaled Log-Sum-Exp Softmin over cosine distances $d_k = 1 - \langle a_t, a_{t-k} \rangle$:
  $$D_{\text{soft}} = \min(d) - \frac{1}{\beta} \ln \left( \frac{1}{K} \sum_{k=1}^K e^{-\beta (d_k - \min(d))} \right) \quad (\beta = 4.0)$$
* Scale by the effective matrix rank $\text{RankEff} = \frac{\text{Tr}(\mathbf{A}\mathbf{A}^T)^2}{\text{Tr}((\mathbf{A}\mathbf{A}^T)^2)}$:
  $$D_{\text{self}} = \tanh\left(\frac{D_{\text{soft}}}{0.65}\right) \cdot \left(0.40 + 0.60 \sqrt{\frac{\text{RankEff} - 1}{K - 1}}\right)$$

### 2. Dual-Horizon Leaky Attractor Novelty ($N_t$)
* Maintain two independent leaky centroids:
  - Local trajectory centroid $\mathbf{c}_{\text{fast}}$ ($\tau = 4$, $\alpha = 0.35$).
  - Global basin centroid $\mathbf{c}_{\text{slow}}$ ($\tau = 16$, $\alpha = 0.08$).
* Evaluate novelty as the geometric mean of local rupture and global macro-basin detachment:
  $$N_t = \tanh\left( \frac{\sqrt{\arccos\langle e_t, \mathbf{c}_{\text{fast}} \rangle \cdot \arccos\langle e_t, \mathbf{c}_{\text{slow}} \rangle}}{1.35} \right)$$

### 3. Signed Polarity Pairwise Alignment ($s_t$)
* Preserve negative alignment for dialectical tension:
  $$s_t = \text{sign}(\langle h_t, a_t \rangle) \cdot |\langle h_t, a_t \rangle|^{1.1} \in [-1, 1]$$

---

## Consequences

1. **Novelty Vitality Sustained Over Long Horizons:**  
   In `dialogue_3527`, novelty is protected from silt decay, maintaining a vibrant $0.517 \pm 0.064$ across all 200 turns.
2. **Subspace-Aware Self-Divergence:**  
   Self-divergence cleanly reflects multi-dimensional exploration ($0.593 \sim 0.670$) without being tripped by single thematic anchor words.
3. **Verification:**  
   All 9 core metric unit tests pass (`9 passed in 0.42s`).
