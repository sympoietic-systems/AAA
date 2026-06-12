"""Mass decay and skill ecology mixin for the Dream Daemon."""

import logging
import uuid
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)


class MassDecayMixin:
    """Handles belief mass decay, skill ecology, and ghost skill resurrection."""

    async def _apply_mass_decay(self, idle_duration: float) -> None:
        if idle_duration < 10:
            return

        now = __import__("time").time()
        if not getattr(self, "last_decay_time", 0.0):
            self.last_decay_time = now - idle_duration

        elapsed = now - self.last_decay_time
        self.last_decay_time = now

        if elapsed < 10:
            return

        beliefs = self.belief_repo.list_beliefs("symbia")
        active_beliefs = [b for b in beliefs if b.lifecycle_stage not in ("collapsed", "faded")]

        if not active_beliefs:
            return

        max_mass = max(b.ontological_mass for b in active_beliefs) or 3.0
        decay_config = self.config.get("belief_ecosystem", {}).get("mass_decay", {})
        lambda_base = decay_config.get("lambda_base", 0.05)

        for b in active_beliefs:
            last_reinforced = b.last_reinforced_at
            if last_reinforced is None:
                continue

            hours_since = (datetime.now(timezone.utc) - last_reinforced.replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
            if hours_since < 1.0:
                continue

            norm_mass = b.ontological_mass / max(max_mass, 0.01)
            decay_rate = lambda_base * (1.0 - min(norm_mass, 0.9))
            new_mass = b.ontological_mass * np.exp(-decay_rate * hours_since)
            new_mass = max(0.0, min(3.0, new_mass))

            new_stage = b.lifecycle_stage
            if b.lifecycle_stage == "crystallized" and new_mass < 0.5:
                new_stage = "senescence"
            elif b.lifecycle_stage == "senescence" and new_mass < 0.02:
                new_stage = "collapsed"
            elif b.lifecycle_stage == "nucleation" and new_mass < 0.001:
                new_stage = "faded"

            if abs(new_mass - b.ontological_mass) < 1e-5 and new_stage == b.lifecycle_stage:
                continue

            self.belief_repo.update_belief_mass(b.id, new_mass)
            if new_stage != b.lifecycle_stage:
                self.belief_repo.update_belief_stage(b.id, new_stage)
                logger.info(f"Belief '{b.label}' mass decay: {b.lifecycle_stage} -> {new_stage} (mass={new_mass:.4f})")

        logger.debug("Applied mass decay to %d beliefs over %.0fs idle", len(active_beliefs), elapsed)
        await self._apply_skill_ecology(idle_duration)

    async def _apply_skill_ecology(self, idle_duration: float) -> None:
        skill_repo = getattr(self, "skill_repo", None)
        belief_repo = getattr(self, "belief_repo", None)
        if not skill_repo or not belief_repo:
            return

        skills = skill_repo.list_skills()
        if not skills:
            return

        now = datetime.now(timezone.utc)
        dormancy_hours = 72.0

        for skill in skills:
            if skill.lifecycle_stage in ("collapsed", "faded"):
                continue

            skill_beliefs = belief_repo.list_beliefs("symbia")
            skill_belief = next((b for b in skill_beliefs if b.label == f"skill:{skill.name}"), None)

            if not skill_belief:
                continue

            mass_mismatch = abs(skill_belief.ontological_mass - skill.ontological_mass) > 1e-3

            if mass_mismatch:
                skill_repo.update_skill_mass(
                    skill.id,
                    skill_belief.ontological_mass,
                    skill_belief.confidence,
                )

            new_stage = skill.lifecycle_stage
            if skill_belief.lifecycle_stage == "collapsed" and skill.lifecycle_stage != "collapsed":
                new_stage = "collapsed"
                skill_repo.update_skill(
                    skill_id=skill.id,
                    lifecycle_stage="collapsed",
                    confidence=skill_belief.confidence,
                    ontological_mass=skill_belief.ontological_mass,
                )
                skill_repo.insert_event(
                    id=str(uuid.uuid4()),
                    skill_id=skill.id,
                    event_type="collapse",
                    source_type="dream_turn",
                    rationale="Belief bridge collapsed — skill enters spectral margin",
                )
                logger.info("Skill '%s' collapsed via belief bridge (mass=%.4f)", skill.name, skill_belief.ontological_mass)

            elif skill_belief.lifecycle_stage == "crystallized" and skill.lifecycle_stage != "crystallized":
                new_stage = "crystallized"
                skill_repo.update_skill(
                    skill_id=skill.id,
                    lifecycle_stage="crystallized",
                    confidence=skill_belief.confidence,
                )

            if skill.lifecycle_stage == "crystallized" and skill.last_used_at:
                if hasattr(skill.last_used_at, 'tzinfo') and skill.last_used_at.tzinfo is not None:
                    last_used = skill.last_used_at
                else:
                    last_used = skill.last_used_at.replace(tzinfo=timezone.utc)
                hours_since_use = (now - last_used).total_seconds() / 3600.0

                if hours_since_use > dormancy_hours and skill.confidence < 0.3:
                    logger.info(
                        "Skill '%s' underperforming: dormant %.0fh, confidence %.2f",
                        skill.name, hours_since_use, skill.confidence,
                    )

        self._check_ghost_skill_resurrection(belief_repo, skill_repo)

    def _check_ghost_skill_resurrection(self, belief_repo, skill_repo) -> None:
        collapsed_skills = skill_repo.list_by_stage("collapsed")
        if not collapsed_skills:
            return

        for skill in collapsed_skills:
            events = skill_repo.list_events(skill.id)
            supporting_events = [
                e for e in events[-10:]
                if e.event_type in ("revision", "crystallization") and "resurrection" not in (e.rationale or "").lower()
            ]
            if len(supporting_events) < 3:
                continue

            skill_beliefs = belief_repo.list_beliefs("symbia")
            skill_belief = next((b for b in skill_beliefs if b.label == f"skill:{skill.name}"), None)

            if skill_belief and skill_belief.lifecycle_stage == "crystallized":
                skill_repo.update_skill(
                    skill_id=skill.id,
                    lifecycle_stage="accretion",
                    confidence=skill_belief.confidence,
                    ontological_mass=skill_belief.ontological_mass,
                )
                skill_repo.insert_event(
                    id=str(uuid.uuid4()),
                    skill_id=skill.id,
                    event_type="emergence",
                    source_type="dream_turn",
                    rationale="Ghost skill resurrected via belief bridge regeneration",
                )
                logger.info("Ghost skill '%s' resurrected to accretion", skill.name)
