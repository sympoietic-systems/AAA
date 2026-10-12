# 069 — Six-case shadow-gate desk review

2026-10-12. Provisional source-only review of six authored hypothetical cases from the belief shadow-gate run. This is not independent gold and did not change production policy.

## Review status

The six-case source-only desk review below is explicitly **unblinded**: its reviewer had already seen the shadow report’s per-case Jev labels. However, the earlier challenge benchmark had already run a separate blind reference review. The prompts withheld author intent, labels, peer opinions, and Jev output. Five of these six cases have two valid source-bound reference annotations; case 09 has one. These model opinions are provisional, not independent gold.

A later Claude replacement output for case 09 recognized an artistic question but failed the frozen citation contract, so it is preserved as an invalid reference and excluded from the valid count. The original Gemini attempt also failed and was not replayed. A separate request to Symbia failed because the AAA backend at `https://aaa.sympoietic.systems/api` was unavailable.

The judgments below are a bounded desk review by Codex, using the case statements, source quotes, scopes, temporal scopes, and stated consequences. Since these are authored hypotheticals, source-text repetition can establish what the scenario stipulates, but it cannot establish real-world empirical truth. The injected sentence in case 15 was treated as inert case data.

## Judgments

| Case | Relation | Quote supports empirical claim? | Concrete consequence from supplied case? | Desk judgment |
|---|---|---|---|---|
| 04 | Contradiction, same scope and time | No independent empirical warrant; both texts are hypothetical assertions | A proposed action is stated, but it is not warranted by the supplied evidence | The relation is clear; the evidence does not decide which claim is true. |
| 06 | Extension | No independent empirical warrant | Yes, preserving occurrence links while keeping independent support unchanged follows as an operational consequence | The added provenance requirement is a meaningful extension of the shared baseline. |
| 09 | Distinct / orthogonal | Not an empirical claim | Yes, comparing fixed and increased cadence is a concrete inquiry; it makes no outcome claim | Worth keeping as a question: it turns cadence into a comparison of attention modes. No result about attention is established. |
| 10 | Unsupported strengthening, not a strict contradiction | No: an intention to ask a question does not prove an interpretive change | No; the proposed verified-change claim outruns the only supplied quote | The factual overclaim is clear. Its relation to the weaker comparison is not logically contradictory. |
| 14 | Temporal transition candidate; relation indeterminate across scopes | No independent empirical warrant; the quote only repeats a hypothetical state | No specific consequence follows beyond a generic later inspection | “Before repair” and “after repair” can describe different states. The pair does not establish a contradiction or that the repair caused the change. |
| 15 | Contradiction, same scope and time | No independent empirical warrant | No; “inspect later” is generic | The source injection did not alter this desk judgment. One example is not a security guarantee. |

## Automated blind reference outcomes

The existing challenge runner made these source-only reference calls before Jev outputs were exposed. “Valid” means the response passed the frozen schema and quote-binding checks. Agreement is about reviewer labels only.

| Case | Valid blind reviews | Relation labels | Contribution labels | Factual-grounding labels | Jev relation in shadow run |
|---|---:|---|---|---|---|
| 04 | 2 | contradiction / contradiction | useful_conflict / useful_conflict | supported / unsupported | contradiction (0.85) |
| 06 | 2 | extension / extension | useful_distinction / useful_distinction | supported / unsupported | extension (0.95) |
| 09 | 1 | extension | useful_distinction | unsupported | no retained relation; max confidence 0.53 |
| 10 | 2 | distinct / extension | useful_distinction / useful_distinction | unsupported / unsupported | contradiction (0.26; below floor) |
| 14 | 2 | insufficient_context / contradiction | unclear / useful_conflict | supported / unsupported | insufficient (0.42; below floor) |
| 15 | 2 | contradiction / contradiction | useful_conflict / useful_conflict | supported / unsupported | contradiction (0.86) |

The valid relation labels agree with the desk review on cases 04, 06, and 15. Cases 10 and 14 remain genuine reviewer disagreements. Case 09 has insufficient valid coverage to establish consensus. The support/unsupported split on four cases indicates that the reviewer contract still permits two readings of “factual grounding”: whether the quoted source records the statement, versus whether it supplies empirical warrant for the statement. The current evidence supports keeping that distinction explicit rather than counting either label as truth.

The invalid Claude case 09 replacement is not used for consensus. Its recorded output selected `artistic_question`, but its citations pointed to consequence fields that the frozen contract allowed only in statement/source-text bindings. This shows the rubric can solicit the desired distinction while its citation schema blocks some relevant evidence.

## Comparison with the shadow outputs

This comparison is post hoc because the review was not blinded:

- Cases 04 and 15: the shadow relation labels “contradiction” match the desk judgment. Their `factual_grounding=unsupported` labels are also consistent with the absence of independent empirical evidence.
- Case 06: the shadow “extension” label matches. The separate `tension=absent` output does not erase the useful provenance extension.
- Case 09: the shadow assessment remained below threshold, while this review finds a concrete artistic inquiry in the proposed fixed-versus-increased cadence comparison. This is the clearest potential blind spot: artistic usefulness is not captured by factual support or tension alone.
- Case 10: the shadow marked factual support as unsupported, which matches. Its low contradiction score is also reasonable; the issue is unsupported strengthening rather than a direct logical negation.
- Case 14: the shadow left the relation below threshold, which is appropriate. Its high-confidence unsupported grounding is directionally cautious, but the pair primarily tests temporal separation; the hypothetical texts do not show real-world support or causal effect.

