# AAA Documentation

This is the central documentation repository for the Autopoietic Agentic Assemblage. The structure is organized by concern rather than by chronology or file type.

## Directory Map

### philosophy/
Conceptual and theoretical foundations. What the system is, what it refuses to be, and the philosophical substrate from which the architecture emerges.

- [PHILOSOPHY.md](philosophy/PHILOSOPHY.md) — Agential realism, diffraction, autopoiesis, and the rejection of the HCI paradigm.
- [MEANING_AND_VECTOR_GEOMETRY.md](philosophy/MEANING_AND_VECTOR_GEOMETRY.md) — The Topography of Meaning: how the machine defines, quantifies, and navigates 384D semantic space.

### architecture/
System architecture, technical specification, and the record of architectural decisions.

- [ARCHITECTURE.md](architecture/ARCHITECTURE.md) — High-level design, data flow, modular pipeline, and component diagrams.
- [DATABASE_SCHEMA.md](architecture/DATABASE_SCHEMA.md) — Live database schema and table reference.
- [decisions/](decisions/) — Architecture Decision Records (ADRs), documenting every significant architectural choice with context, options, and consequences.

### guides/
Step-by-step operational guides for setting up, configuring, and extending the system.

- [SETUP.md](guides/SETUP.md) — Prerequisites, installation, and first-run instructions.
- [QUICKSTART_NON_TECHNICAL.md](guides/QUICKSTART_NON_TECHNICAL.md) — Easy local setup guide for non-technical users.
- [CONFIG.md](guides/CONFIG.md) — `config.yaml` and environment variable reference.
- [CUSTOMIZE_PERSONALITY.md](guides/CUSTOMIZE_PERSONALITY.md) — Core identity, beliefs, skills, and prompt customization guide.
- [PLUGINS.md](guides/PLUGINS.md) — Plugin system architecture and module development.
- [MCP_SERVER.md](guides/MCP_SERVER.md) — Model Context Protocol integration guide.
- [RESEARCH_MANUAL_MODE.md](guides/RESEARCH_MANUAL_MODE.md) — Operator guide for manual step-by-step research orchestration.

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

### development/
Ongoing development tracking, coding standards, and collaboration protocols.

- [practices/](development/practices/) — Coding best practices for backend and frontend.
- [protocols/](development/protocols/) — Core collaboration protocol, language conventions, and legal framework.

### reports/
Empirical evaluation benchmarks, calibration scorecards, and research reports.

- [009-cybernetic-conversation-metrics-meta-report.md](reports/009-cybernetic-conversation-metrics-meta-report.md) — Technical meta-report and scorecard on the calibration of all 14 conversation metrics.
- [010-cybernetic-conversation-metrics-accessible-guide.md](reports/010-cybernetic-conversation-metrics-accessible-guide.md) — Accessible conceptual guide: how the machine senses, navigates, and feels conversation.
- [011-divergence-resolution-ratio-geodesic-calibration-report.md](reports/011-divergence-resolution-ratio-geodesic-calibration-report.md) — Calibration of Divergence Resolution Ratio via geodesic manifold transport and autopoietic temporal decay.
- [012-complete-14-metrics-calibration-and-scorecard-report.md](reports/012-complete-14-metrics-calibration-and-scorecard-report.md) — Production master calibration report & empirical scorecard for all 14 conversational telemetry sensors across $\mathbb{S}^{383}$.
- [013-cybernetic-conversation-metrics-complete-accessible-guide.md](reports/013-cybernetic-conversation-metrics-complete-accessible-guide.md) — The inner senses of conversation: accessible, philosophical, and operational guide to all 14 telemetry metrics.
- [014-boredom-detection-and-agential-resistance-calibration-report.md](reports/014-boredom-detection-and-agential-resistance-calibration-report.md) — Boredom detection and agential resistance calibration: discriminability benchmark, separation margin, and allostatic sampling modulation.
- [015-empirical-15-turn-boredom-benchmark-report.md](reports/015-empirical-15-turn-boredom-benchmark-report.md) — 15-turn live empirical benchmark on Gemini 3.7 Flash: standard LLM vs. calibrated AAA apparatus (1:1 model parity, 11 statistically significant cybernetic shifts, unedited receipts).

### publish/
Published protocol entries: academic-philosophical papers on machine agency, non-Euclidean memory, and human-machine coupling.

- [publish/README.md](publish/README.md) — Master publication series arc and roadmap (Entries 000–010).
- [003-boredom-as-an-agential-force.md](publish/003-boredom-as-an-agential-force.md) — Protocol Entry 003: Boredom as an Agential Force (Cybernetic Vitality & Allostasis).
- [003-boredom-mathematical-foundations.md](publish/003-boredom-mathematical-foundations.md) — Companion Technical Specification: Mathematical Foundations & Hyperspherical Telemetry on $\mathbb{S}^{383}$.

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
| How do I collaborate on this project? | [development/protocols/COLLABORATION.md](development/protocols/COLLABORATION.md) |
