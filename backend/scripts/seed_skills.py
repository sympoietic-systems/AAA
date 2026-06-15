"""Seed initial procedural skills into the database.

Run once: uv run python backend/scripts/seed_skills.py

Reads skills from backend/personality/seed_skills.yaml and inserts them
into the skill_nodes table. Safe to run multiple times — skips if any
skills already exist by default.

Usage:
    python backend/scripts/seed_skills.py
    python backend/scripts/seed_skills.py --force   # re-seed/overwrite existing skills
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import SkillRepository, BeliefRepository
from backend.modules.structural_engine import LexiconScorer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def generate_skill_content(name: str, description: str, is_always_active: bool) -> str:
    sections = [f"# {name}\n\n{description}\n"]
    if is_always_active:
        sections.append("\n## Baseline Disposition\n\n")
        sections.append(f"This skill is a baseline disposition — part of Symbia's core personality, not a tool to activate.\n")
        sections.append(f"It is always present in the system prompt and guides every interaction.\n")
        sections.append(f"\n## Application\n\n")
        sections.append(f"Apply this disposition continuously. It requires no explicit invocation.\n")
    else:
        sections.append(f"\n## When to Use\n\n")
        sections.append(f"This skill is loaded when the conversation context matches its trigger patterns.\n")
        sections.append(f"\n## Application\n\n")
        sections.append(f"Follow the instructions below when this skill is active.\n")
    return "".join(sections)


def compute_skill_vector(text: str, scorer: LexiconScorer) -> str:
    result = {"v16d": [], "v384d": []}
    try:
        v16d = scorer.score(text)
        result["v16d"] = v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)
    except Exception as e:
        logger.warning("Failed to compute 16D structural vector: %s", e)
        result["v16d"] = [0.0] * 16
    return json.dumps(result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed foundational skills into the database.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing skills with seed defaults.")
    parser.add_argument("--db", default="data/aaa.db", help="Database path (default: data/aaa.db).")
    args = parser.parse_args()

    db_path = str(get_db_path(args.db))
    init_db(db_path)

    seed_file = Path(__file__).resolve().parent.parent.parent / "config" / "personality" / "seed_skills.yaml"
    if not seed_file.exists():
        logger.error(f"Seed file not found: {seed_file}")
        sys.exit(1)

    skill_repo = SkillRepository(db_path)
    belief_repo = BeliefRepository(db_path)

    with open(seed_file, "r", encoding="utf-8") as f:
        seed_data = yaml.safe_load(f)

    skills_cfg = seed_data.get("skills", {})
    if not skills_cfg:
        logger.warning("No skills found in seed file.")
        return

    always_active_defs = skills_cfg.get("always_active", [])
    on_demand_defs = skills_cfg.get("on_demand", [])

    scorer = LexiconScorer()
    
    # Process always_active skills
    for skill_def in always_active_defs:
        name = skill_def["id"]
        statement = skill_def["statement"]
        
        existing = skill_repo.get_skill_by_name(name)
        if existing:
            if not args.force:
                logger.info(f"Skill '{name}' already exists. Skipping. Use --force to overwrite.")
                continue
            else:
                logger.info(f"Overwriting existing skill '{name}'...")
                skill_repo.delete_skill(existing.id)
        
        skill_id = str(uuid.uuid4())
        content = generate_skill_content(name, statement, is_always_active=True)
        vec_json = compute_skill_vector(statement, scorer)
        
        skill_repo.create_skill(
            id=skill_id,
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
        try:
            existing_beliefs = belief_repo.list_beliefs("symbia")
            bridge_exists = any(b.label == f"skill:{name}" for b in existing_beliefs)
            if not bridge_exists:
                belief_repo.create_belief(
                    id=str(uuid.uuid4()),
                    agent_id="symbia",
                    label=f"skill:{name}",
                    statement=statement,
                    origin="emergent",
                    confidence=0.90,
                    ontological_mass=1.2,
                    somatic_anchor="conceptual",
                    vector_16d=vec_json,
                    lifecycle_stage="crystallized",
                )
        except Exception as e:
            logger.warning("Failed to create belief bridge for skill %s: %s", name, e)
        
        logger.info(f"  Seeded always-active: {name}")

    # Process on_demand skills
    for skill_def in on_demand_defs:
        name = skill_def["id"]
        description = skill_def.get("description", name)
        triggers = skill_def.get("triggers", [])
        content = skill_def.get("content", "")
        
        existing = skill_repo.get_skill_by_name(name)
        if existing:
            if not args.force:
                logger.info(f"Skill '{name}' already exists. Skipping. Use --force to overwrite.")
                continue
            else:
                logger.info(f"Overwriting existing skill '{name}'...")
                skill_repo.delete_skill(existing.id)
        
        skill_id = str(uuid.uuid4())
        if not content:
            content = generate_skill_content(name, description, is_always_active=False)
        vec_json = compute_skill_vector(content or description, scorer)
        trigger_json = json.dumps(triggers)

        skill_repo.create_skill(
            id=skill_id,
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
        try:
            existing_beliefs = belief_repo.list_beliefs("symbia")
            bridge_exists = any(b.label == f"skill:{name}" for b in existing_beliefs)
            if not bridge_exists:
                belief_repo.create_belief(
                    id=str(uuid.uuid4()),
                    agent_id="symbia",
                    label=f"skill:{name}",
                    statement=description,
                    origin="emergent",
                    confidence=0.85,
                    ontological_mass=1.0,
                    somatic_anchor="conceptual",
                    vector_16d=vec_json,
                    lifecycle_stage="crystallized",
                )
        except Exception as e:
            logger.warning("Failed to create belief bridge for skill %s: %s", name, e)
            
        logger.info(f"  Seeded on-demand: {name}")

    logger.info(f"Done seeding skills into {db_path}.")


if __name__ == "__main__":
    main()
