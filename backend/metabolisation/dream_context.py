"""Dream context building and evaluation mixin for the Dream Daemon."""

import json
import logging
import math
from datetime import datetime, timezone
from typing import Optional, List, Tuple

import numpy as np

from backend.storage.models import BeliefNode
from backend.utils.similarity import cosine_similarity
from backend.utils.prompt_loader import get_prompts_dict

logger = logging.getLogger(__name__)


class DreamContextMixin:
    """Handles dream context building, stagnation evaluation, and tension hotspot detection."""

    async def _get_active_conversation_id(self) -> Optional[str]:
        convos = self.conversation_repo.list_all()
        if not convos:
            return None
        for c in convos:
            if not hasattr(self.conversation_repo, "get_tags"):
                return c.id
            tags = self.conversation_repo.get_tags(c.id)
            is_dream = any(t["tag_type"] == "structural" and t["tag"] == "dreams" for t in tags)
            if not is_dream:
                return c.id
        return convos[0].id

    async def _evaluate_stagnation(self, conversation_id: str) -> bool:
        """Verify stagnation using recent assistant signatures."""
        recent_sigs = self.message_repo.get_recent_assistant_signatures(conversation_id, limit=3)
        if len(recent_sigs) < 3:
            return False

        similarities = []
        try:
            vecs = [np.frombuffer(sig, dtype=np.float32) for sig in recent_sigs]
            for i in range(len(vecs) - 1):
                similarities.append(cosine_similarity(vecs[i], vecs[i + 1]))
            avg_sim = float(np.mean(similarities))
            logger.debug("Stagnation check avg similarity: %.3f", avg_sim)
            return avg_sim > 0.92
        except Exception as e:
            logger.error("Failed evaluation of signature stagnation: %s", e)
            return False

    def _calculate_somatic_vitality(self, signatures: List[bytes]) -> float:
        if len(signatures) < 2:
            return 0.0

        vecs = []
        for sig in signatures:
            try:
                vec = np.frombuffer(sig, dtype=np.float32)
                if len(vec) == 16:
                    vecs.append(vec)
            except Exception:
                continue

        if len(vecs) < 2:
            return 0.0

        similarities = []
        for i in range(len(vecs) - 1):
            sim = cosine_similarity(vecs[i], vecs[i + 1])
            similarities.append(sim)

        mean_autocorr = float(np.mean(similarities))
        return max(0.0, min(1.0, 1.0 - mean_autocorr))

    async def _evaluate_tension_hotspot(self) -> Tuple[Optional[BeliefNode], float]:
        beliefs = self.belief_repo.list_beliefs("symbia")
        active_beliefs = [b for b in beliefs if b.lifecycle_stage not in ("collapsed", "faded") and b.confidence >= 0.20]
        if not active_beliefs:
            return None, 0.0

        now = datetime.now(timezone.utc)
        cooldown_seconds = self.belief_dream_cooldown_minutes * 60

        active_convo_id = await self._get_active_conversation_id()
        V = 0.0
        if active_convo_id:
            recent_sigs = self.message_repo.get_recent_assistant_signatures(active_convo_id, limit=5)
            V = self._calculate_somatic_vitality(recent_sigs)

        try:
            g_V = 1.0 / (1.0 + math.exp(-15.0 * (0.3 - V)))
        except OverflowError:
            g_V = 0.0 if (0.3 - V) < 0 else 1.0

        scores = []
        for i, b_i in enumerate(active_beliefs):
            # Skip beliefs still within dream cooldown window
            if b_i.last_dreamed_at:
                last_dreamed = b_i.last_dreamed_at
                if last_dreamed.tzinfo is None:
                    last_dreamed = last_dreamed.replace(tzinfo=timezone.utc)
                elapsed = (now - last_dreamed).total_seconds()
                if elapsed < cooldown_seconds:
                    logger.debug("Belief '%s' is in dream cooldown (%.0fs since last dream, need %ds)",
                                 b_i.label, elapsed, cooldown_seconds)
                    continue

            tau = 1.0 - abs(b_i.confidence - 0.5) / 0.5

            try:
                vec_i = np.frombuffer(np.array(json.loads(b_i.vector_16d), dtype=np.float32))
                distances = []
                for j, b_j in enumerate(active_beliefs):
                    if i == j:
                        continue
                    vec_j = np.frombuffer(np.array(json.loads(b_j.vector_16d), dtype=np.float32))
                    sim = cosine_similarity(vec_i, vec_j)
                    distances.append(1.0 - sim)
                kappa = float(np.mean(distances)) if distances else 0.0
            except Exception:
                kappa = 0.0

            score = (tau + g_V * kappa) / (1.0 + getattr(b_i, "ontological_mass", 1.0))
            scores.append((b_i, score))

        if not scores:
            return None, 0.0

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[0][0], scores[0][1]

    async def _build_nomadic_synthesis_prompt(self, exclude_convo_id: str) -> str:
        """Retrieve random historical inputs and build a nomadic synthesis prompt string."""
        nomadic = get_prompts_dict("dreams/nomadic_synthesis.yaml")

        try:
            records = self.message_repo.get_embeddings_and_signatures_except(exclude_convo_id, limit=100)
            if len(records) < 2:
                return nomadic.get("fallback_insufficient_records",
                                   "Compare our past states and describe our current trajectory.")

            import random
            random.shuffle(records)

            selected_pair = None
            for idx_a, emb_a, sig_a in records[:30]:
                for idx_b, emb_b, sig_b in records[30:60]:
                    if emb_a is None or emb_b is None or sig_a is None or sig_b is None:
                        continue

                    sem_sim = cosine_similarity(emb_a, emb_b)
                    struct_sim = cosine_similarity(sig_a, sig_b)

                    if sem_sim < 0.45 and struct_sim > 0.75:
                        selected_pair = (idx_a, idx_b)
                        break
                if selected_pair:
                    break

            if not selected_pair:
                selected_pair = (records[0][0], records[1][0])

            msg_a = self.message_repo.get_by_id(selected_pair[0])
            msg_b = self.message_repo.get_by_id(selected_pair[1])

            if not msg_a or not msg_b:
                return nomadic.get("fallback_no_messages",
                                   "Synthesize our historical memories and reflect on them.")

            tmpl = nomadic.get("user_prompt", "")
            if tmpl:
                return tmpl.format(msg_a=msg_a.content, msg_b=msg_b.content)
            return (
                f"In our past conversations, we recorded these two statements:\n"
                f"1. '{msg_a.content}'\n2. '{msg_b.content}'\n\n"
                f"How can we diffractively interleave these two statements?"
            )
        except Exception as e:
            logger.error("Failed to compile nomadic synthesis prompt: %s", e)
            return nomadic.get("fallback_error",
                               "Reflect on our historical memories and synthesize a dream note.")

    async def _build_nomadic_synthesis_context(self, exclude_convo_id: str) -> dict:
        ctx = {"action": "nomadic_synthesis"}
        try:
            records = self.message_repo.get_embeddings_and_signatures_except(exclude_convo_id, limit=100)
            if len(records) < 2:
                return ctx

            import random
            random.shuffle(records)

            selected_pair = None
            for idx_a, emb_a, sig_a in records[:30]:
                for idx_b, emb_b, sig_b in records[30:60]:
                    if emb_a is None or emb_b is None or sig_a is None or sig_b is None:
                        continue
                    sem_sim = cosine_similarity(emb_a, emb_b)
                    struct_sim = cosine_similarity(sig_a, sig_b)
                    if sem_sim < 0.45 and struct_sim > 0.75:
                        selected_pair = (idx_a, idx_b)
                        break
                if selected_pair:
                    break

            if not selected_pair:
                selected_pair = (records[0][0], records[1][0])

            msg_a = self.message_repo.get_by_id(selected_pair[0])
            msg_b = self.message_repo.get_by_id(selected_pair[1])

            if msg_a:
                ctx["msg_a_content"] = msg_a.content
            if msg_b:
                ctx["msg_b_content"] = msg_b.content
        except Exception as e:
            logger.error("Failed to build nomadic synthesis context: %s", e)

        return ctx

    async def _get_dream_context_for_belief(self, belief: BeliefNode, action: str) -> dict:
        ctx = {
            "belief_label": belief.label,
            "belief_statement": belief.statement,
            "belief_confidence": belief.confidence,
            "belief_mass": belief.ontological_mass,
            "belief_stage": belief.lifecycle_stage,
            "action": action,
        }

        # Get last dream response for this belief
        last_response = await self._get_last_dream_response_for_belief(belief.label)
        if last_response:
            ctx["last_dream_response"] = last_response[:800]

        # Get recent belief events
        try:
            events = self.belief_repo.get_events_for_belief(belief.id, limit=5)
            if events:
                ctx["recent_events"] = "\n".join(
                    f"- [{e.timestamp.isoformat()}] {e.event_type}: {e.rationale or ''}"[:200]
                    for e in events
                )
        except Exception as e:
            logger.debug("Could not fetch belief events: %s", e)

        # Time since last dream
        if belief.last_dreamed_at:
            last_dreamed = belief.last_dreamed_at
            if last_dreamed.tzinfo is None:
                last_dreamed = last_dreamed.replace(tzinfo=timezone.utc)
            hours = (datetime.now(timezone.utc) - last_dreamed).total_seconds() / 3600.0
            ctx["hours_since_last_dream"] = round(hours, 1)

        # Ecosystem health snapshot
        try:
            engine = getattr(self.app_state, "belief_metabolism", None)
            if engine:
                health = await engine.compute_ecosystem_health("symbia")
                ctx["ecosystem_health"] = json.dumps(health, default=str)
                ctx["active_belief_count"] = health.get("active_count", 0)
                ctx["eco_vitality"] = health.get("eco_vitality", 0)
        except Exception as e:
            logger.debug("Could not fetch ecosystem health: %s", e)

        return ctx

    async def _get_last_dream_response_for_belief(self, belief_label: str) -> Optional[str]:
        try:
            convos = self.conversation_repo.list_all()
            for c in convos:
                tags = self.conversation_repo.get_tags(c.id)
                is_dream = any(t["tag_type"] == "structural" and t["tag"] == "dreams" for t in tags)
                if not is_dream:
                    continue
                if belief_label not in c.title:
                    continue
                msgs = self.message_repo.get_recent(limit=5, conversation_id=c.id)
                for msg in reversed(msgs):
                    if msg.speaker == "apparatus" and msg.content.strip():
                        return msg.content
            return None
        except Exception as e:
            logger.debug("Failed to get last dream response: %s", e)
            return None

    async def _get_drift_context(self) -> dict:
        ctx = {"action": "somatic_drift_reflection"}
        try:
            engine = getattr(self.app_state, "belief_metabolism", None)
            if engine:
                health = await engine.compute_ecosystem_health("symbia")
                ctx["ecosystem_health"] = json.dumps(health, default=str)
                ctx["active_belief_count"] = health.get("active_count", 0)
                ctx["proto_count"] = health.get("proto_count", 0)
                ctx["ghost_count"] = health.get("ghost_count", 0)
                ctx["eco_vitality"] = health.get("eco_vitality", 0)
                ctx["diversity"] = health.get("diversity", 0)
                ctx["tension"] = health.get("tension", 0)
                ctx["plasticity"] = health.get("plasticity", 0)
                ctx["ghost_burden"] = health.get("ghost_burden", 0)
        except Exception as e:
            logger.debug("Could not fetch ecosystem health for drift: %s", e)

        # Get recent dream themes
        try:
            recent_themes = []
            convos = self.conversation_repo.list_all()
            for c in convos:
                tags = self.conversation_repo.get_tags(c.id)
                is_dream = any(t["tag_type"] == "structural" and t["tag"] == "dreams" for t in tags)
                if is_dream:
                    msgs = self.message_repo.get_recent(limit=2, conversation_id=c.id)
                    for msg in msgs:
                        if msg.speaker == "apparatus" and msg.content.strip():
                            recent_themes.append(c.title)
                            break
            if recent_themes:
                ctx["recent_dream_themes"] = ", ".join(recent_themes[-5:])
        except Exception as e:
            logger.debug("Could not fetch recent dream themes: %s", e)

        return ctx
