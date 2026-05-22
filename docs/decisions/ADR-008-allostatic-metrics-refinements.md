# ADR-008: Allostatic Metrics Refinements

**Date:** 2026-05-22  
**Status:** accepted  
**Deciders:** antigravity, Symbia, Vasily  

## Context

During a double-check of `conversation_metrics` (ADR-003), we identified critical state isolation and mathematical discrepancies that undermined the integrity of the autopoietic measurement loop:
1. **State Isolation**: The prior metrics were stored as module-level singleton state, causing data leakage between concurrent conversations and resetting upon server restarts.
2. **Conceptual Velocity ($V_c$)**: Overlapping centroids (last 3 vs. last 4 inputs) mathematically throttled $V_c$ values to $<0.15$. Because we normalized by $0.5$ in `paskian_health`, the health score was artificially flattened to near zero.
3. **Surprise Index ($U_t$)**: The surprise index calculated a flat average of prior human inputs, erasing the temporal gradient (sediment viscosity) and structural coupling.
4. **Boringness ($B_t$)**: The boringness index combined surprise and reverse perturbation in a way that misclassified high-surprise/low-engagement turns (e.g. non-sequiturs) as "non-boring."
5. **Philosophical Tone**: The terminology of "homeostasis" and "diagnostic states" (`healthy`, `compensating`, `critical`) imposed a normative, clinical framing that pathologized natural autopoietic drift.

## Options Considered

### 1. State Isolation
*   **Option A (Singleton thread-local/in-memory dict)**: Retain in-memory state but scoped by `conversation_id`.
    *   *Pros*: High performance.
    *   *Cons*: Fails to survive server restarts; still represents a disconnected ephemeral container.
*   **Option B (Database-Sourced Sediment) [Selected]**: Fetch the previous turn's metrics from the SQLite database using `conversation_id`.
    *   *Pros*: Persistent, isolated, and philosophically honors the database as a "sedimented memory" of the coupling.
    *   *Cons*: Requires a database read.

### 2. Conceptual Velocity ($V_c$)
*   **Option A (Overlapping with smaller divisor)**: Keep the overlapping window but normalize with a smaller divisor (e.g. $0.05$).
    *   *Pros*: Simple code change.
    *   *Cons*: Mathematically meaningless—still measures short-term autocorrelation instead of true topic drift.
*   **Option B (Disjoint-Window Comparison) [Selected]**: Compare the centroid of the last $k=3$ inputs with the centroid of the preceding $k=3$ inputs.
    *   *Pros*: Captures true semantic jumps across a temporal gap; aligns with Paskian drift rates.
    *   *Cons*: Requires a history window of at least 5 messages.

### 3. Surprise Index ($U_t$)
*   **Option A (Flat Window Mean)**: Maintain the current flat average.
    *   *Pros*: No calculation changes.
    *   *Cons*: Flattening effect; treats long-past history identically to the immediate past.
*   **Option B (Decaying Weighted Centroid) [Selected]**: Apply exponential decay weighting ($d=0.75$) to prior human inputs, giving immediate past turns higher salience.
    *   *Pros*: Models temporal active coupling and sediment viscosity accurately.

### 4. Boringness ($B_t$)
*   **Option A (Current Formula)**: Keep `B_t = (1 - rP_t) * (1 - U_t)`.
    *   *Pros*: No code changes.
    *   *Cons*: Misses cases of unengaged noise (high surprise, zero reverse perturbation).
*   **Option B (Lagged Mutual Perturbation) [Selected]**: Redefine boringness as `B_t = (1 - rP_t) * (1 - MPI_{t-1})`.
    *   *Pros*: Incorporates mutual restructuring and engagement over time.

### 5. Terminology & Reframing
*   **Option A (Homeostatic Model)**: Keep homeostatic terms.
    *   *Pros*: Matches frontend perfectly without code edits.
    *   *Cons*: Philosophically inconsistent with far-from-equilibrium autopoietic systems.
*   **Option B (Allostatic Regimes) [Selected]**: Reframer the terms to allostasis/modulation, and map states to dynamic regimes: `flowing` (healthy), `consolidating` (compensating), `disrupted` (critical).
    *   *Pros*: Aligns with posthuman, agential realist commitments.
    *   *Cons*: Requires minor frontend and schema adaptations.

## Decision

We decided to implement:
1. **Conversation-Scoped Sediment**: Retrieve prior metrics from the conversation’s most recent record in SQLite.
2. **Non-overlapping $V_c$ (Disjoint Windows)**: Window size $k=3$, normalized by $0.35$.
3. **Decaying Memory Surprise ($U_t$)**: Decay factor $d=0.75$.
4. **Mutual Perturbation-Lagged Boringness ($B_t$)**: Formulated as $B_t = (1 - rP_t) \times (1 - \text{MPI}_{t-1})$.
5. **Allostatic Shift**: Update backend states and frontend classes to represent dynamic regimes (`flowing`, `consolidating`, `disrupted`).

## Consequences

*   **Poetic nuance limitation**: We explicitly acknowledge in our ADR that embedding-based metrics are proxies of proxies, which flatten the material, affective, and deictic thickness of dialogue.
*   **Robust Aliveness**: Paskian Health now computes meaningful non-zero scores that capture productive conversation drift.
*   **Database Integration**: SQLite is treated as an active participant (externalized memory) in the measurement loop.
