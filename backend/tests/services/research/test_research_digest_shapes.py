import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.services.research.context_builder import ResearchContextBuilder
from backend.services.research.steps import digest
from backend.services.research.task_state import DigestPayload, StepEnvelope


def structured_analysis():
    return {
        "analysis_status": "complete",
        "learnings": [{"learning": "A source claim", "relevance": "Model relevance assessment"}],
        "gaps": [{"gap": "Missing evidence", "impact": "Model impact assessment"}],
        "followups": [{"followup": "Check the evidence", "type": "query"}],
        "direct_urls": ["https://example.org/source"],
        "diffractive_notes": [{"note": "Interpretive objection", "connection": "Model connection"}],
    }


def test_v134_structured_analysis_projects_only_text_and_retains_metadata():
    raw = structured_analysis()
    result = digest.normalize_analysis(raw)
    assert result["learnings"] == ["A source claim"]
    assert result["gaps"] == ["Missing evidence"]
    assert result["followups"] == ["Check the evidence"]
    assert result["diffractive_notes"] == ["Interpretive objection"]
    assert result["raw_analysis"] == raw
    assert raw["learnings"][0]["relevance"] == "Model relevance assessment"
    assert digest.normalize_analysis(result) == result


def test_v134_single_text_fields_are_single_items_without_character_claims():
    raw = {"analysis_status": "complete", "learnings": "One claim", "diffractive_notes": "One note"}
    result = digest.normalize_analysis(raw)
    assert result["learnings"] == ["One claim"]
    assert result["diffractive_notes"] == ["One note"]
    assert result["raw_analysis"] == raw


@pytest.mark.parametrize("invalid", [0, False, [42], [{"relevance": "Not a claim"}]])
def test_v134_unknown_shapes_are_explicit_source_failures(invalid):
    result = digest.normalize_analysis({"analysis_status": "complete", "learnings": invalid})
    assert result["analysis_status"] == "failed"
    assert result["error_category"] == "invalid_structured_response"
    assert result["learnings"] == [] and result["gaps"]


@pytest.mark.asyncio
async def test_v134_fresh_model_analysis_is_projected_before_delivery(monkeypatch):
    monkeypatch.setattr(ResearchContextBuilder, "build_node_context", AsyncMock(return_value=""))
    monkeypatch.setattr(digest, "generate_unified", AsyncMock(return_value={"json_data": structured_analysis()}))
    orch = SimpleNamespace(
        _state=SimpleNamespace(llm_provider=object()),
        _get_state=lambda _: {},
        _log_meta=MagicMock(),
        _log_llm_response=MagicMock(),
    )
    result = await digest.analyze_source_content(
        orch, "task", "https://example.org/source", "Source", "Usable source content. " * 20, "query", "goal", 2, 4
    )
    assert result["analysis_status"] == "complete"
    assert result["learnings"] == ["A source claim"]
    assert result["raw_analysis"]["gaps"][0]["impact"] == "Model impact assessment"


@pytest.mark.asyncio
async def test_v134_retained_structured_analysis_recovery_needs_no_model_call(monkeypatch):
    raw = structured_analysis()
    state = {"_reuse_completed_digests": True}
    results = SimpleNamespace(
        get_by_step=MagicMock(return_value=[{"id": "source-result", "source_url": "https://example.org/source"}]),
        update_analysis=MagicMock(),
    )
    evidence = SimpleNamespace(
        repo=SimpleNamespace(get_source=MagicMock(return_value=("artifact",))),
        record_interpretation=MagicMock(return_value=("claim",)),
        packet=MagicMock(return_value=None),
    )
    orch = SimpleNamespace(
        _get_state=lambda _: state,
        _get_semaphore=lambda: asyncio.Semaphore(1),
        evidence_store_for=lambda _: evidence,
        step_repo=None,
        step_result_repo=results,
    )
    analyzer = AsyncMock(side_effect=AssertionError("Recovery must not call the model"))
    monkeypatch.setattr(digest, "analyze_source_content", analyzer)
    output = await digest.parallel_digest_grouped(
        orch,
        "task",
        {1: "digest-step"},
        [{"url": "https://example.org/source", "title": "Source", "existing_analysis": raw}],
        ["query"],
        "objective",
        2,
        4,
    )
    analyzer.assert_not_awaited()
    assert evidence.record_interpretation.call_args.args[3]["learnings"] == ["A source claim"]
    persisted = json.loads(results.update_analysis.call_args.args[1])
    assert persisted["raw_analysis"] == raw
    assert output[0]["result"]["followups"] == ["Check the evidence"]


@pytest.mark.asyncio
async def test_v134_combined_digest_accepts_structured_items_before_completing_groups(monkeypatch):
    state = {"plan": {"search_queries": ["query"]}}
    repo = MagicMock()
    orch = SimpleNamespace(
        _get_state=lambda _: state,
        _create_or_update_step=lambda *args, **kwargs: "digest-step",
        step_repo=repo,
        step_result_repo=None,
        task_repo=None,
    )
    monkeypatch.setattr(
        digest,
        "parallel_digest_grouped",
        AsyncMock(return_value=[{"query_group": 1, "source_title": "Source", "result": structured_analysis()}]),
    )
    output = await digest.DigestStep().execute(
        orch,
        StepEnvelope(
            task_id="task",
            objective="objective",
            current_depth=2,
            max_depth=4,
            budget=1,
            payload=DigestPayload(parsed_sources_cache=[{"url": "https://example.org/source"}]),
        ),
    )
    assert output.status == "completed"
    assert output.new_findings == ["[Source]: A source claim"]
    assert output.payload.learnings == ["A source claim"]
    assert output.payload.gaps == ["Missing evidence"]
    assert output.payload.followups == ["Check the evidence"]
    assert repo.update.call_args.kwargs["status"] == "completed"
