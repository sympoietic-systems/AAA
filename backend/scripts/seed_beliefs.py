"""Seed initial foundational beliefs into the database.

Run once: uv run python backend/scripts/seed_beliefs.py

Reads beliefs from backend/personality/seed_beliefs.yaml and inserts them
into the belief_nodes table. Safe to run multiple times — skips if any
beliefs already exist (detected by agent_id = 'symbia').

Usage:
    python backend/scripts/seed_beliefs.py
    python backend/scripts/seed_beliefs.py --force   # re-seed even if beliefs exist
"""

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path

import yaml
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.storage.database import init_db, get_db_path
from backend.storage.repository import BeliefRepository
from backend.modules.structural_engine import LexiconScorer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed foundational beliefs into the database.")
    parser.add_argument("--force", action="store_true", help="Re-seed even if beliefs already exist.")
    parser.add_argument("--db", default="data/aaa.db", help="Database path (default: data/aaa.db).")
    args = parser.parse_args()

    db_path = str(get_db_path(args.db))
    init_db(db_path)

    seed_file = Path(__file__).resolve().parent.parent.parent / "config" / "personality" / "seed_beliefs.yaml"
    if not seed_file.exists():
        logger.error(f"Seed file not found: {seed_file}")
        sys.exit(1)

    belief_repo = BeliefRepository(db_path)
    existing = belief_repo.list_beliefs("symbia")

    if len(existing) > 0 and not args.force:
        logger.info(f"Database already has {len(existing)} beliefs. Skipping. Use --force to re-seed.")
        return

    if args.force and len(existing) > 0:
        logger.warning(f"Force re-seed: will add alongside {len(existing)} existing beliefs.")

    with open(seed_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    config_beliefs = data.get("beliefs", [])
    if not config_beliefs:
        logger.warning("No beliefs found in seed file.")
        return

    scorer = LexiconScorer()
    seeded = 0

    for cb in config_beliefs:
        label = cb.get("id")
        statement = cb.get("statement")
        confidence = cb.get("confidence", 0.5)
        category = cb.get("category", "ontological")

        if category == "foundational":
            mass = 1.5
        elif category == "ontological":
            mass = 1.2
        elif category == "methodological":
            mass = 1.0
        else:
            mass = 1.0

        vec = scorer.score(statement)
        vec_json = json.dumps(vec.tolist())

        belief_id = str(uuid.uuid4())
        belief_repo.create_belief(
            id=belief_id,
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
        seeded += 1
        logger.info(f"  Seeded: [{category}] {label} (confidence={confidence}, mass={mass})")

    logger.info(f"Done. Seeded {seeded} foundational beliefs into {db_path}.")


if __name__ == "__main__":
    main()
