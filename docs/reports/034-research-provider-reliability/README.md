# Report 034: T63 Provider Reliability

Date: 2026-10-05. Scope: opt-in provider reliability, not Research V2 release or research-quality evaluation.

T63 adds pending-before-invocation persistence, request-correlated pool attempts, immutable terminal observations, task/request attempt limits, task/attempt deadlines, bounded outstanding calls and partial task delivery. [ADR-106](../../decisions/ADR-106-research-provider-attempt-boundaries.md) defines compatibility and cancellation limits.

## Verification

- Research receipts, journal, provider boundaries, orchestrator state/phases/collaborators, task transactions, API helpers and model-pool compatibility: 99 tests passed; one known baseline thinking-mode test deselected. A subsequently added partial-task retry API check passed with all four API helper tests, bringing this tested scope to 100 distinct passing tests.
- Named boundary checks include durable pending-before-call, request-correlated failover, timeout despite cancellation resistance, immutable late delivery, cancellation and private-error masking, restart-preserved task attempt count, expired task deadline, stale-action rejection, pending-attempt closure and capacity reservation before asynchronous storage.
- Truncated synthesis produces partial status; `complete()` cannot promote it. A budget-exhausted fallback cannot supply successful delivery.
- Backend lint passes. Changed Python files pass format verification. Strict typing passes for ten directly checked implementation files; configured global mypy retains the pre-existing missing `asyncio.Task` type arguments in `backend/services/keyed_lock.py`.
- Frontend production build passes, including both TypeScript checks. All 125 frontend tests pass. Frontend lint reports the same 16 unbaselined violations in three unchanged Node Explorer files on both this branch and untouched T62 commit `54bfc4e`.
- `test_model_pool::TestModelPool::test_openai_compatible_max_tokens` reproduces on untouched `54bfc4e`: its generic thinking-provider temperature assertion disagrees with the existing implementation. No thinking policy was changed to satisfy that assertion.
- The earlier backend-wide boredom-coupling failure remains documented in [Report 033](../033-research-receipt-baseline/README.md). These results do not establish a green repository-wide suite.

## Live NVIDIA probe

[nvidia-probe.json](nvidia-probe.json) is the sole saved observation for this checkpoint. The explicit live harness used `model_pool_nvidia` with `nvidia/nemotron-3-ultra-550b-a55b`; it produced one complete attempt with a provider response ID, `finish_reason=stop`, no truncation and 27 total tokens. Timing is in the observation. This verifies transport and receipt plumbing, not synthesis quality or a latency distribution. NVIDIA testing is free according to the user's stated provider terms; observed cost remains null because the response supplied no cost.

Run outside pytest with the configured environment file:

```powershell
D:/01_GIT/AAA/.venv/Scripts/python.exe scripts/probe_research_provider.py --env-file D:/01_GIT/AAA/.env
```

The harness selects NVIDIA only, does not change production routing, and uses an automatically removed temporary database. Credentials and raw response text are not saved in the report.

## Remaining boundaries

Deadlines bound cooperative asynchronous waiting. They do not forcibly stop a blocking thread or prove exactly-once legacy step/memory effects. Interrupted action recovery remains explicit. Version-one journals keep their original passive coverage. Numerical price/reservation accounting, report support, child research and independent calibration remain later tasks. Production activation remains disabled by default.
