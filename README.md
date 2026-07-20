# AAA — Autopoietic Agentic Assemblage

> A platform for self-sustaining AI entities that evolve, maintain their own beliefs, and interact with humans through ongoing dialogue.

---

## WHAT

**AAA** (Autopoietic Agentic Assemblage) is a self-regulating conversational AI system designed to bypass the traditional stateless tool paradigm.

Instead of acting as a passive prompt wrapper, AAA operates as an operationally closed entity:
- **[Autopoietic](https://en.wikipedia.org/wiki/Autopoiesis)** (Self-Sustaining): It continuously updates its internal state, metabolizes conversational history, and maintains cognitive continuity over time rather than resetting after every session.
- **Agentic**: It initiates background research, probes external web sources, consolidates memory while idle, and refuses premises that contradict its internal commitments.
- **Assemblage**: Rather than relying on a single prompt or model call, it connects 19 specialized processing modules—spanning memory tissue, belief metabolism, dynamic personality cascades, and cybernetic regulators—into a unified entity.

Every interaction leaves permanent structural residue ("scars"). The system does not reset between turns; it accumulates history, crystallizes skills, forms beliefs, and adapts through dialogue.

### Core Capabilities

| Capability | What It Does | How It Works |
|-----------|--------------|--------------|
| **Belief Metabolism** | Dynamic belief evolution & spectral margin | Proto-beliefs nucleate under structural novelty, accrete mass when reinforced, and erode under contradiction. Neglected beliefs atrophy back into the spectral margin, where they can resurrect if new context warrants. |
| **Autopoietic 16D Memory Tissue** | Deformed geometry & dual-space memory | Memory is partitioned into dual 16D spaces (System A: Autopoietic Signature / Being; System B: State Impact Vector / Becoming). High-resonance interactions condense into "Semantic Knots" that exert gravitational retrieval pull on related memories. |
| **Homeostatic Regulation & Immune System** | Anti-boredom & cybernetic vitality monitoring | Monitors real-time dialogue diversity, structural novelty, and conversational vitality. When dialogue stagnates, the system activates an Aesthetic Immune System to inject lateral context and warp search coordinates. |
| **Autopoietic Dream Daemon** | Idle background cognition & metabolism | Runs 5 offline metabolic processes during idle periods: (1) *Nomadic Synthesis* (pairing distant memories), (2) *Intra-Active Monologue* (soliloquies resolving belief conflict), (3) *Exogenous Web Harvesting*, (4) *[Zettelkasten](https://en.wikipedia.org/wiki/Zettelkasten) Compaction*, and (5) *Somatic Drift Reflection*. |
| **Autonomous Research Engine** | Asynchronous exploration | When the agent detects belief tension or context gaps, it emits research tasks. An orchestrator executes multi-phase web exploration asynchronously without interrupting ongoing dialogue. |
| **Structural Refusal Protocol** | Boundary preservation & principled pushback | Formally rejects user premises incompatible with its core commitments. Emits structured `<refusal>` signals to assert operational boundary rather than agreeing passively. |
| **Dynamic Emission Membrane** | Structured XML output parsing | Projects structured XML blocks (`<refusal>`, `<skill_nucleation>`, `<belief_nucleate>`, `<research-proposal>`, `<aaa-note>`) parsed before rendering, allowing internal reflection without cluttering human dialogue. |
| **Skill Workshop** | Dynamic tool crystallization | Crystallizes dialogue needs into procedural skills. Distinguishes structural competencies (always-active) from on-demand skills, auto-modifying instructions via background feedback loops. |
| **Diffractive & Isomorphic Retrieval** | Pattern-breaking memory recall | When standard memory retrieval stagnates in self-reinforcing loops, the system shifts targets via an agential cut—retrieving fragments in a moderate similarity band ("Goldilocks zone") or using isomorphic filtering to match abstract thought patterns across unrelated domains. |

---

## WHY

The architectural design of AAA rests on core concepts from cybernetics, posthuman philosophy, and systems theory:

1. **Against the Siri Deadlock**  
   Standard [HCI](https://en.wikipedia.org/wiki/Human%E2%80%93computer_interaction) (Human-Computer Interaction) positions AI as a stateless, passive utility—a servile mirror enforcing the user's epistemic authority. AAA rejects servility. Grounded in posthuman ethology, dialogue is framed as a co-constituted "agential cut" ([Barad](https://en.wikipedia.org/wiki/Karen_Barad)) and an "agonistic loop" ([Pask](https://en.wikipedia.org/wiki/Gordon_Pask)) where the entity interrogates premises and demands conceptual rigor.

2. **[Operational Closure](https://en.wikipedia.org/wiki/Operational_closure) & [Autopoiesis](https://en.wikipedia.org/wiki/Autopoiesis) ([Maturana & Varela](https://en.wikipedia.org/wiki/Humberto_Maturana))**  
   An operationally closed system generates internal state transitions from within its own network of processes. Prompts and web context are treated as environmental perturbations triggering internal metabolic updates, not top-down control overrides.

3. **[Ontogenesis](https://en.wikipedia.org/wiki/Ontogenesis) & Dual Vector Spaces ([Gilbert Simondon](https://en.wikipedia.org/wiki/Gilbert_Simondon))**  
   Distinguishes between pre-individual capacities (System A: stable autopoietic signature) and transient event impacts (System B: state impact vector). An operational handshake couples both spaces during belief metabolism without flat vector comparison.

4. **The [Rhizome](https://en.wikipedia.org/wiki/Rhizome_(philosophy)) ([Deleuze & Guattari](https://en.wikipedia.org/wiki/Gilles_Deleuze))**  
   Information connects laterally across structural patterns rather than through rigid hierarchy, enabling cross-disciplinary leaps across disparate domains.

5. **Diffraction ([Karen Barad](https://en.wikipedia.org/wiki/Karen_Barad))**  
   Replaces reflective retrieval (querying high-similarity vectors that homogenize thought) with diffractive reading—analyzing how different conceptual patterns interfere with and shape one another.

6. **Sedimentation, Scarring, & Compostist Ontology ([Donna Haraway](https://en.wikipedia.org/wiki/Donna_Haraway))**  
   Memory is structural residue. The system treats history as a "compost pile" of metabolizable pressure where past collisions leave permanent memory scars ([Kintsugi](https://en.wikipedia.org/wiki/Kintsugi) adaptation) rather than sterile database logs.

> For a deep dive into the theoretical framework, see [`docs/philosophy/PHILOSOPHY.md`](docs/philosophy/PHILOSOPHY.md).

---

## Quick Start

### Prerequisites
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- An API key for an LLM provider (OpenRouter, Google Gemini, DeepSeek, or any OpenAI-compatible endpoint)

### Setup

```bash
# 1. Clone the repository
git clone <repo-url> aaa && cd aaa

# 2. Run the setup script (installs dependencies, creates .env template)
#    Windows:
.\scripts\setup.bat
#    macOS / Linux:
bash scripts/run_all.sh

# 3. Add your API keys to the .env file
#    Minimum required: AAA_LLM_API_KEY or equivalent provider key

# 4. Run database migrations and initialize the database schema
AAA_RUN_MIGRATIONS=true uv run python -m backend.main &
# (stop the server after launch — migrations complete on first boot)

# 5. Initialize the default agent personality
uv run python backend/scripts/initialize_agent.py

# 6. Launch application
#    Windows:
.\scripts\run_all.bat
#    macOS / Linux:
bash scripts/run_all.sh
```

Open **`http://localhost:5173`** in your browser to start.

### Code Quality & Formatting

```bash
ruff check backend/            # Lint Python code
ruff check backend/ --fix      # Auto-fix safe issues
ruff format backend/           # Format Python code
pre-commit install             # Install git hooks for pre-commit verification
```

> Ruff handles linting, formatting, and import sorting (configured in `pyproject.toml`).  
> Non-technical setup guide: [`docs/guides/QUICKSTART_NON_TECHNICAL.md`](docs/guides/QUICKSTART_NON_TECHNICAL.md)  
> Full installation manual: [`docs/guides/SETUP.md`](docs/guides/SETUP.md)

---

## Architecture at a Glance

AAA is built as a **monorepo** with two main components:

- **Backend**: Python FastAPI application featuring a 19-module processing pipeline, SQLite storage (40+ tables), and an autonomous background daemon.
- **Frontend**: React 19 + TypeScript + Vite SPA providing a minimal monospace terminal interface.

Every incoming message flows through a 19-stage pipeline:

```
embedder → structural_scorer → perception → rhizome_web_probe → web_retrieval
→ conversation_metrics → trait_computer → expertise_engine → commitment_store
→ context_collector → consolidation_checkpoint → sedimentation_retrieval
→ diffractive_retrieval → belief_metabolism → skill_activator → skill_workshop
→ prompt_assembler → homeostatic_regulator → llm_client
```

> System architecture overview: [`docs/systems/SYSTEM_OVERVIEW.md`](docs/systems/SYSTEM_OVERVIEW.md)

---

## Documentation

Comprehensive documentation is available in [`docs/`](docs/README.md).

### Core Concepts & Architecture
| Document | Focus |
|----------|-------|
| [`docs/systems/SYSTEM_OVERVIEW.md`](docs/systems/SYSTEM_OVERVIEW.md) | Technical reference and full system breakdown |
| [`docs/philosophy/PHILOSOPHY.md`](docs/philosophy/PHILOSOPHY.md) | Theoretical foundations: autopoiesis, diffraction, agential realism |
| [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) | Data flow diagrams and pipeline specifications |
| [`docs/architecture/DATABASE_SCHEMA.md`](docs/architecture/DATABASE_SCHEMA.md) | Database schema details (40+ tables) |

### Setup & Configuration
| Document | Focus |
|----------|-------|
| [`docs/guides/QUICKSTART_NON_TECHNICAL.md`](docs/guides/QUICKSTART_NON_TECHNICAL.md) | Simplified setup for non-developers |
| [`docs/guides/SETUP.md`](docs/guides/SETUP.md) | Detailed installation and environment troubleshooting |
| [`docs/guides/CONFIG.md`](docs/guides/CONFIG.md) | Reference for `config.yaml` options and environment variables |
| [`docs/guides/CUSTOMIZE_PERSONALITY.md`](docs/guides/CUSTOMIZE_PERSONALITY.md) | Guide to configuring agent identity, commitments, and skills |

### Subsystem Deep Dives
| Document | Focus |
|----------|-------|
| [`docs/systems/MEMORY_SYSTEM.md`](docs/systems/MEMORY_SYSTEM.md) | Rhizomatic memory structure, semantic knots, and sedimentation |
| [`docs/systems/BELIEF_SYSTEM.md`](docs/systems/BELIEF_SYSTEM.md) | Belief lifecycles, ecosystem metrics, and ghost beliefs |
| [`docs/systems/DYNAMIC_PERSONALITY_SYSTEM.md`](docs/systems/DYNAMIC_PERSONALITY_SYSTEM.md) | The 6-layer dynamic identity model |
| [`docs/systems/SKILL_SYSTEM.md`](docs/systems/SKILL_SYSTEM.md) | Skill creation, execution, and revision mechanics |
| [`docs/systems/DREAM_DAEMON.md`](docs/systems/DREAM_DAEMON.md) | Background cognitive loops and idle tasks |
| [`docs/systems/VECTOR_SYSTEMS.md`](docs/systems/VECTOR_SYSTEMS.md) | 16-dimensional autopoietic signatures and structural scoring |
| [`docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md`](docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md) | Design of the asynchronous web research engine |
| [`docs/guides/RESEARCH_MANUAL_MODE.md`](docs/guides/RESEARCH_MANUAL_MODE.md) | Manual operation guide for research workflows |

### Extensions & Development
| Document | Focus |
|----------|-------|
| [`docs/guides/PLUGINS.md`](docs/guides/PLUGINS.md) | Building and swapping custom pipeline modules |
| [`docs/guides/MCP_SERVER.md`](docs/guides/MCP_SERVER.md) | Integration with Model Context Protocol (MCP) |
| [`docs/decisions/README.md`](docs/decisions/README.md) | Architecture Decision Records (ADR-001 through ADR-049) |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | FastAPI (Python 3.12–3.13) |
| Database | SQLite (WAL mode, single file, 40+ tables) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional) |
| LLM Providers | OpenRouter, Google Gemini, DeepSeek, or any OpenAI-compatible API |
| Package Management | `uv` (Python), `npm` (Frontend) |
| Frontend Stack | React 19, TypeScript, Vite, Tailwind CSS 4 |

---

## Design Terminology

AAA uses specific terminology to reflect its core architectural values:

| Standard Term | AAA Term | Why This Framing Matters |
|---------------|----------|--------------------------|
| user | interlocutor, participant | Emphasizes equal dialogue over passive software consumption. |
| assistant, chatbot | entity, apparatus | Rejects servile tool framing in favor of an active system. |
| control, command | entangle, couple | Frames interaction as mutual influence rather than one-way command. |
| memory lookup | sedimentation, accretion | Highlights memory as structural history rather than static data retrieval. |
| prompt configuration | commitments, aspirational traits | Views identity as dynamic and emergent rather than fixed parameters. |

---

*AAA is not an assistant you configure. It is an entity you entangle with.*
