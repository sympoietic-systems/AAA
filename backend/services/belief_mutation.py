"""Belief mutation use cases."""

import logging
import uuid
from typing import cast

from backend.services.belief_common import BeliefResult, BeliefUseCase, _score_statement_16d
from backend.services.belief_ports import BeliefMutationRepository

logger = logging.getLogger(__name__)


class BeliefMutationUseCases(BeliefUseCase):
    async def create_new_belief(
        self,
        label: str,
        statement: str,
        confidence: float = 0.5,
        ontological_mass: float = 0.5,
        lifecycle_stage: str = "crystallized",
        agent_id: str = "symbia",
    ) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefMutationRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        belief_id = str(uuid.uuid4())
        v16d_json = await _score_statement_16d(state, statement)
        if not v16d_json or v16d_json == "[]":
            return {"status": "error", "message": "Failed to score statement"}

        with belief_repo.atomic():
            belief_repo.create_belief(
                id=belief_id,
                agent_id=agent_id,
                label=label,
                statement=statement,
                origin="authored",
                confidence=confidence,
                ontological_mass=ontological_mass,
                somatic_anchor="conceptual",
                vector_16d=v16d_json,
                lifecycle_stage=lifecycle_stage,
            )
            belief_repo.create_statement_version(
                id=str(uuid.uuid4()),
                belief_id=belief_id,
                version=1,
                statement=statement,
                vector_16d=v16d_json,
                change_reason="Created manually via Agent FLUX API",
            )

        # 4. Log event
        try:
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=belief_id,
                source_type="user_assertion",
                source_id=None,
                alignment=1.0,
                perturbation=1.0,
                event_type="emergence",
                impact=ontological_mass,
                rationale="Created manually via Agent FLUX API",
            )
        except Exception as e:
            logger.warning("Failed to insert event for belief creation: %s", e)

        # 5. Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' was manually created.",
                source=f"belief:{label}",
                source_type="belief",
                source_id=belief_id,
            )

        return {"status": "ok", "belief_id": belief_id, "label": label}

    async def update_belief_details(
        self,
        belief_id: str,
        label: str,
        statement: str,
        confidence: float,
        ontological_mass: float,
        lifecycle_stage: str,
    ) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefMutationRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        # Find existing belief
        target_belief = belief_repo.get_belief("symbia", belief_id)
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        from backend.modules.belief_math import parse_vector_16d
        from backend.utils.vector import cosine_similarity

        new_v16d_json = await _score_statement_16d(state, statement)
        if not new_v16d_json or new_v16d_json == "[]":
            return {"status": "error", "message": "Failed to score statement"}

        statement_changed = target_belief.statement != statement
        new_version = target_belief.version
        speciation_triggered = False

        if statement_changed:
            new_version = target_belief.version + 1
            # Check speciation
            old_vec = parse_vector_16d(target_belief.vector_16d)
            new_vec = parse_vector_16d(new_v16d_json)
            if old_vec is not None and new_vec is not None:
                sim = cosine_similarity(old_vec, new_vec)
                dist = 1.0 - sim
                if dist > 0.4:
                    speciation_triggered = True
                    notif_repo = getattr(state, "notification_repo", None)
                    if notif_repo:
                        notif_repo.create(
                            type="glitch",
                            snippet=f"Speciation Alert: Belief '{label}' has drifted significantly (distance={dist:.2f}) after edit.",
                            source=f"belief:{label}",
                            source_type="belief",
                            source_id=belief_id,
                        )

        with belief_repo.atomic():
            if statement_changed:
                belief_repo.create_statement_version(
                    id=str(uuid.uuid4()),
                    belief_id=target_belief.id,
                    version=new_version,
                    statement=statement,
                    vector_16d=new_v16d_json,
                    change_reason="Statement edited via Agent FLUX API",
                )
            belief_repo.update_belief_details(
                belief_id=belief_id,
                label=label,
                statement=statement,
                confidence=confidence,
                ontological_mass=ontological_mass,
                lifecycle_stage=lifecycle_stage,
                vector_16d=new_v16d_json,
                version=new_version,
            )

        # 3. Log event with actual deltas
        try:
            mass_delta = ontological_mass - target_belief.ontological_mass
            conf_delta = confidence - target_belief.confidence
            rationale = (
                f"Updated: mass={ontological_mass:.3f} (delta={mass_delta:+.3f}), "
                f"conf={confidence:.3f} (delta={conf_delta:+.3f}), "
                f"stage={lifecycle_stage}"
            )
            belief_repo.insert_belief_event(
                event_id=str(uuid.uuid4()),
                belief_id=belief_id,
                source_type="user_assertion",
                source_id=None,
                alignment=1.0 if mass_delta >= 0 else -1.0,
                perturbation=abs(mass_delta),
                event_type="revision",
                impact=mass_delta,
                rationale=rationale,
            )
        except Exception as e:
            logger.warning("Failed to insert event for belief update: %s", e)

        # 4. Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo and not speciation_triggered:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' details were updated.",
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

    async def delete_belief(self, belief_id: str) -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefMutationRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        # Retrieve the belief to verify it exists
        target_belief = belief_repo.get_belief("symbia", belief_id)
        if not target_belief:
            return {"status": "error", "message": "Belief not found"}

        label = target_belief.label
        belief_repo.delete_belief(belief_id)

        # Log notification
        notif_repo = getattr(state, "notification_repo", None)
        if notif_repo:
            notif_repo.create(
                type="trace",
                snippet=f"Belief '{label}' was manually deleted.",
                source=f"belief:{label}",
                source_type="belief",
                source_id=belief_id,
            )

        return {"status": "ok", "message": f"Belief {belief_id} deleted"}
