# Navigation performance review — 2026-10-31

Belief histories were scanning the event ledger once per visible belief on the
server event loop. A slow belief request could therefore delay conversation
navigation even though the conversation query itself was fast.

The fix adds `belief_events(belief_id, timestamp DESC)` in migration 070 and moves
belief reads, timeseries, ecosystem computation and skill reads to worker threads.
The existing full belief response remains compatible. Traits & Health now uses
the authenticated `GET /api/beliefs/health?agent_id=symbia` endpoint, which returns
only `somatic` (null for this agent-level view) and `ecosystem`. It reads no event
histories or proposal receipts. The creases dropdown fetches conversation titles
when opened rather than on every page mount.

PM2 now defaults to the built frontend bundle. The local public-page browser check
observed 7 code resources in the build versus 52 in development mode. The preview
server's inherited API proxy was checked: auth discovery returned 200 and an
unauthenticated conversation request returned 401.

## Local measurements

Five samples on a disposable snapshot containing 191,134 belief events and 57
beliefs with histories gave these medians:

- History reads without the index: 1.645 seconds; with the index: 0.120 seconds
  (13.7× faster).
- Full beliefs plus JSON serialization: 278 ms and 2,484,825 bytes.
- Health-only response plus JSON serialization: 33 ms and 306 bytes.

These are local read-path measurements, not production latency or an end-to-end
reproduction of the reported minute-long delay. The original local conversation
list query took about 6 ms. Production data volume, disk contention and network
latency still need measurement during rollout. Existing API callers still receive bounded histories by default. The Beliefs tab
now requests `include_history=false` and retrieves only a selected belief's
histories through `GET /api/beliefs/{belief_id}/history?agent_id=symbia`. Compact
items carry `history_loaded=false` so omitted histories are distinct from empty
histories. The detail view ignores responses from a previous selection or agent;
version and chart requests wait until their respective tabs are opened. A local
read-path check reduced the list from 2.49 MB to 133 KB (about 95%) and from
101 ms to 7 ms, before network transfer.

Reproduce without modifying the source database:

```bash
uv run python -m scripts.benchmark_navigation --database /path/to/aaa.db --samples 5
```

The command copies SQLite into a temporary directory, compares indexed and
unindexed reads there, emits aggregate JSON, and removes the copy on exit.

Validation: the full Python suite passed 1,270 tests; the frontend passed 171
tests, build and lint. Backend Ruff checks and the configured strict mypy slice
(120 source files) passed. The Python suite retains one third-party `mobi`
deprecation warning. Regression checks cover worker-thread execution, the indexed
query plan, health endpoint authorization/validation, and deferred frontend reads.

## Production verification

The tested commit was deployed to `100.111.85.100` on 2026-10-31 after an online
database backup passed its integrity check. Before deployment, beliefs took 2.631
seconds and an overlapping conversation-list request took 3.316 seconds. After
deployment, the overlapping conversation request took 0.102 seconds. A subsequent
check through the frontend proxy returned conversations in 0.020 seconds, beliefs
in 0.308 seconds, and health in 0.048 seconds (281 bytes). These are individual
server-local probes, not browser latency percentiles.

The live browser loaded the built frontend; authenticated API proxy checks passed,
anonymous protected requests returned 401, and migration 070 was recorded. Both
AAA services were online under the existing `www-data` PM2 instance.

## Rollout

After updating the checkout, back up the production database, apply migration 070
through the normal migration runner, and restart the backend. Migration 070 is
idempotent and changes only an index.

Reload the frontend configuration rather than restarting the old saved process:

```bash
pm2 startOrRestart ecosystem.config.cjs --only aaa-frontend --update-env
```

This builds before serving and fails on build errors. Confirm the HTML references
`/assets/` rather than `/src/`, confirm API proxy/auth behavior, and time the
authenticated health, beliefs and conversation endpoints. Preserve the previous
commit and bundle for rollback; the added index can remain during code rollback.

An older PM2 entry may execute the shell script directly. `startOrRestart` can
retain that executable while updating its arguments to the new Bash layout,
passing the script path as its own mode argument. If HTML still references `/src/`,
recreate only the frontend entry:

```bash
pm2 delete aaa-frontend
pm2 start ecosystem.config.cjs --only aaa-frontend
pm2 save
```
