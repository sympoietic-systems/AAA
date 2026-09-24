"""Belief Ecosystem Manager — Tension fields, eco-vitality, and ghost ecology."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

import numpy as np

from backend.modules.belief_math import parse_vector_16d
from backend.storage.repositories import BeliefRepository
from backend.utils.vector import cosine_similarity

logger = logging.getLogger(__name__)


class EcosystemManager:
    """Computes ecosystem health, tension fields, ghost resurrection, and ghost merging/fading."""

    @staticmethod
    def compute_ecosystem_health(
        belief_repo: BeliefRepository,
        agent_id: str = "symbia",
        source_weights: dict | None = None,
        beta: float = 0.05,
    ) -> tuple[dict, float]:
        all_beliefs = belief_repo.list_beliefs(agent_id)
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
        total_tension = belief_repo.get_total_system_tension()
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

        updated_beta = beta
        if plasticity < 0.1:
            updated_beta = min(beta * 1.1, 0.15)
            tuning["learning_rate_beta"] = updated_beta

        if ghost_burden > 0.5:
            tuning["ghost_fading_accelerated"] = True

        health = {
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
        return health, updated_beta

    @staticmethod
    def compute_tension_field(belief_repo: BeliefRepository, agent_id: str = "symbia") -> dict:
        all_beliefs = belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage in ("crystallized", "senescence")]

        symbiotic_count = 0
        antagonistic_count = 0
        total_tension = 0.0

        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                try:
                    vec_a = parse_vector_16d(active[i].vector_16d)
                    vec_b = parse_vector_16d(active[j].vector_16d)
                    if vec_a is None or vec_b is None:
                        continue
                    sim = cosine_similarity(vec_a, vec_b)

                    if sim > 0.7:
                        symbiotic_count += 1
                    elif sim < -0.2:
                        tension = (1.0 + abs(sim)) * min(active[i].ontological_mass, active[j].ontological_mass)
                        total_tension += tension
                        antagonistic_count += 1
                        belief_repo.upsert_tension(active[i].id, active[j].id, sim, tension)
                except Exception:
                    continue

        return {
            "symbiotic_pairs": symbiotic_count,
            "antagonistic_pairs": antagonistic_count,
            "total_tension": total_tension,
        }

    @staticmethod
    def check_ghost_resurrection(belief_repo: BeliefRepository, agent_id: str = "symbia") -> int:
        ghosts = belief_repo.list_ghosts(agent_id)
        resurrected = 0

        for ghost in ghosts:
            events = belief_repo.get_events_for_belief(ghost.id)
            resurrection_events = [
                e
                for e in events
                if e.event_type == "support" and e.alignment_coefficient and e.alignment_coefficient > 0.6
            ]
            if len(resurrection_events) >= 3:
                resurrect_mass = 0.35
                belief_repo.update_belief(
                    belief_id=ghost.id,
                    confidence=max(0.30, ghost.confidence),
                    vector_16d=ghost.vector_16d,
                    origin=ghost.origin,
                    lifecycle_stage="accretion",
                )
                belief_repo.update_belief_mass(ghost.id, resurrect_mass)
                belief_repo.insert_belief_event(
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

    @staticmethod
    def process_ghost_ecology(belief_repo: BeliefRepository, agent_id: str = "symbia") -> dict:
        ghosts = belief_repo.list_ghosts(agent_id)
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
                    if vec_a is None or vec_b is None:
                        continue
                    sim = cosine_similarity(vec_a, vec_b)
                    if sim > 0.9:
                        keeper = ghosts[i] if ghosts[i].ontological_mass >= ghosts[j].ontological_mass else ghosts[j]
                        absorbed = ghosts[j] if keeper.id == ghosts[i].id else ghosts[i]
                        merged_ids.add(absorbed.id)
                        merged += 1
                        new_keeper_mass = min(keeper.ontological_mass + 0.1, 1.5)
                        mass_delta = new_keeper_mass - keeper.ontological_mass
                        belief_repo.update_belief(
                            belief_id=keeper.id,
                            confidence=keeper.confidence,
                            vector_16d=keeper.vector_16d,
                            origin=keeper.origin,
                            lifecycle_stage=keeper.lifecycle_stage,
                        )
                        belief_repo.update_belief_mass(keeper.id, new_keeper_mass)
                        belief_repo.insert_belief_event(
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
                        belief_repo.fold_ghost_into(absorbed.id, keeper.id)
                        logger.info(f"Merged ghost '{absorbed.label}' into '{keeper.label}' (sim={sim:.2f})")
                except Exception:
                    continue

        # Ghost fading: no activity > 30 days
        for ghost in ghosts:
            if ghost.id in merged_ids:
                continue
            last_active = ghost.last_reinforced_at or ghost.updated_at
            if last_active and (datetime.now(UTC) - last_active.replace(tzinfo=UTC)) > timedelta(days=30):
                belief_repo.update_belief_stage(ghost.id, "faded")
                faded += 1
                logger.info(f"Ghost '{ghost.label}' faded permanently (30+ days inactive)")

        return {"merged": merged, "faded": faded}
