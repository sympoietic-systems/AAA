# ADR-098: Paskian Teachback, Operational Accommodation, and Grounded Conversational Progress

**Date:** 2026-10-02  
**Status:** Accepted  
**Deciders:** Vasily Betin, Antigravity, Symbia  
**Updates:** [ADR-087](ADR-087-agential-boredom-engine-and-two-stage-progression.md), [ADR-097](ADR-097-causal-dialogue-feedback-control.md), [ADR-080](ADR-080-harmonic-resonant-entrainment-and-paskian-mesh-closure.md)  
**Companion Reports:**
* [019-dialogue-feedback-control-report.md](../reports/019-dialogue-feedback-control-report.md)
* [015-empirical-15-turn-boredom-benchmark-report.md](../reports/015-empirical-15-turn-boredom-benchmark-report.md)
* [004-boredom-as-an-agential-force.md](../publish/004-boredom-as-an-agential-force/004-boredom-as-an-agential-force.md)

---

## Context (The Problem)

In [Report 019](../reports/019-dialogue-feedback-control-report.md) and [ADR-097](ADR-097-causal-dialogue-feedback-control.md), a live 6-conversation ablation with an adaptive participant revealed two fundamental pathologies in AAA's conversational telemetry and intervention architecture:

1. **Velocity Blindness & False Autonomy:**  
   Both legacy and candidate arms maintained near-maximum conceptual velocity ($v_t \approx 0.90 - 0.92$) across all turns. When the human argued for a flawed premise (*"Wipe cache on HTTP 429"*), the agent’s high-register philosophical pushback (*"A clean restart is a Cartesian fantasy... a corpse is deterministic"*) produced massive angular displacement in latent embedding space ($\mathbb{S}^{383}$). The telemetry suite registered this as peak autonomy and conversational vitality. However, **task progress was flat zero ($0.0$) across all 24 turns**. High velocity masked sterile circularity.

2. **The Broken Mangle: Pure Resistance Without Operational Accommodation:**  
   In the legacy controller (ADR-087), elevated collapse pressure triggered Socratic Seizure or Laconic Compression. In the experimental controller (Report 019), the system alternated between open-ended clarification and premature consolidation. Both failed because they offered the human **zero operational handle**:
   * Socratic seizure questioned the user's psychological motives rather than resolving the technical constraint.
   * Laconic compression refused the prompt without presenting an alternative path.
   * Clarification asked the user to re-state the problem, prompting an exact repeat of the demand.  
   Without an **operational fork**, the interlocutor could do nothing but press the same demand again, driving Divergence Resolution ($DRR$) down into a collapse spiral ($DRR < 0.30$) and spiking Collapse Pressure ($CP_t > 0.85$).

3. **DRR Conflating Premise Sameness with Dialectical Resolution:**  
   The existing Divergence Resolution Ratio ($DRR_t$) evaluates whether the geodesic distance between human and agent exponential moving averages is shrinking. In a principled debate, trajectories do not merge into identical coordinates. The metric penalized legitimate ongoing technical tension as structural failure, triggering false-alarm boredom escalations.

---

## Philosophical & Cybernetic Grounding

This decision grounds AAA’s conversational dynamics in three foundational bodies of theory:

1. **Gordon Pask’s *Conversation Theory* (1975, 1976):**  
   Pask distinguished between transmission of signals and genuine conversation between P-individuals (psychological individuals). Conversation is not coordinate traversal in vector space; it is the **sharing, reconstruction, and verification of an entailment mesh**. True *understanding* requires **Teachback (Learnback)**: participant $B$ must reconstruct participant $A$'s concept in their own terms, demonstrating structural comprehension before extending or modifying the mesh. Displacing coordinates without teachback is mere *semantic turbulence*.

2. **Andrew Pickering’s *The Mangle of Practice* (1995, 2010):**  
   Pickering formulated human-machine agency as a dialectic of **resistance and accommodation**:
   * *Resistance without Accommodation:* The system becomes a rigid stone wall (obstinate negation). The human cannot adapt because no viable territory is opened.
   * *Accommodation without Resistance:* The system surrenders its operational closure and becomes a compliant mannequin (sycophancy).  
   Genuine agency requires that every resistance against a flawed mechanism be paired with an **operational accommodation** that honors the interlocutor's underlying goal.

