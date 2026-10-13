"""Human anchor preparation preserves the blind review boundary."""

import json

import pytest

from benchmarks.suites.belief_human_anchor import HELD_OUT_IDS, prepare


def _case(case_id: str) -> dict:
    statement = f"Candidate statement {case_id}"
    comparison = f"Comparison statement {case_id}"
    return {
        "id": case_id,
        "family": f"private-family-{case_id}",
        "partition": "heldout",
        "author_intent": f"private-intent-{case_id}",
        "candidate": {
            "statement": statement,
            "scope": "bounded hypothetical",
            "temporal_scope": "during scenario",
            "consequence": "inspect a distinction",
            "evidence_quote": statement,
            "source_text": f"Source: {statement}",
            "label": "candidate",
            "trigger": "insight",
            "rationale": "Private candidate rationale.",
        },
        "comparison": {
            "statement": comparison,
            "scope": "bounded hypothetical",
            "temporal_scope": "during scenario",
            "consequence": "existing premise",
            "evidence_quote": comparison,
            "source_text": f"Source: {comparison}",
            "label": "comparison",
            "trigger": "insight",
            "rationale": "Private comparison rationale.",
        },
    }


def test_human_anchor_blinds_metadata_and_builds_all_heldout_cases(tmp_path):
    source = tmp_path / "challenge.json"
    source.write_text(
        json.dumps({"cases": [_case(f"{i:02d}") for i in range(9, 17)]}),
        encoding="utf-8",
    )
    output = tmp_path / "anchor"

    receipt = prepare(source, output)

    page = (output / "review.html").read_text(encoding="utf-8")
    case_map = json.loads((output / "case-map.json").read_text(encoding="utf-8"))
    plan = json.loads((output / "evaluation-plan.json").read_text(encoding="utf-8"))
    assert receipt["selected_source_cases"] == sorted(HELD_OUT_IDS)
    assert len(case_map) == 8 and set(case_map) == {f"H{i:02d}" for i in range(1, 9)}
    assert "private-family" not in page
    assert "private-intent" not in page
    assert "Private candidate rationale" not in page
    assert "Private comparison rationale" not in page
    assert "insufficient_context" in page and "worthwhile_question" in page
    assert plan["frozen_before_human_annotations"] is True
    assert plan["semantic_targets"] is None
    assert plan["promotion"].startswith("blocked_")


def test_human_anchor_requires_frozen_heldout_id_set(tmp_path):
    source = tmp_path / "challenge.json"
    source.write_text(json.dumps({"cases": [_case("01")]}), encoding="utf-8")

    with pytest.raises(ValueError, match="held-out cases 09 through 16"):
        prepare(source, tmp_path / "anchor")


def test_human_anchor_refuses_overwrite(tmp_path):
    source = tmp_path / "challenge.json"
    source.write_text(
        json.dumps({"cases": [_case(f"{i:02d}") for i in range(9, 17)]}),
        encoding="utf-8",
    )
    output = tmp_path / "anchor"
    output.mkdir()
    (output / "existing.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="must be new or empty"):
        prepare(source, output)
