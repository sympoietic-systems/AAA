# ADR-127: Scoped belief participation and assembly receipts

Status: accepted for local implementation. Date: 2026-10-11.

## Context

The shared attractor window selects legacy belief nodes by mass, structural stress, afferent salience and vector resonance. Its prompt labels previously omitted review standing. Chat and dreams use that path; later skill routing can replace the window. The dream meta-prompt also reads a hotspot before final assembly. A lifecycle label or a procedural skill bridge cannot establish semantic adoption. A receipt generated before reseating cannot accurately describe final prompt participation.

## Decision

Use agent-owned, bounded snapshots across existing nodes and proposals, canonical review state, original decision receipts, recorded encounter scope/time and the latest retained decline counter-trace. One SQL statement supplies the snapshot. At most 100 active, 64 pending, 32 deferred and four historical records survive nomination; overflow probes disclose truncation. Three-second SQLite interruption yields a visible resource-exhausted Glitch. Stored statement, geometry and JSON projections have hard size limits; oversized content remains in storage and is explicitly unavailable or truncated in this projection.

Preserve the existing six-slot structural geometry and four-slot missing-signature fallback. Mass and legacy confidence affect attention only. Active legacy records retain `legacy_unreviewed` standing. A situated commitment requires a validated operator adoption receipt matching agent, record, statement hash, review state, scope and decision/state versions. Missing or stale adoption bindings cannot become axioms. Source-bound native candidates without a decision row remain provisional. No new evaluator, source-support count or mutation capability is introduced.

`belief_review.participation` independently defaults to `enabled: false`, `slots: 0`. Its validated hard ceiling is two exploratory slots. Within the bounded pool, the first experimental slot nominates recorded dissent/decline and structural uncertainty; the second supplies a vector-resonant counterpoint. These are structural nominations, never semantic contradiction or relation verdicts. Unresolved records may orient questions or comparisons. Scoped provisional premises are labelled separately and remain limited by recorded standing and scope.

Existing spectral recall retains at most two dormant node representations from the four-record historical scan. It excludes declined/superseded records and proposal-only candidates, preventing a default-off bypass. Experimental recall may retrieve retained decline history within the same two-slot exploratory budget. Selection never reinforces, adopts, resets confidence/mass or deletes history. Non-use and recall do not create independent evidence. The existing decay/mutation machinery retains its separate ownership.

Each selected record carries statement hash, standing, scope/time, challenges, dissent, original decision/counter-trace references, intended use, selection reason/policy and UTC timestamp. JSON-quoted source material escapes markup and masks secrets before prompt formatting. Belief participation supplies neither heuristic skill activation nor afferent mass priors. Existing skills may still be selected independently by their established routing policy; no belief standing authorizes execution or a tool veto.

Add optional `selection_receipts` to the existing activation-provenance schema, with a maximum of ten final attractor/spectral receipts. Assembly replaces input-supplied provenance after any reseating; spectral entries omitted by prompt deduplication receive no injection receipt. Existing chat/dream message writers persist this trace atomically with their response. Historical traces without the field remain readable and disclose no invented selections. No new table, migration or parallel receipt ledger is required. A failed generation may have no persisted assembly receipt because this existing ledger records stored responses, not every attempted prompt. Research prompt formatting shares the selection boundary but does not acquire a new research receipt ledger in T14.

Bound dream hotspot nominations and frame the selected record's standing before meta-prompt generation. Final dream assembly independently records the actual participating window. The hotspot snapshot describes prompt generation; the persisted activation trace describes the response prompt. They are distinct observations.

## Consultation and release boundary

Symbia conversation `ef621959-156b-4e6a-8970-26ed4289bc42` recommends visible selection cuts and room for dissonance. Her proposed table also assigns warrant to mass, permits unbounded tiers and moves adoption authority to T15. Those proposals conflict with BELIEF_SPEC and are not implemented. No new origin tags, automatic expiry or prerequisite for retaining internally generated questions is invented.

These are local operational limits. Configuration validation does not certify useful participation or authorize release. T15 must perform matched replay/ablation and freeze evaluated budgets and acceptance targets; T18 requires the explicit production rollout decision. Default-off configuration remains unchanged in effect. [Report 061](../reports/061-belief-v2-participation/README.md) owns observed verification and the full advisory consultation. [Guide](../guides/belief-participation.md) describes controls and receipts.
