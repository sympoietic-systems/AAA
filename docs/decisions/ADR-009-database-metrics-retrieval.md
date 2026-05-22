# ADR-009: Database Metrics Retrieval and Test Integrity

**Date:** 2026-05-22  
**Status:** accepted  
**Deciders:** antigravity, Vasily  

## Context

While implementing the conversation-scoped sediment retrieval for conversation metrics (from ADR-008), we encountered two critical database-related issues during test execution:

1. **Null Metrics on Agent Responses**: 
   A naive retrieval of prior metrics using `MessageRepository.get_recent_with_metrics(limit=1, conversation_id=conversation_id)` returns the absolute latest conversation log entry. In the conversational loop, the latest log entry is always the preceding agent response (`speaker="apparatus"`). Because metrics are only processed and stored on user input messages, the agent response records have `NULL` metrics. This caused `prev_mpi` and other prior metrics to resolve to `None` on the subsequent turn, breaking calculations (such as boringness) and causing assertion failures.

2. **Foreign Key Violation in Test Setup**: 
   Both `test_allostatic_metrics.py` and `test_step5_context.py` threw `sqlite3.IntegrityError: FOREIGN KEY constraint failed` when attempting to clear the database. This occurred because they attempted to delete records from `conversation_log` before clearing `conversation_metrics`, which references `conversation_log(id)` via a foreign key constraint.

## Options Considered

### 1. Prior Metrics Lookup

*   **Option A (Query Filtered by Metrics Existence)**: Write a new database helper query or adjust the existing one to return only messages that have associated metrics (`INNER JOIN` or `WHERE s_t IS NOT NULL`).
    *   *Pros*: Offloads filtering to SQLite.
    *   *Cons*: Overcomplicates the repository with single-use queries; `get_recent_with_metrics` is already standard and expects to return all turns (including agent ones) for frontend history.
*   **Option B (Backward Scan in Python) [Selected]**: Query for the last 5 turns via the existing `get_recent_with_metrics(limit=5)` and scan them from newest to oldest in Python to locate the first entry with valid metrics (`turn.get("s_t") is not None`).
    *   *Pros*: Clean, uses existing repository methods, and is highly robust to variations in the message flow (e.g. multiple consecutive agent messages or system messages).
    *   *Cons*: Slightly higher memory footprint in Python (trivial for 5 dicts).

### 2. Foreign Key Test Cleanup

*   **Option A (Disable Foreign Keys temporarily)**: Run `PRAGMA foreign_keys=OFF` before clearing the tables, then re-enable it.
    *   *Pros*: Order of deletion doesn't matter.
    *   *Cons*: Hides schema integrity errors; bad practice in database testing.
*   **Option B (Ordered Deletion) [Selected]**: Delete from the child table (`conversation_metrics`) before the parent table (`conversation_log`).
    *   *Pros*: Honors schema constraints naturally and keeps testing configuration identical to production.

## Decision

We decided to:
1. Fetch up to 5 recent turns from `get_recent_with_metrics` and scan backward to locate the first message with valid metrics.
2. Correct the delete statements in test scripts to wipe child tables first.

## Consequences

*   **Correct Continuity**: Paskian metrics (e.g., lagged mutual perturbation in boringness, divergence resolution ratio) now correctly track across turns, surviving server restarts and maintaining conversation boundaries.
*   **Test Stability**: The test suite runs successfully without database state contamination or constraint violations.
