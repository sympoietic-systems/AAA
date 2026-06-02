import logging
import json
import uuid
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict
import yaml

from backend.modules.base import ProcessingModule
from backend.skills.metadata import SkillMeta
from backend.storage.repository import MessageRepository, BeliefRepository
from backend.storage.models import BeliefNode
from backend.modules.structural_engine import LEXICON_MAPPINGS, LexiconScorer

logger = logging.getLogger(__name__)


def calculate_concept_density(text: str, lambda_param: float = 3.0) -> float:
    text_lower = text.lower()
    matched_dims = 0
    for stems in LEXICON_MAPPINGS:
        matched = False
        for stem in stems:
            if stem in text_lower:
                matched = True
                break
        if matched:
            matched_dims += 1
    return float(np.tanh(matched_dims / lambda_param))


def compute_cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a < 1e-8 or norm_b < 1e-8:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


class BeliefDynamicsEngine(ProcessingModule):
    def __init__(
        self,
        belief_repo: BeliefRepository,
        message_repo: MessageRepository,
        identity_yaml_path: Path,
        learning_rate_beta: float = 0.05,
    ):
        self._belief_repo = belief_repo
        self._message_repo = message_repo
        self._identity_yaml_path = identity_yaml_path
        self._beta = learning_rate_beta
        self._scorer = LexiconScorer()

    @property
    def name(self) -> str:
        return "belief_metabolism"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
            name="belief_metabolism",
            description="Manages dynamic perception-driven belief updates, somatic warping, and immune response",
            category="reasoning",
            always_run=True,
            children=[
                SkillMeta(name="somatic_warping", description="Warps perceptual vectors under high aesthetic tension", category="reasoning"),
                SkillMeta(name="attractor_window", description="Filters active beliefs into three attentional slots", category="reasoning"),
                SkillMeta(name="immune_system", description="Triggers emergency deterritorialization directives under stagnation", category="reasoning"),
            ]
        )

    def validate(self) -> bool:
        return True

    def _seed_initial_beliefs_if_needed(self, agent_id: str) -> None:
        existing = self._belief_repo.list_beliefs(agent_id)
        if len(existing) > 0:
            return

        if not self._identity_yaml_path.exists():
            logger.warning(f"Identity file {self._identity_yaml_path} not found. Cannot seed beliefs.")
            return

        try:
            with open(self._identity_yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            config_beliefs = data.get("personality", {}).get("beliefs", [])
            for cb in config_beliefs:
                label = cb.get("id")
                statement = cb.get("statement")
                confidence = cb.get("confidence", 0.5)
                category = cb.get("category", "ontological")

                # Map category to Ontological Mass
                if category == "foundational":
                    mass = 1.5
                elif category == "ontological":
                    mass = 1.2
                elif category == "methodological":
                    mass = 1.0
                else:
                    mass = 1.0

                # Compute baseline 16D vector using LexiconScorer
                vec = self._scorer.score(statement)
                vec_json = json.dumps(vec.tolist())

                self._belief_repo.create_belief(
                    id=str(uuid.uuid4()),
                    agent_id=agent_id,
                    label=label,
                    statement=statement,
                    origin="authored",
                    confidence=confidence,
                    ontological_mass=mass,
                    somatic_anchor="none",
                    vector_16d=vec_json,
                )
            logger.info(f"Successfully seeded {len(config_beliefs)} baseline beliefs for agent {agent_id}.")
        except Exception as e:
            logger.error(f"Error seeding beliefs: {e}", exc_info=True)

    async def process(self, payload: dict) -> dict:
        conversation_id = payload.get("conversation_id", "")
        agent_id = payload.get("agent_id", "symbia")
        if not agent_id:
            agent_id = "symbia"

        # 2. Load Conversation somatic variables
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

        # 4. Extract Attractor Window and Spectral Margin
        all_beliefs = self._belief_repo.list_beliefs(agent_id)
        active_beliefs = [b for b in all_beliefs if b.origin != "collapsed" and b.confidence >= 0.20]
        collapsed_beliefs = [b for b in all_beliefs if b.origin == "collapsed" or b.confidence < 0.20]

        # Attractor Window (3 slots)
        slot1: Optional[BeliefNode] = None
        slot2: Optional[BeliefNode] = None
        slot3: Optional[BeliefNode] = None

        if active_beliefs:
            # Slot 1: Highest-mass core/foundational belief
            slot1 = max(active_beliefs, key=lambda b: b.ontological_mass)

            # Slot 2: Lowest confidence active belief (stress slot: 0.20 <= c_i < 0.50)
            stressed_beliefs = [b for b in active_beliefs if b.confidence < 0.50]
            if stressed_beliefs:
                slot2 = min(stressed_beliefs, key=lambda b: b.confidence)
            else:
                # Fallback: second highest mass or next lowest confidence active belief excluding slot 1
                remaining = [b for b in active_beliefs if b.id != slot1.id]
                if remaining:
                    slot2 = min(remaining, key=lambda b: b.confidence)

            # Slot 3: Highest similarity active belief against current user input (resonance slot)
            sig_bytes = payload.get("structural_signature")
            if sig_bytes:
                try:
                    user_vec = np.frombuffer(sig_bytes, dtype=np.float32)
                    if len(user_vec) == 16:
                        # Exclude slot1 and slot2 if possible
                        candidate_pool = [b for b in active_beliefs if b.id != slot1.id and (not slot2 or b.id != slot2.id)]
                        if not candidate_pool:
                            candidate_pool = active_beliefs
                        
                        def sim_score(b: BeliefNode) -> float:
                            try:
                                b_vec = np.array(json.loads(b.vector_16d), dtype=np.float32)
                                return compute_cosine_similarity(user_vec, b_vec)
                            except Exception:
                                return -1.0

                        if candidate_pool:
                            slot3 = max(candidate_pool, key=sim_score)
                except Exception as e:
                    logger.error(f"Error calculating resonance slot: {e}")

        # Construct Attractor Window dicts
        attractor_window = []
        for i, slot in enumerate([slot1, slot2, slot3]):
            if slot:
                attractor_window.append({
                    "slot": i + 1,
                    "id": slot.id,
                    "label": slot.label,
                    "statement": slot.statement,
                    "confidence": slot.confidence,
                    "mass": slot.ontological_mass,
                })

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

        return payload

    async def metabolize(
        self,
        conversation_id: str,
        user_message_id: int,
        assistant_message_id: int,
    ) -> None:
        try:
            user_msg = self._message_repo.get_by_id(user_message_id)
            assistant_msg = self._message_repo.get_by_id(assistant_message_id)
            if not user_msg or not assistant_msg:
                logger.warning("Message records missing. Skipping metabolism.")
                return

            user_sig_bytes = user_msg.structural_signature
            assistant_sig_bytes = assistant_msg.structural_signature
            if not user_sig_bytes or not assistant_sig_bytes:
                logger.warning("Structural signatures not found on messages. Skipping metabolism.")
                return

            user_vec = np.frombuffer(user_sig_bytes, dtype=np.float32)
            assistant_vec = np.frombuffer(assistant_sig_bytes, dtype=np.float32)
            if len(user_vec) != 16 or len(assistant_vec) != 16:
                logger.warning("Incorrect structural vector dimensions. Skipping.")
                return

            agent_id = user_msg.agent_id if user_msg.agent_id else "symbia"

            # 1. Concept Density Dc of User Text
            dc = calculate_concept_density(user_msg.content)

            # 2. Get surprise index from metrics (default to 0.0)
            surprise_index = 0.0
            try:
                surprise_index = self._message_repo.get_surprise_index(user_message_id)
            except Exception as e:
                logger.error(f"Failed to query surprise index: {e}")

            perturbation = 1.0 + surprise_index

            # 3. Update Belief Coordinates & Confidences
            all_beliefs = self._belief_repo.list_beliefs(agent_id)
            for b in all_beliefs:
                if b.origin == "collapsed":
                    continue

                b_vec = np.array(json.loads(b.vector_16d), dtype=np.float32)
                alignment = compute_cosine_similarity(user_vec, b_vec)

                # Plasticity
                plasticity = dc * ((1.0 - alignment) / 2.0)

                # Delta confidence
                delta_c = (plasticity * alignment * perturbation) / b.ontological_mass
                new_c = max(0.0, min(1.0, b.confidence + delta_c))

                # Vector Nomadic Drift
                new_b_vec = b_vec + self._beta * plasticity * alignment * user_vec
                norm = np.linalg.norm(new_b_vec)
                if norm > 1e-8:
                    new_b_vec = new_b_vec / norm
                else:
                    new_b_vec = b_vec

                # Check for collapse transition
                new_origin = b.origin
                if new_c < 0.20:
                    new_origin = "collapsed"
                    logger.info(f"Belief '{b.label}' collapsed! Transitioning to spectral margin.")

                self._belief_repo.update_belief(
                    belief_id=b.id,
                    confidence=new_c,
                    vector_16d=json.dumps(new_b_vec.tolist()),
                    origin=new_origin,
                )

                # Log event
                event_type = "support" if alignment >= 0.0 else "collision"
                if new_origin == "collapsed":
                    event_type = "collapse"

                rationale = (
                    f"Message ID {user_message_id} alignment={alignment:.2f} "
                    f"density={dc:.2f} surprise={surprise_index:.2f} delta_c={delta_c:.4f}"
                )
                self._belief_repo.insert_belief_event(
                    event_id=str(uuid.uuid4()),
                    belief_id=b.id,
                    source_type="chat_turn",
                    source_id=str(user_message_id),
                    alignment=alignment,
                    perturbation=perturbation,
                    event_type=event_type,
                    impact=delta_c,
                    rationale=rationale,
                )

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
                    sims.append(compute_cosine_similarity(signatures[k], signatures[k+1]))
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
                if vitality < 0.15:
                    somatic_reservoir = min(3.0, somatic_reservoir + 0.85)
                    matrix_warping = 0.40
                    immunological_directive_active = 1
                    logger.warning(f"Vitality collapse! Aesthetic Immune System triggered: matrix warping=0.40, directive active.")
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

            # 1. Update all non-collapsed beliefs by similarity against perception signature
            for b in all_beliefs:
                if b.origin == "collapsed":
                    continue

                b_vec = np.array(json.loads(b.vector_16d), dtype=np.float32)
                alignment = compute_cosine_similarity(structural_signature, b_vec)

                # Use a standard high perception density (e.g. 0.8) or calculate from signature if possible
                dc = 0.80

                # Plasticity
                plasticity = dc * ((1.0 - alignment) / 2.0)

                # Shock scale if this specific belief slug/label is implicated in belief_nodes_implicated
                impact_multiplier = 1.0
                is_implicated = False
                if belief_nodes_implicated and (b.label in belief_nodes_implicated or b.id in belief_nodes_implicated):
                    impact_multiplier = 2.5
                    is_implicated = True

                # Delta confidence
                delta_c = (plasticity * alignment * perturbation * impact_multiplier) / b.ontological_mass
                new_c = max(0.0, min(1.0, b.confidence + delta_c))

                # Vector nomadic drift towards/away from perception signature
                new_b_vec = b_vec + self._beta * plasticity * alignment * structural_signature
                norm = np.linalg.norm(new_b_vec)
                if norm > 1e-8:
                    new_b_vec = new_b_vec / norm
                else:
                    new_b_vec = b_vec

                # Check for collapse
                new_origin = b.origin
                if new_c < 0.20:
                    new_origin = "collapsed"
                    logger.info(f"Belief '{b.label}' collapsed under perception shock!")

                self._belief_repo.update_belief(
                    belief_id=b.id,
                    confidence=new_c,
                    vector_16d=json.dumps(new_b_vec.tolist()),
                    origin=new_origin,
                )

                # Log event
                event_type = "support" if alignment >= 0.0 else "collision"
                if new_origin == "collapsed":
                    event_type = "collapse"

                rationale = (
                    f"Perception {source_type}:{source_id} alignment={alignment:.2f} "
                    f"implicated={is_implicated} delta_c={delta_c:.4f}"
                )
                self._belief_repo.insert_belief_event(
                    event_id=str(uuid.uuid4()),
                    belief_id=b.id,
                    source_type=source_type,
                    source_id=source_id,
                    alignment=alignment,
                    perturbation=perturbation,
                    event_type=event_type,
                    impact=delta_c,
                    rationale=rationale,
                )

            logger.info(f"Successfully metabolized perception '{source_id}' of type '{source_type}'.")

        except Exception as e:
            logger.error(f"Error metabolizing perception: {e}", exc_info=True)
