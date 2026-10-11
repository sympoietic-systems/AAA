"""V135: provider shape errors cannot become completed research phases."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from backend.services.research.steps import consolidate, digest, evaluate, plan, reflect, synthesize
from backend.services.research.task_state import ConsolidatePayload, ReflectionPayload, StepEnvelope


def orchestrator():
    state = {"plan": {}, "digest_signals": {}}
    return SimpleNamespace(
        _state=SimpleNamespace(llm_provider=object()),
        _get_state=lambda _: state,
        _get_cached_phase=lambda *args: {"persona": "persona", "system_prompt": "system"},
        _get_parsed_urls=lambda _: [],
        _format_reflection_markdown=lambda *args, **kwargs: "(none)",
        _create_or_update_step=lambda *args: "step",
        _log_meta=MagicMock(),
        _log_llm_response=MagicMock(),
        _save_llm_response_to_step_data=MagicMock(),
        _push_sedimentation_packet=MagicMock(),
        step_repo=MagicMock(get_by_task=MagicMock(return_value=[])),
        _TRUNC_META_LOG=2000,
        satisfaction_threshold=0.85,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module,processor,runner,payload,response",
    [
        (consolidate, consolidate.ConsolidateStep, "run_consolidation", ConsolidatePayload(), {"next_queries": [{}]}),
        (
            consolidate,
            consolidate.ConsolidateStep,
            "run_consolidation",
            ConsolidatePayload(),
            {"completeness_score": "high"},
        ),
        (reflect, reflect.ReflectionStep, "run_deep_reflection", ReflectionPayload(), {"refined_queries": [{}]}),
        (
            reflect,
            reflect.ReflectionStep,
            "run_deep_reflection",
            ReflectionPayload(),
            {"revised_confidence": float("nan")},
        ),
    ],
)
async def test_v135_invalid_phase_payload_never_completes(module, processor, runner, payload, response, monkeypatch):
    orch = orchestrator()
    monkeypatch.setattr(module, runner, AsyncMock(return_value=response))
    with pytest.raises(ValidationError):
        await processor().execute(
            orch,
            StepEnvelope(task_id="task", objective="goal", current_depth=1, max_depth=4, budget=1, payload=payload),
        )
    orch.step_repo.update.assert_not_called()
    orch._push_sedimentation_packet.assert_not_called()


@pytest.mark.asyncio
async def test_v135_numeric_score_strings_validate_before_formatting(monkeypatch):
    orch = orchestrator()
    monkeypatch.setattr(consolidate, "run_consolidation", AsyncMock(return_value={"completeness_score": "0.58"}))
    output = await consolidate.ConsolidateStep().execute(
        orch,
        StepEnvelope(
            task_id="task", objective="goal", current_depth=1, max_depth=4, budget=1, payload=ConsolidatePayload()
        ),
    )
    assert output.payload.completeness_score == 0.58
    assert output.payload.last_reflection["completeness_score"] == 0.58
    assert orch.step_repo.update.call_args.kwargs["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        {"report_markdown": {"text": "report"}},
        {"answer": {}},
        {"answer": "report", "confidence": "high"},
        ["report"],
        {},
        {"report_markdown": "   "},
        "broken JSON",
    ],
)
async def test_v135_invalid_synthesis_cannot_be_reported_complete(response, monkeypatch):
    monkeypatch.setattr(synthesize, "generate_unified", AsyncMock(return_value={"json_data": response}))
    with pytest.raises(ValueError):
        await synthesize.run_synthesis(orchestrator(), "task", "objective", "goal", [], 0)


@pytest.mark.asyncio
async def test_v135_evaluator_invalid_reason_uses_safe_continue(monkeypatch):
    monkeypatch.setattr(
        evaluate,
        "generate_unified",
        AsyncMock(return_value={"json_data": {"decision": "stop", "reason": {"text": "done"}}}),
    )
    stopped, reason = await evaluate.run_evaluation(
        orchestrator(), "task", "step", "goal", 1, 4, 2, {"completeness_score": 0.5}, 0
    )
    assert not stopped
    assert isinstance(reason, str) and "fallback" in reason


@pytest.mark.asyncio
async def test_v135_invalid_plan_is_replaced_before_persistence(monkeypatch):
    orch = orchestrator()
    orch.task_repo = None
    orch.plan_repo = MagicMock()
    orch._state.config = {}
    orch._get_cached_phase = lambda *args: {"persona": "persona", "system_prompt": "system", "user_prompt": "user"}
    monkeypatch.setattr(
        plan,
        "generate_unified",
        AsyncMock(return_value={"json_data": {"search_queries": [{"query": "invalid object"}]}}),
    )
    result = await plan.run_plan_generation(orch, "task", "objective", 4, 1)
    assert result["search_queries"] == ["objective"]
    import json

    persisted = json.loads(orch.plan_repo.create.call_args.args[0]["plan_json"])
    assert persisted["search_queries"] == ["objective"]


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -0.1, 1.1])
def test_v135_completeness_must_be_finite_fraction(score):
    with pytest.raises(ValidationError):
        ConsolidatePayload(completeness_score=score)


@pytest.mark.asyncio
async def test_v135_digest_invalid_scalar_is_logged_as_shape_failure(monkeypatch):
    from backend.services.research.context_builder import ResearchContextBuilder

    monkeypatch.setattr(ResearchContextBuilder, "build_node_context", AsyncMock(return_value=""))
    monkeypatch.setattr(digest, "generate_unified", AsyncMock(return_value={"json_data": {"learnings": False}}))
    orch = orchestrator()
    result = await digest.analyze_source_content(
        orch, "task", "https://example.org", "Source", "Useful content. " * 40, "query", "goal", 1, 4
    )
    assert result["error_category"] == "invalid_structured_response"
    orch._log_llm_response.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed_retained_state", [False, True])
async def test_v135_failed_document_phase_does_not_advance_or_mark_document_digested(
    tmp_path, monkeypatch, malformed_retained_state
):
    from backend.services.research.orchestrator import SomaticResearchOrchestrator
    from backend.services.research.steps.base import ResearchStepRegistry
    from backend.services.research.task_state import DocDigestPayload, StepOutput
    from backend.storage.database import init_db
    from backend.storage.repositories.research.research_plan import ResearchPlanRepository
    from backend.storage.repositories.research.research_step import ResearchStepRepository
    from backend.storage.repositories.research.research_task import ResearchTaskRepository

    db = str(tmp_path / "phase.db")
    init_db(db).close()
    tasks, steps, plans = ResearchTaskRepository(db), ResearchStepRepository(db), ResearchPlanRepository(db)
    tasks.create(
        {
            "id": "task",
            "title": "Fixture",
            "objective": "goal",
            "trigger_source": "test",
            "status": "active",
            "max_depth": 4,
            "budget_limit_usd": 1,
        }
    )
    plans.create({"id": "plan", "task_id": "task", "plan_json": "{}"})
    app = SimpleNamespace(
        config={"research_orchestrator": {}},
        research_task_repo=tasks,
        research_step_repo=steps,
        research_plan_repo=plans,
        research_step_result_repo=None,
        research_meta_log_repo=None,
    )
    orch = SomaticResearchOrchestrator(app)
    state = orch.init_task("task")
    state.update(phase="document_digestion", plan_id="plan", inject_file_id="document")
    if malformed_retained_state:
        state["injected_documents"] = [{"file_id": {"bad": "type"}}]
    processor = SimpleNamespace(
        step_type="document_digestion",
        execute=AsyncMock(
            return_value=StepOutput(status="failed", message="document not yet indexed", payload=DocDigestPayload())
        ),
    )
    monkeypatch.setattr(ResearchStepRegistry, "get_step", lambda _: processor)
    result = await orch.execute_step("task")
    assert result["status"] == "error" and result["failed_phase"] == "document_digestion"
    assert tasks.get("task")["status"] == "failed"
    assert not state["document_digested"]
    assert steps.get_by_task("task")[0]["status"] == "failed"
    if malformed_retained_state:
        processor.execute.assert_not_awaited()
    await orch.aclose()
