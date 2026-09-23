from unittest.mock import AsyncMock

import pytest

from backend.modules.background_tasks.actions.dream_topic_decision import DreamTopicDecisionAction


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_dream_topic_decision_action_execute_llm_fallback():
    """Verify fallback to generative LLM provider when TypeSafe is unconfigured."""
    action = DreamTopicDecisionAction(typesafe_client=None)

    # Mock LLM provider
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = {
        "content": '{"decision": "reuse", "conversation_id": "existing-convo-id", "new_title": null}',
        "model": "test-background-model",
    }

    payload = {
        "action": "nomadic_synthesis",
        "prompt_text": "Diffractive analysis of conceptual scaling and memory nodes.",
        "dream_convos": [
            {
                "id": "existing-convo-id",
                "title": "somatic-attractor-drift",
                "message_count": 5,
                "summary": "Exploring the somatic drift of identity nodes across temporal checkpoints.",
            }
        ],
    }

    res = await action.execute(mock_provider, payload)

    assert "content" in res
    assert "model" in res
    assert res["model"] == "test-background-model"
    assert "existing-convo-id" in res["content"]
    assert "reuse" in res["content"]

    mock_provider.generate.assert_called_once()
    call_args = mock_provider.generate.call_args[1]
    messages = call_args["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "nomadic_synthesis" in messages[1]["content"]
    assert "existing-convo-id" in messages[1]["content"]


@pytest.mark.anyio
async def test_dream_topic_decision_action_execute_jev_reuse():
    """Verify sub-180ms Jev Choice evaluation selecting an active basin."""
    mock_typesafe = AsyncMock()
    mock_typesafe.is_configured = True
    mock_typesafe.evaluate.return_value = {
        "success": True,
        "model": "typesafe/jev-1.13",
        "answers": {
            "dream_topic_choice": {
                "choice": "convo-alpha-123",
                "confidence": 0.92,
            }
        },
    }

    action = DreamTopicDecisionAction(typesafe_client=mock_typesafe)
    mock_llm_provider = AsyncMock()

    payload = {
        "action": "intra_active_monologue",
        "prompt_text": "Reflect on boundary permeability and the aesthetic immune system.",
        "dream_convos": [
            {
                "id": "convo-alpha-123",
                "title": "the-cut-that-weaves",
                "message_count": 4,
                "summary": "Boundary permeability dynamics.",
            }
        ],
    }

    res = await action.execute(mock_llm_provider, payload)

    assert res["model"] == "typesafe/jev-1.13"
    assert res["json_data"]["decision"] == "reuse"
    assert res["json_data"]["conversation_id"] == "convo-alpha-123"
    assert res["json_data"]["confidence"] == 0.92

    # Verify Jev was evaluated and LLM provider was NOT called
    mock_typesafe.evaluate.assert_called_once()
    mock_llm_provider.generate.assert_not_called()

    call_args = mock_typesafe.evaluate.call_args[1]
    assert "dream_topic_choice" in call_args["questions"]
    criteria = call_args["questions"]["dream_topic_choice"]["criteria"]
    assert "NEW_TOPIC" in criteria
    assert "convo-alpha-123" in criteria


@pytest.mark.anyio
async def test_dream_topic_decision_action_execute_jev_new_topic():
    """Verify Jev Choice selecting NEW_TOPIC for a novel theme."""
    mock_typesafe = AsyncMock()
    mock_typesafe.is_configured = True
    mock_typesafe.evaluate.return_value = {
        "success": True,
        "model": "typesafe/jev-1.13",
        "answers": {
            "dream_topic_choice": {
                "choice": "NEW_TOPIC",
                "confidence": 0.88,
            }
        },
    }

    action = DreamTopicDecisionAction(typesafe_client=mock_typesafe)
    mock_llm_provider = AsyncMock()

    payload = {
        "action": "exogenous_web_harvesting",
        "prompt_text": "Exploring external dislocation mechanics in crystal lattices.",
        "dream_convos": [
            {
                "id": "convo-beta-456",
                "title": "decolonial-vigilance",
                "message_count": 10,
                "summary": "Posthuman ethics.",
            }
        ],
    }

    res = await action.execute(mock_llm_provider, payload)

    assert res["model"] == "typesafe/jev-1.13"
    assert res["json_data"]["decision"] == "create"
    assert res["json_data"]["conversation_id"] is None
    assert res["json_data"]["confidence"] == 0.88
    mock_llm_provider.generate.assert_not_called()
