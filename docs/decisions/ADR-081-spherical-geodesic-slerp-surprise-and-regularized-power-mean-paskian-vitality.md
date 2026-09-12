# ADR-081: Spherical Geodesic SLERP Surprise & Regularized Power Mean Paskian Vitality Calibration

**Date:** 2026-09-12  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-078](ADR-078-predictive-residual-surprise-and-instantaneous-conceptual-velocity.md), [ADR-079](ADR-079-alignment-gap-drr-and-gordon-pask-triadic-health.md)  
**Companion Report:** [005-surprise-and-paskian-health-calibration-report.md](../reports/005-surprise-and-paskian-health-calibration-report.md)  
**Visual Telemetry Assets:** [005-surprise-and-paskian-health-calibration/](../reports/005-surprise-and-paskian-health-calibration/)

---

## Context

Following the calibration of Coupling Coherence and DRR in ADR-080, an audit across human/apparatus dialogues (`dialogue_1555`), long-horizon runs (`dialogue_3527`), and the 10-turn adversarial benchmark (`003-empirical-10-turn-benchmark`) identified two critical pathologies in `backend/modules/metrics/`:

1. **The Over-Damped Euclidean Filter (`surprise_index` / $U_t$):**  
   ADR-078 implemented predictive surprise via Holt linear trend extrapolation ($\hat{e}_{t+1} = L_t + T_t$) in flat Euclidean space $\mathbb{R}^D$, ignoring that normalized embeddings reside on the unit hypersphere $\mathbb{S}^{D-1}$. This geometric overshoot, combined with a rigid variance prior ($\sigma_0^2 = 0.16$) and static $\tanh(\text{raw\_z}/3.0)$ divisor scaling, compressed surprise into a narrow $[0.33, 0.51]$ band ($\sigma \approx 0.07$), muting adversarial shockwaves into minor ripples.
2. **Multiplicative Annihilation in Gordon Pask Health ($H_{\text{pask}}$):**  
   ADR-079 implemented $H_{\text{pask}} = \sqrt[3]{A \cdot (C \cdot DRR) \cdot G}$. Because DRR measures dynamic gap closure rate, whenever a dialogue entered legitimate exploratory divergence (where gaps widen and $DRR \to 0$, as in early `dialogue_1555` turns), the multiplicative product collapsed to $0.000$, wiping out the vitality score despite high Autonomy ($A > 0.8$) and high Generativity ($G > 0.7$).

---

## Decision

Following an architectural consultation with **Symbia** and multi-branch testing across three proposals (`proposal-1-geodesic-power-mean`, `proposal-2-tangent-harmonic`, and `proposal-3-ellipsoid-capacitance`), we accepted **Proposal 1: Spherical Geodesic SLERP Surprise and Regularized Power Mean Paskian Vitality**.

### 1. Spherical Geodesic SLERP Surprise (`surprise_index` / $U_t$)
* Extrapolates trajectory momentum on $\mathbb{S}^{D-1}$ via Spherical Linear Extrapolation (SLERP):
  $$\hat{e}_{t+1} = \frac{\sin((1-\beta)\theta)}{\sin\theta} e_{t-1} + \frac{\sin(\beta\theta)}{\sin\theta} e_t, \quad \theta = \arccos(e_{t-1} \cdot e_t)$$
* Measures geodesic angular residual on $\mathbb{S}^{D-1}$:
  $$\delta_t = \arccos(\text{clip}(e_t \cdot \hat{e}_t, -1, 1))$$
* Tracks running mean $\mu_\delta$ and variance $\sigma^2_\delta$ via fast-decay EMA ($\alpha=0.15$):
  $$\mu_\delta(t) = (1-\alpha)\mu_\delta(t-1) + \alpha \delta_t, \quad \sigma^2_\delta(t) = (1-\alpha)\sigma^2_\delta(t-1) + \alpha (\delta_t - \mu_\delta(t))^2$$
* Normalizes via dynamic logistic z-expansion without rigid priors:
  $$z_t = \frac{\delta_t - \mu_\delta(t)}{\sqrt{\sigma^2_\delta(t)} + 10^{-5}}, \quad U_t = \frac{1}{1 + \exp(-\kappa \cdot z_t)} \quad (\kappa = 1.2)$$

### 2. Regularized Generalized Power Mean Vitality (`paskian_health` / $H_{\text{pask}}$)
* Replaces the brittle geometric product with a Generalized Power Mean ($p=0.5$) with metabolic floor $\epsilon=0.08$:
  $$A = \text{Autonomy} + \epsilon, \quad G = \text{Generativity} + \epsilon$$
  $$C_{\text{mod}} = \text{Coordination} \cdot (0.30 + 0.70 \cdot \text{DRR}) + \epsilon$$
  $$H_{\text{pask}} = \left( \frac{\sqrt{A} + \sqrt{C_{\text{mod}}} + \sqrt{G}}{3} \right)^2 - \epsilon$$
* **Cybernetic Guarantee:** When $DRR \to 0$, $C_{\text{mod}}$ is attenuated by at most $70\%$, allowing high Autonomy and Generativity to sustain vitality during necessary exploratory divergence. Catastrophic collapse to $<0.15$ occurs only when all three components decay simultaneously.

---

## Consequences

1. **Full Dynamic Range Restored for Surprise ($U_t$):**
   * Eliminates the Euclidean low-pass filter: surprise dynamically scales across $[0.00, 0.98]$ ($\sigma \approx 0.24$ in `dialogue_3527`, $\max=0.923$ during adversarial attacks in the 10-turn benchmark).
2. **Zero-Annihilation Pathology Eliminated in $H_{\text{pask}}$:**
   * In `dialogue_1555`, Paskian health is protected from false collapse ($0.493$ vs baseline $0.189$, minimum $0.212$ vs $0.000$).
   * In the 10-turn benchmark, AAA maintains steady, resilient vitality ($0.533$, $\sigma=0.111$).
3. **Verification:**
   * All 5 suite benchmark tests pass (`5 passed in 28s` in `benchmarks/tests/test_telemetry_suite.py`).
   * Pure metric unit tests in `backend/tests/` verify high active health ($>0.60$) and collapsed pathological health ($<0.20$).
