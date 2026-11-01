import pytest

from backend.services.history import HistoryService
from benchmarks.fixtures.message_history_v1 import MessageHistoryRepository as ReferenceHistory
from benchmarks.fixtures.navigation_queries import history, skills


@pytest.mark.asyncio
async def test_skill_summaries_preserve_metadata_and_default_full_content():
    service = skills()
    full = await service.get_skills()
    compact = await service.get_skills(include_content=False)
    assert full.keys() == compact.keys()
    for group in full:
        assert len(full[group]) == len(compact[group])
        for old, new in zip(full[group], compact[group], strict=True):
            assert "content" in old and "short_content" in old and "content_loaded" not in old
            assert new == {
                **{k: v for k, v in old.items() if k not in {"content", "short_content"}},
                "content_loaded": False,
            }


@pytest.mark.parametrize("scope", [None, "fixture", "missing"])
def test_history_projection_preserves_serialized_output_and_full_details(tmp_path, scope):
    path = tmp_path / "history.db"
    repo = history(path, rich=True)
    reference = ReferenceHistory(str(path))
    for limit, offset in [(50, 0), (5, 2)]:
        kwargs = dict(limit=limit, offset=offset, conversation_id=scope)
        expected = reference.get_recent_with_metrics(**kwargs)
        actual = repo.get_recent_with_metrics(**kwargs)
        assert [HistoryService._build_message(r).model_dump() for r in actual] == [
            HistoryService._build_message(r).model_dump() for r in expected
        ]
        assert all("thinking" not in r and "context_sent" not in r for r in actual)
    ids = [r["id"] for r in repo.get_recent_with_metrics(limit=50)]
    expected = reference.get_recent_with_metrics_for_path(ids, limit=10, exclude_message_id=ids[-1])
    actual = repo.get_recent_with_metrics_for_path(ids, limit=10, exclude_message_id=ids[-1])
    assert [HistoryService._build_message(r).model_dump() for r in actual] == [
        HistoryService._build_message(r).model_dump() for r in expected
    ]
    detail = repo.get_by_id(ids[0])
    assert detail.thinking == "reasoning " * 2000
    assert detail.context_sent == "context " * 3000
    assert {r["has_context"] for r in repo.get_recent_with_metrics(limit=50)} == {0, 1}


def test_summary_route_is_opt_in_and_authenticated(monkeypatch):
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from backend.api.deps import get_skill_service, verify_password
    from backend.api.routes.skills import router

    monkeypatch.setenv("AAA_PASSWORD", "fixture-password")
    app = FastAPI()
    app.include_router(router, prefix="/api", dependencies=[Depends(verify_password)])
    app.dependency_overrides[get_skill_service] = skills
    client = TestClient(app)
    assert client.get("/api/skills/db?include_content=false").status_code == 401
    headers = {"Authorization": "Bearer fixture-password"}
    full = client.get("/api/skills/db", headers=headers)
    compact = client.get("/api/skills/db?include_content=false", headers=headers)
    assert full.status_code == compact.status_code == 200
    assert "content" in full.json()["all"][0]
    assert "content" not in compact.json()["all"][0]
    assert client.get("/api/skills/db?include_content=invalid", headers=headers).status_code == 422
