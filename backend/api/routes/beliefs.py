import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/beliefs")
async def get_beliefs(request: Request, conversation_id: Optional[str] = None, agent_id: str = "symbia"):
    state = request.app.state
    belief_repo = getattr(state, "belief_repo", None)
    if not belief_repo:
        raise HTTPException(status_code=503, detail="Belief repository not initialized")

    engine = getattr(state, "belief_metabolism", None)
    if engine:
        try:
            engine._seed_initial_beliefs_if_needed(agent_id)
        except Exception as e:
            logger.error(f"Error seeding beliefs in get_beliefs: {e}")

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
                    "id": e.id,
                    "timestamp": e.timestamp.isoformat(),
                    "source_id": e.source_id,
                    "source_type": e.source_type,
                    "delta_confidence": e.impact_score,
                    "description": e.rationale
                }
                for e in events
            ]
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
                "immunological_directive_active": bool(somatic.get("immunological_directive_active", 0))
            }

            engine = getattr(state, "belief_metabolism", None)
            if engine:
                try:
                    active_beliefs = [b for b in raw_beliefs if b.lifecycle_stage not in ("collapsed", "faded") and b.confidence >= 0.20]
                    collapsed_beliefs = [b for b in raw_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20]

                    if active_beliefs:
                        slot1 = max(active_beliefs, key=lambda b: b.ontological_mass)
                        slot2 = None
                        stressed_beliefs = [b for b in active_beliefs if b.confidence < 0.50]
                        if stressed_beliefs:
                            slot2 = min(stressed_beliefs, key=lambda b: b.confidence)

                        slot3 = None
                        remaining = [b for b in active_beliefs if b.id != slot1.id and (not slot2 or b.id != slot2.id)]
                        if remaining:
                            slot3 = remaining[0]

                        attractors = [slot1]
                        if slot2: attractors.append(slot2)
                        if slot3: attractors.append(slot3)

                        attractor_window = [a.label for a in attractors]

                    spectral_margin = [b.label for b in collapsed_beliefs]
                except Exception as e:
                    logger.error(f"Error computing UI attractor window: {e}")

    ecosystem = None
    engine = getattr(state, "belief_metabolism", None)
    if engine:
        try:
            ecosystem = await engine.compute_ecosystem_health(agent_id)
        except Exception as e:
            logger.error(f"Error computing ecosystem health: {e}")

    return {
        "beliefs": beliefs_list,
        "proto_beliefs": proto_beliefs_list,
        "ghosts": ghosts_list,
        "somatic": somatic_state,
        "attractor_window": attractor_window,
        "spectral_margin": spectral_margin,
        "ecosystem": ecosystem
    }
