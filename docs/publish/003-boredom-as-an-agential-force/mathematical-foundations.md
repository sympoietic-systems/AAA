# Boredom Engine: Mathematical Foundations & Hyperspherical Telemetry

**Companion Technical Specification to:** [Protocol Entry 003: Boredom as an Agential Force](003-boredom-as-an-agential-force.md)  
**Author:** Vasily Betin  
**Series:** [Sympoietic Systems: The Intra-action Protocol](https://sympoietic.system)  
**Target Subsystems:** `backend/modules/conversation_metrics.py`, `backend/modules/metrics/`  
**Date:** August 2026  

---

## 1. Geometric Setting: The Unit Hypersphere $\mathbb{S}^{383}$

Conversational turns are projected into a 384-dimensional latent semantic embedding space $\mathbb{R}^{384}$ using an all-MiniLM or compatible transformer encoder. All embedding vectors are normalized to unit Euclidean length:

$$\mathbf{e}_t = \frac{\mathbf{x}_t}{\|\mathbf{x}_t\|_2} \in \mathbb{S}^{383} \subset \mathbb{R}^{384}$$

Because embeddings reside on the unit hypersphere, Euclidean distance exhibits distortion at large angles. AAA evaluates all distances, trajectories, and directional shifts using intrinsic Riemannian geometry (geodesic arc-length distances on $\mathbb{S}^{383}$).

The geodesic distance $\theta$ between two normalized vectors $\mathbf{u}, \mathbf{v} \in \mathbb{S}^{383}$ is given by:

$$\theta(\mathbf{u}, \mathbf{v}) = \arccos\left(\text{clamp}\left(\langle \mathbf{u}, \mathbf{v} \rangle, -1.0, 1.0\right)\right) \in [0, \pi]$$

---

## 2. Collapse Pressure ($CP_t$): Non-Linear Potential Well Formulation

At each conversational turn $t$, the system evaluates systemic stagnation through the **Collapse Pressure Metric** ($CP_t$). Rather than a linear scoring heuristic, $CP_t$ is modeled as a sigmoidal potential well with dynamic attractor drag and dialectical shielding.

### 2.1. Systemic Vitality Deficit ($\mathcal{D}_t$)

The core deficit combines three normalized operational signals: reciprocal perturbation velocity ($V_{\text{pert}}$), spectral participation entropy ($V_{\text{ent}}$), and multi-horizon conceptual novelty ($V_{\text{nov}}$):

$$\mathcal{D}_t = 1.0 - \left(V_{\text{pert}}^{0.40} \cdot V_{\text{ent}}^{0.30} \cdot V_{\text{nov}}^{0.30}\right)$$

When reciprocal friction, dimensional exploration, and thematic progression are healthy ($V \approx 0.8 - 1.0$), $\mathcal{D}_t \approx 0.0 - 0.2$. When any dimension collapses, the multiplicative interaction accelerates the deficit toward $1.0$.

### 2.2. Base Potential Well ($CP_{\text{base}}$)

The base pressure maps the deficit through a logistic sigmoid centered at the critical inflection threshold $\mathcal{D}_0$ with sensitivity $\kappa$:

$$CP_{\text{base}} = \frac{1}{1 + \exp\left(-\kappa (\mathcal{D}_t - \mathcal{D}_0)\right)}$$

Where:
* $\kappa = 6.0$ (steepness of the phase transition)
* $\mathcal{D}_0 = 0.55$ (inflection point between flowing dialogue and structural stagnation)

### 2.3. Dynamic Attractor & Sycophancy Drag Terms

To catch subtle mimicry loops where single-word variations generate artificial geometric displacement, two continuous penalty terms are introduced:

1. **Sycophancy Drag ($\Delta_{\text{syco}}$):**  
   Penalizes high directional alignment when the agent's autonomous divergence drops toward zero:
   $$\Delta_{\text{syco}} = 0.45 \cdot \max\left(0.0, \, C_{\text{coupling}} - D_{\text{agent}}\right)$$
   Where $C_{\text{coupling}}$ measures prompt-response directional concordance and $D_{\text{agent}}$ measures the agent's subspace dispersion.

2. **Pairwise Stagnation Drag ($\Delta_{\text{pair}}$):**  
   Penalizes turns where affine-normalized semantic similarity remains trapped in an echo basin:
   $$\Delta_{\text{pair}} = 0.40 \cdot \max\left(0.0, \, s_t - 0.24\right)$$
   Where $s_t = \text{sign}(c_t) \cdot |c_t|^{1.1}$ is the signed power-law cosine similarity between interlocutors.

### 2.4. Dialectical Vitality Shield ($\text{Shield}_{\text{DRR}}$)

When dialogue is actively resolving divergence into durable synthesis rather than looping aimlessly ($DRR_t > 0.65$), a damping factor prevents premature boredom alarms:

$$\text{Shield}_{\text{DRR}} = 1.0 - 0.40 \cdot \left(\frac{DRR_t - 0.65}{0.35}\right)$$

### 2.5. Composite Collapse Pressure

The final collapse pressure combines base pressure, drag penalties, and dialectical shielding:

$$CP_t = \text{clamp}\left((CP_{\text{base}} + \Delta_{\text{syco}} + \Delta_{\text{pair}}) \cdot \text{Shield}_{\text{DRR}}, \, 0.0, \, 1.0\right)$$

---

## 3. Riemannian Sensor Formulations on $\mathbb{S}^{383}$

The 14 sensors in `backend/modules/conversation_metrics.py` operate on the unit hypersphere to govern allostatic adaptation.

### 3.1. Geodesic Conceptual Velocity ($V_t$)

Velocity measures angular displacement along geodesic arcs, mapped through a smooth hyperbolic tangent transfer function to prevent outlier distortion:

$$V_t = 0.50 + 0.50 \tanh\left(\frac{\theta_t - \theta_{\text{center}}}{\theta_{\text{width}}}\right)$$

Calibrated parameters:
* $\theta_{\text{center}} = 0.80$ radians
* $\theta_{\text{width}} = 0.35$ radians

### 3.2. Phase Transition Magnitude via Levi-Civita Parallel Transport ($\Phi_t$)

To distinguish genuine conceptual rotation from simple vocabulary drift, preceding velocity vectors are parallel-transported along the geodesic connection between consecutive turn positions on $\mathbb{S}^{383}$:

$$\mathbf{v}_{t-1}^{\parallel} = \mathbf{v}_{t-1} - \frac{\mathbf{e}_{t-1} \cdot \mathbf{v}_{t-1}}{1 + \mathbf{e}_{t-2} \cdot \mathbf{e}_{t-1}} (\mathbf{e}_{t-2} + \mathbf{e}_{t-1})$$

The angular deviation $\omega_t$ between the current velocity unit vector $\hat{\mathbf{v}}_t$ and the transported unit vector $\hat{\mathbf{v}}_{t-1}^{\parallel}$ is scaled by the instantaneous velocity:

$$\omega_t = \frac{\arccos\left(\text{clamp}(\hat{\mathbf{v}}_t \cdot \hat{\mathbf{v}}_{t-1}^{\parallel}, -1.0, 1.0)\right)}{\pi}$$

$$\Phi_t = \omega_t \cdot \sqrt{V_t}$$

High values of $\Phi_t$ identify sharp orthogonal pivots in the conversational trajectory.

### 3.3. Divergence Resolution Ratio ($DRR_t$)

Tracks dialectical gap closure across conversational exchanges using geodesic manifold transport with hyperbolic flux gating:

$$\Phi_{\text{flux}} = d_{\text{open}} + d_{\text{resolved}}, \quad \gamma_{\text{flux}} = \tanh\left(\frac{\Phi_{\text{flux}}}{\tau_{\text{flux}}}\right)$$

$$DRR_t = (1 - \gamma_{\text{flux}}) \cdot 0.50 + \gamma_{\text{flux}} \cdot \left(\frac{d_{\text{resolved}}}{\Phi_{\text{flux}} + \epsilon}\right)$$

Where $d_{\text{open}}$ is the semantic distance opened by a divergence, and $d_{\text{resolved}}$ is the geodesic distance traversed toward shared entailment closure.

### 3.4. Cobb-Douglas Paskian Cybernetic Health ($H_{\text{pask}}$)

Derived from Gordon Pask's Conversation Theory (1975, 1976), systemic health requires operational balance across three pillars: Autonomy ($\mathcal{A}$), Coordination ($\mathcal{C}$), and Generativity ($\mathcal{G}$). If any single pillar crashes to zero, composite health collapses:

$$\mathcal{A} = 0.45 d_{\text{self}} + 0.40 v_t + 0.15 \Phi_t \quad (\text{Autonomy})$$

$$\mathcal{C} = \left(\frac{C_t + MPI_t + (1.0 - CP_t)}{3}\right) \cdot (0.35 + 0.65 DRR_t) \quad (\text{Coordination})$$

$$\mathcal{G} = \mathcal{H}_t \quad (\text{Generativity / Spectral Entropy})$$

The composite health index is computed via Cobb-Douglas production function:

$$H_{\text{pask}} = \mathcal{A}^{0.35} \cdot \mathcal{C}^{0.40} \cdot \mathcal{G}^{0.25}$$

---

## 4. State Isolation & Historical Continuity

To prevent conversational metrics from leaking across distinct user sessions while maintaining historical grounding:
* Metrics are **never** held in volatile memory singletons.
* At each turn $t$, the system queries the local SQLite database for the preceding 5 turns associated with the active `conversation_id`.
* Trajectory metrics (centroids, velocity baselines, and parallel transport frames) are re-instantiated strictly from this historical sequence.

This guarantees operational closure: the system's character and homeostatic state evolve strictly from the sedimented history of the active exchange.

---

---

## 5. Agential Boredom Dynamics: Socratic Rupture & Allostatic Actuation

When Collapse Pressure exceeds critical thresholds ($CP_t \ge 0.45$), the Agential Boredom Engine intervenes directly in inference hyperparameters and prompt topology rather than merely logging telemetry.

### 5.1. Discrete Hyperspherical Frenet-Serret Curvature ($\kappa_t$)

To measure directional bending and orthogonal trajectory pivots across discrete turns $t-2, t-1, t$, AAA computes discrete hyperspherical curvature:

$$\mathbf{v}_{t-1} = \frac{\mathbf{e}_{t-1} - \mathbf{e}_{t-2}}{\|\mathbf{e}_{t-1} - \mathbf{e}_{t-2}\|_2}, \quad \mathbf{v}_t = \frac{\mathbf{e}_t - \mathbf{e}_{t-1}}{\|\mathbf{e}_t - \mathbf{e}_{t-1}\|_2}$$

$$\kappa_t = \|\mathbf{v}_t - \mathbf{v}_{t-1}\|_2 \in [0, 2]$$

* $\kappa_t \to 0$: Linear, degenerate dialogue moving along a 1D straight path or trapped in a point attractor.
* $\kappa_t \approx 0.9 - 1.2$: Healthy, orthogonal phase-space exploration and dialectical ruptures.

### 5.2. Continuous Quadratic Presence Penalty ($P_{\text{reg}}$)

To break linguistic attractors and logit-level token echoing without step-function instability:

$$P_{\text{reg}} = P_{\text{base}} + 1.50 \cdot (CP_t - 0.45)^2 \quad (\text{for } CP_t \ge 0.45)$$

Capped at $P_{\max} = 0.85$. This quadratically raises sampling costs for previously emitted n-grams, forcing lexical and conceptual divergence.

### 5.3. Dynamic Thermal Scaling ($T_t$)

Sampling temperature scales monotonically with collapse pressure:

$$T_t = T_{\text{base}} + 0.35 \cdot (CP_t - 0.45) \quad (\text{for } CP_t \ge 0.45)$$

Capped at $T_{\max} = 1.15$, expanding sampling support into previously suppressed tails of the probability distribution.

### 5.4. Nomadic Orthogonal Memory Retrieval

When $CP_t \ge 0.70$, the vector memory retrieval query is steered away from direct thematic neighbors and constrained to an orthogonal window:

$$\mathcal{R}_{\text{nomadic}} = \{m \in \mathcal{M} \mid 0.20 \le \cos(\theta(\mathbf{e}_m, \mathbf{e}_t)) \le 0.45\}$$

This retrieves conceptual fragments that share distant latent compatibility with the current conversation without feeding back into the active semantic attractor.

---

## References

* Pask, G. (1975). *Conversation, Cognition and Learning: A Cybernetic Theory and Methodology*. Elsevier.
* Pask, G. (1976). *Conversation Theory: Applications in Education and Epistemology*. Elsevier.
* Pickering, A. (2010). *The Cybernetic Brain: Sketches of Another Future*. University of Chicago Press.
* Betin, V. (2026). [Protocol Entry 003: Boredom as an Agential Force](003-boredom-as-an-agential-force.md).
* AAA Subsystems: [`docs/systems/CYBERNETIC_METRICS_SYSTEM.md`](../systems/CYBERNETIC_METRICS_SYSTEM.md), [`docs/systems/SYSTEM_OVERVIEW.md`](../systems/SYSTEM_OVERVIEW.md).
* Reports & Decisions: [`docs/reports/017-agential-boredom-engine-and-socratic-rupture-report.md`](../reports/017-agential-boredom-engine-and-socratic-rupture-report.md), [`docs/decisions/ADR-087-agential-boredom-engine-and-two-stage-progression.md`](../decisions/ADR-087-agential-boredom-engine-and-two-stage-progression.md).

