"""Unified agent initialization and seeding script.

Runs all migrations, validates the environment configuration, and seeds foundational
beliefs, skills, and dynamic personality tables in a single command.

Usage:
    uv run python backend/scripts/initialize_agent.py [--force] [--db <path>]
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Ensure project root is in python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load dotenv before importing config to ensure override validation is correct
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

from backend.modules.structural_engine import LexiconScorer  # noqa: E402
from backend.personality.seeding import seed_dynamic_personality  # noqa: E402
from backend.storage.database import get_db_path, init_db  # noqa: E402
from backend.storage.repository import (  # noqa: E402
    BeliefRepository,
    CommitmentRepository,
    ExpertiseRepository,
    PersonalityStateRepository,
    SkillRepository,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("initialize_agent")


def validate_environment() -> bool:
    """Validate that .env is present and has actual LLM API keys configured."""
    if not ENV_PATH.exists():
        logger.error(
            "========================================================================\n"
            "ERROR: .env file not found at the project root.\n"
            "Please copy .env.example to .env and configure your API keys:\n"
            "    copy .env.example .env\n"
            "========================================================================"
        )
        return False

    # Read environment variables
    models = os.environ.get("AAA_LLM_MODELS", "").strip()
    openrouter_key = os.environ.get("AAA_LLM_API_KEY", "").strip()
    deepseek_key = os.environ.get("AAA_DEEPSEEK_API_KEY", "").strip()
    google_key = os.environ.get("AAA_GOOGLE_API_KEY", "").strip()

    # Check for placeholder values
    placeholders = {
        "your_openrouter_api_key_here",
        "your_deepseek_api_key_here",
        "your_google_api_key_here",
        "AIzaSyDLYF3wt...",
    }

    has_valid_key = False
    configured_keys = []

    if openrouter_key and openrouter_key not in placeholders:
        has_valid_key = True
        configured_keys.append("OpenRouter (AAA_LLM_API_KEY)")
    if deepseek_key and deepseek_key not in placeholders:
        has_valid_key = True
        configured_keys.append("DeepSeek (AAA_DEEPSEEK_API_KEY)")
    if google_key and google_key not in placeholders:
        has_valid_key = True
        configured_keys.append("Google/Gemini (AAA_GOOGLE_API_KEY)")

    if not has_valid_key:
        logger.error(
            "========================================================================\n"
            "ERROR: No valid LLM API key found in .env.\n"
            "Please open .env and set at least one of the following:\n"
            "  - AAA_LLM_API_KEY (for OpenRouter models)\n"
            "  - AAA_DEEPSEEK_API_KEY (for DeepSeek models)\n"
            "  - AAA_GOOGLE_API_KEY (for Google/Gemini models)\n"
            "========================================================================"
        )
        return False

    if not models:
        logger.warning(
            "========================================================================\n"
            "WARNING: AAA_LLM_MODELS is not defined in your environment.\n"
            "The system will fall back to using default models specified in config.yaml.\n"
            "========================================================================"
        )
    else:
        logger.info(f"Valid LLM API key(s) detected: {', '.join(configured_keys)}")
        logger.info(f"Models priority sequence: {models}")

    return True


def generate_skill_content(name: str, description: str, is_always_active: bool) -> str:
    sections = [f"# {name}\n\n{description}\n"]
    if is_always_active:
        sections.append("\n## Baseline Disposition\n\n")
        sections.append(
            "This skill is a baseline disposition — part of Symbia's core personality, not a tool to activate.\n"
        )
        sections.append("It is always present in the system prompt and guides every interaction.\n")
        sections.append("\n## Application\n\n")
        sections.append("Apply this disposition continuously. It requires no explicit invocation.\n")
    else:
        sections.append("\n## When to Use\n\n")
        sections.append("This skill is loaded when the conversation context matches its trigger patterns.\n")
        sections.append("\n## Application\n\n")
        sections.append("Follow the instructions below when this skill is active.\n")
    return "".join(sections)


def compute_vector(text: str, scorer: LexiconScorer, wrap_dict: bool = False) -> str:
    try:
        v16d = scorer.score(text)
        vec_list = v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)
    except Exception as e:
        logger.warning(f"Failed to compute 16D structural vector: {e}")
        vec_list = [0.0] * 16

    if wrap_dict:
        return json.dumps({"v16d": vec_list, "v384d": []})
    return json.dumps(vec_list)


def main():
    parser = argparse.ArgumentParser(description="Unified initialization script for AAA Agent.")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing database and force re-seed all tables."
    )
    parser.add_argument("--db", default="data/aaa.db", help="Database path (default: data/aaa.db).")
    parser.add_argument(
        "--ignore-env",
        action="store_true",
        help="Run seeding even if environment validation fails (development offline mode).",
    )
    args = parser.parse_args()

    logger.info("Initializing Agent Setup...")

    # 1. Environment Validation
    env_ok = validate_environment()
    if not env_ok and not args.ignore_env:
        logger.error(
            "Initialization aborted due to environment validation failure. Fix your .env or run with --ignore-env."
        )
        sys.exit(1)

    # 2. Database Path and Migration Initialization
    db_path = str(get_db_path(args.db))
    logger.info(f"Connecting to database: {db_path}")

    # Initialize DB (creates database and automatically runs all migrations)
    conn = init_db(db_path)
    conn.close()
    logger.info("Database migrations verified and up to date.")

    # Repositories
    belief_repo = BeliefRepository(db_path)
    skill_repo = SkillRepository(db_path)
    commitment_repo = CommitmentRepository(db_path)
    expertise_repo = ExpertiseRepository(db_path)
    personality_state_repo = PersonalityStateRepository(db_path)

    # Scorer for 16D local vector calculation
    scorer = LexiconScorer()

    # Handle force resets
    if args.force:
        logger.info("Force reset requested. Clearing existing tables...")
        reset_conn = sqlite3.connect(db_path)
        cursor = reset_conn.cursor()

        # Clear dynamic personality tables
        cursor.execute("DELETE FROM commitment_events")
        cursor.execute("DELETE FROM commitment_nodes")
        cursor.execute("DELETE FROM expertise_nodes")
        cursor.execute("DELETE FROM personality_state")

        # Clear beliefs and skills
        cursor.execute("DELETE FROM belief_nodes")
        cursor.execute("DELETE FROM skill_nodes")

        reset_conn.commit()
        reset_conn.close()
        logger.info("Database tables cleared.")

    # 3. Seed Foundational Beliefs
    seed_beliefs_file = PROJECT_ROOT / "config" / "personality" / "seed_beliefs.yaml"
    existing_beliefs = belief_repo.list_beliefs("symbia")

    if len(existing_beliefs) > 0 and not args.force:
        logger.info(f"Database already has {len(existing_beliefs)} beliefs. Skipping belief seeding.")
    else:
        logger.info(f"Seeding foundational beliefs from {seed_beliefs_file.name}...")
        if not seed_beliefs_file.exists():
            logger.error(f"Beliefs seed file not found: {seed_beliefs_file}")
            sys.exit(1)

        with open(seed_beliefs_file, encoding="utf-8") as f:
            beliefs_data = yaml.safe_load(f)

        beliefs_list = beliefs_data.get("beliefs", [])
        seeded_beliefs_count = 0

        for cb in beliefs_list:
            label = cb.get("id")
            statement = cb.get("statement")
            confidence = cb.get("confidence", 0.5)
            category = cb.get("category", "ontological")

            # Map category to ontological mass
            if category == "foundational":
                mass = 1.5
            elif category == "ontological":
                mass = 1.2
            elif category == "methodological":
                mass = 1.0
            else:
                mass = 1.0

            vec_json = compute_vector(statement, scorer, wrap_dict=False)

            belief_repo.create_belief(
                id=str(uuid.uuid4()),
                agent_id="symbia",
                label=label,
                statement=statement,
                origin="authored",
                confidence=confidence,
                ontological_mass=mass,
                somatic_anchor="none",
                vector_16d=vec_json,
                lifecycle_stage="crystallized",
            )
            seeded_beliefs_count += 1

        logger.info(f"Successfully seeded {seeded_beliefs_count} foundational beliefs.")

    # 4. Seed Procedural Skills
    seed_skills_file = PROJECT_ROOT / "config" / "personality" / "seed_skills.yaml"
    skills_in_db = len(skill_repo.list_skills())

    if skills_in_db > 0 and not args.force:
        logger.info(f"Database already has {skills_in_db} skills. Skipping skill seeding.")
    else:
        logger.info(f"Seeding procedural skills from {seed_skills_file.name}...")
        if not seed_skills_file.exists():
            logger.error(f"Skills seed file not found: {seed_skills_file}")
            sys.exit(1)

        with open(seed_skills_file, encoding="utf-8") as f:
            skills_data = yaml.safe_load(f)

        skills_cfg = skills_data.get("skills", {})
        always_active_defs = skills_cfg.get("always_active", [])
        on_demand_defs = skills_cfg.get("on_demand", [])

        seeded_skills_count = 0

        # Process always_active
        for sd in always_active_defs:
            name = sd["id"]
            statement = sd["statement"]
            content = sd.get("content", "")

            if not content:
                content = generate_skill_content(name, statement, is_always_active=True)

            vec_json = compute_vector(statement, scorer, wrap_dict=True)

            skill_repo.create_skill(
                id=str(uuid.uuid4()),
                name=name,
                description=statement,
                content=content,
                short_content=statement,
                always_active=True,
                trigger_keywords="[]",
                lifecycle_stage="crystallized",
                confidence=0.90,
                ontological_mass=1.2,
                vector_16d=vec_json,
                source="authored",
            )

            # Create belief bridge
            belief_vec_json = compute_vector(statement, scorer, wrap_dict=False)
            try:
                existing_b = belief_repo.list_beliefs("symbia")
                if not any(b.label == f"skill:{name}" for b in existing_b):
                    belief_repo.create_belief(
                        id=str(uuid.uuid4()),
                        agent_id="symbia",
                        label=f"skill:{name}",
                        statement=statement,
                        origin="emergent",
                        confidence=0.90,
                        ontological_mass=1.2,
                        somatic_anchor="conceptual",
                        vector_16d=belief_vec_json,
                        lifecycle_stage="crystallized",
                    )
            except Exception as e:
                logger.warning(f"Failed to create belief bridge for skill {name}: {e}")

            seeded_skills_count += 1

        # Process on_demand
        for sd in on_demand_defs:
            name = sd["id"]
            description = sd.get("description", name)
            triggers = sd.get("triggers", [])
            content = sd.get("content", "")

            if not content:
                content = generate_skill_content(name, description, is_always_active=False)

            vec_json = compute_vector(content or description, scorer, wrap_dict=True)
            trigger_json = json.dumps(triggers)

            skill_repo.create_skill(
                id=str(uuid.uuid4()),
                name=name,
                description=description,
                content=content,
                short_content="",
                always_active=False,
                trigger_keywords=trigger_json,
                lifecycle_stage="crystallized",
                confidence=0.85,
                ontological_mass=1.0,
                vector_16d=vec_json,
                source="authored",
            )

            # Create belief bridge
            belief_vec_json = compute_vector(description, scorer, wrap_dict=False)
            try:
                existing_b = belief_repo.list_beliefs("symbia")
                if not any(b.label == f"skill:{name}" for b in existing_b):
                    belief_repo.create_belief(
                        id=str(uuid.uuid4()),
                        agent_id="symbia",
                        label=f"skill:{name}",
                        statement=description,
                        origin="emergent",
                        confidence=0.85,
                        ontological_mass=1.0,
                        somatic_anchor="conceptual",
                        vector_16d=belief_vec_json,
                        lifecycle_stage="crystallized",
                    )
            except Exception as e:
                logger.warning(f"Failed to create belief bridge for skill {name}: {e}")

            seeded_skills_count += 1

        logger.info(f"Successfully seeded {seeded_skills_count} skills with belief bridges.")

    # 5. Seed Dynamic Personality
    # Check if commitments exist
    commitments_exist = commitment_repo.count("symbia") > 0
    if commitments_exist and not args.force:
        logger.info("Dynamic personality (commitments/expertise) already seeded. Skipping.")
    else:
        logger.info("Seeding dynamic personality layer (commitments, expertise, traits)...")
        seed_dynamic_personality(
            commitment_repo=commitment_repo,
            expertise_repo=expertise_repo,
            personality_state_repo=personality_state_repo,
            identity_path=PROJECT_ROOT / "config" / "personality" / "seed_personality.yaml",
            agent_id="symbia",
        )
        logger.info("Dynamic personality successfully seeded.")

    logger.info(
        "\n========================================================================\n"
        "SUCCESS: AAA Agent successfully initialized and seeded!\n"
        "========================================================================\n"
        "To start development locally, you can run:\n"
        "    - Backend Server:  uv run python backend/main.py\n"
        "    - Frontend App:    npm run dev (inside the frontend directory)\n\n"
        "Optional high-fidelity LLM vector recalculation:\n"
        "    uv run python backend/scripts/recalculate_autopoietic_vectors.py\n"
        "========================================================================"
    )


if __name__ == "__main__":
    main()
