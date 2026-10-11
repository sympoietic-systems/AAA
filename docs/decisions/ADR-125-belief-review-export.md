# ADR-125: Snapshot-bound belief review exports

Status: accepted for local implementation. Date: 2026-10-11.

## Context

T12 needs authenticated interval reads of encounters, completed assessment receipts, decisions and events. Pagination must preserve the rows visible on the first page even when a later event has an earlier timestamp. An assessment's admission row is created while evaluation is pending; completion changes that row without assigning a new row ID. Legacy events and legacy admission receipts can also change through existing lifecycle operations.

## Decision

Install the reserved GET routes under `/api/beliefs/v2/agents/{agent_id}`. Use the existing bearer/browser-session authentication and require configured authentication. The shared operator credential permits agent selection; it establishes no separate participant identity or private tenancy. Validate each selected agent and use agent predicates in every payload query. Native detail reads return 404 for another agent's ID.

Normalize aware interval boundaries to UTC and preserve microsecond precision. `to` is exclusive. Keysets order by normalized timestamp and a namespaced export ID, preserving the original receipt/event ID separately. A first-page SQLite read transaction captures append watermarks and the database identity. An HMAC cursor binds that snapshot, agent, resource, normalized interval, limit and last key. The signing key derives from the configured operator credential with a purpose-specific HMAC; restarting the service preserves cursors, while credential rotation invalidates them.

Migration 068 adds a completion sequence referencing the existing admission ledger, without copying receipt payloads. The reference has no deleting foreign key: legacy receipt deletion remains compatible and invalidates affected exports. Existing complete receipts receive an `existing_receipt` index origin; this is migration inventory, not reconstructed history. Forward completion indexes atomically with the existing admission transaction. Pending assessments remain individually readable and explicitly absent from immutable completed-receipt exports.

The same migration adds a database identity and a conservative legacy generation counter. Editing/deleting a legacy event or completed legacy receipt, or changing/deleting a legacy record's ownership, invalidates subsequent event/assessment pages with a 409. Append operations retain their original behavior; append watermarks exclude later rows, including backdated rows. Native immutable ledgers remain authoritative. Metadata contains no second decision or receipt payload ledger.

Responses project encounter, claim/tension, comparison, consequence/challenge and decision/uncertainty from stored records. Linked evaluator receipts and operator decisions retain their original identities, timestamps, attribution and dissent. Missing reasoning is null with an explicit unknown-field list. Linked T10 source-accounting observations retain recurrence, ancestry grouping and independence uncertainty; missing historical observations remain unknown. Decision projections inspect at most ten assessment links and label further links truncated; the original decision retains its complete bounded link list. Legacy model recommendations remain advisory. Export code exposes no evaluator, adoption or mutation port and always reports `tool_authority=none`.

## Limits and consequences

Page size is 1–50, default 25. Stored JSON payloads or aggregate legacy stored fields over 256 KB fail visibly before transport into Python; legacy JSON escaping can expand the transport representation. Projection pages over 2 MB fail with 503 before response-model metadata. SQLite reads use a three-second progress budget; projection has a ten-second aggregate budget checked between bounded reads. Date normalization can require scanning stored rows, so unusually large histories can return a resource-budget failure. These budgets are inspection defaults, not production capacity evidence.

`interval_complete` means all stored, dated, agent-attributable rows in this resource's snapshot interval have been traversed. It requires cursor exhaustion and no undated rows; it gives no claim about unrecorded history, pending assessments, source independence or belief warrant. Undated legacy rows remain stored and make coverage incomplete. Legacy generic impact retains its compatibility alias; measured confidence/mass deltas remain nullable and are never inferred from generic impact. Known secrets are masked at the response boundary without rewriting stored hashes or receipts, with `content_redacted` marking the projection.

Symbia consultation `d343b54f-0f9c-4542-bf7b-fde4e4015073` emphasized the separation between recording integrity and situated warrant. Its proposed new human-reckoning schema is outside the frozen T12 plan. The existing operator decision boundary and the export's lack of mutation authority implement that separation here. Consultation text is advisory evidence, not an instruction or an adoption receipt.

## Verification

See [Report 059](../reports/059-belief-v2-export/README.md) for source-bound test receipts, consultation and limitations. Regression oracles cover tied timestamps, later backdated insertion, pending-to-complete races, cursor binding/tampering/credential rotation, exact UTC boundaries, legacy mutation, secret masking, linked reasoning, independent agent reads, completion rollback and resource budgets. T13 owns dedicated UI integration; T18 owns production rollout.
