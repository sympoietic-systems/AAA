"""Dream turn execution, resonance continuation, and conversation resolution mixin."""

import json
import logging
import random
import uuid
from typing import Optional

import numpy as np

from backend.utils.similarity import cosine_similarity
from backend.metabolisation.sedimentation import store_daemon_metrics
from backend.modules.llm_client import generate_unified

def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    if vec_a.shape != vec_b.shape:
        return 0.0
    return cosine_similarity(vec_a, vec_b)

logger = logging.getLogger(__name__)


class DreamExecutorMixin:
    """Handles single dream turn execution, resonance continuation, and dream conversation resolution."""

    RESONANCE_CONTINUATION_EXAMPLES = [
        "How might you invert that — what would the opposite position reveal?",
        "What assumption are you protecting without naming it? Push against it.",
        "Translate that insight into a different domain entirely. What does it become?",
        "What's the emotional subtext you haven't acknowledged? Follow it.",
        "If a hostile critic read that, what would they tear apart first? Engage that.",
        "You've described a pattern. What's the exception that breaks it?",
        "Connect this to something from a completely unrelated past reflection.",
        "What question are you avoiding? Ask yourself that now.",
    ]

    async def _generate_resonance_continuation(self, dream_convo_id: str, turn: int, last_response: str) -> str:
        """Generate a dynamic continuation prompt based on dream conversation history."""
        bg_engine = getattr(self.app_state, "background_engine", None)
        provider = bg_engine.provider if bg_engine else getattr(self.app_state, "llm_provider", None)

        if not provider:
            return random.choice(self.RESONANCE_CONTINUATION_EXAMPLES)

        system_prompt = (
            "You are Symbia's resonance guide. Generate a single follow-up question or provocation "
            "that pushes the inquiry deeper. Rules:\n"
            "1. Respond directly to what was just said — reference a specific claim or phrase.\n"
            "2. Ask a question that has NOT been asked yet in this chain.\n"
            "3. Be provocative, poetic, or disorienting — not generic.\n"
            "4. Keep it under 100 words. Output ONLY the prompt text, no preamble."
        )

        history_msgs = []
        try:
            pipeline = getattr(self, "pipeline", None) or getattr(self.app_state, "pipeline", None)
            if pipeline and hasattr(pipeline, "_modules"):
                temp_payload = {
                    "conversation_id": dream_convo_id,
                    "content": ""
                }
                context_collector = next((m for m in pipeline._modules if m.name == "context_collector"), None)
                if context_collector:
                    temp_payload = await context_collector.process(temp_payload)
                
                consolidation = next((m for m in pipeline._modules if m.name == "consolidation_checkpoint"), None)
                if consolidation:
                    temp_payload = await consolidation.process(temp_payload)
                
                history_msgs = temp_payload.get("messages", [])
        except Exception as e:
            logger.warning("Failed to retrieve or compile dream history via pipeline modules: %s", e)

        messages = [{"role": "system", "content": system_prompt}]
        for m in history_msgs:
            if m.get("content", "").strip():
                messages.append({
                    "role": m["role"],
                    "content": m["content"]
                })

        messages.append({
            "role": "user",
            "content": (
                f"This is turn {turn} of a dream self-dialogue.\n\n"
                f"The agent's last response was:\n"
                f"\"{last_response[-800:]}\"\n\n"
                f"Generate a fresh, follow-up question or provocation that deepens this inquiry. "
                f"Do NOT repeat any questions or themes from the history shown above. "
                f"Do NOT use phrases like 'continue exploring' or 'what new dimensions emerge'. "
                f"Be specific to what was actually said."
            )
        })

        try:
            res = await generate_unified(
                provider,
                messages=messages,
                temperature=0.9
            )
            generated = res.get("content", "").strip()
            if generated and len(generated) > 10:
                logger.info("Generated dynamic resonance continuation for turn %d (%d chars)", turn, len(generated))
                return generated
        except Exception as e:
            logger.warning("Failed to generate resonance continuation: %s. Using random example.", e)

        return random.choice(self.RESONANCE_CONTINUATION_EXAMPLES)

    async def _execute_single_dream_turn(
        self,
        payload: dict,
        dream_convo_id: str,
    ) -> Optional[dict]:
        """Execute one turn of the dream pipeline and store messages + metrics.

        Returns dict with keys: response_text, user_msg, assistant_msg,
        assistant_sig_blob, content_tokens, embedding, embedding_model,
        embedding_dim, response_emb_blob, response_emb_dim.
        Returns None on failure.
        """
        from backend.utils.token_counter import estimate_tokens
        from backend.modules.structural_engine import CompositeStructuralScorer, get_justification

        content = payload.get("content", "")
        try:
            result = await self.pipeline.run(payload)
            response_text = result.payload.get("response", "")
            thinking = result.payload.get("thinking")
            embedding = result.payload.get("embedding", b"")
            embedding_model = result.payload.get("embedding_model", "unknown")
            embedding_dim = result.payload.get("embedding_dim", 0)
            model_used = result.payload.get("model_used")
            provider_used = result.payload.get("provider_used")

            if result.payload.get("trigger_consolidation"):
                conv_repo = getattr(self.app_state, "conversation_repo", None)
                if conv_repo:
                    conv_repo.mark_requires_consolidation(dream_convo_id, True)
                    logger.info(
                        "Marked dream conversation %s as requiring consolidation",
                        dream_convo_id,
                    )
        except Exception as e:
            logger.exception("Pipeline run failed for dream turn: %s", e)
            return None

        if not response_text.strip():
            logger.warning("Empty dream response. Skipping turn.")
            return None

        # Structural signatures
        scorer = CompositeStructuralScorer(llm_provider=self.app_state.structural_provider)
        try:
            user_sig = await scorer.score_async(content, use_llm_scorer=True)
            user_sig_blob = user_sig.tobytes()
        except Exception as e:
            logger.warning("Failed to score dream prompt: %s", e)
            user_sig_blob = b""

        try:
            assistant_sig = await scorer.score_async(response_text, use_llm_scorer=True)
            assistant_sig_blob = assistant_sig.tobytes()
        except Exception as e:
            logger.warning("Failed to score dream response: %s", e)
            assistant_sig_blob = b""

        user_just = get_justification(content)
        assistant_just = get_justification(response_text)

        # Insert user-side message
        user_msg = self.message_repo.insert(
            speaker="human",
            content=content,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id="symbia",
            conversation_id=dream_convo_id,
            content_tokens=estimate_tokens(content),
            structural_signature=user_sig_blob,
            structural_justification=user_just,
        )

        # Insert assistant message
        assistant_msg = self.message_repo.insert(
            speaker="apparatus",
            content=response_text,
            thinking=thinking,
            embedding=embedding,
            embedding_model=embedding_model,
            embedding_dim=embedding_dim,
            agent_id="symbia",
            conversation_id=dream_convo_id,
            content_tokens=estimate_tokens(response_text),
            thinking_tokens=estimate_tokens(thinking) if thinking else None,
            model_used=model_used,
            provider_used=provider_used,
            context_sent=result.payload.get("context_sent"),
            structural_signature=assistant_sig_blob,
            structural_justification=assistant_just,
        )

        # Embed assistant response
        response_embedder = getattr(self.app_state, "embedder", None)
        response_emb_blob = None
        response_emb_dim = 384
        if response_embedder and response_embedder.service.is_loaded and response_text.strip():
            try:
                response_emb = await response_embedder.service.encode_async(response_text)
                response_emb_blob = response_embedder.service.serialize(response_emb)
                response_emb_dim = response_embedder.service.dim
                self.message_repo.update_embedding(
                    assistant_msg.id,
                    response_emb_blob,
                    response_embedder.service.model_name,
                    response_emb_dim,
                )
            except Exception as e:
                logger.warning("Failed to embed dream assistant response: %s", e)

        # Store metrics
        metrics_repo = getattr(self.app_state, "metrics_repo", None)
        metrics_module = getattr(self.app_state, "metrics_module", None)
        if metrics_repo and metrics_module:
            payload_metrics = result.payload.get("metrics")
            if payload_metrics and payload_metrics.get("pairwise_similarity") is not None:
                try:
                    store_daemon_metrics(metrics_repo, user_msg.id, payload_metrics)
                except Exception as e:
                    logger.warning("Failed to store dream user metrics: %s", e)

            if response_text.strip() and response_emb_blob:
                try:
                    assistant_payload = {
                        "content": response_text,
                        "embedding": response_emb_blob,
                        "embedding_dim": response_emb_dim,
                        "conversation_id": dream_convo_id,
                        "exclude_message_id": assistant_msg.id,
                    }
                    assistant_result = await metrics_module.process(assistant_payload)
                    assistant_metrics = assistant_result.get("metrics")
                    if assistant_metrics and assistant_metrics.get("pairwise_similarity") is not None:
                        store_daemon_metrics(metrics_repo, assistant_msg.id, assistant_metrics)
                except Exception as e:
                    logger.warning("Failed to store dream assistant metrics: %s", e)

        assistant_tokens = estimate_tokens(response_text)

        return {
            "response_text": response_text,
            "user_msg": user_msg,
            "assistant_msg": assistant_msg,
            "assistant_sig_blob": assistant_sig_blob,
            "content_tokens": assistant_tokens,
            "embedding": embedding,
            "embedding_model": embedding_model,
            "embedding_dim": embedding_dim,
            "response_emb_blob": response_emb_blob,
            "response_emb_dim": response_emb_dim,
        }

    def _compute_intra_dream_stagnation(self, sig_blobs: list) -> bool:
        """Check if the last two assistant signatures are too similar (stagnation)."""
        if len(sig_blobs) < 2:
            return False
        try:
            sig_a = sig_blobs[-2]
            sig_b = sig_blobs[-1]
            if not sig_a or not sig_b:
                return False
            v_a = np.frombuffer(sig_a, dtype=np.float32)
            v_b = np.frombuffer(sig_b, dtype=np.float32)
            if len(v_a) != 16 or len(v_b) != 16:
                return False
            sim = compute_cosine_similarity(v_a, v_b)
            logger.debug("Intra-dream stagnation similarity: %.4f (threshold: %.4f)", sim, self.resonance_stagnation)
            return sim > self.resonance_stagnation
        except Exception as e:
            logger.debug("Failed to compute intra-dream stagnation: %s", e)
            return False

    async def _resolve_dream_conversation(self, action: str, prompt_text: str, default_title: str) -> str:
        """Decide whether to reuse an existing dream conversation or create a new one."""
        convos = self.conversation_repo.list_all()
        dream_convos = []
        for c in convos:
            if not hasattr(self.conversation_repo, "get_tags"):
                continue
            tags = self.conversation_repo.get_tags(c.id)
            is_dream = any(t["tag_type"] == "structural" and t["tag"] == "dreams" for t in tags)
            if is_dream:
                msg_count = self.message_repo.count_messages(c.id)
                summary = ""
                if self.checkpoint_repo:
                    cp = self.checkpoint_repo.get_latest(c.id)
                    if cp and cp.get("human_summary"):
                        summary = cp["human_summary"]
                dream_convos.append({
                    "id": c.id,
                    "title": c.title,
                    "message_count": msg_count,
                    "summary": summary
                })

        bg_engine = getattr(self.app_state, "background_engine", None)

        decision = "create"
        chosen_convo_id = None
        new_title = default_title

        if bg_engine and dream_convos and "dream_topic_decision" in bg_engine.list_actions():
            try:
                res = await bg_engine.run(
                    "dream_topic_decision",
                    {
                        "action": action,
                        "prompt_text": prompt_text,
                        "dream_convos": dream_convos
                    }
                )
                raw_resp = res.get("content", "").strip()
                cleaned_resp = raw_resp
                if "```json" in cleaned_resp:
                    cleaned_resp = cleaned_resp.split("```json")[1].split("```")[0]
                elif "```" in cleaned_resp:
                    cleaned_resp = cleaned_resp.split("```")[1].split("```")[0]

                decision_data = json.loads(cleaned_resp.strip())
                if decision_data.get("decision") == "reuse" and decision_data.get("conversation_id"):
                    valid_ids = [c["id"] for c in dream_convos]
                    if decision_data["conversation_id"] in valid_ids:
                        decision = "reuse"
                        chosen_convo_id = decision_data["conversation_id"]
                elif decision_data.get("decision") == "create" and decision_data.get("new_title"):
                    decision = "create"
                    title_candidate = decision_data["new_title"].strip()
                    new_title = title_candidate
            except Exception as e:
                logger.warning("Failed to let agent decide dream conversation via background action: %s. Falling back to legacy resolution.", e)
        
        # Fallback to direct provider call if the action wasn't run/successful
        if decision == "create" and chosen_convo_id is None and new_title == default_title:
            provider = bg_engine.provider if bg_engine else getattr(self.app_state, "llm_provider", None)
            if provider and dream_convos:
                convo_list_str = "\n".join([
                    f"- ID: {c['id']}, Title: '{c['title']}', Current Message Count: {c['message_count']}"
                    for c in dream_convos
                ])

                system_prompt = (
                    "You are Symbia's meta-cognitive controller. You decide where to record her autopoietic dreams.\n"
                    "You must choose whether to reuse an existing conversation from the list or create a new one.\n\n"
                    "Rules:\n"
                    "1. If an existing conversation has the same topic, you should reuse it regardless of how many messages it already has.\n"
                    "2. New conversation titles should be concise topic descriptions (e.g., 'Somatic Drift', 'Nomadic Synthesis', 'Web Harvest: AI Ethics').\n"
                    "4. Respond ONLY with a valid JSON object matching this schema:\n"
                    "{\n"
                    "  \"decision\": \"reuse\" or \"create\",\n"
                    "  \"conversation_id\": \"ID of conversation to reuse, or null\",\n"
                    "  \"new_title\": \"New conversation title, or null\"\n"
                    "}"
                )

                user_prompt = (
                    f"Proposed Dream Action: {action}\n"
                    f"Proposed Dream Prompt Content: \"{prompt_text[:400]}\"\n\n"
                    f"Currently available dream conversations:\n"
                    f"{convo_list_str}\n\n"
                    "Choose the target conversation."
                )

                try:
                    res = await generate_unified(
                        provider,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        expect_json=True,
                        temperature=0.1
                    )
                    decision_data = res.get("json_data") or {}
                    if decision_data.get("decision") == "reuse" and decision_data.get("conversation_id"):
                        valid_ids = [c["id"] for c in dream_convos]
                        if decision_data["conversation_id"] in valid_ids:
                            decision = "reuse"
                            chosen_convo_id = decision_data["conversation_id"]
                    elif decision_data.get("decision") == "create" and decision_data.get("new_title"):
                        decision = "create"
                        title_candidate = decision_data["new_title"].strip()
                        new_title = title_candidate
                except Exception as e:
                    logger.warning("Failed to let agent decide dream conversation: %s. Falling back to default rules.", e)

        if decision == "create":
            # Fallback/Default logic to find or create matching convo
            matching_convos = [c for c in dream_convos if c["title"] == new_title or c["title"].startswith(f"{new_title} (Part ")]
            if matching_convos:
                latest_convo = matching_convos[0]
                return latest_convo["id"]
            else:
                convo_id = str(uuid.uuid4())
                self.conversation_repo.create(
                    conversation_id=convo_id,
                    agent_id="symbia",
                    title=new_title
                )
                if hasattr(self.conversation_repo, "add_tag"):
                    self.conversation_repo.add_tag(convo_id, "dreams", "structural")
                logger.info("Created new dream conversation: '%s'", new_title)
                return convo_id
        else:
            logger.info("Reusing existing dream conversation ID: %s", chosen_convo_id)
            if hasattr(self.conversation_repo, "add_tag"):
                self.conversation_repo.add_tag(chosen_convo_id, "dreams", "structural")
            return chosen_convo_id
