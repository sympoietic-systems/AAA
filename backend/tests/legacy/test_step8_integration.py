import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

mock_generate = AsyncMock(
    return_value={
        "content": "Intra-action is Barad's key concept — the mutual constitution of entangled agencies.",
        "thinking": None,
        "model": "mock-gemini-model",
        "provider_used": "mock-provider",
    }
)

with patch(
    "backend.modules.llm_client.OpenAICompatibleProvider.generate",
    new=mock_generate,
):
    from fastapi.testclient import TestClient

    from backend.main import app

    with TestClient(app) as client:
        headers = {}
        password = os.environ.get("AAA_PASSWORD")
        if password:
            headers["Authorization"] = f"Bearer {password}"

        agent = client.get("/api/agent", headers=headers)
        print(f"Agent: {agent.status_code} -> {agent.json().get('name') if agent.status_code == 200 else agent.text}")
        assert agent.status_code == 200
        assert agent.json()["name"] == "Symbia"

        chat = client.post("/api/chat", json={"content": "What is intra-action?", "speaker": "human"}, headers=headers)
        assert chat.status_code == 200, f"Chat failed: {chat.json()}"
        chat_data = chat.json()
        print(f"Chat: {chat_data['content'][:60]}...")
        assert chat_data["model_used"] == "mock-gemini-model"
        assert chat_data["provider_used"] == "mock-provider"

        history = client.get("/api/history", headers=headers)
        msgs = history.json()["messages"]
        print(f"History: {len(msgs)} messages")
        # Find the apparatus message in history and verify fields
        apparatus_msg = next(m for m in reversed(msgs) if m["speaker"] == "apparatus")
        assert apparatus_msg["model_used"] == "mock-gemini-model"
        assert apparatus_msg["provider_used"] == "mock-provider"

        import sqlite3

        from backend.config import load_config
        from backend.storage.database import get_db_path

        config = load_config()
        db = str(get_db_path(config.get("database", {}).get("path", "data/aaa.db")))
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, agent_id, speaker, model_used, provider_used FROM conversation_log").fetchall()
        for r in rows:
            print(
                f"  DB row {r['id']}: agent_id={r['agent_id']!r}, speaker={r['speaker']}, model_used={r['model_used']!r}, provider_used={r['provider_used']!r}"
            )
        conn.close()

        assert rows[-2]["agent_id"].lower() == "symbia"
        assert rows[-1]["agent_id"].lower() == "symbia"
        assert rows[-1]["model_used"] == "mock-gemini-model"
        assert rows[-1]["provider_used"] == "mock-provider"
        print("\nAll tests passed!")
