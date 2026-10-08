"""Mass decay and skill ecology mixin for the Dream Daemon."""

import asyncio
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from backend.modules.belief.decay import DecayManager
from backend.storage.repositories import BeliefRepository, SkillRepository

logger = logging.getLogger(__name__)


class MassDecayMixin:
    """Handles belief mass decay, skill ecology, and ghost skill resurrection."""

    config: dict[str, Any]
    belief_repo: BeliefRepository
    skill_repo: SkillRepository | None
    last_decay_time: float

    async def _apply_mass_decay(self, idle_duration: float) -> None:
        if idle_duration < 10:
            return

        now = time.time()
        if not getattr(self, "last_decay_time", 0.0):
            self.last_decay_time = now - idle_duration

        elapsed = now - self.last_decay_time
        self.last_decay_time = now

        if elapsed < 10:
            return

        if self.config.get("belief_ecosystem", {}).get("wall_clock_decay", {}).get("enabled", False):
            # Compatibility entry point: share the durable accounting clock with
            # the daemon's active atrophy path rather than apply a second formula.
            await asyncio.to_thread(DecayManager.atrophy_beliefs, self.belief_repo, "symbia")
        await self._apply_skill_ecology(idle_duration)

    async def _apply_skill_ecology(self, idle_duration: float) -> None:
        skill_repo = getattr(self, "skill_repo", None)
        belief_repo = getattr(self, "belief_repo", None)
        if not skill_repo or not belief_repo:
            return

        skills = skill_repo.list_skills()
        if not skills:
            return

        now = datetime.now(UTC)
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

            if skill_belief.lifecycle_stage == "collapsed" and skill.lifecycle_stage != "collapsed":
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
                logger.info(
                    "Skill '%s' collapsed via belief bridge (mass=%.4f)", skill.name, skill_belief.ontological_mass
                )

            elif skill_belief.lifecycle_stage == "crystallized" and skill.lifecycle_stage != "crystallized":
                skill_repo.update_skill(
                    skill_id=skill.id,
                    lifecycle_stage="crystallized",
                    confidence=skill_belief.confidence,
                )

            if skill.lifecycle_stage == "crystallized" and skill.last_used_at:
                if hasattr(skill.last_used_at, "tzinfo") and skill.last_used_at.tzinfo is not None:
                    last_used = skill.last_used_at
                else:
                    last_used = skill.last_used_at.replace(tzinfo=UTC)
                hours_since_use = (now - last_used).total_seconds() / 3600.0

                if hours_since_use > dormancy_hours and skill.confidence < 0.3:
                    logger.info(
                        "Skill '%s' underperforming: dormant %.0fh, confidence %.2f",
                        skill.name,
                        hours_since_use,
                        skill.confidence,
                    )

        self._check_ghost_skill_resurrection(belief_repo, skill_repo)

    def _check_ghost_skill_resurrection(self, belief_repo: BeliefRepository, skill_repo: SkillRepository) -> None:
        collapsed_skills = skill_repo.list_by_stage("collapsed")
        if not collapsed_skills:
            return

        for skill in collapsed_skills:
            events = skill_repo.list_events(skill.id)
            supporting_events = [
                e
                for e in events[-10:]
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
