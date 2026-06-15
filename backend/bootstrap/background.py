"""Background task engine and daemon/scheduler initialization.

Extracted from backend/main.py.
"""

import logging

logger = logging.getLogger(__name__)


def _init_background_engine(config: dict, llm_provider, vision_provider):
    """Create the BackgroundTaskEngine with all registered actions.

    Returns: (engine, background_provider)
    """
    bg_cfg = config.get("background_llm", {})

    from backend.bootstrap.providers import _create_provider

    background_provider = None
    if bg_cfg.get("models") or bg_cfg.get("model"):
        try:
            background_provider = _create_provider(bg_cfg, use_default_params=False)
            logger.info(
                "Background model: %s",
                bg_cfg.get("models") or bg_cfg.get("model"),
            )
        except Exception:
            logger.warning("Failed to initialize background provider, using primary")
            background_provider = llm_provider

    # ── Engine with actions ──
    from backend.modules.background_tasks.engine import BackgroundTaskEngine

    engine = BackgroundTaskEngine(
        provider=background_provider or llm_provider,
        vision_provider=vision_provider,
    )

    # Register all background actions
    from backend.modules.background_tasks.actions.consolidate import ConsolidateAction
    from backend.modules.background_tasks.actions.conversation_summary import (
        ConversationSummaryAction,
    )
    from backend.modules.background_tasks.actions.document_collision import (
        DocumentCollisionAction,
    )
    from backend.modules.background_tasks.actions.dream_topic_decision import (
        DreamTopicDecisionAction,
    )
    from backend.modules.background_tasks.actions.metabolize_skill import (
        MetabolizeSkillAction,
    )
    from backend.modules.background_tasks.actions.refine_belief import RefineBeliefAction
    from backend.modules.background_tasks.actions.refine_skill import RefineSkillAction
    from backend.modules.background_tasks.actions.resonance_finder import (
        ResonanceFinderAction,
    )
    from backend.modules.background_tasks.actions.semantic_knot import SemanticKnotAction
    from backend.modules.background_tasks.actions.summarize import SummarizeAction
    from backend.modules.background_tasks.actions.title import GenerateTitleAction

    engine.register(GenerateTitleAction())
    engine.register(SummarizeAction())
    engine.register(ConsolidateAction())
    engine.register(ConversationSummaryAction())
    engine.register(DocumentCollisionAction())
    engine.register(SemanticKnotAction())
    engine.register(DreamTopicDecisionAction())
    engine.register(ResonanceFinderAction())
    engine.register(RefineSkillAction())
    engine.register(MetabolizeSkillAction())
    engine.register(RefineBeliefAction())

    logger.info(
        "Background task engine initialized with actions: %s", engine.list_actions()
    )
    return engine, background_provider


def _start_background_services(app_state):
    """Start the background scheduler and dream daemon."""
    from backend.metabolisation.scheduler import BackgroundStartupScheduler
    from backend.services.file import FileService

    scheduler = BackgroundStartupScheduler(app_state, FileService.process_and_summarize)
    app_state.startup_scheduler = scheduler
    scheduler.start()

    from backend.metabolisation.daemon import AutopoieticDreamDaemon

    dream_daemon = AutopoieticDreamDaemon(app_state)
    app_state.dream_daemon = dream_daemon
    dream_daemon.start()
