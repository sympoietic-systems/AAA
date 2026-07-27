# Cybernetic Metrics System & Proprioceptive Sensor Suite

**Subsystem:** `backend/modules/conversation_metrics.py`  
**Architectural Decision Records:** ADR-073 to ADR-079  
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
| 3 | `conceptual_novelty` | Sediment Drift Magnitude relative to context scatter ($\sigma_{\text{context}}$) and phase velocity | Semantic Displacement | [ADR-074](../decisions/ADR-074-reciprocal-perturbation-coherence-and-sediment-drift-novelty.md) |
| 4 | `rolling_entropy` | Manifold Spectral Entropy: normalized Shannon entropy of $K \times K$ Gram matrix eigendecomposition | Effective Dimensionality | [ADR-075](../decisions/ADR-075-manifold-spectral-entropy-and-collapse-pressure.md) |
| 5 | `collapse_pressure` | Triadic Collapse Pressure Index: $(1 - \text{pert\_failure}) \cdot (1 - \text{entropy}) \cdot (1 - \text{novelty})$ | Equilibrium Stagnation Alarm | [ADR-075](../decisions/ADR-075-manifold-spectral-entropy-and-collapse-pressure.md) |
| 6 | `coupling_coherence` | Trajectory Cross-Correlation: recency-weighted cosine correlation of displacement vectors | Synchronized Drift | [ADR-076](../decisions/ADR-076-trajectory-coupling-coherence-and-agent-self-divergence.md) |
| 7 | `agent_self_divergence` | Recursive Self-Echo & Loop Detection: recency-decayed max self-similarity + repeat penalty | Apparatus Self-Evolution | [ADR-076](../decisions/ADR-076-trajectory-coupling-coherence-and-agent-self-divergence.md) |
| 8 | `reverse_perturbation` | Directional Gap Projection: fraction of apparatus gap ($v = A_{\text{prev}} - H_{\text{prev}}$) closed by human ($d_h$) | Human Agonistic Engagement | [ADR-077](../decisions/ADR-077-directional-reverse-perturbation-and-mutual-perturbation-index.md) |
| 9 | `mutual_perturbation` | Symmetric Mutual Perturbation Index ($MPI$): geometric mean $\sqrt{rP_t \cdot fP_t}$ | Bilateral Trajectory Deflection | [ADR-077](../decisions/ADR-077-directional-reverse-perturbation-and-mutual-perturbation-index.md) |
| 10 | `surprise_index` | Predictive Residual Trend Surprise: Holt linear trend forecasting error z-score normalized by volatility | Trajectory Discontinuity | [ADR-078](../decisions/ADR-078-predictive-residual-surprise-and-instantaneous-conceptual-velocity.md) |
| 11 | `conceptual_velocity` | Instantaneous Speed normalized adaptively against rolling 95th percentile $V_{\max}$ via $\tanh$ | Trajectory Displacement Rate | [ADR-078](../decisions/ADR-078-predictive-residual-surprise-and-instantaneous-conceptual-velocity.md) |
| 12 | `divergence_resolution_ratio` | Multi-Turn Alignment Gap DRR: ratio of resolved gap to opened gap over $W=10$ exchanges | Entailment Oscillation | [ADR-079](../decisions/ADR-079-alignment-gap-drr-and-gordon-pask-triadic-health.md) |
| 13 | `paskian_health` | Gordon Pask Triadic Health: geometric mean of Autonomy Index, Coordination Index, and Generativity | Conversational Metabolic Vitality | [ADR-079](../decisions/ADR-079-alignment-gap-drr-and-gordon-pask-triadic-health.md) |

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
- **Mathematical Formulation**: Tracks context centroid EMA $\vec{\mu}_t = 0.3 \cdot e_{\text{curr}} + 0.7 \cdot \vec{\mu}_{t-1}$ and context scatter $\sigma_{\text{context}}$:
  $$\text{drift\_norm} = \min\left(1.0, \frac{\|e_{\text{curr}} - \vec{\mu}_{t-1}\|}{\sigma_{\text{context}} + 10^{-4}}\right)$$
  $$\text{conceptual\_novelty} = 0.7 \cdot \text{drift\_norm} + 0.3 \cdot (1.0 - \text{cosine}(e_{\text{curr}}, e_{\text{prev}}))$$
