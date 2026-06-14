"""
One-time seeding script for dynamic personality cascade.

Run this once after the m025 migration to populate:
  - commitment_nodes (7 theoretical commitments from identity.yaml)
  - expertise_nodes (8 domain expertise entries)
  - personality_state (aspirational trait attractors)

Usage:
    python -m backend.scripts.seed_dynamic_personality

Or with explicit config path:
    python backend/scripts/seed_dynamic_personality.py --config backend/config.yaml
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import load_config
from backend.personality.seeding import seed_dynamic_personality
from backend.storage.database import get_db_path, init_db
from backend.storage.repository import (
    CommitmentRepository,
    ExpertiseRepository,
    PersonalityStateRepository,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Seed dynamic personality tables from identity.yaml"
    )
    parser.add_argument(
        "--config", default="backend/config.yaml",
        help="Path to config.yaml"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-seed even if data already exists (clears existing)"
    )
    args = parser.parse_args()

    config = load_config()
    db_path = config.get("database", {}).get("path", "data/aaa.db")
    full_db_path = get_db_path(db_path)

    # Initialize DB (run migrations)
    init_conn = init_db(str(full_db_path))
    init_conn.close()

    path = str(full_db_path)
    commitment_repo = CommitmentRepository(path)
    expertise_repo = ExpertiseRepository(path)
    personality_state_repo = PersonalityStateRepository(path)

    # Handle --force
    if args.force:
        import sqlite3
        conn = sqlite3.connect(path)
        conn.execute("DELETE FROM commitment_events")
        conn.execute("DELETE FROM commitment_nodes")
        conn.execute("DELETE FROM expertise_nodes")
        conn.execute("DELETE FROM personality_state")
        conn.commit()
        conn.close()
        logger.info("Cleared existing dynamic personality data (--force)")

    # Find identity.yaml
    personality_cfg = config.get("personality", {})
    identity_path = Path(personality_cfg.get("path", "backend/personality/identity.yaml"))
    if not identity_path.is_absolute():
        identity_path = Path(__file__).resolve().parent.parent.parent / identity_path

    agent_id = config.get("agent", {}).get("name", "symbia")
    if isinstance(agent_id, dict):
        agent_id = agent_id.get("name", "symbia")

    logger.info("Seeding dynamic personality from: %s", identity_path)
    seed_dynamic_personality(
        commitment_repo=commitment_repo,
        expertise_repo=expertise_repo,
        personality_state_repo=personality_state_repo,
        identity_path=identity_path,
        agent_id=agent_id,
    )

    logger.info("Seeding complete.")


if __name__ == "__main__":
    main()
