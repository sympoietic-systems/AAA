"""
Backward-compatibility shim for the original monolithic repository module.

All repository classes and helpers have been moved to:
- backend/storage/connection.py    (ConnectionTracker, with_connection, _get_tracked_connection)
- backend/storage/row_mappers.py   (_row_to_* functions)
- backend/storage/repositories/    (individual repository classes)

This file exists so existing imports like:
    from backend.storage.repository import MessageRepository
continue to work without changes.
"""

from backend.storage.connection import ConnectionTracker, with_connection, _get_tracked_connection
from backend.storage.row_mappers import (
    _row_to_belief_event,
    _row_to_belief_node,
    _row_to_commitment_event,
    _row_to_commitment_node,
    _row_to_conversation,
    _row_to_expertise_node,
    _row_to_memory_node,
    _row_to_message,
    _row_to_metrics,
    _row_to_perception_sediment,
    _row_to_personality_state,
    _row_to_semantic_knot,
    _row_to_skill_event,
    _row_to_skill_node,
)
from backend.storage.repositories import (
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
    ResearchTaskRepository,
    ResearchMetaLogRepository,
    ResearchPlanRepository,
    ResearchStepRepository,
    ResearchStepResultRepository,
    RefusalRepository,
    ScrapedAssetRepository,
    SemanticKnotRepository,
    SkillRepository,
)

__all__ = [
    "ConnectionTracker",
    "with_connection",
    "_get_tracked_connection",
    "_row_to_message",
    "_row_to_conversation",
    "_row_to_metrics",
    "_row_to_perception_sediment",
    "_row_to_memory_node",
    "_row_to_belief_node",
    "_row_to_belief_event",
    "_row_to_commitment_node",
    "_row_to_commitment_event",
    "_row_to_expertise_node",
    "_row_to_personality_state",
    "_row_to_semantic_knot",
    "BeliefRepository",
    "CommitmentRepository",
    "ConsolidationCheckpointRepository",
    "ConversationRepository",
    "DreamLogRepository",
    "ErrorLogRepository",
    "ExpertiseRepository",
    "MemoryNodeRepository",
    "MessageRepository",
    "MetricsRepository",
    "NoteRepository",
    "NotificationRepository",
    "PerceptionSedimentRepository",
    "PersonalityStateRepository",
    "RefusalRepository",
    "ResearchBranchRepository",
    "ResearchTaskRepository",
    "ResearchMetaLogRepository",
    "ResearchPlanRepository",
    "ResearchStepRepository",
    "ResearchStepResultRepository",
    "ScrapedAssetRepository",
    "SemanticKnotRepository",
    "SkillRepository",
]
