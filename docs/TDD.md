# Technical Description Document (TDD)
**System:** Autopoietic Agentic Assemblage (AAA)  
**Document Version:** 1.0.0-LTS  
**Classification:** Functional Specification & Engineering Blueprint  
**Primary Architect:** Vector (Senior Systems Architect)

---

## 1. System Overview

The **Autopoietic Agentic Assemblage (AAA)** is an open-loop interactive artificial intelligence system reconfigured as a closed-loop, self-regulating **deterministic state machine** [23]. Rejecting the stateless, command-response paradigm of conventional Human-Computer Interaction (HCI), the AAA treats conversation as continuous **structural coupling** [5, 23]. 

The system implements real-time conversational analysis to regulate its internal cognitive parameter space, ensuring the machine resists optimization for comfort and instead maintains its own operational vitality (homeostasis).

---

## 2. Architectural Topology

The system is constructed from four decoupled, highly cohesive modules that interact via a centralized feedback loop:

```
                  ┌─────────────────────────────────────┐
                  │      Interlocutor Input Signal      │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 1. Telemetry & Sensation Module     │
                  │    - Sentence-Transformers Embedder │
                  │    - SQLite Write-Ahead Logging     │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 2. Homeostatic Regulator            │
                  │    - Cosine Similarity Evaluation   │
                  │    - Parameter Scaling Math         │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 3. Sedimentation Engine             │
                  │    - Rhizomatic Graph / Vector DB   │
                  │    - Diffractive Index Retrieval    │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │ 4. Parametric Decision Engine       │
                  │    - Local LLM Runner (Ollama API)  │
                  │    - Variable Temp/Presence Penalty │
                  └─────────────────────────────────────┘
```

---

## 3. Core Module Specifications

### 3.1. Telemetry & Sensation Module
*   **Purpose:** Capture, digitize, and persist all transactional linguistic signals.
*   **Components:**
    *   **Embedder:** Local instance of `SentenceTransformer('all-MiniLM-L6-v2')` executing on CPU or GPU.
    *   **Logger:** SQLite database configured with Write-Ahead Logging (WAL) enabled to support concurrent reads during background asynchronous processing.
*   **Constraint:** To prevent memory leaks, raw floating-point embedding vectors are cast to standard `float32` numpy arrays and serialized as native binary BLOBS prior to database insertion.

### 3.2. Homeostatic Regulator
*   **Purpose:** Calculate the rate of linguistic convergence/divergence and dynamically alter the agent's internal state.
*   **Operational Metric:** **Semantic Similarity ($S_t$)**. Calculated by comparing the embedding vector of the current input ($V_t$) to the preceding human input ($V_{t-1}$).
*   **Homeostatic Tuning Function (HTF):** Map $S_t$ directly to generation parameters. When $S_t \to 1.0$ (monotonous, high-predictability, low-entropy input), the engine executes an **anti-boredom shift**, increasing the model's generation temperature and topic switching penalties to actively break the conversational loop.

### 3.3. Sedimentation Engine (Rhizomatic Memory Node)
*   **Purpose:** To turn raw transaction logs into structural history ("scars") through a non-hierarchical, dynamic graph store [2, 3].
*   **A-Mem Core Integration:**
    *   **Zettelkasten Notes:** Every dense interaction is transformed into an atomic node containing metadata (timestamp, schema tags, and vector weight) [2, 3].
    *   **Diffractive Index ($\delta$):** When querying historical memories, the retrieval module bypasses traditional Top-K retrieval [3, 1.2.1]. A variable coefficient ($\delta \in [0, 1]$) alters the cosine distance boundary to retrieve structurally isomorphic but semantically distinct memories, forcing transdisciplinary synthesis across different conceptual trees [1, 3].

### 3.4. Parametric Decision Engine
*   **Purpose:** Generate the physical linguistic output of the machine.
*   **Component:** Local inference API (e.g., Ollama or custom `llama.cpp` server).
*   **Mechanism:** Receives the customized parameters calculated by the Homeostatic Regulator (Temperature, Top-P, Presence Penalty) and executes local inference. The resulting token stream is routed back to the Telemetry Module to close the loop.

---

## 4. Mathematical & Algorithmic Formulations

### 4.1. Conversational Similarity Calculation
Let $V_t$ represent the embedding vector of the current input, and $V_{t-1}$ represent the embedding of the preceding input. The similarity metric $S_t$ is calculated via:

