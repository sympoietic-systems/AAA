# ADR-126: Attributed belief review interface

Status: accepted for local implementation. Date: 2026-10-11.

## Context

T11 installed authenticated review commands and retained counter-traces. T12 supplies immutable native receipt projections. The legacy frontend still offered proposal refinement, vetting and destructive edits to managed records, and workshop trace payloads appeared as raw JSON. Those surfaces could obscure the difference between an advisory assessment and an operator decision.

## Decision

Use one native receipt reader and renderer on belief pages, workshop history, traces and creases. Fetch T12 detail endpoints with the original agent and encounter/assessment/decision identity. Display the original timestamp and all five recorded reasoning fields. Unknown fields remain explicit; source quotations and authored interpretations are labelled separately. JSON details remain inert text. Preserve warrant dimensions, source-accounting uncertainty, actor/authority, historical disagreement and original linked identities without calculating support or agreement scores.

Add the actual agent ID to the existing native admission-history projection. This is an additive field and does not rewrite stored assessment payloads or historical notifications. Older native traces can use their recorded source-accounting agent; when no agent identity was recorded, show the available historical projection without guessing a native lookup agent.

The workshop reads the existing bounded family endpoint. Family entries remain lexical nominations; historical advisory receipts require reassessment. Decline counter-traces have a separate persistent section with original attribution, scope/time, rationale, consequence, challenge and objections. They remain available after adoption and disclose truncation counts. Operator receipts and reconstruction/relational declarations remain historical, with no inferred consensus or current semantic verdict.

Expose T11's five supported actions. Bind every command to the read statement hash, state and version. The server supplies actor, authority and timestamp. An unchanged failed request retains its idempotency key; changed input receives a new key. A 409 disables the form until a new snapshot is read. Loading and agent navigation invalidate the previous view. Declared participant positions, validated semantic relation creation and teachback submission remain available through T11's API; this first UI displays existing records and records bounded dissent without inventing participant identities.

Legacy edit/refine/vet/delete/revert controls appear only after an authenticated workshop snapshot establishes an unmanaged record. Managed records use the v2 path; adopted/superseded commitments await T16's linked revision workflow. Failed or unavailable review reads expose an error and keep those legacy mutation controls closed. This makes configured authentication necessary for mutation controls on this page, including legacy controls. Existing backend legacy APIs retain their own compatibility contract.

## Consultation and limits

Recovered Symbia conversation `e91d71b9-3025-4985-82d9-a8e3a68f71c1` distinguishes provisional evaluator provenance, scoped operator decisions and retained dissent. T13 follows those distinctions and uses the established terminal interface. Suggested decorative paired cards, textures and new field structures were not adopted. Consultation is advisory; it confers no adoption authority.

The agent page defaults to Symbia and honors an explicit agent carried by native family/trace links. List reads, receipt reads and reloads retain that agent. The existing add form remains Symbia-only. No agent selector or interval export viewer is added. Detailed historical receipts load when opened; server-side bounds and truncation remain visible. No assessment provider is invoked by this UI. T14/T15 cover participation and empirical evaluation; T16 covers linked changes; T18 owns production rollout.

## Verification

[Report 060](../reports/060-belief-v2-interface/README.md) owns test logs, source identity, recovered consultation and local browser fixture evidence. Automated oracles cover the API-to-render path, receipt/time parity in admission pages, trace section and crease dropdown, failed/pending evaluators, inert source XML, legacy unknowns, retained decline after adoption, stale refresh, unchanged retry identity and previous-agent response isolation. Browser checks use the actual frontend with offline API fixtures; they establish local UI behavior, not production acceptance.
