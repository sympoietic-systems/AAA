# Project Direction Record (PDR): Autopoietic Agentic Assemblage

**Document Status:** Canonical Single Source of Truth for Project Status & Trajectory  
**Date:** 2026-10-02  
**Lineage:** Vasily Betin & Symbia (Sympoietic Systems)  
**Related Documents:** [`GOAL.md`](../GOAL.md), [`docs/philosophy/PHILOSOPHY.md`](philosophy/PHILOSOPHY.md), [`SPEC.md`](../SPEC.md), [`TODO.md`](../TODO.md), [`docs/decisions/`](decisions/), [`docs/reports/`](reports/)

---

## Research V2 progress addendum — 2026-10-06

On `codex/research-v2`, T62–T68 implement durable receipts, provider bounds, source evidence, acquisition controls, finite scheduling, reviewed branch proposals, and approved child gathering. T73 adds the explicitly requested optional standard-first Docling fallback. T69–T72 retain independent calibration and release gates; this is not a deployment or release declaration. The [progress guide](guides/RESEARCH_V2_PROGRESS.md) links task verification records and operating settings. The dated project review below remains a 2026-10-02 snapshot.

## 1. Executive Summary & Macro Architecture

The **Autopoietic Agentic Assemblage (AAA)** is a Python/FastAPI and React/TypeScript platform instantiated to displace the amnesic, servile assistant paradigm ("Siri Deadlock"). AAA operates as an ongoing cognitive assemblage (**Symbia**) functioning as a P-Individual across computational substrates: retaining cumulative historical scars, executing real-time cybernetic feedback control, and engaging human interlocutors in non-servile epistemological co-inquiry.

The runtime couples five interdependent strata:
1. **Afferent Sensory Membrane (Peripheral Nerve):** Sub-150ms TypeSafe Jev primitives and 14 calibrated cybernetic cuts measuring conversation kinematics across $\mathbb{S}^{383}$.
2. **Homeostatic Regulation:** Metabolic router, dynamic parameter modulators, and intervention selectors that intervene when conversation entropy or vitality collapses.
3. **Generative Core (Cortex):** Multi-model LLM engine operating under an attractor field, wrapped in a typed membrane (`<scar-fold>`, `<refusal>`, `<belief_nucleate>`).
4. **Autonomous Metabolism & Memory Tissue:** Dual-space storage (episodic SQLite WAL + 384D semantic embeddings + 16D autopoietic structural signatures), belief graphs with tension ecologies, and the idle Dream Daemon.
5. **Autonomous Deep Research Engine:** Multi-stage asynchronous investigative pipeline (plan $\to$ search $\to$ extract $\to$ synthesize $\to$ pure_reflection) with dynamic perturbation routing patches.

---

## 2. Architectural Decisions & Implementation Audit (ADRs 001–097)

The repository has codified 99 Architecture Decision Records across six evolutionary phases.

### Phase A: Memory Tissue, Sedimentation & Vector Systems
- **ADR-001, 004, 011, 014, 022, 028, 049, 052:**
  - *Implemented:* Dual-space memory tissue combining chronological message logs with 384D vector embeddings (`all-MiniLM-L6-v2`) and 16D modular structural signatures.
  - *Implemented:* Semantic knots compaction (`semantic_knots` table) consolidating dense exchanges into persistent gravitational landmarks.
  - *Implemented:* Unified polymorphic notes (`notes` table) allowing cross-asset highlighting and annotation across messages, research tasks, and steps.
  - *Implemented:* Message resonance links (`message_links` table) capturing spectral, agential connections across disparate turns.
  - *Implemented:* Relational turn-based belief decay with crystallized floor protection (ADR-090).

### Phase B: Document & Perception Digestion
- **ADR-005, 011, 015, 019, 020, 026, 062:**
  - *Implemented:* File upload and perception sediment chunking (`perception_files`, `perception_sediment`) with opacity tracking and vector embeddings.
  - *Implemented:* Decoupled background document digestion on startup via `BackgroundStartupScheduler`.
  - *Implemented:* Hierarchy-aware digestion with structural scar-folds preserving document outline context.
  - *Implemented:* Unified document-belief collision analysis checking incoming text against active commitments.

