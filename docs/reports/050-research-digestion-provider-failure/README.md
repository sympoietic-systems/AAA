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

## Operator action at the original release (superseded by T79 below)

Deploy the tested commit, then start a new research task. The old task's expired frozen deadline is preserved; this patch does not silently replay it. A paid model can still experience upstream capacity throttling. Other configured paid models can now be attempted with the same usable key. No model preference or production configuration was changed by this fix.

### Follow-up: search POST redirect failure

The next user-reported Search failure was `POST redirects are disabled`, with no source URLs and `undefined` tab counts. This error originates in the application's bounded HTTP wrapper: research sent a POST to DuckDuckGo Lite, but the wrapper deliberately rejects POST redirects to prevent replaying request bodies. Search now sends an encoded GET query through the acquisition wrapper in both research and standalone calls. Redirect destinations retain per-hop validation, redirect ceilings and response-size limits. The failed-step UI omits absent badge counts.

The deterministic regression reproduced the exact error before the change. After the change, redirected search returns the fixture source, preserves query characters, and rejects a redirect to a private address before issuing that request. Related backend verification: 39 tests passed; backend lint, formatting and the 89-module strict typing gate passed. All 146 frontend tests, standard/strict TypeScript checks and production build passed; the lint ratchet reported zero regressions against its existing 164 errors and 10 warnings. The full backend suite was not repeated for this scoped follow-up. This does not establish live DuckDuckGo availability or the quality of the reported long search query. After deployment, retry the Search step only if its task remains eligible and its provider deadline is still valid; otherwise start a fresh copy or whole-task retry.

### Follow-up: search waits on optional model ranking

Read-only production receipts for task `8dc23e13-dda4-4ab1-b990-e647e8a8cb08` are retained under `benchmarks/runs/research/search_stall_20261008/`. Search began at 08:12:49 UTC. Two direct DuckDuckGo queries returned HTTP 200 and two returned HTTP 202; fallback retrieval subsequently supplied candidate pools. The phase then ranked four pools sequentially, without persisting any selected URLs until all ranking finished. OpenRouter capacity throttling, truncated 500-token replies, and repeated NVIDIA DeepSeek timeouts kept the UI showing four running Search groups and zero saved results. Ranking activity continued until roughly 08:20:42 UTC; the frozen task deadline was 08:22:17 UTC. At digestion, the remaining budget was too short to wait for the provider pool cooldown. The task ultimately became partial: 12 sources entered digestion, nine analyses failed, and no findings were extracted; source content remains retained.

Optional ranking now has a 15-second bound per query and disables thinking for its small JSON response. Timeout preserves retrieved candidate order. Each query persists its selected URLs and completion before the next query is ranked. The manual-step API returns 409 before changing state if a phase lock is held, and the UI displays that error. The auto worker preserves an already-terminal task instead of attempting a second completion/failure transition. Cancellation still propagates rather than returning a ranking fallback.

The operator instructed that NVIDIA calls use Nemotron rather than DeepSeek. Local main/background/structural pool entries were changed to Nemotron Super. Legacy NVIDIA DeepSeek routes in configured pools, fallback models and overrides are replaced with Nemotron Super, with a warning, so a retained VPS environment does not continue calling that route after restart. Other providers remain available according to their configured order. See [configuration guidance](../../guides/CONFIG.md).

Verification: the search/lifecycle fix passed all 836 backend and benchmark tests, with the existing third-party MOBI `imghdr` deprecation warning. The final NVIDIA policy and selector-controls change then passed 76 focused backend tests; backend lint, formatting (469 files) and configured strict typing (89 modules) passed. All 146 frontend tests, TypeScript checks and production build passed. The lint ratchet passed with 161 remaining legacy errors, 10 warnings and zero regressions. No live LLM test or deployment was performed during this follow-up; production inspection was read-only. Start a new copy or whole-task retry after deployment because the recorded task is now partial and its original deadline is no longer usable.

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


### Follow-up: second-cycle timeout and explicit same-task recovery

Production task `3bcb61d4-989d-46dc-aa91-221490a1f0ad` began on 2026-10-08 at 15:41:47 UTC with a frozen 600-second watchdog. The first cycle produced nine successful analyses. Reflection then consumed almost four minutes. The second cycle ran ten search queries plus a direct URL group, and Digest began at 15:51:04 with only 43 seconds left. The deadline expired at 15:51:47 after some analyses had succeeded. Private receipts are retained under `benchmarks/runs/research/digest_deadline_20261008/`. This failure demonstrates insufficient remaining execution time; source texts and completed per-source analyses remain recoverable.

The correction caps every cycle at six search queries, raises the default configurable watchdog to 1800 seconds, and implements explicit same-task step recovery with a new bounded execution revision. Digest recovery retains source identities, source text and completed analysis, and reanalyzes missing or failed results. Old receipts remain immutable; stale action writes are rejected. Automatic mode continues afterward. Recovery requires no running phase, unfinished action or running child, and does not extend existing branch consent. This supersedes earlier advice to create a new task solely because its watchdog expired.

Architectural boundary review used the [mcp-architectural-decision workflow](../../../.agents/skills/mcp-architectural-decision/SKILL.md), consultation `28d9f14d-696a-41ee-b472-d1392ce25770`. Recovery keeps the failed execution receipt intact while recording a distinct authorized revision on the same task.


The initial full verification run found two fixture failures: the child reserve test relied on an implicit 64-attempt default, and the resonance API mock guessed an ID after the human message had already been persisted. The branching fixture now freezes 64 explicitly; the resonance integration uses an isolated temporary database, deterministic provider doubles and the actual human message ID. Existing reserve and link assertions remain. A subsequent architecture check required automatic continuation scheduling to pass through the async research service boundary. Focused regressions also reject cross-phase step-ID reuse and source-version reuse when retained text differs.


T79 verification: the final complete backend/benchmark run passed **881 tests**, with the existing third-party MOBI `imghdr` deprecation warning, in 582.25 seconds. Receipt: `benchmarks/runs/research/digest_deadline_recovery_20261009/backend_suite.log`. Recovery and architecture regressions also passed 21 focused checks, including the representation-identity guard; counts overlap the full suite. Backend Ruff lint and formatting pass, and configured strict typing passes for 93 modules. All 146 frontend tests, standard/strict TypeScript checks and production build pass. The frontend lint ratchet reports 161 existing errors, 10 warnings and zero regressions. The new-research form defaults to depth 4 instead of 2; existing research depths remain unchanged. The local query setting was raised from 4 to 6. VPS deployment and a live recovery of the reported task have not been performed; the user will deploy and run that recovery.
