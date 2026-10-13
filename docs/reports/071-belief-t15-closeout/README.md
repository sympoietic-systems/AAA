# 071 — Beliefs v2 T15 evaluation closeout

Date: 2026-10-13. Decision: close T15 as an inconclusive evaluation; keep semantic promotion blocked and exploratory participation at zero. No production writes, provider calls, threshold changes, or deployment occurred in this closeout.

## Decision

T15 has exercised the frozen review corpus, saved-turn counterfactuals, isolated intake, recurrence grouping, per-question diagnostics, a hypothetical challenge, and an offline shadow projection. These runs establish where the current apparatus abstains, where incomplete context grows the review queue, and which selectors repeat the same records. They do not establish semantic accuracy or downstream usefulness.

The user declined the optional eight-case human anchor. The prepared blind packet remains unannotated. No model review is promoted to gold. Numeric semantic thresholds remain unset, and the existing 0.85 confidence floor remains unchanged. The evaluation result is **no-go for semantic acceptance or participation enablement**.

T15 is closed as an evaluation task because its evidence and limitations are now explicit. This status does not clear BELIEF_SPEC §V22 or §V23. Promotion and rollout still require independent judgments and useful-outcome evidence. Production passive participation remains disabled with zero slots.

## Evidence reviewed

| Evaluation surface | Observed evidence | Bound on interpretation |
| --- | --- | --- |
| Frozen review corpus, [Report 062](../062-belief-v2-evaluation/README.md) | 44 held-out cases came from one connected source family; 66 valid review outputs of 88 slots; 20 cases had disagreement; 35 pair contexts were incomplete; 44 lineages were unknown. | No independent labels; no accuracy, false-equivalence, missed-conflict, or usefulness estimate. |
| Saved-turn replay, [Report 063](../063-belief-conversation-replay/README.md) | Five saved turns; 28 generation attempts with 25 complete; 10 judgment attempts with five source-bound provisional projections. | Counterfactual framing; one case had two valid opinions. No independent answer-usefulness or slot-benefit judgment. |
| Isolated intake, [Report 064](../064-belief-intake-replay/README.md) | 13 recorded/generated nominations produced 13 pending proposals and zero Jev calls; six of six live Jev contrast calls abstained. An unscoped exact recurrence created another proposal. | Reconstructed source inputs and authored contrasts do not establish semantic correctness. Queue growth is observed; semantic duplicate rate is not. |
| Recurrence display, [Report 065](../065-belief-recurrence/README.md) | Three stored proposals displayed as one expandable verified branch group; original entries remained available. | Reduces visible clutter only; adds no semantic equivalence or persisted reduction. |
| Dimension diagnostics, [Report 066](../066-belief-dimension-diagnostics/README.md) | 34 question observations retained across six saved assessments; all six assessments abstained. | Diagnostics expose attributed labels; no calibration or accuracy evidence. |
| Hypothetical challenge, [Report 067](../067-belief-challenge/README.md) | 16 cases across eight authored topic families; 10 successful Jev calls abstained; three context guards abstained; three calls were unavailable; 29 valid reference opinions. | References are provisional opinions. A selected four-case subset had 4/4 agreement; this is not accuracy. Challenge full-suite concurrency failure remains unresolved. |
| Offline shadow gate, [Report 068](../068-belief-shadow-gate/README.md) | 12 above-floor dimension observations from seven hypothetical cases; none from six saved contrasts or 13 recorded nominations; 16 cases were context-blocked. | The projection is diagnostic. No human labels or usefulness outcomes validate retained observations. |
| Production validation, [Report 070](../070-belief-production-validation/README.md) | 122 proposals in the 30-day window: 94 pending, 19 refined, nine adopted. First trace types: 82 chat turns, 29 intentions, 11 scar folds. Production admission and encounter tables each had zero rows. | One prompt-prefix false positive was directly bound. This sample does not estimate all-origin false-positive rate or confirm deployed local fixes. |

The local passive-chat fix is committed as `7948856`, but was not deployed. Production build identity and effective flags remain unknown. Existing production activity therefore cannot be treated as a shadow evaluation of the v2 gate.

## Frozen limits and acceptance result

- Production participation slots: `0`.
- Production writes and enablement in this evaluation: `0`.
- Confidence threshold changes: `0`.
- Cases or receipts removed after disagreement, failure, or abstention: `0`.
- Semantic acceptance threshold: unset; no independent baseline justifies one.
- Human anchor: offered as eight blinded held-out cases and declined; annotations received: `0`.

The current evidence fails the semantic acceptance gate because independent ground truth and situated usefulness outcomes are absent. The result does not support threshold tuning, admission changes, or production enablement. Exact recurrence grouping can continue to present incomplete repeats compactly while preserving every source record.

## Remaining work outside T15

T15c's earlier same-key workshop failure was not reproduced in the current full backend test run: 1,048 passed with one existing third-party deprecation warning. Keep the earlier failure in its original report; this single rerun does not identify its cause or rule out a rare race. T15c's challenge accounting and focused gates are complete. T16 must implement revision, supersession, and resurfacing. T17 must close integrated backend/frontend release checks. T18 remains a separately authorized staged rollout requiring build/config identity, complete-window telemetry, origin outcomes, and rollback evidence.

## Provenance and verification

The source reports and run receipts above remain the evidence owners; this closeout adds no cloned production text or provider output. The optional blind packet and generator are under [`benchmarks/runs/belief-human-anchor/2026-10-13-v1/`](../../../benchmarks/runs/belief-human-anchor/2026-10-13-v1/) and `benchmarks/suites/belief_human_anchor.py`. The packet receipt records zero annotations and is excluded from semantic scoring.

This closeout used the existing reports and receipts only. It made no live provider request and no production database/API write. Verification: `uv run pytest backend/tests -q -p no:cacheprovider` → 1,048 passed, one existing `mobi`/`imghdr` deprecation warning, 840.07 seconds; the new anchor builder's focused suite → 3 passed; Ruff lint/format and `git diff --check` passed for the new builder and tests.
