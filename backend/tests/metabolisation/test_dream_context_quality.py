from types import SimpleNamespace

import pytest

from backend.metabolisation.dream_context import DreamContextMixin


class DreamConversationRepository:
    def list_all(self):
        return [SimpleNamespace(id="dream-1", title="belief-alpha")]

    def get_tags(self, _conversation_id):
        return [{"tag_type": "structural", "tag": "dreams"}]


class DreamMessageRepository:
    def __init__(self, messages):
        self.messages = messages

    def get_recent(self, *, limit, conversation_id):
        assert conversation_id == "dream-1"
        return self.messages[-limit:]


def make_daemon(messages):
    daemon = object.__new__(DreamContextMixin)
    daemon.conversation_repo = DreamConversationRepository()
    daemon.message_repo = DreamMessageRepository(messages)
    daemon.app_state = SimpleNamespace(belief_metabolism=None)
    return daemon


@pytest.mark.asyncio
async def test_v124_last_dream_response_skips_degraded_assistant_messages():
    daemon = make_daemon(
        [
            SimpleNamespace(speaker="apparatus", content="Sound older response", quality_status="sound"),
            SimpleNamespace(speaker="apparatus", content="Degraded response", quality_status="degraded"),
        ]
    )

    result = await daemon._get_last_dream_response_for_belief("belief-alpha")

    assert result == "Sound older response"


@pytest.mark.asyncio
async def test_v124_recent_dream_themes_ignore_conversations_with_only_degraded_replies():
    daemon = make_daemon([SimpleNamespace(speaker="apparatus", content="Degraded response", quality_status="degraded")])

    result = await daemon._get_drift_context()

    assert "recent_dream_themes" not in result
