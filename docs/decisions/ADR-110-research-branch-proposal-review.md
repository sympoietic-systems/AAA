# ADR 110: Human Branch Proposal Review

Date: 2026-10-06. Status: accepted for opt-in implementation.

Freeze `off|propose` per task, default `off`; explicit `propose` activates durable evidence receipts. A registered post-afferent inspection can propose exactly two source-backed scopes. Require typed vocabulary/validation differences, anchored witnesses, overlap, risk and shared resource allocations. These are reviewable proposals, not automatic findings of incommensurability. Reject coupled relational questions and unbounded fields. Bounded automatic branching remains unavailable.

Persist proposal/action linkage and the waiting checkpoint together. Waiting starts no child and spends no provider budget. Expose exact witness text, version and extraction warnings. Approval requires an operator acknowledgement that both edited scopes remain within the parent objective. Recheck resource ceilings and current witness eligibility; preserve at least eight parent provider attempts and the original deadline. Resolution is immutable and idempotent for identical requests. One proposal per parent bounds repeated review loops.

Decline and expiry resume the stored parent phase. Expiry beyond the original deadline ends partial. Cancellation archives the pending proposal without child work. An application-owned bounded expiry worker restores from durable waiting tasks and closes on shutdown. UI requests belong to keyed task/status generations; stale completions cannot update another task.

API: GET `/research/tasks/{task_id}/branch-proposal`; POST `/research/tasks/{task_id}/branch-proposals/{proposal_id}/approve` with optional two edited scopes and `boundary_acknowledged`; POST sibling `/decline`. Conflicts return 409; typed field violations return validation errors. T68 implements approved child execution. [Report 038](../reports/038-research-branch-proposals/README.md) owns verification. The prior recovered partial Symbia guidance remains design input; no completed external review is claimed.
