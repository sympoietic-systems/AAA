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


## Recorded conversation replay

[Report 063](../reports/063-belief-conversation-replay/README.md) adds five source-bound saved turns, four matched framing arms, and two generator-family conditions. NVIDIA emitted nominations in all four arms of turn 3974 with both historical and current tag protocols. Automated judgments remain provisional; no independent accuracy or slot benefit is established. Production participation stays off/0.

Run from the repository root; use fresh artifact paths and directories:

```powershell
uv run python -m benchmarks.suites.belief_conversation_replay collect --message-id 3974 --output benchmarks/runs/NEW-REPLAY/capture.json
uv run python -m benchmarks.suites.belief_conversation_replay prepare --input benchmarks/runs/NEW-REPLAY/capture.json --output benchmarks/runs/NEW-REPLAY/packet.json
uv run python -m benchmarks.suites.belief_conversation_replay run --input benchmarks/runs/NEW-REPLAY/packet.json --output benchmarks/runs/NEW-REPLAY/live
uv run python -m benchmarks.suites.belief_replay_report --packet benchmarks/runs/NEW-REPLAY/packet.json --run benchmarks/runs/NEW-REPLAY/live --output benchmarks/runs/NEW-REPLAY/review
```

Collection reads the production API; generation/review uses configured provider credentials and finite calls. This runner has no belief database writer. Resume validates sealed identity/prompt hashes and never reissues failed, uncertain or completed checkpoints. Review and generation have separate failure circuits. Optional NVIDIA model selection uses the explicit `nvidia_router/` prefix. The report retains invalid judgments and separately labels exact-source quote-envelope projections without rewriting receipts.

Saved emissions and legacy previews lack canonical historical standing/geometry. This is a counterfactual response replay, not the full current intake pipeline. Identical scoped1/scoped2 inputs in candidate-poor cases expose model variability. Do not equate emitted tags with accepted candidates, reviewer preferences with gold, or successful-only timings with latency acceptance. The next gate needs isolated full intake replay, independent semantic references and downstream artistic usefulness.


## Isolated intake replay

[Report 064](../reports/064-belief-intake-replay/README.md) exercises the real v2 parser, source intake, assessment, exact-repeat linking and persisted receipt notifications in fresh migrated SQLite databases. It preserves missing recorded context and keeps authored contrasts separate/nongold. Six live Jev responses all abstained at the current confidence floor; unscoped recurrences grew the pending queue. No runtime fix or threshold change is inferred.

```powershell
uv run python -m benchmarks.suites.belief_intake_replay --source benchmarks/runs/belief-conversation-replay/2026-10-11-t15-v1 --output benchmarks/runs/belief-intake-replay/NEW-RUN
```

Add `--recorded-only` to skip authored live contrasts. The output must be new and inside benchmarks/runs; this is a source reconstruction, not a production backup. Contract and pre-call checkpoints persist before work. No resume/retry is provided: inspect failed/uncertain receipts before authorizing a new live condition. The defaults bound provider calls to seven with one worker and preserve current assessment policy. A blank TypeSafe key uses the configured LLM key, matching the documented configuration fallback. Source seals are checked before ingestion.


## Incomplete recurrence review display

[ADR-128](../decisions/ADR-128-incomplete-belief-recurrence-display.md) and [Report 065](../reports/065-belief-recurrence/README.md) add read-only grouping to the candidate queue. Exact repeated text with absent scope, time, evidence quote and consequence can share one expandable entry when the same agent/conversation and every member's ancestor relationship are verified. Sibling branches, enriched context, changed sources and reviewed records remain separate.

Counts describe visible queue entries. Each underlying proposal, source, assessment and detail remains available. Occurrences add no independent support, mass or confidence. The API preserves its proposal arrays and adds optional recurrence_group metadata. The reader considers at most 50 eligible entries and 128 ancestry steps; incomplete/cyclic ancestry leaves entries separate. Group metadata exposes scan truncation and unavailable ancestry. A deep-linked member opens its group, and keyboard controls expand/select the original entries. No schema migration or rollout flag is introduced; this behavior takes effect only when the new build is deployed.

This addresses queue clutter. It does not reduce stored proposal counts, perform semantic merging, tune Jev or close T15 semantic acceptance.


## Per-question evaluation diagnostics

[ADR-129](../decisions/ADR-129-belief-evaluation-diagnostics.md) and [Report 066](../reports/066-belief-dimension-diagnostics/README.md) preserve at most fourteen observed question results in new native assessment receipts. Each records an allowed choice, finite confidence or unavailable value, configured threshold, and within-threshold/below-threshold/missing/invalid-choice/invalid-confidence status. Relation diagnostics bind the original comparison ID and statement hash after invalid-context pairs are excluded.

These observations remain outside accepted relations and warrant dimensions. The all-or-nothing confidence gate and existing scope/time guards remain unchanged. Native belief reasoning, Traces/Creases and export use the same immutable receipt. The UI labels confidence as classifier-reported, without calibrated accuracy. Malformed raw strings/objects/secrets are omitted. Historical receipts without diagnostics stay empty; no provider backfill or automatic retries.

The six saved Jev responses were replayed offline with exact original state/question hashes: thirty-four observations retained, every assessment still abstained, zero accepted relations/decisions. This proves projection/diagnostic retention on those inputs; it does not calibrate Jev or supply independent semantic gold. New JSON fields require compatible readers; binary rollback to a strict older parser needs a compatibility build. Production rollout remains separate.
