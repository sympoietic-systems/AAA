# ADR-020: Resumable Indexing and Startup Background Scheduler

**Date:** 2026-06-02  
**Status:** accepted  
**Deciders:** Antigravity (Dev Agent), Interlocutor (User)

## Context

When indexing large files or books, the server could be restarted, causing the ingestion process to halt. Under the legacy implementation, restarting required re-uploading the file and re-indexing it entirely from scratch. This led to high token costs and latency because:
1. Uploaded file contents were not cached on disk.
2. Ingestion was fully sequential without concurrency limits.
3. Chat metabolisms that were interrupted could be missed.

To solve this, we need a resumable indexing pipeline that persists files, checks database chunks incrementally, runs concurrent workers for chunk indexing, and catches up on unprocessed items on startup.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Pure DB-backed queue** | Very robust transaction tracking | High implementation overhead; requires database migrations and state engines |
| **Disk Cache + Incremental Chunk Checks + Startup Scheduler** (selected) | Simple, cost-effective, avoids redundant embeddings/scoring, catches up automatically | Requires cleaning up disk files manually on file deletion |
| **Always start over** | Extremely simple | High API cost, poor UX, blocks chat for long periods |

## Decision

1. **Upload Cache Persistence**: Save uploaded file bytes to `backend/data/uploads/{conversation_id}/{file_name}`. When deleting files, also delete them from the cache directory.
2. **Incremental Indexing Checks**: Compare generated text chunks with existing records in `perception_sediment` sequentially. On the first mismatch or new chunk, truncate the database from that index onwards and only index the remaining chunks.
3. **Bounded Concurrency**: Index remaining chunks in parallel using an `asyncio.Semaphore` (bounded by `max_concurrent_chunk_workers`, default `8`).
4. **FastAPI Lifespan Startup Scheduler**: Initialize `BackgroundStartupScheduler` in the FastAPI lifespan phase. The scheduler runs multiple catch-up cycles in order:
   - **File Indexing Resumption**: Checks for files in `"uploading"`, `"processing"`, or `"error"` states. If their source cache is on disk, re-queues them.
   - **Structural Signature Backfill**: Scans for messages with `NULL` structural signatures and computes them via lexicon+topology scoring (no LLM). This ensures belief metabolism can run on legacy messages.
   - **Conversation Metrics Backfill**: Scans for messages missing conversation metrics rows and computes them per-conversation in chronological order, including assistant/dream responses with proper embeddings.
   - **Belief Metabolism Catch-up**: Queries for completed chat turns that have not been processed by the belief engine and runs `belief_metabolism.metabolize` on them.
5. **Scheduler Status Endpoint & UI Panel**: Added `GET /api/scheduler/status` endpoint to expose scheduler progression metrics (tasks found, completed, failed, active indexing job names) and integrated a collapsible "Scheduler" section in the right-hand UI `SidePanel.tsx` that polls the status every 10 seconds.
6. **Periodic Sweep**: After initial catch-up, the scheduler runs a continuous loop checking every 60 seconds for new gaps in structural signatures, conversation metrics, or belief metabolism turns.

## Changes since original acceptance (2026-06-05)

- **Structural signature backfill**: `_backfill_structural_signatures()` added to fill `NULL` structural signatures on legacy/antigravity/dream messages.
- **Conversation metrics backfill**: `_backfill_conversation_metrics()` added to compute metrics for ALL messages (human + apparatus) that lack them, including proper response-text embeddings for assistant messages.
- **Periodic sweep loop**: `_periodic_sweep()` re-checks for gaps every 60 seconds to self-heal any new misses.
- **Assistant embedding correction**: Assistant messages now receive their own response-text embedding (previously inherited the user's embedding), enabling meaningful agent_self_divergence and coupling_coherence metrics.

## Consequences

**Positive:**
- **Robustness** — Server restarts no longer break indexing; processing resumes from cache.
- **Cost/Token Efficiency** — Identical chunks are reused, minimizing embedder and structural scorer API usage.
- **Concurrency** — Speed is increased by indexing chunks in parallel.
- **Observability** — Real-time progress monitoring of startup background tasks and belief metabolism catchup directly in the UI.

**Negative:**
- Cached files consume disk space until the files are deleted.
- Parallel LLM queries could hit rate limits if the concurrency limit is set too high.
