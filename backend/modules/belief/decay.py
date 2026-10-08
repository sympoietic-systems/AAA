"""Belief Decay Manager — Turn-based decay and inactivity atrophy."""

import logging
from datetime import UTC, datetime

from backend.storage.repositories import BeliefRepository

logger = logging.getLogger(__name__)


class DecayManager:
    """Manages turn-based decay and time-based atrophy for beliefs."""

    @staticmethod
    def apply_turn_decay(
        belief_repo: BeliefRepository,
        agent_id: str,
        engaged_belief_id: str | None = None,
    ) -> dict[str, int]:
        """Apply discrete per-turn mass decay to active beliefs that were not engaged this turn.

        Turn-based decay only occurs when conversations or dream resonance turns actually run.
        Crystallized beliefs are protected by a strict floor (e.g. 0.55), ensuring disuse alone
        cannot collapse or demote them into senescence.
        """
        try:
            from backend.config import load_config

            cfg = load_config()
            decay_cfg = cfg.get("belief_ecosystem", {}).get("turn_decay", {})
        except Exception:
            decay_cfg = {}

        if not decay_cfg.get("enabled", True):
            return {"atrophied": 0, "collapsed": 0}

        decay_per_turn = float(decay_cfg.get("decay_per_turn", 0.0005))
        crystallized_floor = float(decay_cfg.get("crystallized_floor", 0.55))

        all_beliefs = belief_repo.list_beliefs(agent_id)
        active = [
            b for b in all_beliefs if b.lifecycle_stage not in ("collapsed", "faded") and b.id != engaged_belief_id
        ]

        atrophied = 0
        collapsed = 0

        for belief in active:
            current_mass = belief.ontological_mass
            if belief.lifecycle_stage == "crystallized":
                # Protected floor: cannot decay below floor due to lack of engagement
                if current_mass <= crystallized_floor:
                    continue
                new_mass = max(crystallized_floor, current_mass - decay_per_turn)
            else:
                new_mass = max(0.0, current_mass - decay_per_turn)

            if abs(new_mass - current_mass) < 1e-6:
                continue

            new_stage = belief.lifecycle_stage
            if belief.lifecycle_stage != "crystallized":
                if new_mass < 0.02:
                    new_stage = "collapsed"
                    collapsed += 1
                elif new_mass < 0.001:
                    new_stage = "faded"

            try:
                if new_stage in ("collapsed", "faded"):
                    belief_repo.update_belief(
                        belief_id=belief.id,
                        confidence=belief.confidence,
                        vector_16d=belief.vector_16d,
                        origin=belief.origin,
                        lifecycle_stage=new_stage,
                        suppress_stage_notification=True,
                    )
                belief_repo.update_belief_mass(belief.id, new_mass, touch_reinforced=False)
                atrophied += 1
            except Exception:
                logger.debug("Failed to apply turn decay to belief '%s'", belief.label, exc_info=True)
                continue

        if atrophied > 0:
            logger.debug(
                "Turn-based belief decay: %d unengaged beliefs decayed (decay_per_turn=%.5f, floor=%.2f)",
                atrophied,
                decay_per_turn,
                crystallized_floor,
            )

        return {"atrophied": atrophied, "collapsed": collapsed}

    @staticmethod
    def atrophy_beliefs(belief_repo: BeliefRepository, agent_id: str, *, now: datetime | None = None) -> dict[str, int]:
        """Charge only unaccounted elapsed time; storage failures remain visible.

        The repository rechecks each belief under its writer lock and atomically
        commits mass, checkpoint, and measured event. Wall-clock enablement remains
        the caller's responsibility; the default daemon configuration disables it.
        """
        clock = now or datetime.now(UTC)
        result = {"atrophied": 0, "collapsed": 0}
        for belief in belief_repo.list_beliefs(agent_id):
            if belief.lifecycle_stage in ("collapsed", "faded"):
                continue
            outcome = belief_repo.apply_elapsed_atrophy(agent_id, belief.id, clock)
            for key in result:
                result[key] += outcome[key]
        if result["atrophied"]:
            logger.info("Belief atrophy: %d decayed (%d collapsed)", result["atrophied"], result["collapsed"])
        return result
