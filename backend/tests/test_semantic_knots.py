import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.storage.repository import ConversationRepository, SemanticKnotRepository


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_semantic_knot_repository_basic(tmp_path):
    # Set up temporary sqlite DB
    db_file = tmp_path / "test_knots.db"

    # Initialize DB
    from backend.storage.database import init_db

    init_conn = init_db(str(db_file))
    init_conn.close()

    conv_repo = ConversationRepository(str(db_file))
    repo = SemanticKnotRepository(str(db_file))

    # Create the conversation to satisfy FOREIGN KEY constraint
    conv_id = "conv_456"
    conv_repo.create(conversation_id=conv_id, agent_id="symbia")

    # Test insertion
    knot_id = "knot_123"
    payload = json.dumps({"text": "The conceptual framework of sympoietic systems.", "max_message_id": 42})
    emb = np.ones(384, dtype="float32").tobytes()
    sig = np.ones(16, dtype="float32").tobytes()

    knot = repo.insert_knot(
        id=knot_id,
        conversation_id=conv_id,
        concept_payload=payload,
        embedding=emb,
        embedding_model="test-embed-model",
        token_count=15,
        weight=1.0,
        structural_signature=sig,
    )

    assert knot.id == knot_id
    assert knot.conversation_id == conv_id
    assert knot.concept_payload == payload
    assert knot.embedding == emb
    assert knot.structural_signature == sig

    # Test get_by_conversation
    knots = repo.get_by_conversation(conv_id)
    assert len(knots) == 1
    assert knots[0].id == knot_id

    # Test get_by_ids
    fetched = repo.get_by_ids([knot_id])
    assert len(fetched) == 1
    assert fetched[0].id == knot_id

    # Test get_embeddings_and_signatures_except
    except_list = repo.get_embeddings_and_signatures_except("other_conv", limit=10)
    assert len(except_list) == 1
    assert except_list[0][0] == knot_id
    assert len(except_list[0][1]) == 384
    assert len(except_list[0][2]) == 16
    assert except_list[0][3] == payload

    # Test get_knots_in_similarity_range
    query_vec = np.ones(384, dtype="float32")
    sims = repo.get_knots_in_similarity_range(query_vec, "other_conv", 0.9, 1.1)
    assert len(sims) == 1
    assert sims[0][1] == knot_id


@pytest.mark.anyio
async def test_semantic_knot_compaction_trigger():
    # Setup mock dependencies
    mock_app_state = MagicMock()
    mock_app_state.background_engine = AsyncMock()
    mock_app_state.message_repo = MagicMock()
    mock_app_state.semantic_knot_repo = MagicMock()
    mock_app_state.embedder = AsyncMock()
    mock_app_state.structural_provider = MagicMock()

    # Mock message rows in descending order (most recent first)
    mock_messages = [
        {"id": i, "speaker": "human" if i % 2 == 0 else "apparatus", "content": f"Message content {i}"}
        for i in range(19, 0, -1)
    ]
    mock_app_state.message_repo.get_recent_with_metrics.return_value = list(mock_messages)

    # Mock existing knots (empty)
    mock_app_state.semantic_knot_repo.get_by_conversation.return_value = []

    # Mock background engine result
    mock_app_state.background_engine.run.return_value = {
        "content": "Distilled conceptual insight about symbiotic feedback loops.",
        "model": "test-background-model",
    }

    # Mock embedder
    mock_app_state.embedder.embed_text.return_value = {
        "embedding": np.ones(384, dtype="float32"),
        "model": "test-embed-model",
    }

    # Mock scorer
    with patch("backend.modules.structural_engine.CompositeStructuralScorer") as MockScorer:
        instance = MockScorer.return_value
        instance.score_async = AsyncMock(return_value=np.ones(16, dtype="float32"))

        from backend.api.routes import _fire_and_forget_semantic_knot_compaction

        task_futures = []

        def mock_create_task(coro):
            t = asyncio.create_task(coro)
            task_futures.append(t)
            return t

        with patch("asyncio.get_running_loop") as mock_loop_getter:
            mock_loop = MagicMock()
            mock_loop.create_task = mock_create_task
            mock_loop_getter.return_value = mock_loop

            _fire_and_forget_semantic_knot_compaction(mock_app_state, "conv_test")

        assert len(task_futures) == 1
        await task_futures[0]

    mock_app_state.message_repo.get_recent_with_metrics.assert_called_once_with(limit=1000, conversation_id="conv_test")

    # Chronological messages to compact should be messages 1 to 11
    # Note that range(19, 0, -1) contains IDs 19 down to 1.
    # Reversed rows: 1 up to 19.
    # Keep last 8 raw: rows[:-8] which corresponds to 1 up to 11.
    expected_text_lines = []
    for i in range(1, 12):
        speaker = "human" if i % 2 == 0 else "apparatus"
        label = "Human" if speaker == "human" else "Agent"
        expected_text_lines.append(f"{label}: Message content {i}")

    expected_text = "\n".join(expected_text_lines)

    mock_app_state.background_engine.run.assert_called_once_with("semantic_knot", {"text": expected_text})
    mock_app_state.semantic_knot_repo.insert_knot.assert_called_once()
