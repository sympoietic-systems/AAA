"""Shared live/dream/backfill assessment, independent of structural scorer selection."""

from __future__ import annotations

import asyncio
import json
from typing import Any, cast

from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.response_quality import assess_quality
from backend.storage.models import Message
from backend.storage.repositories.conversation.message import MessageRepository


async def assess_message(
    repo: MessageRepository,
    config: dict[str, Any],
    message: Message,
    semaphore: asyncio.Semaphore | None = None,
) -> dict[str, Any]:
    if message.id is None:
        raise ValueError("Message must be persisted before assessment")
    if not callable(getattr(repo, "save_quality", None)):
        return {
            "status": "unassessed",
            "reason": "quality_persistence_unavailable",
            "source": "jev",
            "excluded_from_context": False,
        }
    existing_receipt = getattr(message, "quality_receipt", None)
    if existing_receipt:
        previous = json.loads(existing_receipt)
        if previous.get("source") == "manual":
            return cast(dict[str, Any], previous)
    parent_id = getattr(message, "parent_message_id", None)
    parent = await asyncio.to_thread(repo.get_by_id, parent_id) if parent_id else None
    evaluator = TypeSafeDecisionClient.from_config(config.get("typesafe", {}))

    async def evaluate() -> dict[str, Any]:
        return await assess_quality(
            evaluator, message.content, parent.content if parent else "", reasoning=getattr(message, "thinking", None)
        )

    if semaphore is not None:
        async with semaphore:
            receipt = await evaluate()
    else:
        receipt = await evaluate()
    return await asyncio.to_thread(repo.save_quality, message.id, receipt)
