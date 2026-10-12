import json

import pytest
from pydantic import ValidationError

from benchmarks.suites.belief_adjudication import (
    Adjudication,
    review_prompt,
    run,
    validate_adjudication,
)
from benchmarks.tests.test_belief_challenge import packet


def answer(case, relation="distinct"):
    return {
        "relation": relation,
        "contribution": "artistic_question",
        "empirical_status": "not_empirical_claim",
        "confidence": 0.7,
        "rationale": "The candidate frames an inquiry without asserting an observed result.",
        "uncertainty": "The supplied scenario provides no outcome data.",
        "citations": [
            {
                "field_path": "candidate.statement",
                "quote": case["candidate"]["statement"],
            },
            {
                "field_path": "candidate.consequence",
                "quote": case["candidate"]["consequence"],
            },
        ],
    }


def test_review_prompt_excludes_author_intent_and_evaluator_labels():
    case = packet()["cases"][8]
    payload = json.loads(review_prompt(case)[1]["content"])
    serialized = json.dumps(payload)
    assert "author_intent" not in serialized
    assert "factual_grounding" not in serialized
    assert "jev" not in serialized.lower()
    assert "candidate.consequence" in review_prompt(case)[0]["content"]


def test_v1_citation_binds_each_quote_to_its_named_source_field():
    case = packet()["cases"][8]
    assert validate_adjudication(case, json.dumps(answer(case)))["relation"] == "distinct"
    invalid = answer(case)
    invalid["citations"][1]["quote"] = case["comparison"]["consequence"]
    with pytest.raises(ValueError, match="Unbound"):
        validate_adjudication(case, json.dumps(invalid))
    with pytest.raises(ValidationError):
        Adjudication.model_validate({**answer(case), "adoption_authority": "approve"})


class Provider:
    def __init__(self, model, relation):
        self.model = model
        self.relation = relation
        self.calls = []

    async def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        payload = json.loads(messages[1]["content"])
        case = {
            "candidate": payload["candidate"],
            "comparison": payload["comparison"],
        }
        return {
            "model": self.model,
            "provider_used": "fixture",
            "content": json.dumps(answer(case, self.relation)),
            "finish_reason": "stop",
            "truncated": False,
        }


@pytest.mark.asyncio
async def test_v2_two_family_reviews_freeze_disagreement_without_authority(tmp_path):
    data = packet()
    cases = data["cases"][:2]
    data["cases"] = cases
    qwen = Provider("qwen/qwen3.8-flash", "contradiction")
    deepseek = Provider("deepseek/deepseek-v4-flash-0731", "extension")
    result = await run(
        data,
        {qwen.model: qwen, deepseek.model: deepseek},
        tmp_path / "run",
        case_ids=tuple(case["id"] for case in cases),
        workers=2,
    )
    assert result["coverage"] == {"disagreement": 2}
    assert result["promotion"] == "BLOCKED" and result["adoption_authority"] == "none"
    assert len(qwen.calls) == len(deepseek.calls) == 2
    first_prompt = json.dumps(qwen.calls[0][0])
    assert "author_intent" not in first_prompt and "comparison.consequence" in first_prompt
    assert (tmp_path / "run" / "references.json").exists()


@pytest.mark.asyncio
async def test_v2_reviewer_families_must_be_distinct(tmp_path):
    same_family = {
        "qwen/qwen3.8-flash": Provider("qwen/qwen3.8-flash", "distinct"),
        "qwen/qwen3.6-plus": Provider("qwen/qwen3.6-plus", "distinct"),
    }
    with pytest.raises(ValueError, match="distinct reviewer model families"):
        await run(packet(), same_family, tmp_path / "invalid", case_ids=("09",))
