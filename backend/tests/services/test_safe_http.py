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


@pytest.mark.asyncio
async def test_borrowed_client_is_not_closed_and_redirect_drops_credentials():
    seen = []

    def handler(request):
        seen.append(request)
        return (
            httpx.Response(302, headers={"location": "https://other.test/final"})
            if len(seen) == 1
            else httpx.Response(200, text="ok")
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await safe_fetch(
            "https://example.test/start",
            client=client,
            validator=lambda url: url,
            headers={"Authorization": "secret", "Cookie": "private"},
        )
        assert result.text == "ok" and not client.is_closed
    assert "authorization" not in seen[1].headers and "cookie" not in seen[1].headers


@pytest.mark.asyncio
async def test_post_redirect_does_not_replay_body():
    with pytest.raises(RedirectLimitError, match="POST"):
        await safe_fetch(
            "https://example.test/post",
            method="POST",
            data={"q": "query"},
            validator=lambda url: url,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(307, headers={"location": "https://other.test/post"})
            ),
        )
