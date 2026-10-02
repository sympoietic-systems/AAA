# Report 025: Four follow-ups — delivery and integrated verification

Date: 2026-10-03. Baseline: `209385b`. Environment: Windows, Python 3.13.3 using the existing repository virtual environment.

## Delivered sequence

Each task was implemented, verified, documented and committed before starting the next. Branches form a sequential stack: each later branch includes earlier completed tasks. `codex/aaa-followups` points to the combined delivery. The isolated checkout is `D:/01_GIT/AAA/.local/followups`; the original checkout remains on `adr-098-paskian-teachback` with its uncommitted ADR work preserved. No merge or push was performed.

| Task | Branch | Task commit | Report |
| --- | --- | --- | --- |
| Message-tree persistence integrity | `codex/message-tree-integrity` | `486a8fc` | [021](021-message-tree-integrity-report.md) |
| Skill vitality and forkability audit | `codex/skill-vitality-audit` | `02b8e70` | [022](022-skill-vitality-audit-report.md) |
| Jev research screening and grounded web collision | `codex/jev-research-triage` | `a06b690` | [023](023-jev-research-triage-report.md) |
| Jev belief review routing and tension evidence | `codex/jev-belief-tension` | Commit containing this report | [024](024-jev-belief-routing-and-tension-report.md) |

The message task fixes a reproduced transaction defect. The historical parent-commit timing allegation was not reproduced. The audit finds three active on-demand skills requiring review and retains incomplete evidence. Research triage is implemented as an opt-in candidate. Belief routing is implemented as a dry-run service with a separate disposable-copy matrix application path.

## Verification scorecard

Canonical [verification receipt](../../benchmarks/runs/verification/followups_20261003/verification.json) and [baseline comparisons](../../benchmarks/runs/verification/followups_20261003/baseline_comparison.json) own the raw gate results.

| Check | Result | Scope / limit |
| --- | --- | --- |
| Full serial pytest | **469 passed, 1 failed** | 470 backend and benchmark tests; 225.9 seconds |
| Message-tree focused integration | PASS — 7 tests | Outer rollback, parent ownership and worker visibility |
| Audit harness | PASS — 2 tests | Snapshot purity, receipt validation and provider signature |
| Research focused suite | PASS — 27 tests | Jev boundaries, crawl resilience and existing orchestration |
| Final belief + endpoint security slice | PASS — 27 tests | Includes 12 belief tests and corrected deterministic SSRF fixtures |
| Ruff check | PASS | Backend and all new benchmark modules/tests |
| Ruff format check | PASS | Backend and all new benchmark modules/tests |
| Strict mypy: new modules | PASS | `evidence_triage.py` and `belief_triage.py` |
| Strict mypy: configured allowlist | **FAIL — existing error** | `dream_trigger_policy.py:331` assigns a tuple to an unannotated field inferred as `None` |
| Frontend checks | NOT RUN | No frontend changes |

Commands use `D:/01_GIT/AAA/.venv/Scripts/python.exe -m ...`, reusing installed dependencies instead of creating another virtual environment. Full pytest ran serially with a fresh `--basetemp` and `-p no:cacheprovider`. No simultaneous pytest processes shared the default test database in these final checks.

## Remaining baseline failures

`test_broad_catch_debt_never_grows` identifies existing broad handlers in `BeliefProposalUseCases._resolve_target_belief` and `RhizomeWebProbe.crawl`. Their AST bodies are identical to baseline `209385b`; no new broad handler was introduced by these tasks. The debt inventory was preserved. The dream-policy file is also identical to that baseline, establishing the existing typing error independently of the new strict modules. These two gates prevent a clean repository-wide verification claim.

The first full run had 468 passes and two failures. Its additional failure was an SSRF unit test using live DNS: `example.com` resolved to restricted `198.18.0.93` in this environment. The guard correctly denied it. The unit test now supplies fixed public and restricted DNS fixtures and asserts both outcomes, with no production security changes. The final full run confirms that failure is resolved. One existing third-party `mobi` / `standard-imghdr` deprecation warning remains.

## Empirical results and rollout decisions

- Skill audit: 65 skills inspected; three active on-demand dormancy review candidates. Four named skills produced a complete, limited boundary refusal across live runs. Timeouts and truncated responses remain excluded from behavioral judgments. No automatic pruning or crystallization decision was made.
- Research triage: Jev selected the labeled source in 8/8 synthetic evaluations; the LLM selector returned 7/8, including one timeout. Median end-to-end latency was 1,808.8 ms versus 5,177.8 ms. The sample is insufficient for default promotion, so `research_triage.enabled` remains false.
- Belief triage: categorical labels matched 8/12 synthetic evaluations; two unresolved-reference cases produced confident false-positive contradiction reviews. Abstention and watchlist rates were each 16.7%. Runtime promotion is withheld.
- Snapshot belief evaluation: 56 beliefs and two explicitly scoped Codex proposals produced 12 evaluations, with seven abstentions and no qualifying contradiction edges. The disposable matrix remained empty; positive persistence and atomic rollback are established by fixture tests. The source snapshot hash stayed unchanged.

Jev remains an evidence evaluator. Authorship, commitment and skill/belief lifecycle changes retain their existing owner. ADR-099 and ADR-100 record this boundary. The ongoing ADR-098 implementation was not used as the test baseline, so combined ADR integration still needs verification after those changes are committed.

## Completion hygiene

Canonical JSON benchmark and verification receipts are retained under `benchmarks/runs/`. Temporary test files, disposable database copies, scratch XML and bytecode caches in the isolated checkout were removed after evidence extraction. Bulk cleanup commands were blocked by the tool policy; individually validated literal file paths succeeded. The original checkout and its running ADR work are preserved. Shared metadata files (`SPEC.md`, `TODO.md`, report registry) will need normal reconciliation when integrating with that uncommitted work.
