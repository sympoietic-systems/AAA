"""Audit recent live replies, or apply server-side assessments after deployment.

Run: uv run python -m scripts.backfill_response_quality --days 14 --output PATH
Add --apply to persist assessments and Creases/Traces on the server.
The checkpoint contains receipts and IDs, never message bodies or credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict, cast
from urllib.parse import urlsplit

import httpx

from backend.config import load_config
from backend.mcp_server import BASE_URL, _mkclient
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.response_quality import SAMPLE_VERSION, assess_quality
from backend.utils.message_quality import content_hash

CHECKPOINT_VERSION = 2


class QualityRecord(TypedDict, total=False):
    status: str
    failure_kind: str
    message_id: int
    content_hash: str
    sample_version: str
    mode: str
    timestamp: str
    model_used: str | None
    attempts: int


class AuditWindow(TypedDict):
    start: str
    end: str
    days: int
    source: str


class AuditCheckpoint(TypedDict):
    checkpoint_version: int
    window: AuditWindow
    candidate_ids: list[int] | None
    snapshot_completed_at: str | None
    records: dict[str, QualityRecord]
    updated_at: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def source_identity(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError("Configured API base must have an absolute HTTP URL")
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"{parsed.scheme.lower()}://{parsed.hostname.lower()}{port}{parsed.path.rstrip('/')}"


def new_checkpoint(days: int, source: str, now: datetime) -> AuditCheckpoint:
    end = now.astimezone(UTC)
    start = end - timedelta(days=days)
    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "window": {"start": start.isoformat(), "end": end.isoformat(), "days": days, "source": source},
        "candidate_ids": None,
        "snapshot_completed_at": None,
        "records": {},
        "updated_at": now.isoformat(),
    }


def load_checkpoint(output: Path, days: int, source: str, now: datetime) -> AuditCheckpoint:
    if not output.exists():
        return new_checkpoint(days, source, now)
    checkpoint = cast(AuditCheckpoint, json.loads(output.read_text(encoding="utf-8")))
    if checkpoint.get("checkpoint_version") != CHECKPOINT_VERSION:
        raise ValueError("Checkpoint predates frozen-window format; start with a new output path")
    window = checkpoint.get("window", {})
    if window.get("days") != days or window.get("source") != source:
        raise ValueError("Checkpoint window or source differs; resume with its original arguments")
    return checkpoint


def summarize(records: dict[str, QualityRecord], candidate_ids: list[int], mode: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message_id in candidate_ids:
        record = records.get(str(message_id), {})
        status = record.get("status", "not_attempted") if record.get("mode") == mode else "not_attempted"
        counts[status] = counts.get(status, 0) + 1
    return counts


def receipt_is_current(record: QualityRecord, mode: str, digest: str) -> bool:
    return (
        record.get("status") != "unavailable"
        and record.get("mode") == mode
        and record.get("content_hash") == digest
        and record.get("sample_version") == SAMPLE_VERSION
    )


def save_checkpoint(output: Path, checkpoint: AuditCheckpoint) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(checkpoint, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(output)


async def run(days: int, output: Path, apply: bool) -> None:
    mode = "apply" if apply else "audit"
    source = source_identity(BASE_URL)
    checkpoint = load_checkpoint(output, days, source, utc_now())
    start = parse_timestamp(checkpoint["window"]["start"])
    end = parse_timestamp(checkpoint["window"]["end"])
    evaluator = TypeSafeDecisionClient.from_config(load_config().get("typesafe", {}))
    async with cast(Any, _mkclient)(timeout=60) as client:
        if apply:
            probe = await client.get(f"{BASE_URL}/messages/quality", params={"limit": 1})
            probe.raise_for_status()  # Fail before any mutation if deployment is missing.
        messages: dict[int, dict[str, Any]] = {}
        if checkpoint["candidate_ids"] is None:
            offset = 0
            candidate_ids: list[int] = []
            while True:
                response = await client.get(f"{BASE_URL}/history", params={"limit": 1000, "offset": offset})
                response.raise_for_status()
                page = response.json()["messages"]
                if not page:
                    break
                for message in page:
                    message_id = int(message["id"])
                    timestamp = parse_timestamp(message["timestamp"])
                    if start <= timestamp < end:
                        messages[message_id] = message
                        if message["speaker"] == "apparatus":
                            candidate_ids.append(message_id)
                oldest = min(parse_timestamp(message["timestamp"]) for message in page)
                if oldest < start or len(page) < 1000:
                    break
                offset += len(page)
            checkpoint["candidate_ids"] = sorted(set(candidate_ids))
            checkpoint["snapshot_completed_at"] = utc_now().isoformat()
            save_checkpoint(output, checkpoint)
        else:
            offset = 0
            remaining = set(checkpoint["candidate_ids"])
            while remaining:
                response = await client.get(f"{BASE_URL}/history", params={"limit": 1000, "offset": offset})
                response.raise_for_status()
                page = response.json()["messages"]
                if not page:
                    break
                for message in page:
                    message_id = int(message["id"])
                    if message_id in remaining:
                        messages[message_id] = message
                        remaining.remove(message_id)
                if len(page) < 1000:
                    break
                offset += len(page)
        frozen_candidate_ids = checkpoint["candidate_ids"]
        if frozen_candidate_ids is None:
            raise RuntimeError("Candidate snapshot was not persisted")
        candidates = [messages[mid] for mid in frozen_candidate_ids if mid in messages]
        print(
            f"{mode}: {len(frozen_candidate_ids)} frozen replies in [{start.isoformat()}, {end.isoformat()})",
            flush=True,
        )
        for message in sorted(candidates, key=lambda m: m["id"]):
            mid = str(message["id"])
            digest = content_hash(message["content"])
            previous = checkpoint["records"].get(mid, {})
            if receipt_is_current(previous, mode, digest):
                continue
            receipt: dict[str, Any]
            try:
                if apply:
                    response = await client.post(f"{BASE_URL}/messages/{mid}/quality/assess")
                    response.raise_for_status()
                    receipt = response.json()
                else:
                    parent_id = message.get("parent_message_id")
                    parent = messages.get(int(parent_id), {}) if parent_id is not None else {}
                    if not parent and parent_id is not None:
                        response = await client.get(f"{BASE_URL}/messages/{mid}/path")
                        response.raise_for_status()
                        parent = next((m for m in response.json() if m["id"] == int(parent_id)), {})
                    response = await client.get(f"{BASE_URL}/messages/{mid}/thinking")
                    response.raise_for_status()
                    receipt = await assess_quality(
                        evaluator,
                        message["content"],
                        parent.get("content", ""),
                        reasoning=response.json().get("thinking"),
                    )
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                receipt = {"status": "unavailable", "failure_kind": type(exc).__name__}
            checkpoint["records"][mid] = cast(
                QualityRecord,
                {
                    **receipt,
                    "message_id": int(mid),
                    "content_hash": digest,
                    "sample_version": SAMPLE_VERSION,
                    "mode": mode,
                    "timestamp": message["timestamp"],
                    "model_used": message.get("model_used"),
                    "attempts": int(previous.get("attempts", 0)) + 1,
                },
            )
            checkpoint["updated_at"] = utc_now().isoformat()
            save_checkpoint(output, checkpoint)
            print(f"{mid}: {receipt['status']} ({receipt.get('confidence')})", flush=True)
        counts = summarize(checkpoint["records"], frozen_candidate_ids, mode)
        print(
            json.dumps(
                {
                    "window": checkpoint["window"],
                    "snapshot_completed_at": checkpoint["snapshot_completed_at"],
                    "mode": mode,
                    "candidate_count": len(frozen_candidate_ids),
                    "counts": counts,
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, choices=range(1, 91))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.days, arguments.output, arguments.apply))
