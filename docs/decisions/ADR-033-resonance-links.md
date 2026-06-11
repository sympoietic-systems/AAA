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
        BgScan -->|check if link exists| LinkExists{Exists in DB?}
        LinkExists -->|Yes: Skip LLM| Skip[No-op]
        LinkExists -->|No: Run Cosine Sim > 0.82| MiniLLM[Mini LLM Validation Request]
        MiniLLM -->|if approved| DBProposed2[(DB message_links: status='proposed')]
    end

    subgraph Tier 3: Spectral suggestions (User-Driven)
        UserSelect[User selects node] -->|query parallel branches| API[GET /spectral-suggestions]
        API -->|display in sidebar| UI[Spectral Echoes UI Panel]
        UI -->|user click manual link| DBActive[(DB message_links: status='active')]
        UI -->|user click ignore| DBIgnore[(DB message_links: status='ignored')]
    end

    DBProposed1 -->|renders on cloud| Visualizer[Dashed Pulsing Line + Tooltip]
    DBProposed2 -->|renders on cloud| Visualizer
    Visualizer -->|human confirm| DBActive
    Visualizer -->|human dismiss| DBIgnore
```

### 1. Database Schema & Undirected Normalization (Migration `m019_resonance_links`)
* Extend the `message_links` table with:
  * `status TEXT NOT NULL DEFAULT 'active'` (values: `'active'`, `'proposed'`, `'ignored'`).
  * `justification TEXT DEFAULT ''` (to store the natural language reason for the resonance).
* **Undirected Key Constraining**: In `add_message_link`, source and target IDs are consistently ordered to construct the primary key `link_id = f"{min(source_id, target_id)}_{max(source_id, target_id)}_{link_type}"`. This prevents duplicate links from being created in opposite directions and allows $O(1)$ lookup checks.
* **Upsert Guard**: Conflicting writes default to keeping the existing `'active'` or `'ignored'` status rather than overwriting it with a new `'proposed'` scan.

### 2. Tier 1: Agential Tags (LLM-Initiated)
* System prompt guidelines instruct Symbia to output a `<resonance target="UUID">Reason</resonance>` block when she detects an echo with a past thread.
* The backend's [chat.py](file:///d:/AAA/backend/services/chat.py) extracts and strips this block from her text, inserting a provisional link in the database (`status = 'proposed'`).

### 3. Tier 2: Asynchronous Validation (The Resonance Scanner)
* Decoupled from the synchronous chat loop to prevent latency overhead.
* A background task triggers after message writing. It scans parallel branches for messages with cosine similarity $> 0.82$.
* **Pre-Check Cache**: Before calling the LLM validation API, the background task queries the database index via `message_repo.link_exists(message_a, message_b)`. If a link exists in the database with any status (`proposed`, `active`, or `ignored`), the LLM query is bypassed, guaranteeing each unique pair of messages is compared at most once.
* If validated, the link is persisted as `status = 'proposed'`.

### 4. Tier 3: Spectral Suggestions (User-Driven)
* A side-panel section **Spectral Echoes** appears when a node is selected.
* It fetches parallel messages with similarity $> 0.70$ (excluding direct ancestors) and displays them.
* **Linked/Ignored Filter**: The database query filters out any candidates that are already linked or ignored.
* **Confirm & Ignore Actions**: The user can click **Link Node** (manual active link) or **Ignore** (writes `status = 'ignored'` to the database, immediately hiding the suggestion from future lists and scans).

### 5. Interactive Canvas Tooltips & Ratification
* In [ConnectionCloud.tsx](file:///d:/AAA/frontend/src/components/ConnectionCloud.tsx), proposed links are rendered as **pulsing, semi-transparent dashed lines** on an HTML5 Canvas.
* Clicking a proposed link opens a popover showing the `justification` and buttons to **[Confirm]** (sets status to `'active'`) or **[Dismiss]** (sets status to `'ignored'` so it prunes it from view and ignores it for future scanner validation).

---

## Consequences

### Positive
* **Sympoietic Co-Curation**: The topology is co-authored. Symbia proposes connections, but they must be ratified by the human participant before becoming active navigability lines.
* **Zero Repeated Scans**: The combination of undirected link keys, `link_exists` caching, and `'ignored'` tombstoning ensures that message pairs are only ever compared once, minimizing API token consumption.
* **Clean Sidebar Suggestions**: Dismissing or creating links instantly removes them from suggestion panels, reducing UI noise.
* **Asynchronous Execution**: High-similarity scans and LLM validation run in the background, adding zero latency to the synchronous chat loop.

### Risks & Mitigations
* **Table/Row Pollution**: Ignored statuses keep rows in `message_links` forever. *Mitigation*: These rows are light (only metadata and small strings) and are indexed by primary key `id`, which performs extremely fast $O(1)$ point queries in SQLite, preventing any performance impact.
