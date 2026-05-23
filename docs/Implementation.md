

# Implementation Roadmap

### Phase 1: The Bare-Metal Loop (The Base Driver) ✅
*   **Goal:** Establish local embedding generation, database persistence, and standard LLM API communication.
*   **Deliverables:** SQLite database schema for raw messages, local embedding utility, and a simple loop script.
*   **Status:** Done

### Phase 2: The Homeostatic Regulator (The Entropy Engine) ✅
*   **Goal:** Compute live conversational metrics and let them dynamically alter generation parameters.
*   **Deliverables:** Entropy calculation utility (cosine similarity between consecutive inputs), dynamic parameter mapping (adjusting `temperature` and `presence_penalty` based on entropy).
*   **Status:** Done — `ConversationMetricsModule` (15 metrics), `HomeostaticRegulatorModule`, scoped to conversation_id

### Phase 3: The Rhizomatic Memory Engine (The Sedimentation Layer) 🔶 Partial
*   **Goal:** Group dense interactions into "Semantic Knots" and implement diffractive retrieval [1, 3].
*   **Deliverables:**
    *   ✅ Multi-conversation architecture (`conversations` table, `conversation_id` FK)
    *   ✅ Cross-conversation embedding similarity retrieval (`SedimentationRetrievalModule`)
    *   ✅ Token tracking and budget enforcement
    *   ✅ Diffractive Index (δ) query algorithm for non-linear context *(Implemented via DiffractiveRetrievalModule)*
    *   🔜 Semantic Knots — compaction of dense interactions into permanent nodes
    *   🔜 Graph/vector store integration (LanceDB, Graphiti, or FAISS)

### Phase 4: Foundational Memory (Ontological Bifurcation)
*   **Goal:** Codify the self-schema and handle belief recalibration [4].
*   **Deliverables:** Core belief graph validation, schema-matching evaluations to trigger deterritorialization updates [4].
