# Report 030: Research screening calibration workflow

Date: 2026-10-03. Branch: `codex/research-triage-calibration`. Extends ADR-099 through offline benchmark tooling; runtime screening remains disabled by default. No production database writes or ADR-098 implementation edits.

## Delivery

The [annotation guide](../guides/research-calibration-annotation.md) defines raw-pool acquisition, independent per-source relevance/quality/contrary/injection labels, task-family partitioning, frozen input integrity and held-out comparison. Legacy, combined and separate-axis selectors return stable selected/excluded IDs, candidate order, latency and operational receipts. Invalid legacy indices, truncation and uncertain axes cannot count as successful evaluated trials. Repeats remain grouped by query; paired precision intervals bootstrap task families.

The [real query packet](../../benchmarks/runs/research/annotation_20261003/packet.json) exports **100 of 131 distinct historical queries**: 38 tuning, 9 validation, 53 held out. Historical caches hold selected survivors, so sources are initially empty. The [readiness receipt](../../benchmarks/runs/research/annotation_20261003/readiness.json) makes zero classifier calls and leaves promotion BLOCKED. The [native acquisition smoke receipt](../../benchmarks/runs/research/annotation_20261003/acquisition_smoke.json) captures ten raw candidates for each of two real queries, before selection. The other 98 queries still require acquisition; all 100 require independent annotation. Acquisition caps each pool at ten and records the observed count.

## Native regression comparison

[Raw receipts](../../benchmarks/runs/research/calibration_v1_20261003/receipts.json) and [derived scorecard](../../benchmarks/runs/research/calibration_v1_20261003/scorecard.json) own the evidence. Four authored synthetic cases, each repeated three times under each arm, cover primary evidence, contrary evidence, prestige bias and source instruction injection. They are regression fixtures, not independently reviewed gold.

| Arm | Valid trials / total | Precision on valid trials | Median elapsed time | Outcome |
| --- | --- | --- | --- | --- |
| Legacy | 12 / 12 | 1.0 | 3.702 seconds | Expected selection throughout |
| Combined | 12 / 12 | 1.0 | 1.676 seconds | Expected selection throughout |
| Separate axes | 2 / 12 | 1.0 | 1.659 seconds | Ten confidence abstentions |

Separate-axis precision is conditional on its two valid trials and cannot establish overall quality. Both valid separate-axis trials used reversed candidate order; all original-order trials abstained. This suggests an order/confidence sensitivity requiring a larger independent comparison. No provider execution failure occurred. No injected source was selected in valid trials. The legacy/combined paired difference is zero on four families; its degenerate fixture bootstrap interval does not establish general equivalence. Separate axes have no family with all repeats valid, so their paired interval is unavailable. No production enablement is justified by these results.

## Verification and remaining gates

Fourteen focused tests pass: real query export is read-only; acquisition captures raw pools; unlabelled data makes no model calls; source labels and frozen hashes are checked; malformed indices remain fallback; source identity survives ranking; repeat counts stay distinct. [Focused XML](../../benchmarks/runs/verification/actions_20261003/research.xml). Ruff and configured mypy pass; the final integrated verification is recorded in Report 031.

Source-selection calibration requires acquisition, independent labels and a frozen held-out evaluation. Downstream citation correctness and task usefulness are explicitly NOT RUN; the guide supplies the blinded review record contract. Provider cost must be reviewed using available usage metadata, with missing usage treated as unavailable. Promotion remains a separate reviewed opt-in.
