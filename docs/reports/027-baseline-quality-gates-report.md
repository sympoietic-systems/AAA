# Report 027: Baseline quality gate repairs

Date: 2026-10-03. Branch: `codex/baseline-quality-gates`. Parent: `1021b7e`.

## Changes

Bridge-belief creation now propagates storage and unexpected failures instead of returning an apparent missing target. Existing missing-target behavior remains for genuine absence. PDF crawl handles expected I/O, value/parser and dependency errors; unexpected exceptions propagate. Temporary PDF creation, extraction and cleanup execute within one worker-thread scope. Dream budget transition state has an explicit optional tuple annotation.

## Verification

Four regression cases were run before the fix: three failed and one passed. Storage failures and unexpected extractor failures reproduced swallowing. After repair, the full suite and static gates are recorded below. No debt inventory increase was made.

The first integrated invocation had 468 passes and six fixture setup errors because the explicitly chosen temporary directory had no parent. This was a command setup error; the parent was created before retrying. Backprop: pre-create writable test workspace before invoking pytest. No application invariant was needed for that environment failure.

Configured strict mypy: PASS, 43 files. Ruff check and format check: PASS, 393 backend files. Existing third-party mobi/imghdr deprecation remains visible.

Canonical full-suite receipt: [baseline.xml](../../benchmarks/runs/verification/actions_20261003/baseline.xml).

Full serial retry: **474 passed**, one third-party warning, 287.63 seconds. Architecture debt gate is green. No performance benchmark required for these failure-boundary and typing repairs.
