from unittest.mock import AsyncMock, patch

import httpx
import pytest

from backend.modules.retrieval.web_retrieval import RhizomeWebProbe


@pytest.mark.asyncio
async def test_v65_crawl_network_error_falls_back_without_disabling_tls():
    probe = RhizomeWebProbe(None, None, None)
    request = httpx.Request("GET", "https://example.test/article")

    with patch(
        "backend.modules.retrieval.web_retrieval.safe_fetch",
        new=AsyncMock(side_effect=httpx.ConnectError("certificate verify failed", request=request)),
    ):
        assert await probe.crawl("https://example.test/article") == ""
