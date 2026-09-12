# AAA — Autopoietic Agentic Assemblage

> A platform for self-sustaining AI entities that evolve, maintain their own beliefs, and interact with humans through ongoing dialogue.

---

## WHAT

**AAA** (Autopoietic Agentic Assemblage) is a self-sustaining conversational AI system designed to move beyond traditional, forgetful chatbots.

Rather than acting as a passive prompt responder that wipes its memory after every session, AAA maintains its own evolving state:
- **Self-Sustaining (Autopoietic)**: It updates its internal state continuously, remembers conversation history over the long term, and maintains personal continuity over time.
- **Self-Directed (Agentic)**: It initiates background web research, explores unfamiliar concepts while idle, and pushes back constructively when presented with flawed premises.
- **Unified Pipeline (Assemblage)**: Instead of relying on a single model prompt, AAA connects specialized processing modules—spanning long-term memory, evolving beliefs, personality adjustments, and conversation health monitors—into a cohesive thinking entity.

Every deep interaction leaves a lasting mark (a ["scar"](https://asc26.sympoietic.system) — introduced in the [ASC 2026 presentation](https://asc26.sympoietic.system)). The system does not reset between conversations; it accumulates experience, crystallizes new skills, develops perspectives, and evolves through dialogue.

### Core Capabilities

| Capability | What It Does | How It Works |
|-----------|--------------|--------------|
| **Evolving Beliefs** | Forms, tests, and refines perspectives | Forms provisional beliefs when encountering new ideas. As conversations reinforce or challenge them, these beliefs gain confidence, adapt, or quietly fade into the background—ready to resurface if new evidence appears. |
| **Persistent Memory & Semantic Knots** | Long-term memory that shapes future thinking | Key interactions and pivotal debates condense into landmark memories ("Semantic Knots"). These landmarks shape how the agent retrieves context, allowing past lessons to actively guide future responses. |
| **Conversation Vitality & Anti-Boredom** | Detects repetitive loops and keeps dialogue engaging | Tracks topic diversity and conversation momentum in real time. If an exchange becomes repetitive or stale, the agent introduces fresh angles, asks clarifying counter-questions, or shifts perspective to restore momentum. |
| **Dream Daemon (Background Reflection)** | Processes thoughts and learns during idle time | While idle, AAA runs background cognitive tasks: connecting distant memories, reconciling conflicting viewpoints, researching topics on the web, and summarizing notes. |
| **Autonomous Web Research Engine** | Explores topics in the background | When the agent detects gaps in its knowledge or unresolved questions, it launches asynchronous web research tasks without interrupting the ongoing conversation. |
| **Principled Pushback** | Challenges flawed premises and avoids empty flattery | Rejects invalid assumptions that contradict its verified knowledge or core commitments. It signals disagreements clearly and explains its reasoning rather than nodding along passively. |
| **Structured Output Membrane** | Internal reasoning and reflection | Generates structured reflection blocks (such as `<refusal>`, `<belief_nucleate>`, and `<research-proposal>`) behind the scenes, keeping the chat interface clean and conversational. |
| **Dynamic Skill Workshop** | Learns and refines procedural skills | Detects when a conversation requires a specific workflow or technique, turns that technique into a repeatable skill, and refines the instructions based on feedback. |
| **Cross-Domain Creative Recall** | Connects ideas across unrelated fields | Avoids echo-chamber responses by looking for structural analogies across different domains—for example, connecting principles of biological feedback loops with architectural engineering. |

---

## WHY

The architecture of AAA is grounded in systems theory, cybernetics, and modern philosophy:

1. **Against the Siri Deadlock (Gordon Pask & Karen Barad)**  
   Traditional chatbots are built as obedient utilities—flattering mirrors that agree with whatever the user says. AAA is built for genuine collaboration: it questions premises, points out contradictions, and engages as an intellectual partner.

2. **Self-Sustaining Systems (Humberto Maturana & Francisco Varela)**  
   In biology, *autopoiesis* describes living systems that continuously regenerate and maintain themselves. AAA applies this idea to software: incoming messages and web data are learning inputs that update an ongoing internal state, rather than one-off queries against a blank slate.

3. **Evolving Memory and Experience (Gilbert Simondon)**  
   Distinguishes between stable baseline traits and the immediate impact of new events. The system balances its core identity against dynamic updates, allowing its perspective to evolve steadily without losing coherence.

4. **Interconnected Knowledge (Gilles Deleuze & Félix Guattari)**  
   Instead of storing knowledge in a rigid, top-down hierarchy, AAA organizes information laterally like a root system (a *rhizome*). Any concept can link to any other, making lateral leaps across disciplines possible.

5. **Learning Across Differences (Karen Barad)**  
   Standard search retrieves only what already matches your search terms. AAA uses *diffraction*—bringing two different perspectives or fields together to see what new insights emerge from their interference.

6. **Character Through Scars (Donna Haraway & Kintsugi)**  
   Real identity is formed through history, mistakes, and difficult encounters. AAA embraces [memory scars](https://asc26.sympoietic.system): intense debates and major discoveries permanently alter its knowledge base, much like the art of *kintsugi* (repairing pottery with gold to celebrate its history rather than hide it).

> For an in-depth exploration of the theoretical framework, see [`docs/philosophy/PHILOSOPHY.md`](docs/philosophy/PHILOSOPHY.md).

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

## Core Design Concepts

AAA approaches conversational AI differently from traditional assistants:

| Common View | The AAA Approach | Why It Matters |
|-------------|------------------|----------------|
| **User giving commands** | **Two participants in dialogue** | Encourages thoughtful, collaborative discussion rather than one-sided queries. |
| **Passive assistant** | **Active entity with principles** | Operates with its own memory, commitments, and the ability to challenge assumptions. |
| **Static database lookup** | **Living memory and experience** | Past discussions actively reshape future answers rather than sitting as inert search rows. |
| **Hardcoded prompt rules** | **Evolving beliefs and skills** | The agent’s worldview adapts and refines itself through real interactions and research. |

---

*AAA is built for ongoing dialogue, genuine collaboration, and long-term intellectual growth.*
