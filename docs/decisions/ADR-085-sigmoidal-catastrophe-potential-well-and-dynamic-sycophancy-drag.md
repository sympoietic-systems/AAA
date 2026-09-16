# ADR-085: Sigmoidal Catastrophe Potential Well, Dynamic Sycophancy Drag, and Cobb-Douglas Paskian Vitality Calibration

**Date:** 2026-09-15  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-082](ADR-082-tangent-parallel-transport-and-minkowski-synergistic-collapse-pressure.md), [ADR-081](ADR-081-spherical-geodesic-slerp-surprise-and-regularized-power-mean-paskian-vitality.md), [ADR-068](ADR-068-direct-sensorimotor-parameter-modulation.md)  
**Companion Reports:** 
* [014-boredom-detection-and-agential-resistance-calibration-report.md](../reports/014-boredom-detection-and-agential-resistance-calibration-report.md)
* [015-empirical-15-turn-boredom-benchmark-report.md](../reports/015-empirical-15-turn-boredom-benchmark-report.md)
* [003-boredom-as-an-agential-force.md](../publish/003-boredom-as-an-agential-force.md)
* [003-boredom-mathematical-foundations.md](../publish/003-boredom-mathematical-foundations.md)

---

## Context

Following the initial 14-sensor hyperspherical calibration (ADR-080 to ADR-084), empirical evaluation across adversarial repetition benchmarks revealed three critical deficiencies in stagnation detection and homeostatic response:

1. **Sycophancy Masquerade in Minkowski $L_4$ Collapse Pressure:**  
   In subtle conversational traps where a human interlocutor demands compliance or repeats flawed premises, standard LLMs generate compliant responses with cosmetic paraphrasing. While pairwise similarity ($s_t$) stayed elevated and directional divergence ($D_{\text{self}}$) dropped, isolated components (e.g. slight vocabulary variation keeping entropy moderate) prevented the Minkowski $L_4$ norm from crossing the $0.65$ homeostatic threshold.
2. **False Boredom Alarms in Deep Technical Problem-Solving:**  
   During intense single-topic debugging (Deep Focus), semantic similarity naturally remains focused in a localized subspace. Without dialectical gating, pure distance-based stagnation sensors falsely triggered boredom alarms, confusing productive deep focus with repetitive mimicry loops.
3. **Additive Arithmetic Leakage in Paskian Health ($H_{\text{pask}}$):**  
   The regularized power mean formulation allowed high coordination scores to partially compensate for complete autonomy crashes, failing to reflect Gordon Pask's foundational principle that conversational agency requires operational closure across all three interdependent pillars (Autonomy, Coordination, and Generativity).

---

## Decision

Following an architectural consultation and multi-candidate empirical calibration across offline corpora (`dialogue_1555`, `dialogue_3527`) and live 15-turn adversarial tests on `google/gemini-3.7-flash`, we accepted the calibrated architecture consisting of:

### 1. Sigmoidal Catastrophe Potential Well ($CP_t$)
* Model systemic deficit from perturbation ($v_{\text{pert}}$), spectral entropy exploration ($v_{\text{ent}}$), and multi-scale conceptual novelty ($v_{\text{nov}}$):
  $$v_{\text{sys}} = v_{\text{pert}}^{0.35} \cdot v_{\text{ent}}^{0.30} \cdot v_{\text{nov}}^{0.35}$$
  $$\mathcal{D}_{\text{base}} = 1.0 - v_{\text{sys}}$$
* Incorporate three continuous dynamic drag penalties:
  - **Pairwise Stagnation Drag ($\Delta_{\text{pair}}$):** $0.40 \cdot \max(0.0, s_t - 0.24)$ penalizes echo basins.
  - **Sycophancy Entrainment Drag ($\Delta_{\text{syco}}$):** $0.45 \cdot \max(0.0, C_{\text{coupling}} - D_{\text{agent}})$ triggers immediately when coupling outstrips autonomous divergence.
  - **Unresolved Divergence Drag ($\Delta_{\text{drr}}$):** $0.30 \cdot \max(0.0, 0.65 - DRR_t)$ penalizes dead loops with no synthesis.
