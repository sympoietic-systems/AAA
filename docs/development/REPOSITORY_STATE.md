# Repository state after integration

Snapshot: 2026-11-01. This records local source integration and verification. No code was pushed, deployed or used for a new live experiment. `origin` was fetched before integration; remote `main` still points to `e298205`.

## Where work lives

| Checkout / branch | Current state | Meaning |
| --- | --- | --- |
| Root checkout / local `main` | Clean; includes performance merge `620f85b` and the reconciliation commits | Shared application baseline. Includes navigation/search/payload optimizations and stack-safe layout. Experimental T94 runtime changes are not merged into main. |
| `chore/reconcile-working-tree` | Same completed integration baseline as local main | Retained integration branch, including this final documentation update. |
| `perf/navigation-loading` | Clean at `95d9ed4`; fully merged into local main | Original nine-commit workstream retained for history. Its earlier deployment records are historical; this task did not query or update production. |
| `codex/t94-historical-revision` | Clean; contains current main plus its distinct feature work | Original source checkpoint `53d78fd`; feature integration `c04f681`. The final documentation merge keeps the branch on current main without merging T94 into main. |
| Local `origin/main` ref | `e298205`, checked by fetch | Does not include these local integration commits; nothing was pushed. |

Additional checkouts are under `~/.t3/worktrees/aaa/`; resolve them with `git worktree list`. The performance checkout was retained unchanged. T94 was checkpointed and reconciled without modifying its original experiment receipts.

To review only T94's work:

```sh
git diff --stat main...codex/t94-historical-revision
git diff main...codex/t94-historical-revision
```

Its feature diff has 52 files, rather than the old 480 changed/untracked path entries that included the copied reorganization.

## What was reconciled

The original root inventory contained 250 staged entries, 18 tracked unstaged entries and 12 untracked paths. Some paths had both staged and unstaged edits; those counts are not a file total.

- The previously authorized package/test reorganization moved belief code into domain packages, split storage models, relocated prompt/persona helpers, grouped tests and removed eight import-time prototype scripts plus retired bootstrap exports. Internal imports, typing paths, documentation and script links follow the canonical locations.
- Persona loading retains nested identity protocols. Consultation message-agent assertions lost during test relocation were restored, and the test closes its SQLite connection. Telemetry tests use deterministic embedding doubles.
- The original partial belief-read backport is now part of the full performance integration. Duplicate responsive-read and migration tests were consolidated at subsystem paths. The broad-catch allowance remains two, split one per async/worker boundary.
- Verification exposed an expired calendar-dependent export test and reproduced a previously reported same-key workshop race. Deterministic date cases and concurrency interleavings now cover both fixes; different-key conflicts and single-decision persistence remain enforced.
- T38 review tooling and its evaluation closeout are committed. Report 076 remains local empirical evidence; its inconclusive result does not promote the active controller.
- T94's source, synthetic fixtures, runtime instrumentation and expanded experiment record were checkpointed before merging the shared baseline. Its original pilot failed progression gates; the revised development implementation has offline verification only. Further live work remains separately gated.

Git preserves content and index state, but does not record why earlier sessions stopped before committing. No discarded-change explanation is inferred.

## Commit provenance

| Commit | Purpose |
| --- | --- |
| `369c39d` | Domain packages, storage-model exports, subsystem tests, persona correction and relocated documentation. |
| `ff8666b` | Initial bounded belief-read backport, migration 070 and architecture allowance repair. |
| `0f17b3b` | Workshop receipt race fix and deterministic concurrency/calendar regressions. |
| `a414071` | T38 review tooling, offline contracts and evaluation closeout without promotion. |
| `5edfb32` | Agent-policy entrypoints and portable OpenCode MCP working directory. |
| `0ec9ea2` | Initial reconciliation inventory and checkout-specific T94 plan status. |
| `53d78fd` | T94 recovery checkpoint before shared-baseline integration; not on main. |
| `620f85b` | Performance merge retaining the package organization and all nine performance commits. |
| `c04f681` | T94 merge retaining its distinct implementation and the verified shared baseline; not on main. |

The final documentation commit updates this inventory; T94 then merges that documentation so current main is its ancestor. Source history is preserved with merges, without rebasing or force-pushing existing work.

## Artifacts and future experiment work

