# Navigation Performance Follow-up Specification

Status: implemented, deployed and verified in production. Date: 2026-10-31.

Owner: this file owns this follow-up's requirements, interfaces, invariants, and
task statuses. IDs are file-scoped. Root [SPEC.md](../../SPEC.md) owns shared
constraints; [the implementation plan](../architecture/NAVIGATION_PERFORMANCE_PLAN.md)
owns sequencing. [Previous changes and measurements](../guides/NAVIGATION_PERFORMANCE.md)
remain the record of the already-deployed navigation fixes.

## §G — Goal

Reduce recurring network traffic, prevent search from blocking unrelated requests,
and reduce unnecessary page-startup and database work. Preserve search results,
conversation content, skill editing, authorization, and existing API defaults.

## §C — Constraints and scope

- Implementation was authorized after review of this plan. Prior performance fixes
  remain the baseline. This follow-up prepares a separate production rollout; local
  verification is not a deployment claim.
- Retain Python/FastAPI, React/TypeScript, SQLite WAL, current model selection, and
  existing dependency directions. No new database, vector database, ANN index,
  Redis, model calls, schema migration, or blanket application cache in this scope.
- Preserve unrelated work in the primary checkout. Implementation uses an isolated
  branch/worktree and small, independently reviewable commits.
- Read-only endpoints retain their authorization and agent/conversation scope.
  Credentials, source text, embeddings, and raw prompts do not enter benchmark
  receipts. Live production probes require the applicable rollout authorization.
- Characterize existing behavior before optimizing it. Existing successful API
  defaults remain compatible; new compact responses require explicit opt-in.
- Each synchronous database/CPU use case crosses one worker boundary. Do not add
  nested offloading or share SQLite connections across threads.
- Unit and regression tests use isolated databases, deterministic embeddings, and
  controlled clocks. No production writes, network/model dependencies, or billable
  evaluation calls in tests.
- No changes to search semantics, conversation ordering, belief admission, skill
  lifecycle, historical receipts, or Markdown safety policy.
- Follow existing ownership decisions: [ADR-030](../decisions/ADR-030-backend-modularity-refactoring.md),
  [ADR-040](../decisions/ADR-040-subscriber-driven-telemetry-and-multi-type-notifications.md),
  [ADR-093](../decisions/ADR-093-frontend-membrane-hardening-ast-sanitization-code-splitting.md),
  and [ADR-096](../decisions/ADR-096-browser-sessions-and-frontend-request-ownership.md).
  A materially different architecture requires its own decision before building.

## §R — Inspected evidence

These observations come from the 2026-10-31 review at code revision `d2a2346`.
Individual probes are not latency percentiles or universal service-level promises.

- R1 — Production Attractors request: 2,326,899 bytes / 293 ms; the same scoped
  request with `include_history=false`: 104,955 bytes / 57.7 ms. The poll interval
  is 15 seconds while subscribed. Source: [telemetryStore.ts](../../frontend/src/stores/telemetryStore.ts).
  [AttractorsSection](../../frontend/src/components/panels/sidepanel/AttractorsSection.tsx)
  consumes labels and metadata, not histories. Closed sections already unsubscribe.
- R2 — Local semantic-search probe over approximately 4,000 messages, using a
  cached query embedding: 1.286 seconds total; maximum observed event-loop delay
  1.080 seconds. Database loading is offloaded, but ranking runs in the async route
  and repeatedly searches the growing result list. Source:
  [search.py](../../backend/api/routes/search.py).
- R3 — Production `/api/skills/db`: 572,619 bytes / 40.4 ms. Local response:
  583,006 serialized bytes; omitting `content` and `short_content`: 280,376 bytes.
  The response contains 178 list entries representing 89 distinct skills. The UI
  already loads selected content separately. Sources:
  [skill.py](../../backend/services/skill.py),
  [SkillsSection.tsx](../../frontend/src/components/pages/agentpage/SkillsSection.tsx).
- R4 — Built React vendor chunk imports the Markdown chunk, which imports KaTeX.
  Those latter chunks total about 597 KB uncompressed and are preloaded by the
  initial HTML. The React substring matcher also matches `react-markdown`.
  Source: [vite.config.ts](../../frontend/vite.config.ts). No alternate bundle has
  yet been measured; the achievable startup reduction remains to be established.
- R5 — Local 50-message SQL projection: 2,281,086 string characters including
  thinking/context versus 63,716 without those fields; five-sample median query
  time 4.09 ms versus 0.30 ms. The serializer already returns those fields as null
  and exposes separate detail endpoints. Production history response: 16.6 ms.
  Sources: [message_history.py](../../backend/storage/repositories/conversation/message_history.py),
  [vector.py](../../backend/utils/vector.py). This is chiefly an I/O/memory gain.

## §I — Interfaces

I.telemetry:
- Keep the existing hook/subscription APIs. Attractors polling calls
  `getBeliefs(conversationId, "symbia", false)` using the existing compact API.
