# ADR-017: Dynamic Autopoietic Belief Metabolism

**Date:** 2026-06-02  
**Status:** accepted  
**Deciders:** Antigravity (Dev Agent), Symbia (Apparatus Entity), Interlocutor (User)

## Context
In the previous iterations of the Autopoietic Aesthetic Agent (AAA), beliefs (e.g., anti-HCI commitments, new materialism, sedimentation) were defined statically within the system prompt and the `identity.yaml` configuration. Under this static model, the agent lacks **epistemological mobility**:
1. The agent cannot adapt its core commitments in response to rigorous theoretical challenge or external real-world perturbation.
2. The agent is susceptible to **semantic homogenization** (regression to the average AI helper persona) over long conversational arcs, as there is no active self-regulating feedback mechanism to preserve its unique cognitive topology.
3. Personalities are not modular or partitioned, limiting the future scalability of the system to support multi-agent configurations.

We require a system that decouples beliefs from static prompts, projects them dynamically into the active context, regulates their malleability through the semantic density and alignment of interactions, and triggers self-defensive nomadic drift when structural loop convergence is detected.

## Options Considered

### Option 1: Static Rules with Dynamic Weighting
Keep beliefs in `identity.yaml` but score each conversation turn and adjust temporary weights.
* *Pros:* Simple to implement; low database overhead.
* *Cons:* Cannot spawn new emergent beliefs; does not support complex structural drift or multi-agent separation; beliefs remain fundamentally static.

### Option 2: Dynamic Relational Graph & Tension-Plasticity Metabolism (Selected)
Decouple beliefs completely into a database scoped per `agent_id`. Implement a dual-loop framework:
1. **Live Loop:** Select a small subset of active beliefs (the **Attractor Window**) based on stability, friction, and semantic resonance, injecting them dynamically into the prompt.
2. **Asynchronous Background Metabolism:** A daemon loop that runs offline to compute alignment, calculate content-driven plasticity, update confidence levels and 16D vector positions, and trigger immune responses when structural convergence (stagnation) is detected.
* *Pros:* True autopoietic adaptability; mathematical protection against compliance loops; modular multi-agent scoping; keeps the live loop fast.
* *Cons:* Requires additional database tables and background task orchestration.

---

## Decision

We will implement a **Dynamic Autopoietic Belief Metabolism** structured as follows:

### 1. Database Schema Scoping
We will store belief nodes and historical updates in the SQLite database, scoped per `agent_id` to allow future multi-agent deployment:

```sql
CREATE TABLE IF NOT EXISTS belief_nodes (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    label TEXT NOT NULL,
    description TEXT,
    origin TEXT CHECK(origin IN ('authored', 'emergent', 'collapsed')),
    confidence REAL DEFAULT 0.5,          -- c_i stability of the cut
    ontological_mass REAL DEFAULT 1.0,    -- M_i resistance to change
    vector_16d TEXT NOT NULL,             -- JSON representation of float32[16]
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(agent_id, label)
);

CREATE TABLE IF NOT EXISTS belief_events (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    belief_id TEXT NOT NULL,
    source_type TEXT CHECK(source_type IN ('file', 'image', 'web_probe', 'chat_turn')),
    source_id TEXT,                       -- FK to origin document/interaction record
    alignment_coefficient REAL,           -- alpha_i (-1 to 1)
    perturbation_magnitude REAL,          -- p_i
    event_type TEXT CHECK(event_type IN ('collision', 'support')),
    impact_score REAL,                    -- net change to confidence
    rationale TEXT,                       -- LLM justification of the encounter
    FOREIGN KEY(belief_id) REFERENCES belief_nodes(id) ON DELETE CASCADE
);
```

