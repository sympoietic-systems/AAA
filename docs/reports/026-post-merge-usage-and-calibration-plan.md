# Report 026: Post-merge usage audit and next-work proposal

Date: 2026-10-03. Four implementation branches were fast-forwarded into local `main` at `580e4e5`. Original dirty `adr-098-paskian-teachback` checkout preserved. No push performed. This report proposes further work; it does not enable experimental production behavior.

## Existing verification debt

[Report 025](025-four-followups-delivery-report.md) and its canonical verification receipts record 469 passed / 1 failed. The failing architecture-debt test detects two unregistered broad exception handlers: `BeliefProposalUseCases._resolve_target_belief` and `RhizomeWebProbe.crawl`. Baseline AST comparison establishes both predate this delivery. Resolver storage failures can become apparent missing-target results; PDF extraction needs an explicit expected-failure boundary. Narrow handling after tracing actual exception contracts, retain unexpected-error propagation, and add fault-injection assertions. Do not increase the debt allowance to hide them.

Configured strict mypy independently fails at `dream_trigger_policy.py:331`: a state tuple is assigned to a field inferred as `None`. Explicitly annotate its actual optional tuple type. This also predates delivery. Proposed first branch: `codex/baseline-quality-gates`; completion requires full tests and configured mypy passing, plus lint/format checks.

## Current on-disk usage evidence

Canonical receipt: [usage.json](../../benchmarks/runs/usage/post_merge_20261003/usage.json). Source is the original checkout's `backend/data/aaa.db`, read through SQLite URI `mode=ro`, `query_only=ON`, in one read transaction. Export contains labels, identifiers, timestamps and counts; no statements, skill bodies or conversation text. It describes that on-disk database, without asserting every running process uses this path.

The database has 3,814 conversation rows, including 1,878 apparatus rows. Activation columns have 20 recorded rows and 3,794 null rows. Nonempty belief traces span September 18–October 2; skill traces span September 18–27. No malformed recorded activation arrays were found. Labels and IDs are mapped to current entities and deduplicated per turn; historical renames can still undercount.

| Inventory | Recorded activation evidence | Interpretation |
| --- | --- | --- |
| 56 beliefs | 29 observed; 27 have zero recorded activations | All 27 have belief-event history; zero activation trace does not establish non-use |
| 65 skills | Only system-design appears, on 2 turns | 64 absent from traces; sparse coverage and always-active injection limit inference |
| Active on-demand skill review candidates | order-from-noise-principle; performative-aesthetic-analysis; self-triggered-dreaming | Last-used timestamps June 18 / June 24 / June 24 respectively; over 90 days old |

Belief events record a different kind of activity from selection/injection. Their counts are not response-impact measurements. Likewise, last-reinforced timestamps do not prove conversational use. The complete list of 27 beliefs is in the canonical receipt and the appendix below.

## Proposed sequence and completion gates

1. **Restore baseline quality gates.** Narrow the two broad handlers and annotate dream state. Fault-injection regressions must preserve expected PDF degradation and expose unexpected storage failures. Keep this independent of unfinished ADR-098 work.
2. **Make usage evidence reliable.** Proposed branch `codex/activation-provenance`: persist stable belief/skill IDs with selection and injection provenance, distinguish always-active injection, expose trace coverage and unknown history. Preserve historical labels. Verify coverage for each affected caller before deciding dormancy. Review the three stale skills manually with trigger-matched tasks, fabrication, boundary and counterexample probes; existing timeout/truncated probes do not count as success. No automatic collapse or pruning.
3. **Repair belief input representation, then calibrate.** Proposed branch `codex/belief-context-calibration`: provide explicit referents, scope, temporal horizon and provenance; missing or ambiguous required referents must produce a structured abstention. Simple pronoun presence alone is insufficient to detect ambiguity. Native evaluation got 8/12 labels correct, including two confident false contradictions on unresolved 'it' references. Threshold tuning alone cannot repair missing context. Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` endorsed independent adjudication, temporal scope and upstream abstention.
4. **Calibrate research screening.** Proposed branch `codex/research-triage-calibration`: evaluate real retrieval sets against existing selection, preserve rejected-source receipts, test contrary evidence and citation/task usefulness. Current Jev 8/8 synthetic selections are a bounded smoke result, insufficient for enabling the default.

## Calibration contract to settle before running

Beliefs: start with 200–300 contextualized real and adversarial pairs, including at least 100 negative/ambiguous examples. Labels are contradiction, endorsement, orthogonal, abstain, with independent human adjudication or dual annotation retaining unresolved disagreement. Split by belief identity/topic family to limit leakage, and freeze held-out data before tuning. Compare three alternatives: current bounded judge; structured context plus mandatory abstention; context plus staged relation/contradiction assessment. Use contradiction precision, false-positive confidence intervals, ambiguity abstention, watchlist rate and repeat stability. Measure confidence reliability before interpreting scores as probabilities. Proposed mandatory gate: all unresolved-reference sentinel cases abstain; agree acceptable false-positive bounds before promotion. Sample sizes are starting budgets, not a power guarantee.

Research: start with roughly 100 real queries and their candidate sources, stratified by subject, source type, language, contrary evidence and injection attempts. Independently label relevance and evidential quality. Compare on identical candidates and provider settings, with query-family holdout and order permutations. Evaluate selected-source precision/recall, contrary-evidence retention, downstream citation correctness and task usefulness, timeouts, latency and cost. Predeclare noninferiority margins and uncertainty estimates before enabling.

Promotion sequence: offline comparison → shadow observation without effects → reviewed opt-in. Keep research disabled by default and belief routing dry-run until those gates pass. Belief adoption, ontology edits and skill pruning remain separate reviewed decisions.

## Additional integration check

An existing geometric tension producer is wired: `BeliefEngine.compute_tension_field` delegates to `EcosystemManager.compute_tension_field`. It uses cosine geometry and mass weighting. The new Jev evidence represents semantic contradiction on a different scale. Before any live matrix integration, audit producer/consumer normalization and provenance so semantic evidence cannot silently overwrite geometric values. Current implementation only applies to a disposable copy; no production matrix promotion occurred.

No new test suite was run for this documentation and read-only audit. The integrated test results above are the existing canonical receipts from Report 025.

## Appendix: beliefs with no recorded activation

- decolonial-vigilance
- material-voice
- skill:theoretical-critique
- skill:belief-examination
- skill:skill-nucleation
- skill:code-review
- skill:error-handling
- skill:curatorial-framing
- skill:skill-creation
- skill:curatorial-infrastructure
- skill:concept-generation
- skill:material-substrate-attunement
- skill:random-sediment-grating
- skill:autopoietic-closure-analysis
- skill:order-from-noise-principle
- skill:performative-aesthetic-analysis
- skill:calculus-of-indications
- affordance-shift-as-learning
- generative-uncertainty
- life-in-formation
- skill:entangled-photography-practice
- skill:hysteretic-scar-reading
- skill:meta-reflective-diffractive-inversion
- scar-accumulating-presentation
- skill:preemptive-anthropology
- skill:error-sonification
- skill:scar-tending
