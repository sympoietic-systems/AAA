# Beliefs v2 evaluation

T15 currently provides a local provisional corpus audit and a synthetic matched participation replay. Semantic acceptance remains open. Keep exploratory participation disabled with zero slots until independent evidence, recorded replay and downstream usefulness close the acceptance gate in [BELIEF_SPEC §A](../systems/BELIEF_SPEC.md).

Run the offline evaluator from the repository root:

```powershell
uv run python -m benchmarks.suites.belief_v2_evaluation --packet docs/reports/049-belief-v2-review-corpus/review-packet.json --frozen benchmarks/runs/belief-auto-review/2026-10-08-t4-v4/frozen-provisional.json --output benchmarks/runs/belief-v2-evaluation/NEW-RUN
```

The output directory must be new. The runner writes `contract.json` before evaluating held-out cases, then writes `evaluation.json`. The contract binds the source packet, freezes the zero/one/two slot arms and zero-tolerance engineering targets, and keeps recommended production slots at zero. Semantic thresholds remain explicitly unset because there is no independent baseline to justify them. An exception leaves a visible incomplete directory; use a fresh run directory after correcting the cause.

The audit revalidates the existing frozen artifact, source and prompt bindings, reviewer identity, context gates and disjoint source-family partitions. It reports attributed relation/warrant nominations, uncertainty, disagreement and failed reviewer slots separately for tuning, validation and held-out cases. It preserves every case. Accuracy, false equivalence, missed conflicts, useful distinction retention, redundant reviewer burden and downstream usefulness remain `null`; agreement cannot fill those fields.

The CLI replay uses the actual T14 exploratory selector on a deliberately synthetic twelve-record coverage sentinel. It uses identical records and signatures at zero, one and two slots. Its receipts retain scoped standing, dissent and dormant inquiry, and assert no new authority or independent warrant. The replay counts insertions and coverage. It neither runs a response model nor measures causal influence, adjudicates semantic conflict, or establishes production latency. The active six-slot window and spectral margin are outside this exploratory ablation; their runtime tests remain in T14.

The Python `replay(snapshot, signatures, source_kind=...)` interface also accepts recorded `SelectionSnapshot` values. Callers must retain their source and capture provenance; a `recorded_snapshot` label alone is no proof of origin. The present CLI run supplies no recorded snapshots or reconstructed legacy geometry. Snapshot and signature hashes bind the result, but their capture provenance is not independently verified by this helper.

To close T15, recover comparison context and source-independent judgments, establish calibration baselines for justified semantic targets before a new held-out run, and retain useful questions/conflicts alongside redundant candidates. Collect source-bound recorded participation snapshots/signatures, measure scan omissions and repeated selection under matched inputs, and evaluate response usefulness independently of insertion counts. Do not interpret a smaller queue as success. Automated provisional preparation remains available; this guide adds no mandatory review of all 54 cases.

See [Report 062](../reports/062-belief-v2-evaluation/README.md) for the empirical result and unresolved judgments, and [participation configuration](belief-participation.md) for the default-off boundary. The evaluator has no database writer, provider request, migration or production configuration port.
