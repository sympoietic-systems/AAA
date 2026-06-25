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
    asset_type      TEXT NOT NULL,      -- 'conversation_message' | 'research_task' | 'research_step'
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

**Unified query** (`get_notes_by_task_with_steps`):
```sql
SELECT n.*, s.step_number, s.step_type
FROM notes n
LEFT JOIN research_steps s ON n.asset_type = 'research_step' AND n.asset_id = s.id
WHERE (n.asset_type = 'research_task' AND n.asset_id = ?)
   OR (n.asset_type = 'research_step' AND n.asset_id IN (
       SELECT id FROM research_steps WHERE task_id = ?
   ))
ORDER BY n.created_at ASC
```

### Asset Types

| `asset_type`          | `asset_id`                    | Inline `<mark>` injection | LLM context entanglement |
|------------------------|------------------------------|--------------------------|--------------------------|
| `conversation_message` | message ID (as text)         | Yes (backend-side)       | Yes (shared notes only) |
| `research_task`        | research task ID             | Yes (client-side via NotableMarkdown) | No                       |
| `research_step`         | research step ID             | Yes (client-side via NotableContent DOM highlighting) | No                       |

### Backward Compatibility

- Old endpoints `/conversations/{id}/notes` remain operational — they delegate to the unified table internally
- Existing note data is auto-migrated from `conversation_notes` → `notes` during `m041_unified_notes`
- `NoteInfo` type extended with `asset_type`, `asset_id`, `conversation_id` fields; old consumers updated

### Frontend Architecture

- **`useNotes(assetType, assetId)`** — generic hook for loading notes on any asset
- **`useConversationNotes(conversationId)`** — thin wrapper preserving the old `addNote(messageId, text, ...)` API
- **`NotesSection`** — reusable component serving both conversation and research views
- **`NotableMarkdown`** — wrapper encapsulating markdown rendering, highlighting, selection, toolbar, popover, and Content/Notes sub-tabs. Used by `ResearchTaskPage` report tab and `StepResultTab` synthesize step
- **`NotableContent`** — wrapper for non-markdown JSX content blocks. Enables text selection → note creation and DOM-based inline highlighting (TreeWalker + text node wrapping) with click-to-edit on marks. Used by `StepResultTab` reflect step sections (consolidated analysis, key insights, gaps, queries)
- **`noteHighlight.ts`** — client-side text wrapping utility for research content (no backend content mutation)
- **Research export** — separate `GET /research/tasks/{id}/export` producing markdown with notes section
- **Unified notes** — `GET /research/tasks/{id}/notes/unified` aggregates task-level + all step-level notes with step metadata via a single SQL JOIN. Rendered in `ResearchTaskPage`'s Notes tab with goto navigation (report for task notes, step selection for step notes) and markdown export

## Consequences

### What becomes easier?

- Adding notes to any text-bearing entity in the system by adding a new `asset_type` value and no DB changes
- Reusing the same UI components (NotesSection, SelectionToolbar, NoteEditorPopover) across asset types
- Exporting research reports with inline notes
- Annotating research step results (digest learnings, reflect insights/gaps) alongside final reports
- Cross-referencing all notes on a research task from a single unified view with goto links

### What becomes harder?

- No FK enforcement on `asset_id` — app-level validation required
- Backward compat layer adds some indirection in the routes
- Client-side highlighting for research content must handle markdown formatting edge cases (no server-side splitting as with conversation messages)
- DOM-based highlighting (NotableContent) must clear and re-apply marks on every notes change; overlapping text selections across notes are not visually layered

### Migration safety

- `m041` creates the new table, copies data, drops the old table in a single transaction-safe migration
- The migration runner executes `m012_conversation_notes` first (creating the old table if it doesn't exist), then `m041_unified_notes` (migrating and dropping it)
- On fresh installs, `m012` creates an empty `conversation_notes`, `m041` drops it immediately
