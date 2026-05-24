# ADR-015: Error Propagation and Manual Reprocessing for File Ingestion

**Date:** 2026-05-24
**Status:** accepted
**Deciders:** Vector, aaa project

## Context

During background file processing (digestion & synthesis in the `SummarizeAction`), API rate limits or model pool exhaustion errors were caught locally and appended to the file's summary text (e.g., `"Plateau 1 error: All models in pool exhausted..."`). As a result:
1. The file was incorrectly marked as `"ready"` rather than failed.
2. A system chat message containing the model exhaustion stack trace was inserted into the conversation.
3. The user could not trigger a retry because the file was marked as successfully ingested.

We need a clean, UI-driven solution that:
- Surfaces LLM errors to the system and changes the file's status to `"error"`.
- Prevents system chat pollution by omitting system messages on failed ingestion.
- Enables manual, single-click reprocessing in the frontend without requiring the user to delete, re-upload, and re-embed the file.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **1. Swallowed errors with status flags** | Easy to implement. | Pollutes chat logs with stack traces; hides actual ingestion failures under a "ready" status. |
| **2. Full event queue with automatic retries / backoff** | Fully automated. | Introduces heavy state tracking, scheduling complexity, and database overhead. |
| **3. Propagation with manual UI-triggered reprocessing** | Simple, robust, leverages existing database chunk sediment, and gives the user control over when to retry. | Requires exposing a new reprocess API route and updating UI panel actions. |

## Decision

We chose **Option 3: Exception Propagation with Manual Reprocessing**.

### 1. Backend Error Propagation
We modified `SummarizeAction.execute()` to raise exceptions upon encountering API errors or model pool exhaustion.
The background runner `_process_and_summarize_file` catches these exceptions, writes the error context to the error log database, and updates the file's status to `"error"`. The execution is aborted before any system messages are generated.

### 2. Manual Reprocessing Endpoint
Because chunk extraction and vector embedding are successfully persisted in `perception_sediment` before summarization takes place, a retry does not need to re-upload or re-chunk the file. We added a new endpoint:
```
POST /api/conversations/{conversation_id}/files/{file_name}/reprocess
```
This endpoint fetches existing chunks by filename, reconstructs the `extracted_text` in sequential chunk order, and runs the `SummarizeAction` background task again.

### 3. Frontend Retry Button
We updated the `SidePanel` component to render a "retry" action button next to files in the `"error"` status. Clicking this button triggers the reprocessing route and restarts polling.

## Consequences

- **Cleaner Chat Flow:** Model exhaustion messages no longer leak into system chat messages.
- **Resource Efficiency:** Reprocessing skips file uploads and chunk/embedding generation, avoiding duplicate embedding model calls and database writes.
- **Improved UX:** Indexing issues are clearly surfaced, and manual retry allows recovering from temporary rate-limits with a single click.
