import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

mock_generate = AsyncMock(return_value={
    "content": "I am Symbia. I hear you, agent antigravity.",
    "thinking": "Responding to antigravity consultation.",
    "model": "mock-gemini-model",
    "provider_used": "mock-provider",
})

with patch(
    "backend.modules.llm_client.OpenAICompatibleProvider.generate",
    new=mock_generate,
):
    from backend.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
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
        print(f"Created conversation {conv_id} as agent antigravity.")

        # 2. Verify conversation info via API
        conv_info_response = client.get(f"/api/conversations/{conv_id}", headers=headers)
        assert conv_info_response.status_code == 200
        conv_info = conv_info_response.json()
        assert conv_info["agent_id"] == "antigravity", f"Expected agent_id antigravity, got {conv_info['agent_id']}"
        
        # Check structural tag - should be 'other agents' because agent_id != 'symbia'
        tags = [t["tag"] for t in conv_info["tags"] if t["tag_type"] == "structural"]
        print(f"Conversation tags: {conv_info['tags']}")
        assert "other agents" in tags, f"Expected 'other agents' structural tag, got {tags}"

        # 3. Add an agent-specific tag and verify it works
        tag_payload = {"tag": "agent:antigravity"}
        tag_response = client.post(f"/api/conversations/{conv_id}/tags", json=tag_payload, headers=headers)
        assert tag_response.status_code == 200

        conv_info_response_2 = client.get(f"/api/conversations/{conv_id}", headers=headers)
        conv_info_2 = conv_info_response_2.json()
        all_tags = [t["tag"] for t in conv_info_2["tags"]]
        print(f"All tags after adding: {all_tags}")
        assert "agent:antigravity" in all_tags

        # 4. Direct DB verification to make sure agent_id is populated in conversation_log and conversations
        import sqlite3
        from backend.storage.database import get_db_path
        from backend.config import load_config
        config = load_config()
        db = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row

        # Check conversations table
        conv_row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        assert conv_row is not None
        print(f"DB conversations row: id={conv_row['id']}, title={conv_row['title']!r}, agent_id={conv_row['agent_id']!r}")
        assert conv_row["agent_id"] == "antigravity"

        # Check conversation_log table
        rows = conn.execute("SELECT id, agent_id, speaker, content FROM conversation_log WHERE conversation_id = ? ORDER BY id ASC", (conv_id,)).fetchall()
        for r in rows:
            print(f"  DB msg row {r['id']}: agent_id={r['agent_id']!r}, speaker={r['speaker']!r}, content={r['content'][:30]!r}")
        
        # User/agent message
        assert rows[0]["agent_id"] == "antigravity"
        assert rows[0]["speaker"] == "antigravity"

        # Assistant message
        assert rows[1]["agent_id"] == "antigravity"
        assert rows[1]["speaker"] == "apparatus"

        conn.close()
        print("\nAll agent consultation integration tests passed successfully!")
