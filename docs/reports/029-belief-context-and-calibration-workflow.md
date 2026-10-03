# Report 029: Belief context guard and calibration workflow

Date: 2026-10-03. Branch: `codex/belief-context-calibration`. Parent: `7b50e97`.

## Delivered

[ADR-102](../decisions/ADR-102-belief-context-and-calibration.md) and the [annotation guide](../guides/belief-calibration-annotation.md) define the contract. Statements need explicit hash-bound scope, time, provenance and referent resolution. Missing/stale/ambiguous mappings abstain before network access. Explicit antecedents permit classification; grammatical nonreferences require explicit annotation. The detector is conservative and English-oriented, not a general resolver. Replay refuses unvalidated context, including historical evidence.

The [real annotation packet](../../benchmarks/runs/beliefs/annotation_v1_20261003/packet.json) contains **240 unlabeled pairs**: 48 tuning, 48 validation, 144 held out, with disjoint belief identities. User confirmed no labeled corpus exists and authorized annotation preparation. The [readiness result](../../benchmarks/runs/beliefs/annotation_v1_20261003/readiness.json) makes zero classifier calls and leaves promotion BLOCKED. Human judgments or declared independent dual-model judgments with known author-model exclusion are required; annotator disagreement remains ambiguity. Freeze detects later dataset changes. Annotation declarations require review; the tool cannot authenticate human identity or prove model independence.

## Verification

**18 tests passed**, covering existing dry-run routing/copy behavior, context guards, explicit resolution, split leakage, independent labels, preserved disagreement, frozen input mutation and repeat-aware intervals. [XML receipt](../../benchmarks/runs/verification/actions_20261003/belief.xml). Configured mypy passes 43 files; strict context/service slice passes 2 files. Ruff check/format pass. No production beliefs, matrix rows or skills were changed.

## Bounded native comparison

Three variants use the same question contract: unguarded offline baseline, explicit context with guards, and context with staged relation/strength assessment. [Raw receipts](../../benchmarks/runs/beliefs/context_sentinels_v1_20261003/receipts.json) and [derived scorecard](../../benchmarks/runs/beliefs/context_sentinels_v1_20261003/scorecard.json) own the evidence. Six synthetic cases were repeated twice; repeats do not increase independent sample size.

| Variant | Correct relations across 6 unique cases | False contradiction reviews | Interpretation |
| --- | --- | --- | --- |
| Unguarded baseline | 4 | 1 | Confident unresolved-reference failure persists |
| Context plus guard | 6 | 0 | Explicit ambiguity abstains before model |
| Context plus staged assessment | 6 | 0 | No quality advantage established over one-call context path |

These fixtures are authored regression labels, not independently adjudicated real gold. Even zero false positives among five negative cases has a wide 95% Wilson interval (upper bound about 43%). This run cannot justify promotion. Raw receipts preserve provider latency; the derived staged latency adds both model-call durations.

## Geometry integration audit

The [read-only snapshot audit](../../benchmarks/runs/beliefs/annotation_v1_20261003/geometry_audit.json) finds 56 beliefs, nonnegative coordinates in [0,1], pair cosine minimum approximately 0.609 and zero tension rows. No pair reaches the existing geometric antagonism threshold below -0.2. This explains that snapshot's empty geometric tension field; it does not establish absence of semantic contradiction. Live semantic/geometric integration still needs separate provenance and scale contracts.

## Remaining gate

Annotate and freeze the packet, enlarge underrepresented negative/ambiguous classes where necessary, then run the real held-out comparison and shadow observation. No automated adoption, ontology edits, skill pruning or production promotion is part of this delivery.
