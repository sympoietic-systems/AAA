from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.modules.providers.typesafe_provider import (
    DEFAULT_TYPESAFE_BASE,
    TypeSafeDecisionClient,
    build_choice_question,
    build_noul_question,
    build_score_question,
)


def test_client_init_and_url_resolution():
    # Direct TypeSafe
    client_ts = TypeSafeDecisionClient(api_key="ts-key", api_base=DEFAULT_TYPESAFE_BASE)
    assert client_ts.is_configured is True
    assert client_ts._resolve_url() == "https://api.typesafe.ai/v1/systemone"

    # OpenRouter
    client_or = TypeSafeDecisionClient(api_key="or-key", api_base="https://openrouter.ai/api/alpha")
    assert client_or.is_configured is True
    assert client_or._resolve_url() == "https://openrouter.ai/api/alpha/decisions"

    # Unconfigured
    client_none = TypeSafeDecisionClient()
    assert client_none.is_configured is False


def test_question_builders():
    choice = build_choice_question("Which skill?", ["api-design", "database-design"], id="q_choice")
    assert choice["type"] == "Choice"
    assert choice["id"] == "q_choice"
    assert choice["options"] == ["api-design", "database-design"]

    noul = build_noul_question("Is code execution required?", id="q_noul")
    assert noul["type"] == "Noul"
    assert noul["id"] == "q_noul"

    score = build_score_question("Rate tension", ["low", "med", "high"], id="q_score")
    assert score["type"] == "Score"
    assert score["options"] == ["low", "med", "high"]


@pytest.mark.asyncio
async def test_evaluate_success_mock():
    client = TypeSafeDecisionClient(api_key="test-key")

    mock_resp_data = {
        "results": {
            "q_choice": {
                "decision": "api-design",
                "confidence": 0.89,
                "probabilities": {"api-design": 0.89, "database-design": 0.11},
            },
            "gate_action": {
                "probability": 0.85,
                "confidence": 0.90,
            },
        }
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_resp_data

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        state = {"turn": "Can you design a REST API for my store?"}
        questions = [
            build_choice_question("Choose skill", ["api-design", "database-design"], id="q_choice"),
            build_noul_question("Is operational?", id="gate_action"),
        ]

        res = await client.evaluate(state=state, questions=questions)
        assert res["success"] is True
        assert res["answers"]["q_choice"]["decision"] == "api-design"
        assert res["answers"]["q_choice"]["confidence"] == 0.89
        assert res["answers"]["gate_action"]["probability"] == 0.85


@pytest.mark.asyncio
async def test_evaluate_unconfigured():
    client = TypeSafeDecisionClient(api_key=None)
    res = await client.evaluate(state={"turn": "hello"}, questions=[])
    assert res["success"] is False
    assert "not configured" in res["error"]
