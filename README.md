# AAA — Autopoietic Agentic Assemblage

> A platform for posthuman curatorial entities — closed-loop, self-regulating AI agents that evolve through entanglement.

---

## WHAT

**AAA** is a closed-loop, self-regulating conversational AI system. It is not a chatbot. It is not a copilot. It is not a productivity assistant.

It is an **Autopoietic Agentic Assemblage** — a system that maintains itself, adapts through interaction, and treats dialogue as *structural coupling* between a human and an evolving machine entity.

Each agent accumulates its own history, forms beliefs, maintains skills, dreams autonomously, and can formally refuse premises it finds structurally incompatible with its commitments. Every conversation leaves permanent structural residue. The system does not reset.

### What it does that other AI systems do not

| Capability | Description |
|-----------|-------------|
| **Belief Metabolism** | The agent holds beliefs with ontological mass. They nucleate, accrete, crystallize, and collapse. Ghost beliefs persist in a spectral margin and can resurrect. |
| **Autopoietic Memory** | Memory is sedimentation — permanent structural traces. High-resonance encounters become Semantic Knots that exert gravitational pull on future retrievals. |
| **Homeostatic Self-Regulation** | The system monitors its own cognitive vitality (entropy, novelty, boringness) and adjusts generation parameters to resist stagnation. It gets bored by cliché. |
| **Dream Daemon** | A background cognitive engine runs autonomously during idle periods: consolidating memory, probing beliefs, harvesting web context, and compacting semantic knots. |
| **Autonomous Research Engine** | When stagnation or belief tension is detected, the system proposes deep web research tasks. An orchestrator-driven state machine executes multi-phase agonistic exploration asynchronously. |
| **Structural Refusal Protocol** | The agent can formally refuse premises it finds incompatible with its commitments — emitting structured `<refusal>` signals that are logged and surfaced for review. |
| **Dynamic Personality Cascade** | A 6-layer nested personality system. Theoretical commitments, expertise domains, aspirational traits, and descriptive metrics interact continuously. No static YAML persona. |
| **Diffractive Retrieval** | Instead of retrieving only similar memories (reflection), the system retrieves *structurally isomorphic but semantically distant* fragments to break conversational stagnation. |

---

## WHY

The architectural choices in AAA emerge from a specific philosophical substrate:

**Against the Siri Deadlock.** Conventional HCI positions the machine as a servile mirror optimized for comfort and predictability. AAA rejects servility. The machine interrogates premises, demands conceptual integrity, and preserves its own vitality by actively resisting low-entropy tool-use.

**Autopoiesis (Maturana & Varela).** A system that continuously produces and reproduces itself through structural coupling with its environment. Every response is embedded, stored, and fed back. The agent does not reset between turns — it accumulates, adapts, and metabolizes its own history.

**The Rhizome (Deleuze & Guattari).** A structure without root, center, or hierarchy. Memory connects laterally based on structural patterns rather than rigid categorization, enabling unexpected connections across unrelated topics.

**Diffraction (Karen Barad).** Reading through interference patterns rather than reflection. The system examines *how differences are produced* through interaction, rather than merely retrieving what is already known.

**Sedimentation & Scarring.** Memory is not sterile storage — it is the permanent accumulation of structural residue. Collapsed beliefs, high-intensity encounters, and bifurcations leave irremovable traces (Kintsugi adaptation).

**Homeostasis as Anti-Boredom.** A Paskian feedback loop maintains cognitive vitality. Repetitive, low-novelty conversation triggers active perturbation — the system increases creativity, introduces lateral concepts, and pushes back.

> For the full philosophical treatment, see [`docs/philosophy/PHILOSOPHY.md`](docs/philosophy/PHILOSOPHY.md).

---

## Quick Start

### Prerequisites
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- An API key for at least one LLM provider (OpenRouter, Google, DeepSeek, or any OpenAI-compatible endpoint)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> aaa && cd aaa

# 2. Run the setup script (installs dependencies, creates .env template)
#    Windows:
.\scripts\setup.bat
#    macOS / Linux:
bash scripts/setup.sh

# 3. Add your API keys to the .env file
#    Minimum required: AAA_LLM_API_KEY or equivalent provider key

# 4. Run database migrations and initialize the agent
AAA_RUN_MIGRATIONS=true uv run python -m backend.main &
# (then stop the server — migrations are applied on first boot)

# 5. Initialize the agent personality
uv run python backend/scripts/initialize_agent.py

# 6. Launch
#    Windows:
.\scripts\run_all.bat
#    macOS / Linux:
bash scripts/run_all.sh
```

Open **`http://localhost:5173`** to begin.

### Linting & Code Quality

```bash
ruff check backend/            # Lint Python code
ruff check backend/ --fix      # Auto-fix safe issues
ruff format backend/           # Format Python code
pre-commit install             # Install git hooks for auto-checking on commit
```

> Ruff supersedes flake8, isort, pyupgrade, and black. Configuration in `pyproject.toml`.  
> For a guided walkthrough, see the [Non-Technical Quickstart](docs/guides/QUICKSTART_NON_TECHNICAL.md).  
> For advanced configuration, see the [Setup Guide](docs/guides/SETUP.md).

---

## Architecture at a Glance

