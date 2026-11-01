import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from backend.metabolisation.dream_executor import DreamExecutorMixin
from backend.modules.context_collector import ContextCollectorModule
from backend.modules.response_quality import assess_quality, quality_sample
from backend.services.history import HistoryService
from backend.storage.database import init_db
from backend.storage.repositories import MessageRepository
from backend.storage.repositories.conversation.notification import NotificationRepository
from backend.utils.message_quality import content_hash


@pytest.fixture
def repo(tmp_path):
    path = str(tmp_path / "quality.db")
    conn = init_db(path)
    conn.close()
    return MessageRepository(path)


def insert(repo, text="Useful answer", **kwargs):
    return repo.insert(
        speaker="apparatus",
        content=text,
        conversation_id="conv",
        embedding=b"",
        embedding_model="",
        embedding_dim=0,
        **kwargs,
    )


def test_generation_receipt_round_trips_without_prompt_or_reasoning(repo):
    generation_receipt = {
        "request_id": "provider-request-123",
        "finish_reason": "stop",
        "truncated": False,
        "usage": {"prompt_tokens": 120, "completion_tokens": 45},
    }
    message = insert(repo, generation_receipt=generation_receipt)
    loaded = repo.get_by_id(message.id)

    assert loaded is not None
    assert json.loads(loaded.generation_receipt) == generation_receipt


def test_degraded_quality_creates_glitch_and_uncertain_creates_trace(repo):
    notifications = NotificationRepository(repo._db_path)
    degraded = insert(repo, text="Runaway response")
    uncertain = insert(repo, text="Ambiguous response")

    repo.save_quality(degraded.id, receipt(degraded.content, status="degraded"))
    repo.save_quality(uncertain.id, receipt(uncertain.content, status="uncertain"))

    assert notifications.get(f"quality-{degraded.id}")["type"] == "glitch"
    assert notifications.get(f"quality-{uncertain.id}")["type"] == "trace"


def receipt(text, status="degraded", source="jev"):
    return {
        "status": status,
        "content_hash": content_hash(text),
        "source": source,
        "reason": "test",
        "confidence": 0.95,
    }


@pytest.mark.asyncio
async def test_v121_degenerate_tail_visible_without_changing_structural_state():
    text = "Coherent answer. " * 400 + "evermore-" * 180
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value={"success": True, "answers": {"response_quality": {"choice": "degraded", "confidence": 0.95}}}
        )
    )
    result = await assess_quality(evaluator, text, "Explain the mechanism")
    state = evaluator.evaluate.call_args.kwargs["state"]
    assert state["text"].endswith("evermore-")
    assert len(state["text"]) <= 3000
    assert result["status"] == "degraded" and result["excluded_from_context"]
    assert "structural_signature" not in state


@pytest.mark.asyncio
async def test_v128_tool_control_token_leak_is_deterministically_degraded():
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value={"success": True, "answers": {"response_quality": {"choice": "sound", "confidence": 0.99}}}
        )
    )

    result = await assess_quality(evaluator, "Here is the answer <|tool_call_begin|>", "Question")

    assert result["status"] == "degraded"
    assert result["reason"] == "provider_control_token_leak"
    assert result["excluded_from_context"]
    assert quality_sample("short") == "short"


@pytest.mark.asyncio
@pytest.mark.parametrize("confidence", [0.07, None, float("nan"), 2, True])
async def test_v121_weak_or_invalid_confidence_keeps_message_in_context(confidence):
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value={
                "success": True,
                "answers": {"response_quality": {"choice": "degraded", "confidence": confidence}},
            }
        )
    )
    result = await assess_quality(evaluator, "Ambiguous philosophical prose", "Reflect")
    assert result["status"] == "uncertain"
    assert not result["excluded_from_context"]


@pytest.mark.asyncio
async def test_v121_reasoning_only_is_not_a_final_answer_even_when_jev_unavailable():
    evaluator = SimpleNamespace(evaluate=AsyncMock(return_value={"success": False}))
    result = await assess_quality(
        evaluator, "I need to draft the answer", "Explain", reasoning="I need to draft the answer"
    )
    assert result["status"] == "degraded" and result["reason"] == "reasoning_only"


