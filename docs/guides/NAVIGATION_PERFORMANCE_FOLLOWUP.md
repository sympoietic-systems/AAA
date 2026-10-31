# Navigation performance follow-up: implementation receipt

Date: 2026-10-31. Baseline: `d2a2346`. Implemented on the isolated
`perf/navigation-loading` branch. Production deployment and live verification completed on 2026-10-31.
The primary checkout's unrelated staged refactor was preserved.

## Behavior

- Attractors requests compact beliefs. Telemetry owns one request and timer per
  key, pauses automatic work while hidden, cancels unused requests, rejects old
  sessions, coalesces manual refreshes, preserves last good data, and retains at
  most 20 inactive snapshots per channel.
- Search keeps existing defaults, snippets, scopes, weights and timestamp-ascending
  ties. Archive reads and ranking cross one worker boundary. Dictionary merging
  replaces repeated scans; vector batches use scalar checks near ties/gates.
  Admission permits two active workers and eight waiters, with a two-second wait
  limit and structured 503 / `Retry-After: 1`. A disconnected client retains its
  worker slot until execution finishes. Periodic GIL yields keep ranking bursts
  from starving the event loop.
- Skills uses opt-in `include_content=false`; default callers still receive full
  content. Selected content loads separately. Errors remain separate from editable
  content, empty strings remain valid, and stale selections cannot clear another
  skill's loading state. Old version-list responses are ignored/aborted.
- Exact React package matching and direct footer imports remove Markdown/math from
  cold login and landing requests. KaTeX CSS loads with the renderer. Content pages
  still load these libraries; this change does not remove their rendering cost.
- History list/path SQL omits raw thinking and context strings already discarded by
  serialization. `has_context`, tokens, metrics, quality, branches and full detail
  retrieval remain intact. Audited callers: history, title generation,
  consolidation, semantic-knot compaction and conversation metrics.

## Measurements

Deterministic synthetic fixtures, cached embeddings, no model/network calls;
20 timed samples after one excluded warm-up. Same process/dependencies per
baseline/candidate pair. These are local measurements, not production SLAs.

| Measurement | Baseline | Candidate |
| --- | ---: | ---: |
| 4,000-message semantic search median | 841 ms | 64 ms |
| Search p95 | 912 ms | 88 ms |
| Event-loop delay p95 (maximum heartbeat gap per query) | 911 ms | 36.5 ms |
| 89-skill grouped JSON | 688,450 B | 99,092 B |
| 50-message projected string volume | 2,243,940 chars | 43,940 chars |
| Cold-login JavaScript, decoded browser resources | 901,412 B | 253,016 B |
| Cold-login JavaScript, separately gzip-compressed files | 271,784 B | 81,213 B |
| Cold-login JavaScript requests | 7 | 6 |

The uncooperative batched worker was rejected: 56.7 ms event-loop p95 exceeded
50 ms despite faster ranking. The accepted worker meets both specified gates.
Peak search-process RSS was about 827 MiB including existing heavyweight imports;
this cumulative process peak is not an isolated ranking allocation measurement.
History read medians were 4.17 → 3.94 ms in this repository fixture: the main gain
is reduced projection volume, not a promised visible endpoint speedup. Skill
formatting remained about 0.8 ms; its main gain is transfer size.

Browser traces used the existing public production login as baseline and the
local production build as candidate. Both settled login and landing graphs exclude
Markdown/KaTeX in the candidate; HTML preloads alone were not the check. Cached
responses and different origins make network latency comparisons invalid. Gzip
sizes above are reproducible file estimates, not observed wire transfer sizes.
A loopback-only read-only preview also rendered agent beliefs (80 selectable
items) and the nodes route; renderer libraries loaded on those content routes.
The old local backend lacks the health-only endpoint and returned 405 there;
this was not treated as a candidate endpoint validation. New API contracts were
validated with isolated API tests. The temporary preview denied all writes.

Receipts:
[search/payload aggregates](../../benchmarks/navigation-performance-receipt.json),
[browser resource trace](../../benchmarks/navigation-browser-receipt.json).
Frozen scalar references live under `benchmarks/fixtures/`; do not update them
when changing production code.

Reproduce from the worktree using the project Python environment:

```bash
python scripts/benchmark_navigation_search.py --candidate --samples 20
python scripts/benchmark_navigation_payloads.py
```

Use `scripts/navigation_browser_probe.js` in the collaborative browser after a
fresh production-build navigation. Compare decoded resources and runtime requests;
record cache state before making network timing claims. Run performance benchmarks
without the test/build workload. Run pytest processes serially: the existing global
test cleanup removes shared `*test*.db` files, so concurrent runs interfere.

## Validation

- Full configured Python suite: 1,293 passed; one existing third-party `mobi`
  deprecation warning. After the final worker scheduling adjustment and richer
  history fixture, 26 focused search/payload tests passed, including near ties,
  threshold boundaries, cancellation, overload, auth, metadata parity and complete
  history response equality with null/empty contexts, metrics and quality receipts.
