"""Main-model synthesis routing and visible provider failure reasons."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.modules.llm_pool import ModelPoolProvider, OpenAICompatibleProvider, ProviderResponseError
from backend.services.research.steps import synthesize


def orchestrator(provider):
    return SimpleNamespace(
        _state=SimpleNamespace(llm_provider=provider),
        _get_state=lambda _: {},
        _get_cached_phase=lambda *args: {"persona": "persona", "system_prompt": "system"},
        _get_parsed_urls=lambda _: [],
        _format_reflection_markdown=lambda *args, **kwargs: "(none)",
        _log_meta=MagicMock(),
        _log_llm_response=MagicMock(),
        _save_llm_response_to_step_data=MagicMock(),
        step_repo=None,
        _TRUNC_META_LOG=2000,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("primary_fails", [False, True])
async def test_main_pool_synthesis_never_uses_sticky_nvidia_or_fallback(primary_fails, monkeypatch):
    main = "openrouter_router/main-model"
    fallback = "nvidia_router/nvidia/nemotron"
    pool = ModelPoolProvider(
        api_key="test-key", models=[main, fallback], fallback_model=fallback, nvidia_keys=["test-nvidia-key"]
    )
    pool._last_model_used = fallback
    calls = []

    async def generate(provider, *args, **kwargs):
        calls.append(provider._model)
        if primary_fails:
            raise ProviderResponseError("Provider rejected request")
        return {"content": '{"report_markdown":"# Main report"}', "model": provider._model}

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", generate)
    orch = orchestrator(pool)
    if primary_fails:
        with pytest.raises(RuntimeError, match="provider request failed"):
            await synthesize.run_synthesis(orch, "task", "objective", "goal", [], 0)
    else:
        assert await synthesize.run_synthesis(orch, "task", "objective", "goal", [], 0) == "# Main report"
    assert calls == ["main-model"]


@pytest.mark.asyncio
@pytest.mark.parametrize("error", ["Retry would exceed the provider execution boundary", "private diagnostic"])
async def test_empty_provider_failure_is_not_an_answer_shape_error(error, monkeypatch):
    response = {"content": "", "json_data": {}, "error": error}
    monkeypatch.setattr(synthesize, "generate_unified", AsyncMock(return_value=response))
    orch = orchestrator(object())
    with pytest.raises(RuntimeError) as exc:
        await synthesize.run_synthesis(orch, "task", "objective", "goal", [], 0, step_id="step")
    assert "answer must" not in str(exc.value)
    if "boundary" in error:
        assert "execution boundary exhausted" in str(exc.value)
    else:
        assert error not in str(exc.value)
    orch._save_llm_response_to_step_data.assert_called_once_with("step", response)
