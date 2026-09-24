"""Autopoietic Dream Daemon — orchestrates background self-reflection cycles.

The daemon monitors user inactivity and triggers autonomous dream actions
(stagnation-breaking, tension hotspots, somatic drift, memory compaction, etc.)
using a multi-turn resonance loop.
"""

import asyncio
import logging
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any

from backend.metabolisation.consolidation import ConsolidationMixin
from backend.metabolisation.dream_context import DreamContextMixin
from backend.metabolisation.dream_execution import DreamExecutionMixin
from backend.metabolisation.dream_executor import DreamExecutorMixin
from backend.metabolisation.dream_maintenance import DreamMaintenanceMixin
from backend.metabolisation.dream_prompts import DreamPromptMixin
from backend.metabolisation.dream_research import DreamResearchMixin
from backend.metabolisation.dream_trigger_policy import DreamTriggerPolicyMixin
from backend.metabolisation.mass_decay import MassDecayMixin
from backend.metabolisation.skill_metabolism import SkillMetabolismMixin

logger = logging.getLogger(__name__)


class AutopoieticDreamDaemon(
    MassDecayMixin,
    DreamContextMixin,
    DreamPromptMixin,
    DreamExecutorMixin,
    DreamTriggerPolicyMixin,
    DreamExecutionMixin,
    DreamMaintenanceMixin,
    ConsolidationMixin,
    SkillMetabolismMixin,
    DreamResearchMixin,
):
    """Background daemon that triggers autonomous self-reflection (dream) cycles."""

    def __init__(self, app_state: Any) -> None:
        self.app_state = app_state
        self.config = getattr(app_state, "config", {})
        self.message_repo = app_state.message_repo
        self.belief_repo = app_state.belief_repo
        self.conversation_repo = app_state.conversation_repo
        self.semantic_knot_repo = getattr(app_state, "semantic_knot_repo", None)
        self.checkpoint_repo = getattr(app_state, "checkpoint_repo", None)
        self.skill_repo = getattr(app_state, "skill_repo", None)
        self.dream_log_repo = getattr(app_state, "dream_log_repo", None)
        self.background_engine = getattr(app_state, "background_engine", None)
        self.pipeline = app_state.pipeline
        self.perception_repo = getattr(app_state, "perception_repo", None)
        self.notification_repo = getattr(app_state, "notification_repo", None)

        # Daemon Configuration
        daemon_cfg = self.config.get("daemon", {})
        self.enabled = daemon_cfg.get("enabled", True)
        self.check_interval = daemon_cfg.get("check_interval", 60)  # seconds
        self.idle_threshold = daemon_cfg.get("idle_threshold", 60)  # seconds (short for testing)
        self.min_dream_interval = daemon_cfg.get("min_dream_interval", 120)  # seconds between dream actions
        self.belief_dream_cooldown_minutes = daemon_cfg.get("belief_dream_cooldown_minutes", 30)
        self.prompt_hash_window = daemon_cfg.get("prompt_hash_window", 10)
        self.dream_resonance_turns = daemon_cfg.get("dream_resonance_turns", 1)
        self.resonance_stagnation = daemon_cfg.get("resonance_stagnation", 0.98)
        self.max_resonance_tokens = daemon_cfg.get("max_resonance_tokens", 8000)
        self.consolidate_cooldown_hours = daemon_cfg.get("consolidate_cooldown_hours", 12)
        self.consolidate_min_new_messages = daemon_cfg.get("consolidate_min_new_messages", 4)
        self.consolidate_first_time_threshold = daemon_cfg.get("consolidate_first_time_threshold", 12)

        # Execution constraints (two-tier budget)
        self.max_daily_dreams = daemon_cfg.get("max_daily_dreams", 120)
        self.short_window_hours = daemon_cfg.get("short_window_hours", 8)
        self.short_window_max = daemon_cfg.get("short_window_max", 2)
        self.dream_counter = 0
        self.last_reset_day = datetime.now(UTC).day

        # State tracking
        self.last_dream_time = 0.0
        self.last_drift_time = 0.0
        self.is_running = False
        self._task: asyncio.Task[None] | None = None

        # Dream telemetry
        self.last_dream_action: str | None = None
        self.dream_action_counts: dict[str, int] = {}
        self._recent_prompt_hashes: deque[str] = deque(maxlen=self.prompt_hash_window)

    def start(self) -> None:
        if not self.enabled:
            logger.info("Autopoietic Dream Daemon is disabled in configuration.")
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Autopoietic Dream Daemon started background thread cycle.")

    def stop(self) -> None:
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("Autopoietic Dream Daemon stopped.")

    async def aclose(self) -> None:
        self.stop()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)

    def get_status(self) -> dict[str, Any]:
        now = time.time()
        last_msg_ts = self.message_repo.get_last_message_timestamp()
        idle_time = now - last_msg_ts.replace(tzinfo=UTC).timestamp() if last_msg_ts else 0.0

        from backend.metabolisation.daemon_trigger_signal import queue_depth

        return {
            "enabled": self.enabled,
            "running": self.is_running,
            "idle_time_seconds": round(idle_time, 2),
            "idle_threshold_seconds": self.idle_threshold,
            "last_dream_time": datetime.fromtimestamp(self.last_dream_time, tz=UTC).isoformat()
            if self.last_dream_time
            else None,
            "dreams_today": self.dream_counter,
            "max_daily_dreams": self.max_daily_dreams,
            "short_window_hours": self.short_window_hours,
            "short_window_max": self.short_window_max,
            "short_window_count": getattr(self, "short_counter", 0),
            "last_dream_action": self.last_dream_action,
            "dream_action_counts": dict(self.dream_action_counts),
            "min_dream_interval": self.min_dream_interval,
            "belief_dream_cooldown_minutes": self.belief_dream_cooldown_minutes,
            "dream_resonance_turns": self.dream_resonance_turns,
            "resonance_stagnation": self.resonance_stagnation,
            "max_resonance_tokens": self.max_resonance_tokens,
            "check_interval": self.check_interval,
            "pending_self_triggers": queue_depth(self.app_state),
        }

    async def _run_loop(self) -> None:
        # Give server time to settle
        await asyncio.sleep(5)
        _last_atrophy_time = 0.0
        _atrophy_interval = 900.0  # Run belief atrophy every 15 minutes
        _last_ghost_ecology_time = 0.0
        _ghost_ecology_interval = 3600.0  # Run ghost ecology every hour
        _last_structure_time = 0.0
        _structure_interval = 1800.0  # Backfill heading-paths every 30 minutes
        _last_msg_id = -1
        while self.is_running:
            # Check if new messages arrived since last tick
            try:
                current_max_id = self.message_repo.get_max_message_id()
            except Exception:
                current_max_id = -1
            has_new_messages = (current_max_id > _last_msg_id) or (_last_msg_id == -1)

            if has_new_messages:
                try:
                    await self.consolidate_pending_conversations()
                except Exception as e:
                    logger.error("Error in Autopoietic Dream Daemon consolidation check: %s", e)

            # Autonomous research proposal scanning (Phase 4)
            try:
                await self._scan_and_propose_research()
            except Exception as e:
                logger.debug("Research proposal scan skipped: %s", e)

            # Drain queued research tasks — safety net for dropped fire-and-forget dispatches
            try:
                await self._drain_research_queue()
            except Exception as e:
                logger.debug("Research queue drain skipped: %s", e)

            # Post-research metabolism for completed tasks
            try:
                await self.metabolize_research_on_idle()
            except Exception as e:
                logger.debug("Research metabolism skipped: %s", e)

            # Research sedimentation rake — crystallizes in-phase memory nodes
            try:
                await self.rake_research_sedimentation()
            except Exception as e:
                logger.debug("Research sedimentation rake skipped: %s", e)

            if has_new_messages:
                try:
                    await self.run_skill_metabolism()
                except Exception as e:
                    logger.exception("Error in Autopoietic Dream Daemon skill metabolism: %s", e)

            _last_msg_id = current_max_id

            # Periodic structure-extraction backfill (ADR-062 migration)
            now_ts_struct = time.time()
            if now_ts_struct - _last_structure_time >= _structure_interval:
                _last_structure_time = now_ts_struct
                try:
                    await self.backfill_structure_on_idle()
                except Exception as e:
                    logger.debug("Structure backfill skipped: %s", e)
            # Periodic belief atrophy — disabled by default in favor of turn-based metabolism
            now_ts = time.time()
            wall_clock_decay_enabled = (
                getattr(self, "config", {})
                .get("belief_ecosystem", {})
                .get("wall_clock_decay", {})
                .get("enabled", False)
            )
            if wall_clock_decay_enabled and (now_ts - _last_atrophy_time >= _atrophy_interval):
                _last_atrophy_time = now_ts
                try:
                    engine = getattr(self.app_state, "belief_metabolism", None)
                    if engine:
                        result = await engine._atrophy_beliefs("symbia")
                        if result.get("atrophied", 0) > 0:
                            logger.info(
                                "Daemon atrophy cycle: %d beliefs decayed (%d collapsed)",
                                result["atrophied"],
                                result.get("collapsed", 0),
                            )
                except Exception as e:
                    logger.exception("Error in daemon atrophy cycle: %s", e)
            # Periodic ghost ecology (merging, fading, resurrection — independent of dream budget)
            if now_ts - _last_ghost_ecology_time >= _ghost_ecology_interval:
                _last_ghost_ecology_time = now_ts
                try:
                    engine = getattr(self.app_state, "belief_metabolism", None)
                    if engine:
                        ghost_result = await engine.process_ghost_ecology("symbia")
                        resurrected = await engine.check_ghost_resurrection("symbia")
                        if ghost_result["merged"] > 0 or ghost_result["faded"] > 0 or resurrected > 0:
                            logger.info(
                                "Ghost ecology: merged=%d, faded=%d, resurrected=%d",
                                ghost_result["merged"],
                                ghost_result["faded"],
                                resurrected,
                            )
                except Exception as e:
                    logger.error("Ghost ecology error: %s", e)
            try:
                await self.check_and_trigger_dream()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in Autopoietic Dream Daemon cycle: %s", e)
            await asyncio.sleep(self.check_interval)
