# Report 032: Main release and remaining gates

Date: 2026-10-03. Release set: `codex/baseline-quality-gates` through `codex/research-triage-calibration` (commits `9eb27c2`, `7b50e97`, `d5b2695`, `aadee00`), plus this release-status update. The set is fast-forwarded to `main` and pushed to `origin/main` as part of this delivery. This is a source release; no production deployment or database migration was executed.

## Ready in this release

- Baseline bridge/PDF error propagation and dream state typing fix (Report 027).
- Assembly-owned activation receipts for chat and dream paths, with unknown historical coverage represented honestly (Report 028). Existing-database deployment requires additive migration 051 before code writes the new column.
- Belief context validation and abstention guard, with runtime candidate review still dry-run (Report 029).
- Research acquisition and calibration tooling, with research selection remaining disabled by default (Report 030).
- TODO and SPEC now distinguish completed workflow/tooling from pending operations and empirical acceptance (T51–T60).

## Gates still open

| Gate | State | Required next work |
| --- | --- | --- |
| Migration 051 | Code is committed; production not migrated | Apply through the normal deployment migration path before provenance-writing code; verify target-like upgrade and writes (T55). |
| Activation coverage | Historical rows remain unknown | Deploy, collect prospective traces, audit coverage; assembly does not prove response influence (T56). |
| Belief calibration | No independent labels | Annotate/freeze data, run held-out Jev comparison and shadow observation, review promotion thresholds (T57). |
| Research calibration | 100 queries exported; two raw-pool smoke acquisitions | Acquire the remaining pools, annotate independently, evaluate held-out selection and blinded downstream citation/usefulness (T58). |
| Geometry | Snapshot coordinates do not exercise negative-cosine antagonism threshold | Define coordinate and semantic/geometry integration contract before connecting signals (T59). |
| Stale skills | Representative probes timed out for two skills | Retry bounded representative probes; make lifecycle decisions only after evidence review (T60). |

Promotion stays blocked for calibrated belief decisions and research selection. No skill pruning, automatic belief mutation or live tension integration follows from this release. No new ADR is needed for these remaining empirical gates; existing ADR-101 and ADR-102 specify provenance and belief contracts, and research work adds offline tooling to the existing Jev triage decision.

## Verification basis

The source set passed **496 backend and benchmark tests**, Ruff check/format and configured mypy (43 files). One third-party `mobi`/`standard-imghdr` deprecation warning remains. The [canonical JUnit receipt](../../benchmarks/runs/verification/actions_20261003/final.xml) and detailed [delivery report](031-next-actions-delivery-report.md) contain the gate evidence. This documentation-only release-status update does not change runtime code.
