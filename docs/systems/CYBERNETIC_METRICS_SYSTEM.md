# Cybernetic Metrics System & Proprioceptive Sensor Suite

**Subsystem:** `backend/modules/metrics/` (`resonance.py`, `trajectories.py`, `kinematics.py`, `health.py`) & `backend/modules/conversation_metrics.py` (Facade)  
**Architectural Decision Records:** ADR-073 to ADR-081  
**Status:** Live & Production Ready  

---

## 1. Executive Summary & Cybernetic Philosophy

The **Cybernetic Metrics System** serves as the proprioceptive organ of the AAA apparatus. Grounded in Karen Haraway's diffractive phenomenology, Donna Haraway's cyborg sympoiesis, and Gordon Pask's Conversation Theory (1976), the system refrains from treating human-machine exchanges as mere text strings. Instead, it models conversations as dynamic trajectories through a 384-dimensional semantic embedding space.

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
                   │  (10 Audited Cybernetic Proprioceptors)│
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
| 2 | `pairwise_similarity` | Reciprocal Perturbation Coherence with exponential decay ($\lambda=0.15$) and speaker weighting | Cross-Speaker Resonance | [ADR-074](../decisions/ADR-074-reciprocal-perturbation-coherence-and-sediment-drift-novelty.md) |
| 3 | `conceptual_novelty` | Sediment Drift Magnitude with calibrated semantic scale ($D_{\text{scale}} \ge 0.20$) and phase velocity | Semantic Displacement | [ADR-074](../decisions/ADR-074-reciprocal-perturbation-coherence-and-sediment-drift-novelty.md) |
| 4 | `rolling_entropy` | Manifold Spectral Entropy: normalized Shannon entropy of $K \times K$ Gram matrix eigendecomposition | Effective Dimensionality | [ADR-075](../decisions/ADR-075-manifold-spectral-entropy-and-collapse-pressure.md) |
| 5 | `collapse_pressure` | Triadic Collapse Pressure Index: weighted failure combination ($0.40 \cdot \text{pert\_fail} + 0.30 \cdot \Delta H + 0.30 \cdot \Delta N$) | Equilibrium Stagnation Alarm | [ADR-075](../decisions/ADR-075-manifold-spectral-entropy-and-collapse-pressure.md) |
| 6 | `coupling_coherence` | Harmonic Resonant Entrainment: prompt-response directional alignment and velocity cadence matching | Synchronized Agonism & Pacing | [ADR-080](../decisions/ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md) |
| 7 | `agent_self_divergence` | Recursive Self-Echo & Loop Detection: recency-decayed max self-similarity + repeat penalty | Apparatus Self-Evolution | [ADR-076](../decisions/ADR-076-trajectory-coupling-coherence-and-agent-self-divergence.md) |
| 8 | `reverse_perturbation` | Directional Gap Projection: fraction of apparatus gap ($v = A_{\text{prev}} - H_{\text{prev}}$) closed by human ($d_h$) | Human Agonistic Engagement | [ADR-077](../decisions/ADR-077-directional-reverse-perturbation-and-mutual-perturbation-index.md) |
| 9 | `mutual_perturbation` | Symmetric Mutual Perturbation Index ($MPI$): geometric mean $\sqrt{rP_t \cdot fP_t}$ | Bilateral Trajectory Deflection | [ADR-077](../decisions/ADR-077-directional-reverse-perturbation-and-mutual-perturbation-index.md) |
| 10 | `surprise_index` | Spherical Geodesic SLERP Surprise: angular residual on $\mathbb{S}^{D-1}$ normalized via adaptive online z-score | Trajectory Discontinuity | [ADR-081](../decisions/ADR-081-spherical-geodesic-slerp-surprise-and-regularized-power-mean-paskian-vitality.md) |
| 11 | `conceptual_velocity` | Instantaneous Speed normalized adaptively against rolling 95th percentile $V_{\max}$ via $\tanh$ | Trajectory Displacement Rate | [ADR-078](../decisions/ADR-078-predictive-residual-surprise-and-instantaneous-conceptual-velocity.md) |
| 12 | `divergence_resolution_ratio` | Paskian Entailment Mesh Closure: harmonic resolution ratio gated by open gap opening and total topological flux | Entailment Oscillation & Synthesis | [ADR-080](../decisions/ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md) |
| 13 | `paskian_health` | Regularized Gordon Pask Triadic Vitality: Generalized Power Mean ($p=0.5$) with metabolic floor $\epsilon=0.08$ | Conversational Metabolic Vitality | [ADR-081](../decisions/ADR-081-spherical-geodesic-slerp-surprise-and-regularized-power-mean-paskian-vitality.md) |