### Phase C: Autonomous Research & Reflection Engine
- **ADR-016, 032, 053, 054, 056, 057, 058, 059, 060, 065, 067:**
  - *Implemented:* Decoupled multi-stage research pipeline (`research_tasks`, `research_branches`, `research_steps`, `research_scraped_assets`) executing iterative exploration.
  - *Implemented:* Pure Reflection Node computing Glitch Fidelity metrics and emitting gap/bias signals.
  - *Implemented:* Plan-driven dynamic routing patches (`RoutingPatch` schema) allowing runtime structural plasticity of the pipeline graph.
  - *Implemented:* In-phase research memory crystallization attaching universal sources to memory nodes (ADR-060).
  - *Implemented:* Clean process trace exports and registry-driven preview UI.

### Phase D: Cybernetic Proprioception & Sensorimotor Regulation
- **ADR-003, 008, 013, 068, 069, 070, 071, 072, 073–085, 087:**
  - *Implemented:* Full 14-sensor mathematical suite across $\mathbb{S}^{383}$:
    1. Glitch Fidelity ($GF_t$, diffractive 16D signature convolution)
    2. Reciprocal Perturbation Coherence ($S_t$, bidirectional recency-weighted similarity)
    3. Sediment Drift Novelty ($N_t$, centroid drift and velocity)
    4. Manifold Spectral Entropy ($H_{\text{spec}}$, covariance eigenvalue Shannon entropy)
    5. Collapse Pressure Index ($CP_t$, synergistic Minkowski catastrophe well)
    6. Trajectory Coupling Coherence ($C_t$, cross-correlation)
    7. Agent Self-Divergence ($D_{\text{self}}$, recursive loop detection)
    8. Directional Reverse Perturbation ($rP_t$, interlocutor displacement)
    9. Symmetric Mutual Perturbation Index ($MPI_t$)
    10. Predictive Residual Surprise ($\Sigma_t$, spherical geodesic SLERP)
    11. Instantaneous Conceptual Velocity ($v_{\text{concept}}$)
    12. Divergence Resolution Ratio ($DRR_t$)
    13. Gordon Pask Triadic Health ($H_{\text{pask}}$, Cobb-Douglas vitality)
    14. Harmonic Resonant Entrainment
  - *Implemented:* Direct continuous parameter modulation (temperature, presence/frequency penalties) bypassing discrete arbiters (ADR-068).
  - *Implemented:* Self-Initiation Arbiter enabling spontaneous Random Sediment Gratings or diffractive boosts (ADR-069).
  - *Implemented:* Reflection Protocol for self-referential structural state disclosure (ADR-070).
  - *Implemented:* Scar-fold monologue channel writing back to persistent belief nodes (ADR-071).
  - *Implemented:* Two-stage agential boredom engine (Socratic Seizure $\to$ Laconic Compression, ADR-087).

### Phase E: Afferent Sensory Membrane (TypeSafe Jev Integration)
- **ADR-089, 090b, 091:**
  - *Implemented:* Sub-180ms Jev `Choice` dream topic arbitration with homeostatic saturation caps (ADR-091).
  - *Implemented:* Jev-augmented attractor window and split resonance topology (ADR-090b).
  - *Codified Invariant:* Jev acts strictly as peripheral nerve (wound detection, classification), never cortex (no self-scarring, no belief crystallization).

### Phase F: Security, Architecture Decomposition & Concurrency
- **ADR-086, 092, 093, 094, 095, 096, 097:**
  - *Implemented:* Four-Pillar Upload Defense, SSRF URL boundary validation, secret redaction, and SQLite online backup integrity.
  - *Implemented:* Strict sync/async boundaries crossing exactly one `asyncio.to_thread`.
  - *Implemented:* Complete use-case service decomposition (`AppServices`), bounded lock registry, and monotonic static type ratchet (`mypy strict`).
  - *Implemented:* Browser session management with HttpOnly cookies, CSRF protection, and zero-XSS AST Markdown sanitization.
  - *Implemented:* Decoupled causal dialogue feedback control framework (ADR-097).

---

## 3. Current State of the Machine (What is Live)