The 1,297 original files under T94's `benchmarks/runs/historical_revision/` are unchanged: 705,538,529 bytes and aggregate SHA256 `203ad0a988f8dc35f042ba14cd065a2fcc863f41f4606fb1f5f6a33ad0dd1524`. This identity hashes sorted relative paths and their file SHA256 values. Trial databases, checkpoints, prior spending and proposal hashes were not rewritten.

Three performance receipts originally tracked outside the artifact directories were moved without byte changes into `benchmarks/runs/navigation/legacy_20261031/`. Its local `source_manifest.json` binds original paths/hashes to `95d9ed4`; historical Git objects retain the originals. Documentation now references the ignored canonical archive. Source fixtures and benchmark helpers remain versioned.

T94's small synthetic cases/outcomes are deliberately versioned source. Empirical reports and run receipts remain ignored under `docs/reports/` and `benchmarks/runs/`. A clean Git tree is not a backup of those artifacts. Ignored links in the T94 checkout reuse canonical reports and navigation/telemetry receipts without copying them; its own historical-revision runs remain local and unchanged.

Integration changes source identity and introduces the shared migration 070. Old frozen proposals do not authorize the new source. Before any live rerun, prepare and validate a new source-bound seal/proposal carrying prior spending, then obtain the additional live allowance. Do not rewrite old hashes or migrate old trial databases to make them match. The proposed additional 60 generation / 480 sensor requests were not authorized or spent by this integration. Held-out execution remains blocked. The expanded contract is `docs/systems/HISTORICAL_REVISION_SPEC.md` on the T94 branch (`git show codex/t94-historical-revision:docs/systems/HISTORICAL_REVISION_SPEC.md`); main retains the original plan with its checkout scope explicit.

## Deliberate import and policy surfaces

Prompt/persona redirects in `backend/utils/` and private bootstrap re-exports from `backend/main.py` are removed. Repository Python callers use their canonical locations.

`backend/storage/models/__init__.py` preserves established model exports; `backend/services/belief/__init__.py` preserves `BeliefService`. Existing `backend/storage/activation.py`, `belief_review.py` and `research_{acquisition,branch_proposal,children,evidence,receipts}.py` expose records used by repository, service and test callers; canonical definitions live in `backend/storage/models/`. Removing those public surfaces requires migrating their identified consumers and checking model identity/rebuilding together.

`.agents/` is a separately versioned, ignored policy checkout. Root `AGENTS.md` and `GEMINI.md` point into it. T94 uses an ignored link to that canonical checkout, plus an ignored `.venv` link to the existing environment. Fresh application-only clones must provision policies and dependencies; relative policy links belong to `.agents/`. Policies were not copied into application history. OpenCode's MCP working directory is `.` so it follows the selected checkout.

## Verification

Shared baseline `620f85b`:

- Full combined Python suite: **1,307 passed**, 940.56 seconds; one existing third-party `mobi` / `imghdr` deprecation warning.
- Backend Ruff lint/format and strict mypy: passed; **135** configured source files checked.
- Frontend: **186 tests passed** across 36 files; lint, typecheck and production build passed. The lint regression gate retains 158 legacy errors and nine warnings with zero regressions.
- Performance integration's 25 affected relative documentation links resolved. The documented navigation benchmark module's `--help` smoke check passed; no performance benchmark or production probe was rerun.

T94 integration `c04f681`:

- **224 focused tests passed**, 91.11 seconds, covering the harness, history selection/assembly, structured and ordinary chat, activation provenance, quality ratchets, belief responsiveness and workshop behavior.
- Backend/harness Ruff lint and formatting passed. Application strict typing checked **136** files, including structured output; the separate strict harness check passed over **22** files.
- There is no frontend source diff against the validated shared baseline. T94's ten affected relative documentation links resolved.
- The pre-merge checkpoint separately passed 140 harness and 14 runtime tests. Counts overlap with the post-merge selection and must not be added as unique coverage. The complete combined suite was run for shared main, not repeated in full on experimental T94.

The earlier reconciliation's calendar failure and workshop race are fixed in the current baseline; its old 1,269-pass/one-failure run is not the current release gate. The older `run_prompted_baseline.py` retains ten pre-existing Ruff findings after its import migration; no whole-repository lint-clean claim is made. Production identity and useful historical learning remain outside these checks. The earlier required Symbia consultation could not connect and supplies no endorsement.
