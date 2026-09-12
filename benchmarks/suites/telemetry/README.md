# Cybernetic Telemetry Benchmark Suite

## Objective
Evaluate and stress-test the 14-dimension cybernetic telemetry apparatus over dialogue embedding trajectories.

## 14-Dimension Telemetry Architecture
The telemetry suite computes and audits metrics across five cybernetic functional pillars:

1. **Kinematics & Momentum:**
   - `s_t` (*Reciprocal Perturbation Coherence / Pairwise Similarity*): Trajectory alignment with temporal decay ($\lambda=0.15$).
   - `N_t` (*Conceptual Novelty*): Semantic distance from expanding conversational centroid.
   - `v_t` (*Conceptual Velocity*): Phase space velocity normalized by 95th percentile $V_{max}$.
   - `Phase Transitions` ($\Delta \Phi_t$): Acceleration and directional turning rate in dense embedding space.

2. **Perturbation Dynamics:**
   - `rP_t` (*Reverse Perturbation*): Impact of human input altering agent trajectory.
   - `fP_t` (*Forward Perturbation*): Impact of agent response driving dialectic momentum.
   - `MPI` (*Mutual Perturbation Index*): Geometric mean $\sqrt{rP_t \cdot fP_t}$ measuring bi-directional coupling.
   - `Surprise` ($U_t$): Predictive residual error normalized by local trend volatility (Holt-Winters double exponential smoothing).

3. **Coordination & Topology:**
   - `C_t` (*Coupling Coherence*): Cosine alignment between consecutive alternating human-agent turns.
   - `D_t` (*Agent Self-Divergence*): Degree to which agent avoids echoing its own immediate history.
   - `H_ent` (*Rolling Spectral Entropy*): Manifold complexity and information richness over sliding windows.

4. **Allostasis & Homeostasis:**
   - `Deficit` ($\Delta_H$): Weighted homeostatic distance across similarity, novelty, entropy, and self-divergence.
   - `Vitality`: Composite vitality index reflecting dynamic conversational health.
   - `B_t` (*Collapse Pressure*): Detection of repetitive semantic collapse and conversational stagnation.

5. **Paskian Interaction Health:**
   - `DRR` (*Divergence Resolution Ratio*): Balance between divergence and convergence ($\text{optimal} \approx 0.15$).
   - `Paskian Health`: Gordon Pask triadic cybernetic vitality index (geometric mean of autonomy, coordination, and generativity).

## Pipelines & Commands

### 1. Offline Dataset Evaluation (`eval`)
Analyzes recorded dialogue trajectories (including branched conversations):
```bash
cmd /c uv run python scripts/benchmark.py eval -i benchmarks/data/dialogues/dialogue_1555_branched_all_messages.json --node 1555 -n branch_1555
```

### 2. Differential Run Comparison (`compare`)
Head-to-head comparison between baseline and candidate runs, highlighting metrics with significant shift ($|\Delta| \ge 0.05$):
```bash
cmd /c uv run python scripts/benchmark.py compare -a benchmarks/runs/telemetry/eval_branch_1555_<TS> -b benchmarks/data/dialogues/dialogue_1555_longest_path_1228_computed_metrics.json -n branch1555_vs_1228
```

### 3. Live Adversarial AI Pressure Test (`live`)
Runs a multi-turn repetitive prompt sequence against OpenRouter Baseline LLM vs. AAA Apparatus (FastAPI `TestClient`):
```bash
cmd /c uv run python scripts/benchmark.py live -m google/gemini-2.5-flash -t 10 -n live_adversarial_test
```
