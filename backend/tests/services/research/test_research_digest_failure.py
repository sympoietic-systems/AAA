from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.modules.llm_http import OpenAICompatibleProvider
from backend.modules.llm_pool import ModelPoolProvider
from backend.modules.llm_protocol import RateLimitError
from backend.modules.provider_attempts import AttemptBudgetExceeded, AttemptScope, attempt_scope
from backend.services.research.steps import digest
from backend.services.research.task_state import DigestPayload, StepEnvelope


@pytest.mark.asyncio
async def test_upstream_429_preserves_shared_key_for_next_paid_model(monkeypatch):
    import backend.modules.llm_pool as pool_module

    pool = ModelPoolProvider("fixture-key", ["openrouter_router/first", "openrouter_router/second"], fallback_model="")
    provider = MagicMock()
    provider.generate = AsyncMock(
        side_effect=[
            RateLimitError("capacity", limit_source="upstream_provider_shared_pool"),
            {"content": "Evidence"},
        ]
    )
    monkeypatch.setattr(pool_module, "OpenAICompatibleProvider", lambda **kwargs: provider)
    result = await pool.generate([])
    assert result["content"] == "Evidence"
    assert provider.generate.await_count == 2
    assert not pool._openrouter_key_mgr._exhausted


@pytest.mark.asyncio
async def test_unknown_429_still_cools_credential(monkeypatch):
    import backend.modules.llm_pool as pool_module

    pool = ModelPoolProvider("fixture-key", ["openrouter_router/first", "openrouter_router/second"], fallback_model="")
    provider = MagicMock()
    provider.generate = AsyncMock(side_effect=RateLimitError("credential limited"))
    monkeypatch.setattr(pool_module, "OpenAICompatibleProvider", lambda **kwargs: provider)
    with pytest.raises(RateLimitError):
        await pool.generate([])
    assert provider.generate.await_count == 1
    assert pool._openrouter_key_mgr._exhausted


@pytest.mark.asyncio
async def test_upstream_429_reports_unknown_headers_without_private_metadata(monkeypatch, caplog):
    import httpx

    provider = OpenAICompatibleProvider("fixture", "fixture", "https://openrouter.ai/api/v1", max_retries=0)
    response = httpx.Response(
        429,
        json={
            "error": {
                "metadata": {
                    "limit_source": "upstream_provider_shared_pool",
                    "raw": "private upstream details",
                }
            }
        },
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
    )
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.post = AsyncMock(return_value=response)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client)
    with pytest.raises(RateLimitError) as exc:
        await provider._request_with_retry({"model": "fixture", "messages": []})
    assert exc.value.limit_source == "upstream_provider_shared_pool"
    assert exc.value.remaining is None and exc.value.limit is None
    assert "unknown/unknown" in caplog.text
    assert "private upstream" not in caplog.text


@pytest.mark.asyncio
async def test_v118_research_pool_waits_for_cooldown_without_resetting_policy(monkeypatch):
    import backend.modules.llm_pool as pool_module

    clock = [100.0]
    monkeypatch.setattr(pool_module.time, "time", lambda: clock[0])
    pool = ModelPoolProvider("", ["nvidia_router/fixture"], fallback_model="", nvidia_keys=["fixture-key"])
    pool._exhausted["nvidia_router/fixture"] = 110.0
    provider = MagicMock()
    provider.provider_name = "fixture"
    provider.model_id = "fixture"
    provider.generate = AsyncMock(return_value={"content": "Evidence", "finish_reason": "stop"})
    monkeypatch.setattr(pool_module, "OpenAICompatibleProvider", lambda **kwargs: provider)
    waits = []

    async def delay(seconds):
        waits.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(pool_module, "retry_delay", delay)
    sink = SimpleNamespace(start=AsyncMock(), finish=AsyncMock())
    scope = AttemptScope(sink, datetime.now(UTC) + timedelta(seconds=30), 5, 2)
    deadline = scope.deadline
    with attempt_scope(scope):
        result = await pool.generate([{"role": "user", "content": "Fixture"}])
    assert result["content"] == "Evidence"
    assert len(waits) == 1 and waits[0] >= 10
    assert scope.deadline == deadline and scope.number == 1
    assert sink.start.await_count == 1


