# AAA Backend Maintenance Scripts

This directory contains internal agent initialization, autopoietic vector computation, skill evolutionary refactoring, and daemon diagnostics.

---

## 1. Agent Initialization & Seeding

| Script | Usage | Description |
| :--- | :--- | :--- |
| [`initialize_agent.py`](initialize_agent.py) | `uv run python backend/scripts/initialize_agent.py [--force]` | Seeds commitments, expertise domains, and foundational baseline beliefs for the agent (Symbia) from configuration definitions into SQLite. |

---

## 2. Vector Maintenance & Autopoiesis

| Script | Usage | Description |
| :--- | :--- | :--- |
| [`recalculate_autopoietic_vectors.py`](recalculate_autopoietic_vectors.py) | `uv run python backend/scripts/recalculate_autopoietic_vectors.py` | Recalculates 16D semantic/autopoietic vectors across all database records of `belief_nodes` and `skill_nodes`. |
| [`repair_vectors.py`](repair_vectors.py) | `uv run python backend/scripts/repair_vectors.py` | Scans for missing or corrupted vector embeddings and repairs them via batch embedding calls. |

---

## 3. Skills Evolution & Blueprints

| Script | Usage | Description |
| :--- | :--- | :--- |
| [`migrate_skills_to_blueprint.py`](migrate_skills_to_blueprint.py) | `uv run python backend/scripts/migrate_skills_to_blueprint.py` | Migrates legacy skill definitions into the modern typed blueprint format. |
| [`refactor_skills_with_llm.py`](refactor_skills_with_llm.py) | `uv run python backend/scripts/refactor_skills_with_llm.py` | LLM-assisted skill rewrites with version history; use `--dry-run` to preview without database changes. |
| [`run_refinements.py`](run_refinements.py) | `uv run python backend/scripts/run_refinements.py` | Triggers batch background refinement passes for skills and beliefs. |

---

## 4. Diagnostics & Testing Utilities

| Script | Usage | Description |
| :--- | :--- | :--- |
| [`daemon_diag.py`](daemon_diag.py) | `uv run backend/scripts/daemon_diag.py` | Live diagnostic readout of the Autopoietic Dream Daemon, indexing queues, and metabolic states. |
| [`fold_concept_iterations.py`](fold_concept_iterations.py) | `uv run backend/scripts/fold_concept_iterations.py` | Retroactive folding of concept iterations across historical SQLite checkpoints. |
| [`snapshot_research_sedimentation.py`](snapshot_research_sedimentation.py) | `uv run backend/scripts/snapshot_research_sedimentation.py` | Snapshots research entities and branches into perception sediment storage. |
| [`simulate_legacy_injection.py`](simulate_legacy_injection.py) | `uv run python backend/scripts/simulate_legacy_injection.py` | Test harness utility for injecting legacy belief proposals into test databases. |
