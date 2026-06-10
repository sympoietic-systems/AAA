import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np
import pytest

# Ensure parent directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.modules.context_collector import ContextCollectorModule
from backend.personality.assembler import PromptAssemblerModule
from backend.modules.consolidation_checkpoint import ConsolidationCheckpointModule
from backend.modules.conversation_metrics import ConversationMetricsModule
from backend.storage.models import Message


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_context_collector_branching():
    # Setup mocks
    mock_msg_repo = MagicMock()
    mock_note_repo = MagicMock()
    
    # Root message (ID 1) -> Branch leaf (ID 2)
    msg1 = Message(
        id=1, timestamp=None, agent_id="", conversation_id="conv_test",
        speaker="human", content="Root message", embedding=b"", embedding_model="", embedding_dim=0
    )
    msg2 = Message(
        id=2, timestamp=None, agent_id="", conversation_id="conv_test",
        speaker="apparatus", content="Response", parent_message_id=1,
        embedding=b"", embedding_model="", embedding_dim=0
    )
    
    mock_msg_repo.get_ancestor_path.return_value = [msg1, msg2]
    mock_note_repo.get_notes_by_conversation.return_value = []
    
    module = ContextCollectorModule(
        message_repo=mock_msg_repo,
        note_repo=mock_note_repo,
        max_history=10,
        floating_window=5,
        caveman_enabled=False
    )
    
    payload = {
        "conversation_id": "conv_test",
        "parent_message_id": 2,
        "content": "Next human input"
    }
    
    res = await module.process(payload)
    
    # Check that ancestor path query was called with parent_message_id
    mock_msg_repo.get_ancestor_path.assert_called_once_with(2, limit=10)
    
    # Check payload injections
    assert res["branch_context_tag"] == "msg_2"
    assert res["ancestor_message_ids"] == [1, 2]
    assert len(res["messages"]) == 3  # Msg 1, Msg 2, current input (Next human input)
    assert res["messages"][0]["content"] == "Root message"
    assert res["messages"][1]["role"] == "assistant"


@pytest.mark.anyio
async def test_prompt_assembler_branching(tmp_path):
    # Create a dummy identity yaml
    identity_file = tmp_path / "identity.yaml"
    identity_file.write_text("personality:\n  system_prompt: 'You are Symbia.'")
    
    mock_skill_registry = MagicMock()
    
    module = PromptAssemblerModule(
        identity_path=identity_file,
        skill_registry=mock_skill_registry
    )
    
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "branch_context_tag": "msg_42"
    }
    
    res = await module.process(payload)
    
    # Verify system message has the nomadic branch tag appended
    system_msg = res["messages"][0]
    assert system_msg["role"] == "system"
    assert "[Nomadic Branch Context Tag: msg_42]" in system_msg["content"]


@pytest.mark.anyio
async def test_consolidation_checkpoint_branching():
    mock_checkpoint_repo = MagicMock()
    mock_memory_node_repo = MagicMock()
    
    # Mock path checkpoint
    mock_checkpoint = {
        "id": 100,
        "conversation_id": "conv_test",
        "message_count": 2,
        "summary": "Summary text",
        "human_summary": "Human prose summary"
    }
    mock_checkpoint_repo.get_latest_checkpoint_for_path.return_value = mock_checkpoint
    
    mock_memory_node_repo.get_nodes_by_checkpoint.return_value = [
        {"id": "node_1", "node_type": "concept", "intensity": 0.9, "intra_active_text": "Gravity trace"}
    ]
    
    module = ConsolidationCheckpointModule(
        checkpoint_repo=mock_checkpoint_repo,
        consolidate_threshold=15,
        memory_node_repo=mock_memory_node_repo
    )
    
    payload = {
        "conversation_id": "conv_test",
        "ancestor_message_ids": [1, 2],
        "raw_msg_count": 3,
        "messages": [{"role": "user", "content": "new question"}]
    }
    
    res = await module.process(payload)
    
    # Verify path-scoped checkpoint resolution
    mock_checkpoint_repo.get_latest_checkpoint_for_path.assert_called_once_with("conv_test", [1, 2])
    # Verify nodes retrieved by checkpoint ID
    mock_memory_node_repo.get_nodes_by_checkpoint.assert_called_once_with(100)
    
    # Verify checkpoint system message was prepended
    assert len(res["messages"]) == 2
    assert "Human prose summary" in res["messages"][0]["content"]
    assert "- [CONCEPT] Gravity trace" in res["messages"][0]["content"]


@pytest.mark.anyio
async def test_conversation_metrics_branching():
    mock_msg_repo = MagicMock()
    
    # Mock ancestor messages with embeddings
    emb = np.ones(384, dtype="float32").tobytes()
    msg1 = Message(
        id=1, timestamp=None, agent_id="", conversation_id="conv_test",
        speaker="human", content="Root", embedding=emb, embedding_model="test", embedding_dim=384
    )
    msg2 = Message(
        id=2, timestamp=None, agent_id="", conversation_id="conv_test",
        speaker="apparatus", content="Response", embedding=emb, embedding_model="test", embedding_dim=384
    )
    
    mock_msg_repo.get_by_ids.return_value = [msg1, msg2]
    mock_msg_repo.get_recent_with_metrics_for_path.return_value = [
        {"id": 2, "s_t": 0.5, "novelty": 0.1, "rolling_entropy": 0.01, "coupling": 0.6, "agent_divergence": 0.2, "reverse_perturbation": 0.3, "surprise_index": 0.4, "mutual_perturbation": 0.5}
    ]
    
    module = ConversationMetricsModule(
        message_repo=mock_msg_repo,
        pairwise_window=2,
        entropy_window=2,
        agent_self_window=2
    )
    
    payload = {
        "conversation_id": "conv_test",
        "ancestor_message_ids": [1, 2],
        "embedding": emb,
        "embedding_dim": 384
    }
    
    res = await module.process(payload)
    
    # Verify metrics calculated correctly and prior metrics loaded via path
    mock_msg_repo.get_by_ids.assert_called_once_with([1, 2])
    mock_msg_repo.get_recent_with_metrics_for_path.assert_called_once_with([1, 2], limit=5, exclude_message_id=None)
    
    assert res["metrics"] is not None
    assert "pairwise_similarity" in res["metrics"]
    assert "homeostatic_deficit" in res