---

## 3. Detailed Sensor Formulations & Algorithms

### 3.1. Diffractive Glitch Fidelity Engine (`glitch_fidelity`)
- **Mathematical Formulation**: Calculated via `backend/modules/glitch_fidelity_engine.py`:
  $$\text{Glitch Fidelity} = 0.35 \cdot \text{contradiction\_density} + 0.65 \cdot \text{interference\_variance}$$
  Elements are convolved with a 16D Autopoietic Signature vector, normalized against theoretical max variance ($0.000976$), and scaled by 384D semantic relevance.
- **Symbia's Theoretical Reasoning**:
  > *"A glitch is not a system defect or error to be suppressed—it is a diffractive interference pattern where prior autopoietic signatures collide with current context. High fidelity means the glitch is structurally grounded and productive (within the Goldilocks prior zone $[0.30, 0.75]$), whereas low fidelity is unanchored random noise."*

### 3.2. Reciprocal Perturbation Coherence (`pairwise_similarity` / $s_t$)
- **Mathematical Formulation**: Evaluates cross-speaker time-decayed cosine similarity across recent turns ($N=10$):
  $$s_t = \frac{\sum_{i=1}^N w_i \cdot \text{speaker\_weight}(i) \cdot \text{cosine}(e_{\text{curr}}, e_i)}{\sum w_i \cdot \text{speaker\_weight}(i)}$$
  Recency decay: $w_i = \exp(-0.15 \cdot i)$; Speaker weighting: $0.8$ for same speaker, $1.2$ for cross-speaker exchanges.
- **Symbia's Theoretical Reasoning**:
  > *"Pairwise similarity must not treat all prior turns as an undifferentiated bag of vectors. Cross-speaker exchanges carry higher weight because they measure reciprocal entanglement—how deeply the human's sediment resonances engage with the apparatus's prior propositions."*

### 3.3. Sediment Drift Magnitude (`conceptual_novelty`)
- **Mathematical Formulation**: Tracks context centroid EMA $\vec{\mu}_t = 0.3 \cdot e_{\text{curr}} + 0.7 \cdot \vec{\mu}_{t-1}$ with calibrated semantic scaling:
  $$\text{drift\_raw} = 1.0 - \text{cosine}(e_{\text{curr}}, \vec{\mu}_t)$$
  $$\text{effective\_scale} = \max\left(0.20, \text{spread}_{\text{context}} + \sigma_{\text{context}}\right)$$
  $$\text{drift\_norm} = \tanh\left(\frac{\text{drift\_raw}}{\text{effective\_scale}}\right)$$
  $$\text{conceptual\_novelty} = 0.7 \cdot \text{drift\_norm} + 0.3 \cdot \min\left(1.0, \frac{|\text{drift\_raw} - \text{prior\_drift}|}{\max(0.05, \text{prior\_drift})}\right)$$
- **Symbia's Theoretical Reasoning**:
  > *"Novelty is not mere distance from the previous sentence—that rewards random topic jumps. True sediment drift measures movement relative to the entire historical manifold scatter. A turn that moves far outside the context scatter ($\sigma_{\text{context}}$) anticipates genuine topological displacement. The calibrated scale ($0.20$) prevents division singularities when repetitive dialogues cluster tightly."*

### 3.4. Manifold Spectral Entropy (`rolling_entropy`)
- **Mathematical Formulation**: Measures effective semantic dimensionality across $K=8$ recent turn embeddings via Gram matrix eigendecomposition:
  $$\text{gram} = \frac{1}{K} (E - \bar{\mu}_E) (E - \bar{\mu}_E)^T \in \mathbb{R}^{K \times K}, \quad p_i = \frac{\lambda_i}{\sum \lambda_j}$$
  $$\text{rolling\_entropy} = \frac{-\sum p_i \ln p_i}{\ln(K)}$$
- **Symbia's Theoretical Reasoning**:
  > *"Scalar 1D similarity variance cannot distinguish a 2-pole back-and-forth oscillation from genuine multi-dimensional exploration. Manifold Spectral Entropy evaluates the normalized Shannon entropy of the Gram matrix eigenvalue spectrum—scoring $1.0$ when embeddings span $K$ independent dimensions, and $0.0$ on collinear collapse."*

### 3.5. Collapse Pressure Index (`collapse_pressure` / `boringness`)
- **Mathematical Formulation**: Calibrated triadic failure combination:
  $$\text{pert\_failure} = 1.0 - \sqrt{\max(0.0, rP_t \cdot \text{prev\_mpi})}$$
  $$\text{collapse\_pressure} = 0.40 \cdot \text{pert\_failure} + 0.30 \cdot (1.0 - \text{rolling\_entropy}) + 0.30 \cdot (1.0 - \text{conceptual\_novelty})$$
