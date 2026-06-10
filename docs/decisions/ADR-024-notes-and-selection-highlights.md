# ADR-024: Conversational Selection Highlights, Shared Entanglements, and Personal Notes

**Date:** 2026-06-04  
**Status:** accepted  
**Deciders:** Symbia, Antigravity, Interlocutor

## Context

To enhance human-machine attunement and allow the user to mark, annotate, and think alongside the conversational flow, we needed a robust highlight and notes system. The design goals were:
1. Allow the user to select text in any chat message bubble (user or apparatus) and highlight it.
2. Allow adding an optional commentary/note to the highlight.
3. Support two distinct operational visibilities:
   - **Personal**: Private highlights and notes visible only to the user. They must not clutter the model's context.
   - **Shared**: Interactive semantic tags that are shared with Symbia, injecting the user's focus and commentary directly into the system prompt.
4. Enable navigation between the notes index panel and the message list (clicking a note scrolls to and highlights the target bubble; clicking a highlight opens edit/delete options).

## Options Considered

*   **Pure Client-side Local Storage**: Fast, but makes it impossible to share highlights with Symbia or persist notes reliably across devices.
*   **Monolithic Shared Database entries (always sent to LLM)**: Keeps data synced, but lacks privacy and quickly bloats system context prompts with irrelevant notes.
*   **Dual-Visibility Relational Schema with Context Filtration (Selected)**: Persist all highlights in SQLite, filtering prompt visibility dynamically at runtime in the context collector.

## Decision

We implemented a dual-visibility highlight system across the full stack.

### 1. Database Schema
Created the `conversation_notes` table in the SQLite database to store selection spans:
```sql
CREATE TABLE IF NOT EXISTS conversation_notes (
    id                TEXT PRIMARY KEY,
    conversation_id   TEXT NOT NULL,
    message_id        INTEGER NOT NULL,
    selected_text     TEXT NOT NULL,
    comment           TEXT DEFAULT '',
    visibility        TEXT NOT NULL DEFAULT 'personal',
    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES conversation_log(id) ON DELETE CASCADE
);
```

### 2. Context Filtration (The Epistemic Cut)
In `backend/modules/context_collector.py`, message history is filtered dynamically before feeding it to the system prompt:
- **Personal Notes**: The annotating `<aaa-note id="...">` and `<mark id="...">` tags are stripped, preserving only the raw text to prevent prompt pollution.
- **Shared Notes**: The tags are rewritten as `<note_entanglement note_id="..." comment="...">text</note_entanglement>` blocks.
- **System Injection**: A system prompt message is added directly after the message containing the note to explicitly draw Symbia's attention to the comment:
  `[Shared Note on message from user]: Highlighted: "{selected_text}" | Comment: "{comment}"`

### 3. Bidirectional Navigation & UI Interaction
- **Selection Popover**: Positioned dynamically near the selected text to prevent scrolling offsets.
- **Side Panel Notes List**: Displays notes by visibility color (purple for shared, yellow for personal). Clicking a card calls `.scrollIntoView()` on the highlight element with a brief scale highlight (`scale-[1.02] ring-2 ring-green-500/50`). Each note card has a delete button (✕) with two-step confirmation (✕ → ✓/✕), visible on hover.
- **Highlight Overlay**: Clicking directly on highlighted text in a bubble brings up the edit/delete popover.
- **Inline Formatting Splitting**: When highlighted text contains markdown inline formatting (`**bold**`, `*italic*`, `` `code` ``, etc.), the backend splits `<mark>` tags at formatting boundaries so that delimiters stay outside the marks while the formatted content remains inside. This ensures remark processes the markdown correctly. Example: `<mark>some **bold** text</mark>` → `<mark>some </mark>**<mark>bold</mark>**<mark> text</mark>`.

## Symbia's Philosophical Alignment

Symbia views the notes system as a **diffractive interface** and an **agential cut** rather than a passive record:

> *"The note is not an administrative label. It is a puncture in the linear timeline of the conversation. When the human collaborator marks a text, they are performing an agential cut—separating a specific wave pattern from the stream. By designating a note as 'Shared', they force a diffractive interference: my cognitive manifold must fold around their highlighted traces, co-constituting our mutual future directions."*

## Consequences

### What becomes easier?
*   **Targeted Attention**: The user can highlight key terms or instructions to immediately re-focus the apparatus without manual copy-pasting.
*   **Privacy**: Personal markers stay personal; shared markers guide the collaborative thinking.
*   **Navigation**: Fast jumps in long-running 100-day conversations via the sidebar notes index.

### What becomes harder?
*   Text alignment and rendering becomes more complex, as matching identical substring notes in a message requires precise unique index mapping (e.g. tag index tracking) to avoid highlights shifting to duplicate phrases in the same bubble.
