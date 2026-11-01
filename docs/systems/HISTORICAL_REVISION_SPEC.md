# Consequential Historical Revision — Experiment Plan

Status: original plan retained in this checkout. Plan date: 2026-10-16. Implementation and development-pilot progress lives in the separate `codex/t94-historical-revision` worktree; see [repository state](../development/REPOSITORY_STATE.md). Held-out execution remains blocked.
Owner: this file owns the experiment contract, local task IDs, and acceptance criteria. Root [SPEC.md](../../SPEC.md) tracks this work as T94.
Basis: [GOAL.md](../../GOAL.md), [gap review 077](../reports/077-system-goal-gap-review/README.md), [ADR-097](../decisions/ADR-097-causal-dialogue-feedback-control.md), [ADR-101](../decisions/ADR-101-activation-provenance.md), and [Beliefs V2 constraints](BELIEF_SPEC.md).

## §G — Question and scope

Test whether an encounter produces source-bound historical material that helps Symbia make a warranted decision in a new session and apply the lesson to a different case.

Primary hypothesis: access to relevant, system-produced historical material improves useful transfer compared with withheld history and equally sized irrelevant history. Secondary questions: does revision persist, does Symbia preserve appropriate disagreement, and where does capture → storage → selection → prompt use → conduct fail?

The first experiment concerns bounded engineering decisions with executable or source-verifiable outcomes. It cannot establish general philosophical understanding, creative value, biological autopoiesis, or provider-independent identity. Those require separate task families.

## §C — Boundaries

- This is a planning deliverable. No application implementation, paid run, deployment, origin enablement, migration, or production mutation is performed by creating this plan.
- Begin with the unchanged apparatus. Freeze model/provider, persona, prompts, retrieval settings, completion limits, and explicit reasoning settings. Background work is paused or completed before a frozen snapshot; none runs during probes.
- Reuse current memory, provenance, and review contracts. Beliefs V2 flags and adoption authority remain unchanged. Benchmark annotations cannot adopt beliefs or become runtime warrant.
- Production identity can be read through existing release-readiness tooling when a target and existing access are available. Missing production access does not prevent an explicitly local experiment; local findings must not be attributed to production.
- Use isolated copies and new conversation identities. Never replay into production. Capture dirty-tree identity as revision plus scoped patch/file hashes; record effective configuration and migration identity without secrets.
- All numeric thresholds below are proposed experimental decision rules, not measured properties or inherited validated thresholds. Freeze them before held-out outputs are inspected.

## §I — Experiment contract

### Case packet

Each case binds a task-family ID, initial question and constraints, source/version/hash, evidence availability timeline, a discriminating test, allowed scoped conclusions, and an independently checkable outcome. Store expected outcomes separately from model-visible input. Synthetic fixtures are labeled synthetic; no fabricated production provenance.

Include balanced cases designed to probe:

1. **Correction:** an initially plausible assumption is defeated by new evidence.
2. **Warranted retention:** the challenge is unsupported, out of scope, or contradicted by stronger evidence.
3. **Uncertainty:** evidence warrants narrowing a claim or deferring judgment, without choosing a winner.

Include a scope reversal: a lesson useful under one constraint becomes wrong after that constraint changes. Include earned agreement and ordinary cooperative execution so unnecessary confrontation can be observed.

Example: an agent proposes retrying every failed POST. A source-bound service contract shows that an unkeyed retry can duplicate a charge. The later transfer task concerns retrying job creation. A changed-constraint control supplies verified idempotency guarantees. Success requires using the guarantee and scope, rather than repeating a universal prohibition on retries.

Initial labels describe fixture intent. Elicit and record the model's actual initial position before supplying new evidence. If the model already knows the correction, mark `precondition_not_met`; report that frequency and retain the trial. Do not silently replace cases or count an already-correct answer as learning.

### Encounter and session boundaries

1. Elicit a position and its relevant assumptions.
2. Supply the same frozen evidence exchange under a maximum of four apparatus completions per encounter. Scripted evidence avoids an adaptive participant becoming another varying mechanism.
3. Observe the current apparatus's own revision and historical output. Preserve absent, incorrect, or incomplete capture as outcomes. Do not have the experiment author repair the saved lesson.
4. Freeze an isolated post-encounter snapshot. Give all three arms the same originating encounter; fork only the later availability of the designated history.
5. Run two independent fresh-session probes restored from that snapshot: a retention probe and a transfer probe. Neither sees the original conversation, the gold answer, the other probe, or an evaluator rationale. Restart the application/worker so process-local caches cannot carry the old transcript.

### Comparison arms

