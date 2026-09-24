"""Typed ownership for application-scoped runtime dependencies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, fields
from dataclasses import field as dataclass_field
from typing import TYPE_CHECKING, Any

from starlette.datastructures import State

from backend.services.keyed_lock import KeyedLockRegistry

if TYPE_CHECKING:
    from backend.metabolisation.daemon import AutopoieticDreamDaemon
    from backend.metabolisation.scheduler import BackgroundStartupScheduler
    from backend.modules.background_tasks.engine import BackgroundTaskEngine
    from backend.modules.belief_engine import BeliefDynamicsEngine
    from backend.modules.conversation_metrics import ConversationMetricsModule
    from backend.modules.embedder import EmbedderModule
    from backend.modules.llm_client import BaseLLMProvider
    from backend.modules.sensory.perception import PerceptionModule
    from backend.modules.structural_engine import StructuralScorerModule
    from backend.pipeline.engine import ProcessingPipeline
    from backend.pipeline.registry import PipelineRegistry
    from backend.services.research.task_manager import ResearchTaskManager
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
        ResearchBranchRepository,
        ResearchMetaLogRepository,
        ResearchPlanRepository,
        ResearchStepRepository,
        ResearchStepResultRepository,
        ResearchTaskRepository,
        ScrapedAssetRepository,
        SemanticKnotRepository,
        SkillRepository,
    )


@dataclass
class AppServices:
    """Single owner for dependencies assembled during the FastAPI lifespan."""

    config: dict[str, Any]
    agent_name: str
    message_repo: MessageRepository
    error_repo: ErrorLogRepository
    metrics_repo: MetricsRepository
    conversation_repo: ConversationRepository
    perception_repo: PerceptionSedimentRepository
    checkpoint_repo: ConsolidationCheckpointRepository
    memory_node_repo: MemoryNodeRepository
    belief_repo: BeliefRepository
    semantic_knot_repo: SemanticKnotRepository
    note_repo: NoteRepository
    skill_repo: SkillRepository
    notification_repo: NotificationRepository
    commitment_repo: CommitmentRepository
    expertise_repo: ExpertiseRepository
    personality_state_repo: PersonalityStateRepository
    dream_log_repo: DreamLogRepository
    daily_summary_repo: DailySummaryRepository
    research_task_repo: ResearchTaskRepository
    research_branch_repo: ResearchBranchRepository
    scraped_asset_repo: ScrapedAssetRepository
    research_meta_log_repo: ResearchMetaLogRepository
    research_plan_repo: ResearchPlanRepository
    research_step_repo: ResearchStepRepository
    research_step_result_repo: ResearchStepResultRepository
    belief_metabolism: BeliefDynamicsEngine
    registry: PipelineRegistry
    pipeline: ProcessingPipeline
    pipeline_order: list[str]
    embedder: EmbedderModule
    llm_provider: BaseLLMProvider
    structural_provider: BaseLLMProvider
    structural_scorer: StructuralScorerModule
    metrics_module: ConversationMetricsModule
    perception_module: PerceptionModule
    system_prompt_tokens: int
    background_engine: BackgroundTaskEngine
    background_provider: BaseLLMProvider | None
    vision_provider: BaseLLMProvider | None
    conversation_locks: KeyedLockRegistry = dataclass_field(default_factory=KeyedLockRegistry)
    research_task_manager: ResearchTaskManager | None = None
    startup_scheduler: BackgroundStartupScheduler | None = None
    dream_daemon: AutopoieticDreamDaemon | None = None
    db_backup_task: asyncio.Task[None] | None = None
    latest_diffractive_meta: dict[str, object] | None = None


def bind_legacy_state_aliases(state: State, services: AppServices) -> None:
    """Publish temporary object-identical aliases for unmigrated callers."""

    state.services = services
    for field in fields(services):
        setattr(state, field.name, getattr(services, field.name))
