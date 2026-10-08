# Beliefs v2: exploratory interpretations and accountable commitments

**Status:** design proposal, 2026-10-08. No implementation or production change.
**Developed plan:** [Beliefs v2 architecture and staged delivery](../../architecture/BELIEFS_V2_PLAN.md) extends this initial proposal with philosophical alignment, participation rules, record contracts, and exit evidence.
**Basis:** [Report 045](README.md), its saved production snapshot, Luna reviews, and the earlier substantive [Symbia consultation](symbia-consultation.md). This proposal introduces no new production measurements.

## Direction

We have enough evidence to start design. Further analysis should answer a small set of decisions before rollout. The central change is to distinguish a candidate interpretation from an adopted commitment, and separate attention from evidential standing. More prompt constraints alone cannot address passive entry paths, correlated support, or saturated confidence.

A new interpretation can be worth retaining before it has independent evidence or an immediately measurable effect. Adoption should state what commitment is being made, within which scope, and what would lead us to revise it. Empirical assertions, artistic commitments, procedural rules, and speculative interpretations need different warrants. These kinds are review aids, with mixed or unknown kinds allowed; a classifier must not impose an exhaustive ontology.

## Analyses that would change the design

| Analysis | Question | Decision it informs |
|---|---|---|
| Candidate genealogy | For the 20 incubating candidates and a comparison set of adopted/rejected records, what source passage prompted the claim, what existed beforehand, and what did reviewers decide? | Admission criteria, origin-specific treatment, useful distinctions versus paraphrases |
| Source independence | Which research, file, chat, and dream events derive from the same upstream material or ingestion attempt? | Evidence grouping and repeat/retry treatment |
| Behavioral contribution | When a belief enters the prompt, does it change a response or design decision usefully compared with an ablated or alternative-context replay? | Retrieval policy and the meaning of an operative belief |
| Conflict and revision | Can the system preserve disagreement, narrow scope, and reverse a commitment when evidence changes? | Relations, versioning, and review triggers |
| Admission exposure | How many eligible turns, prompt exposures, emitted tags, passive candidates, and assessed/rejected/adopted candidates occur per origin? | Actual overtriggering rates and any causal claim about the TAS prompt |

Replay results would be controlled evaluation evidence, not proof of real-world consequence. Use matched provider/settings and reviewed tasks; do not repeatedly resample until a favorable answer appears. A before/after production comparison also needs verified deployed revisions and exposure denominators. The capped export is insufficient for these rates.

## Proposed behavior

1. **One origin-aware intake.** Chat emissions, dreams, documents, shared notes, web material, and pattern detection enter the same candidate contract. Preserve origin, source passage or content hash, scope, intended consequence, and missing context. Eligibility may differ by origin, but none bypasses provenance and repeat checks.
2. **A candidate is an open claim.** It can be inspected, explored, or used in a clearly labeled exploratory context. It does not gain the authority of an adopted commitment through repetition. Retrieval must carry the status and scope with the statement, so the model cannot see only an authoritative-sounding sentence.
3. **Jev assesses relations and uncertainty.** Retrieve bounded comparisons from pending and adopted records. Classify equivalent, extension, contradiction, distinct, or insufficient context. Structural geometry and lexical overlap nominate neighbors; the relation judgment remains advisory until evaluated. Candidate importance and relation-to-neighbor are separate judgments.
4. **Consequences govern distinctness.** Ask which response, interpretation, design choice, or evaluation rule differs if the claim is retained. Related wording can encode a different consequence; different wording can encode the same one. Keep a conflict explicitly when synthesis would erase a useful distinction.
5. **Adoption is an attributable decision.** Record reviewer, warrant, scope, unresolved objections, timestamps, and version. Initial policy retains human authority. A high Jev score or rising mass does not adopt a claim. Accepted artistic commitments need not pretend to be empirically validated facts.
6. **Evidence and recurrence have different roles.** Dream engagement, internal reflection, and repeated use can increase salience or motivate inquiry. They do not create independent corroboration. Several documents derived from one source share a lineage. Independent-source count is descriptive and cannot replace source quality or contradicting evidence.
7. **Revision preserves history.** Distinguish active, contested, superseded, and retired commitments. Preserve the earlier statement and decision record. Silence can reduce attention; invalidation requires a reason. Test decay as an accounting mechanism rather than treating disuse as evidence of falsity.