def test_v121_receipts_preserve_original_manual_override_and_reject_stale_writes(repo):
    msg = insert(repo)
    repo.save_quality(msg.id, receipt(msg.content))
    repo.save_quality(msg.id, receipt(msg.content))
    assert repo.get_by_id(msg.id).content == msg.content
    rows = repo.list_quality("degraded")
    assert rows[0]["message_id"] == msg.id
    restored = repo.save_quality(msg.id, receipt(msg.content, "sound", "manual"))
    assert repo.save_quality(msg.id, receipt(msg.content)) == restored
    assert not repo.degraded_ids("conv")
    repo.update_content(msg.id, "Edited")
    with pytest.raises(ValueError, match="changed"):
        repo.save_quality(msg.id, receipt(msg.content))
    assert repo.get_by_id(msg.id).quality_status == "unassessed"


@pytest.mark.asyncio
async def test_v122_display_retains_degraded_message_while_generation_and_retrieval_exclude_it(repo):
    bad = insert(repo, "broken words " * 50)
    good = insert(repo, "Useful correction", parent_message_id=bad.id)
    repo.save_quality(bad.id, receipt(bad.content))
    history = await HistoryService(repo).list_history(limit=10, offset=0, conversation_id="conv")
    assert len(history.messages) == 2
    assert history.messages[0].quality_status == "degraded"
    assert history.messages[0].quality["excluded_from_context"]
    module = ContextCollectorModule(repo, MagicMock(get_notes_by_conversation=lambda _: []))
    payload = await module.process({"conversation_id": "conv", "parent_message_id": good.id})
    assert bad.id not in payload["ancestor_message_ids"]
    assert payload["quality_excluded_message_ids"] == [bad.id]
    assert all("broken words" not in m["content"] for m in payload["messages"])
    assert not repo.get_sediment_messages_with_metadata([bad.id])


def test_v122_glitch_links_assistant_id_and_reassessment_does_not_duplicate(repo):
    from backend.storage.repositories.conversation.notification import NotificationRepository

    msg = insert(repo)
    repo.save_quality(msg.id, receipt(msg.content))
    repo.save_quality(msg.id, receipt(msg.content))
    glitches = NotificationRepository(repo._db_path).list_active()
    assert len(glitches) == 1
    assert glitches[0]["message_id"] == msg.id
    assert glitches[0]["type"] == "glitch" and glitches[0]["conversation_id"] == "conv"
    repo.save_quality(msg.id, receipt(msg.content, "sound", "manual"))
    assert not NotificationRepository(repo._db_path).list_active()


@pytest.mark.asyncio
async def test_v122_dream_assesses_quality_independently_of_structural_override(repo, monkeypatch):
    from backend.modules import structural_engine
    from backend.services import response_quality

    monkeypatch.setattr(
        structural_engine.CompositeStructuralScorer,
        "score_async",
        AsyncMock(return_value=np.zeros(16, dtype=np.float32)),
    )
    evaluator = SimpleNamespace(
        evaluate=AsyncMock(
            return_value={"success": True, "answers": {"response_quality": {"choice": "degraded", "confidence": 0.98}}}
        )
    )
    monkeypatch.setattr(response_quality.TypeSafeDecisionClient, "from_config", lambda _: evaluator)
    daemon = DreamExecutorMixin()
    daemon.message_repo = repo
    daemon.app_state = SimpleNamespace(config={}, structural_provider=None)
    daemon.pipeline = SimpleNamespace(
        run=AsyncMock(return_value=SimpleNamespace(payload={"response": "evermore-" * 500}))
    )
    result = await daemon._execute_single_dream_turn({"content": "Reflect"}, "conv")
    assert result["assistant_msg"].quality_status == "degraded"
    assert evaluator.evaluate.await_count == 1


def test_v121_quality_event_history_is_append_only(repo):
    msg = insert(repo)
    repo.save_quality(msg.id, receipt(msg.content))
    repo.save_quality(msg.id, receipt(msg.content, "sound", "manual"))
    from backend.storage.database import get_connection

    conn = get_connection(repo._db_path)
    events = conn.execute("SELECT receipt FROM message_quality_events ORDER BY id").fetchall()
    conn.close()
    assert [json.loads(row["receipt"])["status"] for row in events] == ["degraded", "sound"]
