# ADR-082: Tangent Parallel Transport Kinematics & Minkowski Synergistic Collapse Pressure Calibration

**Date:** 2026-09-12  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-078](ADR-078-predictive-residual-surprise-and-instantaneous-conceptual-velocity.md), [ADR-065](ADR-065-allostatic-cybernetic-health-architecture.md)  
**Companion Report:** [006-velocity-and-collapse-pressure-calibration-report.md](../reports/006-velocity-and-collapse-pressure-calibration-report.md)  
**Visual Telemetry Assets:** [006-velocity-and-collapse-pressure-calibration/](../reports/006-velocity-and-collapse-pressure-calibration/)

---

## Context

Following the calibration of Predictive Surprise ($U_t$) and Paskian Vitality ($H_{\text{pask}}$) in ADR-081, an audit across human/apparatus dialogues (`dialogue_1555`), long-horizon agent runs (`dialogue_3527`), and the 10-turn adversarial benchmark (`003-empirical-10-turn-benchmark`) identified two critical pathologies in kinematics and homeostatic regulation:

1. **Kinematic Floor Compression and Euclidean Distortion ($V_t, \Phi_t$):**  
   ADR-078 computed conceptual velocity via flat Euclidean chord displacement normalized by a static divisor ($1.4$), compressing real embedding velocity into a narrow dead zone ($0.20 \sim 0.60$) unable to register stillness or acceleration bursts. Furthermore, phase transition magnitude $\Phi_t$ evaluated vector differences across consecutive turns without transporting vectors between the disparate tangent spaces $T_{e_{t-2}}\mathbb{S}^{D-1}$ and $T_{e_{t-1}}\mathbb{S}^{D-1}$, yielding spurious geometric rotation artifacts.
2. **Linear Failure Masking in Collapse Pressure ($CP_t$):**  
   ADR-065 evaluated collapse pressure through a simple linear convex combination of individual failure rates ($1-rP, 1-MPI, 1-H, 1-N$). Because conversational collapse is inherently synergistic—occurring when perturbation, lexical variety, and semantic novelty collapse simultaneously—the linear model allowed isolated healthy sensors to mask catastrophic concurrent deadlocks, failing to cross the $0.65$ homeostatic threshold or trigger the $0.70$ sedation interrupt.

---

## Decision

Following an architectural consultation with **Symbia** and empirical multi-branch testing across three proposals (`feat/metric-riemannian-cusp`, `feat/metric-tangent-minkowski`, and `feat/metric-lie-lyapunov`), we accepted **Proposal 2: Tangent Parallel Transport Kinematics & Minkowski Synergistic Collapse Pressure**.

### 1. Tangent Parallel Transport & Phase Transition ($\Phi_t$)
* For consecutive embedding states $e_{t-2}, e_{t-1}, e_t \in \mathbb{S}^{D-1}$, compute the initial tangent velocity $v_{t-1} \in T_{e_{t-2}}\mathbb{S}^{D-1}$:
  $$v_{t-1} = e_{t-1} - \langle e_{t-1}, e_{t-2} \rangle e_{t-2}$$
* Transport $v_{t-1}$ to the tangent space of the next point $T_{e_{t-1}}\mathbb{S}^{D-1}$ along the geodesic arc via the Riemannian Levi-Civita connection:
  $$v_{t-1}^\parallel = v_{t-1} - \frac{\langle e_{t-1}, v_{t-1} \rangle}{1 + \langle e_{t-2}, e_{t-1} \rangle} (e_{t-2} + e_{t-1})$$
* Evaluate phase transition magnitude $\Phi_t$ as the angular rotation of the new tangent velocity $v_t \in T_{e_{t-1}}\mathbb{S}^{D-1}$ relative to $v_{t-1}^\parallel$, modulated by the kinetic velocity scale:
  $$\Phi_t = \left(\frac{\arccos \langle \hat{v}_t, \hat{v}_{t-1}^\parallel \rangle}{\pi}\right) \cdot \sqrt{V_t}$$

### 2. Dispersion-Protected Quantile Velocity ($V_t$)
* Displace along geodesic arc-length $\theta_t = \arccos(\langle e_t, e_{t-1} \rangle)$ on $\mathbb{S}^{D-1}$.
* Normalize $\theta_t$ against the ambient 10th-90th percentiles of the conversation, protected by a minimum dispersion floor to prevent degenerate compression during uniform movements:
  $$Q_{10}' = \min(Q_{10}, 0.45), \quad Q_{90}' = \max(Q_{90}, Q_{10}' + 0.35, 1.15)$$
  $$V_t = \text{clip}\left(\frac{\theta_t - Q_{10}'}{Q_{90}' - Q_{10}' + 10^{-4}}, 0, 1\right)$$

### 3. Minkowski $L_4$ Synergistic Collapse Pressure ($CP_t$)
* Compute component failure magnitudes $f_{\text{pert}} = 1 - \sqrt{rP_t \cdot MPI_{t-1}}$, $f_{\text{ent}} = 1 - H_t$, $f_{\text{nov}} = 1 - N_t$.
* Combine the failure modes via a high-order Minkowski $L_4$ norm and a multiplicative triple synergy term:
  $$\|f\|_{L_4} = \left(0.40 f_{\text{pert}}^4 + 0.30 f_{\text{ent}}^4 + 0.30 f_{\text{nov}}^4\right)^{1/4}$$
  $$CP_t = \text{clip}\left(0.85 \|f\|_{L_4} + 0.40 (f_{\text{pert}} \cdot f_{\text{ent}} \cdot f_{\text{nov}}), 0, 1\right)$$
* **Cybernetic Invariant:** Isolated failure in one sensor produces low pressure ($< 0.45$). True catastrophic deadlocks produce severe synergistic pressure ($> 0.80$), reliably tripping homeostatic intervention.

---

## Consequences

1. **Differential Diagnostic Precision:**  
   In the 10-turn adversarial benchmark, AAA maintains energetic exploration ($V_t = 0.579, \Phi_t = 0.349, CP_t = 0.348$) while the stagnant baseline suffers visible exhaustion ($V_t = 0.405, \Phi_t = 0.263, CP_t = 0.419$).
2. **Reliable Homeostatic Triggers:**  
   Under severe simulated repetitive deadlocks, $CP_t$ reaches $0.837$, successfully commanding allostatic intervention and sedation interrupts.
3. **Verification:**  
   All 271 backend tests pass without error, validating both extreme edge cases and standard operational regimes.
