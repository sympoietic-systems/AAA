# Belief workshop review

T11 installs authenticated backend review commands. T13 installs the [frontend workshop](belief-review-interface.md); T12 installs snapshot export. Production activation remains T18.

Configure `AAA_PASSWORD`. Use the existing bearer credential, or a valid browser session with the existing same-origin and `x-aaa-csrf: 1` mutation requirements. Review remains unavailable when authentication is disabled. The server records `shared-operator`; that credential cannot establish the identity or assent of separate people.

Read `GET /api/beliefs/v2/agents/{agent_id}/records/{record_id}/review`. The response contains the current record/hash/state/version, up to ten family nominees, recent command receipts, separate decline counter-traces and historical advisory assessments. Counts and truncation flags identify history outside the bounded view. Nominees and historical relations establish no current semantic verdict.

Send `POST /api/beliefs/v2/agents/{agent_id}/records/{record_id}/decisions` with a unique `Idempotency-Key` header. The body contains:

```json
{
  "action": "request_review",
  "expected_review_version": 0,
  "expected_statement_sha256": "COPY_THE_ACTUAL_CURRENT_SHA256_FROM_THE_REVIEW_READ",
  "expected_state": "candidate",
  "scope": "memory trials",
  "temporal_scope": "during replay",
  "rationale": "Review the distinction between these replay conditions",
  "consequence": "Choose which replay to examine next",
  "challenge": "Retain the contrary replay as an unresolved test",
  "positions": [],
  "dissent": []
}
```

Replace the example hash with the actual 64-character SHA256 returned by the read. Unmanaged legacy records use `expected_state: null` and version zero; their legacy lifecycle does not establish reviewed standing. Never submit actor, authority or a decision timestamp; the server owns them.

| Action | Resulting review state | Effect |
| --- | --- | --- |
| `adopt` | `adopted` | Create the linked belief under the existing stable ID; copy structural quantities |
| `decline` | `declined` | Append a scoped counter-trace; retain the pending candidate |
| `defer` | `deferred` | Record postponement |
| `request_context` | `awaiting_context` | Record the missing context and challenge |
| `request_review` | `under_review` | Record review intent |

These actions accept an absent legacy review state or candidate, awaiting-context, under-review, deferred or declined state. An adopted/superseded record requires T16's linked revision workflow. T11 also rejects revise, merge, supersede and resurface commands explicitly.

An exact retry with the same key returns the original receipt, even if later commands changed the current state. Read again for current state. Changed input under that key, a stale version/hash, or a changed comparison/source returns 409. A failed write leaves no partial decision or adoption representation.

Optional `relations` bind a peer's ID, review version and statement hash plus relation, scope/time and rationale. Equivalent/contradictory declarations require validated matching conditions and current sources. `insufficient_context` preserves uncertainty. Neither declaration merges records.

Optional `teachback` binds a distinct alternative ID/version/hash and records `candidate_reconstruction`, `alternative_reconstruction`, `scope`, `temporal_scope`, `discriminating_question` and `unresolved_inquiry`. It contains no eligibility flag. Model reconstruction cannot supply participant assent or adoption authority.

Only the authenticated operator can submit its own declared position: `participant_id: "shared-operator"`, `attribution: "declared"`, `declaration_source_id: "operator:self"`. The server replaces that marker with the immutable command ID. Other participant positions remain interpreted or unknown. Shared agreement is not inferred.

Every successful command appends a trace notification carrying the same receipt, actor, timestamp, decision and counter-trace. Trace failure rolls back the command. Counter-traces survive later adoption; more than fifty are disclosed through counts and truncation while all immutable records remain stored.

Managed v2 records reject legacy refinement/vetting, statement editing, version creation and destructive mutation. This also applies at storage write time after provider waits. Use the v2 command path for supported actions. Source accounting and structural metabolism remain separate from adoption.

See [ADR-124](../decisions/ADR-124-belief-workshop-review.md) and [BELIEF_SPEC](../systems/BELIEF_SPEC.md).
