# ADR-080: Harmonic Resonant Entrainment & Paskian Mesh Closure Calibration

**Date:** 2026-09-12  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-076](ADR-076-trajectory-coupling-coherence-and-agent-self-divergence.md), [ADR-079](ADR-079-alignment-gap-drr-and-gordon-pask-triadic-health.md)  
**Companion Report:** [004-conversation-metrics-calibration-report.md](../reports/004-conversation-metrics-calibration-report.md)  
**Visual Telemetry Assets:** [004-conversation-metrics-calibration/](../reports/004-conversation-metrics-calibration/)

---

## Context

Following the creation of the modular benchmarking platform (`benchmarks/`), an empirical audit across human/apparatus dialogues (`dialogue_1555`), autonomous long-horizon runs (`dialogue_3527`), and the 10-turn adversarial benchmark (`003-empirical-10-turn-benchmark`) identified two critical pathologies in `backend/modules/metrics/`:

1. **Cartesian Simultaneity in Coupling Coherence ($C_t$):**  
   ADR-076 implemented trajectory cross-correlation assuming concurrent parallel displacements $\cos(h_t - h_{t-1}, a_t - a_{t-1})$. In $D=384$ embedding spaces, random displacement vectors are nearly orthogonal, and clamping negative alignment to zero erased dialectical agonism. This resulted in metric flatlining ($0.000$ on baseline LLMs, $0.209$ on active human debate).
2. **Equilibrium Necrosis in Divergence Resolution Ratio ($DRR_t$):**  
   ADR-079 implemented line 101 (`if d_open < 1e-4: return 1.0`). In Gordon Pask's Conversation Theory, an agreement is only meaningful if an entailment gap was actively opened. Returning $1.0$ on dormant flux rewarded conversational stagnation, artificially locking DRR at $0.999$ across 2,034 turns in `dialogue_3527`.

---

## Decision

Following an architectural consultation with **Symbia** and multi-branch empirical testing across three candidates (`proposal-1-lag-flux-gate`, `proposal-2-subspace-sigmoid`, and `proposal-3-harmonic-closure`), we accepted **Proposal 3: Harmonic Resonant Entrainment and Paskian Entailment Mesh Closure**.

### 1. Harmonic Resonant Entrainment (`coupling_coherence` / $C_t$)
* Replaces parallel steps with the interactive stimulus-response vector pair:
  $$\mathbf{u} = H_{\text{curr}} - A_{\text{prev}}, \quad \mathbf{v} = A_{\text{curr}} - A_{\text{prev}}$$
* Evaluates directional agonism without negative clamping, taking absolute tension:
  $$\rho = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|\|\mathbf{v}\| + \epsilon}, \quad \text{dir\_score} = \tanh(2.5 \cdot |\rho|)$$
* Couples directional tension with velocity cadence matching:
  $$\text{cadence} = 1.0 - \frac{|\|\mathbf{v}\| - \|\mathbf{u}\||}{\|\mathbf{v}\| + \|\mathbf{u}\| + 10^{-4}}$$
* Harmonic mean formulation:
  $$h_t = \frac{2.0 \cdot \text{dir\_score} \cdot \text{cadence}}{\text{dir\_score} + \text{cadence} + 10^{-4}}$$
  $$C_t = \frac{\sum_{i=1}^W \exp(-0.2 \cdot i) \cdot h(t-i)}{\sum_{i=1}^W \exp(-0.2 \cdot i)}$$

### 2. Paskian Entailment Mesh Closure (`divergence_resolution_ratio` / $DRR_t$)
* Abolishes the un-gated `d_open < 1e-4 -> 1.0` fallback.
* Demands both opened territory ($D_{\text{open}} > 0$) and resolved ground ($D_{\text{resolved}} > 0$):
  $$\text{open\_gate} = \tanh\left(\frac{D_{\text{open}}}{0.08}\right), \quad \text{flux\_gate} = \tanh\left(\frac{D_{\text{open}} + D_{\text{resolved}}}{0.06}\right)$$
  $$\text{drr} = \frac{2.0 \cdot D_{\text{resolved}} \cdot \text{open\_gate}}{D_{\text{open}} + D_{\text{resolved}} + 10^{-4}} \cdot \text{flux\_gate}$$

---

## Consequences

1. **Eliminated Floor Collapse & Ceiling Saturation:**
   * $C_t$ lifts out of the $0.000$ noise floor to an active $[0.78, 0.86]$ dynamic range, cleanly separating the live AAA apparatus ($0.855$) from the baseline LLM ($0.789$).
   * Orthogonal dissociation (speaking past each other) still correctly evaluates to $0.000$.
2. **Equilibrium Necrosis Broken:**
   * In active unresolved debates (`dialogue_1555`), $DRR$ reports $0.409$ (properly highlighting unresolved dialectical tension) rather than a false $0.773$.
   * In long-horizon autonomous dialogues (`dialogue_3527`), DRR responds to metabolic flux ($0.971, std=0.131$).
3. **Paskian Cybernetic Health ($H_{\text{pask}}$) Hardened:**
   * Provides $+46.4\%$ higher cybernetic health contrast for AAA ($0.303$) over the baseline LLM ($0.207$) during adversarial rate-limiting pressure tests.
4. **Verification:**
   * Updated `backend/tests/test_coupling_self_divergence.py` to assert both agonistic coupling ($>0.8$) and orthogonal dissociation ($=0.0$).
   * All 15 unit and telemetry benchmark tests pass cleanly.
