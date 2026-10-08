import pytest

from backend.modules.llm_pool import ModelPoolProvider


def test_nvidia_deepseek_routes_replaced_with_nemotron_without_changing_other_providers(caplog):
    original = [
        "nvidia_router/deepseek-ai/deepseek-v4.1-flash",
        "nvidia_router/nvidia/nemotron-3-super-120b-a12b",
        "nvidia_router/nvidia/nemotron-3-ultra-550b-a55b",
        "openrouter_router/deepseek/deepseek-chat",
        "deepseek_router/deepseek-v4-pro",
    ]
    pool = ModelPoolProvider("", original, fallback_model=original[0])
    assert pool._models == original[1:]
    assert pool._fallback_model == original[1]
    assert original[0] == "nvidia_router/deepseek-ai/deepseek-v4.1-flash"
    assert "NVIDIA DeepSeek route disabled" in caplog.text


@pytest.mark.asyncio
async def test_per_call_nvidia_deepseek_override_requests_nemotron(monkeypatch):
    from backend.modules.llm_http import OpenAICompatibleProvider

    seen = []

    async def generate(provider, messages, **params):
        seen.append(provider._model)
        return {"content": "fixture response", "finish_reason": "stop"}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    pool = ModelPoolProvider("", ["nvidia_router/nvidia/nemotron-3-ultra-550b-a55b"], nvidia_keys=["fixture"])
    result = await pool.generate([], model="nvidia_router/deepseek-ai/deepseek-v4.1-flash")
    assert result["content"] == "fixture response"
    assert seen == ["nvidia/nemotron-3-super-120b-a12b"]