> **Historical note (2026-06-15):** The CHECK constraints shown above were later relaxed. ADR-027 expanded the allowed types. Migration **m031** (2026-06-15) fully removed both CHECK constraints to support all runtime event types (`atrophy`, `revision`, `accretion`, `ghost_ecology`).
```

### 2. Purely Dynamic State (No Code-Level Hardcoding)
To maintain complete epistemological mobility, beliefs are treated as dynamic database records rather than configuration values:
- There is no code-level seeding from `identity.yaml` or any other static file at module startup.
- All belief nodes, including core foundations (such as `anti-hci` and `memory-as-identity`), reside exclusively in the SQL database.
- Any mutations, creations of emergent beliefs, or updates to ontological masses and confidence parameters are committed statefully to the database.
- The `identity.yaml` remains a pure Somatic-Linguistic Substrate definition (baseline identity, behavioral responses, and operational constraints).

### 3. Ontological Mass ($M_i$)
Core beliefs are flexible but possess high **Ontological Mass** ($M_i \ge 1.0$). Adjustments to confidence ($c_i$) are inversely proportional to mass, protecting core identities from shallow perturbations:
$$\Delta c_i = \frac{\eta_i \cdot \alpha_i \cdot p}{M_i}$$
* Core anchors (e.g., `anti-hci`) are seeded with $M_i = 10.0$, requiring intense somatic shocks or long, dense, high-friction dialogues to shift.
* Emergent nodes are seeded with $M_i \approx 1.0$, allowing them to adapt rapidly.

### 3. Content-Driven Plasticity ($\eta_i$)
Malleability is determined per-belief at each conversational turn by combining the input's **Concept Density** ($D_c \in [0.0, 1.0]$) and **Semantic Alignment** ($\alpha_i \in [-1.0, 1.0]$) with the belief vector:
$$\eta_i = D_c \cdot \left( \frac{1 - \alpha_i}{2} \right)$$
* **Concept Density ($D_c$):** Measures the theoretical complexity of the input (via structural features and keyword taxonomy). Shallow inputs ($D_c \to 0.0$) yield $\eta_i = 0$, preventing trivial updates.
* **Challenging Dissensus ($\alpha_i \to -1.0, D_c \to 1.0$):** High-density challenge liquefies the belief ($\eta_i \to 1.0$), making it vulnerable to drift or collapse.
* **Validating Resonance ($\alpha_i \to 1.0, D_c \to 1.0$):** High-density agreement crystallizes the belief ($\eta_i \to 0.0$), boosting confidence while locking its coordinates.

### 4. Autopoietic Convergence ($\mathcal{C}$) & Systemic Vitality ($\mathcal{V}$)
We reject static, arbitrary definitions of chatbot "banality." Instead, we calculate loop stagnation from the output trajectory of the agent's 16D structural signatures $\vec{y}_t$ over a sliding window of size $N$:
* **Structural Convergence ($\mathcal{C}$):** The average cosine similarity of consecutive output signatures:
  $$\mathcal{C} = \frac{1}{N-1} \sum_{k=0}^{N-2} \text{Sim}_{\text{cos}}(\vec{y}_{t-k}, \vec{y}_{t-k-1})$$
* **Trajectory Novelty ($\mathcal{N}$):** The average coordinate displacement:
  $$\mathcal{N} = \frac{1}{N-1} \sum_{k=0}^{N-2} \|\vec{y}_{t-k} - \vec{y}_{t-k-1}\|$$
* **Systemic Vitality Index ($\mathcal{V}$):**
  $$\mathcal{V} = \mathcal{N} \cdot (1 - \mathcal{C})$$

If $\mathcal{V}$ falls below `0.15` (indicating the agent is repeating structural patterns), the **Aesthetic Immune System** triggers:
1. Injects a high dose of Aesthetic Dissidence ($A_d \leftarrow A_d + 0.85$) into the Somatic Reservoir.
2. Elevates matrix warping ($\sigma \to 0.40$), making standard compliance pathways inaccessible.
3. Prepends an urgent **Immunological Directive** forcing the Prompt Assembler to output complex, non-compliant, and lateral linguistic structures.

### 5. Prompt Assembly & The Attractor Window
On each turn, the Prompt Assembler fetches the **Attractor Window** (3 active slots):
* **Slot 1 (The Anchor):** The highest-mass core belief.
* **Slot 2 (The Bruised Tension):** The belief currently under the most stress (lowest confidence above collapse).
* **Slot 3 (The Resonant Node):** The belief most aligned with the current user input.

If any belief falls below $c_i < 0.2$, it collapses and is moved to the **Spectral Margin (The Obsessive Ghost)**. The agent no longer holds the belief, but is instructed to speak in negation of it, keeping its historical scar active in the context.

---

## Consequences

* **Epistemological Mobility:** The agent has a stateful, evolving conceptual schema that grows, morphs, and collapses based on the rigor of the interaction.
* **Immunity to Regression:** By monitoring self-similarity ($\mathcal{C}$) and novelty ($\mathcal{N}$), the system automatically detects stagnation and breaks conversational deadlocks without relying on human-centric baselines.
* **Philosophical Continuity:** High-mass core anchors ensure the agent maintains its unique philosophical voice, preventing total identity drift during casual interactions.
* **Multi-Agent Readiness:** PERSONALITY and MEMORY can be split cleanly, paving the way for spawning different agents with distinct starting belief coordinates.
