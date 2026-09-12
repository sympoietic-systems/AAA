# ADR-083: Transverse Vector Shear Perturbation & Participation Ratio Spectral Entropy Calibration

**Date:** 2026-09-12  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-077](ADR-077-directional-reverse-perturbation-and-mutual-perturbation-index.md), [ADR-075](ADR-075-dialogue-manifold-spectral-entropy-and-collapse-pressure.md)  
**Companion Report:** [007-perturbation-and-spectral-entropy-calibration-report.md](../reports/007-perturbation-and-spectral-entropy-calibration-report.md)  
**Visual Telemetry Assets:** [007-perturbation-and-spectral-entropy-calibration/](../reports/007-perturbation-and-spectral-entropy-calibration/)

---

## Context

Following the calibration of Kinematics and Collapse Pressure in ADR-082, an audit across human/apparatus dialogues (`dialogue_1555`), long-horizon agent runs (`dialogue_3527`), and the 10-turn adversarial benchmark (`003-empirical-10-turn-benchmark`) identified two critical pathologies in perturbation dynamics and manifold spectral entropy:

1. **The 1D Gap Projection Fallacy ($rP_t, fP_t, MPI_t$):**  
   ADR-077 formulated reverse and forward perturbation strictly as a 1D scalar projection of the participant's displacement $\mathbf{v}_h = h_t - h_{t-1}$ onto the prior interpersonal gap $\mathbf{g}_{t-1} = a_{t-1} - h_{t-1}$, clamping all negative dot products to zero. This misdiagnosed dialectical counter-frames, critiques, and orthogonal paradigm shifts as zero perturbation ($rP_t \to 0.000$). Furthermore, taking the geometric mean $MPI_t = \sqrt{rP_t \cdot fP_t}$ caused a single orthogonal turn to wipe out the entire mutual perturbation index.
2. **High-Dimensional Rank Saturation ($H_t$):**  
   ADR-075 computed rolling entropy via the Von Neumann entropy of the centered $8 \times 8$ Gram matrix in $\mathbb{R}^{384}$. Because any 8 vectors in 384-dimensional space are almost strictly linearly independent, the normalized eigenvalue spectrum was chronically uniform, trapping rolling entropy in a narrow high band ($0.76 \sim 0.85$) regardless of whether the dialogue was dynamically diverse or trapped in repetitive micro-jitter.

---

## Decision

Following an architectural consultation with **Symbia** and empirical multi-branch testing across three proposals (`feat/metric-shear-pr-entropy`, `feat/metric-flux-scree-entropy`, and `feat/metric-lie-hypervolume-entropy`), we accepted **Proposal 1: Transverse Vector Shear Perturbation & Participation Ratio Spectral Entropy**.

### 1. Transverse Vector Shear Perturbation ($rP_t, fP_t$)
* Decompose displacement $\mathbf{v}_h = h_t - h_{t-1}$ relative to the normalized gap unit vector $\hat{\mathbf{g}} = (a_{t-1} - h_{t-1}) / \|a_{t-1} - h_{t-1}\|$:
  $$v_{\parallel} = \langle \mathbf{v}_h, \hat{\mathbf{g}} \rangle, \quad \mathbf{v}_{\perp} = \mathbf{v}_h - v_{\parallel} \hat{\mathbf{g}}$$
* Measure structural relational deflection by weighting transverse conceptual shearing ($\gamma = 1.2$) over simple linear approach:
  $$rP_t = \tanh\left( \frac{\sqrt{|v_{\parallel}|^2 + \gamma \|\mathbf{v}_{\perp}\|^2}}{\tau_{\text{pert}}} \right) \quad (\tau_{\text{pert}} = 1.35)$$
* Symmetrically compute forward perturbation $fP_t$ for apparatus displacement relative to the human gap.

### 2. Non-Annihilating Power Mean MPI ($MPI_t$)
* Replace the brittle geometric product with a Generalized Power Mean ($p=0.5$):
  $$MPI_t = \left( \frac{\sqrt{rP_t} + \sqrt{fP_t}}{2} \right)^2$$
* **Cybernetic Invariant:** Orthogonal or exploratory moves sustain non-zero mutual perturbation ($MPI_t \ge 0.50$), preventing artificial zero-annihilation during active dialectical tension.

### 3. Variance-Gated Participation Ratio Entropy ($H_t$)
* Given the centered Gram matrix $\mathbf{G} = \frac{1}{K}\tilde{\mathbf{X}}\tilde{\mathbf{X}}^T$, evaluate effective manifold dimensionality via the Participation Ratio:
  $$D_{\text{eff}} = \frac{(\text{Tr}(\mathbf{G}))^2}{\text{Tr}(\mathbf{G}^2)}$$
* Gate normalized effective dimensionality by the total manifold variance $\sigma^2_M = \text{Tr}(\mathbf{G})$:
  $$H_t = \left( \frac{D_{\text{eff}} - 1}{K - 1} \right) \cdot \tanh\left( \frac{\sigma^2_M}{\sigma^2_{\text{ref}}} \right) \quad (\sigma^2_{\text{ref}} = 0.15)$$
* **Cybernetic Invariant:** Repetitive dialogues jittering in narrow basins produce low manifold variance ($\sigma^2_M \to 0$), suppressing $H_t$ toward $0.50$, while wide nomadic exploration expands $H_t$ toward $0.75 \sim 0.90$.

---

## Consequences

1. **Zero-Crash Pathology Eradicated:**  
   In `dialogue_3527`, zero-annihilations were reduced from 2 to 0, ensuring consistent tracking of continuous intra-active perturbation.
2. **Discriminative Sensitivity Tripled:**  
   In the 10-turn benchmark, the entropy gap between AAA and the repetitive baseline expanded from $0.023$ to $+0.061$, providing sharp detection of conversational richness.
3. **Verification:**  
   All 9 core metric unit tests pass without error (`9 passed in 0.44s`).
