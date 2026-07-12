import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Ensure parent directory is in path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Mock LLM generation to return a proposed line of flight
mock_generate = AsyncMock(
    return_value={
        "content": 'This is a response to your query.\n<line_of_flight title="Parallel Drift">Let us explore nomadic drift without representation.</line_of_flight>',
        "thinking": "Synthesizing Barad and Deleuze...",
        "model": "mock-gemini-model",
        "provider_used": "mock-provider",
    }
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_branching_api_integration():
    with patch(
        "backend.modules.llm_client.OpenAICompatibleProvider.generate",
        new=mock_generate,
    ):
        from fastapi.testclient import TestClient

        from backend.main import app

        with TestClient(app) as client:
            # 1. Start a new conversation and send a root message
            chat_req_1 = {"content": "Hello, let us start.", "speaker": "human"}
            res1 = client.post("/api/chat", json=chat_req_1)
            assert res1.status_code == 200
            data1 = res1.json()
            conversation_id = data1["conversation_id"]
            user_msg_1_id = data1["user_message_id"]
            agent_msg_1_id = data1["id"]

            # Verify the <line_of_flight> was stripped and returned in proposed_branches
            assert "<line_of_flight>" not in data1["content"]
            assert "This is a response to your query." in data1["content"]
            assert len(data1["proposed_branches"]) == 1
            assert data1["proposed_branches"][0]["title"] == "Parallel Drift"
            assert "nomadic drift" in data1["proposed_branches"][0]["content"]

            # 2. Send a branched message specifying a parent (e.g. branch off agent_msg_1_id)
            chat_req_2 = {
                "content": "Exploring a tangent.",
                "speaker": "human",
                "conversation_id": conversation_id,
                "parent_message_id": agent_msg_1_id,
            }
            res2 = client.post("/api/chat", json=chat_req_2)
            assert res2.status_code == 200
            data2 = res2.json()
            user_msg_2_id = data2["user_message_id"]
            agent_msg_2_id = data2["id"]

            # Verify parent links
            # User message 2 parent should be agent_msg_1_id
            # Agent message 2 parent should be user_msg_2_id
            assert data2["parent_message_id"] == user_msg_2_id

            # 3. Retrieve tree data for the conversation
            tree_res = client.get(f"/api/conversations/{conversation_id}/tree")
            assert tree_res.status_code == 200
            tree_data = tree_res.json()

            # Verify tree nodes
            nodes = tree_data["nodes"]
            assert len(nodes) >= 4  # user_msg_1, agent_msg_1, user_msg_2, agent_msg_2

            user_msg_2_node = next(n for n in nodes if n["id"] == user_msg_2_id)
            assert user_msg_2_node["parent_message_id"] == agent_msg_1_id

            # 4. Commit a proposed branch
            commit_req = {
                "parent_message_id": agent_msg_1_id,
                "content": "Exploring the proposed branch.",
                "speaker": "apparatus",
            }
            commit_res = client.post(f"/api/conversations/{conversation_id}/commit-branch", json=commit_req)
            assert commit_res.status_code == 200
            commit_data = commit_res.json()

            assert commit_data["content"] == "Exploring the proposed branch."
            assert commit_data["parent_message_id"] == agent_msg_1_id
            assert commit_data["speaker"] == "apparatus"

            # 5. Fetch history and verify parent message IDs are returned
            hist_res = client.get(f"/api/history?conversation_id={conversation_id}")
            assert hist_res.status_code == 200
            hist_data = hist_res.json()

            # Find the committed message in history
            committed_msg = next(m for m in hist_data["messages"] if m["id"] == commit_data["id"])
            assert committed_msg["parent_message_id"] == agent_msg_1_id

            # 6. Test trimmed text in conversation tree
            long_text = "A" * 150
            chat_req_long = {
                "content": long_text,
                "speaker": "human",
                "conversation_id": conversation_id,
                "parent_message_id": agent_msg_2_id,
            }
            res_long = client.post("/api/chat", json=chat_req_long)
            assert res_long.status_code == 200
            user_msg_long_id = res_long.json()["user_message_id"]

            tree_res_2 = client.get(f"/api/conversations/{conversation_id}/tree")
            assert tree_res_2.status_code == 200
            nodes_2 = tree_res_2.json()["nodes"]
            long_node = next(n for n in nodes_2 if n["id"] == user_msg_long_id)
            assert len(long_node["content"]) == 123  # 120 + "..."
            assert long_node["content"].endswith("...")

            # 7. Test get message path endpoint
            path_res = client.get(f"/api/messages/{user_msg_long_id}/path")
            assert path_res.status_code == 200
            path_data = path_res.json()
            path_ids = [m["id"] for m in path_data]
            assert user_msg_1_id in path_ids
            assert agent_msg_1_id in path_ids
            assert user_msg_2_id in path_ids
            assert agent_msg_2_id in path_ids
            assert user_msg_long_id in path_ids
            assert path_ids == sorted(path_ids)
