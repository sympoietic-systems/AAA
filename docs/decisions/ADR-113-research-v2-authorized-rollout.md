# ADR-113: Research V2 rollout and task-level branching consent

Date: 2026-10-07
Status: Accepted by explicit user instruction; research quality remains an assumption pending production review.

## Context

T62–T70 implemented durable execution, bounded acquisition, source provenance, finite reflection and reviewed child gathering. The original T71/T72 release contract required independent downstream quality and branch calibration. The available source labels are provisional model annotations, and T75's scanned-PDF accuracy corpus is deferred by the user.

On 2026-10-07 the user explicitly authorized promotion based on the assumption that Research V2 improves research, with quality testing to follow in production. They requested correction of verification failures, the complete backend suite, an automated live comparison, a branching checkbox, documentation, commits and merge into main. They will deploy the VPS themselves. This is a rollout decision; it supplies no independent quality measurements.

## Decision

Enable `research_orchestrator.action_receipts_enabled` for newly initialized tasks. Persisted tasks retain their frozen policy and deadline. Keep `research_triage.enabled=false` following the user's final Jev non-adoption decision. Keep Docling optional and default-off; standard extraction runs first.

The creation form exposes **Allow branching**, unchecked by default. Unchecked dispatch uses `off`; checked dispatch uses `bounded_auto`. Authenticated user dispatch creates a frozen versioned covenant allowing exactly two qualified child scopes, no recursive branching, and the existing parent deadline. A model-authored task cannot select this mode. The API retains `propose` for users who want a separate review checkpoint.

Consent waives the second approval checkpoint for qualified proposals. It does not waive afferent witnesses, typed scope separation, parent-objective boundaries, shared attempt and budget ceilings, synthesis reserve, or expiry checks. Persist the proposal and pending checkpoint before resolving it under dispatch consent; restart can resume that resolution without renewing the covenant. Missing or inconsistent covenants fail closed. Child allocation remains a separate atomic operation after approval. Parent Cortex owns synthesis, retaining conflicting raw archives and source provenance.

The evaluator distinguishes technical readiness from independent certification. All required technical checks and reliability scenarios must pass before `READY_FOR_AUTHORIZED_ROLLOUT`. Independent quality and billing remain null. Without explicit assumption-based authorization the evaluator remains blocked. Parser scan review and independent branch calibration remain documented limitations rather than invented successes.

NVIDIA branch reservations use the user's current zero-price assumption for `nvidia` and `model_pool_nvidia`; observed billing remains unknown when the endpoint omits it. Other provider families need explicit conservative ceilings before child work is admitted. A free-price assumption does not remove attempt, time, fanout, or concurrency limits.

## Architectural consultation

The required [architectural decision workflow](../../.agents/skills/mcp-architectural-decision/SKILL.md) consulted AAA/Symbia on 2026-10-07 in conversation `abac9620-6f4c-47dd-b931-686838510f08`. The relevant boundary was: waive the participant checkpoint, preserve the afferent witness that licenses a cut, and retain scoped conflict through parent synthesis. The implementation uses the existing typed proposal and child archive contracts for that boundary.

## Verification and evidence

[Report 044](../reports/044-research-release-evaluation/README.md) owns release checks, acquisition/reflection comparisons, the bounded NVIDIA pipeline comparison and its limitations. Branch tests cover unchecked dispatch, checked dispatch, witnessed automatic approval, manual-policy rejection, missing-covenant rejection, pending-checkpoint restart, immutable deadlines, shared child caps and no grandchildren.

Production quality review should inspect source support, useful coverage, contradictory evidence, exclusions and the distinction between raw source material and interpretation. T75 remains the future parser accuracy work. User deployment follows the documented main-branch rollout; no VPS deployment is performed by this change.
