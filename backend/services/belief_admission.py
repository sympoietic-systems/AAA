"""Shared chat/dream candidate intake, bounded shadow evaluation, and durable decisions."""

import asyncio
import hashlib
import json
import logging
import re
import uuid
import weakref
from datetime import UTC, datetime
from typing import Any

from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.sensory.evidence_triage import EvidenceTriage
from backend.services.belief_admission_policy import (
    POLICY_VERSION,
    Candidate,
    context_issues,
    questions,
    recommendation,
)
from backend.storage.repositories.cognitive.belief_admission import AdmissionRepository
from backend.storage.repositories.conversation.message import MessageRepository
from backend.utils.belief_candidate import statement_key

logger = logging.getLogger(__name__)
_CAPACITIES: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore] = weakref.WeakKeyDictionary()


def _capacity() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if loop not in _CAPACITIES:
        _CAPACITIES[loop] = asyncio.Semaphore(2)
    return _CAPACITIES[loop]


def select_comparisons(statement: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lexical semantic nomination, never structural-vector equivalence."""
    words = set(re.findall(r"[\w-]{3,}", statement.casefold()))

    def overlap(record: dict[str, Any]) -> float:
        other = set(re.findall(r"[\w-]{3,}", record["statement"].casefold()))
        return len(words & other) / max(1, len(words | other))

    return sorted(records, key=lambda r: (-overlap(r), r["id"]))[:10]


async def admit_candidate(
    db_path: str,
    conversation_id: str,
    message_id: int,
    data: dict[str, Any],
    *,
    config: dict[str, Any],
    evaluator: EvidenceTriage | None = None,
    origin: str = "chat",
) -> dict[str, Any]:
    candidate = Candidate.model_validate(data)
    repo = AdmissionRepository(db_path)
    messages = MessageRepository(db_path)
    message = await asyncio.to_thread(messages.get_by_id, message_id)
    if not message or message.conversation_id != conversation_id:
        raise ValueError("Candidate source message does not belong to conversation")
    parent = (
        await asyncio.to_thread(messages.get_by_id, message.parent_message_id) if message.parent_message_id else None
    )
    source_text = parent.content if parent else ""
    timestamp = datetime.now(UTC).isoformat()
    key = statement_key(candidate.statement)
    event_key = hashlib.sha256(
        f"{conversation_id}:{message_id}:{key}:{candidate.scope}:{candidate.temporal_scope}".encode()
    ).hexdigest()
    receipt: dict[str, Any] = {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, event_key)),
        "event_key": event_key,
        "statement_key": key,
        "statement": candidate.statement,
        "label": candidate.label,
        "rationale": candidate.rationale,
        "consequence": candidate.consequence,
        "scope": candidate.scope,
        "temporal_scope": candidate.temporal_scope,
        "trigger": candidate.trigger,
        "evidence_quote": candidate.evidence_quote,
        "emission_sha256": data.get("emission_sha256"),
        "source": {
            "type": "intention",
            "author": "symbia",
            "origin": origin,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "parent_message_id": message.parent_message_id,
            "message_sha256": hashlib.sha256(message.content.encode()).hexdigest(),
            "evidence_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
            "scope": candidate.scope,
            "temporal_scope": candidate.temporal_scope,
        },
        "policy_version": POLICY_VERSION,
        "mode": "shadow",
        "created_at": timestamp,
        "status": "assessing",
        "decision": "needs_review",
        "reason": "Candidate received; assessment pending.",
    }
    claimed, saved = await asyncio.to_thread(repo.claim, receipt)
    if not claimed:
        return saved
    records = await asyncio.to_thread(repo.comparisons, "symbia")
    selected = select_comparisons(candidate.statement, records)
    receipt["comparisons"] = [
        {
            "id": r["id"],
            "kind": r["kind"],
            "label": r["label"],
            "statement": r["statement"][:4000],
            "statement_sha256": hashlib.sha256(r["statement"].encode()).hexdigest(),
            "scope": r["scope"],
            "temporal_scope": r["temporal_scope"],
        }
        for r in selected
    ]
    receipt["uncompared_count"] = max(0, len(records) - len(selected))
    issues = context_issues(candidate, source_text)
    receipt["context_issues"] = issues
    evaluation: dict[str, Any] = {"status": "abstained", "reason": "context_incomplete", "answers": {}}
    if not issues:
        if evaluator is None:
            settings = config.get("belief_admission", {})
            if settings.get("jev_shadow", True):
                evaluator = EvidenceTriage(TypeSafeDecisionClient.from_config(config.get("typesafe") or {}))
        if evaluator:
            async with _capacity():
                evaluation = await evaluator.evaluate(
                    {
                        "candidate": candidate.model_dump(exclude={"confidence"}),
                        "source_quote": candidate.evidence_quote,
                        "comparisons": receipt["comparisons"],
                    },
                    questions(selected),
                )
        else:
            evaluation = {"status": "unavailable", "reason": "shadow_disabled", "answers": {}}
    receipt["evaluation"] = evaluation
    receipt["recommendation"] = recommendation(evaluation, len(selected))
    receipt["reason"] = "Human review required; shadow assessment cannot authorize nucleation. " + (
        "Missing or unresolved context: " + ", ".join(issues) if issues else "Inspect source and comparison judgments."
    )
    receipt["assessed_at"] = datetime.now(UTC).isoformat()
    # A candidate is not yet a belief; defer expensive structural scoring to manual adoption/refinement.
    final = await asyncio.to_thread(repo.finish, receipt, candidate.confidence, json.dumps([]))
    logger.info(
        "Belief admission receipt=%s message=%s decision=%s recommendation=%s assessed_at=%s",
        final["id"],
        message_id,
        final["decision"],
        final.get("recommendation"),
        final["assessed_at"],
    )
    return final
