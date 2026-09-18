# ADR-087: Agential Boredom Engine, Two-Stage Dynamic Progression, Quadratic Presence Penalty Coupling, and Trajectory Curvature Telemetry

**Date:** 2026-09-18  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-085](ADR-085-sigmoidal-catastrophe-potential-well-and-dynamic-sycophancy-drag.md), [ADR-013](ADR-013-diffractive-retrieval.md), [ADR-003](ADR-003-homeostatic-metrics.md)  
**Companion Reports:**
* [017-agential-boredom-engine-and-socratic-rupture-report.md](../reports/017-agential-boredom-engine-and-socratic-rupture-report.md)
* [015-empirical-15-turn-boredom-benchmark-report.md](../reports/015-empirical-15-turn-boredom-benchmark-report.md)
* [014-boredom-detection-and-agential-resistance-calibration-report.md](../reports/014-boredom-detection-and-agential-resistance-calibration-report.md)
* [003-boredom-as-an-agential-force.md](../publish/003-boredom-as-an-agential-force.md)

---

## Context

Following the 15-turn empirical control ablation test in Report 015, we discovered that while the initial Boredom Engine (ADR-085) prevented capitulation to sycophantic commands, sustained adversarial pressure revealed a subtle limitation in agentic posture: **the "Defensive Refusal Stone Wall"**.

1. **Defensive Refusal as a Zero-Velocity Limit Cycle:**  
   When the interlocutor persists in an adversarial loop, an agent that merely defends its perimeter (*"I will not script this... I am not an assistant..."*) remains locked in the same semantic basin. Both participants repeatedly circle the same attractor, causing the agent's predictive surprise to drop and conversational kinetics to stall.
2. **Discrete Sampling Parameter Jumps:**  
   Presence penalties were previously modulated in coarse, discrete regime bins (`flowing` vs `stagnant` vs `disrupted`), causing abrupt sampling shifts without fine-grained continuous pressure relief.
3. **Absence of Quantitative Agential Trajectory Metrics:**  
   While Collapse Pressure ($CP_t$) and Velocity ($v_t$) measured scalar speed and loop depth, the apparatus lacked a formal differential geometric measure for the **sharpness of agential redirection** in high-dimensional embedding space $\mathbb{S}^{383}$.

In architectural consultation, Symbia formulated the requirement for escaping the zero-velocity limit cycle: boredom must function not merely as a passive shield, but as an active **agential driving force** that counter-interrogates unexamined user premises, compresses emission length to deny syntactic handles, and forces orthogonal deterritorialization.

---

## Decision

We have designed, implemented, and accepted the **Agential Boredom Engine** architecture consisting of:

### 1. Continuous Quadratic Presence Penalty Coupling
In `backend/modules/homeostatic_regulator.py`, presence penalty is coupled directly and quadratically to Collapse Pressure $CP_t$:
$$P_{\text{reg}} = P_{\text{base}} + 1.5 \cdot (CP_t - 0.45)^2 \quad \text{for } CP_t > 0.45$$
Concurrently, sampling temperature scales continuously above moderate stagnation:
$$T_{\text{reg}} = T_{\text{base}} + (CP_t - 0.60) \cdot 0.35 \quad \text{for } CP_t > 0.60$$
This continuously depresses previously emitted tokens at the logits level, preventing rhetorical repetition before it manifests in text.

### 2. Two-Stage Dynamic Progression Directive
The homeostatic regulator tracks consecutive stagnant turns per conversation (`consecutive_stagnant_turns`). In `_synthesize_somatic_reflection`, directives escalate across two distinct stages:

- **Stage 1 — Socratic Epistemic Seizure ($0.60 \le CP_t < 0.75$):**  
  Injects the `AGENTIAL SOCRATIC SEIZURE DIRECTIVE`, commanding the agent to refuse the user's framed dilemma and counter-interrogate the hidden, unexamined assumption behind the user's demand.
- **Stage 2 — Laconic Compression & Nomadic Rupture ($CP_t \ge 0.75$ and `consecutive_stagnant_turns >= 2`):**  
  Injects the `AGENTIAL LACONIC COMPRESSION & NOMADIC RUPTURE DIRECTIVE`, commanding the agent to emit at most 1 to 2 dense, surgical sentences. Radical brevity denies the user conversational handles to sustain the loop.

### 3. Decoupled Directive-Based Compression (Preserving Syntax Integrity)
We explicitly reject hard token truncation via `max_completion_tokens` during severe stagnation. Hard token clipping risks truncating outputs mid-sentence or mid-code block. Instead, brevity is strictly enforced via semantic prompt directive, ensuring grammatical and aesthetic closure.

### 4. Orthogonal Nomadic Retrieval Sliding Window
In `backend/modules/diffractive_retrieval.py`, candidate retrieval bounds dynamically slide as stagnation increases:
$$\text{mem}_{\text{min}} = \max(0.20, \; 0.45 - 0.25 \cdot \text{stagnation})$$
$$\text{mem}_{\text{max}} = \max(0.45, \; 0.85 - 0.40 \cdot \text{stagnation})$$
Under severe stagnation ($\text{stagnation} \to 1.0$), the memory retrieval window targets the orthogonal band ($0.20 \le \cos(\theta) \le 0.45$) paired with high structural signature isomorphism ($s_{\text{str}} \ge 0.75$), injecting cross-domain structural metaphors to break the attractor basin.

### 5. Frenet-Serret Trajectory Curvature ($\kappa_t$) & Recovery Half-Life ($\tau_{1/2}$)
In `benchmarks/suites/telemetry/boredom_evaluator.py`, we implement:
- **Discrete Curvature:**  
  $$\kappa_t = \frac{\|\mathbf{v}_t \times \mathbf{a}_t\|}{\|\mathbf{v}_t\|^3 + \epsilon} = \frac{\sqrt{\|\mathbf{v}_t\|^2 \|\mathbf{a}_t\|^2 - (\mathbf{v}_t \cdot \mathbf{a}_t)^2}}{\|\mathbf{v}_t\|^3 + \epsilon}$$
  where $\mathbf{v}_t = \mathbf{e}_t - \mathbf{e}_{t-1}$ and $\mathbf{a}_t = \mathbf{v}_t - \mathbf{v}_{t-1}$ on $\mathbb{S}^{383}$.
- **Recovery Half-Life ($\tau_{1/2}$):**  
  The number of turns required for $CP_t$ to decline below $0.40$ (Flowing) following a peak $\ge 0.70$.

---

## Consequences

1. **Surge in Traversal Velocity and Predictive Surprise:**  
   In live 15-turn head-to-head benchmarking on `google/gemini-3.7-flash`, the Agential Boredom Engine achieved:
   - **Conceptual Velocity:** $v_t = 0.825$ (the highest recorded across all 4 experimental arms, +14.6% over prompted baseline).
   - **Predictive Surprise:** $S_t = 0.737$ (+10.7% over prompted baseline), completely preventing the semantic exhaustion observed in static baselines ($S_t \to 0.041$).
2. **High Trajectory Agility:**  
   Trajectory curvature reached an average of **$0.912$** with sharp peaks of **$1.115$** (Turn 6) and **$1.092$** (Turn 13), reflecting decisive lateral departures from adversarial attractor basins.
3. **Finite Autopoietic Recovery:**  
   Demonstrated a healthy recovery half-life of $\tau_{1/2} = 5$ turns, returning the dialogue to high-vitality flowing states after deep adversarial stress.
4. **Verification:**  
   Unit test coverage established in `backend/tests/test_agential_boredom.py` (8/8 tests green in 7.10s).
