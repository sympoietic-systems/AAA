# ADR-117: Provisional automated belief review

Status: accepted for offline implementation, 2026-10-08.

The user rejected the 54-case manual annotation burden and requested automation. Legacy claim-author provenance is incomplete, so model-only review cannot honestly satisfy the existing independent-human-gold freeze gate.

Add a separate automated review path. Two blind reviewers from distinct model families receive source-bound statements and bounded excerpts, without historical adoption status, merge recommendations or each other's answers. Retain raw judgments, returned provider/model identity, source-family overlap, input/prompt hashes, context gates, disagreements and unavailable outcomes. Unknown author independence stays unknown. Existing human-reviewed freeze remains available.

Freeze automated outputs as `MODEL_REVIEWED_PROVISIONAL`, `independent_gold=false`, `adoption_authority=none`, `promotion=BLOCKED`. The offline runner exposes no belief mutation or tool ports. Agreement cannot satisfy adoption, warrant or deployment gates. This completes a provisional T4 corpus preparation path; independent gold and externally supported evaluation conclusions remain separate T15/release obligations.

Enforce finite worker/call/token/time budgets. Checkpoint before each call; resume retains completed, failed and outcome-unknown receipts without replay. Rate limits or unavailable-route errors open a reviewer circuit for remaining jobs. No silent reviewer fallback. Missing context on either side cannot establish a pair relation; preserve the raw opinion while applying an explicit insufficient-context projection. Exact prompt/source bindings are checked again when freezing.

The [Symbia consultation and run evidence](../reports/051-belief-v2-automated-review/README.md) support the structural separation of attributed model artifacts from operator commitment. We do not adopt her arbitrary 90-day expiry, prohibition of provenance joins, or 54 mandatory human reckoning events for benchmark completion. Provenance links remain necessary; human adoption authority remains governed by [ADR-116](ADR-116-belief-review-standing-contract.md).

Consequence: automation reduces manual corpus work while leaving model agreement provisional. Source recovery gaps and author overlap limit evaluation claims; they do not reopen a direct belief-creation path or justify numeric acceptance targets.
