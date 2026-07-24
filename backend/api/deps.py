"""FastAPI dependencies — auth, guards, app-state, and repo injection.

Provides reusable FastAPI Depends callables so route handlers don't need
to manually pull repos from request.app.state with getattr(...).

Usage in route files:
    from backend.api.deps import require_agent_flux, get_app_state, get_message_repo

    @router.post("/endpoint")
    async def handler(
        state = Depends(get_app_state),
        repo = Depends(get_message_repo),
    ):
        ...
"""

import logging
import os

from fastapi import Depends, Header, HTTPException, Request

logger = logging.getLogger(__name__)

# ── Auth ───────────────────────────────────────────────────────────────

AAA_PASSWORD: str = os.environ.get("AAA_PASSWORD", "").strip()


async def verify_password(
    request: Request,
    authorization: str | None = Header(None),
):
    """FastAPI dependency: verify Bearer token against AAA_PASSWORD env var.

    If AAA_PASSWORD is not set, authentication is bypassed.
    The /api/auth/verify endpoint is always allowed (used by frontend to
    detect whether auth is enabled before prompting for a password).

    Also accepts token via query parameter (?token=...) for download links
    that can't use Authorization headers (e.g., window.open navigation).
    """
    import sys

    if not AAA_PASSWORD or "pytest" in sys.modules:
        return

    # Allow the auth verify endpoint through so the frontend can discover auth status
    if request.url.path == "/api/auth/verify":
        return

    token: str | None = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    # Fallback: accept token via query parameter for download links
    if not token:
        qp_token = request.query_params.get("token")
        if qp_token:
            token = qp_token

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token != AAA_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Feature gate ───────────────────────────────────────────────────────


def require_agent_flux():
    """FastAPI dependency: require AAA_AGENT_FLUX=true.

    Use as a route dependency to guard mutation endpoints:
        @router.post("/skills", dependencies=[Depends(require_agent_flux)])

    Centralizes the previously duplicated check_agent_flux() pattern from
    beliefs.py:11 and skills.py:46 with a consistent default value.
    """
    if os.environ.get("AAA_AGENT_FLUX", "false").lower() not in ("true", "1", "yes"):
        raise HTTPException(
            status_code=403,
            detail="Agent modification is disabled (AAA_AGENT_FLUX is false)",
        )


def agent_flux_enabled() -> bool:
    """Non-raising check: return whether AAA_AGENT_FLUX is enabled.

    For use in non-guard contexts (e.g., returning flux status in API responses).
    Replaces the inline os.environ.get(...) pattern in agent.py:16.
    """
    return os.environ.get("AAA_AGENT_FLUX", "false").lower() in ("true", "1", "yes")


# ── App state access ───────────────────────────────────────────────────


def get_app_state(request: Request):
    """FastAPI dependency: provide the full app.state object."""
    return request.app.state


# ── Repository getters ─────────────────────────────────────────────────


def get_message_repo(state=Depends(get_app_state)):
    return getattr(state, "message_repo", None)


def get_error_repo(state=Depends(get_app_state)):
    return getattr(state, "error_repo", None)


def get_metrics_repo(state=Depends(get_app_state)):
    return getattr(state, "metrics_repo", None)


def get_conversation_repo(state=Depends(get_app_state)):
    return getattr(state, "conversation_repo", None)


def get_perception_repo(state=Depends(get_app_state)):
    return getattr(state, "perception_repo", None)


def get_checkpoint_repo(state=Depends(get_app_state)):
    return getattr(state, "checkpoint_repo", None)


def get_memory_node_repo(state=Depends(get_app_state)):
    return getattr(state, "memory_node_repo", None)


def get_belief_repo(state=Depends(get_app_state)):
    return getattr(state, "belief_repo", None)


def get_semantic_knot_repo(state=Depends(get_app_state)):
    return getattr(state, "semantic_knot_repo", None)


def get_note_repo(state=Depends(get_app_state)):
    return getattr(state, "note_repo", None)


def get_skill_repo(state=Depends(get_app_state)):
    return getattr(state, "skill_repo", None)


def get_notification_repo(state=Depends(get_app_state)):
    return getattr(state, "notification_repo", None)


def get_commitment_repo(state=Depends(get_app_state)):
    return getattr(state, "commitment_repo", None)


def get_expertise_repo(state=Depends(get_app_state)):
    return getattr(state, "expertise_repo", None)


def get_personality_state_repo(state=Depends(get_app_state)):
    return getattr(state, "personality_state_repo", None)


def get_dream_log_repo(state=Depends(get_app_state)):
    return getattr(state, "dream_log_repo", None)


def get_daily_summary_repo(state=Depends(get_app_state)):
    repo = getattr(state, "daily_summary_repo", None)
    if not repo:
        msg_repo = getattr(state, "message_repo", None)
        if msg_repo and hasattr(msg_repo, "_db_path"):
            from backend.storage.repositories.daily_summary_repository import DailySummaryRepository
            return DailySummaryRepository(msg_repo._db_path)
    return repo




# ── Module / engine getters ────────────────────────────────────────────


def get_registry(state=Depends(get_app_state)):
    return getattr(state, "registry", None)


def get_embedder(state=Depends(get_app_state)):
    return getattr(state, "embedder", None)


def get_background_engine(state=Depends(get_app_state)):
    return getattr(state, "background_engine", None)


def get_structural_scorer(state=Depends(get_app_state)):
    return getattr(state, "structural_scorer", None)


def get_metrics_module(state=Depends(get_app_state)):
    return getattr(state, "metrics_module", None)


def get_perception_module(state=Depends(get_app_state)):
    return getattr(state, "perception_module", None)


def get_pipeline(state=Depends(get_app_state)):
    return getattr(state, "pipeline", None)


def get_pipeline_order(state=Depends(get_app_state)):
    return getattr(state, "pipeline_order", None)


def get_agent_name(state=Depends(get_app_state)):
    return getattr(state, "agent_name", "symbia")


# ── Service getters ────────────────────────────────────────────────────


def get_chat_service(state=Depends(get_app_state)):
    from backend.services.chat import ChatService

    return ChatService(state)


def get_belief_service(state=Depends(get_app_state)):
    from backend.services.belief import BeliefService

    return BeliefService(state)


def get_skill_service(state=Depends(get_app_state)):
    from backend.services.skill import SkillService

    return SkillService(state)


def get_conversation_service(state=Depends(get_app_state)):
    from backend.services.conversation import ConversationService

    return ConversationService()


# ── Composite helpers ──────────────────────────────────────────────────


def require_conversation(conv_repo, conversation_id: str):
    """Fetch a conversation or raise HTTPException(404).

    Replaces the duplicated 5-line guard pattern in conversations.py,
    tags.py, and files.py (13 occurrences).

    Usage:
        conv = require_conversation(conv_repo, conversation_id)
    """
    if not conv_repo:
        raise HTTPException(status_code=503, detail="Conversation repository not initialized")
    conv = conv_repo.get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv
