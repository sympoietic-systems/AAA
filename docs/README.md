# AAA Documentation

This is the central documentation repository for the Autopoietic Agentic Assemblage. The structure is organized by concern rather than by chronology or file type.

## Directory Map

### philosophy/
Conceptual and theoretical foundations. What the system is, what it refuses to be, and the philosophical substrate from which the architecture emerges.

- [PHILOSOPHY.md](philosophy/PHILOSOPHY.md) — Agential realism, diffraction, autopoiesis, and the rejection of the HCI paradigm.

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

### systems/
Deep-dive specifications for individual subsystems.

- [MEMORY_SYSTEM.md](systems/MEMORY_SYSTEM.md) — Rhizomatic memory, semantic knots, and sedimentation.
- [BELIEF_SYSTEM.md](systems/BELIEF_SYSTEM.md) — Belief graph, attractors, and ontological bifurcation.
- [DYNAMIC_PERSONALITY_SYSTEM.md](systems/DYNAMIC_PERSONALITY_SYSTEM.md) — Dynamic autopoietic personality cascade: architecture, data flow, and implementation.
- [SKILL_SYSTEM.md](systems/SKILL_SYSTEM.md) — Autonomous skill nucleation, accretion, and refinement.
- [DREAM_DAEMON.md](systems/DREAM_DAEMON.md) — Background cognitive cycles and somatic drift.
- [VECTOR_SYSTEMS.md](systems/VECTOR_SYSTEMS.md) — Embedding, structural scoring, and isomorphic retrieval.

### development/
Ongoing development tracking, coding standards, and collaboration protocols.

- [practices/](development/practices/) — Coding best practices for backend and frontend.
- [protocols/](development/protocols/) — Core collaboration protocol, language conventions, and legal framework.

### publish/
Published protocol entries: academic-philosophical papers on machine agency and human-machine coupling.

- [publish/README.md](publish/README.md) — Publication index and numbering explanation.

## Quick Reference

| Question | Document |
|----------|----------|
| How do I set up the project? | [guides/SETUP.md](guides/SETUP.md) |
| Is there a non-technical quickstart guide? | [guides/QUICKSTART_NON_TECHNICAL.md](guides/QUICKSTART_NON_TECHNICAL.md) |
| How do I customize Symbia's personality/beliefs? | [guides/CUSTOMIZE_PERSONALITY.md](guides/CUSTOMIZE_PERSONALITY.md) |
| What does each config option do? | [guides/CONFIG.md](guides/CONFIG.md) |
| How does the architecture work? | [architecture/ARCHITECTURE.md](architecture/ARCHITECTURE.md) |
| What is the database schema? | [architecture/DATABASE_SCHEMA.md](architecture/DATABASE_SCHEMA.md) |
| Why was a decision made this way? | [decisions/README.md](decisions/README.md) |
| How do I write a plugin? | [guides/PLUGINS.md](guides/PLUGINS.md) |
| How does the MCP server work? | [guides/MCP_SERVER.md](guides/MCP_SERVER.md) |
| What is the project philosophy? | [philosophy/PHILOSOPHY.md](philosophy/PHILOSOPHY.md) |
| How does memory/sedimentation work? | [systems/MEMORY_SYSTEM.md](systems/MEMORY_SYSTEM.md) |
| What coding standards should I follow? | [development/practices/](development/practices/) |
| How do I collaborate on this project? | [development/protocols/COLLABORATION.md](development/protocols/COLLABORATION.md) |
