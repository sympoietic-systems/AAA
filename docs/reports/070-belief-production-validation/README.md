# 070 — Belief production validation: current gate coverage

Date: 2026-10-13. Scope: bounded read-only validation of six recent Symbia proposal records against the saved review corpus and the existing automated review receipts. No production writes or policy changes.

## Result

The six sampled proposals still match the production records: all six statement hashes and statuses matched. The corpus passed its structural binding and partition checks. This confirms snapshot integrity for this sample; it does not validate semantic judgments.

The production database currently has zero rows in both `belief_admission` and `belief_encounters` (`has_more=false` on each bounded query). A subsequent bounded scan found 122 proposals created in the 30-day window ending 2026-10-13: 94 pending, 19 refined, and 9 adopted. Their first source-trace types were 82 `chat_turn`, 29 `intention`, and 11 `scar_fold`. The Jev admission path therefore has no production receipts to evaluate, even though legacy proposal creation is active.

One current production event directly demonstrates task-prompt bleed-through. At 2026-10-13 07:19, Codex message 4120 in the investigation conversation was stored as a chat turn. At 07:20, the production server created pending Codex proposal `67dc62ae-b487-4afc-9c0e-df1722684b0d` with `source_trace=[{"type":"chat_turn","id":"4120"}]`. Its 200-character provisional statement is an exact prefix of that 878-character Codex prompt. The prompt was a meta-level question about belief intake, not a proposed durable belief. This proves that a task prompt can enter automatic proposal nucleation; it does not show that all `chat_turn` nominations are false positives or that they become crystallized beliefs.

## Runtime boundary

At validation time, v2 explicit intake wrote encounters and explicit legacy admission wrote `belief_admission` receipts, but automatic chat-turn nucleation fell through to direct legacy proposal creation when passive intake returned `None`. That route bypassed both receipt tables. The unsafe fallback was fixed locally on 2026-10-13: passive chat, user assertions, and conversational patterns now require a source-bound intake receipt; missing, disabled, or unpromoted intake abstains and emits a bounded INFO log without source text. Explicit legacy notes retain their declared compatibility route. The regression tests verify both disabled and missing intake, including the no-proposal result. The focused origin suite now passes (88 tests). This local change has not been verified or deployed in production.

The repository config currently sets `passive_chat`, `explicit_chat`, `explicit_dream`, and v2 `assessment.enabled` to false; legacy `belief_admission.jev_shadow` is true. These are local settings, not a verified production configuration. Authenticated production `/health` returned `ok` with 19 modules, but exposes no build or config identity. The database reports migrations through `068_belief_export_order` (migration id 70); migrations do not identify the running code commit or effective flags. The empty receipt tables are explained for the observed Codex row by the legacy chat-turn path; they cannot establish full-window runtime coverage. The Beliefs v2 spec keeps T15 in progress and T18 pending; its rollout contract requires explicit authorization. No flags were changed.

The saved T4 automated review run contains 10 valid model annotations across the six cases’ 12 reviewer slots. Two reviewers returned `no_comparison` for the pending case. The other eight valid annotations were projected to `insufficient_context`. Five of six cases have incomplete context; all five cases with a proposed comparison lack complete candidate-and-comparison context. The remaining case has no saved comparison and cannot test duplicate detection.

| Check | Result |
|---|---:|
| Production proposal rows matched to saved snapshot | 6 / 6 |
| Statement hashes unchanged | 6 / 6 |
| Saved corpus structural validation | Passed |
| Model review annotations usable | 10 / 12 slots |
| Cases with incomplete context | 5 / 6 |
| Complete saved comparison pairs | 0 / 5 |
| Production admission / encounter receipts | 0 / 0 |
| Independent human semantic labels | 0 |

## Interpretation

The evidence now supports two specific conclusions. The saved review projections fail closed on missing comparison context. Separately, task/chat-turn text can become pending proposals through the legacy `BeliefDynamicsEngine` path without producing a Jev admission receipt. The 30-day source counts show this path is common across agents; the single prompt-prefix match is direct evidence of a false positive in a meta-level task turn. The recovered six-case corpus still lacks complete context for every proposed comparison, so semantic accuracy and the overall false-positive rate remain unmeasured.

The model opinions are provisional diagnostics, not gold labels. Their agreement cannot estimate precision, recall, false-positive rate, reviewer accuracy, or whether a proposal is genuinely new or strong. The empty production receipt tables mean the new gate has not yet been observed in production. No threshold or adoption behavior should be changed from this sample.

## Next validation step

The local policy decision is now explicit: default-off passive conversational origins abstain rather than create receipt-free proposals. T15 acceptance and the separately authorized T18 rollout remain required before changing production behavior. Before rollout, verify the deployed build/config identity and run a complete shadow window that measures source-level nomination, abstention, retain/defer recommendation, and downstream human disposition; use a small blinded human anchor set for semantic quality.

## Provenance

- [Machine-readable validation receipt](../../../benchmarks/runs/belief-production-validation/2026-10-13-v1/validation.json) contains only proposal IDs, status/hash checks, context coverage, reviewer counts, and aggregate gate-table counts; it does not copy proposal text.
- [Saved review packet](../049-belief-v2-review-corpus/review-packet.json) was structurally validated with `uv run python -m benchmarks.suites.belief_review_corpus validate --packet docs/reports/049-belief-v2-review-corpus/review-packet.json`.
- [Frozen provisional reviews](../../../benchmarks/runs/belief-auto-review/2026-10-08-t4-v4/frozen-provisional.json) are historical model outputs and were not treated as independent gold.
- Existing intake-path checks: `uv run pytest backend/tests/test_belief_admission.py backend/tests/test_belief_explicit_intake.py backend/tests/test_belief_assessment.py -q -p no:cacheprovider` (61 passed).
- Production inspection used authenticated, bounded read-only requests against the configured AAA production database and API on 2026-10-13.
- Server evidence: authenticated `/health` returned `ok` (19 modules); the read-only migration table ended at migration id 70, `068_belief_export_order`. The scrubbed server-log tail and authenticated message/proposal GETs bind the current prompt-prefix example; source text is omitted from the receipt.
- Local follow-up: `test_v29_default_off_passive_chat_abstains_without_legacy_proposal` and `test_v29_passive_chat_abstains_when_intake_service_is_missing`; 88 focused origin tests passed, Ruff checks passed, and strict mypy passed for `belief_passive_intake.py`. `belief_engine.py` has pre-existing strict-mypy errors outside this change; its file-level mypy check is not clean.
