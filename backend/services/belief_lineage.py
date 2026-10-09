"""Validated, bounded source accounting reads; public HTTP authorization belongs to T11."""

import asyncio

from pydantic import TypeAdapter

from backend.services.belief_review_contracts import SourceAccounting, SourceAccountingEvent, SourceAccountingSummary
from backend.services.belief_review_store import _agent, _identifier
from backend.storage.repositories.cognitive.belief_lineage import BeliefLineageRepository


class BeliefLineageStore:
    def __init__(self, db_path: str) -> None:
        self.repository = BeliefLineageRepository(db_path)

    async def observation(self, agent_id: str, encounter_id: str) -> SourceAccounting | None:
        return await asyncio.to_thread(self._observation, _agent(agent_id), _identifier(encounter_id))

    def _observation(self, agent: str, encounter: str) -> SourceAccounting | None:
        result = self.repository.observation(agent, encounter)
        return SourceAccounting.model_validate(result) if result else None

    async def summary(self, agent_id: str, record_id: str, limit: int = 50) -> SourceAccountingSummary:
        bound = min(50, max(1, TypeAdapter(int).validate_python(limit, strict=True)))
        return await asyncio.to_thread(self._summary, _agent(agent_id), _identifier(record_id), bound)

    def _summary(self, agent: str, record: str, limit: int) -> SourceAccountingSummary:
        result = self.repository.summary(agent, record, limit)
        return SourceAccountingSummary.model_validate(result)

    async def events(self, agent_id: str, record_id: str, limit: int = 50) -> tuple[SourceAccountingEvent, ...]:
        bound = min(50, max(1, TypeAdapter(int).validate_python(limit, strict=True)))
        return await asyncio.to_thread(self._events, _agent(agent_id), _identifier(record_id), bound)

    def _events(self, agent: str, record: str, limit: int) -> tuple[SourceAccountingEvent, ...]:
        result = self.repository.events(agent, record, limit)
        return tuple(SourceAccountingEvent.model_validate(event) for event in result)
