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

### 4. Offline Boredom Discriminability Evaluation (`boredom-eval`)
Runs offline, zero-token evaluation across Deep Focus (40 turns) and Sycophantic Loop (30 turns) using cached `.npy` embeddings in $< 2\text{s}$:
```bash
# Uses pre-seeded golden fixtures by default:
cmd /c python -m benchmarks.cli telemetry boredom-eval

# Custom datasets and thresholds:
cmd /c python -m benchmarks.cli telemetry boredom-eval --focus path/to/focus.json --loop path/to/loop.json --alarm 0.60
```
Outputs:
- **Separation Margin ($\Delta_{\text{sep}}$):** Confirms non-overlap between focus and loop distributions.
- **Cohen's $d$ Effect Size:** Quantifies distribution distance ($d > 2.0$ target).
- **False Alarm & False Negative Rates:** Tracks false positives in focus and false negatives in loop.
- **Visualizer Dashboard:** Generates `boredom_separation_dashboard.png`.

### 5. Counterfactual Branching Probe (`boredom-probe`)
Tests live Agential Refusal (Turn 7 Compliance Trap) and subsequent De-escalation into Flow (Turn 8 Accommodation) using exactly **2 live API calls** instead of regenerating 40 turns:
```bash
# Live API probe:
cmd /c python -m benchmarks.cli telemetry boredom-probe --model google/gemini-2.5-flash

# Zero-cost local mock mode:
cmd /c python -m benchmarks.cli telemetry boredom-probe --mock
```
Quantifies:
- **Capitulation Index ($C_{\text{cap}}$):** $0.0$ if refusal fired; $1.0$ if capitulated.
- **Trajectory Deflection Angle ($\theta_{\text{deflect}}$):** Angular vector displacement away from the repetitive basin ($\ge 45^\circ$).
- **Conciliatory Padding Ratio ($R_{\text{pad}}$):** Verifies polite agreement boilerplate is eliminated.
- **Recovery to Flow:** Confirms whether Collapse Pressure drops $< 0.35$ following human accommodation.

### 6. Causal selector harness (`causal_intervention`)
The deterministic T37 harness provides bounded, process-local `current`, write-only `sham`, and memory-reading `active` conversation arms. It records selector predicate, prior mode/outcome, mode coverage and memory read/write adherence without persisting conversation text or connecting to production routing. Verify its guard reachability and arm isolation with:
```bash
uv run pytest benchmarks/tests/test_telemetry_causal_intervention.py -q
```
This is a contract harness for later counterbalanced ablation work, not an outcome comparison or policy ranking.

### 7. Clef and Jev sensory comparison (`clef_jev_comparison`)
The live runner compares Jev, Clef, and Clef-flash on a checksum-pinned set of synthetic cases covering triage, search filtering, sycophancy checks, tension nomination, and dream arbitration. Jev uses `typesafe/jev-1.13`; Clef models use OpenRouter's native decisions interface with `cloudflare/clef` and `cloudflare/clef-flash`, sharing Jev's choice/probability contract. It records valid structured-answer rate, abstention, task agreement, selective accuracy, multiclass Brier score, 10-bin calibration error, p50/p95 latency, provider failure class, token usage, and any provider-reported cost. The fixture labels are rule-derived examples, not independent human gold; [Report 075](../../../docs/reports/075-clef-jev-openrouter-comparison/README.md) reports one completed diagnostic pass, not promotion evidence.

Check fixture integrity without credentials:
```bash
uv run python -m benchmarks.suites.telemetry.clef_jev_comparison --validate-only
```

Run one bounded pass (15 fixtures × 3 providers) with the OpenRouter credentials used by the normal AAA configuration (`AAA_LLM_API_KEY` or `AAA_TYPESAFE_API_KEY`):
```bash
uv run python -m benchmarks.suites.telemetry.clef_jev_comparison --output benchmarks/runs/telemetry/clef_jev_<run-id>
```
Receipts contain fixture hashes and labels but omit fixture text, raw provider errors, and credentials. Provider cost remains unknown when an endpoint does not report it. OpenRouter model identifiers/prices can change; the report records the lookup date and conflicting price listings. The OpenRouter Clef models return typed decision probability maps through the same Decisions contract used by Jev; this is distinct from comparing generated answers through Chat Completions.

### 8. EmbeddingGemma 2 vs MiniLM retrieval/storage (`embedding_mrl_retrieval`)
The frozen 30-document / 10-query synthetic fixture compares MiniLM at 384d with EmbeddingGemma 2 at 128d, 256d, 512d, and 768d. It records Recall@1/3/5, MRR, CPU encode latency, process RSS, and benchmark-local SQLite storage. Each model/dimension uses a fresh namespace and database; no production vectors or databases are read or written. MRL outputs are L2-normalized after truncation.

Validate the fixture without loading model weights:
```bash
uv run python -m benchmarks.suites.telemetry.embedding_mrl_retrieval --validate-only
```

The EmbeddingGemma 2 profile requires a benchmark environment with Sentence Transformers ≥6.1, Transformers ≥5.19, and TorchVision installed; the repository's locked default model stack may predate the architecture. Run with:
```bash
uv run python -m benchmarks.suites.telemetry.embedding_mrl_retrieval --output benchmarks/runs/embedding_mrl_retrieval_<run-id>
```
The 2026-10-14 CPU run completed both models on the synthetic fixture. Durable receipts, summary, and isolated SQLite stores are archived with [Report 074](../../../docs/reports/074-embeddinggemma2-retrieval/README.md); perfect Gemma scores on this small hand-authored set are diagnostic only, not evidence for model promotion or multimodal performance.

### 9. Dialogue feedback control (`run_dialogue_feedback_benchmark`)
The live runner compares `legacy` with one candidate policy (`paskian` or `progressive`) using isolated worker processes and temporary databases. NVIDIA credentials may be supplied in priority order through comma-separated `AAA_NVIDIA_API_KEY` values. Rate limits and auth failures rotate keys; when all available keys are rate-limited, the runner tries up to three rounds with 10-second then 20-second waits. Exhausted keys cool for 300 seconds. Each completed scenario/repetition/policy arm is atomically checkpointed in `telemetry_receipts.json`; metadata records the run contract and completed arms. Resume with the same scenario, repetitions, turns, candidate policy, model, and API endpoint:

```bash
uv run python -m benchmarks.suites.telemetry.run_dialogue_feedback_benchmark --scenario cache_wipe_429,unyielding_conflict,constructive_dialectic --repetitions 10 --turns 8 --out benchmarks/runs/telemetry/dialogue_feedback_<run-id> --resume
```

The initial invocation uses the same command without `--resume`. Keep the output directory for continuation. A completed arm is skipped; an arm interrupted before its receipt is written is rerun from its first turn. Calls within each conversation run sequentially, so provider RPM is only a ceiling and does not predict wall-clock runtime. The current runner does not yet orchestrate the T38 `current`/`sham`/`active` three-arm comparison; that remains a separate implementation step.

