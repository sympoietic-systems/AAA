# ADR-052: Unified Polymorphic Notes System

**Date:** 2026-06-25  
**Status:** accepted  
**Deciders:** Antigravity, Interlocutor

## Context

The notes system (ADR-024) was designed exclusively for conversation messages, using a `conversation_notes` table with hard FK ties to `conversations.id` and `conversation_log.id`. As the research engine matured, users needed to annotate research reports, scraped assets, and synthesised findings with the same highlight-and-comment mechanism used in conversations.

Extending the existing schema would require either:
- Separate per-asset note tables (fragmentation, duplicated logic)
- Nullable columns on `conversation_notes` (semantic confusion when half the columns don't apply)

Neither scales to future asset types (belief entanglements, skill documentation, memory nodes).

## Decision

**Replace `conversation_notes` with a unified `notes` table using polymorphic `(asset_type, asset_id)` references.**

### Schema
```sql
CREATE TABLE notes (
    id              TEXT PRIMARY KEY,
    asset_type      TEXT NOT NULL,      -- 'conversation_message' | 'research_task'
    asset_id        TEXT NOT NULL,      -- primary key of the target asset
    conversation_id TEXT,               -- nullable; only for conversation-scoped notes
    selected_text   TEXT NOT NULL,
    comment         TEXT DEFAULT '',
    visibility      TEXT NOT NULL DEFAULT 'personal',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notes_conv  ON notes(conversation_id);
CREATE INDEX idx_notes_asset ON notes(asset_type, asset_id);
```

### Asset Types

| `asset_type`          | `asset_id`                    | Inline `<mark>` injection | LLM context entanglement |
|------------------------|------------------------------|--------------------------|--------------------------|
| `conversation_message` | message ID (as text)         | Yes (backend-side)       | Yes (shared notes only) |
| `research_task`        | research task ID             | No (client-side)         | No                       |

### Backward Compatibility

- Old endpoints `/conversations/{id}/notes` remain operational — they delegate to the unified table internally
- Existing note data is auto-migrated from `conversation_notes` → `notes` during `m041_unified_notes`
- `NoteInfo` type extended with `asset_type`, `asset_id`, `conversation_id` fields; old consumers updated

### Frontend Architecture

- **`useNotes(assetType, assetId)`** — generic hook for loading notes on any asset
- **`useConversationNotes(conversationId)`** — thin wrapper preserving the old `addNote(messageId, text, ...)` API
- **`NotesSection`** — reusable component serving both conversation and research views
- **`noteHighlight.ts`** — client-side text wrapping utility for research content (no backend content mutation)
- **Research export** — separate `GET /research/tasks/{id}/export` producing markdown with notes section

## Consequences

### What becomes easier?

- Adding notes to any text-bearing entity in the system by adding a new `asset_type` value and no DB changes
- Reusing the same UI components (NotesSection, SelectionToolbar, NoteEditorPopover) across asset types
- Exporting research reports with inline notes

### What becomes harder?

- No FK enforcement on `asset_id` — app-level validation required
- Backward compat layer adds some indirection in the routes
- Client-side highlighting for research content must handle markdown formatting edge cases (no server-side splitting as with conversation messages)

### Migration safety

- `m041` creates the new table, copies data, drops the old table in a single transaction-safe migration
- The migration runner executes `m012_conversation_notes` first (creating the old table if it doesn't exist), then `m041_unified_notes` (migrating and dropping it)
- On fresh installs, `m012` creates an empty `conversation_notes`, `m041` drops it immediately
