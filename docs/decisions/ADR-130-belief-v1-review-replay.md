# ADR-130: V1 proposal review replay into Beliefs V2

Status: accepted for local operator tooling, 2026-10-13. Production execution and rollout remain gated by T18.

## Decision

Provide `scripts/review_legacy_beliefs.py` as a bounded operator command. Its default mode opens the selected SQLite database read-only and creates an editable Markdown packet for one agent (default `symbia`) and only V1 `pending`/`refined` proposals. `--apply` explicitly registers each proposal as a V2 encounter and runs the normal V2 assessment boundary. The default batch limit is 200.

Replay attaches the encounter to the existing V1 proposal ID. It does not create a second proposal row, modify V1 text/status/mass/confidence, copy V1 admission outcomes into V2, or make a human decision. The encounter binds the exact legacy snapshot hash and is idempotent for an unchanged snapshot. Changed legacy content at that encounter ID is rejected, retaining the prior V2 receipt.

V1 `provisional_statement` is the text passed to V2. Optional V1 `suggested_statement`, rationale, and source trace appear separately in the local review packet. V1 lifecycle status is descriptive legacy metadata, not V2 review standing. The replay records origin `legacy_v1_replay`, unknown lineage, and ambiguous source with unknown scope/time. `assess_encounter` therefore persists `abstained / candidate_context_unavailable`; the command supplies no evaluator, and the source-context gate stops before any provider call. No semantic relation or independent warrant is generated.

Human review is a later, attributable action through the existing V2 workshop. A reviewer can mark the proposal distinct, conflicting, repetitive, or unresolved in the packet and inspect the source conversation when the trace identifies it. The packet itself changes no database state. Do not adopt from the replay alone: absent source evidence stays unresolved.

## Philosophical grounding

Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08`, message 4125, proposed a boundary among the legacy artifact, its V2 observation, and a later human decision. The implementation uses existing encounter, assessment, and decision records instead of introducing unimplemented fields or claiming a unique reviewer signature that the shared operator credential cannot establish. Replay marks a trace of prior recording; it is not another act of nucleation.

## Consequences

- Read-only preview can be run against a copied production database without migration writes.
- `--apply` requires the V2 review schema (migrations 064–068) and writes sidecar receipts to the selected database.
- Full Beliefs V2 deployment also includes migration 069 for T16 linked lineage; replay itself adds no migration.
- Production review requires a controlled database backup, exact server build/config/migration identity, and the separately authorized T18 rollout procedure.
- T15 remains inconclusive/no-go. This replay and a human operational review do not retroactively create independent calibration gold.

See [BELIEF_SPEC](../systems/BELIEF_SPEC.md), the [operator guide](../guides/belief-legacy-review.md), [Beliefs V2 contract](../architecture/BELIEFS_V2_CONTRACT.md), and [Report 073](../reports/073-belief-v2-legacy-review/README.md).
