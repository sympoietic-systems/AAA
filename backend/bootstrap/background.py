"""Background task engine and daemon/scheduler initialization.

Extracted from backend/main.py.
"""

import asyncio
import logging
import os

logger = logging.getLogger(__name__)


async def _db_backup_loop(db_path, backup_dir, keep: int = 3):
    """Run a DB backup on startup, then every 24 hours. Keeps last 3."""
    from backend.services.backup import create_verified_backup

    async def do_backup():
        if not db_path.exists():
            return
        try:
            backup_path = await asyncio.to_thread(create_verified_backup, db_path, backup_dir, keep=keep)
            logger.info("DB backup created and verified: %s", backup_path)
        except Exception:
            logger.exception("DB backup failed")

    # Run immediately on startup
    await do_backup()

    # Then every 24 hours
    while True:
        await asyncio.sleep(86400)
        await do_backup()


def _start_db_backup_loop(app_state):
    """Launch the DB backup loop as a background task."""
    from backend.storage.database import get_db_path

    config = getattr(app_state, "config", {})
    db_path = get_db_path(config.get("database", {}).get("path", "data/aaa.db"))
    backup_cfg = config.get("backup", {})
    backup_dir = db_path.parent / "backups"
    task = asyncio.create_task(_db_backup_loop(db_path, backup_dir, keep=int(backup_cfg.get("keep", 3))))
    app_state.db_backup_task = task
    logger.info("DB backup loop started")


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
    from backend.modules.background_tasks.actions.research_crystallize import (
        ResearchCrystallizeAction,
    )
    from backend.modules.background_tasks.actions.resonance_finder import (
        ResonanceFinderAction,
    )
    from backend.modules.background_tasks.actions.semantic_knot import SemanticKnotAction
    from backend.modules.background_tasks.actions.structure_extraction import (
        StructureExtractionAction,
    )
    from backend.modules.background_tasks.actions.summarize import SummarizeAction
    from backend.modules.background_tasks.actions.title import GenerateTitleAction
    from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient

    typesafe_cfg = config.get("typesafe", {})
    typesafe_client = None
    if typesafe_cfg.get("enabled", True):
        api_key = typesafe_cfg.get("api_key") or os.environ.get("TYPESAFE_API_KEY") or os.environ.get("AAA_LLM_API_KEY")
        if api_key:
            ts_cfg = dict(typesafe_cfg)
            ts_cfg["api_key"] = api_key
            typesafe_client = TypeSafeDecisionClient.from_config(ts_cfg)

    engine.register(GenerateTitleAction())
    engine.register(SummarizeAction())
    engine.register(ConsolidateAction())
    engine.register(ConversationSummaryAction())
    engine.register(DocumentCollisionAction())
    engine.register(SemanticKnotAction())
    engine.register(DreamTopicDecisionAction(typesafe_client=typesafe_client))
    engine.register(ResonanceFinderAction())
    engine.register(RefineSkillAction())
    engine.register(MetabolizeSkillAction())
    engine.register(RefineBeliefAction())
    engine.register(ResearchCrystallizeAction())
    engine.register(StructureExtractionAction())

    logger.info("Background task engine initialized with actions: %s", engine.list_actions())
    return engine, background_provider


def _start_background_services(app_state):
    """Start the background scheduler, dream daemon, and DB backup."""
    from backend.metabolisation.scheduler import BackgroundStartupScheduler
    from backend.services.file import FileService

    scheduler = BackgroundStartupScheduler(app_state, FileService.process_and_summarize)
    app_state.startup_scheduler = scheduler
    scheduler.start()

    from backend.metabolisation.daemon import AutopoieticDreamDaemon

    dream_daemon = AutopoieticDreamDaemon(app_state)
    app_state.dream_daemon = dream_daemon
    dream_daemon.start()

    # Daily DB backup — runs once on startup, then every 24h
    _start_db_backup_loop(app_state)
