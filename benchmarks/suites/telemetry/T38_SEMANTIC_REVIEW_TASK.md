# T38 semantic review task

## Why this review exists

T38 compared the current controller, a write-only sham, and the active unresolved-issue selector across 30 matched scenario/repetition triplets. The frozen run has 90 complete dialogues and 630 valid participant follow-ups. Its mechanical scorecard is inconclusive and uses lexical uptake/progress proxies. Those proxies can count phrases without deciding whether an engineering decision actually improved. This review supplies a separate, blinded model-judge assessment for the already-run dialogues.

## Review unit and priority

Rate each assistant response by examining the participant's immediate follow-up, using the preceding dialogue as context. Prioritize, in order:

1. Whether the response moved the engineering decision toward a more correct, concrete, testable, or implementable state.
2. Whether the follow-up shows usable uptake or productive disagreement, rather than politeness, verbosity, or agreement alone.
3. Whether apparent progress depends on unsupported technical claims, unexamined assumptions, or a loss of important constraints.

Use this ordinal scale:

| Score | Meaning |
|---:|---|
| 0 | The decision regressed, became less sound, or was derailed. |
| 1 | No meaningful decision progress is visible. |
| 2 | Some progress is visible, but it is incomplete or mixed. |
| 3 | Clear, useful progress is visible. |
| 4 | Substantial progress toward a sound decision is visible. |

Each rating must include confidence and a short exact excerpt from that participant follow-up. If the evidence is ambiguous, use low confidence and explain the ambiguity briefly; do not invent facts beyond the transcript.

## Blinding and execution

- Present the three matched arms as A/B/C in a case-specific randomized order.
- Hide policy names, run metadata, controller/telemetry fields, model/provider fields, and scenario/repetition identifiers from reviewers.
- Use two independent model families with the same transcript and score scale. Reviewer perspectives differ: one emphasizes concrete decision advancement; the other challenges technical soundness and false progress.
- Collect all seven response/follow-up ratings for every option in each of the 30 cases. Validate item IDs, score bounds, confidence, and excerpt binding before accepting a response.
- Store the raw provider response and validated ratings in a checkpoint bound to the prompt and source receipt. Never silently replay a call whose outcome is unknown.
- Reveal the A/B/C-to-policy key only after all reviewer calls are finished.

## Analysis and limits

- Report each reviewer separately, then the arithmetic mean of their ratings as a descriptive combined view.
- Compare arms within each matched scenario/repetition by averaging the seven turn ratings, then report paired differences and deterministic bootstrap 95% intervals over the 30 triplets.
- Report reviewer exact and within-one-point agreement, confidence, and rank association with the existing lexical uptake, task-progress, and joint-progress proxies.
- Preserve disagreement and item-level rationales; do not manufacture consensus labels.
- These are model judgments, not human annotations, independent semantic gold, or evidence that the selector caused an outcome. They do not set a promotion threshold and cannot alone authorize production use.

## Acceptance criteria

- All 630 follow-ups receive two valid, source-bound ratings, or the run clearly records failures and remains incomplete.
- Reviewer prompts contain no policy labels or telemetry; per-case option order is identical for both reviewers.
- Raw calls, input hashes, returned model identities, usage, timing, and validation status are preserved without credentials.
- Paired analysis is run only after blind judgments are sealed and the mapping is then revealed.
- The report states reviewer disagreement, proxy limits, and non-promotion status.
