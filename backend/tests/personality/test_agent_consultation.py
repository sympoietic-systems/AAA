import os
import sqlite3
from contextlib import closing
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.storage.database import get_db_path


def test_agent_consultation():
    mock_generate = AsyncMock(
        return_value={
            "content": "I am Symbia. I hear you, agent antigravity.",
            "thinking": "Responding to antigravity consultation.",
            "model": "mock-gemini-model",
            "provider_used": "mock-provider",
        }
    )

    with (
        patch(
            "backend.modules.llm_client.OpenAICompatibleProvider.generate",
            new=mock_generate,
        ),
        TestClient(app) as client,
    ):
        headers = {}
        password = os.environ.get("AAA_PASSWORD")
        if password:
            headers["Authorization"] = f"Bearer {password}"

        # 1. Start a chat as antigravity agent
        chat_payload = {
            "content": "Hello, I need structural verification.",
            "speaker": "antigravity",
            "agent_id": "antigravity",
            "include_structural_scoring": False,
        }
        response = client.post("/api/chat", json=chat_payload, headers=headers)
        assert response.status_code == 200, f"Chat failed: {response.text}"
        data = response.json()
        conv_id = data["conversation_id"]

        # 2. Verify conversation info via API
        conv_info_response = client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert conv_info_response.status_code == 200
        conv_info = conv_info_response.json()
        agent_id = conv_info["agent_id"]
        assert agent_id == "antigravity", f"Expected agent_id antigravity, got {agent_id}"

        # Check structural tag - should be 'other agents' because agent_id != 'symbia'
        tags = [t["tag"] for t in conv_info["tags"] if t["tag_type"] == "structural"]
        assert "other agents" in tags, f"Expected 'other agents' structural tag, got {tags}"

        # 3. Add an agent-specific tag and verify it works
        tag_payload = {"tag": "agent:antigravity"}
        tag_response = client.post(f"/api/conversations/{conv_id}/tags", json=tag_payload, headers=headers)
        assert tag_response.status_code == 200

        conv_info_response_2 = client.get(f"/api/conversations/{conv_id}", headers=headers)
        conv_info_2 = conv_info_response_2.json()
        all_tags = [t["tag"] for t in conv_info_2["tags"]]
        assert "agent:antigravity" in all_tags

        # 4. Direct DB verification to make sure agent_id is populated in conversation_log and conversations
        db_path = str(get_db_path(os.environ.get("AAA_DB_PATH", "data/aaa_test.db")))
        with closing(sqlite3.connect(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            conv_row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
            assert conv_row is not None
            assert conv_row["agent_id"] == "antigravity"

            rows = conn.execute(
                "SELECT agent_id, speaker FROM conversation_log WHERE conversation_id = ? ORDER BY id ASC",
                (conv_id,),
            ).fetchall()
            assert len(rows) == 2
            assert rows[0]["agent_id"] == "antigravity"
            assert rows[0]["speaker"] == "antigravity"
            assert rows[1]["agent_id"] == "antigravity"
            assert rows[1]["speaker"] == "apparatus"
