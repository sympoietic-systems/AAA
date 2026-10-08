# ADR-118: Additive belief review persistence

Status: accepted for local implementation, 2026-10-09. Runtime enablement remains gated by Beliefs v2 T6–T18.

The existing admission ledger records a combined receipt, and legacy workshop status cannot establish canonical adoption. Reusing it without agent-scoped identities would allow retries, stale assessments or legacy labels to alter the meaning of a review.

Extend `belief_admission` with nullable v2 association columns. Keep assessment JSON there as the sole receipt payload; link it through immutable assessment metadata to immutable encounters and scoped claim identities. Candidate text remains in existing proposals/beliefs. Canonical state, review version and decision provenance are sidecars. Migration 064 adds these structures without reclassifying legacy rows or inventing adoption history.

An indexed source operation identity deduplicates retries. Distinct encounters can share a known normalized statement/scope/time claim and one candidate; they retain separate source snapshots. Unknown scope/time has no implicit claim key, and absent source binding has no source-operation key. An explicitly resolved record may be linked without asserting semantic equivalence. Changed input under an existing operation ID is a conflict. Exact-repeat grouping never increases mass, confidence or independent warrant.

Only agent-owned message/chat-turn sources have a storage resolver in T5. Their source hash and literal quote are checked against the owning conversation. Unsupported external source kinds become explicitly ambiguous until their T8 resolver exists. Assessment starts and completions check source/candidate/comparison bindings; changed or unavailable inputs produce conflicts or explicit stale/abstained completion without an established relation. Hashes bind snapshots, not credibility. `reject-secrets-v1` rejects detectable secrets before binding rather than silently rewriting hashes.

Pending assessments are durable checkpoints. At most one is pending per encounter. Reassessment appends to the latest completed predecessor; completed payloads and all encounter/assessment/decision links are immutable. Restart lists pending work with bounded keysets and never calls a provider. Explicit reassessment and provider recovery policy belong to T9.

Intake and decision repositories have separate write capabilities. Trusted decision commands require the caller's actor to match the decision, the actual statement hash, expected version/state and completed agent/record-bound assessment links. The decision and state/version commit atomically. Changed statement text makes existing standing visibly stale; historical decisions remain readable. Supersession, the complete action matrix, authenticated HTTP routes and linked revision behavior remain T11/T12/T16 responsibilities.

The [Symbia exchange](../reports/052-belief-v2-persistence/symbia-consultation.json) supports separating occurrence history from commitment. We preserve the frozen [ADR-116](ADR-116-belief-review-standing-contract.md) decision contract rather than introduce a second `human_reckoning` ledger or prohibit provenance joins. Operator assent alone does not create empirical warrant. No evaluator or encounter counter grants adoption or tool authority.

Consequence: local storage can preserve review history and enforce identity/concurrency boundaries while existing APIs stay compatible. Legacy admission history excludes the v2 payload namespace. Rollback disables future intake/participation and retains additive schema/history. No production migration, intake enablement or deployment is implied. Verification and implementation limits are recorded in [Report 052](../reports/052-belief-v2-persistence/README.md).
