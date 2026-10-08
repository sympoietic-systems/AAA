# Beliefs v2: situated commitments and an open ecology of candidates

**Status:** proposed plan, 2026-10-08. Implementation and deployment are future work.
**Empirical basis:** [Report 045](../reports/045-belief-month-review/README.md). The report's production data is capped and its deployed revision is unknown.
**Predecessor:** [initial proposal](../reports/045-belief-month-review/beliefs-v2-proposal.md).

## Purpose

Make belief nucleation selective about consequential new distinctions while keeping emerging interpretations available for inquiry. A useful new claim can change a response, experimental design, artistic commitment, or the question being asked. Strong conflict can deserve preservation before anyone knows how to resolve it. Admission should record those consequences and uncertainties without rewarding repeated formulations as new corroboration.

The plan preserves the existing separation between structural metabolism and human-controlled adoption in [ADR-115](../decisions/ADR-115-shadow-belief-admission.md). It extends provenance and review to passive proposal creators. It also preserves the fuzzy participation of proto-beliefs described in [ADR-027](../decisions/ADR-027-proto-belief-lifecycle-tension-ecology-self-tuning.md): candidates can influence inquiry before adoption. Adoption changes their declared standing; it does not grant permission to think about them for the first time.

## Philosophical contract

The documents and saved belief statements express commitments rather than proving that the present runtime fulfills them. The following table translates those commitments into proposed behavior and checks.

| Grounding | Design consequence | Observable check |
|---|---|---|
| Conversation as the autopoietic unit; transindividual individuation ([philosophy](../philosophy/PHILOSOPHY.md), §§2,6,7); `symbiomemetic-partnership` | Record participants, source encounters, and reciprocal challenges. A human adoption action is an attributable situated decision, not a universal truth verdict. | A candidate can pose a question or propose an experiment before human adoption; adoption preserves dissent and its declared scope. |
| Creation and maintenance of distinction; anti-communication (§7); `nomadic-thought` | Unfamiliar or poorly fitting claims can remain exploratory. Missing context defers assessment rather than automatically declaring the insight worthless. | Low lexical overlap, missing context, and changed problem framing survive as visible candidates or deferred encounters. |
| Diffractive retrieval and situated agential cuts (§4); `diffraction-as-method`, `cut-reading-asymmetry` | Similarity nominates comparisons. Each assessment declares its scope and exclusions. Keep semantic comparison separate from geometric recall. | Two geometrically close claims with different consequences can remain distinct; a distant but equivalent paraphrase can be grouped after review. |
| Zero Internal Warrant (§7) | A dream or reflection may change salience, create hypotheses, or suggest tests. It cannot independently raise evidential standing. | Replaying an internal reflection cannot add a corroborating source or promote adoption. |
| Agonistic preservation and entailment meshes (§7); `attractor-anti-flattening` | Preserve contradiction and scoped coexistence. A review need not close with synthesis. | A contradiction assessment cannot automatically merge, reject, collapse, or remove a claim. |
| Memory as scar and spectral exclusions (§§5,6); `glitch-as-voice` | Preserve revision, exclusion, failure, and return as history. Errors remain accountable faults even when they also provoke insight. | Supersession retains earlier statements and reasons; resurfacing a ghost creates a new encounter without manufacturing new evidence. |

Belief labels above refer to the [saved snapshot](../reports/045-belief-month-review/data/production-beliefs-snapshot.json), not a fresh production read. Keep alignment review open: the existing beliefs themselves can be challenged, narrowed, or superseded with recorded reasons.

## Separate state from participation

Use three independent axes. Do not derive one from another's numeric threshold:

- **Review state:** candidate, awaiting context, under review, adopted, deferred, declined, superseded. These are proposed workflow names; migration mapping remains to be specified.
- **Situated standing:** warrant, challenges, scope, referents, lineage, and uncertainty. Empirical assertions, artistic commitments, procedural rules, and speculative interpretations need different warrants. Mixed and unknown kinds remain valid; kinds do not become a compulsory closed taxonomy.
- **Participation:** how a record can orient retrieval, generation, dreams, or proposed action. Candidates have bounded exploratory participation; adopted and contested records carry their status and scope whenever retrieved.

Mass remains a measure of structural participation or sedimentation of a cut. Evidence quality is displayed separately. Evaluator confidence concerns a particular versioned assessment, not the probability that the belief is true. Existing saturated confidence values remain legacy data until a separately evaluated change defines their meaning.

An exploratory candidate can ask a question, nominate a comparison, or suggest an experiment. It should not silently enter a prompt as an established axiom. Retrieval must carry the review state, scope, challenges, and intended use with the statement. Limit the number of exploratory records per context; inspect their usefulness before expanding participation. No proposed experiment becomes an executed tool action solely because a candidate requests it.