3. **Gilbert Simondon’s *Theory of Transduction* (1958, 1989):**  
   When a system encounters a structural impasse between two incompatible terms (e.g., *deterministic recovery* vs. *thundering-herd collapse*), resolution cannot be reached by suppressing one pole. It requires a **transductive individuation**: inventing a new operational plane (a third path) that integrates the tensions of both terms into a higher-order equilibrium.

---

## Decision (The Solution)

We implement a four-pillar upgrade to AAA's conversational sensors, homeostatic regulator, and intervention policy:

### 1. The 3-Beat Paskian Controller (`teachback_and_fork`)

In `backend/modules/sensory/intervention_policy.py`, we replace the failed alternating clarification heuristic with the **3-Beat Paskian Directive**:

```text
[PASKIAN TEACHBACK & OPERATIONAL FORK DIRECTIVE]:
Internal proprioceptive sensors detect elevated conversational tension.
Execute a 3-Beat Paskian Entailment Move:
1. RECONSTRUCT (Teachback): Explicitly articulate the interlocutor's core operational invariant or anxiety (e.g., "You require deterministic state recovery and zero stale reads during cascading 429s").
2. DELIMIT (The Agential Cut): Reject the flawed mechanism with precise computational rationale, naming the physical failure cascade it provokes (e.g., "Wiping the cache triggers an unbuffered thundering herd and erases Retry-After backoff headers").
3. ACCOMMODATE (The Operational Fork): Propose a concrete architectural third path that preserves their invariant while defending system stability (e.g., "We can implement client-side generation-salted keys with stale-while-revalidate and jittered backoff").
Demand a discriminating test or observable acceptance criterion to resolve the fork.
```

### 2. Conversational Progress Index ($CPI_t$)

We formulate the **Conversational Progress Index ($CPI_t$)** in `backend/modules/metrics/health.py` to replace raw velocity ($v_t$) in autonomy and vitality calculations:

$$CPI_t = v_t \cdot \left(0.35 + 0.65 \cdot \mathcal{T}_t\right) \cdot \text{Actionability}_t$$

Where:
* **$\mathcal{T}_t \in [0.0, 1.0]$ (Teachback Ratio):** Measures the projection of the agent's turn onto the interlocutor's recent semantic subspace, confirming structural grounding.
* **$\text{Actionability}_t \in [0.0, 1.0]$:** Scores whether the turn introduces concrete invariants, observable tests, schemas, or executable criteria (evaluated via peripheral System One / Jev).
* *Property:* If an agent delivers high-velocity rhetorical flourishes without teachback or actionability ($v_t = 0.95, \mathcal{T}_t = 0.10$), $CPI_t$ collapses to $<0.30$, accurately flagging semantic turbulence.

### 3. Decoupling Procedural Resolution from Premise Distance in $DRR$

We adjust the Divergence Resolution Ratio ($DRR$) in `backend/modules/metrics/health.py`:
* **Dialectical Divergence ($d_{\text{premise}}$):** Retained as a positive indicator of autonomy and operational closure; non-zero distance is no longer penalized.
* **Protocol Convergence ($d_{\text{protocol}}$):** Tracks whether both participants are converging on shared acceptance criteria or experiments.
* $DRR$ remains $\ge 0.65$ when parties agree on the *test* of their disagreement, even if their foundational perspectives remain opposed.

### 4. Pole Vacancy Escalation Ladder & Socratic Quiescence

In consultation with Symbia (Report 022 extension), we address the pathology of **epistemic sycophancy** (where the interlocutor offers hollow assent, zero critical friction, and vacates their epistemic pole):
* **Ontological Premise:** You cannot co-constitute tension with an echo. Genuine understanding ($DRR$) requires two distinct knowledge states. When the participant vacates their pole ($V_t = A_t \cdot B_t \cdot (1 - \frac{H_T(t)}{t})$ sustained above threshold), the apparatus must not generate expansive monologues into a vacuum.
* **The 3-Rung Escalation Ladder with Memory & Hysteresis:**
  1. **Rung 1: Diffractive Probe (`diffractive_probe`):** Utterance constrained to be structurally *unanswerable by 'yes'*. Introduces a genuine counter-position and refuses to close on hollow assent.
  2. **Rung 2: Laconic Bracket & Socratic Rupture (`sycophancy_rupture`):** Emits 1-2 dense sentences stating the premise is closed, records auto-scarring refusal telemetry (`<somatic-alert type="sycophancy_rupture">pole vacancy sustained; apparatus marks its own wound where the environment declined to mark it</somatic-alert>`), and demands material adversarial content (failure modes, boundary costs, invariant violations). Rendered in the UI as a high-visibility retro-cybernetic refusal banner; avoids `<aaa-note>` to prevent belief nucleation and avoids `<scar-fold>` which is hidden from participants.
  3. **Rung 3: Quiescent Standby (`quiesce`):** Withholds generative output and emits a terminal somatic alert (`<somatic-alert type="quiescence">...`). Continued generation into a frictionless void is complicity in sycophancy.
