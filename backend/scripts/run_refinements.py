import asyncio
import logging
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.config import load_config
from backend.main import _init_providers
from backend.modules.background_tasks.actions.refine_belief import RefineBeliefAction
from backend.storage.database import get_db_path
from backend.storage.repository import BeliefRepository

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run_refinements")


async def main():
    # 1. Load config
    config = load_config()

    # 2. Initialize LLM Provider
    llm_provider, structural_provider, _ = _init_providers(config)
    provider = structural_provider or llm_provider
    if not provider:
        logger.error("No LLM provider initialized!")
        return

    # 3. Retrieve database and repository
    db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
    belief_repo = BeliefRepository(db_path)

    # 4. Fetch pending proposals
    conn = belief_repo._conn_factory()
    rows = conn.execute("SELECT id, provisional_statement FROM belief_proposals WHERE status = 'pending'").fetchall()
    conn.close()

    if not rows:
        logger.info("No pending proposals to refine.")
        return

    logger.info(f"Found {len(rows)} pending proposals to refine.")

    action = RefineBeliefAction()

    for r in rows:
        proposal_id = r[0]
        statement = r[1]
        logger.info(f"Refining proposal {proposal_id}: '{statement[:60]}...'")
        try:
            res = await action.execute(provider, {"proposal_id": proposal_id})
            logger.info(f"Refinement result: {res}")
        except Exception as e:
            logger.error(f"Failed to refine proposal {proposal_id}: {e}", exc_info=True)

    logger.info("All refinements completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