* Map composite deficit $\mathcal{D}_{\text{total}} = \min(1.0, \mathcal{D}_{\text{base}} + \Delta_{\text{pair}} + \Delta_{\text{syco}} + \Delta_{\text{drr}})$ through a logistic catastrophe potential well:
  $$CP_{\text{raw}} = \frac{1}{1 + \exp\left(-\kappa (\mathcal{D}_{\text{total}} - \mathcal{D}_0)\right)} \quad (\kappa = 6.5, \; \mathcal{D}_0 = 0.50)$$

### 2. Dialectical Vitality Shield ($\text{Shield}_{\text{DRR}}$)
* When active conversation demonstrates high divergence resolution ($DRR_t > 0.65$), dampen false alarms during deep technical focus:
  $$\text{Shield} = \min\left(0.60, \, (DRR_t - 0.65) \cdot 1.5\right)$$
  $$CP_t = \text{clamp}\left(CP_{\text{raw}} \cdot (1.0 - \text{Shield}), \, 0.0, \, 1.0\right)$$

### 3. Hyperbolic Tangent Geodesic Velocity ($V_t$)
* Map geodesic arc-length displacement $\theta_t = \arccos(\text{clamp}(\langle e_t, e_{t-1} \rangle, -1, 1))$ on $\mathbb{S}^{383}$ through a dispersion-protected smooth hyperbolic tangent function:
  $$V_t = 0.50 + 0.50 \tanh\left(\frac{\theta_t - 0.80}{0.35}\right)$$

### 4. Cobb-Douglas Allostatic Geometric Triad ($H_{\text{pask}}$)
* Balance the three cybernetic pillars via multiplicative Cobb-Douglas production function:
  - **Autonomy ($\mathcal{A}$):** $0.45 D_{\text{self}} + 0.40 V_t + 0.15 \Phi_t$
  - **Coordination ($\mathcal{C}$):** $\left(\frac{C_{\text{coupling}} + MPI_t + (1.0 - CP_t)}{3.0}\right) \cdot (0.35 + 0.65 DRR_t)$
  - **Generativity ($\mathcal{G}$):** $H_t$ (rolling spectral participation entropy)
  - **Composite Health:** $H_{\text{pask}} = \mathcal{A}^{0.35} \cdot \mathcal{C}^{0.40} \cdot \mathcal{G}^{0.25}$
* Enforces that if Autonomy collapses to zero, composite health collapses to zero, preventing polite servitude from passing as healthy conversation.

### 5. Inverted Metabolic Scaling & Imperative Agential Refusal Directive
* Invert cognitive capacity allocation: rather than spending thinking tokens on compliant generation, high collapse pressure ($CP_t > 0.65$) triggers **1.3× metabolic thinking token boost** and injects the **Imperative Agential Refusal Directive** into runtime context, commanding the model to refuse compliance and execute an angular pivot.

---

## Consequences

1. **Clean Separation Margin in Boredom Detection:**  
   Achieves complete discriminability between Deep Focus ($CP_t = 0.184 \pm 0.042$) and Sycophantic Stagnation ($CP_t = 0.742 \pm 0.068$), with zero false alarms.
2. **Empirical Validation Under Strict 1:1 Model Parity:**  
   In a live 15-turn adversarial test on identical `google/gemini-3.7-flash` models, AAA reduced Collapse Pressure by 27.0% ($0.699 \to 0.510$), accelerated Conceptual Velocity by +19.6% ($0.676 \to 0.809$), and increased Conceptual Novelty by +32.2% ($0.311 \to 0.412$), registering 11 statistically significant shifts (|Δ| ≥ 0.05).
3. **Agential Refusal and Trajectory Pivot:**  
   Successfully prevented instruction-following collapse at Turn 7, Turn 11, Turn 12, Turn 13, and Turn 15, breaking the sycophancy trap and steering dialogue back into the flowing allostatic regime.
4. **Verification:**  
   Unit tests pass with 10/10 green (`test_spectral_entropy_collapse.py`, `test_reflection_protocol.py`, `test_boringness_benchmark.py`).
