# Navigation Performance Implementation Plan

Status: implemented and locally verified; production follow-up rollout pending. Date: 2026-10-31.

The [performance spec](../systems/NAVIGATION_PERFORMANCE_SPEC.md) owns contracts,
acceptance criteria, and task statuses. This plan explains execution order and
verification. The measured review identified recurring traffic and an event-loop
stall; the first two implementation stages address those directly.

## 1. Establish a repeatable baseline — spec T1

Freeze a deterministic archive with approximately 4,000 messages, multiple vector
dimensions, tied scores, malformed/absent vectors, and large prompt/thinking fields.
Include skills with long content and list metadata, plus conversation/agent scope
fixtures. Use controlled deferred requests and clocks for polling tests.

Record the parent commit, dependency versions, CPU/runtime, fixture counts, warm-up,
sample count, raw/compressed payload sizes, timing distribution, and memory. Capture
production-build browser requests separately from server timing. Existing single
probes are evidence for prioritization, not the new benchmark baseline.

Deliverable: repeatable harnesses and baseline receipts, without production writes
or live model calls. Establish actual search ordering before changing ranking.

## 2. Remove recurring telemetry waste — spec T2

Use compact scoped beliefs for Attractors. Then fix request ownership in both
poller variants: one in-flight request/timer per key, a bounded queued manual
refresh, visibility pause/resume, last-subscriber cancellation, stale/session result
rejection, current-state error recovery, and bounded inactive-cache retention.

Test subscribe/unsubscribe while a request is pending; immediate resubscribe;
overlapping refreshes; hidden/visible transitions; session loss; stale failures;
and repeated conversation changes. Preserve last good data on errors.

Exit: spec V1–V4 pass; compact traffic is at most 10% of the frozen full response.
Commit this complete stage independently so it can ship or roll back separately.

## 3. Keep search off the event loop — spec T3

Keep asynchronous embedding generation where it is. Move synchronous candidate
loading and ranking into a service-owned worker use case. First replace repeated
linear result lookups with keyed lookup; then batch vector comparisons by compatible
dimension. Bound active/waiting work and retain slot ownership until a dispatched
worker exits, including after client cancellation.

Compare all modes and weighted combinations against the scalar reference. Cover
near ties, zero vectors, mismatched dimensions, duplicate matches and snippets.
Preserve the implementation's existing tie order; do not repair the contradictory
timestamp-sort comment by changing behavior in this task.

Exit: spec V5–V7 pass, including the 50 ms p95 event-loop and 50% median ranking
improvement benchmark gates. If vectorization changes top results, retain a
parity-preserving implementation and record the unmet performance gate.

## 4. Make skill lists metadata-only — spec T4

Add an opt-in compact contract with a distinct frontend summary type. Keep the
existing grouped response and default full API. Load content for the selected skill
through the current authenticated workshop endpoint. Block content saves until
loading succeeds; preserve legitimate empty content and explicit new-skill input.

Exit: spec V8 passes; compact JSON is at most 60% of the frozen full response and
selection, edit, reload, versions, failure and stale-response tests pass.

## 5. Trim eager browser dependencies — spec T5

Correct React package matching, inspect the resulting graph, then remove remaining
eager shared-UI import paths. Compare clean builds and browser traces on login and
representative agent/conversation/research pages. Verify math and sanitized HTML
after lazy loading, including load failures. Do not merely move a preload into an
immediate startup import.

Exit: spec V9 passes. Report measured request/byte/timing changes without claiming
that all 597 KB of observed library code disappears from every page.

## 6. Stop reading discarded history fields — spec T6

Audit all callers of the list/path repository methods. Narrow only safe SQL
projections, retain the SQL `has_context` expression, and preserve full detail
retrieval. Compare complete serialized outputs, pagination, paths and metrics.

Exit: spec V10 passes. Treat reduced I/O and memory as the main gain; the measured
production endpoint was already fast, so do not promise a large visible speedup.

## 7. Integrated verification and rollout preparation — spec T7

Run the integrated Python and frontend gates once changes are assembled. Re-run
the frozen benchmarks with at least 20 timed samples after warm-up. Produce a
reviewable change set, per-stage results, known limitations and rollback instructions.
Implementation does not become complete by merely drafting a PR or passing unit tests.

Prepare the live checklist in spec §A. A later deployment must verify checkout,
active work, service ownership, auth, compact/default responses, public-site asset
delivery, concurrent search responsiveness, and visible/hidden polling behavior.
Record actual production results after rollout; do not copy local timings into
production claims.

## Deferred work

Leave generic caching, new vector stores, new database indexes, conversation-list
rewrites and broad component virtualization out of this change set. Reconsider
them only if the follow-up measurements identify a remaining material bottleneck.

## Implementation result

All seven tasks are complete locally. [Verification, measurements and the separate
rollout procedure](../guides/NAVIGATION_PERFORMANCE_FOLLOWUP.md) record the accepted
implementation and its limits. Production remains on the previously deployed baseline.
