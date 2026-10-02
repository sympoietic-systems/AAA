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


@pytest.mark.asyncio
async def test_crawl_pdf_extracts_text_fallback():
    probe = RhizomeWebProbe(None, None, None)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/pdf"}
    mock_response.content = b"%PDF-1.4 mock pdf data"

    with (
        patch("backend.modules.retrieval.web_retrieval.safe_fetch", new=AsyncMock(return_value=mock_response)),
        patch("backend.modules.digester.SimpleChunkDigester.extract", return_value="Extracted academic PDF body text."),
    ):
        text = await probe.crawl("https://arxiv.org/pdf/2401.12345.pdf")
        assert text == "Extracted academic PDF body text."
