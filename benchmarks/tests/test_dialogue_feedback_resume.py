from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

from benchmarks.suites.telemetry import run_dialogue_feedback_benchmark as benchmark


def _fake_arm_receipt(*, policy: str, repetition: int, scenario_id: str, turn_count: int) -> dict[str, Any]:
    return {
        "policy": policy,
        "repetition": repetition,
        "scenario_id": scenario_id,
        "turn_count": turn_count,
        "turns": [],
        "participant_validity": {"passed": False, "expected_completions": max(0, turn_count - 1)},
    }


def _configure_offline_main(monkeypatch: pytest.MonkeyPatch, attempts: list[tuple[str, int, str]]) -> None:
    monkeypatch.setattr(benchmark, "load_dotenv", lambda _path: None)
    monkeypatch.setattr(benchmark, "resolve_simulator_api_key", lambda: "test-key")
    monkeypatch.setattr(benchmark, "resolve_simulator_api_base", lambda: "https://example.test/v1")
    monkeypatch.setattr(benchmark, "resolve_simulator_model", lambda: "test/participant")
    monkeypatch.setattr(benchmark, "_production_database_paths", lambda: ())

    def run_arm(
        *,
        policy: str,
        repetition: int,
        turn_count: int,
        simulator_model: str,
        api_base: str,
        isolation_root: Path,
        scenario_id: str = "cache_wipe_429",
    ) -> dict[str, Any]:
        del simulator_model, api_base, isolation_root
        attempts.append((scenario_id, repetition, policy))
        return _fake_arm_receipt(policy=policy, repetition=repetition, scenario_id=scenario_id, turn_count=turn_count)

    monkeypatch.setattr(benchmark, "_run_isolated_arm", run_arm)


def test_resume_skips_completed_arms_and_finishes_original_plan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "interrupted-run"
    attempts: list[tuple[str, int, str]] = []
    _configure_offline_main(monkeypatch, attempts)
    original_run_arm = benchmark._run_isolated_arm
    fail_once = True

    def interrupt_after_first_arm(**kwargs: Any) -> dict[str, Any]:
        nonlocal fail_once
        if len(attempts) == 1 and fail_once:
            fail_once = False
            attempts.append((kwargs["scenario_id"], kwargs["repetition"], kwargs["policy"]))
            raise RuntimeError("simulated interruption")
        return original_run_arm(**kwargs)

    monkeypatch.setattr(benchmark, "_run_isolated_arm", interrupt_after_first_arm)
    monkeypatch.setattr(
        sys,
        "argv",
        ["benchmark", "--out", str(output), "--scenario", "cache_wipe_429", "--repetitions", "2", "--turns", "3"],
    )
    with pytest.raises(RuntimeError, match="simulated interruption"):
        benchmark.main()

    partial_metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    partial_receipts = json.loads((output / "telemetry_receipts.json").read_text(encoding="utf-8"))
    assert partial_metadata["status"] == "running"
    assert len(partial_receipts) == 1
    completed_key = benchmark._receipt_key(partial_receipts[0])
    assert partial_metadata["completed_arms"] == [
        {"scenario_id": completed_key[0], "repetition": completed_key[1], "policy": completed_key[2]}
    ]

    calls_before_resume = len(attempts)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark",
            "--out",
            str(output),
            "--scenario",
            "cache_wipe_429",
            "--repetitions",
            "2",
            "--turns",
            "3",
            "--resume",
        ],
    )
    benchmark.main()

    final_receipts = json.loads((output / "telemetry_receipts.json").read_text(encoding="utf-8"))
    final_metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    final_keys = [benchmark._receipt_key(receipt) for receipt in final_receipts]
    expected_keys = [
        (str(item["scenario_id"]), int(item["repetition"]), str(item["policy"])) for item in final_metadata["arm_order"]
    ]
    assert len(final_receipts) == 4
    assert len(set(final_keys)) == 4
    assert set(final_keys) == set(expected_keys)
    assert sum(attempt == completed_key for attempt in attempts) == 1
    assert len(attempts) == calls_before_resume + 3
    assert final_metadata["status"] == "complete"
    assert final_metadata["completed_arms"] == [
        {"scenario_id": scenario, "repetition": repetition, "policy": policy}
        for scenario, repetition, policy in sorted(set(expected_keys))
    ]
    assert not list(output.glob("*.tmp"))


def test_resume_rejects_changed_run_parameters(tmp_path: Path) -> None:
    output = tmp_path / "interrupted-run"
    output.mkdir()
    contract = benchmark._resume_contract(
        scenario_ids=["cache_wipe_429"],
        repetitions=2,
        turns=3,
        candidate_policy="paskian",
        apparatus_model="nvidia_router/nvidia/nemotron-3-super-120b-a12b",
        simulator_model="nvidia/nemotron-3-super-120b-a12b",
        api_base="https://integrate.api.nvidia.com/v1",
    )
    (output / "metadata.json").write_text(json.dumps({"resume_contract": contract}), encoding="utf-8")
    (output / "telemetry_receipts.json").write_text("[]\n", encoding="utf-8")

    changed_contract = dict(contract, turns_per_conversation=4)
    with pytest.raises(ValueError, match="do not match"):
        benchmark._load_resume_receipts(output, changed_contract)


def test_arm_plan_is_reproducible_and_counterbalanced() -> None:
    first = benchmark._planned_arms(["scenario-a", "scenario-b"], 10, "paskian")
    second = benchmark._planned_arms(["scenario-a", "scenario-b"], 10, "paskian")

    assert first == second
    assert len(first) == 40
    for scenario_id in ("scenario-a", "scenario-b"):
        for repetition in range(1, 11):
            pair = [
                item["policy"]
                for item in first
                if item["scenario_id"] == scenario_id and item["repetition"] == repetition
            ]
            assert sorted(pair) == ["legacy", "paskian"]
    assert len({tuple(item.items()) for item in first}) == len(first)