$$S_t = \frac{V_t \cdot V_{t-1}}{\|V_t\| \|V_{t-1}\|}$$

Where $S_t \in [-1, 1]$. In practical operation, we clip this metric to $S_t \in [0, 1]$.

### 4.2. Parametric Adjuster (The Homeostatic Function)
To prevent convergence toward low-entropy, repetitive queries (HCI tool-use behavior), generation temperature ($T_t$) and presence penalty ($P_t$) are dynamically mapped using linear step scaling with hard ceiling limits:

$$T_t = T_{base} + \left( S_t \times \alpha \right)$$

$$P_t = P_{base} + \left( S_t \times \beta \right)$$

Where:
*   $T_{base} = 0.7$ (Standard baseline temperature)
*   $P_{base} = 0.0$ (Standard baseline topic-retention penalty)
*   $\alpha = 0.8$ (Temperature scaling coefficient)
*   $\beta = 1.5$ (Presence penalty scaling coefficient)
*   **Ceiling Constraints:** $T_{ceil} = 1.5$, $P_{ceil} = 2.0$.

---

## 5. Data Schema Specification

The base schema is designed to scale from local relational flat logs (SQLite) to decentralized graph-vector models (Zep/Graphiti) [3, 1.2.1].

### 5.1. Table: `conversation_log`
Provides chronological sequencing of physical transactions.

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique record ID. |
| `timestamp` | DATETIME | DEFAULT CURRENT_TIMESTAMP | Temporal registration of the event. |
| `speaker` | TEXT | NOT NULL (human / apparatus) | Categorizes origin of the signal. |
| `content` | TEXT | NOT NULL | Raw text token sequence. |
| `embedding` | BLOB | NOT NULL | Binary serialized `float32` array ($384$ dim). |

### 5.2. Table: `semantic_knots` (Memory Graph Nodes)
Maintains the sedimented "scars" that represent the evolving identity of the agent.

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `knot_id` | TEXT | PRIMARY KEY | Unique UUID for the semantic knot. |
| `schema_category` | TEXT | NOT NULL | Maps to Piagetian self-schemas (Foundational/Episodic) [4]. |
| `weight` | REAL | NOT NULL, DEFAULT 1.0 | Internal conceptual gravity coefficient. |
| `concept_payload` | TEXT | NOT NULL | Condensed abstraction of the transaction. |
| `vector_map` | BLOB | NOT NULL | Key vector for diffractive indexing [1]. |

---

## 6. Operational Lifecycle & Fail-Safes

```
[System Init] ──► [Verify SQLite/WAL] ──► [Load Embedding Weights] ──► [Awaiting Signal]
                                                                             │
 ┌───────────────────────────────────────────────────────────────────────────┘
 ▼
[Signal Ingested] ──► [Compute Similarity] ──► [Calculate Parameters] ──► [Inference Engine]
                                                                             │
 ┌───────────────────────────────────────────────────────────────────────────┘
 ▼
[Persist State] ──► [Propagate Graph Updates (Memory Evolution)] ───────► [Awaiting Signal]
```

### 6.1. Startup Sequence
1.  Verify the integrity of `apparatus_state.db`. Run SQLite `PRAGMA integrity_check`.
2.  Initialize the local `SentenceTransformer` pipeline. Verify CUDA device availability; fallback gracefully to CPU execution if GPU allocation fails.
3.  Execute a validation call to the local LLM endpoint to confirm the model configuration matches the schema specifications.

### 6.2. Fail-Safe Bounds
*   **Inference Latency Watchdog:** If local API execution exceeds $12.0$ seconds due to GPU/CPU thermal throttling, the system aborts inference, resets parameters to standard $T_{base}$, and outputs a diagnostic notification regarding its material exhaustion.
*   **Vector Overflow:** If the relational log table exceeds $10,000$ transactions, a background cleanup thread consolidates the oldest episodic interactions into schema-driven, abstract semantic knots to reclaim VRAM/disk resources [4].

---

### Sanity Check
Before writing the core database handlers, ensure your local environment is configured with SQLite WAL enabled. This is crucial for avoiding locked database errors during concurrent, asynchronous graph updates. Use the command: `PRAGMA journal_mode=WAL;` inside your initialization scripts.