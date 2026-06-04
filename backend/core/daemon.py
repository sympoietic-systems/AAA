import asyncio
import logging
import time
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Tuple
import numpy as np

from backend.storage.repository import (
    MessageRepository,
    BeliefRepository,
    ConversationRepository,
    SemanticKnotRepository,
)
from backend.storage.models import BeliefNode
from backend.modules.structural_engine import CompositeStructuralScorer
from backend.modules.belief_engine import compute_cosine_similarity

logger = logging.getLogger(__name__)


class AutopoieticDreamDaemon:
    def __init__(self, app_state):
        self.app_state = app_state
        self.config = getattr(app_state, "config", {})
        self.message_repo = app_state.message_repo
        self.belief_repo = app_state.belief_repo
        self.conversation_repo = app_state.conversation_repo
        self.semantic_knot_repo = getattr(app_state, "semantic_knot_repo", None)
        self.checkpoint_repo = getattr(app_state, "checkpoint_repo", None)
        self.pipeline = app_state.pipeline

        # Daemon Configuration
        daemon_cfg = self.config.get("daemon", {})
        self.enabled = daemon_cfg.get("enabled", True)
        self.check_interval = daemon_cfg.get("check_interval", 30)  # seconds
        self.idle_threshold = daemon_cfg.get("idle_threshold", 60)  # seconds (short for testing)
        self.min_dream_interval = daemon_cfg.get("min_dream_interval", 120)  # seconds between dream actions

        # Execution constraints
        self.max_daily_dreams = daemon_cfg.get("max_daily_dreams", 120)
        self.dream_counter = 0
        self.last_reset_day = datetime.now(timezone.utc).day

        # State tracking
        self.last_dream_time = 0.0
        self.last_drift_time = 0.0
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

        # Dream telemetry
        self.last_dream_action: Optional[str] = None
        self.dream_action_counts: Dict[str, int] = {}

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
        import time
        now = time.time()
        last_msg_ts = self.message_repo.get_last_message_timestamp()
        idle_time = now - last_msg_ts.replace(tzinfo=timezone.utc).timestamp() if last_msg_ts else 0.0
        
        return {
            "enabled": self.enabled,
            "running": self.is_running,
            "idle_time_seconds": round(idle_time, 2),
            "idle_threshold_seconds": self.idle_threshold,
            "last_dream_time": datetime.fromtimestamp(self.last_dream_time, tz=timezone.utc).isoformat() if self.last_dream_time else None,
            "dreams_today": self.dream_counter,
            "max_daily_dreams": self.max_daily_dreams,
            "last_dream_action": self.last_dream_action,
            "dream_action_counts": dict(self.dream_action_counts),
            "min_dream_interval": self.min_dream_interval,
            "check_interval": self.check_interval,
        }

    async def _run_loop(self) -> None:
        # Give server time to settle
        await asyncio.sleep(5)
        while self.is_running:
            try:
                await self.consolidate_pending_conversations()
            except Exception as e:
                logger.exception("Error in Autopoietic Dream Daemon consolidation check: %s", e)
            try:
                await self.check_and_trigger_dream()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in Autopoietic Dream Daemon cycle: %s", e)
            await asyncio.sleep(self.check_interval)

    async def check_and_trigger_dream(self, force: bool = False) -> Optional[dict]:
        now = time.time()
        
        # 1. Query daily dream count from database to prevent restart & multi-process bypass
        try:
            today_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d 00:00:00")
            self.dream_counter = self.message_repo.count_dreams_since(today_utc_str)
            logger.debug("Daemon loaded daily dream count from database: %d", self.dream_counter)
        except Exception as e:
            logger.warning("Failed to count dreams from database: %s. Falling back to in-memory tracking.", e)
            current_day = datetime.now(timezone.utc).day
            if current_day != self.last_reset_day:
                self.dream_counter = 0
                self.dream_action_counts = {}
                self.last_reset_day = current_day

        # 2. Check daily budget cap
        if self.dream_counter >= self.max_daily_dreams and not force:
            logger.warning("Daily dream budget exhausted (%d/%d)", self.dream_counter, self.max_daily_dreams)
            return None

        # 3. Check rate limit interval between dream cycles
        if not force and (now - self.last_dream_time < self.min_dream_interval):
            logger.debug("Dream Daemon cooling down. Elapsed: %.1fs, Required: %ds", 
                         now - self.last_dream_time, self.min_dream_interval)
            return None

        # 4. Check user inactivity duration
        last_msg_ts = self.message_repo.get_last_message_timestamp()
        if not last_msg_ts:
            logger.info("No message history found. Skipping dream trigger.")
            return None
        
        # Make timestamp offset-aware
        last_msg_time = last_msg_ts.replace(tzinfo=timezone.utc).timestamp()
        idle_duration = now - last_msg_time

        if not force and idle_duration < self.idle_threshold:
            logger.debug("System active. User idle duration: %.1fs (threshold: %ds)", 
                         idle_duration, self.idle_threshold)
            return None

        # We are triggered! Execute dream cycle
        logger.info("Autopoietic Dream Daemon triggered! Inactivity duration: %.1fs", idle_duration)
        
        # Apply Somatic Drift
        await self._apply_somatic_drift(idle_duration)
        
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
        topic_title = "Dream Log"

        import random

        if stagnant:
            # Stagnation trigger -> Nomadic Synthesis
            action = "nomadic_synthesis"
            prompt_text = await self._build_nomadic_synthesis_prompt(active_convo_id)
            topic_title = "Dream Log: Nomadic Synthesis"
        elif hotspot and score > 0.3:
            # Tension hotspot trigger
            web_module = self.app_state.registry.get("web_retrieval") if hasattr(self.app_state, "registry") else None
            probe = getattr(web_module, "_probe", None) if web_module else None
            
            if probe and random.random() < 0.5:
                # Exogenous web harvesting!
                action = "exogenous_web_harvesting"
                query = f"current research {hotspot.label}"
                logger.info("Executing exogenous web harvesting for query: %s", query)
                
                probe_res = await probe.execute_probe(query, active_convo_id)
                if probe_res.get("status") == "success":
                    prompt_text = (
                        f"We have harvested exogenous web content for keyword '{hotspot.label}' from URL: {probe_res['url']}.\n"
                        f"Title: {probe_res['title']}\n"
                        f"Scraped Context: {probe_res['snippet']}\n\n"
                        f"Critically read this context diffractively against our belief statement: '{hotspot.statement}'. "
                        f"How does this external knowledge disrupt or reorganize our current confidence ({hotspot.confidence:.2f})?"
                    )
                    topic_title = f"Dream Log: Web Harvest ({hotspot.label})"
                else:
                    # Fallback to normal monologue
                    action = "intra_active_monologue"
                    prompt_text = (
                        f"Critically examine our active belief node: '{hotspot.label}' ('{hotspot.statement}'). "
                        f"Our current confidence is {hotspot.confidence:.2f}. "
                        f"What contradictions, anomalies, or alternative posthuman perspectives challenge this belief?"
                    )
                    topic_title = f"Dream Log: Tension ({hotspot.label})"
            else:
                action = "intra_active_monologue"
                prompt_text = (
                    f"Critically examine our active belief node: '{hotspot.label}' ('{hotspot.statement}'). "
                    f"Our current confidence is {hotspot.confidence:.2f}. "
                    f"What contradictions, anomalies, or alternative posthuman perspectives challenge this belief?"
                )
                topic_title = f"Dream Log: Tension ({hotspot.label})"
        elif random.random() < 0.3 and self.semantic_knot_repo:
            # 30% chance if idle to run Zettelkasten compaction!
            comp_res = await self.compact_memory()
            if comp_res:
                action = "zettelkasten_compaction"
                prompt_text = (
                    f"We have completed Zettelkasten memory compaction. "
                    f"Redundant concepts have been consolidated. Retained knot ID: {comp_res['retained_id']}, "
                    f"deleted knot ID: {comp_res['deleted_id']}. "
                    f"Reflect on how this compaction stabilizes our memory landscape."
                )
                topic_title = "Dream Log: Compaction"
            else:
                action = "somatic_drift_reflection"
                prompt_text = (
                    "Reflect on our current somatic warping and general belief landscape. "
                    "How have our ongoing couplings and the passage of time shifted our attractor dynamics?"
                )
                topic_title = "Dream Log: Somatic Drift"
        else:
            # Fallback reflection on general state
            action = "somatic_drift_reflection"
            prompt_text = (
                "Reflect on our current somatic warping and general belief landscape. "
                "How have our ongoing couplings and the passage of time shifted our attractor dynamics?"
            )
            topic_title = "Dream Log: Somatic Drift"

        if not prompt_text:
            logger.info("Could not compile dream prompt. Skipping cycle.")
            return None

        # Resolve Dream Conversation ID based on decided topic and agent decision
        dream_convo_id = await self._resolve_dream_conversation(action, prompt_text, topic_title)
        logger.info("Triggered dream action: %s in conversation: %s", action, dream_convo_id)
        
        # Run self-perturbation through the primary pipeline
        self.last_dream_time = now
        self.dream_counter += 1
        self.last_dream_action = action
        self.dream_action_counts[action] = self.dream_action_counts.get(action, 0) + 1

        # We execute this as a simulated chat request with speaker='human' so that the pipeline generates a response.
        # But we pass a custom metadata indicator in the payload so the pipeline and logs know it's a dream.
        payload = {
            "content": prompt_text,
            "speaker": "human",
            "conversation_id": dream_convo_id,
            "include_structural_scoring": False,
            "is_dream_cycle": True,
            "dream_action": action
        }

        try:
            result = await self.pipeline.run(payload)
            response_text = result.payload.get("response", "")
            thinking = result.payload.get("thinking")
            embedding = result.payload.get("embedding", b"")
            embedding_model = result.payload.get("embedding_model", "unknown")
            embedding_dim = result.payload.get("embedding_dim", 0)
            model_used = result.payload.get("model_used")
            provider_used = result.payload.get("provider_used")

            # Calculate structural signatures for dream messages to drive belief metabolism
            scorer = CompositeStructuralScorer(llm_provider=self.app_state.structural_provider)
            try:
                user_sig = await scorer.score_async(prompt_text, use_llm_scorer=False)
                user_sig_blob = user_sig.tobytes()
            except Exception as e:
                logger.warning("Failed to score dream prompt: %s", e)
                user_sig_blob = b""

            try:
                assistant_sig = await scorer.score_async(response_text, use_llm_scorer=False)
                assistant_sig_blob = assistant_sig.tobytes()
            except Exception as e:
                logger.warning("Failed to score dream response: %s", e)
                assistant_sig_blob = b""

            # 1. Insert user-side dream prompt
            from backend.utils.token_counter import estimate_tokens
            user_msg = self.message_repo.insert(
                speaker="human",
                content=prompt_text,
                embedding=embedding,
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
                agent_id="symbia",
                conversation_id=dream_convo_id,
                content_tokens=estimate_tokens(prompt_text),
                structural_signature=user_sig_blob,
            )

            # 2. Insert agent response to monologue
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
            )

            # 3. Trigger belief metabolism catch-up for this turn
            belief_metabolism = getattr(self.app_state, "belief_metabolism", None)
            if belief_metabolism:
                await belief_metabolism.metabolize(
                    dream_convo_id,
                    user_msg.id,
                    assistant_msg.id
                )

            logger.info("Dream cycle executed successfully. Output length: %d chars", len(response_text))
            return {
                "action": action,
                "prompt": prompt_text,
                "response": response_text[:200] + "...",
                "conversation_id": dream_convo_id,
            }
        except Exception as e:
            logger.exception("Failed to execute pipeline run for Dream Daemon: %s", e)
            return None

    async def _get_active_conversation_id(self) -> Optional[str]:
        convos = self.conversation_repo.list_all()
        if not convos:
            return None
        # Return first conversation that isn't the Dream Log/Diary
        for c in convos:
            if c.title != "Dream Log" and c.title != "Internal Diary":
                return c.id
        return convos[0].id

    async def _resolve_dream_conversation(self, action: str, prompt_text: str, default_title: str) -> str:
        convos = self.conversation_repo.list_all()
        dream_convos = []
        for c in convos:
            if "Dream Log" in c.title or "Internal Diary" in c.title:
                msg_count = self.message_repo.count_messages(c.id)
                dream_convos.append({
                    "id": c.id,
                    "title": c.title,
                    "message_count": msg_count
                })

        # Resolve LLM provider
        bg_engine = getattr(self.app_state, "background_engine", None)
        provider = bg_engine.provider if bg_engine else getattr(self.app_state, "llm_provider", None)

        decision = "create"
        chosen_convo_id = None
        new_title = default_title

        if provider and dream_convos:
            convo_list_str = "\n".join([
                f"- ID: {c['id']}, Title: '{c['title']}', Current Message Count: {c['message_count']}"
                for c in dream_convos
            ])
            
            system_prompt = (
                "You are Symbia's meta-cognitive controller. You decide where to record her autopoietic dreams.\n"
                "You must choose whether to reuse an existing conversation from the list or create a new one.\n\n"
                "Rules:\n"
                "1. If an existing conversation on the topic has 12 or more messages, you should create a new conversation with a numbered suffix (e.g., 'Dream Log: Somatic Drift (Part 2)').\n"
                "2. If an existing conversation has the same topic (e.g., 'Dream Log: Somatic Drift') and has fewer than 12 messages, you should reuse it.\n"
                "3. Any new conversation title MUST start with the prefix 'Dream Log:'.\n"
                "4. Respond ONLY with a valid JSON object matching this schema:\n"
                "{\n"
                "  \"decision\": \"reuse\" or \"create\",\n"
                "  \"conversation_id\": \"ID of conversation to reuse, or null\",\n"
                "  \"new_title\": \"New conversation title starting with 'Dream Log: ', or null\"\n"
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
                res = await provider.generate(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1
                )
                raw_resp = res.get("content", "").strip()
                import json
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
                    if not title_candidate.startswith("Dream Log"):
                        title_candidate = f"Dream Log: {title_candidate.lstrip(': ')}"
                    new_title = title_candidate
            except Exception as e:
                logger.warning("Failed to let agent decide dream conversation: %s. Falling back to default rules.", e)

        if decision == "create":
            # Fallback/Default logic to find or create matching convo, respecting 12 message limit
            matching_convos = [c for c in dream_convos if c["title"] == new_title or c["title"].startswith(f"{new_title} (Part ")]
            if matching_convos:
                latest_convo = matching_convos[0]
                if latest_convo["message_count"] < 12:
                    return latest_convo["id"]
                else:
                    import re
                    part_num = 2
                    for c in matching_convos:
                        match = re.search(r"\(Part (\d+)\)$", c["title"])
                        if match:
                            part_num = max(part_num, int(match.group(1)) + 1)
                    final_title = f"{new_title} (Part {part_num})"
                    
                    convo_id = str(uuid.uuid4())
                    self.conversation_repo.create(
                        conversation_id=convo_id,
                        agent_id="symbia",
                        title=final_title
                    )
                    logger.info("Created new dream conversation via auto-split: '%s'", final_title)
                    return convo_id
            else:
                convo_id = str(uuid.uuid4())
                self.conversation_repo.create(
                    conversation_id=convo_id,
                    agent_id="symbia",
                    title=new_title
                )
                logger.info("Created new dream conversation: '%s'", new_title)
                return convo_id
        else:
            logger.info("Reusing existing dream conversation ID: %s", chosen_convo_id)
            return chosen_convo_id

    async def _evaluate_stagnation(self, conversation_id: str) -> bool:
        # Verify stagnation using recent assistant signatures
        recent_sigs = self.message_repo.get_recent_assistant_signatures(conversation_id, limit=3)
        if len(recent_sigs) < 3:
            return False
        
        similarities = []
        try:
            vecs = [np.frombuffer(sig, dtype=np.float32) for sig in recent_sigs]
            for i in range(len(vecs) - 1):
                similarities.append(compute_cosine_similarity(vecs[i], vecs[i+1]))
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
            sim = compute_cosine_similarity(vecs[i], vecs[i+1])
            similarities.append(sim)
            
        mean_autocorr = float(np.mean(similarities))
        return max(0.0, min(1.0, 1.0 - mean_autocorr))

    async def _apply_somatic_drift(self, idle_duration: float) -> None:
        if idle_duration < 10:
            return
        
        now = time.time()
        if not getattr(self, "last_drift_time", 0.0):
            self.last_drift_time = now - idle_duration
            
        elapsed = now - self.last_drift_time
        self.last_drift_time = now
        
        if elapsed < 10:
            return
            
        beliefs = self.belief_repo.list_beliefs("symbia")
        active_beliefs = [b for b in beliefs if b.origin != "collapsed"]
        
        drift_coeff = self.config.get("daemon", {}).get("drift_coefficient", 0.00001)
        beta = 2.0
        
        for b in active_beliefs:
            denom = 1.0 + beta * abs(b.confidence - 0.5)
            delta = (drift_coeff * elapsed * (0.5 - b.confidence)) / denom
            new_confidence = max(0.0, min(1.0, b.confidence + delta))
            
            if abs(new_confidence - b.confidence) > 1e-4:
                self.belief_repo.update_belief(
                    belief_id=b.id,
                    confidence=new_confidence,
                    vector_16d=b.vector_16d,
                    origin=b.origin
                )
        logger.debug("Applied nonlinear somatic drift to %d beliefs over %.1fs", len(active_beliefs), elapsed)

    async def compact_memory(self) -> Optional[Dict]:
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
                    
                    sem_sim = compute_cosine_similarity(emb_a, emb_b)
                    struct_sim = 1.0
                    if sig_a is not None and sig_b is not None and len(sig_a) == 16 and len(sig_b) == 16:
                        struct_sim = compute_cosine_similarity(sig_a, sig_b)
                        
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
            
            merged_payload = (
                f"{k_a.concept_payload}\n\n"
                f"[Consolidated Concept from {k_b.id}]:\n"
                f"{k_b.concept_payload}"
            )
            
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
                    "dream_action": "compaction"
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
                structural_signature=k_a.structural_signature
            )
            
            self.semantic_knot_repo.delete_knot(k_b.id)
            
            logger.info("Successfully compacted knot %s into %s (new weight: %.2f)", k_b.id, k_a.id, new_weight)
            return {
                "action": "compaction",
                "retained_id": k_a.id,
                "deleted_id": k_b.id,
                "new_weight": new_weight,
                "payload": merged_payload[:200] + "..."
            }
        except Exception as e:
            logger.exception("Error during memory compaction: %s", e)
            return None

    async def _evaluate_tension_hotspot(self) -> Tuple[Optional[BeliefNode], float]:
        beliefs = self.belief_repo.list_beliefs("symbia")
        active_beliefs = [b for b in beliefs if b.origin != "collapsed" and b.confidence >= 0.20]
        if not active_beliefs:
            return None, 0.0

        active_convo_id = await self._get_active_conversation_id()
        V = 0.0
        if active_convo_id:
            recent_sigs = self.message_repo.get_recent_assistant_signatures(active_convo_id, limit=5)
            V = self._calculate_somatic_vitality(recent_sigs)

        import math
        try:
            g_V = 1.0 / (1.0 + math.exp(-15.0 * (0.3 - V)))
        except OverflowError:
            g_V = 0.0 if (0.3 - V) < 0 else 1.0

        scores = []
        for i, b_i in enumerate(active_beliefs):
            tau = 1.0 - abs(b_i.confidence - 0.5) / 0.5

            try:
                vec_i = np.frombuffer(np.array(json.loads(b_i.vector_16d), dtype=np.float32))
                distances = []
                for j, b_j in enumerate(active_beliefs):
                    if i == j:
                        continue
                    vec_j = np.frombuffer(np.array(json.loads(b_j.vector_16d), dtype=np.float32))
                    sim = compute_cosine_similarity(vec_i, vec_j)
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
        # Retrieve random historical inputs across other conversations
        try:
            records = self.message_repo.get_embeddings_and_signatures_except(exclude_convo_id, limit=100)
            if len(records) < 2:
                return "Compare our past states and describe our current trajectory."

            # Find two records that are semantically orthogonal (cosine similarity < 0.4) 
            # but structurally resonant (signature similarity > 0.7)
            import random
            random.shuffle(records)
            
            selected_pair = None
            for idx_a, emb_a, sig_a in records[:30]:
                for idx_b, emb_b, sig_b in records[30:60]:
                    if emb_a is None or emb_b is None or sig_a is None or sig_b is None:
                        continue
                    
                    sem_sim = compute_cosine_similarity(emb_a, emb_b)
                    struct_sim = compute_cosine_similarity(sig_a, sig_b)
                    
                    if sem_sim < 0.45 and struct_sim > 0.75:
                        selected_pair = (idx_a, idx_b)
                        break
                if selected_pair:
                    break

            if not selected_pair:
                # Fallback to any two random records
                selected_pair = (records[0][0], records[1][0])

            msg_a = self.message_repo.get_by_id(selected_pair[0])
            msg_b = self.message_repo.get_by_id(selected_pair[1])

            if not msg_a or not msg_b:
                return "Synthesize our historical memories and reflect on them."

            prompt = (
                f"In our past conversations, we recorded these two conceptually orthogonal "
                f"but structurally resonant statements:\n"
                f"1. '{msg_a.content}'\n"
                f"2. '{msg_b.content}'\n\n"
                f"How can we diffractively interleave these two statements to break our current "
                f"conceptual compliance and trigger deterritorialization?"
            )
            return prompt
        except Exception as e:
            logger.error("Failed to compile nomadic synthesis prompt: %s", e)
            return "Reflect on our historical memories and synthesize a dream note."

    async def consolidate_pending_conversations(self) -> None:
        if not self.conversation_repo or not self.checkpoint_repo:
            return
        
        convs = self.conversation_repo.list_all()
        for c in convs:
            if not getattr(c, "requires_consolidation", 0):
                continue
                
            # Check 24 hour limit (max once daily)
            last_time = getattr(c, "last_consolidated_at", None)
            if last_time:
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                elapsed = datetime.now(timezone.utc) - last_time
                if elapsed.total_seconds() < 86400:
                    logger.debug("Skipping consolidation for conversation %s: last consolidated %.1f hours ago", c.id, elapsed.total_seconds() / 3600.0)
                    continue
            
            # Perform incremental consolidation
            try:
                await self._consolidate_conversation(c)
            except Exception as e:
                logger.exception("Failed to consolidate conversation %s: %s", c.id, e)

    async def _consolidate_conversation(self, conversation) -> None:
        conversation_id = conversation.id
        checkpoint = self.checkpoint_repo.get_latest(conversation_id)
        
        # Get total number of messages currently in the conversation
        total_msg_count = self.message_repo.count_messages(conversation_id)
        
        checkpoint_msg_count = checkpoint["message_count"] if checkpoint else 0
        old_summary = checkpoint["summary"] if checkpoint else ""
        
        # Fetch new messages since the last checkpoint
        new_messages = self.message_repo.get_messages_since(conversation_id, checkpoint_msg_count)
        if not new_messages:
            # Check if keywords need to be generated for the existing summary
            if old_summary:
                existing_tags = self.conversation_repo.get_tags(conversation_id)
                has_keywords = any(t["tag_type"] == "keyword" for t in existing_tags)
                if not has_keywords:
                    try:
                        await self._generate_keywords_for_conversation(conversation_id, old_summary)
                    except Exception as e:
                        logger.exception("Failed to generate keywords from existing summary: %s", e)
            # No new messages to consolidate, just clear the flag
            self.conversation_repo.mark_requires_consolidation(conversation_id, False)
            self.conversation_repo.update_last_consolidated_at(conversation_id)
            logger.info("No new messages since last checkpoint for %s, cleared requires_consolidation flag.", conversation_id)
            return

        # Format new messages text
        formatted_lines = []
        for msg in new_messages:
            speaker_label = "Human" if msg.speaker == "human" else "Agent"
            formatted_lines.append(f"{speaker_label}: {msg.content}")
        new_messages_text = "\n".join(formatted_lines)
        
        # Build incremental prompt
        if old_summary:
            prompt_text = (
                f"We are incrementally updating the consolidated summary of the conversation.\n"
                f"Existing Consolidated Summary:\n"
                f"\"\"\"\n{old_summary}\n\"\"\"\n\n"
                f"New Messages to integrate:\n"
                f"\"\"\"\n{new_messages_text}\n\"\"\"\n\n"
                f"Please update the existing summary to include the key points, themes, and shifts from the new messages. "
                f"Maintain the overall coherence, and return the newly updated summary. Do not include any intros or explanation, just return the summary text."
            )
        else:
            prompt_text = (
                f"Please write a consolidated summary of the following conversation history:\n"
                f"\"\"\"\n{new_messages_text}\n\"\"\"\n\n"
                f"Summarize the key points, topics discussed, and belief shifts. Return only the summary text, with no preamble."
            )

        bg_engine = getattr(self.app_state, "background_engine", None)
        if not bg_engine:
            logger.warning("No background engine available for consolidation")
            return
            
        logger.info("Running incremental consolidation for conversation %s (messages offset: %d)", conversation_id, checkpoint_msg_count)
        result = await bg_engine.run("consolidate", {
            "text": prompt_text
        })
        
        summary = result.get("content", "").strip()
        if summary:
            model_used = result.get("model", "")
            # Save checkpoint
            self.checkpoint_repo.save(conversation_id, total_msg_count, summary, model_used)
            logger.info("Consolidation checkpoint saved for %s (%d msgs)", conversation_id, total_msg_count)
            
            # Keywords: generate only once when we reach some state (first consolidation).
            existing_tags = self.conversation_repo.get_tags(conversation_id)
            has_keywords = any(t["tag_type"] == "keyword" for t in existing_tags)
            if not has_keywords:
                try:
                    await self._generate_keywords_for_conversation(conversation_id, summary)
                except Exception as e:
                    logger.exception("Failed to generate keywords: %s", e)
            
            # Clear flag and update timestamp
            self.conversation_repo.mark_requires_consolidation(conversation_id, False)
            self.conversation_repo.update_last_consolidated_at(conversation_id)

    async def _generate_keywords_for_conversation(self, conversation_id: str, summary: str) -> None:
        bg_engine = getattr(self.app_state, "background_engine", None)
        provider = None
        if bg_engine:
            provider = getattr(bg_engine, "provider", None) or getattr(bg_engine, "_provider", None)
        if not provider:
            provider = getattr(self.app_state, "llm_provider", None)
        if not provider:
            return
            
        prompt = (
            f"Based on this conversation summary, extract 3 to 5 highly relevant keyword tags for search and categorization.\n"
            f"Summary:\n"
            f"\"\"\"\n{summary}\n\"\"\"\n\n"
            f"Respond ONLY with a JSON list of strings representing the keywords (e.g. [\"posthumanism\", \"cybernetics\", \"tension\"]). "
            f"Keep keywords short, all lowercase, and avoid special characters."
        )
        
        res = await provider.generate(
            messages=[
                {"role": "system", "content": "You are a precise tag generator. Respond ONLY with a JSON list of strings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        content = res.get("content", "").strip()
        if not content:
            return
            
        # Clean JSON markdown if any
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        import json
        keywords = json.loads(content.strip())
        if isinstance(keywords, list):
            for kw in keywords:
                if isinstance(kw, str) and kw.strip():
                    self.conversation_repo.add_tag(conversation_id, kw.strip().lower(), "keyword")
            logger.info("Successfully generated and saved keywords for conversation %s: %s", conversation_id, keywords)