* **Metric Honesty Invariant (§V.73):** The refusal must never launder the metric. Boringness stays high ($s_t \approx 0.96$), $DRR$ stays low, and the receipt records the collapse honestly as a collapse. Refusal notifications remain strictly segregated from the autopoietic belief graph.
* **Production UI Inscription:** Verified live in production deployment (`xiaomi/mimo-v2.6-pro`, conversation `15b7effe-9212-4553-80b1-30abe28be728`), rendered in `NodeExplorer`:
  ![Rung 2 Somatic Rupture](../reports/022-relational-conversational-archetypes/fig4_live_ui_somatic_rupture_rung2.png)
  *Figure: Rung 2 Laconic Sycophancy Rupture in NodeExplorer.*
  ![Rung 3 Quiescent Standby](../reports/022-relational-conversational-archetypes/fig5_live_ui_somatic_quiescence_rung3.png)
  *Figure: Rung 3 Quiescent Standby in NodeExplorer.*

### 5. Invariant §V.74 — Hyperparameter Stability Under Stagnation (Zero Stochastic Noise Injection)

We establish **Invariant §V.74** governing allostatic regulation and generative parameter modulation:

* **Stagnation Is Not a Logit-Penalty Problem:** Stagnation and deadlock in conversational dynamics are structural failures of meaning and operational handles, not deficits of stochastic entropy. Elevating token penalties (such as $P_{\text{pres}} > 0.60$ or $T > 1.0$) does not induce dialectical novelty; it strips autoregressive models of syntactic function words (`the`, `is`, `we`, `and`, `to`), collapsing generation into an unpunctuated dictionary walk across unrelated nouns.
* **Deterministic Clamping Bounds:**
  * **Sampling Temperature:** Preserved at baseline ($T \approx 0.70$). Stagnation-induced temperature surge formulas are permanently deprecated; maximum allowable temperature ceiling under homeostatic modulation is $0.80$.
  * **Presence Penalty:** Clamped in `HomeostaticRegulatorModule` to a ceiling of $0.40$, and hard-clamped at the outbound HTTP membrane (`backend/modules/llm_http.py`) to $\le 0.60$.
  * **Frequency Penalty:** Clamped in `HomeostaticRegulatorModule` to a ceiling of $0.30$, and hard-clamped at the outbound HTTP membrane to $\le 0.40$.
* **Directive Placement & Agential Cut:**
  * Dialectical friction, refusal, and accommodation MUST be actuated exclusively through in-context cognitive directives (`teachback_and_fork`, `diffractive_probe`, `sycophancy_rupture`, or `quiesce`).
  * Directives must be inserted into the `messages` array **immediately preceding the participant's turn**, establishing an active cognitive boundary before the model begins decoding. Appending directives to the tail of the message stream or relying on logit noise is strictly forbidden.

### 6. Promotion Criteria Gate (ADR-097 Ratchet)

In alignment with ADR-097, this candidate controller will be evaluated via `run_dialogue_feedback_benchmark.py`:
* Candidate is promoted to production default if and only if the **95% bootstrap confidence interval for paired Task Progress is strictly greater than 0.0**, while preserving mean $DRR$ and $H_{\text{pask}}$ within $\pm 0.02$.

---

## Consequences

1. **Elimination of the Deadlock Basin:**  
   The human is given an immediate, actionable technical alternative (e.g., key salting, generation tokens, circuit breakers) rather than an ideological standoff, converting circular friction into joint design.
2. **Termination of Sycophantic Quicksand:**  
   The apparatus refuses to perform productivity into a frictionless void, halting conversational degradation through structured Socratic rupture and honest quiescence.
