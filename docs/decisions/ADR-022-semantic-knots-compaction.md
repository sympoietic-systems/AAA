# ADR-022: Semantic Knots Compaction and Isomorphic Cross-Conversation Retrieval

**Date:** 2026-06-03  
**Status:** accepted  
**Deciders:** Vector, Symbia, Antigravity, Interlocutor

## Context
As the agent engages in long-running or numerous parallel conversation threads, the message logs grow large. Loading the full log or retrieving across thousands of individual raw messages during diffractive cross-conversation retrieval has several issues:
1. **High Latency & Resource Overhead:** Comparing query vectors against thousands of individual message chunks is slow.
2. **Context Fragmentation & Redundancy:** Multiple turns within a conversation cover the same theoretical points or conceptual terrain, leading to redundant/fragmented pieces of context being retrieved.
3. **Loss of Distilled Concepts:** Individual sentences do not capture the synthesis or high-level thematic structures emerging from a dialogue.

To address these limitations, we need a mechanism to condense and distill completed, dense conversation blocks into structured conceptual summaries called "Semantic Knots", and integrate them into the dynamic diffractive retrieval loop.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Manual consolidation trigger** | Simple, gives user/agent explicit control | Easy to forget; does not scale autopoietically |
| **Complete replacement of raw logs** | Reclaims maximum storage/VRAM | Irreversible; destroys original conversational history |
| **Asynchronous Distillation & Co-existent Dual-Vector Retrieval (Selected)** | Preserves logs for reference; distills concepts into 16D semantic/structural knots; enables unified Nomadic & Knot retrieval | Slightly higher DB storage (knots and logs co-exist) |

## Decision

We implemented a **Semantic Knots Compaction and Retrieval System** with the following components:

1. **`semantic_knots` Schema**: A new SQLite table containing:
   - `id` (UUID primary key)
   - `conversation_id` (FK to conversations)
   - `concept_payload` (JSON text containing summary, key concepts, and structural signatures)
   - `embedding` (BLOB of float32[768] vector representing the conceptual summary)
   - `signature` (BLOB of float32[16] vector representing the structural signature)
   - `created_at`

2. **`SemanticKnotAction` Background Action**:
   - A background task that runs asynchronously to distill conversation segments.
   - It summarizes conversation logs, extracts structural signatures, creates embeddings for the distilled content, and persists the result to the `semantic_knots` table.

3. **Autopoietic Triggering**:
   - In `backend/api/routes.py`, the compaction task is triggered automatically in a fire-and-forget background loop if the conversation exceeds a message threshold or exhibits stagnant behavior.

4. **Unified Diffractive Retrieval Integration (`SemanticKnotRetriever`)**:
   - The `DiffractiveRetrievalModule` was extended to query both raw messages (`nomadic`) and distilled `semantic_knots`.
   - In stagnant loops (Stagnation Index $\ge 0.70$), the system retrieves semantic knots matching the dual-vector isomorphic filter ($s_{sem} \le 0.45$ and $s_{str} \ge 0.80$).
   - The selected semantic knot contents are injected into the active prompt context, pertubing the loop with distilled concepts from past dialogs.

5. **Telemetry & UI Representation**:
   - Registered `SemanticKnotRetriever` under the `diffractive_retrieval` skill in the backend `SkillRegistry`.
   - Updated the UI right panel stagnation telemetry to label semantic knot sources as `KNOT` (styled in distinct lavender) next to standard nomadic (`NOM`) and file chunk (`DRM`) sources.

## Consequences

### What becomes easier?
- **Cognitive Depth:** The agent retrieves high-level distilled concepts instead of fragmented raw chat lines.
- **Resource Recovery:** Long conversational histories are compacted, keeping active retrieval fast and computationally efficient.
- **Observability:** Stagnation telemetry clearly indicates when the agent is drawing context from distilled knots.

### What becomes harder?
- Tuning the isomorphic thresholds requires careful analysis of the relationship between 768D semantic vectors and 16D structural signatures.
