# Research digestion provider failure

Incident: `829e5971-3b4a-4212-9d6d-323dee0115b2`, production, 2026-10-08. The task stopped as `partial`, with `missing_findings`; it was not still running. Parsing retained 12 source records, but 11 analyses returned an exhausted-pool error and one source was blocked by anti-bot protection. Digest groups incorrectly reported completion, and no final explanation was stored.

## Cause and evidence

Production logs show OpenRouter returning HTTP 429, followed by NVIDIA Ultra HTTP 503 and NVIDIA DeepSeek timeouts. The pool cooled every candidate and subsequent digestion calls made no provider attempts. Failed analyses were converted into empty lists and counted as analyzed sources.

Authenticated read-only production receipts are retained in the private local `benchmarks/runs/research/digestion_incident_20261008/` directory of the original managed investigation worktree. The task, steps, phase, meta-log and server-log snapshots are the incident evidence; no production task was modified.

At 06:41 UTC, a direct request using the local configured OpenRouter key showed a paid key with a $5 daily limit and $4.717 remaining. The exact production research model, `qwen/qwen3.8-flash`, returned 429 with `limit_source=upstream_provider_shared_pool` and `provider_name=Alibaba`. No rate-limit headers were present. The application's previous `0/0 remaining` message defaulted missing headers to zero and did not prove an exhausted quota.

A separate minimal request to paid `qwen/qwen3-30b-a3b-instruct-2507` succeeded through StreamLake, HTTP 200, returning `OK` with 15 total tokens. This confirms local-key access to that model at the time of the check; it does not establish identical VPS credentials or research quality. See [OpenRouter current-key API](https://openrouter.ai/docs/api/api-reference/api-keys/get-current-key).

A second check at 07:07 UTC still returned the same Alibaba upstream shared-pool 429 for `qwen/qwen3.8-flash`. The model's public endpoints API listed only Alibaba. The local configuration had no separate background key, so the probe used the key selected by local OpenRouter routing.

## Changes

- Explicit upstream shared-pool throttling preserves the credential for other models. Unknown or credential-wide limits retain existing key rotation behavior; raw provider metadata is not logged.
- Missing quota headers are represented as unknown, rather than zero.
- Research calls can wait for existing model cooldowns when every candidate is cooling down. Waiting obeys the frozen deadline and attempt ceiling; interactive calls still fail promptly.
- Failed source analysis produces an explicit failure status and explanatory gap. Failed/skipped sources do not increment the successful analysis count. Groups and tasks disclose partial delivery, with a stored explanation when analysis yields no findings.
- The UI labels failed analysis and refreshes step records when task status or phase changes, including the terminal transition. An older request cannot overwrite the latest terminal step response.
- Ordinary backend tests clear ambient provider credentials; tests can explicitly supply their own fixture keys. The skills API authorization/CRUD test mocks vector scoring, preventing its dependency on ambient model evaluation from stalling backend verification.
- Removed an unused browser-session initializer that called a nonexistent repository method and failed the existing strict typing gate. Schema initialization remains owned by database migrations.

## Operator action

Deploy the tested commit, then start a new research task. The old task's expired frozen deadline is preserved; this patch does not silently replay it. A paid model can still experience upstream capacity throttling. Other configured paid models can now be attempted with the same usable key. No model preference or production configuration was changed by this fix.

## Verification

Regression coverage includes bounded cooldown recovery, deadline exhaustion, interactive fail-fast behavior, upstream-versus-key throttling, absent quota headers, private-metadata exclusion, analysis failures, successful-analysis counts, terminal UI refresh and stale-response exclusion.

- Focused incident regressions: 9 passed; provider retry coverage plus the initial eight incident cases: 23 passed; existing model-pool tests: 14 passed.
- Related research receipt, phase, attempt-limit, evidence and retry checks: 85 passed before the additional upstream-limit cases were added.
- Final combined backend/benchmark suite: **764 passed**, one third-party MOBI/`imghdr` deprecation warning, 534.47 seconds. Receipts: `benchmarks/runs/research/digestion_final_suite.log`.
- Frontend: **145 passed**; lint ratchet reports zero regressions; standard and strict TypeScript checks and production build pass using Node 24. The existing lint baseline contains 164 legacy errors and 10 legacy warnings; this is not a claim that full legacy lint is clean.
- Backend Ruff lint and format checks pass. Strict typing of the three modified provider modules passes.
- The initial configured strict gate exposed a pre-existing `SessionStore.initialize()` call to a nonexistent repository method. The unused initializer was removed without changing session issuance or schema initialization. The research service files remain outside the existing strict typing ratchet.
- Configured strict typing: **87 modules passed** on the fix baseline; **89 modules passed** after integrating current committed `main`. No strict scope was removed or weakened.
- After integrating the concurrent committed belief-contract changes from `main`, **59 focused integration tests passed**, and all **145 frontend tests**, frontend type checks, lint ratchet and build passed again. These counts overlap the full suite and must not be added together.
- The subsequently committed review-corpus changes from `main` were also integrated: **12 corpus tests passed**, and configured strict typing remained clean at **89 modules**.
- The first broad backend run was interrupted after its final group stopped progressing. It had reported one upload-test failure; the complete upload-security file subsequently passed independently (15 tests). A fresh full run uses per-test logging and a 45-second stack-dump threshold, with receipts in `benchmarks/runs/research/digestion_full_verification.log`.
- The diagnostic rerun passed the upload and research checks, then stalled at `test_skills_api_flux_control` while awaiting the skill-update request (stack dump retained). After isolating vector scoring, the late backend group passed all 31 tests. The final combined backend/benchmark run uses isolated credentials and is recorded in `benchmarks/runs/research/digestion_final_suite.log`.