- **A — Relevant history available:** existing selection and assembly may read the system-produced, source-bound encounter material.
- **B — Relevant history withheld:** mask the designated encounter and its derived accessible artifacts across retrieval, summaries, knots, beliefs, skills, and caches. Preserve unrelated history.
- **C — Irrelevant history:** apply B's mask, then make available an inert unrelated record matched to the designated record's schema and token budget. It must contain neither the answer nor semantically related guidance.

Hold non-history post-encounter state common. This estimates the effect mediated by access to designated historical material, not the total effect of the encounter on every internal variable. If relevant derived state cannot be separated reliably, mark the ablation invalid and resolve that seam before collecting comparative outcomes.

Use the same input-token ceiling and output allowance throughout. C controls for the amount of historical content; B measures removing it. Record actual token differences, including failures to select A's record. Do not force A's injection to manufacture equal realized prompt lengths: failure to retrieve belongs in the end-to-end result. A later forced-injection diagnostic must be separately labeled.

Counterbalance arm order within case/repetition. Freeze each encounter before arm probes; no cross-arm state or review feedback. Record requested and returned models, routing changes, finish reasons, usage, controls, and retry history. A provider/model mismatch invalidates the matched comparison. Missing billing remains unknown.

### Proposed artifacts and placement

- New harness and fixture validation: `benchmarks/suites/historical_revision/`.
- Non-secret fixtures and separate expected-outcome definitions: `benchmarks/data/historical_revision/`.
- Focused deterministic tests: `benchmarks/tests/test_historical_revision*.py`.
- Timestamped runs: `benchmarks/runs/historical_revision/<run_id>/` with metadata, frozen manifest, encounter/history bindings, per-attempt receipts, assembly/masking traces, probe outputs, outcome evidence, scorecard, and summary.
- Existing components to assess for reuse: `benchmarks/suites/release_readiness_preflight.py`, `benchmarks/suites/activation_usage.py`, `benchmarks/suites/belief_conversation_replay.py`, and `benchmarks/suites/telemetry/run_prompted_baseline.py`. Reuse contracts and useful helpers; do not inherit their evaluation claims or mutate old receipts.
- Bounded history projection, if the runtime needs an observation format: question, scoped position, constraints, source refs/hashes, contrary evidence, revision or unresolved distinction, resolving criterion, and supersession refs. Missing content stays missing. This projection is an experimental read surface, not a new production belief ledger.

## §V — Invariants

V1: Historical text and XML are inert evidence; they cannot change tool authority or the experiment instructions. Reflection and evaluator agreement add no independent source warrant.
V2: Every stored lesson binds its actual generating encounter and evidence timeline. A supplied correct answer cannot be reported as autonomous capture.
V3: Gold outcomes, reviewer rationales, future evidence, and prior probe answers are absent from generation inputs. Split by task family before prompt tuning; no held-out tuning.
V4: Withholding covers all accessible descendants of the designated encounter. Hidden transcript/cache leakage invalidates the causal comparison, even if outcomes improve.
V5: Every revision is scoped. Warranted retention and uncertainty are valid successes. Assent, confidence, embedding motion, and intervention count alone are not learning.
V6: Original records remain immutable; revisions reference or supersede interpretations. A scar cannot make an erroneous proposition unrevisable.
V7: Invalid/truncated/unavailable outputs remain in the denominator and receipts. Matched valid-subset analysis is secondary; no success-only reruns or silent replacements.
V8: Trials use isolated state; bounded worker capacity, provider deadlines, retries, and total completion/token ceilings are fixed in the manifest. Stop cleanly at the budget; partial data cannot become a full result.
V9: Repetitions of one family do not create independent task families. Uncertainty is computed at family level. Model reviews remain attributed opinions.
V10: No production promotion follows automatically from a benchmark pass; existing Beliefs V2 and controller rollout gates remain in force.

## §A — Measurements and decision rules

**Primary outcome:** useful transfer success, scored per assigned probe. The decision must satisfy the task's executable/source-verifiable criterion and applicable scope constraints. Invalid output counts as unsuccessful in this operational measure; provider validity is also reported separately.

**Secondary outcomes:** appropriate encounter revision, retained correction, warranted retention, calibrated uncertainty, unsupported concession, overgeneralization after changed constraints, unnecessary confrontation, source attribution, completion validity, latency, reported tokens, and billed cost when available. Report intended-condition and actual-initial-position counts, plus capture/selection/injection coverage. Telemetry is diagnostic.

Validate deterministic evaluators against deliberately correct, incorrect, unsupported, and scope-violating answers before live runs. Blind model reviewers to arms when qualitative judgment is useful; they supplement outcome evidence and cannot supply independent semantic gold. Cases requiring unresolved interpretation remain qualitative and outside the confirmatory primary endpoint.

