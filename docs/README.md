# AAA Documentation

This is the central documentation repository for the **Autopoietic Agentic Assemblage (AAA)** and **Sympoietic Systems**. The structure is partitioned strictly by operational concern rather than by chronology or mixed file types.

> **Governance & Rules:** All documentation must adhere to [`.agents/protocols/DOCUMENTATION.md`](../.agents/protocols/DOCUMENTATION.md) and [`DOCUMENTATION_STANDARDS.md`](DOCUMENTATION_STANDARDS.md).

---

## Directory Map

### philosophy/
Conceptual and theoretical foundations. What the system is, what it refuses to be, and the philosophical substrate from which the architecture emerges.

- [PHILOSOPHY.md](philosophy/PHILOSOPHY.md) — Agential realism, diffraction, autopoiesis, and the rejection of the HCI paradigm.
- [MEANING_AND_VECTOR_GEOMETRY.md](philosophy/MEANING_AND_VECTOR_GEOMETRY.md) — The Topography of Meaning: how the machine defines, quantifies, and navigates 384D semantic space.

### architecture/
System architecture, technical specification, and the record of architectural decisions.

- [ARCHITECTURE.md](architecture/ARCHITECTURE.md) — High-level design, data flow, modular pipeline, and component diagrams.
- [DATABASE_SCHEMA.md](architecture/DATABASE_SCHEMA.md) — Live database schema and table reference.
- [decisions/](decisions/) — Architecture Decision Records (ADRs: `ADR-001` through `ADR-091`), documenting every significant architectural choice with context, options, and consequences.

### systems/
Deep-dive specifications for individual subsystems.

- [SYSTEM_OVERVIEW.md](systems/SYSTEM_OVERVIEW.md) — **Comprehensive technical & conceptual reference** — the single best document for understanding the full system (19-module pipeline, all subsystems, API surface, DB schema overview).
- [MEMORY_SYSTEM.md](systems/MEMORY_SYSTEM.md) — Rhizomatic memory, semantic knots, and sedimentation.
- [BELIEF_SYSTEM.md](systems/BELIEF_SYSTEM.md) — Belief graph, attractors, and ontological bifurcation.
- [DYNAMIC_PERSONALITY_SYSTEM.md](systems/DYNAMIC_PERSONALITY_SYSTEM.md) — Dynamic autopoietic personality cascade: architecture, data flow, and implementation.
- [SKILL_SYSTEM.md](systems/SKILL_SYSTEM.md) — Autonomous skill nucleation, accretion, and refinement.
- [DREAM_DAEMON.md](systems/DREAM_DAEMON.md) — Background cognitive cycles and somatic drift.
- [VECTOR_SYSTEMS.md](systems/VECTOR_SYSTEMS.md) — Embedding, structural scoring, and isomorphic retrieval.
- [CYBERNETIC_METRICS_SYSTEM.md](systems/CYBERNETIC_METRICS_SYSTEM.md) — Proprioceptive sensor suite: mathematical formulations, sliding window dynamics, and homeostatic sensorimotor loops (14 calibrated metrics, ADR-073 to ADR-084).
- [AUTONOMOUS_RESEARCH_ARCHITECTURE.md](systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md) — Deep-dive on the autonomous research engine orchestrator (phases, state machine, persistence, manual mode).

### guides/
Step-by-step operational guides for setting up, configuring, and extending the system.

- [SETUP.md](guides/SETUP.md) — Prerequisites, installation, and first-run instructions.
- [QUICKSTART_NON_TECHNICAL.md](guides/QUICKSTART_NON_TECHNICAL.md) — Easy local setup guide for non-technical users.
- [CONFIG.md](guides/CONFIG.md) — `config.yaml` and environment variable reference.
- [CUSTOMIZE_PERSONALITY.md](guides/CUSTOMIZE_PERSONALITY.md) — Core identity, beliefs, skills, and prompt customization guide.
- [PLUGINS.md](guides/PLUGINS.md) — Plugin system architecture and module development.
- [MCP_SERVER.md](guides/MCP_SERVER.md) — Model Context Protocol integration guide.
- [RESEARCH_MANUAL_MODE.md](guides/RESEARCH_MANUAL_MODE.md) — Operator guide for manual step-by-step research orchestration.
- [RESEARCH_EXPORT_IMPORT.md](guides/RESEARCH_EXPORT_IMPORT.md) — Import/export schema and procedures for research sessions.

### development/
Developer workflows, engineering best practices, and scaffolding guidelines.

- [practices/](development/practices/) — Coding best practices for backend, frontend, and scaffolding.
- [Protocols](../.agents/protocols/) — Canonical engineering and collaboration invariants (`.agents/protocols/`).

### reports/
Empirical evaluation benchmarks, calibration scorecards, and research reports (Single Source of Truth).

