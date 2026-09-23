"""Belief Decay Manager — Turn-based decay and inactivity atrophy."""

import logging
import uuid
from datetime import UTC, datetime

from backend.storage.repository import BeliefRepository

logger = logging.getLogger(__name__)


class DecayManager:
    """Manages turn-based decay and time-based atrophy for beliefs."""

    @staticmethod
    def apply_turn_decay(
        belief_repo: BeliefRepository,
        agent_id: str,
        engaged_belief_id: str | None = None,
    ) -> dict:
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
    def atrophy_beliefs(belief_repo: BeliefRepository, agent_id: str) -> dict:
        """Apply time-based mass decay to active beliefs that haven't been reinforced recently.

        Decay rate: ~0.1% per hour of inactivity. Beliefs that are actively engaged
        (frequently matched in metabolism) stay stable; neglected beliefs slowly lose mass
        and can eventually collapse. Covers all non-collapsed, non-faded stages.
        """
        all_beliefs = belief_repo.list_beliefs(agent_id)
        active = [b for b in all_beliefs if b.lifecycle_stage not in ("collapsed", "faded")]

        now = datetime.now(UTC)
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
                    last_dt = last_dt.replace(tzinfo=UTC)

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

                belief_repo.update_belief(
                    belief_id=belief.id,
                    confidence=belief.confidence,
                    vector_16d=belief.vector_16d,
                    origin=belief.origin,
                    lifecycle_stage=new_stage,
                    suppress_stage_notification=True,
                )
                belief_repo.update_belief_mass(belief.id, new_mass, touch_reinforced=False)

                belief_repo.insert_belief_event(
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
