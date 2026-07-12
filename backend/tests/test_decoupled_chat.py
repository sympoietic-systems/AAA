import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from backend.main import app


def test_decoupled_chat_flow():
    with TestClient(app) as client:
        import os

        password = os.environ.get("AAA_PASSWORD", "").strip()
        if password:
            client.headers.update({"Authorization": f"Bearer {password}"})

        # Phase 1: Inscribe/save message
        response = client.post(
            "/api/chat/message", json={"content": "Test decoupled message persistence", "speaker": "human"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Test decoupled message persistence"
        assert data["speaker"] == "human"
        assert "conversation_id" in data
        assert "user_message_id" in data

        conv_id = data["conversation_id"]
        user_msg_id = data["user_message_id"]

        # Phase 2: Metabolize/generate response
        gen_response = client.post(
            "/api/chat/generate", json={"conversation_id": conv_id, "user_message_id": user_msg_id}
        )
        assert gen_response.status_code == 200
        gen_data = gen_response.json()
        assert gen_data["speaker"] == "apparatus"
        assert gen_data["parent_message_id"] == user_msg_id
        assert gen_data["conversation_id"] == conv_id
        assert "content" in gen_data
