import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from backend.modules.retrieval.web_retrieval import RhizomeWebProbe
from backend.services.belief_proposal import BeliefProposalUseCases


@pytest.mark.parametrize("error", [sqlite3.OperationalError("locked"), RuntimeError("unexpected")])
def test_v105_bridge_storage_failure_propagates(error):
    skill = SimpleNamespace(name="test", short_content="body", confidence=0.5, vector_16d="[]")
    service = BeliefProposalUseCases()
    service._state = SimpleNamespace(skill_repo=Mock(get_skill=Mock(return_value=skill)))
    repo = Mock(list_beliefs=Mock(return_value=[]), create_belief=Mock(side_effect=error))
    with pytest.raises(type(error)):
        service._resolve_target_belief(repo, "symbia", "test")


@pytest.mark.asyncio
@pytest.mark.parametrize("error,expected", [(ValueError("malformed"), ""), (RuntimeError("bug"), None)])
async def test_v105_pdf_expected_failure_and_unexpected_error(error, expected):
    response = httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF-bad")
    paths = []

    def fail(path, kind):
        paths.append(path)
        raise error

    with (
        patch("backend.modules.retrieval.web_retrieval.safe_fetch", AsyncMock(return_value=response)),
        patch("backend.modules.digester.SimpleChunkDigester.extract", side_effect=fail),
    ):
        probe = RhizomeWebProbe(None, None, None)
        if expected is None:
            with pytest.raises(RuntimeError):
                await probe.crawl("https://example.test/file.pdf")
        else:
            assert await probe.crawl("https://example.test/file.pdf") == expected
    assert paths and not paths[0].exists()
