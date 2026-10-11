# ADR-128: Incomplete belief recurrence display

Status: accepted for local implementation. Date: 2026-10-12.

Report 064 showed that incomplete exact recurrences create separate pending proposals. Missing scope and time cannot establish semantic equivalence. Preserve the storage identities and group the review presentation only.

Add optional recurrence_group metadata to existing proposal list projections. Restrict grouping to current awaiting_context records with exact text and absent scope, time, quotation and consequence. Require agent-owned message/source hashes, one conversation and mutually comparable ancestry. Sibling branches remain separate. A bounded read examines at most 50 eligible entries and 128 ancestry steps; incomplete/cyclic ancestry leaves the entry separate. Metadata reports scan coverage.

All proposal, encounter, assessment, event and decision records remain unchanged. Group counts describe entries in the current queue. Expanding exposes every original entry and detail link, including selected deep-linked members. Review/adoption, enriched context, changed source and revised statement exclude grouping. No migration, backfill, semantic merge, mass/confidence adjustment or evaluator request.

Symbia consultation 920fd1cd-7a63-4fee-8d29-8e3d626502e8 warns that multiplicity can resemble corroboration. Use plain labels: repeated fragment, context incomplete, occurrences add no independent support. Her suggestion that all recurrences share provenance is not assumed; only the recorded ancestry relation is verified.

Adversarial checks: a common root does not prove one branch; compare each member against every peer. Latest evidence must not be hidden by older missing-context receipts. Source hash and current state checks prevent stale UI metadata. Unknown ancestry never supplies grouping authority. Production enablement/deployment remains a separate decision.