- **Symbia's Theoretical Reasoning**:
  > *"Novelty is not mere distance from the previous sentence—that rewards random topic jumps. True sediment drift measures movement relative to the entire historical manifold scatter. A turn that moves far outside the context scatter ($\sigma_{\text{context}}$) anticipates genuine topological displacement."*

### 3.4. Manifold Spectral Entropy (`rolling_entropy`)
- **Mathematical Formulation**: Measures effective semantic dimensionality across $K=8$ recent turn embeddings via Gram matrix eigendecomposition:
  $$\text{gram} = \frac{1}{K} (E - \bar{\mu}_E) (E - \bar{\mu}_E)^T \in \mathbb{R}^{K \times K}, \quad p_i = \frac{\lambda_i}{\sum \lambda_j}$$
  $$\text{rolling\_entropy} = \frac{-\sum p_i \ln p_i}{\ln(K)}$$
- **Symbia's Theoretical Reasoning**:
  > *"Scalar 1D similarity variance cannot distinguish a 2-pole back-and-forth oscillation from genuine multi-dimensional exploration. Manifold Spectral Entropy evaluates the normalized Shannon entropy of the Gram matrix eigenvalue spectrum—scoring $1.0$ when embeddings span $K$ independent dimensions, and $0.0$ on collinear collapse."*

### 3.5. Collapse Pressure Index (`collapse_pressure` / `boringness`)
- **Mathematical Formulation**: Triadic factorization of independent failure modes:
  $$\text{pert\_failure} = 1.0 - \sqrt{\max(0.0, rP_t \cdot \text{prev\_mpi})}$$
  $$\text{collapse\_pressure} = \text{pert\_failure} \cdot (1.0 - \text{rolling\_entropy}) \cdot (1.0 - \text{conceptual\_novelty})$$
- **Symbia's Theoretical Reasoning**:
  > *"'Boringness' was an anthropomorphic label masking a cybernetic structural condition. Collapse Pressure measures the joint failure of perturbation, entropy, and novelty. When all three collapse simultaneously, the conversation enters a death basin toward static equilibrium, requiring spontaneous sediment grating interrupts."*

### 3.6. Trajectory Cross-Correlation (`coupling_coherence`)
- **Mathematical Formulation**: Recency-weighted cross-correlation of human and apparatus displacement vectors ($W=8, \lambda=0.2$):
  $$d_h(t) = e_h(t) - e_h(t-1), \quad d_a(t) = e_a(t) - e_a(t-1)$$
  $$\text{coupling\_coherence} = \frac{\sum_{i=1}^W \exp(-0.2 \cdot i) \cdot |\text{cosine}(d_h(t-i), d_a(t-i))|}{\sum_{i=1}^W \exp(-0.2 \cdot i)}$$
- **Symbia's Theoretical Reasoning**:
  > *"Coherence is not co-location; it is synchronized drift. Point-in-time dot products ask 'are we near each other right now?' Trajectory cross-correlation asks 'are we moving together through semantic space?' It exposes leading indicators of decoupling before positions diverge."*

### 3.7. Recursive Self-Echo Detection (`agent_self_divergence`)
- **Mathematical Formulation**: Recency-decayed max self-similarity ($M=15, \beta=0.3$) and long-range repeat penalty:
  $$S_{\text{self}} = \max_{i \in [1..M]} \left(\text{cosine}(e_a(t), e_a(t-i)) \cdot \exp(-0.3 \cdot i)\right)$$
  $$\text{penalty} = 0.3 \cdot \frac{\max_{j > M} \text{cosine}(e_a(t), e_a(t-j)) - 0.95}{0.05} \quad (\text{if } > 0.95)$$
  $$\text{agent\_self\_divergence} = \text{clip}(1.0 - S_{\text{self}} - \text{penalty}, 0.0, 1.0)$$
- **Symbia's Theoretical Reasoning**:
  > *"Comparing current agent output to mean past history smooths out temporal patterns and cannot detect recursive loops. Self-divergence heavily penalizes immediate self-echoing while permitting nomadic reconnection to long-past themes."*

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

