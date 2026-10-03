# Report 031: Next actions delivery

Date: 2026-10-03. Implemented sequentially in an isolated worktree, with one branch per action. Branches are stacked; the last includes all preceding changes. Local main remains at `1021b7e`. This delivery is not merged or pushed.

| Action | Branch | Commit | Report |
| --- | --- | --- | --- |
| Baseline quality gates | `codex/baseline-quality-gates` | `9eb27c2` | [027](027-baseline-quality-gates-report.md) |
| Activation provenance and stale skills | `codex/activation-provenance` | `7b50e97` | [028](028-activation-provenance-and-stale-skill-review.md) |
| Belief context and calibration workflow | `codex/belief-context-calibration` | `d5b2695` | [029](029-belief-context-and-calibration-workflow.md) |
| Research calibration workflow | `codex/research-triage-calibration` | Commit containing this report | [030](030-research-screening-calibration-workflow.md) |

## Verification

Integrated backend and benchmark suite: **496 passed, zero failures**, 242.30 seconds. One third-party `mobi`/`standard-imghdr` deprecation warning. [Canonical JUnit receipt](../../benchmarks/runs/verification/actions_20261003/final.xml).

```powershell
python -m pytest backend/tests benchmarks/tests -q -p no:cacheprovider --basetemp=.local/checks/actions-final --junitxml=benchmarks/runs/verification/actions_20261003/final.xml
```

Ruff check and format check pass for backend and new research tooling. Configured mypy passes 43 files; the added activation schema/helper and belief context/service strict slices passed their focused checks. Research focused tests were rerun after final scorecard/usage changes. Frontend is unchanged. Native model comparisons and source acquisition were separate from unit tests. No production database migration, belief writeback, pruning or configuration enablement was executed.

## What is ready

The baseline failure is repaired: bridge storage faults propagate, PDF handling preserves unexpected errors, and dream budget state has its tuple type. Activation receipts now cover assembled prompts in chat and dreams with stable IDs, digest and explicit partial coverage; historical missing data remains unknown. Migration 051 must be applied through the normal migration workflow when deploying to an existing database.

Belief evaluation abstains on missing, stale or unresolved context before invoking Jev. The 240-pair annotation packet has 144 held-out pairs; independently reviewed labels are absent by user confirmation. Six synthetic cases repeated twice produced one false contradiction review in the unguarded baseline and none in guarded variants. This small sample supports regression coverage only.

Research tooling exports 100 real queries, acquires raw pools, freezes reviewed labels and compares three selection variants. Two real acquisition smoke queries succeeded. Four synthetic cases repeated three times gave expected selections throughout for legacy and combined screening. Separate axes abstained ten times out of twelve and are not supported for adoption.

## Usage and skill interpretation

Historical activation absence cannot establish that a belief or skill has no value. The current database has no new provenance receipts until deployment; the audit reports unknown coverage explicitly. The earlier apparent-unused inventory is therefore an observation gap requiring prospective evidence.

For the three stale skills, the original generic probes yielded six valid refusals and three timeouts. Representative task probes yielded one valid bounded proposal for `self-triggered-dream`, and timeouts for `order-from-noise` and `performative-interface`. Those timeouts leave assessment incomplete; they do not justify pruning. Skill content and lifecycle were preserved.

## Next acceptance boundary

Merge review can use these branches and reports. After deployment, apply migration 051 and collect fresh provenance. For calibration, acquire remaining raw research pools, annotate both packets independently, freeze the data, evaluate held-out outcomes and perform blinded downstream citation/usefulness review. Keep research default disabled and belief routing in dry-run until that evidence is reviewed. Geometry integration also needs a separate contract: the inspected nonnegative belief coordinates cannot reach the existing negative-cosine antagonism threshold.
