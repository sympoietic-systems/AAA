# 044 — Research V2 release evaluation

Date: 2026-10-07. Tasks: T71 release evaluation and T72 dispatch consent. The user explicitly authorized promotion on assumed research improvement and will review quality in production. Technical verification passes under the repository's configured gates. Independent research quality, branch usefulness and monetary billing remain unknown. No VPS deployment was performed.

## Decision and scope

The original blocked evaluation is preserved in `benchmarks/runs/research/t71_evaluation_20261007`. Its global failures have been repaired. The authorized assembler receipts live in `benchmarks/runs/research/t71_authorized_release_20261007`, hash-referencing the final JUnit, check-status file, acquisition fixture and prior T69/T70 receipts. Its three-repeat medians are 4.632269 seconds legacy, 4.537621 bounded cold and 0.002129 bounded warm. The authorized release assembler requires passing checks and all 13 reliability scenarios before returning `READY_FOR_AUTHORIZED_ROLLOUT`; it records the explicit quality assumption separately. Without that authorization it remains blocked. [ADR 113](../../decisions/ADR-113-research-v2-authorized-rollout.md) records the contract amendment.

Research V2 action receipts are enabled for new tasks. Jev remains disabled following the user's final non-adoption decision. Docling remains optional and default-off. Branching remains off unless the user checks Allow branching; that checkbox freezes bounded dispatch consent while preserving source witnesses, two-child limits, shared budgets and the parent deadline. Existing tasks retain their policy.

## Automated live NVIDIA comparison

Private canonical receipts: `benchmarks/runs/research/t71_live_final_20261007/telemetry_receipts.json`, with dataset and runner hashes in `metadata.json`. `summary_reassembled.json` derives token and incomplete-call counts from those unchanged receipts using the final summary code. The raw summary written by the running worker predates those extra summary fields. No source pools or raw model responses are copied into this report.

The comparison ran actual registered pipeline steps with `nvidia/nemotron-3-super-120b-a12b`. Both arms used the same frozen objective and two captured snippets, the same provider, 4,096-token call ceiling, 40-second execution boundary and bounded call/phase limits. One snippet was too short for usable source contact; both arms ultimately counted one unique usable URL. Branching was off. Retrieval used frozen snippets; live web search, full-document parsing, persona generation, indexing and queue/manager lifecycle were excluded. This compares bounded pipeline behavior, not two deployed applications or complete internet research.

| Final replay observation | Legacy path | V2 path |
| --- | ---: | ---: |
| Cases | 1 | 1 |
| Pipeline seconds | 125.002 | 248.489 |
| Provider calls | 8 | 12 |
| Calls with reported token usage | 8 | 11 |
| Reported total tokens | 17,353 | 28,092 |
| Interrupted/incomplete calls | 0 | 1 |
| Leaf HTTP errors / truncations observed | 0 / 0 | 0 / 0 |
| Pipeline result | Report returned | Partial report after execution timeout |
| Unique usable sources | 1 | 1 |
| Independent quality / billing | Unknown | Unknown |

V2 correctly retained degraded delivery when a provider attempt exceeded the 40-second boundary. The missing call's tokens are unknown, so V2's reported tokens are an incomplete total. Legacy also emitted an invalid-JSON warning earlier in the run; its report and harness operational-valid flag do not certify source support or quality. Legacy task status remained active because the harness excludes the task manager; its pipeline phase reached complete. V2 ended partial. Neither a report nor a model completion is an independent quality judgment. The V2 first-result counter reflects initial source parsing, not time to a useful answer, and has no comparable legacy value.

This case does **not** demonstrate better quality, faster research, or cheaper execution. The appropriate next observation is a representative production set with source-level review, rather than promotion of these timings as a general result.

## Debugging observations and fixes

Earlier Ultra attempts suffered 503s/timeouts. Nano inference returned 404 despite a catalog entry; a separate Llama probe returned 410. These are endpoint observations, not quality scores. Inference availability must be checked through an actual request.

A pre-fix Super run returned both reports: legacy 313.416 seconds/16 calls, V2 121.320 seconds/8 calls. It exposed malformed JSON falling back to an empty reflection while reporting no error, and repeated analyses being counted as distinct sources. Those results are debugging evidence and cannot substantiate a speed or quality win. The final replay above follows these fixes:

