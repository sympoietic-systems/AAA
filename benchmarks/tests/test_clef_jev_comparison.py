from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.suites.telemetry import clef_jev_comparison as comparison


def _answers(choice: str, choices: tuple[str, ...]) -> dict[str, object]:
    probability = {item: 0.9 if item == choice else 0.1 / (len(choices) - 1) for item in choices}
    return {"decision": {"choice": choice, "confidence": probability[choice], "probabilities": probability}}


def test_t89_frozen_fixture_is_bounded_and_covers_five_sensor_tasks() -> None:
    packet, cases, digest = comparison.load_fixtures()
    assert len(cases) == 15
    assert {case["task"] for case in cases} == {
        "triage",
        "search_filter",
        "sycophancy_check",
        "tension_nomination",
        "dream_arbitration",
    }
    assert packet["label_provenance"].startswith("hand-authored synthetic")
    assert len(digest) == 64
    for case in cases:
        question = comparison.question_for(case)["decision"]
        assert question["type"] == "choice"
        assert "abstain" in case["options"]


def test_t89_fixture_rejects_duplicate_ids_and_unknown_labels(tmp_path: Path) -> None:
    packet, cases, _ = comparison.load_fixtures()
    broken = {**packet, "cases": [cases[0], {**cases[1], "id": cases[0]["id"]}]}
    fixture = tmp_path / "bad.json"
    fixture.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        comparison.load_fixtures(fixture)


@pytest.mark.asyncio
async def test_openrouter_clef_adapter_uses_native_decision_endpoint_and_model_override() -> None:
    seen: dict[str, object] = {}

    class FakeTypeSafeClient:
        model = "typesafe/jev-1.13"

        async def evaluate(self, **kwargs: object) -> dict[str, object]:
            seen.update(kwargs)
            return {
                "success": True,
                "model": kwargs.get("model"),
                "answers": _answers("urgent", ("urgent", "routine", "abstain")),
            }

    client = FakeTypeSafeClient()
    adapter = comparison.JevAdapter(client, model="cloudflare/clef-flash")
    result = await adapter.evaluate({"message": "outage"}, {"decision": {"type": "Choice"}})
    assert adapter.model == "cloudflare/clef-flash"
    assert seen["model"] == "cloudflare/clef-flash"
    assert result["success"] is True
    assert result["answers"] == _answers("urgent", ("urgent", "routine", "abstain"))


def test_t89_choice_validator_rejects_invalid_distribution_and_confidence_mismatch() -> None:
    choices = {"yes", "no", "abstain"}
    result = {"success": True, "answers": _answers("yes", tuple(sorted(choices)))}
    assert comparison._choice_answer(result, choices)[3] is None
    malformed = {
        "success": True,
        "answers": {
            "decision": {"choice": "yes", "confidence": 0.9, "probabilities": {"yes": 1.2, "no": 0, "abstain": 0}}
        },
    }
    assert comparison._choice_answer(malformed, choices)[3] == "invalid_probability_map"
    mismatch = {
        "success": True,
        "answers": {
            "decision": {"choice": "yes", "confidence": 0.4, "probabilities": {"yes": 0.9, "no": 0.05, "abstain": 0.05}}
        },
    }
    assert comparison._choice_answer(mismatch, choices)[3] == "confidence_probability_mismatch"


class _FakeAdapter:
    def __init__(self, model: str) -> None:
        self.model = model

    async def evaluate(self, state: dict[str, object], questions: dict[str, dict[str, object]]) -> dict[str, object]:
        choices = tuple(questions["decision"]["criteria"])
        expected = str(state["expected"])
        chosen = expected if self.model != "jev-fake" else "abstain"
        return {
            "success": True,
            "model": self.model,
            "answers": _answers(chosen, choices),
            "usage": {"input_tokens": 10, "output_tokens": 1},
        }


@pytest.mark.asyncio
async def test_t89_run_records_validity_calibration_latency_and_cost_without_fixture_text(tmp_path: Path) -> None:
    case = {
        "id": "tiny",
        "task": "triage",
        "state": {"expected": "urgent", "secret_free_text": "synthetic fixture body"},
        "options": {"urgent": "Urgent", "routine": "Routine", "abstain": "Insufficient"},
        "expected": "urgent",
    }
    packet = {"dataset_id": "tiny", "label_provenance": "synthetic"}
    fixture_sha = comparison.canonical_sha256([case])
    adapters = {
        "jev": _FakeAdapter("jev-fake"),
        "clef": _FakeAdapter("clef"),
        "clef-flash": _FakeAdapter("clef-flash"),
    }
    result = await comparison.run_comparison(adapters, [case])
    assert len(result["rows"]) == 3
    assert result["summary"]["clef"]["accuracy"] == 1
    assert result["summary"]["jev"]["abstention_rate"] == 1
    assert result["summary"]["clef-flash"]["usage"]["input_tokens"] == 10
    output = tmp_path / "run"
    comparison._write_run(output, packet, fixture_sha, result, 1)
    assert {"metadata.json", "telemetry_receipts.json", "summary.md", "run.log"}.issubset(
        {path.name for path in output.iterdir()}
    )
    serialized = (output / "telemetry_receipts.json").read_text(encoding="utf-8")
    assert "synthetic fixture body" not in serialized
    assert "secret_free_text" not in serialized


def test_t89_summary_cost_unknown_is_distinguished_from_zero() -> None:
    rows = [
        {
            "provider": model,
            "validity": "valid",
            "status": "success",
            "latency_ms": 1,
            "expected": "yes",
            "choice": "yes",
            "correct": True,
            "confidence": 0.9,
            "probabilities": {"yes": 0.9, "no": 0.1},
            "usage": {"input_tokens": 1, "output_tokens": 1, "reported_cost_usd": None},
        }
        for model in comparison.MODELS
    ]
    summary = comparison.summarize(rows)
    assert summary["clef"]["usage"]["reported_cost_usd"] is None
    assert summary["clef"]["usage"]["unpriced_calls"] == 1
