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

from backend.config import load_config
from backend.mcp_server import BASE_URL, _mkclient
from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
from backend.modules.response_quality import SAMPLE_VERSION, assess_quality
from backend.utils.message_quality import content_hash


async def run(days: int, output: Path, apply: bool) -> None:
    mode = "apply" if apply else "audit"
    checkpoint = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {"records": {}}
    cutoff = datetime.now(UTC) - timedelta(days=days)
    evaluator = TypeSafeDecisionClient.from_config(load_config().get("typesafe", {}))
    async with _mkclient(timeout=60) as client:
        if apply:
            probe = await client.get(f"{BASE_URL}/messages/quality", params={"limit": 1})
            probe.raise_for_status()  # Fail before any mutation if deployment is missing.
        messages = {}
        offset = 0
        while True:
            response = await client.get(f"{BASE_URL}/history", params={"limit": 1000, "offset": offset})
            response.raise_for_status()
            page = response.json()["messages"]
            if not page:
                break
            for message in page:
                messages[message["id"]] = message
            oldest = min(
                datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")).replace(tzinfo=UTC) for m in page
            )
            if oldest < cutoff or len(page) < 1000:
                break
            offset += len(page)
        candidates = [
            m
            for m in messages.values()
            if m["speaker"] == "apparatus"
            and datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")).replace(tzinfo=UTC) >= cutoff
        ]
        print(f"{mode}: {len(candidates)} replies since {cutoff.isoformat()}", flush=True)
        for message in sorted(candidates, key=lambda m: m["id"]):
            mid = str(message["id"])
            digest = content_hash(message["content"])
            previous = checkpoint["records"].get(mid, {})
            if (
                previous.get("mode") == mode
                and previous.get("content_hash") == digest
                and previous.get("sample_version") == SAMPLE_VERSION
            ):
                continue
            if apply:
                response = await client.post(f"{BASE_URL}/messages/{mid}/quality/assess")
                response.raise_for_status()
                receipt = response.json()
            else:
                parent = messages.get(message.get("parent_message_id"), {})
                if not parent and message.get("parent_message_id"):
                    response = await client.get(f"{BASE_URL}/messages/{mid}/path")
                    response.raise_for_status()
                    parent = next((m for m in response.json() if m["id"] == message["parent_message_id"]), {})
                response = await client.get(f"{BASE_URL}/messages/{mid}/thinking")
                response.raise_for_status()
                receipt = await assess_quality(
                    evaluator, message["content"], parent.get("content", ""), reasoning=response.json().get("thinking")
                )
            checkpoint["records"][mid] = {
                **receipt,
                "mode": mode,
                "timestamp": message["timestamp"],
                "model_used": message.get("model_used"),
            }
            checkpoint.update(
                {"days": days, "updated_at": datetime.now(UTC).isoformat(), "sample_version": SAMPLE_VERSION}
            )
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(output.suffix + ".tmp")
            temporary.write_text(json.dumps(checkpoint, indent=2, allow_nan=False), encoding="utf-8")
            temporary.replace(output)
            print(f"{mid}: {receipt['status']} ({receipt.get('confidence')})", flush=True)
        counts = {}
        for record in checkpoint["records"].values():
            counts[record["status"]] = counts.get(record["status"], 0) + 1
        print(json.dumps(counts), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, choices=range(1, 91))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    arguments = parser.parse_args()
    asyncio.run(run(arguments.days, arguments.output, arguments.apply))
