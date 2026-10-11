"""Real isolated intake checks; deterministic classifier is not semantic gold."""

import json

import pytest

from benchmarks.suites.belief_intake_replay import contrasts, run


class Client:
    model = "fixture-only"
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
async def test_v2_v4_v13_scoped_repeat_receipts_traces_without_adoption(tmp_path):
    rows = await run(tmp_path / "replay", contrasts(), Client())
    assert rows[1]["receipt"]["proposal_id"] == rows[0]["receipt"]["proposal_id"]
    assert rows[1]["counts"]["belief_proposals"] == rows[0]["counts"]["belief_proposals"]
    assert all(row["counts"]["belief_review_decisions"] == 0 for row in rows)
    assert rows[-1]["provider_calls"] == 0
    assert rows[-1]["receipt"]["evaluation"]["status"] == "abstained"
    traces = json.loads((tmp_path / "replay/authored_contrast_nongold-traces.json").read_text())
    assert traces and any("Admission receipt:" in trace["snippet"] for trace in traces)


@pytest.mark.asyncio
async def test_v3_v14_missing_scope_recurrence_visible_and_history_inert(tmp_path):
    data = {"statement": "Refusal prevents habitual routing.", "label": "refusal"}
    cases = [
        {
            "id": str(i),
            "origin": "recorded_generated_nomination",
            "parent": "Refuse routing.",
            "data": data,
            "raw": '<belief_nucleate label="refusal">Refusal prevents habitual routing.</belief_nucleate>',
        }
        for i in range(2)
    ]
    rows = await run(tmp_path / "replay", cases, Client())
    assert all(r["provider_calls"] == 0 and r["history_inert"] for r in rows)
    assert all(r["receipt"]["evaluation"]["status"] == "abstained" for r in rows)
    assert rows[1]["counts"]["belief_encounters"] == 2
    assert all(r["counts"]["belief_review_decisions"] == 0 for r in rows)