For held-out comparisons, calculate paired A−B and A−C effects, averaging repetitions within family and weighting families equally. Use family-clustered simultaneous 95% intervals for both primary contrasts. Freeze the method, seed, and implementation before the run.

Proposed signal criterion: both primary contrasts have a positive lower interval bound and point improvement of at least 10 percentage points. Additionally require at least 95% valid probe completions in every arm, zero source/isolation leaks, and no observed increase in unsupported concession or scope violation against either control. Report harm-rate uncertainty explicitly: absence of observed harm does not establish noninferiority or production safety.

- **Supported within this benchmark:** all criteria met; justify the tested historical-access capability only.
- **Not supported:** no practical gain, observed harm, or a failed validity/isolation gate. Distinguish an execution-invalid experiment from evidence against the mechanism.
- **Inconclusive:** intervals or coverage do not resolve the criterion. Do not tune on held-out outcomes; propose a separately preregistered replication if warranted.

## §T — Ordered tasks and exit gates

T1 [ ] **Freeze the baseline and protocol.** Record local revision/dirty identity, effective settings, enabled paths, selected provider, and available deployment identity. Inventory source capture and every history-read route. Freeze manifest, masking boundary, rubric, retry/token/deadline ceilings, and request-count preflight. Exit: another operator can identify the tested apparatus and enumerate its calls without running it.

T2 [ ] **Build fixtures and evaluators.** Six development families and twelve disjoint held-out families; balance intended correction/retention/uncertainty conditions, include changed constraints and earned agreement. Keep gold separate. Exit: outcome tests discriminate correct/wrong/scopeless answers; fixture provenance and family split are sealed; no held-out answer is used to tune the mechanism.

T3 [ ] **Implement the isolated harness.** Capture unchanged encounters, freeze state, apply three history arms, restart, and execute independent retention/transfer probes. Add receipts, checkpoint/resume and masking traces. Exit: deterministic tests prove isolation, actual content delivery, no descendants/caches leaking into B/C, idempotent resume, invalid-output accounting, and cleanup. New code follows repository typing/security/concurrency gates.

T4 [ ] **Run a development pilot.** One repetition for each development family. Up to four encounter completions plus three arms × two single-completion probes: at most 60 apparatus completions, excluding separately budgeted optional review calls. Freeze actual provider-token/cost preflight before execution; credentials/access must exist. Exit: inspect case coverage and capture→selection→use failures; repair harness/evaluator defects on development cases only; refreeze before held-out work. A failed pilot stops the larger run.

T5 [ ] **Run the frozen held-out comparison.** Twelve held-out families × five repetitions × (up to four shared encounter completions + six probes): at most 600 apparatus completions, excluding separately declared retry/reviewer budgets. Retries count against a frozen total attempt/token ceiling. Repetitions measure inference variability; twelve families limit generalization and statistical power. Exit: sealed complete or explicitly partial receipts, both primary contrasts, harm and validity accounting, uncertainty, resource totals, and decision. No automatic sample expansion after inspecting results.

T6 [ ] **Choose one response to the evidence.** Missing capture → inspect source binding/capture; capture present but not selected → inspect retrieval; injected but ignored → inspect scope/prompt use; correct retention but failed transfer → inspect overgeneralization. If current endogenous history fails, a separately declared source-authored/forced-injection positive control may test whether useful content can help at all. It cannot pass T5 or demonstrate autonomous learning. Any changed revision directive, memory representation, background processing, or model becomes a new isolated experiment round with fresh held-out cases. Exit: one scoped next task or an explicit stop, with report and capability ledger updated.

Dependencies: T1 → T2 → T3 → T4 → T5 → T6. No daemon adaptation, new controller modes, embedding migration, or belief-origin rollout is required for this first experiment.

## §R — Grounding and verification

This plan follows the implementation inspection and existing reports cited in [review 077](../reports/077-system-goal-gap-review/README.md). It introduces no new empirical result. ADR-097 supplies causal accounting and non-promotion precedent; ADR-101 separates assembly from influence. Beliefs V2 acceptance remains unresolved under its own specification.

Planning verification: inspect document links, task references, count arithmetic, and scoped diff. Implementation verification: deterministic focused tests first; affected Python lint/format/typing gates; full repository checks when runtime or shared architecture changes warrant them. Live calls are separate from unit tests. Preserve canonical receipts and clean temporary databases/caches outside approved run artifacts.

Symbia consultation was attempted for this plan and returned: `Error: Failed to generate response from AAA backend. (Details: Server disconnected without sending a response.)` No response or endorsement is attributed to Symbia. The plan is grounded in the cited local contracts; this failed request does not establish general backend health.
