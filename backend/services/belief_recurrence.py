"""Read-only grouping of exact incomplete queue entries; equality is not a verdict."""

import asyncio
from typing import Any

from backend.storage.repositories.base import BaseRepository
from backend.storage.repositories.cognitive.belief_recurrence import BeliefRecurrenceRepository


def eligible(item: dict[str, Any]) -> dict[str, Any] | None:
    history = item.get("admission_history", [])
    if item.get("proposal_status") != "pending" or not history:
        return None
    receipt = history[0]
    source = receipt.get("source", {})
    issues = receipt.get("context_issues", [])
    required = {"missing_scope", "missing_temporal_scope", "missing_evidence_quote", "missing_consequence"}
    if (
        receipt.get("policy_version") not in {"belief-v2-advisory-v1", "belief-v2-explicit-deferred"}
        or receipt.get("statement") != item.get("statement")
        or not required.issubset(issues)
        or receipt.get("evaluation", {}).get("status") != "abstained"
        or source.get("origin") != "chat"
        or not isinstance(source.get("message_id"), int)
        or not source.get("conversation_id")
        or not source.get("message_sha256")
    ):
        return None
    return {"id": item["id"], "statement": item["statement"], "source": source}


def project(items: list[dict[str, Any]], repo: BeliefRecurrenceRepository, agent: str) -> list[dict[str, Any]]:
    entries = [value for item in sorted(items, key=lambda x: x["id"]) if (value := eligible(item))]
    selected = entries[:50]
    paths = repo.sources(agent, selected)
    groups: list[list[dict[str, Any]]] = []
    for entry in selected:
        if entry["id"] not in paths:
            continue
        peers = next(
            (
                group
                for group in groups
                if all(
                    entry["statement"] == other["statement"]
                    and entry["source"]["conversation_id"] == other["source"]["conversation_id"]
                    and (
                        entry["source"]["message_id"] in paths[other["id"]]
                        or other["source"]["message_id"] in paths[entry["id"]]
                    )
                    for other in group
                )
            ),
            None,
        )
        if peers is None:
            groups.append([entry])
        else:
            peers.append(entry)
    metadata = {}
    for group in groups:
        if len(group) < 2:
            continue
        value = {
            "id": group[0]["id"],
            "member_ids": [entry["id"] for entry in group],
            "count": len(group),
            "count_kind": "visible_queue_entries",
            "standing": "context_incomplete",
            "semantic_equivalence": "unknown",
            "independent_warrant_delta": 0,
            "tool_authority": "none",
            "scan_truncated": len(entries) > 50,
            "ancestry_unavailable": len(selected) - len(paths),
        }
        metadata.update({entry["id"]: value for entry in group})
    return [item | ({"recurrence_group": metadata[item["id"]]} if item["id"] in metadata else {}) for item in items]


async def recurrence_projection(items: list[dict[str, Any]], repository: object, agent: str) -> list[dict[str, Any]]:
    if not isinstance(repository, BaseRepository):
        return items
    return await asyncio.to_thread(project, items, BeliefRecurrenceRepository(repository.db_path), agent)