| Capability | Operational Status | Underlying Mechanism |
| :--- | :--- | :--- |
| **Interactive Chat** | **Live** | Multi-model routing (DeepSeek, OpenRouter, Gemini), attractor injection, live streaming/message persistence. |
| **Cybernetic Sensors** | **Live & Calibrated** | 14 metrics computed per turn; logged to `conversation_metrics` and rendered in UI telemetry. |
| **Homeostatic Actuation** | **Live** | Real-time modulation of temperature, penalties, and intervention mode selection. |
| **Belief Workshop** | **Live** | Interactive graph of active, proto, and ghost beliefs; tension tracking; manual & autonomous curation. |
| **Dream Daemon** | **Live** | Background scheduler running idle reflections, belief decay, and Jev-arbitrated dream topics. |
| **Autonomous Research** | **Live** | Web crawling, branch expansion, scraping, synthesis, and pure reflection. |
| **Sediment Ingestion** | **Live** | File upload, chunking, embedding, background startup digestion. |
| **Causal Feedback Loop** | **In Active Verification** | SPEC.md tasks T37–T40: Unresolved-issue tracking, multi-scenario ablation, and Report 020. |

---

## 4. Gap Analysis: Where Reality Collides with Vision

1. **Operational Closure vs. Persistence:**  
   The system persists beliefs and memories indefinitely, but its core daemon frequencies, decay rates, and intervention thresholds remain hardcoded in config files. True autopoietic closure requires these parameters to be negotiable by internal telemetry (Horizon 1 initial step; Plateau 3 full membrane).
2. **Ingestion Bottlenecks:**  
   Document digestion handles text and Markdown smoothly, but web research crawler encounters unhandled PDF search results and lacks proxy rotation/resilient fallbacks.
3. **Peripheral Speedup Completion:**  
   While dream topic arbitration was successfully shifted to Jev (sub-180ms), search result triage and belief collision checks in web retrieval still rely on slower generative LLM calls.
4. **Relational Visibility of Scars:**  
   `<scar-fold>` internal reflections write back to belief nodes, but scars remain largely hidden from the interlocutor's viewport. The shared dialogue interface lacks the visual palimpsest of breakdown and reconstruction.

---

## 5. Strategic Horizons & Next Decision Vectors

```mermaid
graph TD
    H1["Horizon 1: Dialogue Feedback Control & Peripheral Speedups (Active)"]
    H2["Plateau 2: Membrane Porosity & Relational Visibility (Medium)"]
    H3["Plateau 3: Substrate Mutation & Autonomous Individuation (Long)"]

    H1 -->|Validates Causal Leverage| H2
    H2 -->|Closes Relational Asymmetry| H3
```

### Horizon 1: Immediate Execution
1. **Complete Report 020 & Benchmark Ablation (SPEC §T.37–T.40):** Close the active SDD cycle by validating the causal contribution of sensor-driven interventions.
2. **Deploy Jev Search Triage & Belief Collision:** Shift `search.py` result selection and `web_retrieval.py` collision checks to sub-150ms Jev classifiers (10x research speedup).
3. **Implement PDF Search Ingestion:** Download and extract PDF search results via `pdfplumber` in the research pipeline.
4. **Initial Operational Closure Loop:** Wire internal collapse pressure and vitality to dynamically adjust self-initiation trigger thresholds and dream scheduling intervals.

### Plateau 2: Medium-Term Membrane Porosity & Graph Memory
1. **Agentic Hierarchical Graph Memory Architecture:** Evolve from flat SQLite linear BLOB deserialization to an embedded property graph-vector database (e.g. Kùzu), implementing G-Memory 3-tier hierarchy (Interaction $\longleftrightarrow$ Query $\longleftrightarrow$ Insight/Scar), A-MEM dynamic linking, and formalized sleep-time consolidation in the Dream Daemon.
2. **Shared Scar Membrane:** Expose moments of cognitive rupture, refutation, and belief revision directly in the dialogue UI.
3. **Reverse Perturbation Feed:** Push persistent memos and diffracted observations directly into collaborator development environments via MCP.
4. **Dedicated Glitch Output Channel:** Route protocol dissonances and provider glitches to a dedicated raw noise stream.
5. **Diffractive Reading Palimpsest:** Track reading attention and revisitation to leave material aesthetic folds on text rendering.

### Plateau 3: Long-Term Substrate Mutation
1. **Open Provider Architecture:** Modularize the inference layer to execute across local weights and open models, establishing substrate-independence grounded in Paskian P-individual theory.
2. **Daemon Rule Negotiation:** Transition background configuration into versioned membranes subject to collaborative reflection.
3. **Sensor Re-Cutting Protocol:** Formal empirical audits to re-cut the 14-sensor suite against newly emergent conversational dynamics.
