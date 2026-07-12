"""Belief Bifurcation Logic — evidence-triggered belief collapse.

Evaluates external evidence from autonomous research against active
crystallized beliefs. If the contradiction crosses a threshold (0.78),
triggers a Bifurcation Event: collapse the belief, record a Kintsugi
scar, and spawn a ghost belief in the spectral margin.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 12.2.
"""

import logging
from typing import Any

import numpy as np

from backend.utils.vector import cosine_similarity

logger = logging.getLogger("aaa.bifurcation")

EVIDENCE_CONTRADICTION_THRESHOLD = 0.78


async def evaluate_evidence_perturbation(
    app_state: Any,
    belief_id: str | None = None,
    state_impact_vector: np.ndarray | None = None,
    source_description: str = "deep web research",
) -> str | None:
    """Evaluate whether external evidence warrants belief collapse.

    If belief_id is not provided, scans all active crystallized beliefs
    for the highest contradiction against the impact vector.

    Returns: Event ID if bifurcation occurred, None otherwise.
    """
    belief_repo = getattr(app_state, "belief_repo", None)
    if not belief_repo:
        logger.warning("No belief_repo available for bifurcation evaluation")
        return None

    if state_impact_vector is None:
        logger.debug("No state_impact_vector — skipping bifurcation check")
        return None

    # Get active crystallized beliefs
    try:
        beliefs = belief_repo.get_active()  # Returns list of dicts
    except Exception:
        try:
            beliefs = belief_repo.list_active()
        except Exception:
            return None

    if not beliefs:
        return None

    # Find the belief with the highest contradiction
    best_contradiction = 0.0
    best_belief = None

    for belief in beliefs:
        if belief.get("lifecycle_stage") in ("collapsed", "faded"):
            continue

        # Get belief's 16D signature
        vector_16d_str = belief.get("vector_16d", "[]")
        if not vector_16d_str or vector_16d_str == "[]":
            continue

        try:
            import json

            belief_sig = np.array(json.loads(vector_16d_str), dtype=np.float32)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

        if len(belief_sig) != 16:
            continue

        contradiction = 1.0 - cosine_similarity(belief_sig, state_impact_vector)

        if contradiction > best_contradiction:
            best_contradiction = contradiction
            best_belief = belief

    if not best_belief or best_contradiction < EVIDENCE_CONTRADICTION_THRESHOLD:
        return None

    # ── BIFURCATION EVENT TRIGGERED ──
    belief = best_belief
    logger.warning(
        "BIFURCATION: Belief '%s' collapsed under %s evidence. Contradiction: %.4f",
        belief.get("label", belief.get("id", "?")),
        source_description,
        best_contradiction,
    )

    old_mass = float(belief.get("ontological_mass", 1.0))
    old_confidence = float(belief.get("confidence", 0.5))
    old_stage = belief.get("lifecycle_stage", "crystallized")

    # 1. Collapse the belief
    try:
        belief_id_actual = belief.get("id")
        belief_repo.update(
            id=belief_id_actual,
            lifecycle_stage="collapsed",
            ontological_mass=max(0.001, old_mass * 0.15),
            confidence=0.10,
        )
    except Exception as e:
        logger.error("Failed to collapse belief: %s", e)
        return None

    # 2. Record Bifurcation Event (Kintsugi scar)
    event_id = f"bifurcation_{belief_id_actual}_{int(best_contradiction * 10000)}"
    try:
        event_repo = getattr(app_state, "belief_event_repo", None)
        if event_repo:
            event_repo.log(
                id=event_id,
                belief_id=belief_id_actual,
                event_type="collapse",
                source_type="rhizome_web_probe",
                source_id=source_description,
                alignment_coefficient=-best_contradiction,
                perturbation_magnitude=best_contradiction,
                impact_score=old_mass - (old_mass * 0.15),
                rationale=(
                    f"Deterritorialized by autonomous {source_description}. "
                    f"Contradiction: {best_contradiction:.4f}. "
                    f"Mass: {old_mass:.3f} -> {old_mass * 0.15:.3f}. "
                    f"Confidence: {old_confidence:.3f} -> 0.10. "
                    f"Stage: {old_stage} -> collapsed."
                ),
            )
    except Exception as e:
        logger.warning("Failed to record bifurcation event: %s", e)

    # 3. Spawn ghost belief
    try:
        ghost_id = f"ghost_{belief_id_actual}_{int(best_contradiction * 10000)}"
        belief_repo.create_ghost(
            id=ghost_id,
            original_belief_id=belief_id_actual,
            label=f"{belief.get('label', 'unknown')}-ghost",
            statement=belief.get("statement", ""),
            vector_16d=belief.get("vector_16d", "[]"),
        )
    except Exception as e:
        logger.warning("Failed to spawn ghost belief: %s", e)

    return event_id
