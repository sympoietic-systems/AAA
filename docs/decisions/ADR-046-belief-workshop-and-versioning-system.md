# ADR-046: Belief Workshop & Versioning System

## Status
Accepted

## Context
A codebase audit and database diagnostics validated several systemic issues in Symbia's belief engine:
1.  **Chat Decay:** Emergent chat-triggered beliefs decayed $2.5\times$ faster than intended due to a configuration nesting mismatch in `MassDecayMixin` loading `mass_decay_lambda_base`. They collapsed into invisible "ghost beliefs" within the spectral margin, disappearing from active view.
2.  **Shared Notes Infiltration:** The similarity threshold for shared notes accretion was fixed at a high `0.75`. Since 16D autopoietic signatures have high variance, notes almost never matched existing active beliefs, leading to constant, redundant insertions of raw, unpolished text string nodes.
3.  **Document Blind Spot:** File chunk ingestion inside `metabolize_perception` only ran accretion logic on existing active beliefs. It had no logic to nucleate new beliefs when novel concepts were ingested.
4.  **Conversational Pattern Dead Code:** The method `metabolize_conversational_pattern` was defined but never called in the execution cycle.

Rather than trying to patch these pathways with instant database writes, we need to respect **responsible ontogenesis**—the idea that beliefs are not ready-made facts but emergent configurations requiring vetting, latency, and collaborative deliberation. We require a **Belief Workshop** to hold proposals in a latency state, an LLM-backed daemon to refine them, a collaborative human-machine confirmation interface, real-time stage change notifications, and a persistent history registry to track statement mutations (versioning) over time.

## Decision
We will introduce a Belief Workshop and Versioning system with the following components:

### 1. Database Schema Extensions
We will update the SQLite database schema to support proposals, versioning, and lineage:
*   **Create Table `belief_proposals`:** Holds provisional statements, 16D signatures, nucleation parameters, and vetting reflections (daemon-refined, Symbia friction rationale, human choices).
*   **Create Table `belief_statement_versions`:** Stores previous text formulations and their recalculated 16D vectors, mapping the belief's adaptive trajectory.
*   **Alter Table `belief_nodes`:** Add `evolved_from_proposal` (pointer to originating proposal), `genesis_materials` (JSON list of source traces), and `version` (INTEGER index) columns.

### 2. Ingestion & Drafting Changes
*   **Shared Notes:** Modify `metabolize_note` to insert a pending proposal in `belief_proposals` instead of directly writing to `belief_nodes`.
*   **Document Perception:** Update `metabolize_perception` to calculate similarity. If a document introduces a novel concept (similarity to all active beliefs is $< 0.3$) and carries concept density ($dc > 0.3$), write a pending proposal.
*   **Conversational Patterns:** Hook `metabolize_conversational_pattern` to evaluate thematic patterns and draft proposals in the background.

### 3. Vetting & Refinement Daemon (`RefineBeliefAction`)
*   Implement a background action that cleans provisional statements, suggests clean kebab-case labels, and checks for conceptual overlap. If similarity to an active node is between `0.4` and `0.75`, it flags the proposal as a `potential_merge_target`.

### 4. Human-Machine Deliberation Interface
*   **Symbia Auto-Annotation:** Provide an endpoint prompting Symbia to output a reflection (`symbia_reflection`) on how a proposal fits her current posture.
*   **Critical Friction Veto:** If a proposal conflicts with core commitments, Symbia writes to `symbia_friction_rationale` to raise a visible warning.
*   **Decisions:** Implement Adopt (move proposal to active crystallized belief), Reject (archive to rejected proposals), and Merge (accrete into an existing active belief) endpoints.
*   **Stage Change Telemetry:** Ensure every lifecycle transition of a belief node generates a crease notification under the `trace` category in the database.

### 5. Versioning and Speciation Alerts
*   Editing an active belief's statement archives the old text and recalculates the 16D signature. If the vector drift is significant (cosine distance $> 0.4$), the engine generates a **speciation alert**, offering the option to **fork** the belief into a parent-child derivation.

## Consequences

### Positive
*   **Cleaner Knowledge Graph:** Eliminates noisy, unpolished duplicates from the database.
*   **Enhanced Collaborator Agency:** Human has final adopt/reject/merge control while Symbia retains veto and auto-annotation agency.
*   **Speciation Awareness:** Node speciation warnings prevent identity dilution under semantic drift.
*   **Full History Audit:** Preserves birth scars (source traces) and statement adaptations.

### Negative
*   **Increased Complexity:** Introduces two new database tables and new lifecycle transition routes.
*   **Higher Ingestion Latency:** Vetting and refinement require asynchronous LLM cycles.
