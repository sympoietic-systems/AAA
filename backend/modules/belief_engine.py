import logging
import json
import uuid
from datetime import datetime, timezone, timedelta
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
        self._source_weights = {
            "chat_turn": 0.4,
            "user_assertion": 0.4,
            "ingested_document": 0.5,
            "conversational_pattern": 0.4,
            "shared_note": 0.5,
            "web_retrieval": 0.15,
        }

    def _get_source_weight(self, source_type: str) -> float:
        return self._source_weights.get(source_type, 0.4)

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
        authored = [b for b in existing if b.origin == "authored"]
        if len(authored) > 0:
            return

        seed_path = self._identity_yaml_path.parent / "seed_beliefs.yaml"
        if not seed_path.exists():
            logger.warning(f"Seed beliefs file {seed_path} not found. Cannot seed beliefs.")
            return

        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            config_beliefs = data.get("beliefs", [])
            for cb in config_beliefs:
                label = cb.get("id")
                statement = cb.get("statement")
                confidence = cb.get("confidence", 0.5)
                category = cb.get("category", "ontological")

                if category == "foundational":
                    mass = 1.5
                elif category == "ontological":
                    mass = 1.2
                elif category == "methodological":
                    mass = 1.0
                else:
                    mass = 1.0

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
                    lifecycle_stage="crystallized",
                )
            logger.info(f"Successfully seeded {len(config_beliefs)} baseline beliefs for agent {agent_id}.")
        except Exception as e:
            logger.error(f"Error seeding beliefs: {e}", exc_info=True)

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
        all_labels = {b.label for b in existing}

        words = [w for w in statement.split() if w.isalnum()]
        label_words = words[:3] if words else ["proto"]
        label_base = "_".join(label_words).lower()
        label = label_base
        counter = 1
        while label in all_labels:
            label = f"{label_base}_{counter}"
            counter += 1

        initial_mass = 0.05 * source_weight / 0.5

        ghosts = [b for b in existing if b.lifecycle_stage == "collapsed"]
        resonance_jumped = False
        for ghost in ghosts:
            try:
                ghost_vec = np.array(json.loads(ghost.vector_16d), dtype=np.float32)
                ghost_sim = compute_cosine_similarity(vector, ghost_vec)
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

        belief_id = str(uuid.uuid4())
        stage = "nucleation" if initial_mass < 0.5 else "accretion"
        self._belief_repo.create_belief(
            id=belief_id,
            agent_id=agent_id,
            label=label,
            statement=statement,
            origin="emergent",
            confidence=0.10,
            ontological_mass=initial_mass,
            somatic_anchor="conceptual",
            vector_16d=json.dumps(vector.tolist()),
            lifecycle_stage=stage,
        )

        self._belief_repo.insert_belief_event(
            event_id=str(uuid.uuid4()),
            belief_id=belief_id,
            source_type=source_type,
            source_id=source_id,
            alignment=1.0,
            perturbation=1.0,
            event_type="emergence",
            impact=initial_mass,
            rationale=f"Proto-belief nucleated from {source_type}:{source_id} with mass={initial_mass:.3f}, stage={stage}",
        )

        logger.info(f"Nucleated proto-belief '{label}' (mass={initial_mass:.3f}, stage={stage})")
        return belief_id

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
        eta = 0.02
        current_mass = belief.ontological_mass
        delta_m = eta * source_weight * alignment / (1.0 + current_mass)

        new_mass = current_mass + delta_m
        new_mass = max(0.0, min(3.0, new_mass))

        new_confidence = belief.confidence
        dc = 0.5
        plasticity = dc * ((1.0 - alignment) / 2.0)
        delta_c = (plasticity * alignment * perturbation) / max(current_mass, 0.01)
        new_confidence = max(0.0, min(1.0, belief.confidence + delta_c))

        new_stage = self._compute_lifecycle_stage(belief, new_mass, new_confidence)

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
        )

        return new_mass

    def _compute_lifecycle_stage(
        self,
        belief: BeliefNode,
        new_mass: float,
        new_confidence: float,
    ) -> str:
        current_stage = belief.lifecycle_stage

        if new_confidence < 0.20:
            return "collapsed"
        if new_mass < 0.02:
            return "collapsed"
        if new_mass < 0.001:
            return "faded"

        if new_mass >= 0.5 and current_stage in ("nucleation", "accretion"):
            return "crystallized"

        if current_stage == "crystallized":
            return "crystallized"
        if current_stage == "senescence":
            if new_mass >= 0.5:
                return "crystallized"
            return "senescence"
        if current_stage == "collapsed":
            return "collapsed"
        if current_stage == "faded":
            return "faded"

        if new_mass < 0.1:
            return "nucleation"
        return "accretion"

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
                b_vec = np.array(json.loads(b.vector_16d), dtype=np.float32)
                sim = compute_cosine_similarity(input_vector, b_vec)
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
        active_beliefs = [b for b in all_beliefs if b.lifecycle_stage not in ("collapsed", "faded") and b.confidence >= 0.20]
        collapsed_beliefs = [b for b in all_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20]

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

            # 3. Proto-belief lifecycle: find closest match, accrete or nucleate
            closest = self._find_closest_active_belief(agent_id, user_vec, min_similarity=0.3)
            source_weight = self._get_source_weight("chat_turn")
            if closest is not None:
                b_vec = np.array(json.loads(closest.vector_16d), dtype=np.float32)
                alignment = compute_cosine_similarity(user_vec, b_vec)
                self._accrete_belief(closest, user_vec, source_weight, alignment, perturbation,
                                     source_type="chat_turn", source_id=str(user_message_id))
            elif dc > 0.3:
                self._nucleate_proto_belief(
                    agent_id=agent_id,
                    statement=user_msg.content[:200],
                    vector=user_vec,
                    source_type="chat_turn",
                    source_id=str(user_message_id),
                    source_weight=source_weight,
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
                if b.lifecycle_stage in ("collapsed", "faded"):
                    continue

                b_vec = np.array(json.loads(b.vector_16d), dtype=np.float32)
                alignment = compute_cosine_similarity(structural_signature, b_vec)

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
            all_beliefs = self._belief_repo.list_beliefs(agent_id)
            best_match = None
            best_sim = -1.0

            for b in all_beliefs:
                if b.lifecycle_stage in ("collapsed", "faded"):
                    continue
                b_vec = np.array(json.loads(b.vector_16d), dtype=np.float32)
                sim = compute_cosine_similarity(note_vec, b_vec)
                if sim > best_sim:
                    best_sim = sim
                    best_match = b

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
            if closest is not None:
                b_vec = np.array(json.loads(closest.vector_16d), dtype=np.float32)
                alignment = compute_cosine_similarity(web_vec, b_vec)
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
            if closest is not None:
                b_vec = np.array(json.loads(closest.vector_16d), dtype=np.float32)
                alignment = compute_cosine_similarity(theme_vec, b_vec)
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
                        vec_a = np.array(json.loads(active[i].vector_16d), dtype=np.float32)
                        vec_b = np.array(json.loads(active[j].vector_16d), dtype=np.float32)
                        distances.append(1.0 - abs(compute_cosine_similarity(vec_a, vec_b)))
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
                    vec_a = np.array(json.loads(active[i].vector_16d), dtype=np.float32)
                    vec_b = np.array(json.loads(active[j].vector_16d), dtype=np.float32)
                    sim = compute_cosine_similarity(vec_a, vec_b)

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
                    vec_a = np.array(json.loads(ghosts[i].vector_16d), dtype=np.float32)
                    vec_b = np.array(json.loads(ghosts[j].vector_16d), dtype=np.float32)
                    sim = compute_cosine_similarity(vec_a, vec_b)
                    if sim > 0.9:
                        keeper = ghosts[i] if ghosts[i].ontological_mass >= ghosts[j].ontological_mass else ghosts[j]
                        absorbed = ghosts[j] if keeper.id == ghosts[i].id else ghosts[i]
                        merged_ids.add(absorbed.id)
                        merged += 1
                        keeper_statement = f"{keeper.statement} [absorbed: {absorbed.statement}]"
                        self._belief_repo.update_belief(
                            belief_id=keeper.id,
                            confidence=keeper.confidence,
                            vector_16d=keeper.vector_16d,
                            origin=keeper.origin,
                            lifecycle_stage=keeper.lifecycle_stage,
                        )
                        self._belief_repo.update_belief_mass(keeper.id, min(keeper.ontological_mass + 0.1, 1.5))
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

