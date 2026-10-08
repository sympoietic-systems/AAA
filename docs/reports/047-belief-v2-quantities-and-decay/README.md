# Beliefs v2 T2: measured event quantities and elapsed-time accounting

Date: 2026-10-08. Status: implemented and verified locally; production migration/deployment not performed.

Scope: [BELIEF_SPEC.md T2](../../systems/BELIEF_SPEC.md), invariants V16/V17/V18 and additive preservation V21. Tests ran in the shared checkout; unrelated commits advanced HEAD during the work. The final full-suite run started from `38b5ab23342ab43d640c3dfc3687d7ce791162c3` plus the T2 working-tree changes. HEAD later advanced to `1ad3f41`. This is local verification, rather than certification of an immutable production build. [Verification metadata](verification.json) records source hashes and observed gate results.

## Resulting behavior

Belief events now carry nullable `delta_mass` and `confidence_delta`, plus `impact_quantity` and `impact_unit`. Accretion records the actual changes after clamping, reads the latest belief under the writer lock, and commits its event with the mutation. A failed mutation leaves no measured event behind. Atrophy records its actual mass change and zero confidence change.

The API retains `delta_confidence` as a deprecated alias for generic `impact_score`, and also exposes the generic value as `impact_value`. Existing clients therefore retain their field. The new belief log uses measured fields, including clipped zero values, and labels unknown historical impacts as unknown quantities. Historical scores and rounded rationale text are not converted into measured confidence or mass changes. Removing the deprecated alias requires an explicit versioned compatibility decision in the later contract work.

Wall-clock atrophy now uses a durable `belief_nodes.atrophy_accounted_at` checkpoint. It charges elapsed time only after the later of that checkpoint and reinforcement. Current mass, lifecycle, checkpoint, and event are committed in one writer transaction, with agent/stage/current-state rechecks. Repeat calls, reopening the repository, and concurrent workers cannot charge the same interval again. Event failures propagate and roll back the charge. Decay leaves `last_reinforced_at` and confidence unchanged.

The policy retains its 0.1% hourly rate, 30-minute reinforcement grace, 20% charge cap, and small-change accumulation threshold. A capped charge accounts for the entire interval. The legacy `_apply_mass_decay` helper now delegates to this same accounting operation; it cannot independently apply the historical exponential formula. Async entry points offload the synchronous operation.

Migration `m063_belief_event_quantities_and_atrophy_clock` adds the fields without interpreting historical events. Existing beliefs start their checkpoint at migration time without changing mass, confidence, or reinforcement. Repository-created beliefs initialize the clock at creation; missing checkpoints begin at the next sweep without reconstructing old charges.

## Verification

| Gate | Observed result |
| --- | --- |
| Backend Ruff lint | Passed |
| Backend Ruff format check | Passed; 462 files already formatted |
| Strict mypy | Passed; 87 source files, including the three newly added scope entries |
| Final full Python suite | 755 passed, one third-party `mobi`/`imghdr` deprecation warning; 602.10 seconds |
| Frontend type checking | Passed |
| Frontend lint | Exit 0; 164 legacy errors, 10 legacy warnings; zero regressions |
| Full frontend tests | 25 files, 142 tests passed |
| Frontend build | Passed |
| Changed-document links and `git diff --check` | Passed |

The final Python command used `pytest -x -q`, `faulthandler_timeout=60`, external temporary/cache directories, and `PYTHONDONTWRITEBYTECODE=1`. A slow test emitted a diagnostic thread dump, then continued; the suite completed successfully. An earlier full run was stopped to include the final stale-snapshot fix. The initial red regression run failed because the accounting column did not exist; nine initial regressions then passed, followed by a 47-test focused selection. The final suite includes all subsequent regressions.

`backend/tests/test_belief_t2.py` adds 18 test cases covering retry/restart, reinforcement, concurrent same-clock calls, backward clocks/agent isolation, missing checkpoints, transaction failure, legacy unknown quantities, measured deltas, clipping, latest-state rereads, warm migration, grace/cap, shared legacy accounting, and four turn-floor cases. `BeliefDetail.test.tsx` adds three display regressions. Existing metabolism/admission/dream tests also pass.

A concurrent session implementation exposed three strict-mypy errors from reusing local names across differently typed branches. A separate mechanical repair names the integer wall clock and persisted tuple explicitly, preserving behavior; root SPEC.md B117 records it. Unrelated session-initialization and skill-system edits were preserved.

## Limits and next task

Wall-clock decay remains disabled by default. The crystallized floor continues to apply to turn decay; the optional wall-clock policy retains its existing ability to erode mass and collapse beliefs below 0.02. T2 does not enable that policy, reset historical mass/confidence, or calibrate semantic admission. Turn decay still lacks per-belief events; additional producer coverage belongs to T10.

The existing accretion collapse path still deletes belief events when moving a belief to a rejected proposal. T16 owns that history-retention repair. T2 does not claim complete lifetime event preservation.

Deploying this code requires applying m063 first through an authorized rollout. Production identity remains unverified; no production database calls or writes were made in T2. T3 next freezes encounter/assessment/decision contracts, state mapping, relation adapters, authority, bounded defaults, and rollout/rollback compatibility.
