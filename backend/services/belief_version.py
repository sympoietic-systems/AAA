"""Belief statement-version use cases."""

import json
import logging
import uuid
from typing import cast

from backend.services.belief_common import BeliefResult, BeliefUseCase, _score_statement_16d
from backend.services.belief_ports import BeliefVersionRepository

logger = logging.getLogger(__name__)


class BeliefVersionUseCases(BeliefUseCase):
    async def update_belief_statement(
        self, belief_id: str, statement: str, change_reason: str | None = None
    ) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefVersionRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        active_beliefs = belief_repo.list_beliefs("symbia")
        target_belief = None
        for b in active_beliefs:
            if b.id == belief_id:
                target_belief = b
                break

        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        from backend.modules.belief_math import parse_vector_16d
        from backend.utils.vector import cosine_similarity

        new_v16d_json = await _score_statement_16d(state, statement)
        if not new_v16d_json or new_v16d_json == "[]":
            return {"status": "error", "message": "Failed to score statement"}

        # Update belief statement and bump version
        new_version = target_belief.version + 1
        with belief_repo.atomic():
            belief_repo.update_belief_statement(
                belief_id=target_belief.id, statement=statement, vector_16d=new_v16d_json, version=new_version
            )
            belief_repo.create_statement_version(
                id=str(uuid.uuid4()),
                belief_id=target_belief.id,
                version=new_version,
                statement=statement,
                vector_16d=new_v16d_json,
                change_reason=change_reason or "Statement edited by user/agent",
            )

        old_vec = parse_vector_16d(target_belief.vector_16d)
        new_vec = parse_vector_16d(new_v16d_json)

        speciation_triggered = False
        if old_vec is not None and new_vec is not None:
            sim = cosine_similarity(old_vec, new_vec)
            dist = 1.0 - sim
            if dist > 0.4:
                speciation_triggered = True
                notif_repo = getattr(state, "notification_repo", None)
                if notif_repo:
                    notif_repo.create(
                        type="glitch",
                        snippet=f"Speciation Alert: Belief '{target_belief.label}' has drifted significantly (distance={dist:.2f}). Consider forking into multiple concepts.",
                        source=f"belief:{target_belief.label}",
                        source_type="belief",
                        source_id=target_belief.id,
                    )

        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo and not speciation_triggered:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{target_belief.label}' updated statement to version {new_version}.",
                source=f"belief:{target_belief.label}",
                source_type="belief",
                source_id=target_belief.id,
            )

        return {
            "status": "ok",
            "belief_id": target_belief.id,
            "version": new_version,
            "speciation_alert": speciation_triggered,
        }

    async def get_statement_versions(self, belief_id: str) -> list[BeliefResult]:
        state = self._state
        belief_repo = cast(BeliefVersionRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return []

        versions = belief_repo.list_statement_versions(belief_id)
        return [
            {
                "id": v.id,
                "belief_id": v.belief_id,
                "version": v.version,
                "statement": v.statement,
                "vector_16d": json.loads(v.vector_16d) if v.vector_16d else [],
                "change_reason": v.change_reason,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def revert_belief_version(self, belief_id: str, version: int) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefVersionRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        # Fetch the version from DB
        version_data = belief_repo.get_statement_version(belief_id, version)
        if not version_data:
            return {"status": "error", "message": f"Version {version} for belief {belief_id} not found"}

        # Retrieve the current belief
        target_belief = belief_repo.get_belief("symbia", belief_id)
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        from backend.modules.belief_math import parse_vector_16d
        from backend.utils.vector import cosine_similarity

        label = target_belief.label
        statement = version_data.statement
        vector_16d_str = version_data.vector_16d

        new_version = target_belief.version + 1

        # Check speciation
        speciation_triggered = False
        old_vec = parse_vector_16d(target_belief.vector_16d)
        new_vec = parse_vector_16d(vector_16d_str)
        if old_vec is not None and new_vec is not None:
            sim = cosine_similarity(old_vec, new_vec)
            dist = 1.0 - sim
            if dist > 0.4:
                speciation_triggered = True
                notif_repo = getattr(state, "notification_repo", None)
                if notif_repo:
                    notif_repo.create(
                        type="glitch",
                        snippet=f"Speciation Alert: Belief '{label}' has drifted significantly (distance={dist:.2f}) after reverting to version {version}.",
                        source=f"belief:{label}",
                        source_type="belief",
                        source_id=belief_id,
                    )

        with belief_repo.atomic():
            belief_repo.create_statement_version(
                id=str(uuid.uuid4()),
                belief_id=belief_id,
                version=new_version,
                statement=statement,
                vector_16d=vector_16d_str,
                change_reason=f"Reverted to version {version}",
            )
            belief_repo.update_belief_details(
                belief_id=belief_id,
                label=label,
                statement=statement,
                confidence=target_belief.confidence,
                ontological_mass=target_belief.ontological_mass,
                lifecycle_stage=target_belief.lifecycle_stage,
                vector_16d=vector_16d_str,
                version=new_version,
            )

        # Log event
        try:
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=belief_id,
                source_type="user_assertion",
                source_id=None,
                alignment=1.0,
                perturbation=0.5,
                event_type="revision",
                impact=0.1,
                rationale=f"Reverted statement to version {version} via Agent FLUX API",
            )
        except Exception as e:
            logger.warning("Failed to insert event for belief revert: %s", e)

        # Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo and not speciation_triggered:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' reverted statement to version {version}.",
                source=f"belief:{label}",
                source_type="belief",
                source_id=belief_id,
            )

        return {
            "status": "ok",
            "belief_id": belief_id,
            "version": new_version,
            "speciation_alert": speciation_triggered,
        }