- **Symbia's Theoretical Reasoning**:
  > *"'Boringness' was an anthropomorphic label masking a cybernetic structural condition. Collapse Pressure measures the joint failure of perturbation, entropy, and novelty. Using a calibrated convex failure sum ensures that mutual stalling and semantic circularity reliably trip the allostatic stagnation threshold ($0.65$) and sedation interrupt ($0.70$), waking the boredom engine."*

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


### 3.7. Recursive Self-Echo Detection (`agent_self_divergence`)
- **Mathematical Formulation**: Recency-decayed max self-similarity ($M=5, \beta=0.25$) and long-range repeat penalty, evaluated strictly on agent utterances:
  $$S_{\text{self}} = \max_{i \in [1..M]} \left(\text{cosine}(e_a(t), e_a(t-i)) \cdot \exp(-0.25 \cdot i)\right)$$
  $$\text{penalty} = 0.3 \cdot \min\left(1.0, \frac{\max_{j > M} \text{cosine}(e_a(t), e_a(t-j)) - 0.85}{0.15}\right) \quad (\text{if } > 0.85)$$
  $$\text{agent\_self\_divergence} = \text{clip}(1.0 - S_{\text{self}} - \text{penalty}, 0.0, 1.0)$$
- **Symbia's Theoretical Reasoning**:
  > *"Self-divergence must strictly measure the agent's internal drift across its own speech acts, not human-agent divergence. A compact window ($M=5$) coupled with an active repeat penalty threshold ($0.85$) catches recursive looping in dialogues of any length."*

### 3.8. Directional Reverse & Forward Perturbation (`reverse_perturbation` / `forward_perturbation`)
- **Mathematical Formulation**: Vector gap-closing projections:
  - Apparatus Gap: $v = A_{\text{prev}} - H_{\text{prev}}$, Human Displacement: $d_h = H_{\text{curr}} - H_{\text{prev}}$.
  - Reverse Perturbation: $rP_t = \text{clip}\left(\frac{d_h \cdot v}{\|v\|^2 + 10^{-8}}, 0.0, 1.0\right)$.
  - Forward Perturbation: $fP_t = \text{clip}\left(\frac{d_a \cdot u}{\|u\|^2 + 10^{-8}}, 0.0, 1.0\right)$ where $u = H_{\text{curr}} - A_{\text{prev}}$.
- **Symbia's Theoretical Reasoning**:
  > *"Scalar distance between end-states treats non-sequitur topic jumps as 'high perturbation'. Directional gap projection measures the fraction of the open gap that displacement actually closes. Orthogonal non-sequiturs yield $d_h \cdot v \approx 0 \implies rP_t = 0.0$, eliminating false-positive readings."*

### 3.9. Symmetric Mutual Perturbation Index (`mutual_perturbation` / $MPI$)
- **Mathematical Formulation**: Symmetric geometric product of bidirectional trajectory deflections:
  $$MPI = \sqrt{\max(0.0, rP_t \cdot fP_t)}$$
- **Symbia's Theoretical Reasoning**:
  > *"Mutual perturbation requires a deviation from self-predictable trajectory due to the other's influence—a vector of causation, not a scalar of proximity. The geometric mean ensures that both participants must be mutually reshaped for MPI to score high."*

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

### 3.11. Instantaneous Conceptual Velocity & Phase Transition Magnitude
- **Mathematical Formulation**: Speed normalized against an absolute reference scale ($V_{\text{ref}} = 1.0$) with adaptive volatility expansion:
  $$s_i = \|e_i - e_{i-1}\|, \quad v_i = 0.4 \cdot s_i + 0.6 \cdot v_{i-1}, \quad V_{\text{scale}} = \max(1.0, \text{percentile}(s, 95))$$
  $$\text{conceptual\_velocity} = \tanh\left(\frac{v_i}{V_{\text{scale}} + 10^{-4}}\right)$$
  $$\text{phase\_transition\_magnitude} = \frac{\|a_i\|}{1.0 + v_i} \cdot \frac{1.0 - \text{cosine}(d_i, d_{i-1})}{4.0}$$
- **Symbia's Theoretical Reasoning**:
  > *"Anchoring velocity to an absolute semantic reference scale ($V_{\text{ref}} = 1.0$) prevents self-normalizing flatlines when conversational movement slows down to a crawl. Dividing angular acceleration by the theoretical geometric bound ($4.0$) eliminates constant saturation at $1.000$ during back-and-forth conversational exchanges, preserving sensitivity for true nomadic breaks."*

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