- Frontend: 183 passed; production build and both TypeScript checks passed.
  Math after lazy policy loading and hostile HTML sanitization are covered.
- Backend Ruff check/format passed; strict mypy passed 121 files, including the new
  search service. New polling code entered the frontend strict typing ratchet.
- Frontend lint ratchet passed with zero regressions; 158 legacy errors and nine
  legacy warnings remain. Static-analysis rules were not weakened.

## Separate production rollout

The following procedure was executed for this follow-up. Do not replay the
previous rollout's migration or rebuild from the dirty primary checkout.

1. SSH as `root@100.111.85.100`. Verify `/srv/apps/AAA` is still the live checkout,
   inspect status/active work, record its revision and current public asset hashes.
   Verify `www-data` still owns AAA's PM2 processes with `PM2_HOME=/var/www/.pm2`.
2. Preserve the deployed commit and built assets outside the checkout. Retain the
   existing database backup. No migration or database restore is required here.
3. Fetch the tested feature revision and fast-forward only a clean compatible live
   branch. Stop on unrelated changes or divergent history. Build `frontend` before
   restarting affected AAA services. Use the existing locked dependencies.
4. Restart `aaa-backend` and `aaa-frontend` under the verified PM2 owner. Inspect
   frontend executable/args: `/usr/bin/bash` and `scripts/run_frontend.sh`, production
   mode. Restarting an old incompatible executable layout is insufficient; see
   [the previous rollout note](NAVIGATION_PERFORMANCE.md).
5. Verify the deployed revision, online processes, built `/assets/` HTML, API proxy,
   session/CSRF behavior, anonymous 401s, default/compact skills and beliefs,
   cross-conversation/agent scope, selected histories/content and full thinking/
   context detail. Do not edit skills merely to test performance on live data.
6. On the public site, observe visible and hidden polling, selection changes,
   session expiry, cold login resources, Markdown/math, and concurrent search plus
   a lightweight request. Verify search saturation is bounded and returns the
   documented retry response. Record actual live timings separately from this table.
7. Roll back on contract/auth drift, leaked request chains, instability or increased
   stalls. Restore the previous code revision and saved bundle, then restart the
   same services. Do not restore/delete the database; this change has no migration.

## Production rollout record

Deployment authorized on 2026-10-31. Preflight confirmed a clean `/srv/apps/AAA`
checkout at `d2a2346`, with both AAA services online under `www-data`. The frontend
uses `/usr/bin/bash scripts/run_frontend.sh` in production mode. Deploy only the
tested `perf/navigation-loading` revision; preserve the prior bundle and revision.
The server fast-forwarded to `0c2fd56` (performance implementation `603096e`),
built successfully as `www-data`, then restarted only `aaa-backend` and
`aaa-frontend` and saved the PM2 process configuration. Both services returned
online. A transient 502 during the frontend startup build cleared when preview
started; the final public login and API checks succeeded.

Rollback artifacts are retained at
`/srv/apps/AAA-rollbacks/navigation-followup-20261031/`: the prior revision
`d2a2346` and `frontend-dist.tar.gz`. The existing database backup remains intact;
no database migration was introduced or manually applied.

Single post-restart probes through the production frontend proxy returned:

| Probe | Result | Elapsed |
| --- | --- | ---: |
| Health | 200; 281 B | 134 ms |
| Compact skills | 200; 275,751 B versus 572,619 B full | 53 ms |
| Compact beliefs | 200; 104,785 B versus 2,326,729 B full | 83 ms |
| Selected belief history | 200; 42,083 B | 17 ms |
| History list | 200; 24,712 B | 11 ms |
| Glitch search, no model call | 200 | 279 ms |
| Overlapping conversation list | 200 | 26 ms |

Default full content remains present; compact skill records omit both content
fields and carry `content_loaded=false`. Cross-agent belief history returned 404,
anonymous skills returned 401, thinking/context detail remained accessible, and
list responses continued to omit their raw content. Cookie session creation,
verification and revocation passed, and cross-origin mutation was rejected with
403. No skill edits or conversation writes were used for validation.

The actual public login browser requested six JavaScript resources totaling
253,016 decoded bytes, with no Markdown/KaTeX request. It serves
`/assets/index-CoC5aQyh.js`, matching the tested production build. These are live
sanity probes, not latency percentiles or an end-to-end speed guarantee.
Authenticated visible/hidden polling and overload/cancellation were covered by
local deterministic tests; those interactions were not repeated in an authenticated
public browser session. Public content/math checks remain a useful user smoke test.

Aggregate live evidence is in
[`navigation-production-receipt.json`](../../benchmarks/navigation-production-receipt.json).
The subsequent documentation-only commit records these results; it does not require
another service restart.
