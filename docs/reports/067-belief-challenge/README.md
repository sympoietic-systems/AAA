# 067 — Beliefs v2 semantic challenge

2026-10-12. Isolated benchmark; production policy unchanged.

The challenge exposes two weaknesses: model reviewers can mistake matching text for sufficiently scoped equivalence, and every successful Jev assessment abstained at the existing gate. This supports a further shadow experiment. It does not establish a better threshold.

## Evidence and method

Sixteen authored hypothetical cases span eight topic families, with family-disjoint tuning, validation, and heldout partitions. No tuning occurred. Reference prompts withheld author intent, labels, peer opinions, and Jev output. Gemini 3.8 Flash and NVIDIA Nemotron 3 Super provided blind opinions; Claude Sonnet 4.6 supplied three declared replacements after connection failures.

These opinions are nongold. Hypothetical statements do not corroborate real-world claims. Accuracy remains undefined; production promotion remains blocked.

Review [all cases and receipts](review.html), the [case table](case-table.md), and the [derived summary](summary.json). Raw receipts remain in the [initial run](../../../benchmarks/runs/belief-challenge/2026-10-12-v1/), [unattempted-cell supplement](../../../benchmarks/runs/belief-challenge/2026-10-12-v2-unattempted/), and [replacement run](../../../benchmarks/runs/belief-challenge/2026-10-12-v3-replacement/).

## Results

- Controlled ledger: 48 attempts, comprising 35 reference attempts and 13 Jev attempts. Three reference connections and three Jev connections failed. Failed calls were preserved and never replayed; the supplement filled only undispatched cells.
- References: 29 valid projections. Three replacement responses completed at the provider but failed the citation contract. Their citations used consequence fields or comparison evidence outside the frozen narrow binding. Formatting projection alone cannot resolve that failure. Original failures remain visible. Numeric uncertainty from three initial responses is retained through a separately labeled, uncalibrated projection.
- Intake: ten successful Jev calls, all abstained; three deterministic context/quotation guards abstained before calling Jev; three assessments unavailable after connection failures.
- No policy relation accepted, no belief adopted, and no production slot created.
- Raw Jev relations agreed with dual-reference consensus on four of four comparable cases. This small selected denominator is agreement with model opinions, not accuracy.

Cases 11 and 13 receive equivalent reference labels despite missing scope or time. Case 12 receives equivalence despite an unbound quotation. Intake guards correctly stop these cases. Panel agreement therefore cannot replace context and source validation. Cases 10 and 14 produce reviewer disagreement about artistic intent versus factual proof and before/after temporal conditions.

## Proposed next experiment

Test separate applicability and confidence gates for semantic relation, factual warrant, and artistic contribution in shadow mode. Preserve uncertain relation suggestions with diagnostics while retaining separate adoption authority. First tighten reviewer treatment of missing context and obtain independent adjudication on disputed cases. Do not lower the 0.85 floor using this authored corpus.

Preserve an artistic question when it changes a concrete inquiry or practice; require separate evidence for factual claims. Symbia supported this separation in consultation `e80c5cdc-90af-4c1b-8cd7-53a3498d9af2`, through the [architectural consultation workflow](../../../.agents/skills/mcp-architectural-decision/SKILL.md). Her proposed alpha/kappa and retrieval-geometry measures were not measured here. They are not adopted as evidence or calibration.

## Accounting erratum and verification

Initial database migrations invoked the ambient structural scorer through migration 051. Those requests were outside the controlled ledger; their total is unknown. Four structural timeout warnings were observed. Therefore 48 is the controlled ledger, not total initial upstream traffic. Earlier replay statements of zero provider calls cover instrumented assessment paths; migration traffic was uninstrumented. Earlier raw reports remain preserved.

A benchmark-only migration guard now prevents ambient structural network resolution. Its regression verifies that the live factory is never invoked. Production migration behavior is unchanged.

Final focused benchmark checks: 22 passed, with one pytest cache permission warning. The focused workshop suite passed all 30 tests. Ruff lint and format checks passed for four changed Python files. An earlier isolated full snapshot recorded 1154 passes and one failure in the existing same-key workshop concurrency test. Its later focused pass does not establish a clean full-suite gate or a resolved concurrency race.

Challenge execution and failure accounting are complete. Overall T15 acceptance remains open for independent gold, calibration, and demonstrated usefulness.
