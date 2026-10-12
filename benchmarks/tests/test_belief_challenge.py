"""Frozen references are source-bound opinions, never classifier gold."""

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from benchmarks.suites.belief_challenge import REVIEWERS, freeze, reference_prompt, run, supplement, validate_reference
from benchmarks.suites.belief_conversation_replay import checkpoint_call
from benchmarks.suites.belief_intake_replay import setup


def packet():
    return json.loads(Path("benchmarks/data/belief-challenge-v1.json").read_text(encoding="utf-8"))


def reference(case):
    return {
        "relation": "equivalent",
        "contribution": "repetition",
        "factual_grounding": "unclear",
        "confidence": 0.9,
        "rationale": "Fixture-only comparison.",
        "uncertainty": "Not semantic gold.",
        "citations": [{"source": "candidate", "quote": case["candidate"]["statement"]}],
    }


def test_v22_v26_families_disjoint_and_reference_blind():
    data = packet()
    contract = freeze(data)
    assert contract["accuracy"] is None and contract["threshold"] == 0.85
    prompt = json.loads(reference_prompt(data["cases"][0])[1]["content"])
    assert set(prompt) == {"candidate", "comparison"}
    assert "label" not in prompt["candidate"] and "author_intent" not in prompt
    bad = copy.deepcopy(data)
    bad["cases"][1]["partition"] = "heldout"
    with pytest.raises(ValueError, match="crosses partitions"):
        freeze(bad)


def test_v26_quote_binding_rejects_changed_reference():
    case = packet()["cases"][0]
    value = reference(case)
    assert validate_reference(case, json.dumps(value))["relation"] == "equivalent"
    value["citations"][0]["quote"] = "Changed source phrase."
    with pytest.raises(ValueError, match="Unbound"):
        validate_reference(case, json.dumps(value))


def test_v19_migration_setup_cannot_resolve_live_scorer(tmp_path):
    with patch("backend.modules.structural_engine.CompositeStructuralScorer") as ambient:
        setup(tmp_path / "isolated.sqlite")
        ambient.assert_not_called()


def test_v26_numeric_uncertainty_projection_preserves_raw_value():
    case = packet()["cases"][0]
    value = reference(case)
    value["uncertainty"] = 0.05
    with pytest.raises(ValueError):
        validate_reference(case, json.dumps(value))
    projected = validate_reference(case, json.dumps(value), schema_revision=2)
    assert projected["uncertainty"] == 0.05
    assert projected["relation"] == value["relation"]
    fenced = "```json\n" + json.dumps(value) + "\n```"
    with pytest.raises(ValueError):
        validate_reference(case, fenced, schema_revision=2)
    assert validate_reference(case, fenced, schema_revision=3) == projected
    with pytest.raises(ValueError):
        validate_reference(case, "Extra claim\n" + fenced, schema_revision=3)


class Provider:
    def __init__(self, model):
        self.model = model.removeprefix("nvidia_router/")
        self.calls = 0
        self.arguments = []

    async def generate(self, messages, **kwargs):
        self.calls += 1
        self.arguments.append(kwargs)
        payload = json.loads(messages[1]["content"])
        value = reference({"candidate": payload["candidate"]})
        return {"model": self.model, "content": json.dumps(value), "finish_reason": "stop"}


class Jev:
    model = "typesafe/fixture"
    is_configured = True

    async def evaluate(self, state, questions):
        choices = {
            "consequence": "local",
            "factual_grounding": "unclear",
            "artistic_grounding": "supported",
            "tension": "present",
        }
        return {
            "success": True,
            "model": self.model,
            "answers": {key: {"choice": choices.get(key, "equivalent"), "confidence": 0.95} for key in questions},
        }


@pytest.mark.asyncio
async def test_v26_json_checkpoint_retains_custom_schema_without_replay(tmp_path):
    case = packet()["cases"][0]
    provider = Provider(REVIEWERS[0])
    path = tmp_path / "response.json"
    identity = {"case_id": "01", "model_requested": REVIEWERS[0]}
    row = await checkpoint_call(provider, reference_prompt(case), path, identity, response_json=True)
    again = await checkpoint_call(provider, reference_prompt(case), path, identity, response_json=True)
    assert row == again and provider.calls == 1
    assert provider.arguments[0]["response_format"] == {"type": "json_object"}
    assert validate_reference(case, row["raw_output"])


@pytest.mark.asyncio
async def test_v4_v22_actual_repeat_route_and_nongold_summary(tmp_path):
    data = packet()
    data["cases"] = data["cases"][:2]
    providers = {m: Provider(m) for m in REVIEWERS}
    result = await run(data, providers, Jev(), tmp_path / "challenge")
    assert result["adoption_decisions"] == 0 and result["accuracy"] is None
    assert result["cases"][0]["disposition"] == "repetition"
    assert all(c["dual_reference_consensus"] == "equivalent" for c in result["cases"])
    with pytest.raises(FileExistsError):
        await run(data, providers, Jev(), tmp_path / "challenge")
    before = sum(p.calls for p in providers.values())
    reused = await supplement(data, providers, Jev(), tmp_path / "challenge", tmp_path / "supplement")
    assert reused["reference_status"]["complete"] == 4
    assert sum(p.calls for p in providers.values()) == before
    (tmp_path / "challenge/reference-01-google.json").unlink()
    with pytest.raises(ValueError, match="Missing attempted reference"):
        await supplement(data, providers, Jev(), tmp_path / "challenge", tmp_path / "unsafe-supplement")
