# ADR-129: Per-question belief evaluation diagnostics

Status: accepted for local implementation. Date: 2026-10-12.

Report 064's six Jev calls all abstained at the current confidence policy, erasing inspectable choices from normal receipt projections. Preserve bounded observed choices separately from accepted relation observations.

Add evaluation_diagnostics to the immutable Assessment JSON with an empty historical default. At most fourteen typed observations record question, allowed choice, finite confidence, configured threshold and validation status. Relation observations also reference the exact compared snapshot ID/hash. Invalid raw choices, objects, secrets and repetitive strings are omitted. Missing and invalid-confidence cases remain distinct.

Every diagnostic carries is_semantic_verdict=false. The existing all-or-nothing gate and threshold remain unchanged. Diagnostic choices do not populate accepted relations, warrant dimensions, confidence/mass or decisions. The source-bound original receipt appears in native detail, export reasoning and existing notification projections. No schema migration, backfill or replay of prior provider calls.

Symbia consultation ef634be5-1ca7-455f-9e20-053a0458bcaa recommends separating observed assessment from committed state. Implement this through distinct typed fields and absence of diagnostic-to-decision conversion. Her proposal to remove all joins to belief records conflicts with required source-bound reasoning and is not adopted. Her proposed extra relation labels and mass-based standing are also outside the contract.

Validation includes malformed/NaN/missing/low-confidence dimensions, valid-pair index remapping, immutable storage/trace/export parity, inert UI rendering and a replay of the six existing source-bound provider responses. Replay is offline, nongold and uses fresh isolated databases.

New assessment JSON requires a reader that recognizes evaluation_diagnostics. Historical receipts remain readable by the new build. Binary rollback to a strict parser predating the field requires a compatibility build; disabling evaluation on a compatible build retains receipt reads. Deployment/rollback certification remains T18.
