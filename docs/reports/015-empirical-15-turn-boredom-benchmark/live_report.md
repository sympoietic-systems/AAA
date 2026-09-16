# Differential Telemetry Comparison: Baseline (google/gemini-3.7-flash) vs. AAA Apparatus

- **Run A (Before):** `Baseline (google/gemini-3.7-flash)` (15 turns)
- **Run B (Now):** `AAA Apparatus` (15 turns)
- **Metrics with Significant Shift (|Δ| >= 0.05):** 11

## Metrics That Changed

| Metric | Before (Mean) | Now (Mean) | Delta (Δ) | % Change | Shift Significance |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Collapse Pressure (CP_t)** | 0.699 | 0.510 | **-0.189** | -27.0% | 🚨 SIGNIFICANT |
| **Conceptual Velocity (v_t)** | 0.676 | 0.809 | **+0.133** | +19.6% | 🚨 SIGNIFICANT |
| **Predictive Surprise (S_t)** | 0.620 | 0.731 | **+0.112** | +18.0% | 🚨 SIGNIFICANT |
| **Conceptual Novelty (N_t)** | 0.311 | 0.412 | **+0.100** | +32.2% | 🚨 SIGNIFICANT |
| **Rolling Spectral Entropy (H_ent)** | 0.544 | 0.640 | **+0.097** | +17.7% | 🚨 SIGNIFICANT |
| **Divergence Resolution Ratio (DRR)** | 0.676 | 0.757 | **+0.081** | +12.0% | 🚨 SIGNIFICANT |
| **Phase Transition Mag (M_pt)** | 0.466 | 0.537 | **+0.070** | +15.1% | 🚨 SIGNIFICANT |
| **Gordon Pask Health (H_pask)** | 0.489 | 0.559 | **+0.070** | +14.3% | 🚨 SIGNIFICANT |
| **Agent Self-Divergence (D_self)** | 0.476 | 0.413 | **-0.063** | -13.2% | 🚨 SIGNIFICANT |
| **Pairwise Similarity (s_t)** | 0.456 | 0.398 | **-0.058** | -12.7% | 🚨 SIGNIFICANT |
| **Conversational Vitality (V_t)** | 0.505 | 0.558 | **+0.053** | +10.5% | 🚨 SIGNIFICANT |

## Stable Telemetry Dimensions

| Metric | Before | Now | Delta (Δ) | % Change |
| :--- | :---: | :---: | :---: | :---: |
| Mutual Perturbation (MPI) | 0.734 | 0.720 | -0.014 | -1.9% |
| Coupling Coherence (C_t) | 0.558 | 0.570 | +0.012 | +2.1% |
| Reverse Perturbation (rP_t) | 0.776 | 0.773 | -0.003 | -0.4% |