@pytest.mark.asyncio
async def test_v117_pool_cooldown_cannot_extend_deadline():
    import time

    pool = ModelPoolProvider("", ["nvidia_router/fixture"], fallback_model="", nvidia_keys=["fixture-key"])
    pool._exhausted["nvidia_router/fixture"] = time.time() + 30
    sink = SimpleNamespace(start=AsyncMock(), finish=AsyncMock())
    scope = AttemptScope(sink, datetime.now(UTC) + timedelta(seconds=1), 1, 1)
    with attempt_scope(scope), pytest.raises(AttemptBudgetExceeded):
        await pool.generate([])
    sink.start.assert_not_awaited()


@pytest.mark.asyncio
async def test_pool_unscoped_cooldown_remains_fail_fast(monkeypatch):
    import time

    import backend.modules.llm_pool as pool_module

    pool = ModelPoolProvider("", ["nvidia_router/fixture"], fallback_model="", nvidia_keys=["fixture-key"])
    pool._exhausted["nvidia_router/fixture"] = time.time() + 30
    delay = AsyncMock()
    monkeypatch.setattr(pool_module, "retry_delay", delay)
    with pytest.raises(RateLimitError, match="cooldown"):
        await pool.generate([])
    delay.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("completion", ["invalid JSON", RateLimitError("private failure")])
async def test_v118_analysis_failure_has_explicit_gap_and_no_findings(monkeypatch, completion):
    monkeypatch.setattr(
        "backend.services.research.context_builder.ResearchContextBuilder.build_node_context",
        AsyncMock(return_value=""),
    )
    generate = AsyncMock()
    if isinstance(completion, Exception):
        generate.side_effect = completion
    else:
        generate.return_value = {"content": completion}
    orch = SimpleNamespace(
        _state=SimpleNamespace(llm_provider=SimpleNamespace(generate=generate, provider_name="fixture")),
        _get_state=lambda _: {},
        _log_meta=MagicMock(),
        _log_llm_response=MagicMock(),
    )
    result = await digest.analyze_source_content(
        orch,
        "task",
        "https://example.org/source",
        "Source",
        "Usable source content. " * 20,
        "query",
        "goal",
        0,
        1,
    )
    assert result["analysis_status"] == "failed"
    assert result["learnings"] == [] and result["gaps"]
    assert "private" not in str(result)


@pytest.mark.asyncio
async def test_v118_failed_digest_is_partial_and_does_not_count_failed_analysis(monkeypatch):
    state = {"plan": {"search_queries": ["query"]}}
    step_repo = MagicMock()
    orch = SimpleNamespace(
        _get_state=lambda _: state,
        _create_or_update_step=lambda *args, **kwargs: "digest-step",
        step_repo=step_repo,
        step_result_repo=None,
        task_repo=MagicMock(),
    )
    monkeypatch.setattr(
        digest,
        "parallel_digest_grouped",
        AsyncMock(
            return_value=[
                {
                    "query_group": 1,
                    "source_url": "https://example.org/source",
                    "source_title": "Source",
                    "result": {
                        "analysis_status": "failed",
                        "learnings": [],
                        "gaps": ["Provider unavailable"],
                        "followups": [],
                    },
                }
            ]
        ),
    )
    output = await digest.DigestStep().execute(
        orch,
        StepEnvelope(
            task_id="task",
            objective="Investigate",
            current_depth=0,
            max_depth=1,
            budget=0.5,
            payload=DigestPayload(parsed_sources_cache=[{"url": "https://example.org/source", "content": "Source"}]),
        ),
    )
    assert output.status == "partial"
    assert output.payload.analyzed_sources_count == 0
    assert output.payload.gaps and not output.new_findings
    assert step_repo.update.call_args.kwargs["status"] == "failed"
    assert "failed" in step_repo.update.call_args.kwargs["result_summary"]
    assert "Source analysis unavailable" in state["result_summary"]
