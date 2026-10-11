import copy
from dataclasses import asdict, replace

import pytest

from benchmarks.suites.belief_auto_review import freeze_provisional, run
from benchmarks.suites.belief_v2_evaluation import audit, freeze_contract, replay, stress_fixture, structural_acceptance
from benchmarks.suites.calibration_contract import digest
from benchmarks.tests.test_belief_auto_review import providers
from benchmarks.tests.test_belief_review_corpus import packet


@pytest.mark.asyncio
async def test_v22_provisional_agreement_never_supplies_accuracy_or_acceptance(tmp_path):
    source = packet()
    frozen = freeze_provisional(source, await run(source, providers(), tmp_path))
    contract = freeze_contract(source, replay_source="synthetic_regression")
    result = audit(source, frozen, contract)
    assert result["accuracy"] is None and result["redundant_review_burden"] is None
    assert result["semantic_acceptance"] == "UNRESOLVED"
    assert result["promotion"] == "BLOCKED" and result["adoption_authority"] == "none"
    assert sum(p["retained_cases"] for p in result["partitions"].values()) == 6
    assert sum(p["valid_review_outputs"] for p in result["partitions"].values()) == 12
    # This fixture has no comparison records: absence differs from unavailable pair context.
    assert sum(p["effective_relations"].get("no_comparison", 0) for p in result["partitions"].values()) == 12
    changed = copy.deepcopy(frozen)
    changed["independent_gold"] = True
    with pytest.raises(ValueError):
        audit(source, changed, contract)


@pytest.mark.asyncio
async def test_v22_contract_and_frozen_bindings_reject_tamper(tmp_path):
    source = packet()
    frozen = freeze_provisional(source, await run(source, providers(), tmp_path))
    contract = freeze_contract(source, replay_source="synthetic_regression")
    changed = copy.deepcopy(contract)
    changed["recommended_production_slots"] = 2
    bound = dict(changed)
    bound.pop("contract_sha256")
    changed["contract_sha256"] = digest(bound)
    with pytest.raises(ValueError, match="budgets"):
        audit(source, frozen, changed)
    frozen["cases"][0]["review_outcome"] = "model_agreement"
    frozen["cases"][0]["context_incomplete"] = False
    with pytest.raises(ValueError, match="artifact"):
        audit(source, frozen, contract)


def test_v22_family_leakage_rejected_before_contract_freeze():
    source = packet()
    source["cases"][1]["split_entities"] = source["cases"][0]["split_entities"]
    source["cases"][1]["split"] = "validation" if source["cases"][0]["split"] != "validation" else "heldout"
    with pytest.raises(ValueError, match="leakage"):
        freeze_contract(source, replay_source="synthetic_regression")


def test_v22_source_binding_checked_before_contract_freeze():
    source = packet()
    source["cases"][0]["a"]["statement"] = "Changed source"
    with pytest.raises(ValueError):
        freeze_contract(source, replay_source="synthetic_regression")


def test_v9_v14_v15_matched_replay_preserves_standing_dissent_and_records():
    snapshot, signatures = stress_fixture()
    before = asdict(snapshot)
    result = replay(snapshot, signatures, source_kind="synthetic_regression")
    assert asdict(snapshot) == before
    assert [a["insertion_count"] for a in result["arms"]] == [0, 2, 4]
    assert [a["unique_selected"] for a in result["arms"]] == [0, 1, 2]
    assert result["arms"][2]["dormant_selected"] == 1
    assert result["arms"][2]["dissent_selected"] == 1
    assert len(result["arms"][2]["unselected_record_ids"]) == 10
    for arm in result["arms"]:
        for row in arm["rows"]:
            for receipt in row["receipts"]:
                assert receipt["standing"] == "provisional_candidate"
                assert receipt["scope"] == "synthetic replay"
                assert receipt["tool_authority"] == "none"
                assert receipt["independent_warrant_delta"] == 0
    assert result["promotion"] == "BLOCKED"


def test_v19_replay_validates_bounds_geometry_identity_and_provenance():
    snapshot, signatures = stress_fixture()
    for invalid in ([], [[0.0]], [[float("nan")] * 16], signatures * 51):
        with pytest.raises(ValueError):
            replay(snapshot, invalid, source_kind="synthetic_regression")
    with pytest.raises(ValueError, match="provenance"):
        replay(snapshot, signatures, source_kind="production_accuracy")
    with pytest.raises(ValueError, match="Duplicate"):
        replay(
            replace(snapshot, records=(snapshot.records[0], snapshot.records[0])),
            signatures,
            source_kind="synthetic_regression",
        )
    result = replay(replace(snapshot, truncated=True), signatures, source_kind="recorded_snapshot")
    assert result["scan_truncated"]
    assert all(r["scan_truncated"] for a in result["arms"] for row in a["rows"] for r in row["receipts"])


def test_v22_structural_pass_cannot_close_semantic_acceptance():
    contract = freeze_contract(packet(), replay_source="synthetic_regression")
    snapshot, signatures = stress_fixture()
    result = {"participation_replay": replay(snapshot, signatures, source_kind="synthetic_regression")}
    acceptance = structural_acceptance(contract, result)
    assert acceptance["engineering"] == "PASS"
    assert acceptance["overall"] == "INCOMPLETE" and acceptance["promotion"] == "BLOCKED"
    result["participation_replay"]["arms"][2]["warrant_changes"] = 1
    acceptance = structural_acceptance(contract, result)
    assert acceptance["engineering"] == "FAIL"
    assert acceptance["failures"] == ["slots_2:warrant_changes"]