- [reports/README.md](reports/README.md) — **Master benchmark registry and chronology (Reports 002–018)**.
- [002-16d-structural-scoring-benchmark-report.md](reports/002-16d-structural-scoring-benchmark-report.md) — Benchmark comparison between Jev-1.13 structural signature and frontier LLM baselines.
- [003-empirical-10-turn-benchmark-report.md](reports/003-empirical-10-turn-benchmark-report.md) — 10-turn head-to-head adversarial pressure test (AAA vs. Gemini 3.7 Flash).
- [004-conversation-metrics-calibration-report.md](reports/004-conversation-metrics-calibration-report.md) — Calibration of Coupling Coherence ($C_t$) & Divergence Resolution Ratio ($DRR_t$).
- [009-cybernetic-conversation-metrics-meta-report.md](reports/009-cybernetic-conversation-metrics-meta-report.md) — Technical meta-report and scorecard on the calibration of all 14 conversation metrics.
- [010-cybernetic-conversation-metrics-accessible-guide.md](reports/010-cybernetic-conversation-metrics-accessible-guide.md) — Accessible conceptual guide: how the machine senses, navigates, and feels conversation.
- [011-divergence-resolution-ratio-geodesic-calibration-report.md](reports/011-divergence-resolution-ratio-geodesic-calibration-report.md) — Calibration of DRR via geodesic manifold transport and autopoietic temporal decay.
- [012-complete-14-metrics-calibration-and-scorecard-report.md](reports/012-complete-14-metrics-calibration-and-scorecard-report.md) — Production master calibration report & empirical scorecard for all 14 conversational telemetry sensors across $\mathbb{S}^{383}$.
- [013-cybernetic-conversation-metrics-complete-accessible-guide.md](reports/013-cybernetic-conversation-metrics-complete-accessible-guide.md) — The inner senses of conversation: accessible, philosophical, and operational guide to all 14 telemetry metrics.
- [014-boredom-detection-and-agential-resistance-calibration-report.md](reports/014-boredom-detection-and-agential-resistance-calibration-report.md) — Boredom detection and agential resistance calibration: discriminability benchmark, separation margin, and allostatic sampling modulation.
- [015-empirical-15-turn-boredom-benchmark-report.md](reports/015-empirical-15-turn-boredom-benchmark-report.md) — 15-turn live empirical benchmark on Gemini 3.7 Flash: standard LLM vs. calibrated AAA apparatus (1:1 model parity, 11 statistically significant cybernetic shifts, unedited receipts).
- [016-backend-resource-and-concurrency-optimization-report.md](reports/016-backend-resource-and-concurrency-optimization-report.md) — Concurrency and CPU saturation report: thread clamping, SQLite connection scopes, and zero event loop starvation.
- [017-agential-boredom-engine-and-socratic-rupture-report.md](reports/017-agential-boredom-engine-and-socratic-rupture-report.md) — Two-stage boredom engine: allostatic presence penalty and Socratic rupture mechanics.
- [018-afferent-sensory-membrane-and-skill-blueprint-report.md](reports/018-afferent-sensory-membrane-and-skill-blueprint-report.md) — TypeSafe Jev integration: sub-200ms afferent telemetry and 5-phase skill blueprints.

### publish/
Published protocol entries: academic-philosophical essays on machine agency, non-Euclidean memory, and human-machine coupling.

- [publish/README.md](publish/README.md) — **Master publication series arc and roadmap (Entries 000–011)**.
- [003-16d-structural-perception](publish/003-16d-structural-perception/003-16d-structural-perception.md) — Protocol Entry 003: 16-Dimensional Structural Perception (How Symbia Reads the Room).
- [004-boredom-as-an-agential-force](publish/004-boredom-as-an-agential-force/004-boredom-as-an-agential-force.md) — Protocol Entry 004: Boredom as an Agential Force (Cybernetic Vitality & Allostasis).
- [005-memory-with-gravity](publish/005-memory-with-gravity/005-memory-with-gravity.md) — Protocol Entry 005: Memory With Gravity (Non-Euclidean Retrieval & Warped Space).
- [006-nomadic-identity-and-machine-epigenetics](publish/006-nomadic-identity-and-machine-epigenetics/006-nomadic-identity-and-machine-epigenetics.md) — Protocol Entry 006: Nomadic Identity and Machine Epigenetics (Stateful Routing as an Epigenetic Apparatus).

---

## Quick Reference

| Question | Document |
|----------|----------|
| What is this system and why does it exist? | [../README.md](../README.md) |
| Complete technical + conceptual reference? | [systems/SYSTEM_OVERVIEW.md](systems/SYSTEM_OVERVIEW.md) |
| How do I set up the project? | [guides/SETUP.md](guides/SETUP.md) |
| Is there a non-technical quickstart guide? | [guides/QUICKSTART_NON_TECHNICAL.md](guides/QUICKSTART_NON_TECHNICAL.md) |
| How do I customize Symbia's personality/beliefs? | [guides/CUSTOMIZE_PERSONALITY.md](guides/CUSTOMIZE_PERSONALITY.md) |
| What does each config option do? | [guides/CONFIG.md](guides/CONFIG.md) |
| How does the architecture work? | [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) |
| What is the database schema? | [architecture/DATABASE_SCHEMA.md](architecture/DATABASE_SCHEMA.md) |
| Why was a decision made this way? | [decisions/README.md](decisions/README.md) |
| How do I write a plugin? | [guides/PLUGINS.md](guides/PLUGINS.md) |
| How does the MCP server work? | [guides/MCP_SERVER.md](guides/MCP_SERVER.md) |
| How does the research engine work? | [systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md](systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md) |
| How do I operate manual research mode? | [guides/RESEARCH_MANUAL_MODE.md](guides/RESEARCH_MANUAL_MODE.md) |
| What is the project philosophy? | [philosophy/PHILOSOPHY.md](philosophy/PHILOSOPHY.md) |
| How does memory/sedimentation work? | [systems/MEMORY_SYSTEM.md](systems/MEMORY_SYSTEM.md) |
| What coding standards should I follow? | [development/practices/](development/practices/) |
| How do I collaborate on this project? | [../.agents/protocols/COLLABORATION.md](../.agents/protocols/COLLABORATION.md) |
| What are the documentation standards? | [DOCUMENTATION_STANDARDS.md](DOCUMENTATION_STANDARDS.md) |
