"""Background task runners for post-response processing.

Extracted from services/chat.py to keep ChatService focused on
pipeline orchestration. These are async functions passed to
FastAPI's BackgroundTasks.add_task().
"""

import logging

logger = logging.getLogger(__name__)


async def run_background_resonance_scan(
    background_engine,
    message_repo,
    conversation_id: str,
    message_id: int,
):
    """Scan for cross-branch resonance links after each agent response."""
    try:
        path_msgs = message_repo.get_ancestor_path(message_id)
        ancestor_ids = [m.id for m in path_msgs]

        current_msg = None
        for m in path_msgs:
            if m.id == message_id:
                current_msg = m
                break
        if not current_msg:
            msgs = message_repo.get_by_ids([message_id])
            if msgs:
                current_msg = msgs[0]

        if not current_msg or not current_msg.embedding:
            return

        candidates = message_repo.get_parallel_messages_by_similarity(
            conversation_id=conversation_id,
            message_id=message_id,
            ancestor_ids=ancestor_ids,
            threshold=0.82,
            limit=5,
        )

        for cand in candidates:
            if message_repo.link_exists(message_id, cand["message_id"]):
                logger.info(
                    "Resonance link already exists or was ignored between %d and %d, skipping comparison",
                    message_id, cand["message_id"],
                )
                continue

            payload = {
                "message_a": current_msg.content,
                "speaker_a": current_msg.speaker,
                "message_b": cand["content"],
                "speaker_b": cand["speaker"],
            }
            res = await background_engine.run("resonance_finder", payload)
            if res.get("has_resonance"):
                reason = res.get("reason", "")
                message_repo.add_message_link(
                    source_id=message_id,
                    target_id=cand["message_id"],
                    link_type="resonance",
                    status="proposed",
                    justification=reason,
                )
                logger.info(
                    "Background resonance link proposed: %d -> %d (reason: %s)",
                    message_id, cand["message_id"], reason,
                )
    except Exception:
        logger.exception("Error during background resonance scan")


async def run_background_skill_refinement(
    background_engine,
    conversation_id: str,
    skill_data: dict,
):
    """Run skill refinement daemon for a proposed skill."""
    try:
        logger.info("Running background skill refinement daemon for proposed skill: %s", skill_data.get("name"))
        res = await background_engine.run(
            "refine_skill",
            {
                "skill_data": skill_data,
                "conversation_id": conversation_id,
            },
        )
        if res.get("error"):
            logger.error("Skill refinement daemon failed: %s", res["error"])
        else:
            decision = res.get("decision")
            reason = res.get("reason")
            logger.info("Skill refinement daemon finished. Decision: %s. Reason: %s", decision, reason)
    except Exception:
        logger.exception("Failed to run background skill refinement")
