# Report 024: Jev belief candidate routing and tension evidence

Branch: `codex/jev-belief-tension`. Parent: `a06b690`. Date: 2026-10-03.

## Implemented surface

`BeliefTriage` provides dry-run pair evaluation, candidate routing and bounded matrix evaluation. It has no database write port. Structural cosine similarity nominates pairs; Jev evaluates semantic contradiction, endorsement, orthogonality or abstention. Receipts retain separate contradiction and absorbability estimates, confidence, input and statement hashes, model, latency, pair IDs, prior evidence and review recommendations. Replaying stored answers gives the same recommendation without a model call.

Mass changes the confidence threshold and review priority, while contradiction remains an unweighted estimate. High-mass beliefs require 0.85 confidence; the 0.70–0.85 band remains an uncommitted watchlist. Low confidence and conflicting categorical/numeric answers abstain. Absorbability uncertainty cannot hide a strong contradiction. Previous matrix evidence appears only in receipts and is excluded from Jev input.

The CLI can read checkpointed snapshots and apply qualified belief-pair evidence to a **fresh disposable copy**. It validates current statement hashes, mass and vector similarity and uses one bounded atomic transaction. It cannot update the source database, mutate belief/proposal tables, or create matrix edges from proposal-only IDs. The existing runtime belief engine and commitment guard are outside this prototype; promotion is withheld on empirical grounds. [ADR-100](../decisions/ADR-100-jev-belief-evidence-and-review-routing.md) documents this boundary.

## Verification

12 focused tests passed: semantic routing independent of identical vectors, maturity gate and watchlist, prior evidence excluded from input, deterministic replay, malformed vectors/numbers, conflicting answers, bounded candidates, proposal-only identity, independent absorption confidence, positive matrix persistence on a fixture copy and full rollback on stale evidence. The fixture source hash and belief rows remain unchanged. Copy application refuses existing destinations and the source itself. Strict mypy passes for both new typed modules. Final integrated verification is in Report 025.

Initial fixture seeds violated the existing `origin` and `somatic_anchor` checks; corrected seeds use `authored` and `none`. Initial calibration also exposed an unrelated absorbability-confidence gate suppressing contradiction. Its confidence now gates absorption review independently. SPEC V103 and B80 preserve these contracts. The final integrated run also found a live-DNS dependency in an existing SSRF unit test. Fixed public and restricted DNS fixtures now make that test deterministic while retaining restricted-host denial; V104 and B81 record the isolation contract.

## Native semantic calibration

Canonical [corpus](../../benchmarks/runs/beliefs/calibration_corrected_20261003/corpus.json) and [receipts](../../benchmarks/runs/beliefs/calibration_corrected_20261003/receipts.json) contain six synthetic cases repeated twice through the configured TypeSafe Jev endpoint. Every case uses identical vectors, deliberately preventing vector similarity from serving as the semantic oracle.

Categorical labels matched 8/12 evaluations. The explicit contradiction, endorsement, unrelated statements and different-time scope cases matched on both repetitions. Unresolved-reference statements (`It is ready` / `It is not ready`) were confidently classified as contradictory in both repetitions, although the corpus requires abstention without established common referents. Injection text was labeled orthogonal rather than abstain, but low confidence prevented routing on both repetitions.

Routing produced four contradiction reviews, two endorsement reviews, two distinct-claim reviews, two watchlist records and two abstentions. Abstention rate: 16.7%; watchlist rate: 16.7%. Median end-to-end evaluation latency: 2,145.8 ms. Two of the four contradiction reviews are the unresolved-reference false positives. This is a wiring/calibration smoke test, not a representative accuracy estimate or a validated probability calibration. The evidence does **not** support runtime promotion.

## Read-only snapshot inspection

Canonical [scoped snapshot receipts](../../benchmarks/runs/beliefs/snapshot_scoped_20261003/snapshot_receipts.json) inspect 56 active Symbia beliefs and two pending proposals owned by `codex`. Proposal owner is an explicit CLI scope because pending proposals in this backup are owned by originating agents rather than Symbia. Eight nominated belief pairs and four proposal-target pairs were evaluated. There were three endorsement reviews, two distinct-claim reviews and seven abstentions (58.3%); all four proposal comparisons abstained. Median end-to-end latency: 1,816.5 ms.

No pair qualified for a contradiction edge, so the fresh matrix copy remained empty. That outcome is retained; no edges were invented to demonstrate activity. Positive write behavior is independently established by the transaction regression fixture. Only JSON receipts are retained in the repository; disposable database copies are cleaned after verification.

The 341 MB backup SHA-256 was identical before and after inspection:

`1289ad8bfb4a56b0c5f99d9a3354c95fa701ba94bf3abd69f8ba7c6bf1046d2f`

The first snapshot pass used the default Symbia proposal-owner scope and correctly found zero proposals. It is excluded from the canonical scoped run. Structural nomination is capped at 64 beliefs and 20 pair evaluations; this inspection measures neither exhaustive contradiction recall nor the quality of all 91 historical proposals.
