# Report 039: Approved research children

Date: 2026-10-06. Task: T68. Branch: `codex/research-v2`.

Approved proposals now enter a registered `branch_gathering` action under frozen policy version 7. The repository allocates exactly two deterministic child task IDs from the reviewed scopes in one transaction. Each child has its own contract, evidence ledger, fixed attempt allocation and monetary allocation. Both inherit the original parent deadline. Children execute search, parse and digest sequentially; they cannot create grandchildren, consolidate, synthesize or write findings into shared beliefs.

## Resource contract

Provider reservation checks the child allocation and the whole task family atomically. Child calls cannot consume the parent's verification/synthesis reserve; unfinished child allocations remain protected from parent spending. Unused capacity never increases a sibling's allocation. Cancellation revokes child authority before late delivery. Restart preserves allocations and completed archives; interrupted running work requires explicit recovery rather than automatic replay.

A family provider call requires a per-call monetary ceiling declared before task initialization in `research_orchestrator.branch_provider_cost_ceilings_usd`, keyed by the actual leaf provider name. Missing ceilings reject the call before dispatch. Reservations count conservatively even when billing metadata is absent. Observed `known_cost_usd` stays nullable. A reported cost above its declared ceiling produces a partial receipt with `declared_cost_ceiling_exceeded`. These configured ceilings are an operator/provider contract; an external billing change cannot be physically prevented by the application. No default zero price is inferred from missing telemetry. Explicit free-provider terms may support a zero reservation without converting unknown observed billing into zero.

## Evidence and merge

Immutable child archives retain complete source representations, exact spans, source/version identities, claim-support and contrary edges, parser limitations, decision exclusions and unresolved objections. Parent action observations link child IDs and packet hashes. JSON export/import and Markdown provenance appendices preserve child archives as read-only evidence, with no imported execution authority. Uncommitted child snapshots remain explicitly partial/cancelled/failed.

The parent Cortex receives an attributed, bounded prompt view of both scopes and their validation norms. Shared URL/content groups are marked as dependent evidence. Contrary claims and exclusions remain in the archives; gathering does not certify semantic support. Cached previews cannot hide newly gathered child evidence. Repeating gathering reuses the same archives without spending again or appending duplicate interpretations.

Acquisition caching is now scoped by task while retaining shared clients, provider gates and global worker bounds. Siblings therefore cannot inherit each other's cache receipt authority. Fresh observations of unchanged text receive distinct source versions; representation hashes still expose content equivalence. Cache hits retain the original observation/version.

## Verification

- Final integrated research and safe HTTP suite: **181 passed in 179.34 seconds**.
- Eleven child-specific tests cover approval/capability gates, deterministic allocation, shared attempts and monetary caps, parent reserve, raw evidence through failure, cancellation/stale delivery, restart refusal, idempotent merge, task cache isolation, unchanged-content refetch and parent Cortex prompt ownership.
- Focused strict mypy: nine affected modules passed. Configured mypy checks 71 modules and retains the previously documented `keyed_lock.py:13` generic `asyncio.Task` error.
- Backend Ruff passed; 25 affected Python files passed format verification. No frontend code changed in T68; T67's frontend checks remain recorded in Report 038.
- All migrations/tests used isolated databases. No production migration, live branch performance comparison, independent branch calibration or release approval is claimed.

T69 still needs independent labels and downstream review. T70 needs a frozen parser/OCR corpus. T71 release quality and T72 automatic branching remain gated by those evaluations.
