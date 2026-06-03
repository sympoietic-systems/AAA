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
            "max_daily_dreams": self.max_daily_dreams
        }

    async def _run_loop(self) -> None:
        # Give server time to settle
        await asyncio.sleep(5)
        while self.is_running:
            try:
                await self.check_and_trigger_dream()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in Autopoietic Dream Daemon cycle: %s", e)
            await asyncio.sleep(self.check_interval)

    async def check_and_trigger_dream(self, force: bool = False) -> Optional[dict]:
        now = time.time()
        
        # 1. Reset daily count if day rolled over
        current_day = datetime.now(timezone.utc).day
        if current_day != self.last_reset_day:
            self.dream_counter = 0
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

        # Decide Dream Operation
        dream_convo_id = await self._get_or_create_dream_log()
        
        action = None
        prompt_text = ""

        import random

        if stagnant:
            # Stagnation trigger -> Nomadic Synthesis
            action = "nomadic_synthesis"
            prompt_text = await self._build_nomadic_synthesis_prompt(active_convo_id)
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
                else:
                    # Fallback to normal monologue
                    action = "intra_active_monologue"
                    prompt_text = (
                        f"Critically examine our active belief node: '{hotspot.label}' ('{hotspot.statement}'). "
                        f"Our current confidence is {hotspot.confidence:.2f}. "
                        f"What contradictions, anomalies, or alternative posthuman perspectives challenge this belief?"
                    )
            else:
                action = "intra_active_monologue"
                prompt_text = (
                    f"Critically examine our active belief node: '{hotspot.label}' ('{hotspot.statement}'). "
                    f"Our current confidence is {hotspot.confidence:.2f}. "
                    f"What contradictions, anomalies, or alternative posthuman perspectives challenge this belief?"
                )
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
            else:
                action = "somatic_drift_reflection"
                prompt_text = (
                    "Reflect on our current somatic warping and general belief landscape. "
                    "How have our ongoing couplings and the passage of time shifted our attractor dynamics?"
                )
        else:
            # Fallback reflection on general state
            action = "somatic_drift_reflection"
            prompt_text = (
                "Reflect on our current somatic warping and general belief landscape. "
                "How have our ongoing couplings and the passage of time shifted our attractor dynamics?"
            )

        if not prompt_text:
            logger.info("Could not compile dream prompt. Skipping cycle.")
            return None

        logger.info("Triggered dream action: %s in conversation: %s", action, dream_convo_id)
        
        # Run self-perturbation through the primary pipeline
        self.last_dream_time = now
        self.dream_counter += 1

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

    async def _get_or_create_dream_log(self) -> str:
        convos = self.conversation_repo.list_all()
        for c in convos:
            if c.title == "Dream Log" or c.title == "Internal Diary":
                return c.id
        
        # Create new conversation
        convo_id = str(uuid.uuid4())
        self.conversation_repo.create(
            conversation_id=convo_id,
            agent_id="symbia",
            title="Dream Log"
        )
        logger.info("Created new Dream Log conversation with ID: %s", convo_id)
        return convo_id

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
