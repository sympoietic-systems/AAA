"""Bounded outbound HTTP fetches for user-controlled destinations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from backend.utils.security import validate_safe_url

DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 3


class SafeFetchError(RuntimeError):
    """Base error for bounded outbound requests."""


class UnsafeDestinationError(SafeFetchError):
    pass


class ResponseTooLargeError(SafeFetchError):
    pass


class RedirectLimitError(SafeFetchError):
    pass


@dataclass(frozen=True)
class SafeFetchResponse:
    status_code: int
    url: str
    headers: Mapping[str, str]
    content: bytes

    @property
    def text(self) -> str:
        charset = "utf-8"
        content_type = self.headers.get("content-type", "")
        if "charset=" in content_type:
            charset = content_type.rsplit("charset=", 1)[-1].split(";", 1)[0].strip()
        return self.content.decode(charset, errors="replace")


async def safe_fetch(
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15.0,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    transport: httpx.AsyncBaseTransport | None = None,
    validator: Callable[[str], str] = validate_safe_url,
) -> SafeFetchResponse:
    """GET a public URL with per-hop validation and bounded streaming.

    Automatic redirects stay disabled. Validation performs DNS resolution
    immediately before each request so every resolved address must remain public.
    """
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    if max_redirects < 0:
        raise ValueError("max_redirects cannot be negative")

    current_url = url
    request_headers = dict(headers or {})
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        follow_redirects=False,
        transport=transport,
    ) as client:
        for hop in range(max_redirects + 1):
            try:
                safe_url = await asyncio.to_thread(validator, current_url)
            except ValueError as exc:
                raise UnsafeDestinationError(str(exc)) from exc

            async with client.stream("GET", safe_url, headers=request_headers) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise SafeFetchError("Redirect response missing Location header")
                    if hop >= max_redirects:
                        raise RedirectLimitError(f"Redirect limit exceeded ({max_redirects})")
                    current_url = urljoin(safe_url, location)
                    continue

                declared_size = response.headers.get("content-length")
                if declared_size:
                    try:
                        if int(declared_size) > max_bytes:
                            raise ResponseTooLargeError(f"Response exceeds {max_bytes} byte limit")
                    except ValueError:
                        pass

                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        raise ResponseTooLargeError(f"Response exceeds {max_bytes} byte limit")

                return SafeFetchResponse(
                    status_code=response.status_code,
                    url=str(response.url),
                    headers=dict(response.headers),
                    content=bytes(body),
                )

    raise RedirectLimitError(f"Redirect limit exceeded ({max_redirects})")
