import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from backend.modules.base import ProcessingModule
from backend.modules.belief import DecayManager, EcosystemManager, PerceptionMetabolismHandler
from backend.modules.belief_math import (
    calculate_concept_density,
    clamp_confidence,
    clamp_mass,
    compute_delta_confidence,
    compute_delta_mass,
    compute_lifecycle_stage,
    parse_vector_16d,
)
from backend.modules.structural_engine import CompositeStructuralScorer
from backend.pipeline.metadata import ModuleMeta
from backend.storage.models import BeliefNode
from backend.storage.repositories.cognitive.refusal import RefusalRepository
from backend.storage.repository import BeliefRepository, MessageRepository
from backend.utils.similarity import cosine_similarity

logger = logging.getLogger(__name__)


# ── Re-exports for backwards compatibility ──────────────────────────
# These were historically defined here; moved to belief_math.py.


class BeliefDynamicsEngine(ProcessingModule):
    _NUCLEATION_THRESHOLD: float = float(os.getenv("AAA_BELIEF_NUCLEATION_THRESHOLD", "0.2"))

    def __init__(
        self,
        belief_repo: BeliefRepository,
        message_repo: MessageRepository,
        identity_yaml_path: Path,
        learning_rate_beta: float = 0.05,
        llm_provider: object | None = None,
    ):
        self._belief_repo = belief_repo
        self._message_repo = message_repo
        self._identity_yaml_path = identity_yaml_path
        self._beta = learning_rate_beta
        self._scorer = CompositeStructuralScorer()
        self._llm_provider = llm_provider
        self._source_weights = {
            "chat_turn": 0.4,
            "user_assertion": 0.4,
            "ingested_document": 0.5,
            "conversational_pattern": 0.4,
            "shared_note": 0.5,
            "web_retrieval": 0.15,
            "dream_turn": 0.05,
            "research_step": 0.35,
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
                ModuleMeta(
                    name="somatic_warping",
                    description="Warps perceptual vectors under high aesthetic tension",
                    category="reasoning",
                ),
                ModuleMeta(
                    name="attractor_window",
                    description="Filters active beliefs into three attentional slots",
                    category="reasoning",
                ),
                ModuleMeta(
                    name="immune_system",
                    description="Triggers emergency deterritorialization directives under stagnation",
                    category="reasoning",
                ),
            ],
        )

    def validate(self) -> bool:
        return True

    async def _ensure_signature(self, msg, current_sig_bytes: bytes) -> bytes:
        if current_sig_bytes:
            return current_sig_bytes
        content = getattr(msg, "content", "") or ""
        if not content.strip():
            return b""
        try:
            scorer = CompositeStructuralScorer(llm_provider=self._llm_provider)
            sig = await scorer.score_async(content, use_llm_scorer=True)
            sig_bytes = sig.tobytes()
        except Exception as e:
            logger.warning(
                "Failed LLM-based signature computation for message %d, falling back to empirical: %s",
                getattr(msg, "id", None),
                e,
            )
            try:
                scorer = CompositeStructuralScorer(llm_provider=None)
                sig = await scorer.score_async(content, use_llm_scorer=False)
                sig_bytes = sig.tobytes()
            except Exception as e2:
                logger.warning("Failed fallback signature computation for message %d: %s", getattr(msg, "id", None), e2)
                return b""

        try:
            if hasattr(msg, "id") and msg.id:
                self._message_repo.update_signature(msg.id, sig_bytes)
            logger.info("Lazy-computed structural signature for message %d (LLM enabled)", msg.id)
            return sig_bytes
        except Exception as e:
            logger.warning(
                "Failed updating lazy signature database record for message %d: %s", getattr(msg, "id", None), e
            )
            return sig_bytes

    def _nucleate_proto_belief(
        self,
        agent_id: str,
        statement: str,
        vector: np.ndarray,
        source_type: str,
        source_id: str,
        source_weight: float,
    ) -> str | None:
        existing = self._belief_repo.list_beliefs(agent_id)

        initial_mass = 0.05 * source_weight / 0.5

        ghosts = [b for b in existing if b.lifecycle_stage == "collapsed"]
        resonance_jumped = False
        for ghost in ghosts:
            try:
                ghost_vec = parse_vector_16d(ghost.vector_16d)
                if ghost_vec is None:
                    logger.warning(
                        f"Ghost belief '{ghost.label}' (ID: {ghost.id}) has invalid or empty vector_16d: {ghost.vector_16d[:80]}"
                    )
                    continue
                ghost_sim = cosine_similarity(vector, ghost_vec)
                if ghost_sim > 0.9:
                    jump_mass = 0.4 * source_weight / 0.5
                    initial_mass = max(initial_mass, jump_mass)
                    resonance_jumped = True
                    logger.info(
                        f"Resonance jump: ghost '{ghost.label}' (sim={ghost_sim:.2f}) boosted nucleation mass to {initial_mass:.3f}"
                    )
                    break
                elif ghost_sim > 0.7 and not resonance_jumped:
                    dampen = 1.0 - (ghost_sim - 0.7) * 1.67
                    initial_mass *= max(0.3, dampen)
                    logger.info(
                        f"Ghost dampening: '{ghost.label}' (sim={ghost_sim:.2f}) reduced nucleation mass to {initial_mass:.3f}"
                    )
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
            status="pending",
        )

        logger.info(
            f"Created pending belief proposal '{proposal_id}' in the workshop (nucleation mass={initial_mass:.3f})"
        )
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
        dc: float = 0.5,
    ) -> float:
        delta_m = compute_delta_mass(source_weight, alignment, belief.ontological_mass)
        new_mass = clamp_mass(belief.ontological_mass + delta_m)

        delta_c = compute_delta_confidence(alignment, perturbation, belief.ontological_mass, dc=dc)
        new_confidence = clamp_confidence(belief.confidence + delta_c)

        new_stage = compute_lifecycle_stage(belief.lifecycle_stage, new_mass, new_confidence)

        event_type = "support" if alignment >= 0.0 else "collision"
        if new_stage != belief.lifecycle_stage:
            event_type = (
                "crystallization"
                if new_stage == "crystallized"
                else "collapse"
                if new_stage == "collapsed"
                else event_type
            )

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
                rejection_rationale=f"Belief collapsed during autopoietic metabolism. Final Mass: {new_mass:.3f}, Final Confidence: {new_confidence:.3f}",
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

        return new_mass

    async def _apply_turn_decay(self, agent_id: str, engaged_belief_id: str | None = None) -> dict:
        """Apply discrete per-turn mass decay to active beliefs that were not engaged this turn."""
        return DecayManager.apply_turn_decay(self._belief_repo, agent_id, engaged_belief_id)

    async def _atrophy_beliefs(self, agent_id: str) -> dict:
        """Apply time-based mass decay to active beliefs that haven't been reinforced recently."""
        return DecayManager.atrophy_beliefs(self._belief_repo, agent_id)

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
    ) -> BeliefNode | None:
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage not in ("collapsed", "faded")]

        best = None
        best_sim = -1.0
        for b in active:
            try:
                b_vec = parse_vector_16d(b.vector_16d)
                if b_vec is None:
                    logger.warning(
                        f"Belief '{b.label}' (ID: {b.id}) has invalid or empty vector_16d: {b.vector_16d[:80]}"
                    )
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
                    sig_vec[8] *= 1.0 - sigma
                    sig_vec[10] *= 1.0 - sigma
                    # Multiply Rhizomatic (index 5) and Nomadic (index 13)
                    sig_vec[5] *= 1.0 + sigma * 3.0
                    sig_vec[13] *= 1.0 + sigma * 3.0

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
            self._belief_repo,
            agent_id,
            sig_16d,
        )

        # Spectral Margin (up to 2 collapsed beliefs)
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        collapsed_beliefs = [
            b for b in all_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20
        ]

        # Spectral Margin (up to 2 collapsed beliefs)
        spectral_margin = []
        # Sort collapsed by updating time or just list up to 2
        for cb in collapsed_beliefs[:2]:
            spectral_margin.append(
                {
                    "id": cb.id,
                    "label": cb.label,
                    "statement": cb.statement,
                    "confidence": cb.confidence,
                }
            )

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
                    logger.warning(
                        "Structural signatures could not be computed. Marking as metabolized to avoid retry loop."
                    )
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

            closest = self._find_closest_active_belief(agent_id, user_vec, min_similarity=self._NUCLEATION_THRESHOLD)
            source_weight = self._get_source_weight(source_type)
            b_vec = parse_vector_16d(closest.vector_16d) if closest else None
            if closest is not None and b_vec is not None:
                alignment = cosine_similarity(user_vec, b_vec)
                self._accrete_belief(
                    closest,
                    user_vec,
                    source_weight,
                    alignment,
                    perturbation,
                    source_type=source_type,
                    source_id=str(user_message_id),
                )
            elif dc > self._NUCLEATION_THRESHOLD:
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=user_msg.content[:200],
                    vector=user_vec,
                    source_type=source_type,
                    source_id=str(user_message_id),
                    source_weight=source_weight,
                )

            engaged_id = closest.id if (closest is not None and b_vec is not None) else None
            try:
                await self._apply_turn_decay(agent_id, engaged_belief_id=engaged_id)
            except Exception as e:
                logger.warning("Turn-based belief decay failed in metabolize: %s", e)

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
                    sims.append(cosine_similarity(signatures[k], signatures[k + 1]))
                    diffs.append(float(np.linalg.norm(signatures[k] - signatures[k + 1])))

                c_avg = float(np.mean(sims))
                n_avg = float(np.mean(diffs))
                vitality = n_avg * (1.0 - c_avg)

                logger.info(
                    f"Self-similarity Convergence C: {c_avg:.3f}, Novelty N: {n_avg:.3f}, Vitality V: {vitality:.3f}"
                )

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
                        now_ts = datetime.now(UTC)
                        has_recent_refusal = any(
                            r.created_at and now_ts - r.created_at.replace(tzinfo=UTC) < timedelta(minutes=15)
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
                                "Vitality collapse! Aesthetic Immune System triggered: "
                                "matrix warping=0.40, directive active."
                            )
                    except Exception as ref_e:
                        logger.warning("Failed to check refusals for immune suppression: %s", ref_e)
                        somatic_reservoir = min(3.0, somatic_reservoir + 0.85)
                        matrix_warping = 0.40
                        immunological_directive_active = 1
                        logger.warning(
                            "Vitality collapse! Aesthetic Immune System triggered: "
                            "matrix warping=0.40, directive active."
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
        belief_nodes_implicated: list[str] | None = None,
        perturbation: float = 1.0,
    ) -> None:
        await PerceptionMetabolismHandler.metabolize_perception(
            self,
            conversation_id=conversation_id,
            source_id=source_id,
            source_type=source_type,
            structural_signature=structural_signature,
            belief_nodes_implicated=belief_nodes_implicated,
            perturbation=perturbation,
        )

    async def metabolize_note(
        self,
        conversation_id: str,
        message_id: int,
        selected_text: str,
        comment: str,
        note_id: str,
    ) -> None:
        await PerceptionMetabolismHandler.metabolize_note(
            self,
            conversation_id=conversation_id,
            message_id=message_id,
            selected_text=selected_text,
            comment=comment,
            note_id=note_id,
        )

    async def metabolize_web(
        self,
        conversation_id: str,
        source_id: str,
        extracted_text: str,
    ) -> None:
        await PerceptionMetabolismHandler.metabolize_web(
            self,
            conversation_id=conversation_id,
            source_id=source_id,
            extracted_text=extracted_text,
        )

    async def metabolize_conversational_pattern(
        self,
        agent_id: str,
        theme_text: str,
    ) -> None:
        await PerceptionMetabolismHandler.metabolize_conversational_pattern(
            self,
            agent_id=agent_id,
            theme_text=theme_text,
        )

    async def compute_ecosystem_health(self, agent_id: str = "symbia") -> dict:
        health, new_beta = EcosystemManager.compute_ecosystem_health(
            self._belief_repo,
            agent_id=agent_id,
            source_weights=self._source_weights,
            beta=self._beta,
        )
        self._beta = new_beta
        return health

    async def compute_tension_field(self, agent_id: str = "symbia") -> dict:
        return EcosystemManager.compute_tension_field(self._belief_repo, agent_id=agent_id)

    async def check_ghost_resurrection(self, agent_id: str = "symbia") -> int:
        return EcosystemManager.check_ghost_resurrection(self._belief_repo, agent_id=agent_id)

    async def process_ghost_ecology(self, agent_id: str = "symbia") -> dict:
        return EcosystemManager.process_ghost_ecology(self._belief_repo, agent_id=agent_id)
