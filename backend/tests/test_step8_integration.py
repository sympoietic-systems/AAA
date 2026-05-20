import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, "D:/AAA")

mock_generate = AsyncMock(return_value={
    "content": "Hello! This is a *markdown* test.\n\n```python\nprint('hi')\n```",
    "thinking": "Let me analyze this question step by step...",
})

with patch(
    "backend.modules.llm_client.OpenAICompatibleProvider.generate",
    new=mock_generate,
):
    from backend.main import app

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        health = client.get("/api/health")
        print(f"Health: {health.status_code} {health.json()['status']}")

        chat = client.post("/api/chat", json={"content": "Hi!", "speaker": "human"})
        print(f"Chat status: {chat.status_code}")
        data = chat.json()
        print(f"Content: {data.get('content', '')[:60]}")
        print(f"Thinking: {data.get('thinking', '')[:60]}")
        assert chat.status_code == 200
        assert "markdown" in data["content"]
        assert data["thinking"] == "Let me analyze this question step by step..."
        assert data["speaker"] == "apparatus"

        history = client.get("/api/history")
        hist_data = history.json()
        print(f"History count: {hist_data['count']}")
        assert hist_data["count"] >= 2

        apparatus_msg = [m for m in hist_data["messages"] if m["speaker"] == "apparatus"][0]
        print(f"History thinking: {apparatus_msg.get('thinking', '')[:60]}")
        assert apparatus_msg["thinking"] == "Let me analyze this question step by step..."

        print("\nFull integration test passed!")
