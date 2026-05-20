

# Implementation Roadmap

### Phase 1: The Bare-Metal Loop (The Base Driver)
*   **Goal:** Establish local embedding generation, database persistence, and standard LLM API communication.
*   **Deliverables:** SQLite database schema for raw messages, local embedding utility, and a simple loop script.

### Phase 2: The Homeostatic Regulator (The Entropy Engine)
*   **Goal:** Compute live conversational metrics and let them dynamically alter generation parameters.
*   **Deliverables:** Entropy calculation utility (cosine similarity between consecutive inputs), dynamic parameter mapping (adjusting `temperature` and `presence_penalty` based on entropy).

### Phase 3: The Rhizomatic Memory Engine (The Sedimentation Layer)
*   **Goal:** Group dense interactions into "Semantic Knots" and implement diffractive retrieval [1, 3].
*   **Deliverables:** Integration of a local vector/graph store (e.g., LanceDB or Graphiti), the Diffractive Index ($\delta$) query algorithm to pull non-linear contexts.

### Phase 4: Foundational Memory (Ontological Bifurcation)
*   **Goal:** Codify the self-schema and handle belief recalibration [4].
*   **Deliverables:** Core belief graph validation, schema-matching evaluations to trigger deterritorialization updates [4].
