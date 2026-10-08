from datetime import UTC, datetime, timedelta

import httpx
import pytest

from backend.modules.retrieval.safe_http import UnsafeDestinationError
from backend.services.research.acquisition import (
    AcquisitionContext,
    AcquisitionPolicy,
    AcquisitionRuntime,
    acquisition_scope,
)
from backend.services.research.search_tool import _search_ddg_lite


@pytest.mark.asyncio
@pytest.mark.parametrize("unsafe", [False, True])
async def test_search_redirect_uses_get_and_validates_every_destination(unsafe):
    requests = []
    validated = []
    query = 'Barad & dome + "performance"'

    def validator(url):
        validated.append(url)
        if "127.0.0.1" in url:
            raise ValueError("restricted destination")
        return url

    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(302, headers={"location": "http://127.0.0.1/private" if unsafe else "/results"})
        return httpx.Response(200, text='<a href="https://example.org/paper">Dome paper</a>')

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    runtime = AcquisitionRuntime(
        AcquisitionPolicy(minimum_interval_seconds=0, ddg_interval_seconds=0), client=client, validator=validator
    )
    try:
        with acquisition_scope(AcquisitionContext(runtime, datetime.now(UTC) + timedelta(seconds=10), [])):
            if unsafe:
                with pytest.raises(UnsafeDestinationError):
                    await _search_ddg_lite(query)
            else:
                assert await _search_ddg_lite(query) == [
                    {"url": "https://example.org/paper", "title": "Dome paper", "snippet": ""}
                ]
        assert requests[0].method == "GET"
        assert requests[0].url.params["q"] == query
        assert requests[0].content == b""
        assert len(validated) == 2
        assert len(requests) == (1 if unsafe else 2)
    finally:
        await runtime.aclose()
