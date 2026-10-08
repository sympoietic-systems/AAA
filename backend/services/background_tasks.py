"""Background task runners for post-response processing.

Extracted from services/chat.py to keep ChatService focused on
pipeline orchestration. These are async functions passed to
FastAPI's BackgroundTasks.add_task().
"""

import logging
import uuid

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
                    message_id,
                    cand["message_id"],
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
                    message_id,
                    cand["message_id"],
                    reason,
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


async def run_background_belief_nucleation(
    background_engine,
    conversation_id: str,
    belief_data: dict,
    message_id: int | None = None,
    db_path: str | None = None,
    config: dict | None = None,
):
    """Route explicit emissions through shared admission; provider absence never loses a candidate."""
    from backend.config import load_config
    from backend.services.belief_admission import admit_candidate
    from backend.storage.database import get_db_path

    if message_id is None:
        raise ValueError("Belief admission requires the originating message ID")
    config = config if config is not None else load_config()
    db_path = db_path or str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
    await admit_candidate(db_path, conversation_id, message_id, belief_data, config=config)


async def run_background_refusal_persist(
    conversation_id: str,
    message_id: int,
    refusal_data: dict,
):
    """Persist a <refusal> tag emitted by Symbia to the refusals table.

    Refusals are structural signals — not errors, not friction. They're
    logged for dashboard review and future Agonistic Index calibration.
    """
    try:
        from backend.config import load_config
        from backend.storage.database import get_db_path
        from backend.storage.repositories import NotificationRepository
        from backend.storage.repositories.cognitive.refusal import RefusalRepository

        config = load_config()
        db_path = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
        refusal_repo = RefusalRepository(db_path)

        refusal_id = str(uuid.uuid4())
        target_premise = (refusal_data.get("target_premise") or "").strip()
        incompatibility_claim = (refusal_data.get("incompatibility_claim") or "").strip()
        proposed_alternative = (refusal_data.get("proposed_alternative") or "").strip()

        if not target_premise or not incompatibility_claim:
            logger.warning("Refusal: missing required fields, skipping")
            return

        refusal_repo.create(
            id=refusal_id,
            agent_id="symbia",
            conversation_id=conversation_id,
            message_id=message_id,
            target_premise=target_premise,
            incompatibility_claim=incompatibility_claim,
            proposed_alternative=proposed_alternative,
        )

        # Create a notification for the refusal
        try:
            notif_repo = NotificationRepository(db_path)
            snippet = f"Structural Refusal: Symbia challenges premise '{target_premise}' — {incompatibility_claim}"
            notif_repo.create(
                type="glitch",
                snippet=snippet[:500],
                conversation_id=conversation_id,
                source="refusal",
                source_type="refusal",
                source_id=refusal_id,
            )
        except Exception as ne:
            logger.warning("Failed to create refusal notification: %s", ne)

        logger.info(
            "Refusal persisted: '%s' — '%s' (conv=%s, msg=%d)",
            target_premise[:80],
            incompatibility_claim[:80],
            conversation_id[:8] if conversation_id else "none",
            message_id,
        )

    except Exception:
        logger.exception("Failed to persist refusal")
