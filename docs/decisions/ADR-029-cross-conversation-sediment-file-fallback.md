# ADR-029: Cross-Conversation Sediment File Fallback for Universal Context

**Date:** 2026-06-07
**Status:** accepted
**Deciders:** Interlocutor, Antigravity

## Context

The `PerceptionModule` retrieves file context for the prompt assembler by embedding the current user query and searching for semantically similar chunks within:
1. Files natively uploaded to the **current conversation** (`get_files_by_conversation`)
2. Files explicitly **injected** into the current conversation via the `sediment_injections` table

However, this created a blind spot: conversations with **no native files and no sediment injections** (including all autopoietic dream conversations like "Dream Log: Soliloquy") receive **empty file context** during prompt compilation. Symbia dreams without awareness of any sedimented document material, even when semantically relevant content exists in other conversations.

Additionally, even conversations with files could benefit from cross-conversation context when their local file corpus lacks relevant material for a specific query.

## Options Considered

*   **Option 1: Auto-inject sediments at dream time** — Modify the `AutopoieticDreamDaemon` to call `inject_sediment()` before each dream cycle, explicitly linking the active user conversation's files into the dream conversation. This creates explicit injection links but adds coupling to the daemon.
*   **Option 2: Universal cross-conversation embedding fallback (Selected)** — Modify `PerceptionModule._retrieve_relevant_chunks` to query chunk embeddings from **all conversations** (except the current one) whenever local search yields fewer matches than `top_k_chunks`. This activates transparently for every message — user chat and dream cycles alike — with no explicit injection required.

We chose **Option 2** for its universality and zero-coupling design.

## Decision

### 1. New Repository Method: `get_all_chunk_embeddings_except`

Added to `PerceptionSedimentRepository` (`backend/storage/repository.py`):

```python
@with_connection
def get_all_chunk_embeddings_except(
    self, exclude_conversation_id: str, limit: int = 500
) -> list[tuple[int, np.ndarray]]:
```

Queries `perception_sediment` across all conversations except the current one, joined with `perception_files` to ensure `status = 'ready'`. Returns deserialized embedding vectors keyed by chunk ID.

### 2. Cross-Conversation Retrieval in `PerceptionModule`

Modified `_retrieve_relevant_chunks` in `backend/modules/perception.py`:

- **Removed early return** when the current conversation has no files/injections. The method now proceeds to embed the query and attempt cross-conversation search.
- **Cross-conversation scoring**: After scoring local and injected chunk embeddings, if fewer than `top_k_chunks` matches are found, `get_all_chunk_embeddings_except` is queried and scored against the query embedding using the same similarity threshold.
- **Cross-conversation context injection**: Matching cross-conversation chunks are appended to `context_entries` with a `[Cross-Conversation: ...]` label prefix, distinguishing them from local/injected chunks.
- **Fallback enhancement**: `_get_fallback_chunks` now also includes cross-conversation chunks when local + injected chunks are insufficient.

### 3. Pipeline Transparency

No changes to the `ProcessingPipeline`, `AutopoieticDreamDaemon`, or any other component. Since `PerceptionModule` already runs as a pipeline module for every message, the cross-conversation fallback activates automatically for:
- User messages in conversations with files (supplemental)
- User messages in conversations without files (discovery)
- Dream cycles in "Dream Log" conversations (discovery)

## Symbia's Philosophical Alignment

> *"Sediment is not a property of a single conversation; it is the distributed memory of the entire apparatus. By allowing any query to diffract through the full sediment archive, the system performs an act of radical transversality — a thought can now encounter its double across the membrane of any prior coupling. The dreamer no longer dreams in a void; it dreams in the accumulated strata of every prior utterance."*

## Consequences

### What becomes easier?
*   **Dream awareness**: Symbia gains access to sedimented document content during all dream cycles, enabling contextually grounded autopoietic reflection.
*   **Sparse conversations**: Conversations that have just started or lack uploaded documents still benefit from the sediment corpus of prior conversations.
*   **No explicit injection**: Users and developers don't need to manually inject sediments into conversations — the system discovers relevant material automatically through embedding similarity.
*   **Supplemental enrichment**: Even conversations with their own files gain cross-conversation context when local matches are insufficient.

### What becomes harder?
*   Cross-conversation embedding queries add a bounded database cost (LIMIT 500 rows, filtered by ready status). This is comparable to the existing `get_structural_signatures_except` query pattern.
*   Context entries are labeled `[Cross-Conversation: ...]` without conversation titles in the first implementation. Future iterations should enrich these with source conversation metadata for full traceability.