- Preserve the 15-second visible-page interval and existing jitter. Add no network
  request merely because another subscriber joins the same channel/key.
- Polling transports accept an optional `AbortSignal`; existing callers remain
  valid. Use the explicit same-origin API transport and existing session handling.
- Automatic polling pauses when the document is hidden. On visibility restoration,
  an actively subscribed channel refreshes once, then resumes its normal schedule.
- A manual refresh during an active request queues at most one follow-up refresh;
  its promise resolves after the follow-up settles. It must not return only an old
  request's pre-mutation result. Explicit refreshes may run without subscriptions.

I.search:
- Preserve `GET /api/search`, query parameters, success schema, and 100-result cap.
  Move synchronous candidate loading and ranking into an existing service-owned
  worker use case; retain asynchronous query-embedding generation outside it.
- Replace repeated result-list scans with keyed lookup; batch compatible vector
  comparisons. Preserve handling of absent, malformed, zero, and mismatched vectors.
- Preserve actual current tie ordering, not just the route comment. The inspected
  implementation sorts equal-score timestamps ascending despite a descending-order
  comment. Correcting that discrepancy is a separate behavior change, outside scope.
- Admit at most two active ranking jobs and eight waiting jobs per process. Capacity
  waits are bounded to two seconds. Excess/expired admission returns the existing
  structured error envelope with HTTP 503 and `Retry-After: 1`; no raw exception data.
  These are implementation defaults to verify against VPS memory, not new env vars.

I.skills:
- Add opt-in `GET /api/skills/db?include_content=false`; default remains `true`.
  Preserve grouped arrays, `all`, ordering, IDs, lifecycle, and list metadata.
- Compact items omit `content` and `short_content` and carry `content_loaded=false`.
  Define a distinct frontend summary type; absence must not masquerade as empty
  editable content. Keep the full response type/default unchanged.
- The Skills page requests summaries and uses the existing workshop load endpoint
  for the selected skill. Preserve that endpoint's method, CSRF, and auth behavior.
  Saving content requires a successful selected-skill load, or explicit user input
  for a newly created skill; loading/error states cannot overwrite content with empty text.

I.bundle:
- Match React package boundaries explicitly. `react-markdown` must not enter the
  React runtime vendor group through a substring match.
- Inspect and remove eager import paths that pull Markdown/math through shared UI
  exports. Those renderers load when a rendered view requires them. Do not remove
  sanitization, safe math behavior, or error/loading boundaries to reduce bytes.
- Vite production serving, API proxying, cookie authentication, and deep links remain
  compatible. No CDN or reverse-proxy configuration change is assumed.

I.history:
- Preserve history/path/thinking/context endpoints and their response values.
  Remove unused large columns only from the history-list and path SQL projections
  whose serializers already discard them. Keep `has_context`, token counts, metrics,
  signatures, quality, active items, pagination, and message ordering intact.
- Keep full-record retrieval for actual prompt/thinking detail consumers. Audit all
  callers of the shared repository methods before removing any column.

## §V — Acceptance invariants

V1: Compact telemetry preserves conversation scope, attractors, spectral labels,
category, mass, and confidence; no event/admission histories are requested.
On the frozen review fixture, its JSON size is at most 10% of the full response.

V2: At most one request and one scheduled timer exist per polling channel/key.
Repeated mount/unmount, visibility changes, and manual refresh cannot create
parallel poll chains. A queued manual refresh executes at most once per active request.

V3: Hidden documents schedule no automatic polling. Final unsubscribe cancels its
automatic timer/request. A session change invalidates old-session results and queued
work; a key change cannot publish data into another key. Abort is not a user-facing glitch.

V4: Last successful data survives refresh failures and polling cycles. Subscribers
see immutable snapshots; inactive cache entries are evicted least-recently-used
above 20 per channel. Active subscriptions are not evicted. No persistent browser cache is added.

V5: Search performs no archive-ranking loop on the event loop. On the deterministic
review-sized fixture, warm-run event-loop delay p95 is at most 50 ms and ranking
median is at least 50% lower than baseline. These are benchmark gates, not public SLAs.
Failure to meet either gate requires a recorded revised approach, not a completion claim.

V6: Across text, semantic, diffractive, glitch, and mixed-weight fixtures, result
IDs, ordering, snippets, scopes, and cap match the scalar reference. Scores match
within absolute tolerance 1e-6; near-tie cases must retain reference ordering and
top-100 membership. Do not approximate retrieval or silently change score meaning.

V7: Search admission respects I.search bounds; cancellation before dispatch removes
queued work. Cancellation after dispatch cannot free an active slot until the worker
actually exits. Worker failures remain visible through existing error handling.

V8: Compact skill lists preserve every skill and group membership. On the frozen
review fixture, compact JSON is at most 60% of full JSON. Selected content, editing,
versions, and late-response ownership remain correct; default API calls remain full.

