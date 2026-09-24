"""History query use cases with one sync-to-async boundary per request."""

from __future__ import annotations

import asyncio

from backend.contracts import HistoryMessage, HistoryResponse
from backend.services.metrics import MetricsService
from backend.storage.repositories import MessageRepository
from backend.utils.vector import build_history_message


class HistoryService:
    def __init__(self, repository: MessageRepository) -> None:
        self._repository = repository

    async def list_history(self, *, limit: int, offset: int, conversation_id: str | None) -> HistoryResponse:
        return await asyncio.to_thread(
            self._list_history,
            limit=limit,
            offset=offset,
            conversation_id=conversation_id,
        )

    def _list_history(self, *, limit: int, offset: int, conversation_id: str | None) -> HistoryResponse:
        rows = self._repository.get_recent_with_metrics(
            limit=limit,
            offset=offset,
            conversation_id=conversation_id,
        )
        messages = [self._build_message(row) for row in rows]
        total_count = self._repository.count_messages(conversation_id)
        return HistoryResponse(messages=messages, count=total_count)

    async def get_thinking(self, message_id: int) -> str | None:
        return await asyncio.to_thread(self._get_message_field, message_id, "thinking")

    async def get_context(self, message_id: int) -> str | None:
        return await asyncio.to_thread(self._get_message_field, message_id, "context_sent")

    def _get_message_field(self, message_id: int, field: str) -> str | None:
        message = self._repository.get_by_id(message_id)
        if message is None:
            raise LookupError("Message not found")
        value = getattr(message, field)
        return value if isinstance(value, str) else None

    async def get_path(self, message_id: int) -> list[HistoryMessage]:
        return await asyncio.to_thread(self._get_path, message_id)

    def _get_path(self, message_id: int) -> list[HistoryMessage]:
        ancestors = self._repository.get_ancestor_path(message_id, limit=500)
        if not ancestors:
            raise LookupError("Message path not found")
        ancestor_ids = [message.id for message in ancestors if message.id is not None]
        rows = self._repository.get_recent_with_metrics_for_path(ancestor_ids, limit=len(ancestor_ids))
        return [self._build_message(row) for row in rows]

    @staticmethod
    def _build_message(row: dict[str, object]) -> HistoryMessage:
        metrics = MetricsService.build_history(row)
        return build_history_message(row, metrics)