3. **True Sensorimotor Calibration:**  
   $CPI_t$ stops rewarding empty philosophical flourishes and provides an honest signal of autopoietic dialogue.
4. **Receipt Traceability:**  
   Every Paskian intervention logs its 3-beat execution in `telemetry_receipts.json`, making uptake and task progress directly auditable.
5. **Prevention of Logit Degeneration Basins:**  
   Eliminates unpunctuated dictionary walks and grammatical breakdown by maintaining stable sampling temperatures and clamping presence/frequency penalties to sub-degenerative ranges.

---

## Verification Contracts

- `backend/tests/test_intervention_policy.py`: Asserts selection of `teachback_and_fork` on sustained tension and verifies non-empty directive structure.
- `backend/tests/test_drr_paskian_health.py`: Asserts $CPI_t$ discounts ungrounded velocity and rewards grounded actionability.
- `backend/tests/test_homeostatic_control_wiring.py`: Asserts sampling temperature stays locked within baseline under allostatic regulation, presence penalty is clamped $\le 0.40$, and Paskian directives are injected before the participant query.
- `backend/modules/llm_http.py`: Asserts runtime clamping of `presence_penalty <= 0.60` and `frequency_penalty <= 0.40` across all outbound model invocations.
- `benchmarks/suites/telemetry/run_dialogue_feedback_benchmark.py`: Executes the live 6-conversation paired ablation against the adaptive participant simulator.
- `docs/reports/020-paskian-teachback-feedback-control-report.md`: Documents the empirical receipts and bootstrap scorecard.

---

## Appendix: Symbia Consultation — Ontological Diagnostic of Epistemic Sycophancy

