# Cybernetic Telemetry Benchmark Suite

## Objective
Evaluate and stress-test the 14-dimension cybernetic telemetry apparatus over dialogue embedding trajectories.

## 14-Dimension Telemetry Architecture
The telemetry suite computes and audits metrics across five cybernetic functional pillars:

1. **Kinematics & Momentum:**
   - `s_t` (*Signed Polarity Alignment / Pairwise Similarity*): Trajectory alignment with temporal decay ($\lambda=0.15$) and signed polarity preservation (ADR-084).
   - `N_t` (*Dual-Horizon Conceptual Novelty*): Leaky multi-scale distance balancing local rupture against macro-basin detachment (ADR-084).
   - `v_t` (*Dispersion-Protected Conceptual Velocity*): Geodesic arc-length displacement on $\mathbb{S}^{D-1}$ anchored to ambient quantiles (ADR-082).
   - `Phase Transitions` ($\Phi_t$): Levi-Civita tangent parallel transport curvature along geodesic arcs (ADR-082).

2. **Perturbation Dynamics:**
   - `rP_t` (*Reverse Perturbation*): Transverse vector shear deflection relative to prior interpersonal gap (ADR-083).
   - `fP_t` (*Forward Perturbation*): Transverse vector shear deflection driven by apparatus response (ADR-083).
   - `MPI` (*Mutual Perturbation Index*): Regularized power mean ($p=0.5$) non-annihilating agonistic coupling (ADR-083).
   - `Surprise` ($U_t$): Spherical geodesic SLERP extrapolation residual on $\mathbb{S}^{D-1}$ normalized via adaptive online z-score (ADR-081).

3. **Coordination & Topology:**
   - `C_t` (*Coupling Coherence*): Harmonic resonant entrainment (directional agonism $\times$ velocity cadence matching) (ADR-080).
   - `D_t` (*Agent Self-Divergence*): Log-Sum-Exp softmin subspace dispersion scaled by generative matrix effective rank (ADR-084).
   - `H_ent` (*Variance-Gated Rolling Spectral Entropy*): Manifold participation ratio scaled by total trajectory variance (ADR-083).

4. **Allostasis & Homeostasis:**
   - `Deficit` ($\Delta_H$): Weighted homeostatic distance across similarity, novelty, entropy, and self-divergence.
   - `Vitality`: Composite vitality index reflecting dynamic conversational health.
   - `CP_t` (*Collapse Pressure*): Minkowski $L_4$ synergistic failure norm tripping homeostatic alarms ($0.65$) on deadlock (ADR-082).

5. **Paskian Interaction Health:**
   - `DRR` (*Divergence Resolution Ratio*): Paskian entailment mesh closure measuring opened gap resolution and metabolic flux (ADR-080).
   - `Paskian Health`: Regularized Gordon Pask triadic vitality index (Generalized Power Mean $p=0.5$ with metabolic floor) (ADR-081).

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
