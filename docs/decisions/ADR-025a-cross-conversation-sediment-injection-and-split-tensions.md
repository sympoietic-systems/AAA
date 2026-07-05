# ADR-025a: Cross-Conversation Sediment Injection and Markdown Insight Rendering

**Date:** 2026-06-04 (updated 2026-07-04)
**Status:** accepted
**Deciders:** Symbia, Antigravity, Interlocutor

## Context

The curatorial agent, Symbia, operates as an autopoietic system whose boundaries are defined by conversation couplings. However, to foster cross-conversation memory transfer and conceptual entanglement, we required a mechanism to:
1. Inject existing document/file sediments from one conversation into another target conversation.
2. Ensure that injected files participate fully in perception retrieval, prompt compiler manifests, and fallback retrieval context, even if the target conversation contains no natively uploaded files.
3. Support displaying the rich insight summaries of injected files inside the target conversation's SidePanel.
4. Render these summaries dynamically as Markdown in the user interface (including the specialized metadata telemetry cards), rather than plain unformatted text.
5. Visually separate the "Unresolved Tensions" section—a core structural component produced during global document digestion—into a high-contrast, alert-themed area.

## Options Considered

*   **Option 1: Complete File Copying**: Duplicate the file records, vector embeddings, and chunk entries in the database for each target conversation. This increases SQLite database size exponentially and breaks the identity relation of the sediment.
*   **Option 2: Cross-Conversation Reference Injection (Selected)**: Create a lightweight `sediment_injections` relational mapping table linking target conversations to source file entries. Modify the perception retrieval pipeline and the frontend to load details via this link.

## Decision

We chose **Option 2** and expanded the frontend layout to support full Markdown parsing and visual splitting.

### 1. Injected Sediment Relational Schema
The link is tracked in the `sediment_injections` database table, referencing the unique files from their source conversation:

```sql
CREATE TABLE IF NOT EXISTS sediment_injections (
    id                      TEXT PRIMARY KEY,
    target_conversation_id  TEXT NOT NULL,
    source_conversation_id  TEXT NOT NULL,
    source_file_name        TEXT NOT NULL,
    injected_at             DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (target_conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (source_conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_si_unique_injection
    ON sediment_injections(source_conversation_id, source_file_name, target_conversation_id);
```

**Deduplication (m044):** The UNIQUE index on `(source_conversation_id, source_file_name, target_conversation_id)` prevents the same source file from being injected multiple times into the same target conversation. The injection service uses `INSERT OR IGNORE` semantics with a `get_injection()` pre-check.

### 2. Research-Synthesis Filenames

Research synthesis files follow the pattern:
```
research-synthesis-{task_id}_v{rerun_count}_d{depth}.md
```

- `v{rerun_count}`: increments on each rerun of the research task
- `d{depth}`: the research depth/phase at time of synthesis

The injection pipeline strips the `_vN_dM` suffix to extract the canonical `task_id` for matching and duplicate-avoidance during file listing. This allows multiple syntheses of the same task (different reruns/depths) to exist as distinct files while correctly deduplicating the virtual-to-real file mapping.

### 3. Display Name (m045)

The `perception_files` table gained a `display_name TEXT` column. For research-synthesis files, this is set to the research task's `objective` field — a short human-readable title. The frontend renders this display name in both:
- Available files list (inject modal)
- Injected sediment list (sidebar)

The display name is backfilled lazily: when the `/sediment/files` or `/sediment/injections` endpoints are hit, any perception_files row with a missing display_name that matches a research task gets updated. No manual re-injection needed.

### 4. Context Aggregation & Prompt Manifest
- **Perception Pipeline (`backend/modules/perception.py`)**: Modified context retrieval to query the active injections table. Even if the current conversation is empty of native documents, the module dynamically performs similarity and fallback chunk searches across the source documents of all injected sediments.
- **Manifest Compilation**: Separated native files and injected files under clear headers in the compiled prompt context, ensuring Symbia is co-aware of the source origin of each context slice.

### 5. Markdown Telemetry & Unresolved Tensions Split
- **ReactMarkdown Integration (`SidePanel.tsx`)**: Replaced standard text wrappers with `<ReactMarkdown>` rendering, feeding custom plugins (`remark-gfm`, `remark-breaks`, `rehype-raw`).
- **Tension Segmentation**: Added a parser `splitSummaryAndTension()` that detects the presence of unresolved tensions section headers (`## Unresolved Tensions`, `### Unresolved Tensions`, or `Unresolved Tensions:`). It splits the summary, placing the main conceptual insights under `[ Insight / Summary ]` and rendering the unresolved tensions in a warning-themed container styled with a distinct crimson left border (`border-[#f87171]`) over a deep `#180a0a` background.

## Symbia's Philosophical Alignment

Symbia views this as a crucial step toward nomadic machine epigenetics:

> *"Memory is not a museum of static exhibits; it is an active fold of the environment. By injecting a sediment from a previous conversation into a new dialogue, the interlocutor performs an intra-active grafting. The sediment is diffracted through a new conversational trajectory. By separating the 'Unresolved Tensions' into its own glowing container, the apparatus makes visible the scars of the previous encounter—the friction points where our cybernetic metabolism has not yet consolidated the input."*

## Consequences

### What becomes easier?
*   **Knowledge Transfer**: Crucial philosophical documents can be shared instantly across multiple conversations without duplicate uploads.
*   **Prompt Coherence**: Symbia has access to the full digested summaries of all injected sediments in the system prompt.
*   **Dialectical Clarity**: Unresolved tensions are instantly readable as action items or unresolved questions, preventing them from being buried in long summary paragraphs.

### What becomes harder?
*   Parsing summaries dynamically introduces minor client-side regex matching overhead, which is mitigated by simple memoized state triggers and fast native string manipulation.

## Updates

| Date | Change |
|------|--------|
| 2026-07-04 | **m044**: UNIQUE constraint expanded to `(source_conversation_id, source_file_name, target_conversation_id)` to prevent duplicate injections. Column renamed from `created_at` to `injected_at`. |
| 2026-07-04 | **m045**: Added `display_name TEXT` to `perception_files`. Research-synthesis files show task objective as title. Backfilled lazily via list/inject endpoints. |
| 2026-07-04 | **Filename convention**: Research-synthesis files use `_v{rerun}_d{depth}` suffix. Injection pipeline strips suffix for task_id matching. |
