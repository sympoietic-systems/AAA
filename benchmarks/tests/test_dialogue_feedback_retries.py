from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import httpx
import pytest

from benchmarks.suites.telemetry import run_dialogue_feedback_benchmark as benchmark


def _response(status_code: int, *, content: str = "A measured answer.") -> httpx.Response:
    payload = (
        {
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 4},
            "model": "fixture/nemotron",
            "provider": "nvidia",
        }
        if status_code == 200
        else {"error": {"message": "fixture unavailable"}}
    )
    return httpx.Response(status_code, json=payload, request=httpx.Request("POST", "https://fixture.test"))


def test_nvidia_participant_rotates_fallback_key_and_cools_failed_key(monkeypatch: pytest.MonkeyPatch) -> None:
    benchmark._nvidia_simulator_key_cooldowns.clear()
    request_keys: list[str] = []

    def respond(*_args, **kwargs):
        request_keys.append(kwargs["headers"]["Authorization"])
        return _response(429 if len(request_keys) == 1 else 200)

    monkeypatch.setattr(benchmark.httpx, "post", respond)
    monkeypatch.setattr(benchmark.time, "sleep", lambda _seconds: None)

    completion = benchmark._simulated_participant(
        [],
        model="nvidia/nemotron-3-super-120b-a12b",
        api_key="fixture-primary,fixture-fallback",
        api_base="https://integrate.api.nvidia.com/v1",
    )

    assert completion.valid
    assert request_keys == ["Bearer fixture-primary", "Bearer fixture-fallback"]
    assert "fixture-primary" in benchmark._nvidia_simulator_key_cooldowns
    assert "fixture-fallback" not in benchmark._nvidia_simulator_key_cooldowns


def test_nvidia_participant_retries_connection_failures_across_both_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    benchmark._nvidia_simulator_key_cooldowns.clear()
    request_keys: list[str] = []
    delays: list[float] = []

    def connect_then_recover(*_args, **kwargs):
        request_keys.append(kwargs["headers"]["Authorization"])
        if len(request_keys) < 3:
            request = httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")
            raise httpx.ConnectError("simulated TLS EOF", request=request)
        return _response(200)

    monkeypatch.setattr(benchmark.httpx, "post", connect_then_recover)
    monkeypatch.setattr(benchmark.time, "sleep", delays.append)

    completion = benchmark._simulated_participant(
        [],
        model="nvidia/nemotron-3-super-120b-a12b",
        api_key="fixture-primary,fixture-fallback",
        api_base="https://integrate.api.nvidia.com/v1",
    )

    assert completion.valid
    assert request_keys == ["Bearer fixture-primary", "Bearer fixture-fallback", "Bearer fixture-primary"]
    assert delays == [10.0]


def test_nvidia_participant_stops_after_three_rounds_and_backs_off(monkeypatch: pytest.MonkeyPatch) -> None:
    benchmark._nvidia_simulator_key_cooldowns.clear()
    request_keys: list[str] = []
    delays: list[float] = []

    def unavailable(*_args, **kwargs):
        request_keys.append(kwargs["headers"]["Authorization"])
        return _response(429)

    monkeypatch.setattr(benchmark.httpx, "post", unavailable)
    monkeypatch.setattr(benchmark.time, "sleep", delays.append)

    with pytest.raises(httpx.HTTPStatusError):
        benchmark._simulated_participant(
            [],
            model="nvidia/nemotron-3-super-120b-a12b",
            api_key="fixture-primary,fixture-fallback",
            api_base="https://integrate.api.nvidia.com/v1",
        )

    assert request_keys == [
        "Bearer fixture-primary",
        "Bearer fixture-fallback",
        "Bearer fixture-primary",
        "Bearer fixture-fallback",
        "Bearer fixture-primary",
        "Bearer fixture-fallback",
    ]
    assert delays == [10.0, 20.0]
    assert set(benchmark._nvidia_simulator_key_cooldowns) == {"fixture-primary", "fixture-fallback"}


def test_non_nvidia_participant_keeps_existing_retry_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    delays: list[float] = []

    def overloaded_then_ok(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return _response(503 if calls < 3 else 200)

    monkeypatch.setattr(benchmark.httpx, "post", overloaded_then_ok)
    monkeypatch.setattr(benchmark.time, "sleep", delays.append)

    completion = benchmark._simulated_participant(
        [],
        model="fixture/openrouter-model",
        api_key="fixture-openrouter-key",
        api_base="https://openrouter.ai/api/v1",
    )

    assert completion.valid
    assert calls == 3
    assert delays == [3.0, 6.0]


def test_failed_isolated_arm_retries_after_backoff_and_clears_partial_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    arm_root = tmp_path / "isolated" / "r1_scenario_current"
    calls = 0
    delays: list[float] = []

    def fail_then_write_receipt(command: list[str], **_kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            (arm_root / "partial.db").write_text("failed worker state", encoding="utf-8")
            raise subprocess.CalledProcessError(1, command)
        assert not (arm_root / "partial.db").exists()
        output_path = Path(command[command.index("--worker-output") + 1])
        output_path.write_text(
            '{"policy":"current","repetition":1,"scenario_id":"scenario"}',
            encoding="utf-8",
        )

    monkeypatch.setattr(benchmark.subprocess, "run", fail_then_write_receipt)
    monkeypatch.setattr(benchmark.time, "sleep", delays.append)

    receipt = benchmark._run_isolated_arm(
        policy="current",
        repetition=1,
        turn_count=3,
        simulator_model="fixture/participant",
        api_base="https://fixture.test/v1",
        isolation_root=tmp_path / "isolated",
        scenario_id="scenario",
        causal_arm="current",
    )

    assert receipt["policy"] == "current"
    assert calls == 2
    assert delays == [10]