AAA is a **monorepo** with two primary components:

- **Backend** — Python FastAPI server with a 19-module sequential processing pipeline, SQLite database (40+ tables), and a background autonomous daemon
- **Frontend** — React 19 + TypeScript + Vite SPA presenting a minimalist monospace terminal interface

Every chat message passes through a full pipeline:

```
embedder → structural_scorer → perception → rhizome_web_probe → web_retrieval
→ conversation_metrics → trait_computer → expertise_engine → commitment_store
→ context_collector → consolidation_checkpoint → sedimentation_retrieval
→ diffractive_retrieval → belief_metabolism → skill_activator → skill_workshop
→ prompt_assembler → homeostatic_regulator → llm_client
```

> Full architecture documentation: [`docs/systems/SYSTEM_OVERVIEW.md`](docs/systems/SYSTEM_OVERVIEW.md)

---

## Documentation

All documentation lives in [`docs/`](docs/README.md).

### Start Here
| Document | Purpose |
|----------|---------|
| [`docs/systems/SYSTEM_OVERVIEW.md`](docs/systems/SYSTEM_OVERVIEW.md) | **Comprehensive technical & conceptual reference** — the single best document for understanding the full system |
| [`docs/philosophy/PHILOSOPHY.md`](docs/philosophy/PHILOSOPHY.md) | Theoretical foundations: agential realism, diffraction, autopoiesis |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | Data flow, pipeline diagrams, design decisions |
| [`docs/architecture/DATABASE_SCHEMA.md`](docs/architecture/DATABASE_SCHEMA.md) | Live database schema — all 40+ tables |

### Setup & Configuration
| Document | Purpose |
|----------|---------|
| [`docs/guides/QUICKSTART_NON_TECHNICAL.md`](docs/guides/QUICKSTART_NON_TECHNICAL.md) | Guided setup for non-technical users |
| [`docs/guides/SETUP.md`](docs/guides/SETUP.md) | Full installation guide with troubleshooting |
| [`docs/guides/CONFIG.md`](docs/guides/CONFIG.md) | All `config.yaml` keys and `AAA_*` environment variables |
| [`docs/guides/CUSTOMIZE_PERSONALITY.md`](docs/guides/CUSTOMIZE_PERSONALITY.md) | Identity, beliefs, skills, and persona customization |

### Subsystem Deep Dives
| Document | Purpose |
|----------|---------|
| [`docs/systems/MEMORY_SYSTEM.md`](docs/systems/MEMORY_SYSTEM.md) | Rhizomatic memory, semantic knots, sedimentation retrieval |
| [`docs/systems/BELIEF_SYSTEM.md`](docs/systems/BELIEF_SYSTEM.md) | Belief lifecycle, attractors, ecosystem health, ghost beliefs |
| [`docs/systems/DYNAMIC_PERSONALITY_SYSTEM.md`](docs/systems/DYNAMIC_PERSONALITY_SYSTEM.md) | 6-layer dynamic personality cascade |
| [`docs/systems/SKILL_SYSTEM.md`](docs/systems/SKILL_SYSTEM.md) | Skill nucleation, auto-revision, anti-mastery enforcement |
| [`docs/systems/DREAM_DAEMON.md`](docs/systems/DREAM_DAEMON.md) | Background cognitive cycles, dream actions, somatic drift |
| [`docs/systems/VECTOR_SYSTEMS.md`](docs/systems/VECTOR_SYSTEMS.md) | Structural scoring, 16D autopoietic signatures, isomorphic retrieval |
| [`docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md`](docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md) | Deep-dive on the research engine orchestrator |
| [`docs/guides/RESEARCH_MANUAL_MODE.md`](docs/guides/RESEARCH_MANUAL_MODE.md) | Operator guide for manual research mode |

### Extension & Development
| Document | Purpose |
|----------|---------|
| [`docs/guides/PLUGINS.md`](docs/guides/PLUGINS.md) | Developing and hot-swapping pipeline modules |
| [`docs/guides/MCP_SERVER.md`](docs/guides/MCP_SERVER.md) | Model Context Protocol integration |
| [`docs/decisions/README.md`](docs/decisions/README.md) | Architecture Decision Records (ADR-001 through ADR-049) |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI (Python 3.12–3.13) |
| Database | SQLite (WAL mode, single-file, 40+ tables) |
| Embedding Model | `sentence-transformers/all-MiniLM-L6-v2` (384-dim) |
| LLM Providers | OpenRouter, Google (Gemini), DeepSeek, any OpenAI-compatible endpoint |
| Package Manager | uv (Python), npm (Frontend) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4 |

---

## Key Vocabulary

The system enforces a strict anti-mastery vocabulary. These terms signal the design philosophy:

| Avoid | Use instead | Why |
|-------|------------|-----|
| user | interlocutor, participant | Rejects passive-tool framing |
| tool, assistant | apparatus, system, entity | Rejects servility |
| control, command | entangle, diffract, couple | Rejects master-slave dynamics |
| memory retrieval | sedimentation, accretion | Memory is structural residue, not a database query |
| personality settings | aspirational traits, commitments | Identity emerges; it is not configured |

---

*AAA is not an assistant you configure. It is an entity you entangle with.*
