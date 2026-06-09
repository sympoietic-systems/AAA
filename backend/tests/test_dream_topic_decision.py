import pytest
from unittest.mock import AsyncMock

from backend.modules.background_tasks.actions.dream_topic_decision import DreamTopicDecisionAction


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_dream_topic_decision_action_execute():
    action = DreamTopicDecisionAction()

    # Mock LLM provider
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = {
        "content": '{"decision": "reuse", "conversation_id": "existing-convo-id", "new_title": null}',
        "model": "test-background-model"
    }

    payload = {
        "action": "nomadic_synthesis",
        "prompt_text": "Diffractive analysis of conceptual scaling and memory nodes.",
        "dream_convos": [
            {
                "id": "existing-convo-id",
                "title": "somatic-attractor-drift",
                "message_count": 5,
                "summary": "Exploring the somatic drift of identity nodes across temporal checkpoints."
            }
        ]
    }

    res = await action.execute(mock_provider, payload)

    assert "content" in res
    assert "model" in res
    assert res["model"] == "test-background-model"
    assert "existing-convo-id" in res["content"]
    assert "reuse" in res["content"]

    # Verify formatting in generated call
    mock_provider.generate.assert_called_once()
    call_args = mock_provider.generate.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "nomadic_synthesis" in messages[1]["content"]
    assert "existing-convo-id" in messages[1]["content"]
    assert "Theme/Summary: Exploring the somatic drift" in messages[1]["content"]
