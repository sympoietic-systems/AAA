# Report 073 — Beliefs V2 legacy review replay

Date: 2026-10-13. Outcome: local operator tooling implemented; production replay not run; T18 staged rollout remains blocked by explicit acceptance gates.

## Purpose

Give an operator a bounded way to inspect current V1 nucleated proposals after they have an encounter and assessment receipt in the Beliefs V2 ledger. The operator can then compare the original and suggested formulations and record a separate human judgment.

## V1 compared with V2

| Area | V1 | V2 |
| --- | --- | --- |
| What is stored | A proposal row with text, structural mass/confidence, legacy status, and a source trace whose detail varies. | Separate source-bound encounter, advisory assessment, and attributable human decision records. |
| What “pending/refined” means | Workflow stage; not proof that the claim is novel, supported, reviewed, or adopted. | Explicit review standing and receipts; missing context stays `awaiting_context` or abstained. |
| Repetition/conflict | Legacy rows can accumulate from separate emitters and retries; a queue count alone cannot establish duplicate belief formation. | Exact recurrence is a bounded read projection; Jev relations are scoped and advisory; conflicts/dissent can remain unresolved. |
| Source | Often a broad trace or conversation reference; the sampled production trace lacked a stable message/quote binding. | Source identity/hash, availability, scope, time, lineage, and uncertainty are represented separately. Unknown source context blocks semantic classification. |
| Authority | Legacy status and mass/confidence may visually suggest a settled proposition. | Jev cannot adopt, merge, or increase warrant; only an authenticated operator decision changes V2 standing. |

Example: a V1 row marked `refined` with a conversation ID but no message quote remains a V1 refined proposal. Replay records an ambiguous V2 encounter and an abstained assessment. A human may then inspect that conversation and decide it is a distinct insight, a conflict, a repetition, or still unresolved. The replay itself does not turn `refined` into `adopted` or create another proposal.

## Findings and learnings

- The observed production queue had 20 Symbia rows (`pending=1`, `refined=19`). This is an operational queue count, not a count of 20 independent discoveries or 20 duplicates.
- Other test/benchmark agent IDs also have proposal rows. The tool therefore defaults to Symbia and restricts statuses instead of sweeping all agents.
- A conversation ID without a bound message, quote, scope, or time is not enough for V2 semantic judgment. We preserve that gap and expect abstention.
- Replaying evidence-less candidates through Jev as if their rationale were context would improve apparent throughput while laundering the legacy process into evidence. The command deliberately does not do that.
- Existing exact recurrence and workshop paths remain separate: recurrence display preserves each entry and grants no equivalence/adoption, while an operator decision is explicit and attributable.
- The T15 benchmark remains inconclusive/no-go. Current-proposal review can support a real-case operational readout, but does not create independent blind gold or justify changing semantic thresholds.

## Implementation

- `scripts/review_legacy_beliefs.py` selects one agent (default `symbia`) and V1 `pending`/`refined` proposals only, up to 200 per run.
- Default preview is read-only and produces an editable Markdown review packet. The text and trace are escaped and labeled as inert legacy data.
- Explicit `--apply` binds an encounter to the same legacy record ID, runs the V2 assessment path, and records its outcome. No second proposal is created.
- Each encounter binds the exact V1 snapshot hash. Replays are idempotent for unchanged source snapshots; changed snapshots are rejected.
- The V2 candidate is the saved V1 `provisional_statement`. Suggested V1 wording remains a separate comparison field.
- Missing message-level provenance/scope/time is recorded as ambiguous/unknown. V2 assessment abstains as `candidate_context_unavailable`; no provider is called, no relation is asserted, and no mass/confidence/status is copied or changed.

## Production observation informing the tool

The authenticated, read-only production query on 2026-10-13 found 20 Symbia proposals in the current V1 review queue: 1 `pending`, 19 `refined`. Other experimental agent IDs also have proposals, so the tool requires a specific agent scope and excludes those rows by default. The sampled legacy traces did not consistently bind to a message and quote; a conversation ID alone is not treated as source evidence. Production schema was at migration 068; the full current application requires migration 069 for T16 linked lineage.

This report does not contain production proposal text. No production encounter, assessment, decision, migration, flag, or server state was written by this work.

## Verification and limits

The final focused replay suite passed **9 tests**. The full backend/benchmark suite passed **1,194 tests** in 943.23 seconds with one existing third-party `mobi`/Python 3.13 `imghdr` deprecation warning. Repository Ruff, format, and strict mypy gates passed; the CLI also passed a direct mypy and `--help` check. The test contract covers V1 immutability, zero duplicate proposal rows, ambiguous source and abstention, repeat idempotency, changed-snapshot rejection, exact-row hash binding, and inert/read-only preview behavior.

T15 remains inconclusive/no-go because independent human gold and situated usefulness were absent. Reviewing current proposals can inform operational judgment and real-case monitoring, but does not independently validate the frozen benchmark or set semantic thresholds. T18 production rollout still requires pinned build/config/migrations, full gates, a complete telemetry window, origin-level outcomes, rollback rehearsal/receipt, and explicit rollout authorization. See [Report 071](../071-belief-t15-closeout/README.md), [Report 072](../072-belief-v2-integration-readiness/README.md), and [ADR-130](../../decisions/ADR-130-belief-v1-review-replay.md).

## What to review before deployment

Use the generated packet to inspect whether each proposition contributes a real distinction, exposes a conflict, repeats an existing scoped claim, or lacks enough source context. For each judgment, record the existing belief compared, the new relation/tension, the missing source/context, and confidence. For traces that name only a conversation, inspect the actual originating message before marking a proposal novel or supported.

Deployment review remains separate. Confirm exact production build/config and migrations 064–069, complete the T15 independent human anchor before setting semantic acceptance targets, and require full-window receipts for nomination, abstention, defer/retain, and human disposition. Rehearse rollback while preserving additive receipts. Keep origin flags disabled until the explicit T18 release decision.
