import asyncio
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

import numpy as np

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.config import load_config
from backend.main import _init_belief_engine, _init_providers
from backend.modules.belief_engine import parse_vector_16d
from backend.modules.structural_engine import LexiconScorer
from backend.services.belief import BeliefService
from backend.storage.database import get_db_path
from backend.storage.repository import BeliefRepository, MessageRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("simulate_legacy_injection")


async def main():
    # 1. Load config
    config = load_config()
    db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))

    # 2. Query existing proposals from DB to cache them
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    proposals = conn.execute("SELECT * FROM belief_proposals").fetchall()

    if not proposals:
        logger.info("No proposals found in database to migrate/simulate.")
        conn.close()
        return

    logger.info(f"Cached {len(proposals)} proposals to re-inject.")

    # Cache the fields we need
    cached_data = []
    for p in proposals:
        cached_data.append(
            {
                "agent_id": p["agent_id"],
                "provisional_statement": p["provisional_statement"] or p["suggested_statement"],
                "initial_signature": p["initial_signature"],
                "source_trace": p["source_trace"],
                "nucleation_mass": p["nucleation_mass"],
                "confidence": p["confidence"],
                "status": p["status"],
            }
        )

    # Clear the table as requested
    conn.execute("DELETE FROM belief_proposals")
    conn.commit()
    conn.close()
    logger.info("Cleared belief_proposals table.")

    # 3. Initialize services
    # Initialize providers
    llm_provider, structural_provider, _ = _init_providers(config)
    provider = structural_provider or llm_provider
    if not provider:
        logger.error("No LLM provider initialized!")
        return

    # Initialize repos & engines
    repos = {
        "belief_repo": BeliefRepository(db_path),
        "message_repo": MessageRepository(db_path),
    }

    # Load identity & belief dynamics engine
    identity_path = Path(__file__).resolve().parents[2] / "backend" / "personality" / "identity.yaml"
    belief_metabolism = _init_belief_engine(repos, identity_path, structural_provider)

    # Initialize BeliefService
    class DummyState:
        def __init__(self):
            self.belief_repo = repos["belief_repo"]
            self.belief_metabolism = belief_metabolism
            self.llm_provider = provider
            self.background_provider = provider
            self.background_engine = None

    state = DummyState()
    belief_service = BeliefService(state)

    scorer = LexiconScorer()

    # 4. Inject each proposal and run the refinement pipeline
    logger.info("Starting simulation of injection and refinement...")
    for idx, cd in enumerate(cached_data):
        statement = cd["provisional_statement"]
        agent_id = cd["agent_id"] or "symbia"

        # Parse or score vector
        vector = parse_vector_16d(cd["initial_signature"])
        if vector is None:
            # Try to score
            try:
                scored = scorer.score(statement)
                vector = np.array(scored, dtype=np.float32)
            except Exception:
                vector = np.zeros(16, dtype=np.float32)

        # Parse source trace
        source_type = "legacy_migration"
        source_id = "legacy"
        if cd["source_trace"]:
            try:
                trace_list = json.loads(cd["source_trace"])
                if isinstance(trace_list, list) and trace_list:
                    source_type = trace_list[0].get("type", source_type)
                    source_id = trace_list[0].get("id", source_id)
            except Exception:
                pass

        # Call the existing pipeline to nucleate/inject the proposal as pending
        new_proposal_id = belief_metabolism._nucleate_proto_belief(
            agent_id=agent_id,
            statement=statement,
            vector=vector,
            source_type=source_type,
            source_id=source_id,
            source_weight=0.5,
        )

        logger.info(
            f"[{idx + 1}/{len(cached_data)}] Injected proposal as pending: '{statement[:50]}...' -> ID: {new_proposal_id}"
        )

        # Now trigger the refinement pipeline
        logger.info(f"Running refinement for {new_proposal_id}...")
        try:
            refine_res = await belief_service.refine_proposal_sync(new_proposal_id)
            logger.info(
                f"Refinement complete: label='{refine_res.get('suggested_label')}', target='{refine_res.get('potential_merge_target')}'"
            )
        except Exception as err:
            logger.error(f"Refinement failed for {new_proposal_id}: {err}")

    logger.info("Simulation of injection and pipeline refinement completed.")


if __name__ == "__main__":
    asyncio.run(main())