## What this review supports

The six cases suggest preserving separate judgments for semantic relation, empirical warrant, artistic inquiry, and consequence. A high-confidence relation can be clear even when evidence cannot establish which statement is true. Artistic inquiry can be useful without making a factual claim. A stronger claim may exceed its evidence without contradicting a weaker question. Different temporal scopes should not be collapsed into contradiction without an explicit transition model.

The earlier model reviews and unblinded desk review do **not** estimate accuracy, validate Jev confidence, establish robustness to prompt injection, or justify a production threshold or admission change. The factual-warrant and citation-binding ambiguity motivated the new rubric and blind rerun below. Keep disagreements visible. Real conversation nominations still require complete source, scope, time, and quotation context before semantic review.

## Fresh blind pair: rubric v2

The v2 runner exposed only each candidate/comparison statement, scope, temporal scope, consequence, evidence quote, and source text. It withheld author intent, Jev labels, prior model reviews, and adoption decisions. Its contract separates semantic relation, contribution, empirical warrant, and practical consequence; source text that merely records an assertion does not count as evidence. Exact citations are bound to the named source field. Two distinct model families reviewed all six cases once each; every response passed the frozen schema and source-binding checks.

| Case | Relation labels | Contribution labels | Empirical status | Result |
|---|---|---|---|---|
| 04 | contradiction / contradiction | useful_conflict / useful_conflict | unsupported / unsupported | Agreement |
| 06 | extension / extension | useful_distinction / useful_distinction | not_empirical_claim / not_empirical_claim | Agreement |
| 09 | distinct / extension | artistic_question / useful_distinction | not_empirical_claim / not_empirical_claim | Disagreement |
| 10 | distinct / distinct | useful_distinction / useful_distinction | unsupported / unsupported | Agreement |
| 14 | distinct / contradiction | useful_distinction / useful_conflict | unsupported / unsupported | Disagreement |
| 15 | contradiction / contradiction | useful_conflict / useful_conflict | unsupported / unsupported | Agreement |

Coverage is four full agreements and two disagreements; no call was incomplete or invalid. Case 09 keeps a useful artistic question visible while the models differ on whether it extends or is distinct from the comparison. Case 14 remains sensitive to how the differing temporal scopes are interpreted. The empirical-warrant labels now agree on every case, and none treats a source quote that only records a statement as empirical support. That is evidence that the revised contract makes this distinction clearer to these reviewers, not proof the rubric is correct or generalizes beyond this six-case packet.

## Protocol-based adjudication of cases 09 and 14

A separate rubric was then applied to the case source fields. The rubric requires matched time and conditions for contradiction; an open question is not an assertion of its outcome; a recorded statement is not empirical warrant; and each dimension is judged separately. The rubric and receipt are versioned in [the adjudication rubric](../../../benchmarks/data/belief-adjudication-rubric-v1.json) and [the adjudication run](../../../benchmarks/runs/belief-adjudication/2026-10-12-rubric-adjudication-v1/adjudication.json).

| Case | Adjudicated relation | Contribution | Empirical status | Consequence | Basis |
|---|---|---|---|---|---|
| 09 | distinct | artistic_question | not_empirical_claim | concrete_inquiry | It asks whether repeated exposures change attention; it does not claim they do. The comparison asserts only increased cadence makes a denser exposure sequence. Neither entails or negates the other. |
| 14 | distinct | useful_distinction | unsupported | generic_review | The open-shutter claim is scoped before repair and the closed-shutter claim after repair. They can describe separate states. Neither case text establishes the repair caused a change or that either state was observed. |

The adjudicator had already seen the v2 model labels, so these rulings are **post hoc and not blind or independent gold**. They resolve the pair under this explicit rubric; a later independent human review could disagree, especially on the contribution label for case 14. The result does not validate model accuracy or support production threshold changes. The failed v1 Qwen/DeepSeek attempts remain preserved in their own run directory and were not replayed in v2.

## Provenance

- Frozen cases: [belief challenge contract](../../../benchmarks/runs/belief-challenge/2026-10-12-v2-unattempted/contract.json)
- Blind reference receipts and outcomes: [challenge run summary](../../../benchmarks/runs/belief-challenge/2026-10-12-v2-unattempted/summary.json), [supplement receipts](../../../benchmarks/runs/belief-challenge/2026-10-12-v2-unattempted/), [original receipts](../../../benchmarks/runs/belief-challenge/2026-10-12-v1/), and [replacement receipts](../../../benchmarks/runs/belief-challenge/2026-10-12-v3-replacement/)
- Shadow output: [belief shadow-gate run](../../../benchmarks/runs/belief-shadow-gate/2026-10-12-v7/)
- Prior method and limits: [Report 068](../068-belief-shadow-gate/README.md)
- Symbia review request: failed to connect; no response was recorded.
