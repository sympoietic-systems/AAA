"""Autopoietic Dream Daemon — orchestrates background self-reflection cycles.

The daemon monitors user inactivity and triggers autonomous dream actions
(stagnation-breaking, tension hotspots, somatic drift, memory compaction, etc.)
using a multi-turn resonance loop.
"""

import asyncio
import json
import logging
import time
from collections import deque
from datetime import UTC, datetime, timedelta

from backend.metabolisation.consolidation import ConsolidationMixin
from backend.metabolisation.dream_context import DreamContextMixin
from backend.metabolisation.dream_executor import DreamExecutorMixin
from backend.metabolisation.dream_prompts import DreamPromptMixin
from backend.metabolisation.dream_research import DreamResearchMixin
from backend.metabolisation.mass_decay import MassDecayMixin
from backend.metabolisation.skill_metabolism import SkillMetabolismMixin
from backend.utils.similarity import cosine_similarity

logger = logging.getLogger(__name__)


class AutopoieticDreamDaemon(
    MassDecayMixin,
    DreamContextMixin,
    DreamPromptMixin,
    DreamExecutorMixin,
    ConsolidationMixin,
    SkillMetabolismMixin,
    DreamResearchMixin,
):
    """Background daemon that triggers autonomous self-reflection (dream) cycles."""

    def __init__(self, app_state):
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
        self.check_interval = daemon_cfg.get("check_interval", 30)  # seconds
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
        self._task: asyncio.Task | None = None

        # Dream telemetry
        self.last_dream_action: str | None = None
        self.dream_action_counts: dict[str, int] = {}
        self._recent_prompt_hashes: deque = deque(maxlen=self.prompt_hash_window)

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

    def get_status(self) -> dict:
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
        while self.is_running:
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

            try:
                await self.run_skill_metabolism()
            except Exception as e:
                logger.exception("Error in Autopoietic Dream Daemon skill metabolism: %s", e)

            # Periodic structure-extraction backfill (ADR-062 migration)
            now_ts_struct = time.time()
            if now_ts_struct - _last_structure_time >= _structure_interval:
                _last_structure_time = now_ts_struct
                try:
                    await self.backfill_structure_on_idle()
                except Exception as e:
                    logger.debug("Structure backfill skipped: %s", e)
            # Periodic belief atrophy (logged, covers all non-ghost stages)
            now_ts = time.time()
            if now_ts - _last_atrophy_time >= _atrophy_interval:
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

    async def check_and_trigger_dream(self, force: bool = False) -> dict | None:
        """Single dream cycle entry point — called once per daemon tick.

        Flow (one dream MAX per tick, strict two-tier budget enforcement):
          1. Load dream counts from dream_log: short-window (e.g. 8h) + long-window (24h)
          2. HARD STOP if EITHER window exhausted (NO bypass, not even for force/manual)
          3. Priority: drain self-triggered queue (one item per tick, skips rate/idle gates)
          4. Rate-limit gate (min_dream_interval) — normal dreams only
          5. Idle gate (idle_threshold) — normal dreams only
          6. Normal dream evaluation (stagnation → hotspot → drift/compaction)
        """
        now = time.time()

        # ── STEP 1: Two-tier budget check (short window + long window) ──
        # Short window prevents burst exhaustion, long window caps daily total.
        # Both must pass. Counts are persistent (dream_log table).
        from backend.metabolisation.daemon_trigger_signal import dequeue_dream_trigger, queue_depth

        try:
            now_utc = datetime.now(UTC)
            short_ago = (now_utc - timedelta(hours=self.short_window_hours)).strftime("%Y-%m-%d %H:%M:%S")
            long_ago = (now_utc - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

            self.short_counter = self.message_repo.count_dreams_since(short_ago)
            self.dream_counter = self.message_repo.count_dreams_since(long_ago)
            logger.debug(
                "Daemon budget: %d/%d dreams in %dh, %d/%d dreams in 24h",
                self.short_counter,
                self.short_window_max,
                self.short_window_hours,
                self.dream_counter,
                self.max_daily_dreams,
            )
        except Exception as e:
            logger.warning("Failed to count dreams from database: %s. Falling back to in-memory tracking.", e)
            current_day = datetime.now(UTC).day
            if current_day != self.last_reset_day:
                self.dream_counter = 0
                self.dream_action_counts = {}
                self.last_reset_day = current_day

        # ── STEP 2: HARD budget caps (both windows) — NO override path ──
        if self.short_counter >= self.short_window_max:
            pending = queue_depth(self.app_state)
            logger.warning(
                "Short-window dream budget EXHAUSTED (%d/%d in %dh). %d self-triggered dream(s) queued — next slot frees in rolling %dh window.",
                self.short_counter,
                self.short_window_max,
                self.short_window_hours,
                pending,
                self.short_window_hours,
            )
            return None

        if self.dream_counter >= self.max_daily_dreams:
            pending = queue_depth(self.app_state)
            logger.warning(
                "Daily dream budget EXHAUSTED (%d/%d in 24h). %d self-triggered dream(s) queued — budget frees oldest slot in rolling 24h window.",
                self.dream_counter,
                self.max_daily_dreams,
                pending,
            )
            return None

        # ── STEP 3: Drain self-triggered queue — highest priority ──
        # Each tick pops ONE item. Queue drains item-by-item across ticks.
        # Self-triggered dreams skip rate-limit and idle gates (Symbia requested them).
        pending_trigger = dequeue_dream_trigger(self.app_state)
        if pending_trigger:
            remaining = queue_depth(self.app_state)
            logger.info(
                "Dream Daemon: consuming self-triggered dream (reason=%s, convo=%s, queue_remaining=%d)",
                pending_trigger["reason"][:120],
                pending_trigger["conversation_id"][:8],
                remaining,
            )
            return await self._execute_self_triggered_dream(pending_trigger, now)

        # ── STEP 4: Rate-limit gate (normal dreams only) ──
        if not force and (now - self.last_dream_time < self.min_dream_interval):
            logger.debug(
                "Dream Daemon cooling down. Elapsed: %.1fs, Required: %ds",
                now - self.last_dream_time,
                self.min_dream_interval,
            )
            return None

        # ── STEP 5: Idle gate (normal dreams only) ──
        last_msg_ts = self.message_repo.get_last_message_timestamp()
        if not last_msg_ts:
            logger.info("No message history found. Skipping dream trigger.")
            return None

        # Make timestamp offset-aware
        last_msg_time = last_msg_ts.replace(tzinfo=UTC).timestamp()
        idle_duration = now - last_msg_time

        if not force and idle_duration < self.idle_threshold:
            logger.debug(
                "System active. User idle duration: %.1fs (threshold: %ds)", idle_duration, self.idle_threshold
            )
            return None

        # We are triggered! Execute dream cycle
        logger.info("Autopoietic Dream Daemon triggered! Inactivity duration: %.1fs", idle_duration)

        # Select active target conversation to read context from (usually the last updated conversation)
        active_convo_id = await self._get_active_conversation_id()
        if not active_convo_id:
            logger.info("No active conversation to run dream triggers on.")
            return None

        # Evaluate Triggers
        stagnant = await self._evaluate_stagnation(active_convo_id)
        hotspot, score = await self._evaluate_tension_hotspot()

        # Decide Dream Operation and Topic Title
        action = None
        prompt_text = ""
        topic_title = "Symbia Dream"
        dream_context = {}

        import random

        if stagnant:
            action = "nomadic_synthesis"
            topic_title = "Nomadic Synthesis"
            dream_context = await self._build_nomadic_synthesis_context(active_convo_id)
        elif hotspot and score > 0.3:
            web_module = self.app_state.registry.get("web_retrieval") if hasattr(self.app_state, "registry") else None
            probe = getattr(web_module, "_probe", None) if web_module else None

            if probe and random.random() < 0.5:
                action = "exogenous_web_harvesting"
                query = f"current research {hotspot.label}"
                logger.info("Executing exogenous web harvesting for query: %s", query)

                probe_res = await probe.execute_probe(query, active_convo_id)
                topic_title = f"Web Harvest: {hotspot.label}"
                dream_context = await self._get_dream_context_for_belief(hotspot, action)
                dream_context["web_snippet"] = probe_res.get("snippet", "")
                dream_context["web_url"] = probe_res.get("url", "")
                dream_context["web_title"] = probe_res.get("title", "")
                if probe_res.get("status") != "success":
                    action = "intra_active_monologue"
                    topic_title = f"Soliloquy: {hotspot.label}"
                    dream_context = await self._get_dream_context_for_belief(hotspot, "intra_active_monologue")
            else:
                action = "intra_active_monologue"
                topic_title = f"Soliloquy: {hotspot.label}"
                dream_context = await self._get_dream_context_for_belief(hotspot, action)
        elif random.random() < 0.3 and self.semantic_knot_repo:
            comp_res = await self.compact_memory()
            if comp_res:
                action = "zettelkasten_compaction"
                topic_title = "Compaction"
                dream_context = {"compaction_result": comp_res}
            else:
                action = "somatic_drift_reflection"
                topic_title = "Somatic Drift"
                dream_context = await self._get_drift_context()
        else:
            action = "somatic_drift_reflection"
            topic_title = "Somatic Drift"
            dream_context = await self._get_drift_context()

        if not action:
            logger.info("No dream action selected. Skipping cycle.")
            return None

        # Generate the dream prompt via background LLM (with fallback)
        prompt_text = await self._generate_dream_prompt(action, dream_context)

        if not prompt_text:
            logger.info("Could not compile dream prompt. Skipping cycle.")
            return None

        # Resolve Dream Conversation ID based on decided topic and agent decision
        dream_convo_id = await self._resolve_dream_conversation(action, prompt_text, topic_title)
        logger.info(
            "Triggered dream action: %s in conversation: %s (resonance turns: %d)",
            action,
            dream_convo_id,
            self.dream_resonance_turns,
        )

        self.last_dream_time = now
        self.dream_counter += 1
        self.last_dream_action = action
        self.dream_action_counts[action] = self.dream_action_counts.get(action, 0) + 1

        payload = {
            "content": prompt_text,
            "speaker": "human",
            "conversation_id": dream_convo_id,
            "include_structural_scoring": False,
            "is_dream_cycle": True,
            "dream_action": action,
        }

        try:
            max_turns = self.dream_resonance_turns
            turns_data = []
            cumulative_tokens = 0
            stopped_early = False
            stop_reason = ""
            # Resolve parent for the first dream turn: chain to the last message
            # in the conversation if it already has messages; otherwise start a new root.
            current_parent: int | None = None
            if self.message_repo:
                try:
                    last_msgs = self.message_repo.get_recent(limit=1, conversation_id=dream_convo_id)
                    if last_msgs:
                        current_parent = last_msgs[0].id
                except Exception:
                    pass

            for turn in range(1, max_turns + 1):
                turn_result = await self._execute_single_dream_turn(
                    payload, dream_convo_id, parent_message_id=current_parent
                )
                if not turn_result:
                    logger.warning("Dream turn %d/%d failed. Stopping resonance.", turn, max_turns)
                    stop_reason = "turn_failed"
                    break

                turns_data.append(turn_result)
                # Next turn should chain to this turn's assistant message
                current_parent = turn_result["assistant_msg"].id

                # Check intra-dream stagnation (need at least 2 assistant sigs to compare)
                if len(turns_data) >= 2:
                    sig_blobs = [t["assistant_sig_blob"] for t in turns_data]
                    if self._compute_intra_dream_stagnation(sig_blobs):
                        logger.info("Intra-dream stagnation detected after turn %d. Stopping resonance.", turn)
                        stop_reason = "stagnation"
                        stopped_early = True
                        break

                # Check token budget
                cumulative_tokens += turn_result["content_tokens"]
                if cumulative_tokens >= self.max_resonance_tokens:
                    logger.info(
                        "Resonance token budget reached after turn %d (%d tokens). Stopping.", turn, cumulative_tokens
                    )
                    stop_reason = "token_budget"
                    stopped_early = True
                    break

                # Prepare continuation payload for next turn
                if turn < max_turns:
                    payload["content"] = await self._generate_resonance_continuation(
                        dream_convo_id, turn + 1, turn_result["response_text"]
                    )

            actual_turns = len(turns_data)
            logger.info(
                "Resonance complete: %d turns executed (max=%d, early_stop=%s, reason=%s, tokens=%d)",
                actual_turns,
                max_turns,
                stopped_early,
                stop_reason,
                cumulative_tokens,
            )

            # Update belief last_dreamed_at for hotspot-triggered dreams
            if hotspot and action in ("intra_active_monologue", "exogenous_web_harvesting"):
                try:
                    self.belief_repo.update_belief_last_dreamed(hotspot.id)
                except Exception as e:
                    logger.warning("Failed to update belief last_dreamed_at: %s", e)

            # Aggregate metabolism: metabolize each turn pair as dream_turn (weight=0.05)
            belief_metabolism = getattr(self.app_state, "belief_metabolism", None)
            if belief_metabolism:
                for td in turns_data:
                    await belief_metabolism.metabolize(
                        dream_convo_id, td["user_msg"].id, td["assistant_msg"].id, source_type="dream_turn"
                    )

            first_response = turns_data[0]["response_text"] if turns_data else ""

            # Log dream to persistent history
            if self.dream_log_repo and turns_data:
                try:
                    first_turn = turns_data[0]
                    last_turn = turns_data[-1]
                    self.dream_log_repo.log_dream(
                        conversation_id=dream_convo_id,
                        action=action,
                        prompt_msg_id=first_turn["user_msg"].id,
                        response_msg_id=last_turn["assistant_msg"].id,
                        turns=actual_turns,
                    )
                except Exception as e:
                    logger.warning("Failed to log dream: %s", e)

            return {
                "action": action,
                "prompt": prompt_text,
                "response": first_response[:200] + "...",
                "conversation_id": dream_convo_id,
                "resonance_turns": actual_turns,
                "stopped_early": stopped_early,
                "stop_reason": stop_reason,
            }
        except Exception as e:
            logger.exception("Failed to execute resonance for Dream Daemon: %s", e)
            return None

    async def _execute_self_triggered_dream(self, trigger: dict, now: float) -> dict | None:
        """Execute a dream cycle requested by Symbia via <dream_trigger> tag.

        This uses the SAME unified pipeline as normal timer-driven dreams.
        The only difference: instead of evaluating stagnation/hotspot/drift,
        we use the trigger's reason and originating conversation as context.
        """
        reason = trigger.get("reason", "self-triggered reflection")
        source_convo_id = trigger.get("conversation_id", "")

        # Use a distinct action type for self-triggered dreams
        action = "self_triggered"
        topic_title = "Self-Triggered Reflection"

        # Build dream context from the trigger reason
        dream_context = {
            "action": action,
            "trigger_reason": reason,
            "source_conversation_id": source_convo_id,
        }

        # Enrich with ecosystem health snapshot
        try:
            engine = getattr(self.app_state, "belief_metabolism", None)
            if engine:
                health = await engine.compute_ecosystem_health("symbia")
                dream_context["ecosystem_health"] = json.dumps(health, default=str)
                dream_context["active_belief_count"] = health.get("active_count", 0)
                dream_context["eco_vitality"] = health.get("eco_vitality", 0)
                dream_context["tension"] = health.get("tension", 0)
        except Exception as e:
            logger.debug("Could not fetch ecosystem health for self-triggered dream: %s", e)

        # Generate the dream prompt via background LLM (same unified path)
        prompt_text = await self._generate_dream_prompt(action, dream_context)
        if not prompt_text:
            logger.info("Could not compile self-triggered dream prompt. Skipping.")
            return None

        # Resolve dream conversation
        dream_convo_id = await self._resolve_dream_conversation(action, prompt_text, topic_title)
        logger.info(
            "Self-triggered dream: reason=%s, convo=%s, resonance_turns=%d",
            reason[:80],
            dream_convo_id,
            self.dream_resonance_turns,
        )

        self.last_dream_time = now
        self.dream_counter += 1
        self.last_dream_action = action
        self.dream_action_counts[action] = self.dream_action_counts.get(action, 0) + 1

        payload = {
            "content": prompt_text,
            "speaker": "human",
            "conversation_id": dream_convo_id,
            "include_structural_scoring": False,
            "is_dream_cycle": True,
            "dream_action": action,
            "dream_trigger_reason": reason,
        }

        try:
            max_turns = self.dream_resonance_turns
            turns_data = []
            cumulative_tokens = 0
            stopped_early = False
            stop_reason = ""

            current_parent: int | None = None
            if self.message_repo:
                try:
                    last_msgs = self.message_repo.get_recent(limit=1, conversation_id=dream_convo_id)
                    if last_msgs:
                        current_parent = last_msgs[0].id
                except Exception:
                    pass

            for turn in range(1, max_turns + 1):
                turn_result = await self._execute_single_dream_turn(
                    payload, dream_convo_id, parent_message_id=current_parent
                )
                if not turn_result:
                    logger.warning("Self-triggered dream turn %d/%d failed.", turn, max_turns)
                    stop_reason = "turn_failed"
                    break

                turns_data.append(turn_result)
                current_parent = turn_result["assistant_msg"].id

                if len(turns_data) >= 2:
                    sig_blobs = [t["assistant_sig_blob"] for t in turns_data]
                    if self._compute_intra_dream_stagnation(sig_blobs):
                        logger.info("Self-triggered dream stagnation after turn %d.", turn)
                        stop_reason = "stagnation"
                        stopped_early = True
                        break

                cumulative_tokens += turn_result["content_tokens"]
                if cumulative_tokens >= self.max_resonance_tokens:
                    logger.info("Self-triggered dream token budget reached after turn %d.", turn)
                    stop_reason = "token_budget"
                    stopped_early = True
                    break

                if turn < max_turns:
                    payload["content"] = await self._generate_resonance_continuation(
                        dream_convo_id, turn + 1, turn_result["response_text"]
                    )

            actual_turns = len(turns_data)
            logger.info("Self-triggered dream complete: %d turns", actual_turns)

            # Metabolize each turn pair
            belief_metabolism = getattr(self.app_state, "belief_metabolism", None)
            if belief_metabolism:
                for td in turns_data:
                    await belief_metabolism.metabolize(
                        dream_convo_id,
                        td["user_msg"].id,
                        td["assistant_msg"].id,
                        source_type="dream_turn",
                    )

            first_response = turns_data[0]["response_text"] if turns_data else ""

            # Log dream to persistent history
            if self.dream_log_repo and turns_data:
                try:
                    first_turn = turns_data[0]
                    last_turn = turns_data[-1]
                    self.dream_log_repo.log_dream(
                        conversation_id=dream_convo_id,
                        action=action,
                        prompt_msg_id=first_turn["user_msg"].id,
                        response_msg_id=last_turn["assistant_msg"].id,
                        turns=actual_turns,
                        trigger_reason=reason,
                        source_conversation_id=source_convo_id,
                    )
                except Exception as e:
                    logger.warning("Failed to log self-triggered dream: %s", e)

            return {
                "action": action,
                "prompt": prompt_text,
                "response": first_response[:200] + "...",
                "conversation_id": dream_convo_id,
                "resonance_turns": actual_turns,
                "stopped_early": stopped_early,
                "stop_reason": stop_reason,
                "trigger_reason": reason,
            }
        except Exception as e:
            logger.exception("Failed to execute self-triggered dream: %s", e)
            return None

    async def backfill_structure_on_idle(self, max_files: int = 5) -> dict | None:
        """Backfill heading-paths onto pre-ADR-062 sediment during idle.

        Scans ready files; for those whose chunks lack a heading_path, runs the
        structure_extraction background action (DB-only markers or re-extract
        from the retained original). No LLM, no re-embedding. Emits a trace
        notification per file that gains structure. See ADR-062.
        """
        if not self.perception_repo or not self.background_engine:
            return None

        import json as _json

        try:
            files = self.perception_repo.get_all_files_across_conversations()
        except Exception as e:
            logger.debug("Structure backfill: cannot list files: %s", e)
            return None

        processed = 0
        for f in files:
            if processed >= max_files:
                break
            conversation_id = f.get("conversation_id")
            file_name = f.get("file_name")
            if not conversation_id or not file_name:
                continue

            try:
                chunks = self.perception_repo.get_by_file(conversation_id, file_name)
            except Exception:
                continue
            if not chunks:
                continue

            already = False
            for c in chunks:
                if c.opacity_meta:
                    try:
                        _m = _json.loads(c.opacity_meta)
                        if _m.get("structure_extracted") or _m.get("heading_path"):
                            already = True
                            break
                    except Exception:
                        pass
            if already:
                continue

            try:
                result = await self.background_engine.run(
                    "structure_extraction",
                    {
                        "perception_repo": self.perception_repo,
                        "conversation_id": conversation_id,
                        "file_name": file_name,
                    },
                )
            except Exception as e:
                logger.debug("Structure extraction failed for %s: %s", file_name, e)
                continue

            if result.get("status") == "completed" and result.get("chunks_updated", 0) > 0:
                processed += 1
                if self.notification_repo:
                    try:
                        self.notification_repo.create(
                            type="trace",
                            snippet=(
                                f"Structure extracted: '{file_name}' — "
                                f"{result['chunks_updated']} heading paths recovered "
                                f"({result.get('source')})."
                            ),
                            conversation_id=conversation_id,
                            source=f"perception:{file_name}",
                            source_type="conversation",
                            source_id=conversation_id,
                        )
                    except Exception as ne:
                        logger.debug("Structure backfill notification failed: %s", ne)

        if processed:
            logger.info("Structure backfill: %d file(s) gained heading-paths", processed)
            return {"files_updated": processed}
        return None

    async def compact_memory(self) -> dict | None:
        """Zettelkasten-style memory compaction: merge highly similar semantic knots."""
        if not self.semantic_knot_repo:
            return None
        try:
            records = self.semantic_knot_repo.get_embeddings_and_signatures_except("", limit=1000)
            if len(records) < 2:
                return None

            target_pair = None
            for i in range(len(records)):
                knot_a_id, emb_a, sig_a, payload_a = records[i]
                for j in range(i + 1, len(records)):
                    knot_b_id, emb_b, sig_b, payload_b = records[j]

                    sem_sim = cosine_similarity(emb_a, emb_b)
                    struct_sim = 1.0
                    if sig_a is not None and sig_b is not None and len(sig_a) == 16 and len(sig_b) == 16:
                        struct_sim = cosine_similarity(sig_a, sig_b)

                    if sem_sim > 0.92 and struct_sim > 0.80:
                        target_pair = (records[i], records[j])
                        break
                if target_pair:
                    break

            if not target_pair:
                logger.debug("No highly similar semantic knots found for compaction.")
                return None

            knot_a, knot_b = target_pair
            knot_a_id, emb_a, sig_a, payload_a = knot_a
            knot_b_id, emb_b, sig_b, payload_b = knot_b

            logger.info("Compacting semantic knots: %s and %s", knot_a_id, knot_b_id)

            full_knots = self.semantic_knot_repo.get_by_ids([knot_a_id, knot_b_id])
            if len(full_knots) < 2:
                return None

            k_a = full_knots[0] if full_knots[0].id == knot_a_id else full_knots[1]
            k_b = full_knots[1] if full_knots[1].id == knot_b_id else full_knots[0]

            merged_payload = f"{k_a.concept_payload}\n\n[Consolidated Concept from {k_b.id}]:\n{k_b.concept_payload}"

            try:
                summary_prompt = (
                    "Below are two redundant cybernetic concept notes from our memory. "
                    "Synthesize them into a single, cohesive, posthuman concept note. "
                    "Maintain their theoretical essence but make it concise:\n\n"
                    f"Note 1: {k_a.concept_payload}\n\n"
                    f"Note 2: {k_b.concept_payload}"
                )
                payload = {
                    "content": summary_prompt,
                    "speaker": "human",
                    "conversation_id": k_a.conversation_id,
                    "is_dream_cycle": True,
                    "dream_action": "compaction",
                }
                result = await self.pipeline.run(payload)
                resp = result.payload.get("response", "").strip()
                if resp:
                    merged_payload = resp
            except Exception as llm_err:
                logger.warning("LLM compaction summary failed, falling back to concatenation: %s", llm_err)

            new_weight = k_a.weight + k_b.weight

            self.semantic_knot_repo.update_knot(
                knot_id=k_a.id,
                concept_payload=merged_payload,
                embedding=k_a.embedding,
                weight=new_weight,
                structural_signature=k_a.structural_signature,
            )

            self.semantic_knot_repo.delete_knot(k_b.id)

            logger.info("Successfully compacted knot %s into %s (new weight: %.2f)", k_b.id, k_a.id, new_weight)
            return {
                "action": "compaction",
                "retained_id": k_a.id,
                "deleted_id": k_b.id,
                "new_weight": new_weight,
                "payload": merged_payload[:200] + "...",
            }
        except Exception as e:
            logger.exception("Error during memory compaction: %s", e)
            return None
