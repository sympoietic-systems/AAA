"""Dream trigger policy and budget gates."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import cast

from backend.metabolisation.dream_collaborator import DreamDaemonCollaborator, DreamResult

logger = logging.getLogger(__name__)


class DreamTriggerPolicyMixin(DreamDaemonCollaborator):
    async def check_and_trigger_dream(self, force: bool = False) -> DreamResult | None:
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
            return cast(DreamResult | None, await self._execute_self_triggered_dream(pending_trigger, now))

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
                    import uuid

                    self.belief_repo.insert_belief_event(
                        event_id=str(uuid.uuid4()),
                        belief_id=hotspot.id,
                        source_type="dream_hotspot",
                        source_id=dream_convo_id,
                        alignment=1.0,
                        perturbation=0.05,
                        event_type="dream_engagement",
                        impact=0.05,
                        rationale=f"Hotspot engaged in dream monologue/harvest ({action}, {actual_turns} turns)",
                        suppress_notification=False,
                    )
                except Exception as e:
                    logger.warning("Failed to update belief last_dreamed_at or record event: %s", e)

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
