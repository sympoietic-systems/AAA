# Report 037: T66 Finite Research Actions

Date: 2026-10-06. Scope: opt-in policy v5, scheduler version 1.

The scheduler admits registered action kinds with phase prerequisites, persisted predecessor linkage and the existing shared provider limits/deadline. A hard 64-action ceiling and three unchanged acquisition/digestion transitions bound loops. Unsupported insert/remove patches, arbitrary phases and invalid patch lifetimes fail explicitly. Override patches remain subject to prerequisites and reflection guards.

One framing reflection is permitted. A second consecutive reflection requires a newly persisted contrary edge tied to source segments and a changed typed anchor projection. Query rewording, confidence, source counts, new content alone and same-content refetch cannot warrant another pass. A third consecutive pass is blocked. Internal reflection cycles retain zero evidential weight. Current witnesses require an unexpired fetched acquisition or authorized document provenance; historical evidence remains retained. The implementation conservatively supports contradiction witnesses; it does not infer category failure or consequential exclusion from prose.

Decisions and witness references appear in immutable terminal action observations. Scheduler state, patch TTL and reroute count survive checkpoint/restart. Only the latest decision is duplicated in the checkpoint; the action ledger owns durable history. Existing frozen policies retain prior execution behavior. Pure-reflection envelope mapping preserves critique and diffractive audit fields.

## Verification

- Core scheduler/journal/evidence run: 48 passed. Final full research and safe-HTTP regression run: 157 passed in 126.34 seconds. Runs overlap.
- Backend lint passes; all 10 changed Python files pass format checks. Strict mypy passes for six implementation files. Configured mypy checks 63 files and retains the known `keyed_lock.py:13` Task annotation error.
- Tests cover prerequisite rejection before provider spending; finite-patch rejection; narration-only and same-content rejection; new content without a contrary edge; witnessed second pass and third-pass ceiling; no-progress/action ceilings; mapper round-trip; immutable routing decision; restart state; durable acquisition/anchor lineage; expired current witness exclusion with historical retention.
- An older provider-observation fixture entered parsing without candidates; it now supplies valid candidate input. Initial test formatting was corrected before final checks. Review replaced a prose query fingerprint with a typed anchor/contrary projection. V110/V111/V112 already prohibit these failures; no new invariant required.

No live model call was required for deterministic verification. NVIDIA remains selected for live testing/debugging. A Symbia architecture consultation disconnected; saved history supplied partial guidance, not a completed review or approval. Later independent annotation, corpus and human release gates remain pending.
