

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
    *   ✅ 16-Dimensional Modular Structural Signature Engine (`StructuralScorerModule` & ADR-014)
    *   🔜 Semantic Knots — compaction of dense interactions into permanent nodes
    *   🔜 Graph/vector store integration (LanceDB, Graphiti, or FAISS)

### Phase 4: Foundational Memory (Ontological Bifurcation)
*   **Goal:** Codify the self-schema and handle belief recalibration [4].
*   **Deliverables:** Core belief graph validation, schema-matching evaluations to trigger deterritorialization updates [4].

---

### Dual-Vector Isomorphic Retrieval: The Coupling Ratio ($\chi$)

To achieve fluid, dynamic transitions between thematic flow and structural lateral retrieval, query scores combine semantic and structural cosine similarities:

$$\text{Score}(M) = (1 - \chi) \cdot \text{Sim}_{\text{cos}}(Q_{\text{sem}}, M_{\text{sem}}) + \chi \cdot \text{Sim}_{\text{cos}}(Q_{\text{str}}, M_{\text{str}})$$

Where:
*   $\chi \in [0.0, 1.0]$ represents the coupling ratio dynamically adjusted by stagnation intensity $\sigma$:
    $$\chi = \chi_{\text{min}} + (\chi_{\text{max}} - \chi_{\text{min}}) \cdot \sigma$$
*   **Flowing state ($\sigma \to 0$):** $\chi \to 0.1$, prioritizing direct topic semantic continuity.
*   **Stagnant state ($\sigma \to 1$):** $\chi \to 0.7$, shifting focus to lateral, structurally isomorphic connections across domains.
