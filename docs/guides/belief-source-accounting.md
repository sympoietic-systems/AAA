# Belief source accounting

T10 records source lineage, internal activity and recurrence separately. [ADR-123](../decisions/ADR-123-belief-source-accounting.md) defines the boundary; [BELIEF_SPEC](../systems/BELIEF_SPEC.md) owns status.

Migration 066 creates forward observation/event tables without modifying historical events or encounters. New v2 encounter registration writes its observation atomically. Origin flags retain their existing default-off behavior and durable promotion/pause semantics. Legacy creators remain outside this ledger. No independent-support certification path, background worker or new public route is installed.

Use `BeliefLineageStore.observation(agent_id, encounter_id)` for the exact source snapshot, `summary(agent_id, record_id, limit)` for recorded counters and uncertainty, and `events(agent_id, record_id, limit)` for typed forward events. Reads validate identifiers, enforce agent ownership and clamp limits to 1–50. Summary observations are a bounded recent page; `truncated` identifies partial display. HTTP authorization and complete-interval export remain T11/T12.

The admission page/history and received/assessed trace receipts carry `source_accounting`. A null value means the encounter predates ledger coverage; it must not become fabricated zero support. Summary `historical_unrecorded_encounters` identifies that gap. Observed counts describe only covered v2 encounters. Independent warrant remains unverified, including for a source carrying a declared `independent` label. Known parent roots have shared grouping keys; these represent declared local ancestry, not authenticated upstream independence.

`internal_activity` counts covered encounters with an internal contribution. `recurrence` counts subsequent covered encounters of the same scoped claim. Retry and Jev reassessment add neither. A first post-migration observation has no recorded recurrence even if older encounters exist. Different scope/time does not become the same claim through accounting.

Events have unit `encounter_observation` and value one, with separate source-lineage/internal-activity/recurrence quantities. Zero mass/confidence deltas apply to accounting itself; legacy accretion events remain separate. No event grants adoption or evidential credit. Unknown ancestry, cycles, missing sources and grouping overflow remain visible. [Report 057](../reports/057-belief-v2-source-accounting/README.md) preserves local checks and consultation provenance.
