import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, "D:/AAA")

mock_generate = AsyncMock(return_value={
    "content": "Intra-action is Barad's key concept — the mutual constitution of entangled agencies.",
    "thinking": None,
})

with patch(
    "backend.modules.llm_client.OpenAICompatibleProvider.generate",
    new=mock_generate,
):
    from backend.main import app

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        agent = client.get("/api/agent")
        print(f"Agent: {agent.status_code} -> {agent.json()['name']}")
        assert agent.status_code == 200
        assert agent.json()["name"] == "Symbia"

        chat = client.post("/api/chat", json={"content": "What is intra-action?", "speaker": "human"})
        assert chat.status_code == 200, f"Chat failed: {chat.json()}"
        print(f"Chat: {chat.json()['content'][:60]}...")

        history = client.get("/api/history")
        msgs = history.json()["messages"]
        print(f"History: {len(msgs)} messages")

        import sqlite3
        db = "D:/AAA/backend/data/aaa.db"
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, agent_id, speaker FROM conversation_log").fetchall()
        for r in rows:
            print(f"  DB row {r['id']}: agent_id={r['agent_id']!r}, speaker={r['speaker']}")
        conn.close()

        assert rows[0]["agent_id"] == "Symbia"
        assert rows[1]["agent_id"] == "Symbia"
        print("\nAll tests passed!")
