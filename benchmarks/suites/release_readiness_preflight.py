"""Save bounded release-readiness evidence from a running AAA instance."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def validate_base_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Base URL must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Base URL must not contain credentials, query, or fragment")
    return base_url.rstrip("/")


async def fetch_preflight(client: httpx.AsyncClient, base_url: str, days: int) -> dict:
    target = f"{validate_base_url(base_url)}/release-readiness"
    response = await client.get(target, params={"days": days})
    response.raise_for_status()
    return response.json()


async def run(base_url: str, output: Path, days: int) -> None:
    headers = {}
    password = os.environ.get("AAA_PASSWORD", "").strip()
    if password:
        headers["Authorization"] = f"Bearer {password}"
    async with httpx.AsyncClient(timeout=30, follow_redirects=False, headers=headers) as client:
        receipt = await fetch_preflight(client, base_url, days)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"output": str(output), "generated_at": receipt["generated_at"], "read_only": True}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="AAA API base URL, including /api")
    parser.add_argument("--days", type=int, default=30, choices=range(1, 91))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.base_url, args.output, args.days))


if __name__ == "__main__":
    main()
