# Reviewing beliefs in the frontend

Open **Agent → Personality → Beliefs**, then select a candidate or belief. Native admission reasoning reads the original encounter or assessment receipt. Each receipt shows its identity, UTC timestamp and five fields: encounter/source, claim/tension, comparison, consequence/challenge and decision/uncertainty. Expand the recorded details to inspect hashes, lineage, warrant dimensions and linked identities. Missing historical fields remain unknown.

The scoped workshop displays review standing separately from the legacy lifecycle. Source quotation and authored claim are separate. A provisional evaluator recommendation does not establish adoption. Evaluator failures, pending work, abstention and unavailable receipts remain visible; retry a failed receipt read without creating a new assessment.

Family review shows up to ten lexical nominations from a bounded scan. These entries imply no equivalence, corroboration or merge verdict. Historical assessment receipts require reassessment before binding a new decision. The UI does not attach them automatically.

For an eligible record, select request review, request context, defer, decline or adopt. Supply scope, rationale, consequence and challenge; time scope and an unresolved objection are optional. **Record decision** uses the current statement hash, state and review version. The server records its shared operator actor and UTC time. That credential does not establish separate participant identity or bilateral agreement.

If a connection fails, retry unchanged fields to recover the same idempotent command. Changed fields create a new command identity. A version/source conflict disables the form: use **refresh changed record**, inspect the newly read state, then decide again. The previous form is unavailable while the read is pending. Existing adopted/superseded commitments await T16's linked revision interface.

Decline retains the candidate and its counter-trace. The persistent counter-trace section shows attribution, scope/time, rationale, consequence, challenge and recorded objections even after later adoption. Counts and truncation identify older stored history outside the bounded display. Open operator receipts to inspect the original decision and any historical relation or teachback declaration. The first UI does not submit participant declarations, validated pair relations or teachback; the authenticated [T11 API](belief-workshop-review.md) retains those capabilities.

**Traces** and **creases → traces** recognize workshop receipts and admission receipts. Expand the receipt and load its recorded reasoning to see the same T12 receipt identity and timestamp as the belief/workshop view. Raw quotations and historical emission tags are displayed as text. The link opens the belief workshop.

Configured authentication is required for the v2 workshop and exports. Legacy mutation controls are shown only after a successful review read establishes an unmanaged record; a failed read keeps them closed. Existing unrecorded history is preserved and receives no invented provenance or review standing. The agent page defaults to Symbia. Native family/trace deep links carry an explicit agent through list reads, receipt reads and reloads; the existing add form remains Symbia-only.

Implementation status is maintained in [BELIEF_SPEC](../systems/BELIEF_SPEC.md). [ADR-126](../decisions/ADR-126-belief-review-interface.md) records the presentation and command boundary. Local verification evidence is in [Report 060](../reports/060-belief-v2-interface/README.md); production rollout is T18.
