import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from pydantic import ValidationError

from backend.metabolisation.dream_executor import DreamExecutorMixin
from backend.personality.assembler import PromptAssemblerModule
from backend.services.chat import ChatService
from backend.storage.activation import serialize_activation_trace
from backend.storage.migrations import run_all_migrations
from backend.storage.repositories import MessageRepository
from backend.utils.activation_provenance import build_activation_trace
from benchmarks.suites.activation_usage import audit


def payload():
    return {"attractor_window": [], "always_active_skills": [], "loaded_skills": []}


@pytest.mark.asyncio
async def test_v106_assembly_records_actual_injections_and_replaces_supplied_trace(tmp_path):
    identity = tmp_path / "identity.yaml"
    identity.write_text("personality: {}", encoding="utf-8")
    p = payload()
    p.update(
        always_active_skills=[{"id": "always", "name": "research-proposal", "content": "full instructions"}],
        loaded_skills=[{"id": "dynamic", "name": "review", "description": "review carefully"}],
        activation_provenance={"fake": "model narrative"},
        messages=[{"role": "user", "content": "hi"}],
        attractor_window=[
            {"id": "belief", "label": "label", "statement": "claim", "slot": 1, "mass": 0.5, "confidence": 0.5}
        ],
        web_context=[{"url": "https://example.test?api_key=secret", "content": "retrieved"}],
    )
    result = await PromptAssemblerModule(identity, MagicMock()).process(p)
    trace = result["activation_provenance"]
    assert trace["coverage"] == "complete"
    assert {e["id"] for e in trace["entries"] if e["kind"] != "external"} == {"always", "dynamic", "belief"}
    assert all(e["injected"] for e in trace["entries"])
    assert "full instructions" in str(result["messages"])
    assert "secret" not in json.dumps(trace) and "full instructions" not in json.dumps(trace)
    assert trace["entries"][-1]["id"].startswith("uri-sha256:")


def test_v106_selected_is_not_injected_and_missing_identity_is_partial():
    p = payload()
    p["always_active_skills"] = [{"name": "research-proposal", "content": ""}]
    trace = build_activation_trace(p, [])
    assert trace["coverage"] == "partial"
    assert trace["entries"][0]["selected"] and not trace["entries"][0]["injected"]
    assert build_activation_trace({}, [])["coverage"] == "partial"


def test_v106_migration_preserves_unknown_and_insert_is_atomic(tmp_path):
    path = tmp_path / "provenance.db"
    conn = sqlite3.connect(path)
    run_all_migrations(conn)
    run_all_migrations(conn)
    conn.close()
    repo = MessageRepository(str(path))
    old = repo.insert("apparatus", "old", b"", "fixture", 0)
    trace = build_activation_trace(payload(), [])
    new = repo.insert("apparatus", "new", b"", "fixture", 0, activation_provenance=trace)
    assert old.activation_provenance is None
    assert json.loads(repo.get_by_id(new.id).activation_provenance) == trace
    with pytest.raises(RuntimeError), repo.atomic():
        repo.insert("apparatus", "rollback", b"", "fixture", 0, activation_provenance=trace)
        raise RuntimeError("rollback")
    report = audit(path)
    assert report["apparatus_rows"] == 2 and report["coverage"] == {"unknown": 1, "complete": 1}
    with pytest.raises(ValidationError):
        serialize_activation_trace({**trace, "influence": 1})
    assert audit(path)["apparatus_rows"] == 2


def test_v106_trace_is_bounded():
    p = payload()
    p["loaded_skills"] = [{"id": str(i), "name": str(i)} for i in range(200)]
    trace = build_activation_trace(p, [])
    assert len(trace["entries"]) == 128 and trace["coverage"] == "partial"


@pytest.mark.asyncio
async def test_v106_chat_and_dream_persist_same_assembly_trace(tmp_path):
    path = tmp_path / "callers.db"
    with sqlite3.connect(path) as conn:
        run_all_migrations(conn)
    repo = MessageRepository(str(path))
    user = repo.insert("human", "question", b"", "fixture", 0, conversation_id="c")
    trace = build_activation_trace(payload(), [])
    result = SimpleNamespace(status="ok", payload={"response": "answer", "activation_provenance": trace})
    pipeline = SimpleNamespace(run=AsyncMock(return_value=result))
    state = SimpleNamespace(
        pipeline=pipeline, message_repo=repo, error_repo=MagicMock(), structural_provider=None, config={}
    )
    scorer = MagicMock(score_async=AsyncMock(return_value=np.zeros(16, dtype=np.float32)))
    with (
        patch("backend.services.chat.CompositeStructuralScorer", return_value=scorer),
        patch("backend.modules.structural_engine.CompositeStructuralScorer", return_value=scorer),
    ):
        response = await ChatService(state).generate_response("c", user.id)
        dream = DreamExecutorMixin()
        dream.pipeline = pipeline
        dream.message_repo = repo
        dream.app_state = state
        turn = await dream._execute_single_dream_turn({"content": "dream"}, "d")
    assert turn is not None
    assert json.loads(repo.get_by_id(response.id).activation_provenance) == trace
    assert json.loads(repo.get_by_id(turn["assistant_msg"].id).activation_provenance) == trace
