# Repository state after reconciliation

Snapshot: 2026-11-01. This is a local checkout and branch inventory, not a fresh production health check. Refresh it when integrating either workstream below.

## Where work lives

| Checkout / branch | State at inspection | Meaning |
| --- | --- | --- |
| Root checkout, `chore/reconcile-working-tree` | Reconciles work previously left on `main` at `e298205` | Backend package/test reorganization, persona correction, T38 review tooling and closeout, T94 plan, a bounded belief-read performance backport, and agent entrypoints. |
| `main` / local `origin/main` | `e298205`, 2026-10-15 | Does not yet contain this reconciliation or the performance branch. Remote refs were not refreshed during this audit. |
| `perf/navigation-loading` | Clean at `95d9ed4`; nine commits ahead of the common base | Broader navigation optimization, lazy belief histories, bounded search/list payloads, production frontend serving and stack-safe conversation layout. Earlier task records report deployment; this audit did not query production. |
| `codex/t94-historical-revision` | 480 changed/untracked path entries at base `e298205`, including 240 untracked paths; nothing staged | Contains a copy of much of the old root reorganization plus T94 harness, fixtures, runtime changes and experimental records. It is not a clean independent implementation diff yet. Counts use `git status --porcelain -uall`, so moved files appear as separate removed/untracked paths. |

The additional checkouts are under `~/.t3/worktrees/aaa/`. Use `git worktree list` to resolve their current paths. Their files were inspected without staging, committing, resetting or cleaning either checkout.

## Why the root was dirty

The initial root inventory contained 250 staged entries, 18 tracked unstaged entries and 12 untracked paths. Some paths had both staged and unstaged edits; these counts must not be added as a file total.

- **Package and test organization:** the earlier “review current project/codebase” task explicitly authorized the phased reorganization, removal of prompt/persona redirect modules, removal of private bootstrap re-exports, and deletion of eight legacy prototype test scripts. The scripts executed setup, database operations or model calls during import, so they do not belong in the offline pytest suite. The current subsystem tests remain the verification surface.
- **Persona and test corrections:** existing records B147/B148 describe the nested identity-schema fix and deterministic telemetry embeddings. The reconciliation also restores consultation message assertions lost during the test move and closes that test's SQLite connection.
- **Verification repairs:** the workshop/export integration test expired at its hardcoded 2026-11-01 cutoff; it now uses a frozen clock and timestamp-bound export windows, tested across the cutoff and a later year. A subsequent run reproduced the previously reported same-key workshop race. A deterministic interleaving established the missed-receipt/advanced-state cause; the command now rechecks its hash-bound receipt before rejecting stale state. Different keys still conflict and only one decision is persisted.
- **Belief-read performance:** the root had only part of `775f64f` from `perf/navigation-loading`: migration 070, worker-thread reads/timeseries, ecosystem offloading and regressions. This backport does not include the branch's broader navigation work. The broad-catch baseline needed its existing allowance split across the async and worker methods; the total remains two.
- **T38 review:** the untracked review scripts and tests support the completed semantic review recorded in local Report 076. SPEC/TODO and ADR-097 now distinguish completed evaluation from the unpromoted active controller. No new provider call was made to recreate that experiment.
- **T94 planning:** the root contains the experiment plan, not the later implementation. The “Assess System Gaps Against Goals” task continued in its own worktree. Its latest saved handoff reports 198 focused tests and a six-family offline audit, with a revised development rerun awaiting a new allowance of 60 generation and 480 sensor requests. These are attributed task records, not checks rerun by this reconciliation. Held-out execution remains blocked.
- **Agent setup:** root `AGENTS.md` and `GEMINI.md` are symlinks into the separately versioned `.agents` checkout. OpenCode's MCP working directory is relative so it follows the selected checkout instead of hardcoding this machine's root path.

Git preserves the pending content and index state, but does not record why earlier sessions stopped before committing. No discarded-change or forgotten-work explanation is inferred.

## Local commit groups

| Commit | Purpose |
| --- | --- |
| `369c39d` | Domain packages, storage-model exports, subsystem tests, persona correction and relocated documentation. |
| `ff8666b` | Bounded belief-read performance backport, migration 070, worker-thread/query-plan checks and architecture allowance repair. |
| `0f17b3b` | Workshop receipt race fix and deterministic concurrency/calendar regressions. |
| `a414071` | T38 review tooling, offline contracts and evaluation closeout without promotion. |
| `5edfb32` | Agent-policy entrypoints and portable OpenCode MCP working directory. |