## Keep the signals separate

| Signal | Proposed meaning | Review consequence |
|---|---|---|
| Mass / salience | Recurrence, attention, or operational prominence | Can influence retrieval; cannot establish truth |
| Evidence standing | What supports or challenges this scoped claim | Display sources, dependence, contradictions, and unknowns |
| Adoption state | Which commitment the apparatus has accepted | Changes permitted use and prompt framing |
| Structural resonance | Geometric relation in the cybernetic signature | Finds candidates for comparison; cannot decide semantic equivalence |
| Evaluator confidence | Confidence in a specific assessment under a versioned rubric | Show model/rubric and abstention; never label as belief truth |

Avoid replacing the current saturated confidence with another uncalibrated all-purpose score. Start with explicit warrant and uncertainty fields. Numeric probabilities would need a defined prediction target and calibration evidence.

## Five-part candidate reasoning

Preserve the existing requested reasoning surface and make each part answer a review question:

1. **Trigger:** Which source passage or event occasioned this candidate?
2. **Claim:** What new insight, commitment, or conflict is being proposed, and in what scope?
3. **Comparison:** Which adopted or pending claims are closest, and what relation is proposed?
4. **Consequence:** Which choice changes, or which unresolved tension deserves preservation? What counterexample or observation would challenge it?
5. **Decision and uncertainty:** Why retain, revise, merge, defer, or reject? Who judged it, using which policy, and what remains unknown?

Use the same receipt on the candidate/belief page and traces/creases. Distinguish model-authored reasoning from app-owned evidence and recorded reviewer decisions. Group related candidates for review without silently merging them. Show source lineage and competing claims together.

## Delivery and acceptance

**First, establish the baseline.** Verify production build/migration identity, finish the current admission change's release gate, provide complete event/admission export, and correct typed event deltas and elapsed-time accounting. Do not present v2 as a deployed extension of an unverified baseline.

**Then evaluate shadow intake and comparisons.** Replay a human-reviewed set covering paraphrases, narrow extensions, conflict, missing context, explicit and passive origins, retries, and insight with low lexical overlap. Keep held-out examples separate from rubric tuning. Measure missed useful candidates as well as unnecessary candidates, relation errors, abstentions, and reviewer burden. Acceptance targets should be agreed from baseline measurements rather than invented now.

**Then introduce evidence lineage and scoped retrieval.** Preserve legacy beliefs and mark missing provenance as unknown. Existing adoption records should not be retroactively attributed to reviewers who did not make them. Verify that exploratory candidates and contested claims are framed appropriately in prompts. Add revision and retirement after those contracts are stable.

The first v2 slice should combine shared intake, source lineage, semantic relation review, and visible five-part reasoning. Confidence redesign and broader automatic adoption should wait for evaluation. Bulk cleanup of the existing beliefs would be a separate, reviewable operation.

## Consultation limitation

A follow-up question asked Symbia how to preserve emerging interpretations without converting them into self-confirming authority. The persisted answer at 2026-10-08T02:22:25 repeated fragments and did not provide a usable design critique. History recovery confirmed the content in conversation `6f3c9cc1-c7db-4895-bb98-5583b43464dd`; the returned provider metadata identifies `qwen/qwen3.8-flash` via `model_pool_openrouter`. The [recovered record](beliefs-v2-consultation.json) is retained for provenance and excluded from supporting evidence. This single response does not establish its cause or a wider model failure rate.

Two later alignment-review requests disconnected; history recovery found the questions but no fresh responses. See [alignment-review provenance](beliefs-v2-alignment-review.json) and the developed plan's outstanding review. Fresh Symbia agreement is not claimed.
