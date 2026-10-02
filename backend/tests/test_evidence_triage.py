from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.modules.retrieval.web_retrieval import RhizomeWebProbe
from backend.modules.sensory.evidence_triage import EvidenceTriage, probability
from backend.services.research.envelope_mapper import ResearchEnvelopeMapper
from backend.services.research.task_state import SearchPayload, StepOutput, TaskStateManager, make_initial_state


def client(answers):
    return SimpleNamespace(
        model="fixture", is_configured=True, evaluate=AsyncMock(return_value={"success": True, "answers": answers})
    )


@pytest.mark.asyncio
async def test_screen_ranks_without_hidden_exclusions_and_replays():
    evaluator = client({"0": {"score": 0.1, "confidence": 0.95}, "1": {"score": 0.9, "confidence": 0.95}})
    triage = EvidenceTriage(evaluator)
    sources = [{"url": "https://ad.test"}, {"url": "https://primary.test"}]
    selected, receipt = await triage.screen("evidence", "evidence", sources, 1)
    assert selected == [sources[1]]
    assert selected[0] is not sources[1]
    assert receipt["candidates"] == [
        {"id": "0", "url": "https://ad.test", "selected": False},
        {"id": "1", "url": "https://primary.test", "selected": True},
    ]
    assert (await triage.screen("evidence", "evidence", sources, 1))[1]["input_sha256"] == receipt["input_sha256"]
    assert sources == [{"url": "https://ad.test"}, {"url": "https://primary.test"}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "answer",
    [
        {"score": 0.9, "confidence": 0.1},
        {"score": float("nan"), "confidence": 0.9},
        {"score": True, "confidence": 0.9},
        {},
    ],
)
async def test_invalid_evidence_abstains_and_preserves_top_result(answer):
    triage = EvidenceTriage(client({"0": answer}))
    selected, receipt = await triage.screen("a", "b", [{"url": "https://fallback.test"}], 1)
    assert len(selected) == 1
    assert receipt["status"] == "abstain" and receipt["fallback"]


@pytest.mark.asyncio
async def test_unavailable_timeout_and_bounded_questions():
    evaluator = client({})
    evaluator.evaluate.side_effect = TimeoutError()
    triage = EvidenceTriage(evaluator)
    selected, receipt = await triage.screen("a", "b", [{"url": str(i)} for i in range(15)], 20)
    assert len(selected) == 10 and receipt["unscreened_count"] == 5
    assert len(evaluator.evaluate.call_args.args[1]) == 10
    assert receipt["status"] == "unavailable" and receipt["reason"] == "TimeoutError"
    evaluator.is_configured = False
    assert (await triage.screen("a", "b", [{"url": "u"}], 1))[1]["reason"] == "unconfigured"


@pytest.mark.asyncio
async def test_collision_only_supplied_ids_and_no_vector_authorship():
    evaluator = client(
        {"belief": {"choice": "invented", "confidence": 0.99}, "interference": {"score": 0.9, "confidence": 0.99}}
    )
    triage = EvidenceTriage(evaluator)
    beliefs = [{"id": "known", "statement": "A"}]
    receipt = await triage.collision("B", beliefs)
    assert receipt["status"] == "abstain" and receipt["implicated_nodes"] == []
    evaluator.evaluate.return_value["answers"]["belief"]["choice"] = "known"
    receipt = await triage.collision("B", beliefs)
    assert receipt["status"] == "routed" and receipt["implicated_nodes"] == ["known"]
    assert "state_vector_impact" not in receipt
    assert (await triage.collision("B", []))["reason"] == "no_beliefs"


def test_receipt_roundtrip_and_config_gate():
    state = {}
    payload = SearchPayload(triage_receipts=[{"status": "abstain"}])
    output = StepOutput(payload=payload)
    ResearchEnvelopeMapper.apply_step_output(state, "searching", output)
    assert state["triage_receipts"] == [{"status": "abstain"}]
    repo = MagicMock()
    manager = TaskStateManager(repo)
    manager._states["test"] = state
    manager._persist_state("test")
    saved = repo.update.call_args.kwargs["orchestrator_state"]
    restored = make_initial_state(
        {"objective": "test", "max_depth": 1, "budget_limit_usd": 1, "orchestrator_state": saved}
    )
    assert restored["triage_receipts"] == state["triage_receipts"]
    assert EvidenceTriage.from_config({}) is None
    for invalid in (True, -1, float("inf"), "0.8"):
        with pytest.raises(ValueError):
            probability(invalid)


@pytest.mark.asyncio
async def test_web_probe_persists_grounded_receipt_without_generative_call():
    evaluator = client(
        {
            "0": {"score": 0.9, "confidence": 0.99},
            "belief": {"choice": "known", "confidence": 0.99},
            "interference": {"score": 0.8, "confidence": 0.99},
        }
    )
    repo = MagicMock()
    embedder = SimpleNamespace(
        service=SimpleNamespace(encode_async=AsyncMock(return_value=[]), serialize=lambda _: b"", model_name="fixture")
    )
    scorer = SimpleNamespace(
        _scorer=SimpleNamespace(score_async=AsyncMock(return_value=SimpleNamespace(tobytes=lambda: b"")))
    )
    beliefs = MagicMock()
    beliefs.list_beliefs.return_value = [
        SimpleNamespace(id="known", statement="A", ontological_mass=1, lifecycle_stage="crystallized", confidence=0.9)
    ]
    llm = MagicMock()
    probe = RhizomeWebProbe(repo, embedder, scorer, llm, EvidenceTriage(evaluator), beliefs)
    probe.search = AsyncMock(return_value=[{"title": "A", "url": "https://example.test", "snippet": "B"}])
    probe.crawl = AsyncMock(return_value="External evidence")
    result = await probe.execute_probe("query", "conversation")
    assert result["implicated_nodes"] == ["known"]
    assert result["state_vector_impact"] == [0.0] * 16
    assert "Jev triage receipt" in repo.update_file.call_args.kwargs["summary"]
    llm.generate.assert_not_called()
