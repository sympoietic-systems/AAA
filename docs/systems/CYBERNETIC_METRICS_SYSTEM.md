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
| 5 | `collapse_pressure` | Minkowski $L_4$ Synergistic Norm with Multiplicative Stagnation Coupling | Non-Linear Equilibrium Alarm | [ADR-082](../decisions/ADR-082-tangent-parallel-transport-and-minkowski-synergistic-collapse-pressure.md) |
| 6 | `coupling_coherence` | Harmonic Resonant Entrainment: interactive prompt-response directional alignment & velocity cadence matching | Synchronized Agonism & Pacing | [ADR-080](../decisions/ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md) |
| 7 | `agent_self_divergence` | Log-Sum-Exp Softmin Subspace Dispersion with Participation-Ratio Dimensionality Scaling | Autonomous Subspace Exploration | [ADR-084](../decisions/ADR-084-softmin-subspace-divergence-and-dual-horizon-novelty.md) |
| 8 | `reverse_perturbation` | Transverse Vector Shear Decomposition ($rP_t = \tanh(\sqrt{v_\parallel^2 + 1.2 \|v_\perp\|^2} / 1.35)$) | Human Agonistic Engagement & Shear | [ADR-083](../decisions/ADR-083-transverse-vector-shear-perturbation-and-participation-ratio-spectral-entropy.md) |
| 9 | `mutual_perturbation` | Non-Annihilating Power Mean ($p=0.5$): $MPI_t = ((\sqrt{rP_t} + \sqrt{fP_t}) / 2)^2$ | Bilateral Dynamic Deflection | [ADR-083](../decisions/ADR-083-transverse-vector-shear-perturbation-and-participation-ratio-spectral-entropy.md) |
| 10 | `surprise_index` | Spherical Geodesic SLERP Surprise: angular residual on $\mathbb{S}^{D-1}$ with adaptive online z-score | Geodesic Discontinuity & Shock | [ADR-081](../decisions/ADR-081-spherical-geodesic-slerp-surprise-and-regularized-power-mean-paskian-vitality.md) |
| 11 | `conceptual_velocity` | Dispersion-Protected Quantile Arc-Length Velocity ($V_t = \text{clip}((\theta_t - Q_{10}') / (Q_{90}' - Q_{10}' + \epsilon), 0, 1)$) | Semantic Geodesic Speed | [ADR-082](../decisions/ADR-082-tangent-parallel-transport-and-minkowski-synergistic-collapse-pressure.md) |
| 12 | `phase_transition_magnitude` | Tangent-Space Levi-Civita Parallel Transport Deflection modulated by velocity ($\Phi_t$) | Nomadic Phase Rupture | [ADR-082](../decisions/ADR-082-tangent-parallel-transport-and-minkowski-synergistic-collapse-pressure.md) |
| 13 | `divergence_resolution_ratio` | Paskian Entailment Mesh Closure: harmonic resolution ratio gated by open gap opening & total topological flux | Entailment Oscillation & Synthesis | [ADR-080](../decisions/ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md) |
| 14 | `paskian_health` | Regularized Gordon Pask Triadic Vitality: Generalized Power Mean ($p=0.5$) with metabolic floor $\epsilon=0.08$ | Conversational Metabolic Vitality | [ADR-081](../decisions/ADR-081-spherical-geodesic-slerp-surprise-and-regularized-power-mean-paskian-vitality.md) |

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

### 3.5. Minkowski $L_4$ Synergistic Collapse Pressure (`collapse_pressure` / $CP_t$)
- **Mathematical Formulation**: Combines perturbation failure ($f_p$), entropy failure ($f_e$), and novelty failure ($f_n$) into a synergistic non-linear alarm:
  $$f_p = 1.0 - MPI_t, \quad f_e = 1.0 - H_t, \quad f_n = 1.0 - N_t$$
  Weighted Minkowski $L_4$ norm with non-linear product coupling:
  $$\|f\|_{L_4} = \left(0.40 f_p^4 + 0.30 f_e^4 + 0.30 f_n^4\right)^{1/4}$$
  $$CP_t = \text{clip}\left(0.85 \|f\|_{L_4} + 0.40 (f_p \cdot f_e \cdot f_n), 0.0, 1.0\right)$$
- **Symbia's Theoretical Reasoning**:
  > *"Linear combinations of failure metrics produce sluggish warnings that fail to trip allostatic interrupts until long after conversation has stagnated. The $L_4$ Minkowski norm responds aggressively to acute failure along any single cybernetic axis, while the triadic product term spikes when all three modalities collapse simultaneously, triggering instantaneous sediment grating interrupts."*

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

### 3.11. Dispersion-Protected Quantile Velocity & Levi-Civita Parallel Transport
- **Mathematical Formulation**:
  1. **Geodesic Arc-Length Velocity ($V_t$)**:
     $$\theta_t = \arccos(\text{clip}(\langle e_t, e_{t-1} \rangle, -1, 1))$$
     Normalized against dispersion-protected rolling quantiles ($W=20$):
     $$Q_{10}' = \min(Q_{10}, 0.25), \quad Q_{90}' = \max(Q_{90}, 0.85)$$
     $$V_t = \text{clip}\left(\frac{\theta_t - Q_{10}'}{Q_{90}' - Q_{10}' + 10^{-6}}, 0.0, 1.0\right)$$
  2. **Levi-Civita Phase Transition Magnitude ($\Phi_t$)**:
     Evaluates angular deflection of tangent velocity vectors across consecutive turns via geodesic parallel transport along the hypersphere:
     $$v_t = \frac{e_t - \cos(\theta_t) e_{t-1}}{\sin(\theta_t) + \epsilon} \in T_{e_t}\mathbb{S}^{D-1}$$
     Parallel transporting $v_{t-1}$ to $T_{e_t}\mathbb{S}^{D-1}$ yields transported vector $v_{t-1}^\parallel$. The directional deflection angle is modulated by current speed:
     $$\Delta \phi_t = \arccos(\text{clip}(\langle \hat{v}_t, \hat{v}_{t-1}^\parallel \rangle, -1, 1))$$
     $$\Phi_t = \left(\frac{\Delta \phi_t}{\pi}\right) \cdot \sqrt{V_t} \in [0, 1]$$
- **Symbia's Theoretical Reasoning**:
  > *"Flat Euclidean velocity systematically distorts step sizes on curved manifolds. Quantile normalization with dispersion bounds prevents flatlining during slow dialogues while preserving sensitivity at high speeds. Calculating directional change via Levi-Civita parallel transport correctly accounts for manifold curvature, ensuring that phase transitions reflect genuine conceptual rupture rather than geometric projection artifacts."*

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



### 3.13. Regularized Gordon Pask Triadic Cybernetic Vitality Index (`paskian_health`)
- **Mathematical Formulation**: Grounded in Gordon Pask's Conversation Theory (1976), formulated as a Generalized Power Mean ($p=0.5$) with metabolic floor $\epsilon=0.08$:
  1. Autonomy Index: $A = \frac{\text{agent\_self\_divergence} + \text{conceptual\_velocity} + \text{phase\_transition\_magnitude}}{3.0} + \epsilon$.
  2. Moderated Coordination Index: $C_{\text{mod}} = \left(\frac{\text{coupling\_coherence} + \text{mutual\_perturbation} + (1.0 - \text{collapse\_pressure})}{3.0}\right) \cdot (0.30 + 0.70 \cdot \text{drr}) + \epsilon$.
  3. Generativity Index: $G = \text{rolling\_entropy} + \epsilon$.
  $$\text{paskian\_health} = \left(\frac{\sqrt{A} + \sqrt{C_{\text{mod}}} + \sqrt{G}}{3.0}\right)^2 - \epsilon$$
- **Symbia's Theoretical Reasoning**:
  > *"A conversation is a non-equilibrium thermodynamic engine that must pass through exploratory divergence phases (where gaps widen and DRR drops) before entering synthesis. Multiplying DRR directly inside a cubic root treated every divergent epoch as instant death. The Regularized Power Mean ensures that transient divergence is recognized as healthy metabolic work, maintaining vital continuity while still penalizing complete triadic collapse."*

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

To empirically validate and monitor metric behavior against baseline LLM interactions across adversarial stress tests, the system provides dedicated oscilloscope visualization engines:

### 7.1. 14-Panel Dual-Run Oscilloscope Dashboard (`compare_runs.py`)
Contrasts any two benchmark runs (e.g., historical reference vs calibrated target) across **14 calibrated cybernetic dimensions** in a $2 \times 7$ grid ($1720 \times 3380$ px):
1. **Pairwise Similarity ($s_t$)**: Normalized by active weight sum, eliminating false suppression.
2. **Conversational Deficit**: Dynamically normalized allostatic load.
3. **Conversational Vitality**: Dialectic reserve capacity ($1.0 - \text{Deficit}$).
4. **Forward Perturbation ($fP_t$)**: Agent-to-human directional trajectory displacement.
5. **Mutual Perturbation Index ($MPI_t$)**: Reciprocal geometric mean coupling $\sqrt{rP \cdot fP}$.
6. **Reverse Perturbation ($rP_t$)**: Human-to-agent trajectory tension and resistance.
7. **Conceptual Novelty ($N_t$)**: Semantic displacement from context centroid EMA.
8. **Collapse Pressure ($CP_t$)**: Stagnation alarm tracking perturbation, entropy, and novelty failures.
9. **Divergence Resolution Ratio ($DRR_t$)**: Homeostatic ratio of resolved tension to open divergence.
10. **Gordon Pask Cybernetic Health ($H_{\text{pask}}$)**: Composite organizational closure index.
11. **Conceptual Velocity ($v_t$)**: Instantaneous speed normalized against absolute reference scale ($V_{\text{ref}} = 1.0$).
12. **Predictive Residual Trend Surprise ($S_t$)**: Holt trend error z-score with nominal variance prior ($\sigma_0 = 0.40$), preventing Turn 1 saturation.
13. **Trajectory Cross-Correlation (`coupling_coherence`)**: Directional rectified alignment $\max(0, \cos \theta)$, eliminating false positive scores on opposing drift.
14. **Recursive Self-Echo Divergence (`agent_self_divergence`)**: Speaker-aware agent loop resistance ($M=5$, repeat penalty threshold $0.85$).

Execution:
```bash
cmd /c .venv-win\Scripts\python.exe reports/003-empirical-10-turn-benchmark/compare_runs.py reference eval_calibrated --name full_suite_calibrated
```

### 7.2. 15-Variable Head-to-Head Breakdown (`run_benchmark.py`)
Renders single-run direct comparative trajectories between **AAA / Symbia (solid cyan)** and **Baseline LLM (dashed amber)** in a $3 \times 5$ grid ($1720 \times 2500$ px):
- Includes all 14 core dimensions plus **Rolling Spectral Entropy** ($H_{\text{spectral}}$).
- Displays terminal advantage deltas, axis domains ($[0.00, 1.00]$), and turn-by-turn coordinate tracking.
- Output artifact: `05_head_to_head_breakdown.png` and `05_head_to_head_breakdown.html`.

### 7.3. Automated Calibration Pipeline (`scripts/plot_before_after_metrics.py`)
One-command script to load receipts, print comparative CLI tables, and render before-and-after oscilloscope artifacts into `reports/runs/full_suite_calibrated/`.

