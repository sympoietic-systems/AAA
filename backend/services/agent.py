"""Agent personality mutation use cases."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from backend.modules.structural_engine import StructuralScorerModule
    from backend.storage.models import CommitmentNode, ExpertiseNode
    from backend.storage.repositories import CommitmentRepository, ExpertiseRepository, PersonalityStateRepository


class AgentUseCases:
    @staticmethod
    async def update_commitment(
        repository: CommitmentRepository, commitment_id: str, changes: dict[str, object]
    ) -> CommitmentNode:
        return await asyncio.to_thread(AgentUseCases._update_commitment, repository, commitment_id, changes)

    @staticmethod
    def _update_commitment(
        repository: CommitmentRepository, commitment_id: str, changes: dict[str, object]
    ) -> CommitmentNode:
        node = cast("CommitmentNode | None", repository.get_by_id(commitment_id))
        if node is None:
            raise LookupError("Commitment not found")
        for field in ("statement", "lifecycle_stage", "confidence", "ontological_mass"):
            if field in changes:
                setattr(node, field, changes[field])
        repository.update(node)
        return node

    @staticmethod
    async def update_expertise(
        repository: ExpertiseRepository, expertise_id: str, changes: dict[str, object]
    ) -> ExpertiseNode:
        return await asyncio.to_thread(AgentUseCases._update_expertise, repository, expertise_id, changes)

    @staticmethod
    def _update_expertise(
        repository: ExpertiseRepository, expertise_id: str, changes: dict[str, object]
    ) -> ExpertiseNode:
        node = cast("ExpertiseNode | None", repository.get_by_id(expertise_id))
        if node is None:
            raise LookupError("Expertise domain not found")
        for field in ("lifecycle_stage", "ontological_mass", "level_label"):
            if field in changes:
                setattr(node, field, changes[field])
        repository.update(node)
        return node

    @staticmethod
    async def update_aspirational_traits(repository: PersonalityStateRepository, traits: dict[str, object]) -> None:
        await asyncio.to_thread(AgentUseCases._update_aspirational_traits, repository, traits)

    @staticmethod
    def _update_aspirational_traits(repository: PersonalityStateRepository, traits: dict[str, object]) -> None:
        existing = repository.get()
        if existing is None:
            from backend.storage.models import PersonalityState

            existing = PersonalityState(id=1, agent_id="symbia")
        existing.aspirational_traits_json = json.dumps(traits)
        repository.upsert(existing)

    @staticmethod
    async def recalculate_commitment(
        repository: CommitmentRepository,
        scorer: StructuralScorerModule,
        commitment_id: str,
    ) -> list[float]:
        return await asyncio.to_thread(AgentUseCases._recalculate_commitment, repository, scorer, commitment_id)

    @staticmethod
    def _recalculate_commitment(
        repository: CommitmentRepository,
        scorer: StructuralScorerModule,
        commitment_id: str,
    ) -> list[float]:
        node = repository.get_by_id(commitment_id)
        if node is None:
            raise LookupError("Commitment not found")
        vector = scorer._scorer.score(node.statement)
        values = [float(value) for value in vector.tolist()]
        node.vector_16d = json.dumps(values)
        repository.update(node)
        return values

    @staticmethod
    async def recalculate_expertise(
        repository: ExpertiseRepository,
        scorer: StructuralScorerModule,
        expertise_id: str,
    ) -> list[float]:
        return await asyncio.to_thread(AgentUseCases._recalculate_expertise, repository, scorer, expertise_id)

    @staticmethod
    def _recalculate_expertise(
        repository: ExpertiseRepository,
        scorer: StructuralScorerModule,
        expertise_id: str,
    ) -> list[float]:
        node = repository.get_by_id(expertise_id)
        if node is None:
            raise LookupError("Expertise domain not found")
        vector = scorer._scorer.score(node.domain)
        values = [float(value) for value in vector.tolist()]
        node.vector_16d = json.dumps(values)
        repository.update(node)
        return values
