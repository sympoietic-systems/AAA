# ADR-115: Source-bound shadow admission for explicit belief candidates

Date: 2026-10-08
Status: Accepted for implementation; production migration and runtime behavior not verified

## Context

Explicit `<belief_nucleate>` tags could create pending belief proposals without checking whether their claims were grounded, consequential, or repetitive. Dream turns also needed to use the same route as chat. A proposal list alone did not show what source caused a candidate, what comparisons were made, or when the assessment completed.

The user's decision is to nucleate beliefs only when an emission contains a meaningful new insight or conflict, expose the assessment reasoning on the belief page, and record the assessment in Creases/Traces. Existing production sediment must remain untouched, and human adoption remains the mutation boundary.

## Decision

Route parsed explicit tags from chat and dream through one source-bound admission service. Require the candidate to identify a concrete trigger, source quote, scope, temporal scope, and consequence. A missing field, quote mismatch, or unresolved referent produces a visible review state.

Persist one receipt per source emission in `belief_admission`. Include stable source IDs and hashes, the original-tag hash, a bounded set of up to ten belief/proposal comparisons and their hashes, evaluation answers/confidences, evaluator state/model, policy version, decision, and UTC timestamps. Use a deterministic event key for retries. Recheck exact statement/scope/time matches under the database writer transaction; record exact repeats against their existing target rather than creating a second proposal.

Evaluation remains shadow-only. Jev may provide an advisory assessment, but it cannot create, adopt, merge, or reject beliefs. Unavailable, uncertain, stale, or incomplete assessments remain visible for human review. Manual adoption retains the existing scoring and lifecycle path. Historical proposals without receipts are reported as having unavailable admission reasoning; no retroactive classification is inferred.

Create a received and an assessed Creases/Traces entry for each receipt. Render the same receipt in belief details with source links and expandable comparison/assessment reasoning. Mask secrets in persisted receipt and trace representations.

This gate covers explicit XML emissions. Legacy passive concept-density nucleation and any other non-tagged nucleation path keep their existing behavior, so deployment of this gate alone does not establish a system-wide nucleation-rate change.

## Consequences

- Explicit candidate emissions are separately visible before human adoption and can be distinguished from crystallized beliefs.
- Repeated exact claims remain auditable as occurrences without growing the proposal queue.
- The evaluator's labels and provisional confidence floor are not calibrated admission criteria; they do not drive automatic actions.
- The migration is additive and does not rewrite existing proposals, beliefs, or production sediment.
- Production requires migration `m060_belief_admission` before the new persistence path can run. Production migration/deployment was not performed as part of this implementation.
- The code and documentation are implemented in the working tree, but runtime test gates remain incomplete; see `SPEC.md` task T78.

## Verification boundary

Backend Ruff lint, Ruff format check, and strict mypy passed. The belief, chat, branching, and dream regression selection passed (99 tests total); the frontend admission component tests passed (2 tests), and the frontend production build passed.

The full backend suite was started but did not complete cleanly: an order-dependent run reported `conversation_log` missing in `test_branching_api_integration` and later stalled near completion. That test passed alone and in the 99-test scoped selection. The full suite remains an open repository-wide gate in `SPEC.md` task T78. These checks do not establish production deployment, migration state, evaluator calibration, or live admission behavior.
