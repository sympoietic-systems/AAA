"""Background task engine and daemon/scheduler initialization.

Extracted from backend/main.py.
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


async def _db_backup_loop():
    """Run a DB backup on startup, then every 24 hours. Keeps last 3."""
    DB_PATH = Path(__file__).resolve().parent.parent / "data" / "aaa.db"
    BACKUP_DIR = DB_PATH.parent / "backups"
    MAX_BACKUPS = 3

    async def do_backup():
        if not DB_PATH.exists():
            return
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")
        backup_path = BACKUP_DIR / f"aaa_backup_{today}.db"
        if backup_path.exists():
            return  # already done today
        try:
            new_size = DB_PATH.stat().st_size
            shutil.copy2(str(DB_PATH), str(backup_path))
            logger.info("DB backup created: %s (%dB)", backup_path, new_size)

            # Prune old backups — but only if new one is not suspiciously smaller
            existing = sorted(BACKUP_DIR.glob("aaa_backup_*.db"), key=os.path.getmtime, reverse=True)
            if len(existing) > MAX_BACKUPS:
                # Check previous backup size ratio
                prev_size = existing[1].stat().st_size if len(existing) > 1 else new_size
                if new_size < prev_size * 0.3:
                    logger.warning(
                        "New backup (%dB) is <30%% of previous (%dB) — "
                        "keeping old backups as safety", new_size, prev_size,
                    )
                    return
                for old in existing[MAX_BACKUPS:]:
                    old.unlink()
                    logger.info("Pruned old backup: %s", old)
        except Exception as e:
            logger.warning("DB backup failed: %s", e)

    # Run immediately on startup
    await do_backup()

    # Then every 24 hours
    while True:
        await asyncio.sleep(86400)
        await do_backup()


def _start_db_backup_loop():
    """Launch the DB backup loop as a background task."""
    asyncio.create_task(_db_backup_loop())
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
    _start_db_backup_loop()