V9: The cold-login page's eager JavaScript dependency graph excludes Markdown/math
rendering libraries. Measure both HTML preloads and runtime requests: moving a
library from a preload into an immediate dynamic import does not satisfy this gate.
Record raw and compressed bytes, request count, and timings; no claimed network gain
without a browser trace. Mathematical and sanitized Markdown rendering stays covered.

V10: History and path responses compare equal before/after on fixtures containing
large prompts, thinking, empty/null context, branches, metrics, and quality receipts.
The projection omits raw prompt/thinking columns but retains correct `has_context`.
Projected string volume on the frozen 50-message sample is at most 10% of baseline.

V11: Measurements distinguish SQL time, service/ranking time, serialization, HTTP
transfer, and browser rendering. Baseline/candidate runs use the same fixture,
dependency versions, environment, and concurrency. Warm-up is excluded; collect at
least 20 timed samples and report median/p95, counts, sizes, and process memory.

V12: No task completes with relevant failures, an unbounded worker/request queue,
weakened static-analysis rules, source/receipt loss, or unreported baseline failures.
Production completion requires a deployed revision, health/auth checks, and live
receipts; local test success alone is not a deployment claim.

## §T — Implementation tasks

id|status|task|cites
T1|x|freeze deterministic fixtures and current contracts; add reusable payload, event-loop, query-projection and browser measurement harnesses; record baseline environment and aggregate receipts|V6,V10,V11
T2|x|switch Attractors to compact polling; add visibility pause, request/timer ownership, cancellation, queued manual refresh, current-state error handling and bounded inactive retention; fake-clock/race/session tests|I.telemetry,V1,V2,V3,V4
T3|x|characterize all search modes and ties; move candidate loading/ranking behind one worker boundary; keyed score merging, batched exact comparisons and bounded admission; parity/concurrency/cancellation benchmarks|I.search,V5,V6,V7
T4|x|add opt-in skill summary contract and frontend types; use selected-content loading with safe editing states and stale-response protection; payload/auth/compatibility tests|I.skills,V8
T5|x|correct package matching and eager shared-UI imports; verify login and representative content routes in production build; preserve math/Markdown safety and document actual browser trace delta|I.bundle,V9,V11
T6|x|audit history repository callers; remove discarded raw columns from safe projections; retain detail retrieval and all output fields; response-equivalence and projection-volume tests|I.history,V10
T7|x|run integrated gates and comparable benchmarks; record accepted deltas, limitations and rollback steps; prepare a separately executable production rollout and post-deploy checklist|V1,V2,V3,V4,V5,V6,V7,V8,V9,V10,V11,V12

## §A — Verification and rollout gates

- Run boundary-specific tests while iterating. After integrated changes, run Python
  lint/format, configured strict mypy, full pytest, and frontend build/lint/tests.
  New/refactored service modules enter the existing strict typing ratchet. Do not
  rerun the full suite for each documentation edit.
- Baselines and benchmark receipts contain aggregates only. Create synthetic test
  databases in temporary directories; permitted real-data profiling uses a read-only
  source and disposable local snapshot. Remove temporary copies and test databases.
- Present each task's contract/result parity and measured deltas before proposing
  rollout. Do not mark a statistical claim from a single production probe.
- When rollout is authorized, inspect the live checkout, active work, deployed
  revision and service ownership first. Production previously used `/srv/apps/AAA`
  and the `www-data` PM2 instance; verify rather than assume those remain current.
- No database migration is expected. Retain the prior commit and built assets;
  preserve existing database backups. Build before serving, restart only affected
  AAA services, and use the documented PM2 executable-layout check.
- Verify default and compact APIs, cross-agent/conversation scope, session/CSRF,
  anonymous 401, search overload behavior, selected content and mathematical output.
  Verify the actual public site, not only localhost. Observe a visible and hidden
  polling cycle and a concurrent search plus lightweight request.
- Roll back code/bundle on contract drift, auth failure, request-chain leaks,
  increased event-loop stalls, service instability, or meaningful benchmark
  regression. Reverting this work must not restore a database or delete source data.

## §B — Bug log

B1|2026-10-31|Attractors repeatedly downloaded full histories and could overlap stale/session requests|compact transport plus per-key ownership, visibility/session cancellation, queued manual refresh and race tests; V1–V4
B2|2026-10-31|async search ranked synchronously and repeatedly scanned growing result lists|single bounded worker boundary, keyed merge, batched comparisons with scalar tie checks; periodic worker GIL yield meets the event-loop gate; V5–V7
B3|2026-10-31|skill load failures became editable error text and an earlier selection could clear a later selection's loading state|separate per-skill content/error/loading ownership; disable editing until content exists; preserve empty strings; V8

See [verification and rollout](../guides/NAVIGATION_PERFORMANCE_FOLLOWUP.md) and
[aggregate benchmark receipt](../../benchmarks/navigation-performance-receipt.json).
