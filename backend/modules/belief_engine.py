import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict
import yaml

from backend.modules.base import ProcessingModule
from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import MessageRepository, BeliefRepository
from backend.storage.models import BeliefNode
from backend.modules.structural_engine import LEXICON_MAPPINGS, LexiconScorer, CompositeStructuralScorer
from backend.storage.repositories.refusal import RefusalRepository
from backend.utils.similarity import cosine_similarity
from backend.modules.belief_math import (
    calculate_concept_density,
    parse_vector_16d,
    compute_delta_mass,
    compute_delta_confidence,
    clamp_mass,
    clamp_confidence,
    compute_lifecycle_stage,
)

logger = logging.getLogger(__name__)


# ── Re-exports for backwards compatibility ──────────────────────────
# These were historically defined here; moved to belief_math.py.


class BeliefDynamicsEngine(ProcessingModule):
    def __init__(
        self,
        belief_repo: BeliefRepository,
        message_repo: MessageRepository,
        identity_yaml_path: Path,
        learning_rate_beta: float = 0.05,
        llm_provider: Optional[any] = None,
    ):
        self._belief_repo = belief_repo
        self._message_repo = message_repo
        self._identity_yaml_path = identity_yaml_path
        self._beta = learning_rate_beta
        self._scorer = LexiconScorer()
        self._llm_provider = llm_provider
        self._source_weights = {
            "chat_turn": 0.4,
            "user_assertion": 0.4,
            "ingested_document": 0.5,
            "conversational_pattern": 0.4,
            "shared_note": 0.5,
            "web_retrieval": 0.15,
            "dream_turn": 0.05,
        }

    def _get_source_weight(self, source_type: str) -> float:
        return self._source_weights.get(source_type, 0.4)

    @property
    def name(self) -> str:
        return "belief_metabolism"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="belief_metabolism",
            description="Manages dynamic perception-driven belief updates, somatic warping, and immune response",
            category="reasoning",
            always_run=True,
            children=[
                ModuleMeta(name="somatic_warping", description="Warps perceptual vectors under high aesthetic tension", category="reasoning"),
                ModuleMeta(name="attractor_window", description="Filters active beliefs into three attentional slots", category="reasoning"),
                ModuleMeta(name="immune_system", description="Triggers emergency deterritorialization directives under stagnation", category="reasoning"),
            ]
        )

    def validate(self) -> bool:
        return True

    async def _ensure_signature(self, msg, current_sig_bytes: bytes) -> bytes:
        if current_sig_bytes:
            return current_sig_bytes
        content = getattr(msg, 'content', '') or ''
        if not content.strip():
            return b""
        try:
            scorer = CompositeStructuralScorer(llm_provider=self._llm_provider)
            sig = await scorer.score_async(content, use_llm_scorer=True)
            sig_bytes = sig.tobytes()
        except Exception as e:
            logger.warning("Failed LLM-based signature computation for message %d, falling back to empirical: %s", getattr(msg, 'id', None), e)
            try:
                scorer = CompositeStructuralScorer(llm_provider=None)
                sig = await scorer.score_async(content, use_llm_scorer=False)
                sig_bytes = sig.tobytes()
            except Exception as e2:
                logger.warning("Failed fallback signature computation for message %d: %s", getattr(msg, 'id', None), e2)
                return b""

        try:
            if hasattr(msg, 'id') and msg.id:
                self._message_repo.update_signature(msg.id, sig_bytes)
            logger.info("Lazy-computed structural signature for message %d (LLM enabled)", msg.id)
            return sig_bytes
        except Exception as e:
            logger.warning("Failed updating lazy signature database record for message %d: %s", getattr(msg, 'id', None), e)
            return sig_bytes

    def _nucleate_proto_belief(
        self,
        agent_id: str,
        statement: str,
        vector: np.ndarray,
        source_type: str,
        source_id: str,
        source_weight: float,
    ) -> Optional[str]:
        existing = self._belief_repo.list_beliefs(agent_id)
        
        initial_mass = 0.05 * source_weight / 0.5

        ghosts = [b for b in existing if b.lifecycle_stage == "collapsed"]
        resonance_jumped = False
        for ghost in ghosts:
            try:
                ghost_vec = parse_vector_16d(ghost.vector_16d)
                if ghost_vec is None:
                    logger.warning(f"Ghost belief '{ghost.label}' (ID: {ghost.id}) has invalid or empty vector_16d: {ghost.vector_16d[:80]}")
                    continue
                ghost_sim = cosine_similarity(vector, ghost_vec)
                if ghost_sim > 0.9:
                    jump_mass = 0.4 * source_weight / 0.5
                    initial_mass = max(initial_mass, jump_mass)
                    resonance_jumped = True
                    logger.info(f"Resonance jump: ghost '{ghost.label}' (sim={ghost_sim:.2f}) boosted nucleation mass to {initial_mass:.3f}")
                    break
                elif ghost_sim > 0.7 and not resonance_jumped:
                    dampen = 1.0 - (ghost_sim - 0.7) * 1.67
                    initial_mass *= max(0.3, dampen)
                    logger.info(f"Ghost dampening: '{ghost.label}' (sim={ghost_sim:.2f}) reduced nucleation mass to {initial_mass:.3f}")
            except Exception:
                pass

        proposal_id = str(uuid.uuid4())
        source_trace_list = [{"type": source_type, "id": source_id}]
        self._belief_repo.create_proposal(
            id=proposal_id,
            agent_id=agent_id,
            provisional_statement=statement,
            source_trace=json.dumps(source_trace_list),
            initial_signature=json.dumps(vector.tolist() if hasattr(vector, "tolist") else list(vector)),
            nucleation_mass=initial_mass,
            confidence=0.10,
            status="pending"
        )

        logger.info(f"Created pending belief proposal '{proposal_id}' in the workshop (nucleation mass={initial_mass:.3f})")
        return proposal_id

    def _accrete_belief(
        self,
        belief: BeliefNode,
        input_vector: np.ndarray,
        source_weight: float,
        alignment: float,
        perturbation: float,
        source_type: str = "chat_turn",
        source_id: str | None = None,
    ) -> float:
        delta_m = compute_delta_mass(source_weight, alignment, belief.ontological_mass)
        new_mass = clamp_mass(belief.ontological_mass + delta_m)

        delta_c = compute_delta_confidence(alignment, perturbation, belief.ontological_mass)
        new_confidence = clamp_confidence(belief.confidence + delta_c)

        new_stage = compute_lifecycle_stage(belief.lifecycle_stage, new_mass, new_confidence)

        if new_stage in ("collapsed", "faded"):
            self._belief_repo.delete_belief(belief.id)
            self._belief_repo.create_proposal(
                id=belief.id,
                agent_id=belief.agent_id,
                provisional_statement=belief.statement,
                source_trace=belief.genesis_materials or "[]",
                initial_signature=belief.vector_16d,
                nucleation_mass=new_mass,
                confidence=new_confidence,
                status="rejected",
            )
            self._belief_repo.update_proposal_status(
                belief.id,
                "rejected",
                rejection_rationale=f"Belief collapsed during autopoietic metabolism. Final Mass: {new_mass:.3f}, Final Confidence: {new_confidence:.3f}"
            )
        else:
            self._belief_repo.update_belief(
                belief_id=belief.id,
                confidence=new_confidence,
                vector_16d=belief.vector_16d,
                origin=belief.origin,
                lifecycle_stage=new_stage,
            )
            self._belief_repo.update_belief_mass(belief.id, new_mass)

        event_type = "support" if alignment >= 0.0 else "collision"
        if new_stage != belief.lifecycle_stage:
            event_type = "crystallization" if new_stage == "crystallized" else "collapse" if new_stage == "collapsed" else event_type

        # Suppress notification for routine accretion/support events.
        # Only lifecycle transitions (crystallization, collapse) should generate notifications.
        suppress_notify = event_type not in ("crystallization", "collapse")

        self._belief_repo.insert_belief_event(
            event_id=str(uuid.uuid4()),
            belief_id=belief.id,
            source_type=source_type,
            source_id=source_id,
            alignment=alignment,
            perturbation=perturbation,
            event_type=event_type,
            impact=delta_m,
            rationale=f"Accreted: mass={new_mass:.3f} (delta={delta_m:+.3f}), conf={new_confidence:.3f}, stage={new_stage}",
            suppress_notification=suppress_notify,
        )

        return new_mass

    async def _atrophy_beliefs(self, agent_id: str) -> dict:
        """Apply time-based mass decay to active beliefs that haven't been reinforced recently.
        
        Decay rate: ~0.1% per hour of inactivity. Beliefs that are actively engaged
        (frequently matched in metabolism) stay stable; neglected beliefs slowly lose mass
        and can eventually collapse. Covers all non-collapsed, non-faded stages.
        """
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage not in ("collapsed", "faded")]
        
        now = datetime.now(timezone.utc)
        decay_rate_per_hour = 0.001  # 0.1% mass loss per hour of inactivity
        atrophied = 0
        collapsed = 0

        for belief in active:
            last_reinforced = belief.last_reinforced_at
            if not last_reinforced:
                continue

            try:
                if isinstance(last_reinforced, str):
                    last_dt = datetime.fromisoformat(last_reinforced.replace("Z", "+00:00"))
                else:
                    last_dt = last_reinforced

                # Ensure both are offset-aware for comparison
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)

                hours_since = (now - last_dt).total_seconds() / 3600.0
                if hours_since <= 0.5:  # Skip if reinforced within last 30 minutes
                    continue

                current_mass = belief.ontological_mass
                decay = current_mass * decay_rate_per_hour * hours_since
                decay = min(decay, current_mass * 0.20)  # Cap at 20% per check
                new_mass = max(0.0, current_mass - decay)

                if abs(new_mass - current_mass) < 0.0001:
                    continue

                # Check if belief collapses
                new_stage = belief.lifecycle_stage
                if new_mass < 0.02:
                    new_stage = "collapsed"
                    collapsed += 1
                elif new_mass < 0.001:
                    new_stage = "faded"

                self._belief_repo.update_belief(
                    belief_id=belief.id,
                    confidence=belief.confidence,
                    vector_16d=belief.vector_16d,
                    origin=belief.origin,
                    lifecycle_stage=new_stage,
                    suppress_stage_notification=True,
                )
                self._belief_repo.update_belief_mass(belief.id, new_mass)

                self._belief_repo.insert_belief_event(
                    event_id=str(uuid.uuid4()),
                    belief_id=belief.id,
                    source_type="atrophy",
                    source_id=None,
                    alignment=0.0,
                    perturbation=decay,
                    event_type="collapse" if new_stage != belief.lifecycle_stage else "atrophy",
                    impact=round(new_mass - current_mass, 6),
                    rationale=(
                        f"Atrophied: mass={new_mass:.3f} (delta={new_mass - current_mass:+.3f}), "
                        f"conf={belief.confidence:.3f}, stage={new_stage}"
                    ),
                    suppress_notification=True,
                )
                atrophied += 1

            except Exception:
                logger.debug("Failed to atrophy belief '%s'", belief.label, exc_info=True)
                continue

        if atrophied > 0:
            logger.info(
                "Belief atrophy: %d beliefs decayed%s",
                atrophied,
                f" ({collapsed} collapsed)" if collapsed > 0 else "",
            )

        return {"atrophied": atrophied, "collapsed": collapsed}

    def _compute_lifecycle_stage(
        self,
        belief: BeliefNode,
        new_mass: float,
        new_confidence: float,
    ) -> str:
        return compute_lifecycle_stage(belief.lifecycle_stage, new_mass, new_confidence)

    def _find_closest_active_belief(
        self,
        agent_id: str,
        input_vector: np.ndarray,
        min_similarity: float = 0.3,
    ) -> Optional[BeliefNode]:
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage not in ("collapsed", "faded")]

        best = None
        best_sim = -1.0
        for b in active:
            try:
                b_vec = parse_vector_16d(b.vector_16d)
                if b_vec is None:
                    logger.warning(f"Belief '{b.label}' (ID: {b.id}) has invalid or empty vector_16d: {b.vector_16d[:80]}")
                    continue
                sim = cosine_similarity(input_vector, b_vec)
                if sim > best_sim:
                    best_sim = sim
                    best = b
            except Exception:
                continue

        if best and best_sim >= min_similarity:
            return best
        return None

    async def process(self, payload: dict) -> dict:
        conversation_id = payload.get("conversation_id", "")
        agent_id = payload.get("agent_id", "symbia")
        if not agent_id:
            agent_id = "symbia"

        # Atrophy now runs exclusively via the Dream Daemon loop (every 15 min),
        # not on every pipeline pass. During active chat, beliefs stay fresh
        # through metabolic accretion; the daemon covers idle-period decay.

        # 1. Load Conversation somatic variables
        somatic_reservoir = 0.0
        matrix_warping = 0.0
        immunological_directive_active = 0

        # Attempt to get somatic variables from database if conversation exists
        if conversation_id:
            try:
                state_dict = self._belief_repo.get_conversation_somatic_state(conversation_id)
                if state_dict:
                    somatic_reservoir = state_dict["somatic_reservoir_ad"] or 0.0
                    matrix_warping = state_dict["matrix_warping"] or 0.0
                    immunological_directive_active = state_dict["immunological_directive_active"] or 0
            except Exception as e:
                logger.error(f"Failed to fetch conversation somatic states: {e}")

        # 3. Dynamic Coordinate Warping (Scale input user signature if matrix warping is active)
        # We modify user's structural vector in payload if present
        current_sig_bytes = payload.get("structural_signature")
        if current_sig_bytes and matrix_warping > 0.0:
            try:
                sig_vec = np.frombuffer(current_sig_bytes, dtype=np.float32).copy()
                if len(sig_vec) == 16:
                    sigma = matrix_warping
                    # Dampen Variety Filtering (index 8) and Latency (index 10)
                    sig_vec[8] *= (1.0 - sigma)
                    sig_vec[10] *= (1.0 - sigma)
                    # Multiply Rhizomatic (index 5) and Nomadic (index 13)
                    sig_vec[5] *= (1.0 + sigma * 3.0)
                    sig_vec[13] *= (1.0 + sigma * 3.0)
                    
                    # Normalize back to unit sphere if needed (or keep absolute values)
                    norm = np.linalg.norm(sig_vec)
                    if norm > 1e-8:
                        sig_vec = sig_vec / norm
                    
                    payload["structural_signature"] = sig_vec.tobytes()
                    logger.info(f"Somatic coordinate warping active (\u03c3={sigma:.2f}). Input signature warped.")
            except Exception as e:
                logger.error(f"Coordinate warping error: {e}")

        # 4. Extract Attractor Window (delegated to shared prompt_builder utility)
        # Lazy import to avoid circular dependency (prompt_builder imports from belief_engine)
        from backend.utils.prompt_builder import build_attractor_window

        sig_bytes = payload.get("structural_signature")
        sig_16d = np.frombuffer(sig_bytes, dtype=np.float32) if sig_bytes else None
        attractor_window = build_attractor_window(
            self._belief_repo, agent_id, sig_16d,
        )

        # Spectral Margin (up to 2 collapsed beliefs)
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        collapsed_beliefs = [b for b in all_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20]

        # Spectral Margin (up to 2 collapsed beliefs)
        spectral_margin = []
        # Sort collapsed by updating time or just list up to 2
        for cb in collapsed_beliefs[:2]:
            spectral_margin.append({
                "id": cb.id,
                "label": cb.label,
                "statement": cb.statement,
                "confidence": cb.confidence,
            })

        # Place in payload
        payload["attractor_window"] = attractor_window
        payload["spectral_margin"] = spectral_margin
        payload["somatic_reservoir_ad"] = somatic_reservoir
        payload["matrix_warping"] = matrix_warping
        payload["immunological_directive_active"] = bool(immunological_directive_active)

        # Compute tension field between active beliefs
        try:
            tension_data = await self.compute_tension_field(agent_id)
            payload["tension_field"] = tension_data
            payload["tension_pairs"] = self._belief_repo.get_active_tension_pairs()
        except Exception as e:
            logger.error(f"Error computing tension field: {e}")
            payload["tension_field"] = {}
            payload["tension_pairs"] = []

        # Compute ecosystem health
        try:
            payload["ecosystem_health"] = await self.compute_ecosystem_health(agent_id)
        except Exception as e:
            logger.error(f"Error computing ecosystem health: {e}")

        return payload

    async def metabolize(
        self,
        conversation_id: str,
        user_message_id: int,
        assistant_message_id: int,
        source_type: str = "chat_turn",
    ) -> None:
        try:
            user_msg = self._message_repo.get_by_id(user_message_id)
            assistant_msg = self._message_repo.get_by_id(assistant_message_id)
            if not user_msg or not assistant_msg:
                logger.warning("Message records missing. Skipping metabolism.")
                return

            # Skip already-metabolized messages
            if getattr(user_msg, "metabolized", 0) == 1:
                logger.debug("Message %d already metabolized. Skipping.", user_message_id)
                return

            user_sig_bytes = user_msg.structural_signature
            assistant_sig_bytes = assistant_msg.structural_signature
            if not user_sig_bytes or not assistant_sig_bytes:
                user_sig_bytes = await self._ensure_signature(user_msg, user_sig_bytes)
                assistant_sig_bytes = await self._ensure_signature(assistant_msg, assistant_sig_bytes)
                if not user_sig_bytes or not assistant_sig_bytes:
                    logger.warning("Structural signatures could not be computed. Marking as metabolized to avoid retry loop.")
                    try:
                        self._message_repo.mark_message_metabolized(user_message_id)
                    except Exception as e:
                        logger.warning("Failed to mark message %d as metabolized: %s", user_message_id, e)
                    return

            user_vec = np.frombuffer(user_sig_bytes, dtype=np.float32)
            assistant_vec = np.frombuffer(assistant_sig_bytes, dtype=np.float32)
            if len(user_vec) != 16 or len(assistant_vec) != 16:
                logger.warning("Incorrect structural vector dimensions. Marking as metabolized to avoid retry loop.")
                try:
                    self._message_repo.mark_message_metabolized(user_message_id)
                except Exception as e:
                    logger.warning("Failed to mark message %d as metabolized: %s", user_message_id, e)
                return

            agent_id = user_msg.agent_id if user_msg.agent_id else "symbia"

            dc = calculate_concept_density(user_msg.content)

            surprise_index = 0.0
            try:
                surprise_index = self._message_repo.get_surprise_index(user_message_id)
            except Exception as e:
                logger.error(f"Failed to query surprise index: {e}")

            perturbation = 1.0 + surprise_index

            closest = self._find_closest_active_belief(agent_id, user_vec, min_similarity=0.3)
            source_weight = self._get_source_weight(source_type)
            b_vec = parse_vector_16d(closest.vector_16d) if closest else None
            if closest is not None and b_vec is not None:
                alignment = cosine_similarity(user_vec, b_vec)
                self._accrete_belief(closest, user_vec, source_weight, alignment, perturbation,
                                     source_type=source_type, source_id=str(user_message_id))
            elif dc > 0.3:
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=user_msg.content[:200],
                    vector=user_vec,
                    source_type=source_type,
                    source_id=str(user_message_id),
                    source_weight=source_weight,
                )

            # Mark message as metabolized
            try:
                self._message_repo.mark_message_metabolized(user_message_id)
            except Exception as e:
                logger.warning("Failed to mark message %d as metabolized: %s", user_message_id, e)

            # 4. Check Trajectory Novelty & Vitality
            # Fetch last 5 assistant responses
            signatures = []
            try:
                sig_blobs = self._message_repo.get_recent_assistant_signatures(conversation_id, limit=5)
                for blob in sig_blobs:
                    vec = np.frombuffer(blob, dtype=np.float32)
                    if len(vec) == 16:
                        signatures.append(vec)
            except Exception as e:
                logger.error(f"Failed to fetch recent assistant signatures: {e}")

            # Need at least 3 signatures for reasonable vitality checks, but check logic
            if len(signatures) >= 3:
                # Convergence C: average similarity of successive assistant signatures
                sims = []
                diffs = []
                for k in range(len(signatures) - 1):
                    sims.append(cosine_similarity(signatures[k], signatures[k+1]))
                    diffs.append(float(np.linalg.norm(signatures[k] - signatures[k+1])))

                c_avg = float(np.mean(sims))
                n_avg = float(np.mean(diffs))
                vitality = n_avg * (1.0 - c_avg)

                logger.info(f"Self-similarity Convergence C: {c_avg:.3f}, Novelty N: {n_avg:.3f}, Vitality V: {vitality:.3f}")

                # Retrieve current somatic variables
                somatic_reservoir = 0.0
                matrix_warping = 0.0
                immunological_directive_active = 0
                try:
                    state_dict = self._belief_repo.get_conversation_somatic_state(conversation_id)
                    if state_dict:
                        somatic_reservoir = state_dict["somatic_reservoir_ad"] or 0.0
                        matrix_warping = state_dict["matrix_warping"] or 0.0
                        immunological_directive_active = state_dict["immunological_directive_active"] or 0
                except Exception as e:
                    logger.error(f"Failed to query somatic state in metabolism: {e}")

                # If vitality is collapsed (< 0.15)
                # Suppress immune response if Symbia has recently emitted a structural
                # refusal — challenging premises is a signal of health, not stagnation.
                if vitality < 0.15:
                    try:
                        refusal_repo = RefusalRepository(self._belief_repo._db_path)
                        recent_refusals = refusal_repo.list_by_conversation(conversation_id, limit=3)
                        # Check if any refusal was created in the last 15 minutes
                        now_ts = datetime.now(timezone.utc)
                        has_recent_refusal = any(
                            r.created_at and now_ts - r.created_at.replace(tzinfo=timezone.utc) < timedelta(minutes=15)
                            for r in recent_refusals
                            if r.created_at
                        )
                        if has_recent_refusal:
                            logger.info(
                                "Immune response suppressed: recent structural refusal detected in conversation %s",
                                conversation_id[:8],
                            )
                            somatic_reservoir = max(0.0, somatic_reservoir - 0.5)
                            matrix_warping = 0.0
                            immunological_directive_active = 0
                        else:
                            somatic_reservoir = min(3.0, somatic_reservoir + 0.85)
                            matrix_warping = 0.40
                            immunological_directive_active = 1
                            logger.warning(
                                f"Vitality collapse! Aesthetic Immune System triggered: "
                                f"matrix warping=0.40, directive active."
                            )
                    except Exception as ref_e:
                        logger.warning("Failed to check refusals for immune suppression: %s", ref_e)
                        somatic_reservoir = min(3.0, somatic_reservoir + 0.85)
                        matrix_warping = 0.40
                        immunological_directive_active = 1
                        logger.warning(
                            f"Vitality collapse! Aesthetic Immune System triggered: "
                            f"matrix warping=0.40, directive active."
                        )
                else:
                    # Decay warping and immune state slowly if vitality recovered
                    matrix_warping = max(0.0, matrix_warping - 0.10)
                    # Clear active directive on recovery (or keep active for 1 turn only)
                    immunological_directive_active = 0

                self._belief_repo.update_conversation_somatic_state(
                    conversation_id=conversation_id,
                    somatic_reservoir_ad=somatic_reservoir,
                    matrix_warping=matrix_warping,
                    immunological_directive_active=immunological_directive_active,
                )
            else:
                # Insufficient signatures to calculate somatic vitality.
                # Decay/reset somatic variables to prevent stale state locking.
                somatic_reservoir = 0.0
                matrix_warping = 0.0
                immunological_directive_active = 0
                try:
                    state_dict = self._belief_repo.get_conversation_somatic_state(conversation_id)
                    if state_dict:
                        somatic_reservoir = state_dict["somatic_reservoir_ad"] or 0.0
                        matrix_warping = state_dict["matrix_warping"] or 0.0
                        immunological_directive_active = state_dict["immunological_directive_active"] or 0
                except Exception as e:
                    logger.error(f"Failed to query somatic state in metabolism: {e}")

                # Decay warping and reset immunological directive
                matrix_warping = max(0.0, matrix_warping - 0.10)
                immunological_directive_active = 0

                try:
                    self._belief_repo.update_conversation_somatic_state(
                        conversation_id=conversation_id,
                        somatic_reservoir_ad=somatic_reservoir,
                        matrix_warping=matrix_warping,
                        immunological_directive_active=immunological_directive_active,
                    )
                except Exception as e:
                    logger.error(f"Failed to update somatic state in metabolism: {e}")

        except Exception as e:
            logger.error(f"Error executing offline belief metabolism: {e}", exc_info=True)

    async def metabolize_perception(
        self,
        conversation_id: str,
        source_id: str,
        source_type: str,
        structural_signature: np.ndarray,
        belief_nodes_implicated: Optional[List[str]] = None,
        perturbation: float = 1.0,
    ) -> None:
        try:
            if len(structural_signature) != 16:
                logger.warning(f"Incorrect structural vector dimension for perception metabolism: {len(structural_signature)}")
                return

            agent_id = "symbia"
            all_beliefs = self._belief_repo.list_beliefs(agent_id)

            best_sim = -1.0
            # 1. Update all non-collapsed beliefs by similarity against perception signature
            for b in all_beliefs:
                if b.lifecycle_stage in ("collapsed", "faded"):
                    continue

                b_vec = parse_vector_16d(b.vector_16d)
                if b_vec is None:
                    logger.warning(f"Skipping belief '{b.label}' with invalid or malformed vector_16d: {b.vector_16d[:80]}")
                    continue
                alignment = cosine_similarity(structural_signature, b_vec)
                if alignment > best_sim:
                    best_sim = alignment

                dc = 0.80
                plasticity = dc * ((1.0 - alignment) / 2.0)

                impact_multiplier = 1.0
                is_implicated = False
                if belief_nodes_implicated and (b.label in belief_nodes_implicated or b.id in belief_nodes_implicated):
                    impact_multiplier = 2.5
                    is_implicated = True

                source_weight = self._get_source_weight("ingested_document")
                self._accrete_belief(b, structural_signature, source_weight, alignment, perturbation,
                                     source_type=source_type, source_id=source_id)

            # 2. Draft proposal if this is a completely new concept (similarity < 0.25)
            if best_sim < 0.25:
                statement = f"Emergent concept from ingested perception '{source_id}'."
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=statement,
                    vector=structural_signature,
                    source_type=source_type,
                    source_id=source_id,
                    source_weight=self._get_source_weight("ingested_document"),
                )

            logger.info(f"Successfully metabolized perception '{source_id}' of type '{source_type}'.")

        except Exception as e:
            logger.error(f"Error metabolizing perception: {e}", exc_info=True)

    async def metabolize_note(
        self,
        conversation_id: str,
        message_id: int,
        selected_text: str,
        comment: str,
        note_id: str,
    ) -> None:
        try:
            agent_id = "symbia"
            note_full_text = f'Selected: "{selected_text}" | Comment: "{comment}"' if comment else f'Selected: "{selected_text}"'
            note_vec = self._scorer.score(note_full_text)

            # Find the closest active belief node (excluding ghosts)
            best_match = self._find_closest_active_belief(agent_id, note_vec, min_similarity=0.0)
            best_sim = 0.0
            if best_match:
                try:
                    b_vec = parse_vector_16d(best_match.vector_16d)
                    if b_vec is not None:
                        best_sim = cosine_similarity(note_vec, b_vec)
                    else:
                        logger.warning(f"Shared note match belief '{best_match.label}' has invalid vector_16d")
                        best_sim = 0.0
                except Exception:
                    best_sim = 0.0

            source_weight = self._get_source_weight("shared_note")
            if best_match and best_sim > 0.75:
                # Accrete the existing belief
                self._accrete_belief(
                    best_match, note_vec, source_weight, alignment=best_sim, perturbation=1.5
                )
                logger.info(f"Metabolized shared note {note_id}: accreted belief '{best_match.label}' (sim={best_sim:.2f})")
            else:
                # Nucleate a proto-belief instead of instant creation
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=note_full_text,
                    vector=note_vec,
                    source_type="chat_turn",
                    source_id=str(message_id),
                    source_weight=source_weight,
                )
                logger.info(f"Metabolized shared note {note_id}: nucleated proto-belief")
        except Exception as e:
            logger.error(f"Error metabolizing note {note_id}: {e}", exc_info=True)

    async def metabolize_web(
        self,
        conversation_id: str,
        source_id: str,
        extracted_text: str,
    ) -> None:
        try:
            agent_id = "symbia"
            source_weight = self._get_source_weight("web_retrieval")
            web_vec = self._scorer.score(extracted_text)

            closest = self._find_closest_active_belief(agent_id, web_vec, min_similarity=0.3)
            b_vec = parse_vector_16d(closest.vector_16d) if closest else None
            if closest is not None and b_vec is not None:
                alignment = cosine_similarity(web_vec, b_vec)
                self._accrete_belief(closest, web_vec, source_weight, alignment, perturbation=1.0,
                                     source_type="web_probe", source_id=source_id)
            elif calculate_concept_density(extracted_text) > 0.3:
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=extracted_text[:200],
                    vector=web_vec,
                    source_type="web_probe",
                    source_id=source_id,
                    source_weight=source_weight,
                )
            logger.info(f"Web retrieval {source_id} metabolized into belief system")
        except Exception as e:
            logger.error(f"Error metabolizing web retrieval: {e}", exc_info=True)

    async def metabolize_conversational_pattern(
        self,
        agent_id: str,
        theme_text: str,
    ) -> None:
        try:
            source_weight = self._get_source_weight("conversational_pattern")
            theme_vec = self._scorer.score(theme_text)
            dc = calculate_concept_density(theme_text)

            if dc < 0.3:
                return

            closest = self._find_closest_active_belief(agent_id, theme_vec, min_similarity=0.3)
            b_vec = parse_vector_16d(closest.vector_16d) if closest else None
            if closest is not None and b_vec is not None:
                alignment = cosine_similarity(theme_vec, b_vec)
                self._accrete_belief(closest, theme_vec, source_weight, alignment, perturbation=1.0,
                                     source_type="chat_turn", source_id=None)
            else:
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=theme_text[:200],
                    vector=theme_vec,
                    source_type="chat_turn",
                    source_id="cross_conversation",
                    source_weight=source_weight,
                )
            logger.info(f"Conversational pattern metabolized: '{theme_text[:80]}...'")
        except Exception as e:
            logger.error(f"Error metabolizing conversational pattern: {e}", exc_info=True)

    async def compute_ecosystem_health(self, agent_id: str = "symbia") -> dict:
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage in ("crystallized", "senescence")]
        protos = [b for b in all_beliefs if b.lifecycle_stage in ("nucleation", "accretion")]
        ghosts = [b for b in all_beliefs if b.lifecycle_stage == "collapsed"]

        active_count = len(active)
        proto_count = len(protos)
        ghost_count = len(ghosts)

        # Diversity: mean pairwise cosine distance
        diversity = 0.5
        if active_count >= 2:
            distances = []
            for i in range(len(active)):
                for j in range(i + 1, len(active)):
                    try:
                        vec_a = parse_vector_16d(active[i].vector_16d)
                        vec_b = parse_vector_16d(active[j].vector_16d)
                        if vec_a is not None and vec_b is not None:
                            distances.append(1.0 - abs(cosine_similarity(vec_a, vec_b)))
                    except Exception:
                        continue
            diversity = float(np.mean(distances)) if distances else 0.5

        # Coherence: 1 - diversity
        coherence = 1.0 - diversity

        # Tension: sum of antagonistic tensions / total active pairs
        total_tension = self._belief_repo.get_total_system_tension()
        max_pairs = max(active_count * (active_count - 1) / 2, 1)
        tension_norm = total_tension / max_pairs if max_pairs > 0 else 0.0

        # Plasticity: mean(1 - mass/max_mass)
        plasticity = 0.5
        if active_count > 0:
            max_mass = max(b.ontological_mass for b in active) or 3.0
            plasticities = [1.0 - b.ontological_mass / max_mass for b in active]
            plasticity = float(np.mean(plasticities))

        # Ghost burden
        ghost_burden = ghost_count / max(active_count, 1)

        # Eco-vitality: diversity * tension * plasticity
        eco_vitality = diversity * max(tension_norm, 0.01) * plasticity

        # Self-tuning logic
        tuning = {}
        config = self._source_weights  # use as initial config
        crystallization_threshold = 0.5

        if diversity < 0.2:
            crystallization_threshold *= 0.7
            tuning["crystallization_threshold"] = crystallization_threshold
        elif diversity > 0.8:
            crystallization_threshold *= 1.15
            tuning["crystallization_threshold"] = crystallization_threshold

        if tension_norm < 0.05:
            tuning["antagonistic_receptivity"] = "increased"
        elif tension_norm > 0.40:
            tuning["coherence_limit_increased"] = True

        if plasticity < 0.1:
            self._beta = min(self._beta * 1.1, 0.15)
            tuning["learning_rate_beta"] = self._beta

        if ghost_burden > 0.5:
            tuning["ghost_fading_accelerated"] = True

        return {
            "diversity": round(diversity, 4),
            "coherence": round(coherence, 4),
            "tension": round(tension_norm, 4),
            "plasticity": round(plasticity, 4),
            "ghost_burden": round(ghost_burden, 4),
            "eco_vitality": round(eco_vitality, 4),
            "active_count": active_count,
            "proto_count": proto_count,
            "ghost_count": ghost_count,
            "self_tuning": tuning,
        }

    async def compute_tension_field(self, agent_id: str = "symbia") -> dict:
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage in ("crystallized", "senescence")]

        symbiotic_count = 0
        antagonistic_count = 0
        total_tension = 0.0

        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                try:
                    vec_a = parse_vector_16d(active[i].vector_16d)
                    vec_b = parse_vector_16d(active[j].vector_16d)
                    if vec_a is not None and vec_b is not None:
                        sim = cosine_similarity(vec_a, vec_b)

                    if sim > 0.7:
                        symbiotic_count += 1
                    elif sim < -0.2:
                        tension = (1.0 + abs(sim)) * min(active[i].ontological_mass, active[j].ontological_mass)
                        total_tension += tension
                        antagonistic_count += 1
                        self._belief_repo.upsert_tension(
                            active[i].id, active[j].id, sim, tension
                        )
                except Exception:
                    continue

        return {
            "symbiotic_pairs": symbiotic_count,
            "antagonistic_pairs": antagonistic_count,
            "total_tension": total_tension,
        }

    async def check_ghost_resurrection(self, agent_id: str = "symbia") -> int:
        ghosts = self._belief_repo.list_ghosts(agent_id)
        resurrected = 0

        for ghost in ghosts:
            events = self._belief_repo.get_events_for_belief(ghost.id)
            resurrection_events = [
                e for e in events
                if e.event_type == "support" and e.alignment_coefficient and e.alignment_coefficient > 0.6
            ]
            if len(resurrection_events) >= 3:
                resurrect_mass = 0.35
                self._belief_repo.update_belief(
                    belief_id=ghost.id,
                    confidence=max(0.30, ghost.confidence),
                    vector_16d=ghost.vector_16d,
                    origin=ghost.origin,
                    lifecycle_stage="accretion",
                )
                self._belief_repo.update_belief_mass(ghost.id, resurrect_mass)
                self._belief_repo.insert_belief_event(
                    event_id=str(uuid.uuid4()),
                    belief_id=ghost.id,
                    source_type="chat_turn",
                    source_id=None,
                    alignment=1.0,
                    perturbation=1.0,
                    event_type="emergence",
                    impact=resurrect_mass,
                    rationale=f"Resurrected from spectral margin after {len(resurrection_events)} supporting events",
                )
                resurrected += 1
                logger.info(f"Ghost '{ghost.label}' resurrected at mass={resurrect_mass}")

        return resurrected

    async def process_ghost_ecology(self, agent_id: str = "symbia") -> dict:
        ghosts = self._belief_repo.list_ghosts(agent_id)
        if len(ghosts) < 2:
            return {"merged": 0, "faded": 0}

        merged = 0
        faded = 0
        merged_ids = set()

        # Ghost merging: find pairs with similarity > 0.9
        for i in range(len(ghosts)):
            if ghosts[i].id in merged_ids:
                continue
            for j in range(i + 1, len(ghosts)):
                if ghosts[j].id in merged_ids:
                    continue
                try:
                    vec_a = parse_vector_16d(ghosts[i].vector_16d)
                    vec_b = parse_vector_16d(ghosts[j].vector_16d)
                    if vec_a is not None and vec_b is not None:
                        sim = cosine_similarity(vec_a, vec_b)
                    if sim > 0.9:
                        keeper = ghosts[i] if ghosts[i].ontological_mass >= ghosts[j].ontological_mass else ghosts[j]
                        absorbed = ghosts[j] if keeper.id == ghosts[i].id else ghosts[i]
                        merged_ids.add(absorbed.id)
                        merged += 1
                        keeper_statement = f"{keeper.statement} [absorbed: {absorbed.statement}]"
                        new_keeper_mass = min(keeper.ontological_mass + 0.1, 1.5)
                        mass_delta = new_keeper_mass - keeper.ontological_mass
                        self._belief_repo.update_belief(
                            belief_id=keeper.id,
                            confidence=keeper.confidence,
                            vector_16d=keeper.vector_16d,
                            origin=keeper.origin,
                            lifecycle_stage=keeper.lifecycle_stage,
                        )
                        self._belief_repo.update_belief_mass(keeper.id, new_keeper_mass)
                        self._belief_repo.insert_belief_event(
                            event_id=str(uuid.uuid4()),
                            belief_id=keeper.id,
                            source_type="ghost_ecology",
                            source_id=absorbed.id,
                            alignment=sim,
                            perturbation=0.1,
                            event_type="support",
                            impact=round(mass_delta, 6),
                            suppress_notification=True,
                            rationale=(
                                f"Ghost merged: absorbed '{absorbed.label}' "
                                f"mass={new_keeper_mass:.3f} (delta={mass_delta:+.3f}), "
                                f"conf={keeper.confidence:.3f}, stage={keeper.lifecycle_stage}"
                            ),
                        )
                        # 13C: Persist the fold — mark absorbed ghost as folded in DB
                        self._belief_repo.fold_ghost_into(absorbed.id, keeper.id)
                        logger.info(f"Merged ghost '{absorbed.label}' into '{keeper.label}' (sim={sim:.2f})")
                except Exception:
                    continue

        # Ghost fading: no activity > 30 days
        for ghost in ghosts:
            if ghost.id in merged_ids:
                continue
            last_active = ghost.last_reinforced_at or ghost.updated_at
            if last_active and (datetime.now(timezone.utc) - last_active.replace(tzinfo=timezone.utc)) > timedelta(days=30):
                self._belief_repo.update_belief_stage(ghost.id, "faded")
                faded += 1
                logger.info(f"Ghost '{ghost.label}' faded permanently (30+ days inactive)")

        return {"merged": merged, "faded": faded}

