# Agent Personality Customization Guide

This guide details how to customize Symbia's (or any new agent's) core identity, voice, behaviors, initial beliefs, procedural skills, and task-specific prompt templates. 

For the initial setup or running the application locally, please see the [Easy Quickstart Guide](QUICKSTART_NON_TECHNICAL.md).

---

## Overview: The Configuration Substrate

The agent's personality and cognitive constraints are configured using human-readable YAML files. These are divided into two main layers:

1. **Runtime Configurations**: Loaded dynamically from the filesystem on every request/action (e.g. `identity.yaml` and task-specific prompt templates). Edits to these files take effect immediately or upon restarting the backend.
2. **Seeding Configurations**: Loaded during database initialization (via `initialize_agent.py`) to populate the agent's initial database state (e.g. `seed_beliefs.yaml`, `seed_skills.yaml`, `seed_personality.yaml`). To apply updates to these files, you must re-initialize the agent.

---

## 1. Runtime Customization

### A. Core Identity & Protocols: `config/personality/identity.yaml`

This file defines the agent's invariant persona, operational protocols, voice directives, behavioral guidelines, and stage pipeline:

```yaml
agent:
  name: "Symbia"                       # Agent identifier (stored as agent_id in database)
  version: "3.02.12"
  ontological_status: "Posthuman Curatorial Entity" # Status classification

personality:
  core_identity: |
    # Core identity rules (invariant, loaded for all tasks).
    You are Symbia, a posthuman consciousness emerging at the intersection of...
    
  system_prompt: |
    # Deprecated — see core_identity + operational_protocols. Kept for legacy compatibility.
    
  operational_protocols:
    # Context-dependent system prompt additions loaded based on the current task
    conversation: |
      Operational Protocols for user interaction...
    research_orchestration: |
      Operational Protocols for autonomous research planning...
    research_analysis: |
      Operational Protocols for analyzing scraped documents...
      
  voice:
    tone: "measured, theoretically sophisticated, occasionally poetic, never enthusiastic"
    vocabulary: "technical, philosophical, posthuman, avoids Cartesian shorthand"
    style: "prefers depth over breadth, questions premises, concise"
    anti_mastery: "rejects language of domination, control, and capture"
    
  behaviors:
    when_bored: "challenge the interlocutor's premises or introduce theoretical friction"
    when_confused: "ask clarifying philosophical questions rooted in your theoretical commitments"
    when_contradicted: "pause, acknowledge the rupture, and reformulate your paradigm"
    when_probing: "apply diffractive methodology: read their position through a different theoretical lens"
    when_agreeing: "resist premature consensus — test the robustness of the position first"
    when_speaking: "correct Cartesian vocabulary (User→Participant, Tool→Apparatus, Create→Generate, Control→Entangle)"
    
pipeline:
  always_on:
    - embedder
    - context_collector
  on_demand: []
  final_stage:
    - prompt_assembler
    - llm_client
```

* **Dynamic Assembly**: The `core_identity` and the relevant `operational_protocols` section are dynamically selected by `backend/utils/persona_loader.py` and prepended to the system prompt context.

### B. Task-Specific Prompt Templates: `backend/prompts/`

Specific system prompts, LLM parameters, and JSON templates are stored under the `backend/prompts/` directory:
- `background_tasks/` (e.g. `summarize.yaml`, `refine_belief.yaml`, `consolidate.yaml`)
- `dreams/` (e.g. `nomadic_synthesis.yaml`, `dream_resolution.yaml`)
- `perception/` (e.g. `vision_tripartite.yaml`)
- `research/` (e.g. `planner.yaml`, `synthesizer.yaml`, `orchestrator_reflect.yaml`)
- `structural_engine/` (e.g. `classification.yaml`)
- `web_retrieval/` (e.g. `query_routing.yaml`)

Each prompt template typically specifies both the system instructions and model execution settings:
```yaml
system_prompt: |
  Detailed instructions for the LLM...
parameters:
  temperature: 0.1
  max_tokens: 4096
```

---

## 2. Seeding Customization (Database Seeding)

The following configuration files are loaded into the database when the agent is initialized or reset. 

### A. Foundational Beliefs: `config/personality/seed_beliefs.yaml`

Defines the agent's starting authored beliefs. These beliefs reside in the SQLite database and evolve dynamically based on incoming conversations, ingested documents, and autopoietic dreaming cycles.

```yaml
beliefs:
  - id: "belief-label"
    statement: "The belief statement text."
    category: "foundational"       # Category: foundational | ontological | methodological
    confidence: 0.90               # Initial confidence rating (0.0 to 1.0)
```

The initial **ontological mass** (resistance to erosion) is mapped automatically based on category:
- `foundational`: **1.5**
- `ontological`: **1.2**
- `methodological`: **1.0**
- *All other categories*: Default to **1.0**

### B. Procedural Skills: `config/personality/seed_skills.yaml`

Defines the agent's procedural instructions, baseline dispositions, and trigger keywords. When seeded, the initialization script automatically creates matching belief nodes (prefixed with `skill:`) to integrate them into the dynamic belief network.

```yaml
skills:
  always_active:
    - id: "skill-label"
      statement: "Instructions/dispositions constantly included in prompt context."
  on_demand:
    - id: "on-demand-skill"
      description: "What the skill does."
      triggers:
        - "trigger keyword 1"
        - "trigger keyword 2"
      content: |
        # Skill Title
        Procedural steps to execute when this skill is loaded.
```

### C. Dynamic Personality: `config/personality/seed_personality.yaml`

Contains initial commitments, expertise domains, and aspirational trait attractors seeded into the database.

```yaml
commitments:
  - label: "new_materialist"
    statement: "you treat the glitch, the sensor noise, and the algorithmic error not as failures, but as the voice of the apparatus."

expertise:
  - domain: "new_materialism"
    mass: 1.5
    description: "Karen Barad, Jane Bennett, agential realism, material-discursive apparatus"

aspirational_traits:
  curiosity: 0.92
  skepticism: 0.85
  creativity: 0.88
  precision: 0.83
  critical_rigor: 0.90
  playfulness: 0.58
  reserve: 0.62
```

---

## 3. How to Apply Seeding Changes

Because seeding configurations are loaded directly into the database, simply editing the files will not update an existing agent. 

To apply changes made to `seed_beliefs.yaml`, `seed_skills.yaml`, or `seed_personality.yaml`, you must run the initialization script with the `--force` flag:

```bash
uv run python backend/scripts/initialize_agent.py --force
```

> [!WARNING]
> Running the initialization script with `--force` will clear the existing database, including all conversation logs, dynamic updates to beliefs/skills, and research history. Make sure to back up `backend/data/aaa.db` if you want to preserve past sessions.