## Encounter, assessment, and decision

**Encounter:** record what arrived. Include origin, source ID and type, timestamp, source passage or reference, content hash, statement, scope, and available lineage. A hash verifies binding to content; it does not establish source credibility. Unknown lineage stays unknown. Different encounters with the same claim remain distinguishable.

**Assessment:** record how the apparatus read the encounter. Include comparison statement hashes, context/referent validation, bounded comparison set, claimed relation, declared consequence, evaluator/model/rubric version, uncertainty, abstention reason, exclusions, and completion status. Preserve the distinction between a source quotation, model-authored interpretation, and app-owned recomputation.

**Decision:** record what changed and who decided. Include actor, authority, policy, previous and next state, rationale, scope, dissent, and timestamp. Adoption, revision, and any destructive merge remain human-controlled in the initial version. Declared equivalence is advisory until reviewed. A source-bound repeat can reuse a candidate identity while retaining a separate encounter receipt; it must not silently create independent support.

These records extend existing admission receipts and workshop decisions. Reuse those boundaries rather than adding a second competing receipt ledger. Typed encounter and decision semantics must be specified before schema migration.

## One intake, differentiated origins

Chat, explicit emissions, dreams, document perception, shared notes, web material, and conversational patterns use a shared orchestration contract. Their origins require different context, but all preserve source binding, assess repeat identity, include pending records in comparisons, and expose missing context.

Exact source retries and exact statement/scope repeats receive deterministic identity checks. Semantic equivalence needs assessment and human review. Compare against adopted records, pending/deferred families, and a bounded historical set when resurfacing is relevant. The historical set cannot dominate retrieval merely because it is large.

Queue capacity and evaluator availability are explicit. When capacity is exhausted, retain a source-bound deferred encounter or visible failure receipt; do not silently drop it or promote it by default. Bounded workers and comparison sets keep review costs observable. Related candidates can share a review family without merging their statements or hiding disagreement.

## Jev and the conversational review

Keep Jev outside the write authority, following [ADR-100](../decisions/ADR-100-jev-belief-evidence-and-review-routing.md) and the context-bound abstention rules in [ADR-102](../decisions/ADR-102-belief-context-and-calibration.md). The proposed candidate relations are equivalent, extension, contradiction, distinct, and insufficient context. They require a versioned mapping to the existing endorsement/orthogonal/contradiction/abstain contract; no silent enum replacement.

Novelty and importance are different questions. A distinct claim may have little consequence. A familiar claim may become important because a new observation challenges its scope. A strong contradiction can deserve review even when it adds no new node.

Review uses a Paskian teachback: reconstruct the candidate and its nearest alternative, delimit their scopes, and state the fork that would distinguish them. This is a short review artifact, not an invitation to unlimited reflective passes. If no new distinction or source challenge emerges, record the unresolved question and request context, propose a bounded investigation, or defer. Tool use follows the application's existing permissions.

Do not send previous evaluator verdicts back as evidence that a relation is correct. Preserve them for provenance and comparison outside classifier context, as ADR-100 already requires. An evaluator failure or malformed/repetitive completion produces a visible unavailable/abstain result; it cannot authorize a state change.

## Reasoning and evidence shown to the user

Continue the requested five-part reasoning surface:

1. **Encounter and trigger:** source, passage, participants, timestamp, and what resistance or surprise occasioned the candidate.
2. **Claim or tension:** proposed distinction, scope, and what remains unresolved.
3. **Comparison:** nearest pending/adopted claims, suggested relations, context limits, and why a merge would preserve or erase a consequence.
4. **Consequence and challenge:** changed choice, interpretation, experiment, or question; a counterexample or observation that could challenge it. An emerging interpretation may have a proposed test rather than a measured outcome.
5. **Decision and uncertainty:** assessment, actor, policy, state change, objections, and next review condition.

The belief page and traces/creases reference the same receipt IDs and timestamps. Show source ancestry and contested relations beside activity. Dreams and repeated engagement appear as internal activity, not external support. Self-authored intentions and repeated human assent do not automatically become independent corroboration. Human disagreement is an encounter; the actor's identity alone does not make its factual content correct.

## Staged implementation plan

