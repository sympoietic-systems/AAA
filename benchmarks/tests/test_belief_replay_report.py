import json

import pytest

from benchmarks.suites.belief_conversation_replay import prepare, run, write_checkpoint
from benchmarks.suites.belief_replay_report import quoted_excerpt, render, summarize
from benchmarks.tests.test_belief_conversation_replay import Provider, capture


def test_v22_quotation_envelope_normalization_keeps_exact_source_requirement():
    outputs = {"scoped0": {"raw_output": "An exact observed phrase."}}
    mapping = {"A": "scoped0"}
    assert quoted_excerpt('A: "exact observed phrase"', mapping, outputs)
    assert quoted_excerpt("A: 'exact observed phrase'", mapping, outputs)
    assert not quoted_excerpt("A: 'exact ... phrase'", mapping, outputs)
    assert not quoted_excerpt("B: exact observed phrase", mapping, outputs)
    assert not quoted_excerpt('A: ""', mapping, outputs)


@pytest.mark.asyncio
async def test_v22_derived_validation_preserves_original_failed_receipts(tmp_path):
    class Quoted(Provider):
        async def generate(self, messages, **params):
            response = await super().generate(messages, **params)
            value = json.loads(response["content"])
            value["citations"] = [c.split(": ")[0] + ': "' + c.split(": ")[1] + '"' for c in value["citations"]]
            response["content"] = json.dumps(value)
            return response

    packet = prepare(capture())
    generator = Provider("google/gemini-3.8-flash")
    reviewers = {model: Quoted(model) for model in ("google/gemini-3.8-flash", "nvidia/nemotron-3-super-120b-a12b")}
    await run(packet, generator, reviewers, tmp_path, generator.model)
    for position in (0, 1):
        path = tmp_path / f"judgment-4-{position}.json"
        row = json.loads(path.read_text(encoding="utf-8"))
        row.update(status="failed", error_type="UnboundJudgmentCitationOrWinner")
        write_checkpoint(path, row)
    before = (tmp_path / "judgment-4-0.json").read_bytes()
    result = summarize(packet, tmp_path)
    assert result["raw_judgment_status"] == {"failed": 2}
    assert result["validated_judgments"] == 2
    assert result["independent_gold"] is False and result["accuracy"] is None
    assert (tmp_path / "judgment-4-0.json").read_bytes() == before
    page = render(result)
    assert "default-src 'none'" in page and "Provisional model judgments" in page
    assert generator.calls == 4
