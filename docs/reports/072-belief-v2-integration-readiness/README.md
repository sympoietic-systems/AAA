# 072 — Beliefs v2 integration and release readiness

Date: 2026-10-13. Scope: local T17 integration gate. This report covers a local checkout and isolated test databases; it is not production certification.

## Result

The integrated local contract is ready for the separately controlled rollout decision. One authenticated API test now follows a source-bound encounter through a workshop decline, retained counter-trace, review history, and read-only export. Source lineage remains unchanged and scoped dissent is identical in the mutation receipt, review view, and exported decision. Existing UI tests cover receipt identity/time parity in admission and trace views, retained counter-traces, and linked-lineage presentation.

Release readiness is **NO-GO for production rollout**. T15 remains inconclusive: independent semantic ground truth and situated usefulness judgments are absent, and the user declined the optional human anchor. The T15 closeout and its evidence remain authoritative. T17 does not override that result. Participation remains disabled with zero exploratory slots; all origin intake flags remain false. No production database, migration, provider, or deployment was used.

## Contract audit

- Migration 069 is additive and immutable. The T16 isolated rollback test verifies that application rollback leaves linked history readable. T17 adds no migration.
- Existing authenticated workshop and export routes implement the frozen T3 request/response contract; the new test exercises them together. No API or schema change was needed.
- `backend/config.yaml` keeps assessment and participation disabled, slots at zero, and every v2 origin-intake flag false. T17 changes no runtime configuration.
- ADR-129 remains the accepted T16 decision for linked revision, supersession, and resurfacing. No new architectural decision was required by the integration review.
- Existing UI tests verify shared receipt identity and timestamp across belief and trace surfaces, and bounded retained dissent and lineage rendering. They use deterministic fixtures, not production data.

## Verification

- `uv run pytest backend/tests/test_belief_workshop_v2.py -q -p no:cacheprovider` — 35 passed, including `test_api_receipt_source_lineage_and_dissent_match_review_and_export`.
- `npm test -- --run` — 30 files, 166 tests passed.
- `npm run typecheck` and `npm run build` — passed.
- `npm run lint` — passed; the repository wrapper reported 159 existing legacy errors and 10 warnings, with zero regressions.
- `uv run ruff check backend/`, `uv run ruff format --check backend/`, and `uv run mypy` — passed.
- Full `uv run pytest backend/tests -q -p no:cacheprovider` — 1,053 passed, one third-party `mobi`/`imghdr` deprecation warning, 953.73 seconds.
- `git diff --check` — passed after final task files were updated.

## Limits and next gate

These checks establish local contract and presentation parity only. They do not establish semantic accuracy, participation usefulness, production build/config identity, effective server flags, migration state, complete-window telemetry, or rollback readiness on the production host. T18 must retain its explicit rollout authorization and V23 evidence requirements.
