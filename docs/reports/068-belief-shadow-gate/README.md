# 068 — Belief assessment dimension shadow comparison

2026-10-12. Frozen offline projection. The production assessment gate and belief records were not changed.

The aggregate gate accepted none of the 16 completed assessments. A separate projection of each recorded dimension retained 12 observations at the existing 0.85 floor, across seven authored hypothetical cases. It retained no observations from 19 non-challenge cases: six saved contrast assessments and 13 recorded conversation nominations. Three challenge calls were unavailable; the 13 nominations and three challenge cases stopped at source/context checks before assessment. The evidence shows that aggregate abstention can obscure individually confident labels in this challenge; it cannot establish that those labels are correct or useful.

## Inputs and method

The run joined three existing frozen inputs by their local case order and receipt references:

- Six saved Jev contrast assessments from the dimension-diagnostics replay. All dimensions remained below 0.85.
- Thirteen recorded conversation nominations from the sealed intake replay. None reached Jev because required context or quotation fields were missing.
- Sixteen authored hypothetical challenge cases. Ten had successful Jev answers, three had prior connection failures, and three were blocked by context guards.

The projection requires candidate scope, time, and an exact source-bound quote. Relation observations also require a comparison with matching scope and time. Each dimension is compared independently to the unchanged 0.85 floor. Missing, low-confidence, noncommittal, or context-invalid dimensions remain unresolved. “Retained” means only that a recorded dimension passed this shadow rule; it confers no truth, usefulness, factual support, or adoption authority.

No provider calls were made during this run. It wrote no production records and has no join to candidate or adopted-belief storage. Symbia’s consultation `32f483d9-8ced-4707-8e3d-61c7ffab6173` emphasized keeping evaluation receipts structurally separate from warrant and adoption pathways; any later bridge requires a separate human reckoning.

## Findings

The 12 retained observations all came from the hypothetical challenge:

| Dimension | Retained | Meaning in these receipts |
|---|---:|---|
| Factual grounding | 5 | “Unsupported” only; not evidence about the real world |
| Semantic relation | 3 | Two contradiction labels and one extension label, under matched stated scope/time |
| Tension | 3 | “Absent” labels; no claim that a question is useful |
| Artistic grounding | 1 | “Unsupported” label; no judgment of artistic merit |
| Consequence | 0 | No response cleared the floor |

The six saved contrast assessments produced no above-floor dimension. In particular, their artistic-question case remained unresolved. The recorded conversation nominations produced no assessment and no shadow observation. The context guards prevented those incomplete proposals from entering semantic comparison.

The comparison therefore demonstrates a review-interface distinction: an aggregate abstention can coexist with a few high-confidence dimension labels. It does not validate a new admission rule. The high-confidence challenge labels are provisional model outputs on authored hypotheticals. No independent human labels or outcome data establish their correctness or value.

## Follow-up

Keep the per-dimension view in a benchmark-only namespace. A later usefulness study needs human adjudication and situated outcomes, especially for the artistic-question case. Any production integration would need its own design and review; this run supplies no authority to alter belief admission or adoption.

## Reproducibility

The sealed derived output, source hashes, and per-case projection are in [the benchmark run](../../../benchmarks/runs/belief-shadow-gate/2026-10-12-v7/). Its inputs are the [belief challenge supplement](../../../benchmarks/runs/belief-challenge/2026-10-12-v2-unattempted/), [dimension diagnostics replay](../../../benchmarks/runs/belief-dimension-diagnostics/2026-10-12/replayed/), and [sealed recorded intake](../../../benchmarks/runs/belief-intake-replay/2026-10-11-v4-sealed-recorded/).

Six shadow-gate tests and six challenge tests passed. Ruff lint and format checks passed. No full backend suite was run for this benchmark-only change.
