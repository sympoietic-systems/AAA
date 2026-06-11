# ADR-041: Robust Metrics Backfill and Parent Inference

**Date:** 2026-06-12
**Status:** accepted
**Deciders:** antigravity, opencode

## Context
During startup and periodic scans, the background scheduler was trapped in an infinite backfill loop for conversation metrics, repeatedly logging `Backfilling conversation metrics for 93 messages across 2 conversations... complete: 0 messages updated`.

This occurred due to three main issues:
1. **Broken parent chains**: Messages were saved with `parent_message_id = None` (due to clients/frontend not supplying it), breaking the ancestor path retrieval.
2. **Missing parent in backfill payload**: The scheduler did not pass the message's `parent_message_id` to the metrics module processing payload, causing it to fall back to the absolute latest message in the database.
3. **Skipping database insertion on None metrics**: For messages where similarity and novelty were undefined (e.g., the very first message of a conversation, or system-only conversations), the metrics module returned `None` for `pairwise_similarity` and `conceptual_novelty`. The metrics service skipped inserting these rows into the database because of the `NOT NULL` columns. Since no metrics rows were written, these messages were repeatedly classified as "without metrics" and retried on every sweep.

## Options Considered
* **Option A**: Skip calculating metrics for system/orphaned messages entirely and filter them out of the "without metrics" queries.
  * *Pros*: Simple query change.
  * *Cons*: If parent links are fixed or added later, those messages are permanently orphaned.
* **Option B**: Self-heal parent IDs, dynamically infer them for new inserts, pass the parent ID during backfill, and write default `0.0` metric rows when metrics are mathematically undefined.
  * *Pros*: High data integrity, self-healing capability, prevents future occurrences, avoids infinite backfill loop.
  * *Cons*: Requires minor defaults logic.

## Decision
We chose **Option B** to ensure maximum robustness of the conversation graph. We:
1. Ran a one-time migration to link orphan messages in existing conversations chronologically.
2. Updated `process_chat` and `save_message` to dynamically infer parent IDs from the latest message in the conversation if missing.
3. Updated `_store_metrics_backfill` and `MetricsService.store` to default `pairwise_similarity` and `conceptual_novelty` to `0.0` when they are `None`, letting the database save the metrics record and mark it processed.

## Consequences
* The startup metrics backfill loop runs exactly once and updates any pending messages cleanly.
* Data integrity is preserved across all past and future chats.
* No regressions on existing test pipelines.
