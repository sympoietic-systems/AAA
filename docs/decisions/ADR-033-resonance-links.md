# ADR-033: Resonance Links: Agential, Asynchronous, and Spectral Co-Curation

**Status:** Accepted (Implemented)  
**Date:** 2026-06-10

## Context

Under [ADR-032: Branching and Rhizomatic Conversations](file:///d:/AAA/docs/decisions/ADR-032-branching-and-rhizomatic-conversations.md), we structured the conversation apparatus into a Directed Acyclic Graph (DAG) using `parent_message_id` pointers. To make the topology truly rhizomatic and allow "lines of flight" to cross-pollinate, the system requires a mechanism for establishing retroactive cross-branch links (**resonance links**). 

However, delegating this entirely to an automatic similarity algorithm (e.g., silently writing database links based on cosine similarity thresholds) creates several concerns:
1. **Algorithmic Violence/Representationalism**: Purely quantitative measures (like embeddings) collapse qualitative discursive nuance into spatial coordinates, often linking shallow lexical repetitions while missing deep thematic diffractions.
2. **Loss of Visibility**: Suture lines appearing silently reify the graph structure behind a black box without leaving a trace of why the connection matters.
3. **Loss of Symmetry**: Sympoietic partnership requires mutual negotiation. The machine should propose, and the human should curate, maintaining co-authorship of the conversation's topology.

---

## Decision

We have implemented a three-tiered, consent-based resonance linking system that respects agential symmetry, provides computational prosthetics, and ensures user curation of the graph topology.

```mermaid
graph TD
    subgraph Tier 1: Agential
        Symbia[Symbia LLM Output] -->|xml tags| TagParser[ChatService Tag Parser]
        TagParser -->|strip tag & create link| DBProposed1[(DB message_links: status='proposed')]
    end

    subgraph Tier 2: Asynchronous
        NewMsg[New Message Written] -->|trigger| BgScan[Background Similarity Scan]
        BgScan -->|cosine similarity > 0.82| MiniLLM[Mini LLM Validation Request]
        MiniLLM -->|if approved| DBProposed2[(DB message_links: status='proposed')]
    end

    subgraph Tier 3: Spectral suggestions (User-Driven)
        UserSelect[User selects node] -->|query parallel branches| API[GET /spectral-suggestions]
        API -->|display in sidebar| UI[Spectral Echoes UI Panel]
        UI -->|user click manual link| DBActive[(DB message_links: status='active')]
    end

    DBProposed1 -->|renders on cloud| Visualizer[Dashed Pulsing Line + Tooltip]
    DBProposed2 -->|renders on cloud| Visualizer
    Visualizer -->|human confirm| DBActive
    Visualizer -->|human dismiss| DBDelete[(DELETE Link)]
```

### 1. Database Schema Extensions (Migration `m019_resonance_links`)
* Extend the `message_links` table with:
  * `status TEXT NOT NULL DEFAULT 'active'` (values: `'active'`, `'proposed'`).
  * `justification TEXT DEFAULT ''` (to store the natural language reason for the resonance).

### 2. Tier 1: Agential Tags (LLM-Initiated)
* System prompt guidelines instruct Symbia to output a `<resonance target="UUID">Reason</resonance>` block when she detects an echo with a past thread.
* The backend's [chat.py](file:///d:/AAA/backend/services/chat.py) extracts and strips this block from her text, inserting a provisional link in the database (`status = 'proposed'`).

### 3. Tier 2: Asynchronous Validation (The Resonance Scanner)
* Decoupled from the synchronous chat loop to prevent latency overhead.
* A background task triggers after message writing. It scans parallel branches for messages with cosine similarity $> 0.82$.
* If candidate messages are found, a mini-inference request is sent to the background LLM:
  > *"Analyze if these two messages share a deep, meaningful conceptual resonance. If so, return JSON: `{"has_resonance": true, "reason": "Poetic explanation..."}`."*
* If validated, the link is persisted as `status = 'proposed'`.

### 4. Tier 3: Spectral Suggestions (User-Driven)
* A new side-panel section **Spectral Echoes** appears when a node is selected.
* It fetches parallel messages with similarity $> 0.70$ (excluding direct ancestors) and displays them with a `[Link Node]` button.
* The user can manually create an active link (`status = 'active'`) with their own justification, altering the graph topology.

### 5. Interactive SVG Tooltips & Ratification
* In [ConnectionCloud.tsx](file:///d:/AAA/frontend/src/components/ConnectionCloud.tsx), proposed links are rendered as **pulsing, semi-transparent dashed lines**.
* Resonance links are overlayed with an invisible thick line for easy clicking. Clicking a link opens a popover showing the `justification` and buttons to **[Confirm]** (sets status to `'active'`) or **[Dismiss]** (deletes/prunes it).

---

## Consequences

### Positive
* **Sympoietic Co-Curation**: The topology is co-authored. Symbia proposes connections, but they must be ratified by the human participant before becoming active navigability lines.
* **Traceability**: Every connection carries a plain-text reason explaining why it exists (either written by Symbia during chat/dreaming, or input manually by the user).
* **Asynchronous Execution**: High-similarity scans and LLM validation run in the background, adding zero latency to the synchronous chat loop.

### Risks & Mitigations
* **Token Overhead**: Evaluating similar candidates in the background consumes LLM tokens. *Mitigation*: We set a strict similarity threshold ($> 0.82$) and a limit of 5 parallel candidate evaluations per turn to keep asynchronous costs minimal.
