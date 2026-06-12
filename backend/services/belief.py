import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BeliefService:
    def __init__(self, state):
        self._state = state

    async def get_beliefs(self, conversation_id: Optional[str] = None, agent_id: str = "symbia") -> dict:
        state = self._state
        belief_repo = getattr(state, "belief_repo", None)
        engine = getattr(state, "belief_metabolism", None)
        if not belief_repo:
            return {"beliefs": [], "proto_beliefs": [], "ghosts": [], "somatic": None,
                    "attractor_window": [], "spectral_margin": [], "ecosystem": None}

        raw_beliefs = belief_repo.list_beliefs(agent_id)
        beliefs_list = []
        proto_beliefs_list = []
        ghosts_list = []

        for b in raw_beliefs:
            events = belief_repo.get_events_for_belief(b.id)
            if b.ontological_mass >= 1.5:
                cat = "foundational"
            elif b.ontological_mass >= 1.2:
                cat = "ontological"
            else:
                cat = "methodological"

            belief_data = {
                "id": b.id,
                "label": b.label,
                "statement": b.statement,
                "category": cat,
                "confidence": b.confidence,
                "ontological_mass": b.ontological_mass,
                "vector_16d": b.vector_16d,
                "origin": b.origin,
                "lifecycle_stage": b.lifecycle_stage,
                "last_reinforced_at": b.last_reinforced_at.isoformat() if b.last_reinforced_at else None,
                "updated_at": b.updated_at.isoformat() if b.updated_at else None,
                "events": [
                    {
                        "id": e.id, "timestamp": e.timestamp.isoformat(),
                        "source_id": e.source_id, "source_type": e.source_type,
                        "delta_confidence": e.impact_score, "description": e.rationale,
                    }
                    for e in events
                ],
            }

            stage = b.lifecycle_stage
            if stage in ("crystallized", "senescence"):
                beliefs_list.append(belief_data)
            elif stage in ("nucleation", "accretion"):
                proto_beliefs_list.append(belief_data)
            elif stage == "collapsed":
                ghosts_list.append(belief_data)

        somatic_state = None
        attractor_window = []
        spectral_margin = []

        if conversation_id:
            somatic = belief_repo.get_conversation_somatic_state(conversation_id)
            if somatic:
                somatic_state = {
                    "somatic_reservoir_ad": somatic.get("somatic_reservoir_ad", 0.0),
                    "matrix_warping": somatic.get("matrix_warping", 0.0),
                    "immunological_directive_active": bool(somatic.get("immunological_directive_active", 0)),
                }

                if engine:
                    try:
                        active = [b for b in raw_beliefs if b.lifecycle_stage not in ("collapsed", "faded") and b.confidence >= 0.20]
                        collapsed = [b for b in raw_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20]

                        if active:
                            slot1 = max(active, key=lambda b: b.ontological_mass)
                            attractors = [slot1]
                            stressed = [b for b in active if b.confidence < 0.50]
                            slot2 = min(stressed, key=lambda b: b.confidence) if stressed else None
                            if slot2:
                                attractors.append(slot2)
                            remaining = [b for b in active if b.id != slot1.id and b.id != (slot2.id if slot2 else None)]
                            if remaining:
                                attractors.append(remaining[0])
                            attractor_window = [a.label for a in attractors]

                        spectral_margin = [b.label for b in collapsed]
                    except Exception as e:
                        logger.error("Error computing UI attractor window: %s", e)

        ecosystem = None
        if engine:
            try:
                ecosystem = await engine.compute_ecosystem_health(agent_id)
            except Exception as e:
                logger.error("Error computing ecosystem health: %s", e)

        return {
            "beliefs": beliefs_list,
            "proto_beliefs": proto_beliefs_list,
            "ghosts": ghosts_list,
            "somatic": somatic_state,
            "attractor_window": attractor_window,
            "spectral_margin": spectral_margin,
            "ecosystem": ecosystem,
        }