- Invalid structured completion sets `invalid_json_completion`; an active V2 delivery scope records failure and cannot silently finish complete.
- Synthesis counts unique usable URLs and digested file IDs, including child archives; repeated parent/child visits are deduplicated. Child material remains unreviewed raw evidence.
- Synthesis reports actual child count rather than phase count, and uses the configured embedder service off the event loop.
- The live observer records cancellation as terminal and summaries count incomplete calls separately from HTTP errors. Old receipts preserve their original started marker.

Global repairs include parameterized lock typing, metrics recommendation work off the event loop, repository-backed message metrics, narrower decode catches, thinking-mode temperature sanitization, current ADR-098 homeostatic test expectations, migration-seed-aware fixtures, deterministic chat tests, retry callback contracts and fail-closed benchmark scoring when an arm is absent. Architecture debt allowances were transferred to renamed methods without increasing totals. Frontend component types removed lint regressions and reduced the existing debt baseline; no rule was disabled to pass verification.

## Verification and limits

The final combined suite passed 661 tests: 648 backend tests and 13 release/live benchmark tests. JUnit is recorded in `benchmarks/runs/research/t71_release_final.xml`; subsequent main integration verification is recorded separately. Backend Ruff lint and formatting pass; configured strict mypy passes for 73 files. Frontend typing, production build and configured lint pass; frontend tests pass with 131 tests in 22 files. The configured frontend lint gate reports 164 accepted legacy errors and 10 legacy warnings with zero regressions. Raw `npm run lint:all` remains nonzero: this release does not claim all historical frontend lint debt is cleared.

One third-party MOBI `imghdr` deprecation warning remains in Python tests. Test databases and raw receipts live in ignored run directories or untracked `.verify` scratch space; they are not committed. No production database was modified. Earlier scratch cleanup was rejected by automatic policy review, so those files were preserved.

The scenario assembler requires all 13 outage, truncation, cancellation, late-delivery, restart, reflection, branch-off/wait/approve/decline/failure/restart and parent-merge scenarios to pass. Missing, skipped or mixed failed parameterizations cannot become passes. Dispatch-covenant tests additionally cover witnessed approval, immutable deadlines, restart, missing covenant and rejection of model-origin consent. Test counts across older reports overlap and must not be added.

Offline acquisition replay uses equal coverage hashes across legacy, bounded cold and bounded warm paths. The original three-repeat medians were 4.630691, 4.537804 and 0.002459 seconds respectively. Warm cache avoids fixture work; this is not a production speedup. Reflection ablation checks the actual guard and restart state, not independently scored synthesis quality.

## Remaining evidence and operation

T69 concluded with Jev non-adoption; [Report 042](../042-jev-experimental-promotion/README.md) owns its actual endpoint trials. [Report 043](../043-parser-evaluation/README.md) owns the native-text PDF comparison. Genuine scans, independent parser references and VPS resource/license certification remain user-deferred T75. Independent downstream support/coverage and branch usefulness review remain explicit rollout limitations.

Follow [Research V2 rollout](../../guides/RESEARCH_V2_ROLLOUT.md) for defaults and deployment preparation. On the described 4-core/8-GB VPS, keep optional Docling off initially. After deploying, review source support, useful coverage, contrary retention, partial status and branch value. No measured quality superiority or observed dollar cost is asserted.

## Reproduction

```powershell
python -m benchmarks.suites.research_live --dataset <frozen-packet.json> --env-file <private-env-file> --output <new-run-directory> --cases 1 --model nvidia/nemotron-3-super-120b-a12b
python -m benchmarks.suites.research_release --checks <check-statuses.json> --regression-xml <pytest-junit.xml> --jev-summary <t69-summary.json> --parser-receipts <t70-receipts.json> --output <new-run-directory> --repeats 3 --authorized-assumption-rollout
```

The live runner checkpoints each call and phase and hashes frozen inputs. It stops further calls after permanent endpoint failures. The release assembler validates explicit check statuses, bounded JUnit input and frozen acquisition dimensions; absent technical evidence fails closed. The authorization flag records the existing human rollout decision and supplies no independent quality labels.
