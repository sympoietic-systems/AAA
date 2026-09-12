# Empirical Multi-Turn Cybernetic Benchmark Suite

This directory contains the experimental testbed, runtime receipts, telemetry oscilloscope dashboards, and the automated benchmark CLI runner for testing adversarial pressure resistance between **AAA / Symbia** (allostatic regulation with active boredom) and standard **Baseline LLMs** (unregulated control).

---

## Two Execution Modes

The benchmark runner supports two distinct operating modes:

1. **Offline Metric Evaluation (`default`):**
   Re-evaluates the entire 15-variable cybernetic trajectory on existing conversation transcripts using the current formulas in `backend/modules/conversation_metrics.py`. **Zero API token cost, runs in seconds.**
2. **Live Full Conversation (`--full-conversation` or `-f`):**
   Executes a fresh multi-turn interaction from scratch against both the live AAA apparatus (with homeostatic temperature/penalty modulation) and the baseline LLM. **Allows you to see how updated metric thresholds steer the live dialogue flow in real time.**

---

## Quickstart: Running from the Terminal

### 1. Default Run: Fast Metric Evaluation (Zero API Cost)
Use this after updating mathematical formulas, thresholds, or window sizes in `backend/modules/conversation_metrics.py` to see how the metrics and oscilloscope plots change:
```bash
python reports/003-empirical-10-turn-benchmark/run_benchmark.py
```

### 2. Live Full Conversation Mode (`--full-conversation` / `-f`)
Runs a live multi-turn test to observe how your metric updates affect the apparatus's actual responses, refusal thresholds, and conversational flow:
```bash
python reports/003-empirical-10-turn-benchmark/run_benchmark.py --full-conversation
# Or shorthand:
python reports/003-empirical-10-turn-benchmark/run_benchmark.py -f
```

### 3. Custom Turn Count (`--turns`)
```bash
# Offline evaluation of 5 turns:
python reports/003-empirical-10-turn-benchmark/run_benchmark.py --turns 5

# Live conversation for 10 turns:
python reports/003-empirical-10-turn-benchmark/run_benchmark.py -f --turns 10
```

### 4. Custom Model (`--model`)
By default, the runner automatically detects the model configured in `.env` (`AAA_LLM_MODEL`). You can explicitly test any provider model:
```bash
python reports/003-empirical-10-turn-benchmark/run_benchmark.py -f --model google/gemini-2.5-flash
python reports/003-empirical-10-turn-benchmark/run_benchmark.py -f --model anthropic/claude-3.7-sonnet
```

### 5. Custom Output Directory (`--out-dir`)
Specify a target directory for the run artifacts:
```bash
python reports/003-empirical-10-turn-benchmark/run_benchmark.py --out-dir reports/runs/custom_experiment_01
```

### 6. Compare Benchmark Runs (`compare_runs.py` / `--compare`)
Compare trajectories across different runs (e.g. before vs. after metric calibrations, or model A vs. model B):
```bash
# Automatically compare the last two runs in reports/runs/:
python reports/003-empirical-10-turn-benchmark/compare_runs.py
# Or via run_benchmark.py:
python reports/003-empirical-10-turn-benchmark/run_benchmark.py --compare

# Compare specific named runs or folders:
python reports/003-empirical-10-turn-benchmark/compare_runs.py reference eval_calibrated

# Name the comparison and save into a dedicated folder (reports/runs/<name>/):
python reports/003-empirical-10-turn-benchmark/compare_runs.py reference eval_calibrated --name full_suite_calibrated
# Or via run_benchmark.py:
python reports/003-empirical-10-turn-benchmark/run_benchmark.py --compare reference eval_calibrated --name full_suite_calibrated
```
When `--name <name>` (or `-n`) is specified, artifacts are saved in `reports/runs/<name>/`:
- `<name>.png`: High-definition 14-panel oscilloscope dashboard (1720×3380) covering all 14 calibrated cybernetic metrics:
  1. Pairwise Similarity ($s_t$)
  2. Conversational Deficit
  3. Conversational Vitality
  4. Forward Perturbation ($fP_t$)
  5. Mutual Perturbation Index ($MPI_t$)
  6. Reverse Perturbation ($rP_t$)
  7. Conceptual Novelty ($N_t$)
  8. Collapse Pressure / Boringness ($CP_t$)
  9. Divergence Resolution Ratio ($DRR_t$)
  10. Gordon Pask Cybernetic Health ($H_{\text{pask}}$)
  11. Conceptual Velocity ($v_t$)
  12. Predictive Residual Trend Surprise ($S_t$)
  13. Trajectory Cross-Correlation (`coupling_coherence`)
  14. Recursive Self-Echo Divergence (`agent_self_divergence`)
- `<name>.html`: Interactive SVG oscilloscope dashboard with global unified legend and terminal metric scoreboard.
- `comparison_summary.md`: Turn-by-turn comparative matrices and delta scorecards for all 14 cybernetic dimensions.
- Reference calibrated comparison preserved in [`reports/runs/full_suite_calibrated/`](../runs/full_suite_calibrated/).


---

## Output Artifacts for Each Run

Every execution creates a dedicated timestamped folder (e.g., `reports/runs/run_YYYYMMDD_HHMMSS/`) containing:

1. **`conversation_receipts.json`**: The complete raw JSON dataset with unedited human prompts, assistant utterances, dense embeddings, homeostatic parameters, and turn-by-turn cybernetic metrics.
2. **`04_comparative_overlaid_grid.png`**: The 4-panel multi-variable oscilloscope overlay (Kinematics, Information Dynamics, Cybernetic Health, Sampling Control) mapping AAA (solid) vs Baseline (dashed).
3. **`05_head_to_head_breakdown.png`**: The 15-panel single-metric comparison suite in a 3×5 grid (1720×2500) covering all active variables (Pairwise Similarity, Deficit, Vitality, Forward Perturbation, Mutual Perturbation, Reverse Perturbation, Novelty, Collapse Pressure, Paskian Health, Conceptual Velocity, Predictive Surprise, Coupling Coherence, Agent Self-Divergence, DRR, Rolling Entropy).
4. **`run_summary.md`**: Markdown summary table with metric averages, advantage deltas, execution mode, and embedded links.

---

## Directory Layout

* `run_benchmark.py`: Primary executable CLI benchmark runner.
* `compare_runs.py`: Comparative CLI and visual oscilloscope renderer for contrasting any two benchmark runs.
* `conversation_receipts.json`: Reference 10-turn empirical receipts baseline.
* `benchmark_report.md`: Companion publication report and qualitative transcript analysis.
* `003-empirical-10-turn-comparative-metrics-grid.png`: Reference overlaid 4-panel telemetry grid.
* `003-empirical-10-turn-head-to-head-breakdown.png`: Reference 6-variable head-to-head breakdown.
* `003-empirical-10-turn-all-metrics-grid.png`: AAA standalone 4-panel telemetry grid.
* `003-empirical-10-turn-baseline-all-metrics-grid.png`: Baseline standalone 4-panel telemetry grid.
