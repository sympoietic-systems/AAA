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

from __future__ import annotations

import logging
import os
from dataclasses import fields
from typing import TYPE_CHECKING, cast

from fastapi import Depends, Header, HTTPException, Request
from starlette.datastructures import State

from backend.bootstrap.services import AppServices
from backend.core.auth import auth_enabled, bearer_token, credentials_valid

if TYPE_CHECKING:
    from backend.modules.background_tasks.engine import BackgroundTaskEngine
    from backend.modules.conversation_metrics import ConversationMetricsModule
    from backend.modules.embedder import EmbedderModule
    from backend.modules.sensory.perception import PerceptionModule
    from backend.modules.structural_engine import StructuralScorerModule
    from backend.pipeline.engine import ProcessingPipeline
    from backend.pipeline.registry import PipelineRegistry
    from backend.services.belief import BeliefService
    from backend.services.chat import ChatService
    from backend.services.conversation import ConversationService, ConversationUseCases
    from backend.services.history import HistoryService
    from backend.services.note import NoteUseCases
    from backend.services.skill import SkillService
    from backend.storage.models import Conversation
    from backend.storage.repositories import (
        BeliefRepository,
        CommitmentRepository,
        ConsolidationCheckpointRepository,
        ConversationRepository,
        DailySummaryRepository,
        DreamLogRepository,
        ErrorLogRepository,
        ExpertiseRepository,
        MemoryNodeRepository,
        MessageRepository,
        MetricsRepository,
        NoteRepository,
        NotificationRepository,
        PerceptionSedimentRepository,
        PersonalityStateRepository,
        SemanticKnotRepository,
        SkillRepository,
    )

logger = logging.getLogger(__name__)

# ── Auth ───────────────────────────────────────────────────────────────


async def verify_password(
    request: Request,
    authorization: str | None = Header(None),
) -> None:
    """FastAPI dependency: verify Bearer token against AAA_PASSWORD env var.

    If AAA_PASSWORD is not set, authentication is bypassed.
    The /api/auth/verify endpoint is always allowed (used by frontend to
    detect whether auth is enabled before prompting for a password).

    Credentials are accepted only through the Authorization header.
    """
    if not auth_enabled():
        return

    # Allow the auth verify endpoint through so the frontend can discover auth status
    if request.url.path == "/api/auth/verify":
        return

    token = bearer_token(authorization)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not credentials_valid(token):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Feature gate ───────────────────────────────────────────────────────


def require_agent_flux() -> None:
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


def get_app_state(request: Request) -> State:
    """FastAPI dependency: provide the full app.state object."""
    return request.app.state


def get_app_services(state: State = Depends(get_app_state)) -> AppServices:
    """Return the typed application container or a structured startup failure."""
    services = getattr(state, "services", None)
    if not isinstance(services, AppServices):
        raise HTTPException(status_code=503, detail="Application services are not initialized")
    return services


def _require_dependency(state: State, name: str) -> object:
    services = getattr(state, "services", None)
    container_value = getattr(services, name, None) if services is not None else None
    legacy_value = getattr(state, name, None)
    value = legacy_value if legacy_value is not None and legacy_value is not container_value else container_value
    if value is None:
        label = name.replace("_", " ").capitalize()
        raise HTTPException(status_code=503, detail=f"{label} is not initialized")
    return value


# ── Repository getters ─────────────────────────────────────────────────


def get_message_repo(state: State = Depends(get_app_state)) -> MessageRepository:
    return cast("MessageRepository", _require_dependency(state, "message_repo"))


def get_error_repo(state: State = Depends(get_app_state)) -> ErrorLogRepository:
    return cast("ErrorLogRepository", _require_dependency(state, "error_repo"))


def get_metrics_repo(state: State = Depends(get_app_state)) -> MetricsRepository:
    return cast("MetricsRepository", _require_dependency(state, "metrics_repo"))


def get_conversation_repo(state: State = Depends(get_app_state)) -> ConversationRepository:
    return cast("ConversationRepository", _require_dependency(state, "conversation_repo"))


def get_perception_repo(state: State = Depends(get_app_state)) -> PerceptionSedimentRepository:
    return cast("PerceptionSedimentRepository", _require_dependency(state, "perception_repo"))


def get_checkpoint_repo(state: State = Depends(get_app_state)) -> ConsolidationCheckpointRepository:
    return cast("ConsolidationCheckpointRepository", _require_dependency(state, "checkpoint_repo"))


def get_memory_node_repo(state: State = Depends(get_app_state)) -> MemoryNodeRepository:
    return cast("MemoryNodeRepository", _require_dependency(state, "memory_node_repo"))


def get_belief_repo(state: State = Depends(get_app_state)) -> BeliefRepository:
    return cast("BeliefRepository", _require_dependency(state, "belief_repo"))


def get_semantic_knot_repo(state: State = Depends(get_app_state)) -> SemanticKnotRepository:
    return cast("SemanticKnotRepository", _require_dependency(state, "semantic_knot_repo"))