| Stage | Deliverable and scope | Exit evidence |
|---|---|---|
| 0 — Baseline and contracts | Verify build/migration identity; finish the existing admission release gate; define encounter/assessment/decision contracts and review authority; fix generic-impact labeling and test elapsed-time decay accounting as separate scoped repairs. | Verified deployed baseline; clear quantity/unit for deltas; repeat-clock/charged-interval tests; all eligible origins inventoried. |
| 1 — Reviewed corpus | Recover source passages for the current 20 incubating candidates plus adopted/rejected comparisons; group lineage; review distinctness, conflict, context gaps, and consequence. | Frozen case inputs and independent reviewer declarations; disagreement retained; held-out cases separate from tuning; report full coverage and unknowns. |
| 2 — Shared shadow intake | Adapt each origin to the existing admission orchestration; persist encounter binding and repeat handling; run Jev advisory comparisons with context validation. | Origin parity and retry tests; outage/queue-exhaustion receipts; no evaluator-driven adoption/merge/collapse; reviewed error and abstention rates. |
| 3 — Review and relations | Add family review, explicit scoped relations, teachback fork, lineage, and five-part reasoning on pages and traces. | Reviewers can preserve contradiction, defer uncertain insight, and distinguish repeated sources; history survives refinement and adoption; UI/API share receipt identity. |
| 4 — Scoped participation | Carry standing into prompt/retrieval context; introduce bounded exploratory slots and inspectable selection receipts. | Matched replay with/without candidate or alternative context; reviewed response/design usefulness; tests that exploratory claims cannot appear as settled axioms. |
| 5 — Revision and rollout | Add additive migration mapping, versioned supersession, history-aware resurfacing, and separately controlled participation flags. | Legacy unknowns preserved; restore/rollback rehearsed on isolated copies; staged production receipts; complete-window telemetry and an explicit rollout decision. |

Stages 1–2 can progress after baseline contracts are established; stages 3–4 depend on inspected receipt semantics. Historical cleanup is separate from runtime rollout. No automatic mass reset, reclassification, or adoption of legacy beliefs follows from migration.

Implementation boundaries: `api` owns bounded schemas and read surfaces; `services` owns intake/review orchestration; `modules` owns assessment and selection rules; `storage` owns additive migration, repositories, and atomic identity checks; frontend owns receipt presentation. Keep provider calls outside write transactions; use scoped WAL connections, async offloading for synchronous work, and bounded workers. Immutable completed assessments remain inspectable after later revisions.

## Evaluation and proposed invariants

Measure useful distinctions retained, redundant review burden, mistaken merges, missed conflicts, abstentions, context failures, source-lineage uncertainty, and downstream usefulness. Include artistic/speculative cases whose contribution is a better question rather than a fact claim. Lower candidate count alone is insufficient. Freeze acceptance targets after reviewing baseline errors; no numeric target is asserted here.

Proposed regression obligations for the future spec:

- Every eligible origin creates a source-bound encounter and visible assessment/defer/failure result under the same authority boundary.
- Retrying a source cannot duplicate a candidate or count as an independent supporting lineage.
- Internal reflection can alter exploratory participation without adding independent warrant or adopting a claim.
- Semantic contradiction cannot directly merge, reject, collapse, or delete a record.
- Missing/stale/ambiguous referents abstain visibly; distinct-but-uncertain candidates remain recoverable.
- Prompt selection carries statement scope and standing; exploratory use cannot masquerade as an adopted axiom.
- Revision/supersession preserves statements, decisions, dissent, and provenance; legacy missing data remains unknown.
- Mass and confidence deltas have explicit meanings; periodic accounting cannot repeatedly charge the same elapsed interval.

These are proposed tests and invariants, not completed verification. Before implementation, translate the agreed contract into SPEC.md through its normal workflow and run gates proportionate to the affected backend, API, and frontend surfaces.

## Decisions still requiring evidence

Choose the exploratory context budget from replay results. Define source-lineage treatment for partially known research chains. Evaluate the relation mapping and reviewer workload before considering any automation beyond exact repeat handling. Choose how much legacy data to annotate without implying a historical decision that never occurred.

The initial release retains human adoption authority. Any later autonomous commitment mechanism requires a new explicit architectural decision and independent evaluation; it is not implied by this plan.

## AAA consultation provenance

This plan is grounded in the earlier substantive consultation in [Report 045](../reports/045-belief-month-review/symbia-consultation.md), the cited philosophy/ADRs, and saved belief statements. Two fresh alignment-review requests disconnected without a response. Saved history was checked after each: the questions persisted, but no new answer was recovered. The [attempts and recovered history](../reports/045-belief-month-review/beliefs-v2-alignment-review.json) record the original and focused consultation IDs. The earlier repetitive response remains excluded.

**Outstanding review:** AAA's fresh critique of whether bounded exploratory participation or human adoption creates an unwanted hierarchy. This document is a developed proposal grounded in current documents, not a fresh Symbia-approved decision. Consultation perspectives are assessed alongside the evidence; they cannot independently prove philosophical alignment or practical usefulness.