The final documentation commit adds this inventory, retains the original T94 plan with its checkout scope made explicit, and marks PDR as a historical snapshot. These are local commits; this reconciliation does not push or merge them.

## Integration boundaries

1. Review this branch as the root reconciliation. It does not merge or deploy the other workstreams.
2. Integrate `perf/navigation-loading` with an explicit conflict review. Its first commit overlaps the belief-read backport; its code uses pre-reorganization paths. Preserve both the package layout and the later performance behavior. B149 names that shared performance lineage; B150 is already assigned to its deep-conversation fix. Reconciliation bug records start at B151 to avoid that collision.
3. Reconcile the T94 worktree against the shared baseline before presenting its work as a new diff. Preserve its uncommitted code, fixtures, checkpoints and accounting. Its untracked `.venv` symlink is a local environment reference, not implementation source; exclude it when preparing that workstream's commit. Do not copy the root plan over its expanded implementation spec. Further paid pilot calls require the separate rerun authorization described in that workstream.
4. Keep empirical reports and run receipts local under `docs/reports/` and `benchmarks/runs/`, as required by the documentation protocol. A clean Git tree does not back up these artifacts. T94's non-secret fixtures are also local in its worktree; review their fixture/versioning contract before any integration.

## Deliberate import surfaces

The prompt/persona redirects in `backend/utils/` and private bootstrap re-exports from `backend/main.py` are removed, as previously authorized. Repository Python callers use the new locations.

`backend/storage/models/__init__.py` retains the established storage-model exports. `backend/services/belief/__init__.py` retains the `BeliefService` entrypoint. Existing `backend/storage/activation.py`, `belief_review.py` and `research_{acquisition,branch_proposal,children,evidence,receipts}.py` still expose records used by repository, service and test callers; their canonical definitions now live under `backend/storage/models/`. These public surfaces were preserved during the move. Removing them would require migrating those identified consumers together and checking object identity and model rebuilding, rather than deleting apparently duplicate files.

## Agent-policy prerequisite

`.agents/` is ignored by the application repository and maintained as a separate repository. Provision that checkout before relying on the root agent symlinks. It was clean at inspection; its policies and skills were not copied into the application history. The symlinks can be unresolved in a fresh application-only clone until the policy checkout is installed. Relative links inside the policy belong to its canonical `.agents/` directory.

## Verification

The reconciliation runs backend lint/format, the configured strict mypy slice, the combined backend/benchmark suite, and the frontend build. Focused architecture, worker-thread and index-plan checks passed before the full run. Frontend lint/typecheck and all 166 frontend tests passed in the immediately preceding status review; no frontend application source changed here.

The migrated belief-benchmark imports, affected benchmark tests and legacy-review script pass Ruff. The older `run_prompted_baseline.py` retains ten pre-existing Ruff findings, verified against `HEAD`; its persona import was relocated without changing those findings. Frontend lint also retains its recorded legacy baseline of 159 errors and ten warnings with zero regressions. Neither legacy baseline is described as globally lint-clean.

Observed results:

- Combined backend/benchmark run: **1,269 passed, one failed**, 869.38 seconds. The failure was the date-dependent workshop/export test described above. One existing third-party `mobi` / `imghdr` deprecation warning remained.
- After the calendar correction, a 75-case focused run produced 74 passes and the previously documented same-key race. A deterministic two-case reproduction then distinguished identical-key replay from different-key rejection.
- After both fixes: **379 passed** across all belief-service tests, quality tests and migration 070, 53.67 seconds. This includes the calendar cases, deterministic interleaving and original six-request race. The full combined suite was not repeated after these scoped repairs; these results must not be represented as a fresh all-green combined run.
- Backend Ruff lint/format and strict mypy: passed; mypy checked its configured **134-file** slice. The new T38 review scripts/tests also passed Ruff lint/format.
- Frontend production build: passed. The preceding status review's lint/typecheck and **166 passing tests** remain applicable because no frontend application source changed.
- OpenCode `debug config`: passed after changing the MCP working directory to `.`. All 86 affected relative documentation links resolved, interpreting policy symlinks from their canonical source. Git whitespace checks passed; no temporary test databases remained in the root or backend data directory, and regenerable bytecode/tool caches were removed.

Production state and the full T94 implementation are outside these checks. Symbia consultation was attempted for the existing package boundaries and returned “Failed to connect to AAA backend”; no endorsement or general backend diagnosis is inferred.