def get_note_repo(state: State = Depends(get_app_state)) -> NoteRepository:
    return cast("NoteRepository", _require_dependency(state, "note_repo"))


def get_skill_repo(state: State = Depends(get_app_state)) -> SkillRepository:
    return cast("SkillRepository", _require_dependency(state, "skill_repo"))


def get_notification_repo(state: State = Depends(get_app_state)) -> NotificationRepository:
    return cast("NotificationRepository", _require_dependency(state, "notification_repo"))


def get_commitment_repo(state: State = Depends(get_app_state)) -> CommitmentRepository:
    return cast("CommitmentRepository", _require_dependency(state, "commitment_repo"))


def get_expertise_repo(state: State = Depends(get_app_state)) -> ExpertiseRepository:
    return cast("ExpertiseRepository", _require_dependency(state, "expertise_repo"))


def get_personality_state_repo(state: State = Depends(get_app_state)) -> PersonalityStateRepository:
    return cast("PersonalityStateRepository", _require_dependency(state, "personality_state_repo"))


def get_dream_log_repo(state: State = Depends(get_app_state)) -> DreamLogRepository:
    return cast("DreamLogRepository", _require_dependency(state, "dream_log_repo"))


def get_daily_summary_repo(state: State = Depends(get_app_state)) -> DailySummaryRepository:
    return cast("DailySummaryRepository", _require_dependency(state, "daily_summary_repo"))


# ── Module / engine getters ────────────────────────────────────────────


def get_registry(state: State = Depends(get_app_state)) -> PipelineRegistry:
    return cast("PipelineRegistry", _require_dependency(state, "registry"))


def get_embedder(state: State = Depends(get_app_state)) -> EmbedderModule:
    return cast("EmbedderModule", _require_dependency(state, "embedder"))


def get_background_engine(state: State = Depends(get_app_state)) -> BackgroundTaskEngine:
    return cast("BackgroundTaskEngine", _require_dependency(state, "background_engine"))


def get_structural_scorer(state: State = Depends(get_app_state)) -> StructuralScorerModule:
    return cast("StructuralScorerModule", _require_dependency(state, "structural_scorer"))


def get_metrics_module(state: State = Depends(get_app_state)) -> ConversationMetricsModule:
    return cast("ConversationMetricsModule", _require_dependency(state, "metrics_module"))


def get_perception_module(state: State = Depends(get_app_state)) -> PerceptionModule:
    return cast("PerceptionModule", _require_dependency(state, "perception_module"))


def get_pipeline(state: State = Depends(get_app_state)) -> ProcessingPipeline:
    return cast("ProcessingPipeline", _require_dependency(state, "pipeline"))


def get_pipeline_order(state: State = Depends(get_app_state)) -> list[str]:
    return cast("list[str]", _require_dependency(state, "pipeline_order"))


def get_agent_name(state: State = Depends(get_app_state)) -> str:
    services = getattr(state, "services", None)
    value = getattr(services, "agent_name", None) if services is not None else None
    return cast("str", value or getattr(state, "agent_name", "symbia"))


# ── Service getters ────────────────────────────────────────────────────


def _service_context(state: State) -> AppServices | State:
    services = getattr(state, "services", None)
    if not isinstance(services, AppServices):
        return state
    for field in fields(services):
        legacy_value = getattr(state, field.name, None)
        if legacy_value is not None and legacy_value is not getattr(services, field.name):
            return state
    return services


def get_chat_service(state: State = Depends(get_app_state)) -> ChatService:
    from backend.services.chat import ChatService

    return ChatService(_service_context(state))


def get_belief_service(state: State = Depends(get_app_state)) -> BeliefService:
    from backend.services.belief import BeliefService

    return BeliefService(_service_context(state))


def get_skill_service(state: State = Depends(get_app_state)) -> SkillService:
    from backend.services.skill import SkillService

    return SkillService(_service_context(state))


def get_conversation_service() -> ConversationService:
    from backend.services.conversation import ConversationService

    return ConversationService()


def get_conversation_use_cases(state: State = Depends(get_app_state)) -> ConversationUseCases:
    from backend.services.conversation import ConversationUseCases

    context = _service_context(state)
    conversation_repo = cast("ConversationRepository", _require_dependency(state, "conversation_repo"))
    message_repo = cast("MessageRepository", _require_dependency(state, "message_repo"))
    return ConversationUseCases(
        conversation_repo,
        message_repo,
        checkpoint_repo=getattr(context, "checkpoint_repo", None),
        note_repo=getattr(context, "note_repo", None),
        memory_node_repo=getattr(context, "memory_node_repo", None),
    )


def get_history_service(message_repo: MessageRepository = Depends(get_message_repo)) -> HistoryService:
    from backend.services.history import HistoryService

    return HistoryService(message_repo)


def get_note_use_cases(note_repo: NoteRepository = Depends(get_note_repo)) -> NoteUseCases:
    from backend.services.note import NoteUseCases

    return NoteUseCases(note_repo)


# ── Composite helpers ──────────────────────────────────────────────────


def require_conversation(conv_repo: ConversationRepository, conversation_id: str) -> Conversation:
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
