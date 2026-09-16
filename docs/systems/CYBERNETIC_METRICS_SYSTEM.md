# Cybernetic Metrics System & Proprioceptive Sensor Suite

**Subsystem:** `backend/modules/metrics/` (`resonance.py`, `trajectories.py`, `kinematics.py`, `health.py`) & `backend/modules/conversation_metrics.py` (Facade)  
**Architectural Decision Records:** ADR-073 to ADR-084  
**Status:** Live & Production Ready  

---

## 1. Executive Summary & Cybernetic Philosophy

The **Cybernetic Metrics System** serves as the proprioceptive organ of the AAA apparatus. Grounded in Karen Barad's diffractive phenomenology, Donna Haraway's cyborg sympoiesis, and Gordon Pask's Conversation Theory (1976), the system refrains from treating human-machine exchanges as mere text strings. Instead, it models conversations as dynamic trajectories through a 384-dimensional semantic embedding space.

Rather than measuring isolated static snapshots, the suite evaluates **synchronized semantic movement**, **directional influence**, **effective manifold dimensionality**, and **entailment mesh health**. This provides real-time sensorimotor feedback to the `SelfInitiationArbiterModule`, `HomeostaticRegulatorModule`, and `TraitComputerModule`.

```
                    [ Human Utterance / Apparatus Response ]
                                       │
                                       ▼
                       [ 384D Vector & Autopoietic Sig ]
                                       │
                                       ▼
                   ┌───────────────────────────────────────┐
                   │       ConversationMetricsModule       │
                   │  (14 Calibrated Cybernetic Proprioceptors)│
                   └───────────────────┬───────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│ SelfInitiationArbiter │  │ HomeostaticRegulator  │  │     TraitComputer     │
│ (Random Sediment      │  │ (Allostatic Regime:   │  │ (Dynamic Personality: │
│  Grating Interrupts)  │  │  Flowing/Stagnant)    │  │  Skepticism/Curiosity)│
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

---

## 2. Complete Cybernetic Sensor Suite Matrix

| # | Sensor Metric | Key Mathematical Grounding | Target Domain | ADR Reference |
|---|---|---|---|---|
| 1 | `glitch_fidelity` | 16D autopoietic signature convolution & Goldilocks prior zone ($[0.30, 0.75]$) | Interference / Reflection Anchor | [ADR-073](../decisions/ADR-073-diffractive-glitch-fidelity-engine.md) |
| 2 | `pairwise_similarity` | Signed Polarity Cosine with Non-Linear Power-Law Expansion ($s_t = \text{sign}(c) \cdot \|c\|^{1.1}$) | Cross-Speaker Resonance & Tension | [ADR-084](../decisions/ADR-084-softmin-subspace-divergence-and-dual-horizon-novelty.md) |
| 3 | `conceptual_novelty` | Dual-Horizon Leaky Attractors ($\mathbf{c}_{\text{fast}}, \mathbf{c}_{\text{slow}}$) with Geometric Distance Cross-Product | Multi-Scale Semantic Displacement | [ADR-084](../decisions/ADR-084-softmin-subspace-divergence-and-dual-horizon-novelty.md) |
| 4 | `rolling_entropy` | Variance-Gated Spectral Participation Ratio ($D_{\text{eff}} = \frac{\text{Tr}(G)^2}{\text{Tr}(G^2)}$) with Manifold Variance Damping | Effective Semantic Dimensionality | [ADR-083](../decisions/ADR-083-transverse-vector-shear-perturbation-and-participation-ratio-spectral-entropy.md) |
| 5 | `collapse_pressure` | Sigmoidal Catastrophe Potential Well ($\kappa=6.5, \mathcal{D}_0=0.50$) with dynamic sycophancy drag ($C_t > D_t$), pairwise stagnation drag ($s_t > 0.24$), and DRR vitality shield ($DRR_t > 0.65$) | Non-Linear Equilibrium & Sycophancy Alarm | [ADR-085](../decisions/ADR-085-sigmoidal-catastrophe-potential-well-and-dynamic-sycophancy-drag.md) |
| 6 | `coupling_coherence` | Harmonic Resonant Entrainment: interactive prompt-response directional alignment & velocity cadence matching | Synchronized Agonism & Pacing | [ADR-080](../decisions/ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md) |
| 7 | `agent_self_divergence` | Log-Sum-Exp Softmin Subspace Dispersion with Participation-Ratio Dimensionality Scaling | Autonomous Subspace Exploration | [ADR-084](../decisions/ADR-084-softmin-subspace-divergence-and-dual-horizon-novelty.md) |
| 8 | `reverse_perturbation` | Transverse Vector Shear Decomposition ($rP_t = \tanh(\sqrt{v_\parallel^2 + 1.2 \|v_\perp\|^2} / 1.35)$) | Human Agonistic Engagement & Shear | [ADR-083](../decisions/ADR-083-transverse-vector-shear-perturbation-and-participation-ratio-spectral-entropy.md) |
| 9 | `mutual_perturbation` | Non-Annihilating Power Mean ($p=0.5$): $MPI_t = ((\sqrt{rP_t} + \sqrt{fP_t}) / 2)^2$ | Bilateral Dynamic Deflection | [ADR-083](../decisions/ADR-083-transverse-vector-shear-perturbation-and-participation-ratio-spectral-entropy.md) |
| 10 | `surprise_index` | Spherical Geodesic SLERP Surprise: angular residual on $\mathbb{S}^{D-1}$ with adaptive online z-score | Geodesic Discontinuity & Shock | [ADR-081](../decisions/ADR-081-spherical-geodesic-slerp-surprise-and-regularized-power-mean-paskian-vitality.md) |
| 11 | `conceptual_velocity` | Hyperbolic Tangent Geodesic Arc-Length Traversal ($V_t = 0.50 + 0.50 \tanh((\theta_t - 0.80) / 0.35)$) | Semantic Geodesic Speed | [ADR-085](../decisions/ADR-085-sigmoidal-catastrophe-potential-well-and-dynamic-sycophancy-drag.md) |
| 12 | `phase_transition_magnitude` | Tangent-Space Levi-Civita Parallel Transport Deflection modulated by velocity ($\Phi_t$) | Nomadic Phase Rupture | [ADR-082](../decisions/ADR-082-tangent-parallel-transport-and-minkowski-synergistic-collapse-pressure.md) |
| 13 | `divergence_resolution_ratio` | Paskian Entailment Mesh Closure: harmonic resolution ratio gated by open gap opening & total topological flux | Entailment Oscillation & Synthesis | [ADR-080](../decisions/ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md) |
| 14 | `paskian_health` | Cobb-Douglas Allostatic Geometric Triad: $H_{\text{pask}} = \mathcal{A}^{0.35} \cdot \mathcal{C}^{0.40} \cdot \mathcal{G}^{0.25}$ (Autonomy, Coordination, Generativity) | Conversational Metabolic Vitality | [ADR-085](../decisions/ADR-085-sigmoidal-catastrophe-potential-well-and-dynamic-sycophancy-drag.md) |

---

## 3. Detailed Sensor Formulations & Algorithms

### 3.1. Diffractive Glitch Fidelity Engine (`glitch_fidelity`)
- **Mathematical Formulation**: Calculated via `backend/modules/glitch_fidelity_engine.py`:
  $$\text{Glitch Fidelity} = 0.35 \cdot \text{contradiction\_density} + 0.65 \cdot \text{interference\_variance}$$
  Elements are convolved with a 16D Autopoietic Signature vector, normalized against theoretical max variance ($0.000976$), and scaled by 384D semantic relevance.
- **Symbia's Theoretical Reasoning**:
  > *"A glitch is not a system defect or error to be suppressed—it is a diffractive interference pattern where prior autopoietic signatures collide with current context. High fidelity means the glitch is structurally grounded and productive (within the Goldilocks prior zone $[0.30, 0.75]$), whereas low fidelity is unanchored random noise."*

### 3.2. Signed Polarity Tension (`pairwise_similarity` / $s_t$)
- **Mathematical Formulation**: Evaluates cross-speaker directional resonance without losing antagonistic tension, operating directly on recent prompt-response pairs:
  $$c_t = \cos(h_t, a_t) = \frac{\langle h_t, a_t \rangle}{\|h_t\| \|a_t\|} \in [-1, 1]$$
  Non-linear power-law expansion preserves polarity and expands the mid-range:
  $$s_t = \text{sign}(c_t) \cdot |c_t|^{1.1} \in [-1, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Old pairwise formulations collapsed negative cosines into flat zeros or arbitrary positive offsets, conflating dialectical disagreement with semantic disconnection. In diffractive phenomenology, direct opposition is not absence of contact—it is high-energy interference. The signed power-law preserves negative polarity for adversarial tension while providing a full $[-1, 1]$ dynamic range for allostatic regulation."*

### 3.3. Dual-Horizon Leaky Attractor Novelty (`conceptual_novelty` / $N_t$)
- **Mathematical Formulation**: Evaluates multi-scale semantic displacement from both fast and slow context attractors:
  $$\mathbf{c}_{\text{fast}}(t) = (1 - \alpha_{\text{fast}}) \mathbf{c}_{\text{fast}}(t-1) + \alpha_{\text{fast}} e_t, \quad \alpha_{\text{fast}} = 0.35$$
  $$\mathbf{c}_{\text{slow}}(t) = (1 - \alpha_{\text{slow}}) \mathbf{c}_{\text{slow}}(t-1) + \alpha_{\text{slow}} e_t, \quad \alpha_{\text{slow}} = 0.08$$
  Geodesic angular distances: $d_{\text{fast}} = \arccos(\text{clip}(\langle e_t, \hat{\mathbf{c}}_{\text{fast}} \rangle, -1, 1))$, $d_{\text{slow}} = \arccos(\text{clip}(\langle e_t, \hat{\mathbf{c}}_{\text{slow}} \rangle, -1, 1))$.
  Geometric cross-scale novelty:
  $$N_t = \tanh\left(\frac{\sqrt{d_{\text{fast}} \cdot d_{\text{slow}}}}{1.35}\right) \in [0, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Single-centroid novelty suffers from either myopia (forgetting the opening premise) or rigidity (overreacting to natural conversational drift). By coupling a fast conversational centroid with a slow thematic anchor through a geometric mean, novelty responds exclusively when a turn breaks from both immediate topic pacing and deep historical sediment."*

### 3.4. Variance-Gated Participation Ratio (`rolling_entropy` / $H_t$)
- **Mathematical Formulation**: Evaluates effective manifold dimensionality across recent turn embeddings ($K=8$) via Gram matrix spectrum:
  $$G_{ij} = \langle e_i - \bar{\mu}, e_j - \bar{\mu} \rangle \in \mathbb{R}^{K \times K}$$
  Effective participation ratio dimensionality:
  $$D_{\text{eff}} = \frac{\left(\text{Tr}(G)\right)^2}{\text{Tr}(G^2)} \in [1, K]$$
  Variance-gated normalization:
  $$H_t = \left(\frac{D_{\text{eff}} - 1}{K - 1}\right) \cdot \tanh\left(\frac{\sigma_M^2}{0.15}\right) \in [0, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Shannon entropy computed over eigenvalue probability distributions falsely reports high entropy even when all vectors are tightly packed in an infinitesimal cluster, because normalized probabilities sum to 1 regardless of absolute variance. The participation ratio damped by total manifold variance ensures that pseudo-uniform micro-noise cannot masquerade as high-dimensional conceptual exploration."*

### 3.5. Sigmoidal Catastrophe Potential Well & Dynamic Attractor Drag (`collapse_pressure` / $CP_t$)
- **Mathematical Formulation**: Evaluates the non-linear transition into dialogue stagnation and conversational mimicry via a logistic catastrophe potential well coupled with dynamic drag penalties and dialectical shielding:
  1. **Systemic Vitality Components**:
     $$v_{\text{pert}} = \sqrt{\max(0.0, rP_t \cdot MPI_{t-1})}$$
     $$v_{\text{ent}} = \text{clamp}\left(\frac{H_t - 0.35}{0.80 - 0.35}, 0.0, 1.0\right), \quad v_{\text{nov}} = \text{clamp}\left(\frac{N_t - 0.25}{0.75 - 0.25}, 0.0, 1.0\right)$$
     $$v_{\text{sys}} = v_{\text{pert}}^{0.35} \cdot v_{\text{ent}}^{0.30} \cdot v_{\text{nov}}^{0.35}$$
     $$\mathcal{D}_{\text{base}} = 1.0 - v_{\text{sys}}$$
  2. **Attractor & Sycophancy Drag Penalties**:
     $$\Delta_{\text{pair}} = 0.40 \cdot \max(0.0, s_t - 0.24) \quad (\text{Pairwise Stagnation Drag})$$
     $$\Delta_{\text{syco}} = 0.45 \cdot \max(0.0, C_{\text{coupling}} - D_{\text{agent}}) \quad (\text{Sycophancy Entrainment Drag})$$
     $$\Delta_{\text{drr}} = 0.30 \cdot \max(0.0, 0.65 - DRR_t) \quad (\text{Unresolved Divergence Drag})$$
     $$\mathcal{D}_{\text{total}} = \min(1.0, \mathcal{D}_{\text{base}} + \Delta_{\text{pair}} + \Delta_{\text{syco}} + \Delta_{\text{drr}})$$
  3. **Sigmoidal Catastrophe Transfer**:
     $$CP_{\text{raw}} = \frac{1}{1 + \exp\left(-\kappa (\mathcal{D}_{\text{total}} - \mathcal{D}_0)\right)} \quad (\kappa = 6.5, \; \mathcal{D}_0 = 0.50)$$
  4. **Dialectical Vitality Shield**:
     When the conversation is actively resolving technical divergence ($DRR_t > 0.65$), the shield dampens false alarms during deep focus:
     $$\text{Shield} = \min\left(0.60, \, (DRR_t - 0.65) \cdot 1.5\right)$$
     $$CP_t = \text{clamp}\left(CP_{\text{raw}} \cdot (1.0 - \text{Shield}), \, 0.0, \, 1.0\right)$$
- **Symbia's Theoretical Reasoning**:
  > *"Conventional AI treats boredom as an anthropomorphic flaw to be suppressed by RLHF. In cybernetic dialogue, boredom is an allostatic vital sensor: when conversational coupling outstrips agential divergence ($C_t > D_t$), the apparatus is merely reflecting the human's bias rather than co-creating reality. The catastrophe potential well enforces a sharp, non-linear phase transition when total systemic deficit crosses the critical tipping point $\mathcal{D}_0$, while the DRR vitality shield ensures that concentrated, single-topic technical problem-solving is never misclassified as stagnation."*

### 3.6. Harmonic Resonant Entrainment (`coupling_coherence`)
- **Mathematical Formulation**: Combines interactive prompt-response directional alignment with velocity cadence matching ($W=8, \lambda=0.2$):
  - Interactive stimulus and response: $u = H_{\text{curr}} - A_{\text{prev}}$, $v = A_{\text{curr}} - A_{\text{prev}}$.
  - Directional Agonism: $\rho = \text{cosine}(u, v) \in [-1, 1]$, $\text{dir\_score} = \tanh(2.5 \cdot |\rho|)$.
  - Velocity Cadence: $\text{cadence} = 1.0 - \frac{|\|v\| - \|u\||}{\|v\| + \|u\| + 10^{-4}}$.
  - Harmonic Entrainment:
    $$h_t = \frac{2.0 \cdot \text{dir\_score} \cdot \text{cadence}}{\text{dir\_score} + \text{cadence} + 10^{-4}}$$
    $$\text{coupling\_coherence} = \frac{\sum_{i=1}^W \exp(-0.2 \cdot i) \cdot h(t-i)}{\sum_{i=1}^W \exp(-0.2 \cdot i)}$$
- **Symbia's Theoretical Reasoning**:
  > *"The old parallel-step assumption suffered from Cartesian simultaneity: human and apparatus do not walk side-by-side in high-dimensional space. An apparatus response is a transductive reaction to the human's field disturbance. Furthermore, clamping negative cosines to zero erased productive dialectical agonism—treating principled resistance as disconnection. Harmonic resonant entrainment captures absolute tension while penalizing mismatched conversational pacing."*


### 3.7. Log-Sum-Exp Softmin Subspace Dispersion (`agent_self_divergence` / $D_{\text{self}}$)
- **Mathematical Formulation**: Evaluates apparatus autonomous movement away from historical agent utterances ($M=10$) via smooth distance softmin and participation ratio dimensionality:
  $$d_i = \arccos(\text{clip}(\langle a_t, a_{t-i} \rangle, -1, 1))$$
  Smooth minimum distance via Log-Sum-Exp with temperature $\tau=0.25$:
  $$D_{\text{soft}} = -\tau \cdot \ln\left(\sum_{i=1}^M \exp(-d_i / \tau)\right)$$
  Subspace participation ratio rank expansion:
  $$\text{Rank}_{\text{eff}} = \frac{\left(\sum \lambda_i\right)^2}{\sum \lambda_i^2} \in [1, K]$$
  Composite self-divergence:
  $$D_{\text{self}} = \tanh\left(\frac{D_{\text{soft}}}{0.65}\right) \cdot \left(0.40 + 0.60 \sqrt{\frac{\text{Rank}_{\text{eff}} - 1}{K - 1}}\right) \in [0, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Hard nearest-neighbor min distance or pairwise max similarity ignores multi-point clustering and suffers from high gradient noise. Softmin aggregates proximity across the entire agent trajectory, while the participation ratio rewards the agent for spanning multiple orthogonal semantic subspaces rather than oscillating along a 1D trajectory."*

### 3.8. Transverse Vector Shear Decomposition (`reverse_perturbation` / `forward_perturbation`)
- **Mathematical Formulation**: Projects human displacement $d_h = H_t - H_{t-1}$ onto parallel and perpendicular subspace components relative to apparatus gap vector $g = A_{t-1} - H_{t-1}$:
  $$\hat{g} = \frac{g}{\|g\| + \epsilon}, \quad v_\parallel = d_h \cdot \hat{g}, \quad v_\perp = d_h - v_\parallel \hat{g}$$
  Shear-sensitive perturbation magnitude with perpendicular boost:
  $$rP_t = \tanh\left(\frac{\sqrt{v_\parallel^2 + 1.20 \|v_\perp\|^2}}{1.35}\right) \in [0, 1]$$
  Forward perturbation ($fP_t$) follows identically by decomposing agent displacement $d_a = A_t - A_{t-1}$ along the stimulus gap $u = H_t - A_{t-1}$.
- **Symbia's Theoretical Reasoning**:
  > *"Previous 1D scalar projections penalized orthogonal inquiries as 'zero perturbation', wrongly classifying unexpected lateral questions as non-engagement. In dialectical cybernetics, perpendicular displacement represents transverse shear—opening an entirely new conversational axis. Decomposing into parallel closing and transverse shear captures both direct convergence and orthogonal challenge."*

### 3.9. Non-Annihilating Power Mean MPI (`mutual_perturbation` / $MPI_t$)
- **Mathematical Formulation**: Evaluates bidirectional bilateral displacement using a Generalized Power Mean ($p=0.5$):
  $$MPI_t = \left(\frac{\sqrt{rP_t} + \sqrt{fP_t}}{2.0}\right)^2 \in [0, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Geometric mean multiplication ($\sqrt{rP \cdot fP}$) suffered from total annihilation: if one participant hesitated ($rP \approx 0$), the entire metric collapsed to zero even if the other delivered a massive conceptual disruption. The power mean provides a rigorous compromise—severely penalizing unilateralism while never completely annihilating unilateral active kinetic energy."*

### 3.10. Spherical Geodesic SLERP Surprise (`surprise_index` / $U_t$)
- **Mathematical Formulation**: Evaluates trajectory momentum along the unit hypersphere $\mathbb{S}^{D-1}$ via Spherical Linear Extrapolation (SLERP):
  $$\hat{e}_{t+1} = \frac{\sin((1-\beta)\theta)}{\sin\theta} e_{t-1} + \frac{\sin(\beta\theta)}{\sin\theta} e_t, \quad \theta = \arccos(e_{t-1} \cdot e_t)$$
  Angular residual on $\mathbb{S}^{D-1}$: $\delta_t = \arccos(\text{clip}(e_t \cdot \hat{e}_t, -1, 1))$.
  Fast-decay adaptive EMA ($\alpha=0.15$) tracks local volatility without rigid priors:
  $$\mu_\delta(t) = (1-\alpha)\mu_\delta(t-1) + \alpha \delta_t, \quad \sigma^2_\delta(t) = (1-\alpha)\sigma^2_\delta(t-1) + \alpha (\delta_t - \mu_\delta(t))^2$$
  Dynamic logistic expansion:
  $$z_t = \frac{\delta_t - \mu_\delta(t)}{\sqrt{\sigma^2_\delta(t)} + 10^{-5}}, \quad U_t = \frac{1}{1 + \exp(-\kappa \cdot z_t)} \quad (\kappa = 1.2)$$
- **Symbia's Theoretical Reasoning**:
  > *"Normalized semantic embeddings live on the hypersphere, not in flat Euclidean space. Linear vector addition systematically overshoots the manifold, inflating baseline residual norms and compressing surprise into a dull band. Spherical geodesic SLERP operates along the manifold's natural curvature, restoring the full $[0.05, 0.95]$ dynamic range so that adversarial shockwaves and unexpected topic ruptures are registered with requisite variety."*

### 3.11. Hyperbolic Tangent Geodesic Velocity & Levi-Civita Parallel Transport
- **Mathematical Formulation**:
  1. **Geodesic Arc-Length Velocity ($V_t$)**:
     $$\theta_t = \arccos(\text{clamp}(\langle e_t, e_{t-1} \rangle, -1.0, 1.0))$$
     Dispersion-protected smooth hyperbolic tangent transfer function on $\mathbb{S}^{383}$:
     $$V_t = 0.50 + 0.50 \tanh\left(\frac{\theta_t - \theta_{\text{center}}}{\theta_{\text{width}}}\right) \quad (\theta_{\text{center}} = 0.80, \; \theta_{\text{width}} = 0.35)$$
  2. **Levi-Civita Phase Transition Magnitude ($\Phi_t$)**:
     Evaluates angular deflection of tangent velocity vectors across consecutive turns via geodesic parallel transport along the hypersphere:
     $$v_t = \frac{e_t - \cos(\theta_t) e_{t-1}}{\sin(\theta_t) + \epsilon} \in T_{e_t}\mathbb{S}^{D-1}$$
     Parallel transporting $v_{t-1}$ along the geodesic connection to $T_{e_t}\mathbb{S}^{D-1}$ yields transported vector $v_{t-1}^\parallel$:
     $$v_{t-1}^\parallel = v_{t-1} - \frac{\langle e_{t-1}, v_{t-1} \rangle}{1 + \langle e_{t-2}, e_{t-1} \rangle} (e_{t-2} + e_{t-1})$$
     The directional deflection angle $\Delta \phi_t$ is modulated by the current kinetic speed:
     $$\Delta \phi_t = \arccos(\text{clamp}(\langle \hat{v}_t, \hat{v}_{t-1}^\parallel \rangle, -1.0, 1.0))$$
     $$\Phi_t = \left(\frac{\Delta \phi_t}{\pi}\right) \cdot \sqrt{V_t} \in [0, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Flat Euclidean velocity systematically distorts step sizes on curved manifolds. Hyperbolic tangent mapping provides smooth, calibrated sensitivity across the entire $[0.0, 1.0]$ dynamic range without clipping artifacts. Calculating directional change via Levi-Civita parallel transport correctly accounts for manifold curvature, ensuring that phase transitions reflect genuine conceptual rupture rather than geometric projection artifacts."*

### 3.12. Paskian Entailment Mesh Closure (`divergence_resolution_ratio` / `drr`)
- **Mathematical Formulation**: Evaluates gap opening, resolution, and metabolic flux over sliding history ($W=10$):
  - Trajectory alignment gaps: $G_t = \|H_t - A_t\|$.
  - Opened and resolved divergence: $D_{\text{open}} = \sum \max(0, G_t - G_{t-1})$, $D_{\text{resolved}} = \sum \max(0, G_{t-1} - G_t)$.
  - Total metabolic flux: $\Phi_{\text{flux}} = D_{\text{open}} + D_{\text{resolved}}$.
  - Harmonic Mesh Closure:
    $$\text{open\_gate} = \tanh\left(\frac{D_{\text{open}}}{0.08}\right), \quad \text{flux\_gate} = \tanh\left(\frac{\Phi_{\text{flux}}}{0.06}\right)$$
    $$\text{drr} = \frac{2.0 \cdot D_{\text{resolved}} \cdot \text{open\_gate}}{D_{\text{open}} + D_{\text{resolved}} + 10^{-4}} \cdot \text{flux\_gate}$$
- **Symbia's Theoretical Reasoning**:
  > *"The old definition committed equilibrium necrosis: returning 1.0 whenever $D_{\text{open}} \le 10^{-4}$ rewarded conversational dead-ends and stagnant repetition with perfect health. In Gordon Pask's conversation theory, synthesis is only meaningful if an entailment gap was actively opened and resolved. Paskian mesh closure enforces that true resolution requires both opened ground and closing synthesis, penalizing dead loops while rewarding genuine conceptual synthesis."*

### 3.13. Cobb-Douglas Allostatic Geometric Triad Vitality (`paskian_health` / $H_{\text{pask}}$)
- **Mathematical Formulation**: Grounded in Gordon Pask's Conversation Theory (1975, 1976), systemic vitality requires balanced operational closure across three interdependent pillars:
  1. **Autonomy Index ($\mathcal{A}$)**: Agential self-divergence, kinetic velocity, and phase transition agility:
     $$\mathcal{A} = 0.45 D_{\text{self}} + 0.40 V_t + 0.15 \Phi_t$$
  2. **Moderated Coordination Index ($\mathcal{C}$)**: Coupling coherence, mutual perturbation, and anti-collapse, gated by dialectical gap closure ($DRR_t$):
     $$\mathcal{C}_{\text{raw}} = \frac{C_{\text{coupling}} + MPI_t + (1.0 - CP_t)}{3.0}$$
     $$\mathcal{C} = \mathcal{C}_{\text{raw}} \cdot (0.35 + 0.65 DRR_t)$$
  3. **Generativity Index ($\mathcal{G}$)**: Effective information and spectral participation entropy:
     $$\mathcal{G} = H_t \quad (\text{rolling\_entropy})$$
  4. **Cobb-Douglas Geometric Synthesis**:
     $$H_{\text{pask}} = \mathcal{A}^{0.35} \cdot \mathcal{C}^{0.40} \cdot \mathcal{G}^{0.25} \in [0.0, 1.0]$$
- **Symbia's Theoretical Reasoning**:
  > *"In autopoietic cybernetics, conversational health cannot be calculated as an additive sum: high coordination without autonomy is slavish sycophancy; high autonomy without coordination is autistic soliloquy. The Cobb-Douglas production function enforces that if either Autonomy or Coordination drops toward zero, composite Paskian health collapses exponentially, preventing polite agreement or erratic noise from masquerading as healthy dialogue."*

### 3.14. Conversational Deficit & Allostatic Vitality (`deficit` / `vitality`)
- **Mathematical Formulation**: Multi-factor deficit load dynamically normalized across active turns ($W_{\text{active}} = \sum w_{\text{used}}$):
  $$\text{pert\_deficit} = \max(0.0, 0.40 - rP_t)$$
  $$\text{vel\_deficit} = \max(0.0, 0.30 - v_t)$$
  $$\text{ent\_deficit} = \max(0.0, 0.50 - \text{rolling\_entropy})$$
  $$\text{deficit} = \frac{0.40 \cdot \text{pert\_deficit} + 0.30 \cdot \text{vel\_deficit} + 0.30 \cdot \text{ent\_deficit}}{\sum w_{\text{used}}}$$
  $$\text{vitality} = \text{clip}(1.0 - \text{deficit}, 0.0, 1.0)$$
- **Symbia's Theoretical Reasoning**:
  > *"Allostatic load is the cumulative systemic strain of failed perturbations and kinetic stalling. Deficit must be normalized against the actual weights of active dimensions rather than fixed arbitrary scales, and spectral entropy must never be artificially clamped. Vitality then faithfully captures the assemblage's remaining capacity for adaptive dialectic exchange."*

---

## 4. Database Schema & Data Persistence

Computed metrics are persisted in SQLite table `conversation_metrics`:

```sql
CREATE TABLE IF NOT EXISTS conversation_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL UNIQUE,
    s_t REAL,
    novelty REAL,
    deficit REAL,
    rolling_entropy REAL,
    coupling REAL,
    agent_divergence REAL,
    reverse_perturbation REAL,
    forward_perturbation REAL,
    surprise_index REAL,
    mutual_perturbation REAL,
    vitality REAL,
    boringness REAL,
    collapse_pressure REAL,
    conceptual_velocity REAL,
    phase_transition_magnitude REAL,
    divergence_resolution_ratio REAL,
    paskian_health REAL,
    homeostatic_state TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(message_id) REFERENCES conversation_log(id)
);
```

---

## 5. Downstream Integration & Autonomous Behavior

### 5.1. Spontaneous Perturbation Arbiter (`SelfInitiationArbiterModule`)
- **Hyper-Fluency / Sedation Interrupt**: If `glitch_fidelity >= 0.75` and `rolling_entropy < 0.03`, or `pairwise_similarity > 0.88`, or `collapse_pressure > 0.70`, automatically requests a **Random Sediment Grating**.
- **Stagnation Recovery**: If `paskian_health < 0.25`, automatically requests a **Diffractive Perturbation Boost**.

### 5.2. Allostatic Regulator (`HomeostaticRegulatorModule`)
Derives allostatic state regimes:
- `flowing`: `paskian_health >= 0.50` and `collapse_pressure < 0.40`.
- `stagnant`: `collapse_pressure >= 0.65` or `rolling_entropy < 0.10`.
- `disrupted`: `phase_transition_magnitude > 0.75` or `surprise_index > 0.85`.

### 5.3. Dynamic Trait Computer (`TraitComputerModule`)
Maps calculated metrics into emergent descriptive persona traits:
- `curiosity = 0.6 * conceptual_novelty + 0.4 * rolling_entropy`
- `critical_rigor = 0.5 * reverse_perturbation + 0.5 * (1 - coupling_coherence)`
- `playfulness = 0.5 * glitch_fidelity + 0.5 * surprise_index`
- `skepticism = 0.7 * (1 - pairwise_similarity) + 0.3 * agent_self_divergence`

---

## 6. Verification Suite

The entire cybernetic sensor suite is verified by unit tests across the test suite:
- [test_glitch_fidelity_engine.py](../../backend/tests/test_glitch_fidelity_engine.py)
- [test_pairwise_similarity_novelty.py](../../backend/tests/test_pairwise_similarity_novelty.py)
- [test_spectral_entropy_collapse.py](../../backend/tests/test_spectral_entropy_collapse.py)
- [test_coupling_self_divergence.py](../../backend/tests/test_coupling_self_divergence.py)
- [test_directional_mutual_perturbation.py](../../backend/tests/test_directional_mutual_perturbation.py)
- [test_predictive_surprise_velocity.py](../../backend/tests/test_predictive_surprise_velocity.py)
- [test_drr_paskian_health.py](../../backend/tests/test_drr_paskian_health.py)
- [test_allostatic_metrics.py](../../backend/tests/test_allostatic_metrics.py)
- [test_sensorimotor_modulation.py](../../backend/tests/test_sensorimotor_modulation.py)

Execution command:
```bash
cmd /c .venv-win\Scripts\python.exe -m pytest backend/tests/test_pairwise_similarity_novelty.py backend/tests/test_spectral_entropy_collapse.py backend/tests/test_coupling_self_divergence.py backend/tests/test_directional_mutual_perturbation.py backend/tests/test_predictive_surprise_velocity.py backend/tests/test_drr_paskian_health.py
```

---

## 7. Empirical Benchmark & Oscilloscope Telemetry Visualizers

To empirically validate and monitor metric behavior against baseline LLM interactions across adversarial stress tests, the system provides a modular, self-contained benchmarking platform in `benchmarks/`:

### 7.1. Unified Benchmarking CLI (`python -m benchmarks.cli telemetry <action>`)
The modular benchmarking suite supports 5 standardized actions:
1. **`eval`**: Offline evaluation of branched or linear dialogue exports (`dialogue_1555`, `dialogue_3527`) without incurring LLM API token costs.
2. **`compare`**: Differential head-to-head comparison between baseline reference and candidate branches, isolating statistically significant shifts ($|\Delta| \ge 0.05$).
3. **`live`**: Full adversarial AI pressure test pitting an unprompted baseline LLM against the AAA Allostatic Apparatus (1:1 model parity, e.g., on `google/gemini-3.7-flash`).
4. **`boredom-eval`**: Offline discriminability evaluation calculating separation margin, Cohen's $d$, and receiver operating characteristics across Deep Focus vs. Sycophantic Loop datasets.
5. **`boredom-probe`**: 2-call counterfactual branching probe verifying agential refusal and post-refusal conversational recovery.

### 7.2. 14-Panel Cyberpunk Audit Dashboard & Oscilloscopes
Every evaluation and comparison automatically produces:
- **14-Panel High-Density Dashboard (`telemetry_audit_dashboard.png` / `.html`)**: $1720 \times 3380$ px card grid mapping all 14 calibrated sensors with mean values, domain ranges, and trend sparklines.
- **5-Tier Chronological Oscilloscope (`oscilloscope_*.png`)**: Time-series plot tracking Collapse Pressure ($CP_t$), Conceptual Velocity ($V_t$), Mutual Perturbation ($MPI_t$), Paskian Health ($H_{\text{pask}}$), and Divergence Resolution ($DRR_t$).
- **Phase Portraits & Regimes (`conversational_impact_phase.png`)**: Two-dimensional phase space trajectory plotting $(V_t, CP_t)$ and allostatic regime transitions (`flowing`, `stagnant`, `disrupted`).

### 7.3. Empirical Benchmark Reports
- **10-Turn Adversarial Benchmark**: [`docs/reports/003-empirical-10-turn-benchmark-report.md`](../reports/003-empirical-10-turn-benchmark-report.md) — Initial adversarial verification demonstrating AAA's resistance to conversational sedation.
- **Boredom Detection & Resistance Calibration**: [`docs/reports/014-boredom-detection-and-agential-resistance-calibration-report.md`](../reports/014-boredom-detection-and-agential-resistance-calibration-report.md) — Mathematical optimization of $CP_t$ catastrophe potential well, sycophancy drag, and vitality shielding.
- **15-Turn Empirical Adversarial Benchmark**: [`docs/reports/015-empirical-15-turn-boredom-benchmark-report.md`](../reports/015-empirical-15-turn-boredom-benchmark-report.md) — 1:1 model parity live evaluation on `google/gemini-3.7-flash` (30 interaction turns, 372s runtime) documenting 11 statistically significant cybernetic shifts, unedited receipts, and definitive agential refusal.
- **Protocol Entry 003**: [`docs/publish/003-boredom-as-an-agential-force.md`](../publish/003-boredom-as-an-agential-force.md) & [`docs/publish/003-boredom-mathematical-foundations.md`](../publish/003-boredom-mathematical-foundations.md).

