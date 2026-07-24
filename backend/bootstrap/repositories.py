"""Repository initialization.

Extracted from backend/main.py.
Creates and wires all database repository instances.
"""

import logging

logger = logging.getLogger(__name__)


def _init_repos(config: dict) -> dict:
    """Initialize database and return a dict of all repository instances."""
    db_path = config.get("database", {}).get("path", "data/aaa.db")

    from backend.storage.database import get_db_path, init_db

    full_db_path = get_db_path(db_path)
    init_conn = init_db(str(full_db_path))
    init_conn.close()
    logger.info("Database initialized at %s", full_db_path)

    path = str(full_db_path)

    # Lazy imports so repository modules are only loaded when needed
    from backend.storage.repository import (
        BeliefRepository,
        CommitmentRepository,
        ConsolidationCheckpointRepository,
        ConversationRepository,
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
    from backend.storage.repositories.daily_summary_repository import DailySummaryRepository

    return {
        "message_repo": MessageRepository(path),
        "error_repo": ErrorLogRepository(path),
        "metrics_repo": MetricsRepository(path),
        "conversation_repo": ConversationRepository(path),
        "perception_repo": PerceptionSedimentRepository(path),
        "checkpoint_repo": ConsolidationCheckpointRepository(path),
        "memory_node_repo": MemoryNodeRepository(path),
        "belief_repo": BeliefRepository(path),
        "semantic_knot_repo": SemanticKnotRepository(path),
        "note_repo": NoteRepository(path),
        "skill_repo": SkillRepository(path),
        "notification_repo": NotificationRepository(path),
        "commitment_repo": CommitmentRepository(path),
        "expertise_repo": ExpertiseRepository(path),
        "personality_state_repo": PersonalityStateRepository(path),
        "dream_log_repo": DreamLogRepository(path),
        "daily_summary_repo": DailySummaryRepository(path),
        "research_task_repo": ResearchTaskRepository(path),
        "research_branch_repo": ResearchBranchRepository(path),
        "scraped_asset_repo": ScrapedAssetRepository(path),
        "research_meta_log_repo": ResearchMetaLogRepository(path),
        "research_plan_repo": ResearchPlanRepository(path),
        "research_step_repo": ResearchStepRepository(path),
        "research_step_result_repo": ResearchStepResultRepository(path),
    }

