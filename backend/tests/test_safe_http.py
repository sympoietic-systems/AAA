import httpx
import pytest

from backend.modules.retrieval.safe_http import (
    RedirectLimitError,
    ResponseTooLargeError,
    UnsafeDestinationError,
    safe_fetch,
)
from backend.utils.security import validate_safe_url


def _public_only(url: str) -> str:
    if "127.0.0.1" in url:
        raise ValueError("restricted destination")
    return url


@pytest.mark.asyncio
async def test_safe_fetch_revalidates_redirect_destination():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/secret"})

    with pytest.raises(UnsafeDestinationError):
        await safe_fetch(
            "https://example.test/start",
            transport=httpx.MockTransport(handler),
            validator=_public_only,
        )


@pytest.mark.asyncio
async def test_safe_fetch_streams_with_hard_byte_limit():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 17)

    with pytest.raises(ResponseTooLargeError):
        await safe_fetch(
            "https://example.test/data",
            max_bytes=16,
            transport=httpx.MockTransport(handler),
            validator=_public_only,
        )


@pytest.mark.asyncio
async def test_safe_fetch_enforces_redirect_limit():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "/again"})

    with pytest.raises(RedirectLimitError):
        await safe_fetch(
            "https://example.test/start",
            max_redirects=1,
            transport=httpx.MockTransport(handler),
            validator=_public_only,
        )


def test_validate_safe_url_rejects_credentials():
    with pytest.raises(ValueError, match="credentials"):
        validate_safe_url("https://user:password@example.com/path")
