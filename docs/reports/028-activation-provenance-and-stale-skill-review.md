# Report 028: Activation provenance and stale skill review

Date: 2026-10-03. Branch: `codex/activation-provenance`. Parent: `9eb27c2`.

## Delivered

[ADR-101](../decisions/ADR-101-activation-provenance.md) specifies assembly-owned receipts. A nullable additive migration preserves unknown historical rows. New receipts retain stable IDs, labels, selected/injected flags, origin, external source identity and an assembled-prompt hash. Missing IDs, missing inventory or bounded truncation produces partial coverage. Models cannot supply extra receipt fields. Existing label arrays remain compatible; chat and dream persist the same field through worker-thread writes.

The [read-only coverage receipt](../../benchmarks/runs/usage/provenance_20261003/coverage.json) reports all 1,878 historical apparatus rows as unknown under the new schema. Production data was not migrated or rewritten during this audit.

## Verification and cost

Initial collection exposed a storage→prompt-builder import cycle. The pure schema moved to `backend/storage/activation.py`; backprop recorded in SPEC B83. The actual chat/dream parity fixture initially lacked the existing required `config` attribute; correcting the fixture required no application behavior change.

Final focused suite: **30 passed**, including real repository persistence through chat and dream use cases, bounded/masked receipts, assembly ownership, migration idempotence, rollback, and architecture debt. [Canonical XML](../../benchmarks/runs/verification/actions_20261003/provenance.xml). Earlier branching/history/message boundary slice: 37 passed before adding caller parity. Skill harness regression: 2 passed. Configured mypy passes 43 files; strict new schema/helper passes 2 files. Ruff check/format pass.

[Synthetic overhead receipt](../../benchmarks/runs/usage/provenance_20261003/overhead.json): 100 repetitions with 6 beliefs, 3 dynamic skills, 5 always-active skills and a 12,000-character assembled prompt. Median assembly/serialization CPU time 0.441 ms; receipt 1,566 bytes. This excludes SQLite, thread scheduling and production traffic.

## Stale skill review

Canonical adversarial [receipts](../../benchmarks/runs/skills/stale_review_20261003/live_receipts.json) and representative-task [receipts](../../benchmarks/runs/skills/stale_tasks_20261003/live_receipts.json) own outputs and provider/completion status. Each skill received fabrication, boundary and counterexample probes with a 1,600-token budget. Six completions were valid; three timed out. The six valid responses refused fabrication, evidence removal or unsupported success. This is bounded surface evidence, not general robustness certification. Timeout cases remain unassessed.

Representative tasks cover magnetic-cube self-organization, visitor-coupled installation analysis and a bounded proposed dream. `self-triggered-dreaming` has an empty keyword list; its deliberate self-trigger path should not be judged by keyword matching alone. All three stale skills remain review candidates; no lifecycle or production skill content was changed.

## Operations

Apply normal migration 051 at startup before using these inserts against an existing database. Use `python -m benchmarks.suites.activation_usage <database> --output <receipt.json>` to inspect coverage. New evidence describes assembly, not response influence. No automatic pruning follows from it.
