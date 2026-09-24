"""Queued self-trigger dream execution."""

import json
import logging
from typing import Any

from backend.metabolisation.dream_collaborator import DreamDaemonCollaborator, DreamResult

logger = logging.getLogger(__name__)


class DreamExecutionMixin(DreamDaemonCollaborator):
    async def _execute_self_triggered_dream(self, trigger: dict[str, Any], now: float) -> DreamResult | None:
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