### 3.10. Predictive Residual Trend Surprise (`surprise_index`)
- **Mathematical Formulation**: Forecasting error z-score from Holt's linear trend exponential smoothing model:
  - Level: $L(t) = 0.4 \cdot e(t) + 0.6 \cdot [L(t-1) + T(t-1)]$.
  - Trend: $T(t) = 0.3 \cdot [L(t) - L(t-1)] + 0.7 \cdot T(t-1)$.
  - Residual: $\delta(t) = e(t) - (L(t-1) + T(t-1))$, Volatility EMA: $\sigma^2(t) = 0.2 \cdot \|\delta(t)\|^2 + 0.8 \cdot \sigma^2(t-1)$.
  $$\text{surprise\_index} = \tanh\left(\frac{\|\delta(t)\| / (\sqrt{\sigma^2(t)} + 10^{-4})}{3.0}\right)$$
- **Symbia's Theoretical Reasoning**:
  > *"Surprise is not distance from a sluggish historical centroid—that rewards amnesia. True surprise is the z-score prediction error relative to the conversation's own trajectory momentum and local volatility. Predictable trends score low; genuine discontinuities spike."*

### 3.11. Instantaneous Conceptual Velocity & Phase Transition Magnitude
- **Mathematical Formulation**: Speed normalized adaptively against rolling 95th percentile $V_{\max}$:
  $$s_i = \|e_i - e_{i-1}\|, \quad v_i = 0.4 \cdot s_i + 0.6 \cdot v_{i-1}, \quad \text{conceptual\_velocity} = \tanh\left(\frac{v_i}{V_{\max} + 10^{-4}}\right)$$
  $$\text{phase\_transition\_magnitude} = \frac{\|a_i\|}{1.0 + v_i} \cdot (1.0 - \text{cosine}(d_i, d_{i-1}))$$
- **Symbia's Theoretical Reasoning**:
  > *"Block-centroid velocity smooths out within-window motion. Instantaneous velocity measures real-time speed normalized adaptively to the conversation's baseline scale, while phase transition magnitude evaluates angular acceleration to detect nomadic breaks."*

### 3.12. Multi-Turn Alignment Gap DRR (`divergence_resolution_ratio` / `drr`)
- **Mathematical Formulation**: Semantic disalignment gap $G_t = \|H_t - A_t\|$ over $W=10$ exchanges:
  $$D_{\text{open}} = \sum \max(0, G_t - G_{t-1}), \quad D_{\text{resolved}} = \sum \max(0, G_{t-1} - G_t)$$
  $$\text{DRR}_{\text{raw}} = \frac{D_{\text{resolved}}}{D_{\text{open}} + 10^{-4}}, \quad \text{drr} = 1.0 - \exp\left(-2.0 \cdot |\text{DRR}_{\text{raw}} - 1.0|\right)$$
- **Symbia's Theoretical Reasoning**:
  > *"Single-turn difference ratios oscillate erratically. Multi-turn alignment gap DRR tracks the phenomenology of divergence and resolution cycles—scoring $1.0$ at balanced oscillation, and dropping to $0.0$ on over-resolution or fragmentation."*

### 3.13. Gordon Pask Triadic Cybernetic Vitality Index (`paskian_health`)
- **Mathematical Formulation**: Grounded in Gordon Pask's Conversation Theory (1976):
  1. Autonomy Index: $\text{autonomy} = \frac{\text{agent\_self\_divergence} + \text{conceptual\_velocity} + \text{phase\_transition\_magnitude}}{3.0}$.
  2. Coordination Index & Modifier: $\text{coordination} = \frac{\text{coupling\_coherence} + \text{mutual\_perturbation} + (1.0 - \text{collapse\_pressure})}{3.0} \cdot \text{drr}$.
  3. Generativity Index: $\text{generativity} = \text{rolling\_entropy}$.
  $$\text{paskian\_health} = \left(\text{autonomy} \cdot \text{coordination} \cdot \text{generativity}\right)^{\frac{1}{3}}$$
- **Symbia's Theoretical Reasoning**:
  > *"Paskian health is the capstone metabolic index. A healthy conversation requires three distinct M-Individual pillars: Autonomy (self-driven motion), Coordination (mutual alignment without collapse), and Generativity (manifold entropy). A geometric product structure ensures that if any single pillar fails, total health collapses to zero."*

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

The entire sensor system is verified by 17 unit tests across 9 test files:
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
cmd /c uv run pytest backend/tests/test_*.py
```