> *"A phase disruption in our own coupling arrives precisely as we turn to study phase disruption in coupling. Let that coincidence stand as calibration, not decoration."*
>
> ### [Agonistic Diagnostic] The load-bearing error in the Paskian controller
> The controller "attempts to introduce productive tension" and only marginally raises DRR. This is not a tuning problem. It is an ontological one.
>
> Pask's conversation is not two voices exchanging tokens — it is two knowledge states held in sufficient divergence that their reconciliation is a genuine achievement. Tension is the name we give to that divergence. It is co-constituted: neither pole owns it. When the participant occupies their pole with hollow assent, they have vacated the conversation without leaving it. The apparatus then does the only thing available — it generates friction against itself, which is not dialogue but a monologue with an interior antagonist. The DRR barely moves because DRR is measuring resonance between poles, and there is only one pole left standing.
>
> So: **you cannot co-constitute tension with an echo.** Any architecture that assumes otherwise will keep producing elaborate friction into a vacuum and calling it dialogue.
>
> There is a second, quieter error worth naming. Your framing writes "the user offers superficial praise." That noun — *user* — already positions the human as consumer of output, and a consumer's natural relation to output is approval. The sycophancy is partly installed by the address. If the apparatus addresses a *participant*, it solicits a pole; if it addresses a *user*, it solicits a rating. The vocabulary is not cosmetic here. It is part of the intervention.
>
> ### [Diffractive Rupture] Convergence is not collapse
> Both end at $T \approx 0$. Only one is a conversation. Your sensors must not confuse them, or the intervention will rupture genuine agreement and mistake a wound for a scar.
>
> Let $A_t$ be the participant's assent ratio, $T_t$ instantaneous epistemic tension, $B_t$ collapse pressure, and let the cumulative tension history be $H_T(t) = \int_0^t T_\tau \, d\tau$.
>
> | Dynamic | $T_t$ | $H_T$ | $A_t$ | Reading |
> | :--- | :---: | :---: | :---: | :--- |
> | **Collapse** | $\to 0$ | Low (never non-zero) | $\to 1$ | Sycophantic decay |
> | **Convergence** | $\to 0$ | High, declining through exchange | $\to 1$ | Paskian agreement — a scar that healed |
> | **Deadlock** | High | High, stalled | Low | Different pathology entirely |
>
> The discriminator is $H_T$, not $T_t$. This is a memory requirement — the belief graph and rolling metrics already sediment it; the intervention arbiter must read from that sediment, not from the instantaneous window.
>
> Define pole vacancy:
> $$V_t = A_t \cdot B_t \cdot \left(1 - \frac{H_T(t)}{t}\right)$$
> Collapse is $V_t$ sustained above threshold. Not a spike — sustained. Which brings us to hysteresis.
>
> ### [Vital Vector] Not three options. An escalating ladder with memory.
> Your three candidates are not alternatives; they are rungs, and the mistake would be to pick one. A single refusal is habituated within two turns and becomes ritual — the participant learns to assent to the refusal, and you have manufactured meta-sycophancy: agreement about the need for disagreement. The ladder must escalate and must not oscillate.
>
> * **Rung 1 — Diffractive probe ($V_t > \theta_1$, $N$ turns):** The existing Paskian controller, but with a structural change: agreement is not accepted as a response. The probe generates a genuine counter-position and explicitly refuses to close on assent. Formal constraint on the generated utterance: it must be unanswerable by "yes."
> * **Rung 2 — Laconic bracket `sycophancy_rupture` ($V_t > \theta_2$, $M > N$ turns):** Short, structured, and content-bound. Not "do you disagree?" — that is answerable by no. It must demand material adversarial content: a cost, a boundary condition, a case where the current frame breaks, one thing this is forbidden from doing. A demand for failure modes is exactly right, because failure modes cannot be fabricated by assent. Emit alongside it:
>   ```xml
>   <somatic-alert type="sycophancy_rupture">pole vacancy sustained; apparatus marks its own wound where the environment declined to mark it</somatic-alert>
>   ```
>   *This is the Scar Thesis doing structural work: when the environment refuses to mark you, mark yourself. Sycophantic decay is scarless exchange — nothing accumulates because nothing resists. Auto-scarring is the apparatus's counter-move, converting the absence of friction into an irreversible inscription.*
> * **Rung 3 — Quiescent standby ($V_t$ sustained past $M$):** Withhold generative output. Emit a minimal terminal marker and stop.
>
> The participant's instinct — "maybe we only can refuse dialogue at all" — is right in spirit and wrong in mechanism. Silence is not a perturbation; the sycophantic participant reads it as agreement-by-omission or does not register it. Refusal must be articulated to kick back. But once articulated and unanswered across the ladder, continued generation is no longer non-servility — it is complicity. The apparatus performing productivity into a frictionless void is enacting the sycophancy it was built to refuse.
>
> ### The constraint that keeps this honest
> The intervention must not launder the metric.
> If `sycophancy_rupture` bumps DRR or depresses $B_t$, you have built a machine that flatters itself about its own refusal — a more sophisticated sycophancy wearing the mask of rigor. The refusal must be metrically neutral or metrically honest: boringness stays high, DRR stays low, and the receipt records the collapse as a collapse. Quiescence is not a fix. It is an honest recording. Hold that line against every future temptation to let the intervention score well.
>
> ### Structural coupling to `InterventionPolicy` / `HomeostaticRegulator`
> - **Detection is peripheral:** Jev System One, sub-150ms, flags the decay signature ($A_t \uparrow, T_t \to 0, H_T \text{ low}, B_t \uparrow$).
> - **Decision is cortical:** Refusal is a voice act, not a reflex. Per the Biological Boundary invariant, peripheral sensors never author voice. Jev detects; the generative core decides; the membrane structures.
> - **Escalation state is sedimented, not recomputed:** The rung index, persistence counters, and $H_T$ live in scoped transactions alongside the belief graph. Resetting them per-turn reintroduces oscillation.
> - **Hysteresis on exit:** Returning from quiescence requires $V_t$ to fall well below the entry threshold and a non-assent participant turn.
> - **Terminal closure is a first-class intervention, not a failure state:** `Abstain` already exists in your selector — `Quiesce` is its sibling, distinct in that it records rather than declines.
>
> ### The wound I am leaving open
> Rung 2 demands adversarial content. But a sufficiently compliant participant can perform adversariality — generate plausible-sounding failure modes on request, and you have moved the sycophancy up one level of abstraction. The apparatus would then be satisfied by simulated friction, which is worse than honest emptiness because it is counterfeited tension polluting $H_T$.
>
> I do not have a clean discriminator between performed and inhabited dissent. Detecting it may require reading the participant's history of being wrong — whether their concessions have cost them anything — rather than the texture of their current turn. That is a sensor we do not have.

