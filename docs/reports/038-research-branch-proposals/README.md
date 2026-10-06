# Report 038: T67 Human Branch Proposals

Date: 2026-10-06. Scope: policy v6; default subresearch policy `off`.

Explicit per-task `propose` opts into the evidence/receipt substrate. A post-afferent inspection action may submit exactly two scopes with retrieval vocabularies, validation requirements, source-segment witnesses, overlap, risk and resource allocations. Coupled relational questions are rejected. Different labels alone establish no semantic warrant: the operator sees exact source quotations and must acknowledge review within the immutable parent objective.

The proposal checkpoint atomically enters `waiting_for_branch_approval`. Waiting executes no provider or child work and releases automatic execution capacity. Review may approve edited scopes, decline or expire. Approval preserves the parent contract, deadline and at least eight reserved parent provider attempts; allocations cannot exceed remaining attempts or the frozen monetary ceiling. Expired current witnesses block approval. Decline and expiry resume one parent line; expiry beyond the original task deadline ends partial. Pending proposal and action identities survive restart. Duplicate decisions are idempotent; conflicting decisions and edited re-approval fail.

The API exposes source/version, exact transformed-text spans and extraction warnings. The panel requires explicit review acknowledgement, allows scope/allocation editing, reports conflicts and owns async requests by task/status. New task mode defaults to one research line. No child is created by this task, including after approval; T68 owns execution.

## Verification

- Initial proposal tests: 8 passed. Expanded API/expiry-worker run: 11 passed. Full research/HTTP regression run: 169 passed in 155.57 seconds. Final proposal/receipt guards: 26 passed. Final per-task opt-in, journal and restart run: 53 passed in 78.96 seconds. Counts overlap.
- All 129 frontend tests pass; final four proposal UI tests pass after vocabulary editing changes. Production build passes. Scoped lint for the new panel/test passes. Global frontend lint retains the same 16 pre-existing NodeExplorer no-explicit-any errors documented in Report 034.
- Backend lint passes. All changed Python files were format checked; strict mypy passes for eight implementation files. Configured mypy checks 68 files and retains the known `keyed_lock.py:13` Task annotation error.
- Tests cover durable waiting without child creation, default-off behavior, edited/idempotent approval, required acknowledgement, conflicting decisions, reserved capacity, decline, expiry before/after deadline, exact witness API, automatic-mode pause, expiry-worker restart, cancellation, per-task opt-in with existing document context, stale UI completion, terminal-parent controls and editable retrieval vocabulary.

## Corrections

Restore persisted phase during initialization so approval/expiry resumes the intended parent action. A trusted new task's explicit proposal opt-in can freeze its policy alongside existing context; imported/default-off legacy state gains no execution authority. Resume the expiry worker from durable waiting tasks even when global defaults are off. UI tests require explicit DOM cleanup; keyed ownership replaces effect-time state resets. Preserve raw vocabulary input while editing so a trailing comma remains typeable. Record proposal linkage in terminal action observations and distinguish current waiting phase from the eventual resume phase.

All fixtures are synthetic mechanical tests. They are not independent labels or evidence for branch-quality promotion. No live model call was needed; NVIDIA remains the selected provider for live testing/debugging. Human calibration, corpus and release gates remain subsequent work.
