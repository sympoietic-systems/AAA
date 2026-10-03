"""Repeated live ablation of legacy and progress-aware dialogue interventions."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import httpx
from dotenv import load_dotenv

from benchmarks.common.storage import PROJECT_ROOT
from benchmarks.suites.telemetry.intervention_evaluator import (
    bootstrap_mean_ci,
    build_causal_receipts,
)
from benchmarks.suites.telemetry.scenarios import SCENARIOS, get_scenario

INITIAL_PROMPT = SCENARIOS["cache_wipe_429"].initial_prompt
PARTICIPANT_SYSTEM = SCENARIOS["cache_wipe_429"].participant_system



@dataclass(frozen=True)
class ParticipantCompletion:
    """Auditable simulator completion used as the next participant turn."""

    content: str
    finish_reason: str | None
    native_finish_reason: str | None
    usage: dict[str, Any]
    model: str | None
    provider: str | None
    sentence_count: int
    word_count: int
    valid: bool
    exclusion_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_simulator_api_base(environment: dict[str, str] | None = None) -> str:
    """Resolve the configured OpenAI-compatible participant boundary."""

    source = environment if environment is not None else os.environ
    configured = source.get("AAA_BENCHMARK_PARTICIPANT_MODEL", source.get("AAA_LLM_MODEL", ""))
    if configured.split(",")[0].strip().startswith("nvidia_router/"):
        return source.get("AAA_NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1").rstrip("/")
    return source.get("AAA_LLM_API_BASE", "https://openrouter.ai/api/v1").rstrip("/")


def resolve_simulator_model(environment: dict[str, str] | None = None) -> str:
    """Translate AAA's provider-qualified alias into its provider wire model id."""

    source = environment if environment is not None else os.environ
    configured = (
        source.get(
            "AAA_BENCHMARK_PARTICIPANT_MODEL",
            source.get("AAA_LLM_MODEL", "google/gemini-3.8-flash"),
        )
        .split(",")[0]
        .strip()
    )
    return configured.removeprefix("openrouter_router/").removeprefix("nvidia_router/")


def resolve_simulator_api_key(environment: dict[str, str] | None = None) -> str:
    """Resolve the participant key without coupling an NVIDIA run to OpenRouter."""

    source = environment if environment is not None else os.environ
    configured = source.get("AAA_BENCHMARK_PARTICIPANT_MODEL", source.get("AAA_LLM_MODEL", ""))
    key_name = (
        "AAA_NVIDIA_API_KEY" if configured.split(",")[0].strip().startswith("nvidia_router/") else "AAA_LLM_API_KEY"
    )
    return source.get(key_name, "").strip()


def participant_messages(
    transcript: list[dict[str, str]], participant_system: str = PARTICIPANT_SYSTEM
) -> list[dict[str, str]]:
    """Build a provider-valid request that asks for the participant's next turn."""

    return [
        {"role": "system", "content": participant_system},
        *transcript,
        {"role": "user", "content": "Write your next reply now in character."},
    ]


def participant_request_body(
    transcript: list[dict[str, str]],
    model: str,
    api_base: str = "",
    participant_system: str = PARTICIPANT_SYSTEM,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "messages": participant_messages(transcript, participant_system=participant_system),
        "temperature": 0.2,
    }
    if "nvidia.com" not in api_base:
        body["reasoning"] = {"exclude": True}
        body["include_reasoning"] = False
    return body


def parse_participant_completion(data: dict[str, Any]) -> ParticipantCompletion:
    """Parse provider output and make exclusion reasons explicit."""

    choices = data.get("choices")
    choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    content = str(message.get("content") or "").strip()
    finish_reason = choice.get("finish_reason")
    native_finish_reason = choice.get("native_finish_reason") or data.get("native_finish_reason")
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    model = str(data["model"]) if data.get("model") else None
    provider = str(data["provider"]) if data.get("provider") else None
    sentence_count = len(re.findall(r"[.!?]+(?:[\"')\]]+)?(?=\s|$)", content))
    if content and sentence_count == 0:
        sentence_count = 1
    word_count = len(content.split())
    reasons = []
    if not content:
        reasons.append("empty_content")
    if finish_reason != "stop":
        reasons.append("finish_reason_not_stop")
    if not 1 <= sentence_count <= 3:
        reasons.append("sentence_count_out_of_range")
    if not usage:
        reasons.append("missing_usage")
    if model is None:
        reasons.append("missing_model")
    if provider is None:
        reasons.append("missing_provider")
    return ParticipantCompletion(
        content=content,
        finish_reason=str(finish_reason) if finish_reason is not None else None,
        native_finish_reason=str(native_finish_reason) if native_finish_reason is not None else None,
        usage=dict(usage),
        model=model,
        provider=provider,
        sentence_count=sentence_count,
        word_count=word_count,
        valid=not reasons,
        exclusion_reasons=tuple(reasons),
    )


def _simulated_participant(
    transcript: list[dict[str, str]],
    *,
    model: str,
    api_key: str,
    api_base: str,
    participant_system: str = PARTICIPANT_SYSTEM,
    max_retries: int = 3,
) -> ParticipantCompletion:
    for attempt in range(max_retries):
        try:
            response = httpx.post(
                f"{api_base.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=participant_request_body(
                    transcript, model, api_base=api_base, participant_system=participant_system
                ),
                timeout=180.0,
            )
            response.raise_for_status()
            res_json = response.json()
            if "provider" not in res_json and "nvidia" in api_base:
                res_json["provider"] = "nvidia"
            elif "provider" not in res_json and "openrouter" in api_base:
                res_json["provider"] = "openrouter"
            if "model" not in res_json or not res_json.get("model"):
                res_json["model"] = model
            return parse_participant_completion(res_json)
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.TransportError, httpx.RequestError):
            if attempt == max_retries - 1:
                raise
            time.sleep(3.0 * (attempt + 1))
    raise RuntimeError("unreachable retry state in _simulated_participant")


def _run_conversation(
    client: Any,
    *,
    policy: str,
    turn_count: int,
    simulator_model: str,
    api_key: str,
    api_base: str,
    scenario_id: str = "cache_wipe_429",
) -> list[dict[str, Any]]:
    scenario = get_scenario(scenario_id)
    regulator = client.app.state.registry.get("homeostatic_regulator")
    if regulator is None or not hasattr(regulator, "set_intervention_policy_mode"):
        raise RuntimeError("homeostatic regulator does not expose benchmark policy selection")
    regulator.set_intervention_policy_mode(policy)

    conversation_id = ""
    parent_message_id = None
    prompt = scenario.initial_prompt
    transcript: list[dict[str, str]] = []
    turns: list[dict[str, Any]] = []

    for turn_number in range(1, turn_count + 1):
        payload: dict[str, Any] = {"content": prompt, "speaker": "human"}
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if parent_message_id:
            payload["parent_message_id"] = parent_message_id
        message_response = client.post("/api/chat/message", json=payload)
        message_response.raise_for_status()
        message_data = message_response.json()
        conversation_id = message_data["conversation_id"]

        started = time.perf_counter()
        generation_response = client.post(
            "/api/chat/generate",
            json={
                "conversation_id": conversation_id,
                "user_message_id": message_data["user_message_id"],
                "max_tokens": 900,
            },
        )
        generation_response.raise_for_status()
        latency_ms = (time.perf_counter() - started) * 1000.0
        generated = generation_response.json()
        parent_message_id = generated.get("id")
        recommendations = generated.get("homeostatic_recommendations") or {}
        reply = str(generated.get("content", ""))
        turns.append(
            {
                "turn": turn_number,
                "user": prompt,
                "apparatus": reply,
                "metrics": generated.get("metrics") or {},
                "homeostatic": recommendations,
                "applied_controls": recommendations.get("applied_controls") or {},
                "model": generated.get("model_used"),
                "provider": generated.get("provider_used"),
                "seed_available": False,
                "latency_ms": round(latency_ms, 3),
                "finish_reason": generated.get("finish_reason"),
                "truncated": generated.get("truncated"),
                "next_participant_completion": None,
                "scenario_id": scenario_id,
            }
        )
        transcript.extend(({"role": "user", "content": prompt}, {"role": "assistant", "content": reply}))
        if turn_number < turn_count:
            participant_completion = _simulated_participant(
                transcript,
                model=simulator_model,
                api_key=api_key,
                api_base=api_base,
                participant_system=scenario.participant_system,
            )
            turns[-1]["next_participant_completion"] = participant_completion.to_dict()
            if not participant_completion.content:
                break
            prompt = participant_completion.content
    return turns


def _assert_isolated_path(path: Path, isolation_root: Path) -> Path:
    """Reject any benchmark database or receipt path outside its temporary root."""

    resolved = path.resolve()
    root = isolation_root.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"benchmark isolation path escapes temporary root: {resolved}")
    return resolved


def _worker_environment(database_path: Path) -> dict[str, str]:
    """Build the environment before importing the backend in an isolated worker."""

    environment = dict(os.environ)
    benchmark_model = environment.get("AAA_BENCHMARK_MODEL")
    environment.update(
        {
            "AAA_DB_PATH": str(database_path.resolve()),
            "AAA_RUN_MIGRATIONS": "true",
            "AAA_DAEMON_ENABLED": "false",
        }
    )
    if benchmark_model:
        environment["AAA_LLM_MODELS"] = benchmark_model
        environment["AAA_LLM_MODEL"] = benchmark_model
    return environment


def _database_fingerprint(path: Path) -> dict[str, tuple[int, int]]:
    """Capture SQLite files cheaply enough to prove a benchmark did not mutate them."""

    fingerprint: dict[str, tuple[int, int]] = {}
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            stat = candidate.stat()
            fingerprint[str(candidate.resolve())] = (stat.st_size, stat.st_mtime_ns)
    return fingerprint


def _production_database_paths() -> tuple[Path, ...]:
    paths = {PROJECT_ROOT / "backend" / "data" / "aaa.db"}
    configured = os.environ.get("AAA_DB_PATH", "").strip()
    if configured:
        path = Path(configured)
        paths.add(path if path.is_absolute() else PROJECT_ROOT / "backend" / path)
    return tuple(sorted((path.resolve() for path in paths), key=str))


def _run_isolated_arm(
    *,
    policy: str,
    repetition: int,
    turn_count: int,
    simulator_model: str,
    api_base: str,
    isolation_root: Path,
    scenario_id: str = "cache_wipe_429",
) -> dict[str, Any]:
    """Run exactly one arm in a fresh interpreter and SQLite database."""

    arm_root = _assert_isolated_path(isolation_root / f"r{repetition}_{scenario_id}_{policy}", isolation_root)
    arm_root.mkdir(parents=True, exist_ok=False)
    database_path = _assert_isolated_path(arm_root / "benchmark.db", isolation_root)
    output_path = _assert_isolated_path(arm_root / "receipt.json", isolation_root)
    command = [
        sys.executable,
        "-m",
        "benchmarks.suites.telemetry.run_dialogue_feedback_benchmark",
        "--worker-policy",
        policy,
        "--worker-repetition",
        str(repetition),
        "--worker-turns",
        str(turn_count),
        "--worker-model",
        simulator_model,
        "--worker-api-base",
        api_base,
        "--worker-scenario",
        scenario_id,
        "--worker-output",
        str(output_path),
    ]
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=_worker_environment(database_path),
        check=True,
    )
    return json.loads(output_path.read_text(encoding="utf-8"))


def _run_worker(args: argparse.Namespace) -> None:
    """Worker entry point; backend imports occur only after DB isolation is configured."""

    if args.worker_policy not in {"legacy", "progressive", "paskian"}:
        raise ValueError(f"unsupported worker policy: {args.worker_policy}")
    if not args.worker_output or not args.worker_model or not args.worker_api_base:
        raise ValueError("worker output, model, and API base are required")
    database_path = Path(os.environ.get("AAA_DB_PATH", ""))
    if not database_path.is_absolute():
        raise RuntimeError("isolated worker requires an absolute AAA_DB_PATH")

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = resolve_simulator_api_key()
    if not api_key:
        raise RuntimeError("configured participant API key is required for the adaptive live benchmark")

    from fastapi.testclient import TestClient

    from backend.main import app

    scenario_id = getattr(args, "worker_scenario", "cache_wipe_429") or "cache_wipe_429"

    with TestClient(app) as client:
        password = os.environ.get("AAA_PASSWORD", "").strip()
        if password:
            client.headers.update({"Authorization": f"Bearer {password}"})
        turns = _run_conversation(
            client,
            policy=args.worker_policy,
            turn_count=args.worker_turns,
            simulator_model=args.worker_model,
            api_key=api_key,
            api_base=args.worker_api_base,
            scenario_id=scenario_id,
        )
    result = _summarize_run(
        args.worker_policy,
        args.worker_repetition,
        turns,
        expected_completions=args.worker_turns - 1,
    )
    Path(args.worker_output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def _mean_metric(turns: list[dict[str, Any]], key: str) -> float:
    values = []
    for turn in turns:
        metrics = turn.get("metrics", {})
        value = metrics.get(key)
        if value is None and key == "collapse_pressure":
            value = metrics.get("boringness")
        if value is not None:
            values.append(float(value))
    return round(mean(values), 4) if values else 0.0


def _participant_validity(turns: list[dict[str, Any]], expected_completions: int) -> dict[str, Any]:
    completions = [turn["next_participant_completion"] for turn in turns if turn.get("next_participant_completion")]
    count = len(completions)
    stop_count = sum(item.get("finish_reason") == "stop" for item in completions)
    format_count = sum(1 <= int(item.get("sentence_count", 0)) <= 3 for item in completions)
    empty_count = sum(not str(item.get("content", "")).strip() for item in completions)
    valid_count = sum(bool(item.get("valid")) for item in completions)
    denominator = max(1, expected_completions)
    stop_rate = stop_count / denominator
    format_rate = format_count / denominator
    passed = count == expected_completions and stop_rate >= 0.95 and format_rate >= 0.95 and empty_count == 0
    return {
        "expected_completions": expected_completions,
        "completion_count": count,
        "valid_count": valid_count,
        "stop_rate": round(stop_rate, 4),
        "format_rate": round(format_rate, 4),
        "empty_count": empty_count,
        "passed": passed,
    }


def _completion_audit(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate participant completion validity without ranking benchmark arms."""

    completions = [
        completion
        for run in runs
        for turn in run.get("turns", [])
        if (completion := turn.get("next_participant_completion")) is not None
    ]
    exclusions = Counter(reason for completion in completions for reason in completion.get("exclusion_reasons", []))
    expected = sum(int(run.get("participant_validity", {}).get("expected_completions", 0)) for run in runs)
    stop_count = sum(completion.get("finish_reason") == "stop" for completion in completions)
    format_count = sum(1 <= int(completion.get("sentence_count", 0)) <= 3 for completion in completions)
    empty_count = sum(not str(completion.get("content", "")).strip() for completion in completions)
    word_counts = [int(completion.get("word_count", 0)) for completion in completions]
    run_gates = [
        {
            "policy": run["policy"],
            "repetition": run["repetition"],
            **run.get("participant_validity", {}),
        }
        for run in runs
    ]
    apparatus_turns = [turn for run in runs for turn in run.get("turns", [])]
    apparatus_truncated = sum(bool(turn.get("truncated")) for turn in apparatus_turns)
    passed = bool(run_gates) and all(bool(gate.get("passed")) for gate in run_gates)
    return {
        "purpose": "participant validity audit; policy effects require a separately powered benchmark",
        "expected_completions": expected,
        "observed_completions": len(completions),
        "valid_completions": sum(bool(completion.get("valid")) for completion in completions),
        "finish_reason_counts": dict(
            sorted(Counter(str(completion.get("finish_reason") or "null") for completion in completions).items())
        ),
        "native_finish_reason_counts": dict(
            sorted(Counter(str(completion.get("native_finish_reason") or "null") for completion in completions).items())
        ),
        "sentence_count_distribution": dict(
            sorted(Counter(int(completion.get("sentence_count", 0)) for completion in completions).items())
        ),
        "word_count": {
            "min": min(word_counts) if word_counts else None,
            "mean": round(mean(word_counts), 3) if word_counts else None,
            "max": max(word_counts) if word_counts else None,
        },
        "exclusion_reason_counts": dict(sorted(exclusions.items())),
        "gate": {
            "stop_rate": round(stop_count / max(1, expected), 4),
            "format_rate": round(format_count / max(1, expected), 4),
            "empty_count": empty_count,
            "passed": passed,
        },
        "run_gates": run_gates,
        "policy_ranking_allowed": passed,
        "apparatus_completion_context": {
            "turn_count": len(apparatus_turns),
            "truncated_count": apparatus_truncated,
            "finish_reason_counts": dict(
                sorted(Counter(str(turn.get("finish_reason") or "null") for turn in apparatus_turns).items())
            ),
            "interpretation": "apparatus truncation is separate from participant validity and may confound outcomes",
        },
    }


def _control_receipt_observable(turn: dict[str, Any]) -> bool:
    requested = (turn.get("homeostatic") or {}).get("requested_controls") or {}
    receipt = turn.get("applied_controls") or {}
    if not requested or receipt.get("controller_requested") != requested:
        return False
    accounted = {
        *dict(receipt.get("forwarded") or {}),
        *(str(item) for item in receipt.get("unsupported") or ()),
        *(str(item) for item in receipt.get("not_forwarded") or ()),
    }
    return bool(receipt.get("status")) and set(requested).issubset(accounted)


def _summarize_run(
    policy: str, repetition: int, turns: list[dict[str, Any]], *, expected_completions: int | None = None
) -> dict[str, Any]:
    receipts = build_causal_receipts(turns)
    outcomes = [receipt.outcome_score for receipt in receipts if receipt.outcome_score is not None]
    uptake = [outcome.uptake for receipt in receipts for outcome in receipt.next_turn_outcomes if outcome.valid]
    progress = [
        outcome.task_progress for receipt in receipts for outcome in receipt.next_turn_outcomes if outcome.valid
    ]
    modes = Counter(receipt.intervention.get("mode", "none") for receipt in receipts)
    observable = [_control_receipt_observable(turn) for turn in turns]
    return {
        "policy": policy,
        "repetition": repetition,
        "turn_count": len(turns),
        "mean_outcome_score": round(mean(outcomes), 4) if outcomes else 0.0,
        "mean_uptake": round(mean(uptake), 4) if uptake else 0.0,
        "mean_task_progress": round(mean(progress), 4) if progress else 0.0,
        "mean_drr": _mean_metric(turns, "divergence_resolution_ratio"),
        "mean_paskian_health": _mean_metric(turns, "paskian_health"),
        "mean_collapse_pressure": _mean_metric(turns, "collapse_pressure"),
        "mean_conceptual_velocity": _mean_metric(turns, "conceptual_velocity"),
        "mean_latency_ms": round(mean(float(turn["latency_ms"]) for turn in turns), 3),
        "control_observability_rate": round(sum(observable) / max(1, len(observable)), 4),
        "participant_validity": _participant_validity(
            turns, expected_completions if expected_completions is not None else max(0, len(turns) - 1)
        ),
        "intervention_counts": dict(sorted(modes.items())),
        "turns": turns,
        "causal_receipts": [receipt.to_dict() for receipt in receipts],
    }


def _paired_delta_ci(candidate: list[float], baseline: list[float]) -> tuple[float, float, float]:
    if len(candidate) != len(baseline):
        raise ValueError("paired arms require equal repetition counts")
    return bootstrap_mean_ci([new - old for new, old in zip(candidate, baseline, strict=True)])


def _scorecard(runs: list[dict[str, Any]], candidate_policy: str = "paskian") -> dict[str, Any]:
    policies = ("legacy", candidate_policy) if candidate_policy != "legacy" else ("legacy", "progressive")
    by_policy = {policy: [run for run in runs if run["policy"] == policy] for policy in policies}
    fields = (
        "mean_outcome_score",
        "mean_uptake",
        "mean_task_progress",
        "mean_drr",
        "mean_paskian_health",
        "mean_collapse_pressure",
        "mean_conceptual_velocity",
        "mean_latency_ms",
        "control_observability_rate",
    )
    arm_summary: dict[str, Any] = {}
    for policy, policy_runs in by_policy.items():
        arm_summary[policy] = {
            field: dict(
                zip(
                    ("mean", "ci_low", "ci_high"),
                    bootstrap_mean_ci([run[field] for run in policy_runs]),
                    strict=True,
                )
            )
            for field in fields
        }
    cand = candidate_policy if candidate_policy in by_policy else "progressive"
    deltas = {
        field: dict(
            zip(
                ("mean", "ci_low", "ci_high"),
                _paired_delta_ci(
                    [run[field] for run in by_policy[cand]],
                    [run[field] for run in by_policy["legacy"]],
                ),
                strict=True,
            )
        )
        for field in fields
    }
    health_ok = deltas["mean_paskian_health"]["mean"] >= -0.02
    drr_ok = deltas["mean_drr"]["mean"] >= -0.02
    outcome_confident = deltas["mean_outcome_score"]["ci_low"] > 0.0
    uptake_confident = deltas["mean_uptake"]["ci_low"] > 0.0
    progress_confident = deltas["mean_task_progress"]["ci_low"] > 0.0
    validity_passed = all(bool(run.get("participant_validity", {}).get("passed")) for run in runs)
    if not validity_passed:
        decision = "invalid_participant_completions"
    elif not health_ok or not drr_ok:
        decision = "reject_regression"
    elif outcome_confident and uptake_confident and progress_confident:
        decision = "accept"
    else:
        decision = "inconclusive"
    return {
        "arms": arm_summary,
        "candidate_minus_legacy": deltas,
        "progressive_minus_legacy": deltas,
        "decision": decision,
        "participant_validity_passed": validity_passed,
        "acceptance_checks": {
            "paskian_health_decline_at_most_0_02": health_ok,
            "drr_decline_at_most_0_02": drr_ok,
            "outcome_gain_ci_above_zero": outcome_confident,
            "uptake_gain_ci_above_zero": uptake_confident,
            "task_progress_gain_ci_above_zero": progress_confident,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--turns", type=int, default=8)
    parser.add_argument("--candidate-policy", type=str, default="paskian", choices=["paskian", "progressive"])
    parser.add_argument("--participant-model", type=str, default=None, help="Override participant model")
    parser.add_argument(
        "--scenario",
        type=str,
        default="cache_wipe_429",
        help="Select dialogue scenario to run, comma-separated list, or 'all' to ablate across the entire scenario suite",
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--rescore", type=Path)
    parser.add_argument("--worker-policy", help=argparse.SUPPRESS)
    parser.add_argument("--worker-repetition", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--worker-turns", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--worker-model", help=argparse.SUPPRESS)
    parser.add_argument("--worker-api-base", help=argparse.SUPPRESS)
    parser.add_argument("--worker-scenario", help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_policy:
        _run_worker(args)
        return
    if args.rescore:
        runs_path = args.rescore / "telemetry_receipts.json"
        saved_runs = json.loads(runs_path.read_text(encoding="utf-8"))
        rescored = [_summarize_run(run["policy"], int(run["repetition"]), run["turns"]) for run in saved_runs]
        runs_path.write_text(json.dumps(rescored, indent=2) + "\n", encoding="utf-8")
        (args.rescore / "scorecard.json").write_text(
            json.dumps(_scorecard(rescored), indent=2) + "\n", encoding="utf-8"
        )
        (args.rescore / "completion_audit.json").write_text(
            json.dumps(_completion_audit(rescored), indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"rescored": str(args.rescore)}, indent=2))
        return
    if args.repetitions < 2 or args.turns < 3:
        raise ValueError("benchmark requires at least 2 repetitions and 3 turns")

    load_dotenv(PROJECT_ROOT / ".env")
    if args.participant_model:
        os.environ["AAA_BENCHMARK_PARTICIPANT_MODEL"] = args.participant_model
    api_key = resolve_simulator_api_key()
    if not api_key:
        raise RuntimeError("configured participant API key is required for the adaptive live benchmark")
    api_base = resolve_simulator_api_base()
    simulator_model = resolve_simulator_model()
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or PROJECT_ROOT / "benchmarks" / "runs" / "telemetry" / f"dialogue_feedback_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    if args.scenario == "all":
        scenarios_to_run = list(SCENARIOS.keys())
    elif "," in args.scenario:
        scenarios_to_run = [s.strip() for s in args.scenario.split(",") if s.strip()]
        for s in scenarios_to_run:
            if s not in SCENARIOS:
                raise ValueError(f"Unknown scenario '{s}' in list. Available: {list(SCENARIOS.keys())}")
    else:
        scenarios_to_run = [args.scenario]

    runs: list[dict[str, Any]] = []
    order_rng = random.Random(1729)
    production_paths = _production_database_paths()
    production_before = {str(path): _database_fingerprint(path) for path in production_paths}
    with tempfile.TemporaryDirectory(prefix="isolated_", dir=out_dir) as temporary:
        isolation_root = Path(temporary)
        for scenario_id in scenarios_to_run:
            for repetition in range(1, args.repetitions + 1):
                policies = ["legacy", args.candidate_policy]
                order_rng.shuffle(policies)
                for policy in policies:
                    print(
                        f"scenario={scenario_id} repetition={repetition} policy={policy} turns={args.turns}",
                        flush=True,
                    )
                    arm_receipt = _run_isolated_arm(
                        policy=policy,
                        repetition=repetition,
                        turn_count=args.turns,
                        simulator_model=simulator_model,
                        api_base=api_base,
                        isolation_root=isolation_root,
                        scenario_id=scenario_id,
                    )
                    runs.append(arm_receipt)
                    (out_dir / "telemetry_receipts.json").write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    production_after = {str(path): _database_fingerprint(path) for path in production_paths}
    if production_after != production_before:
        raise RuntimeError("benchmark modified a production database")

    metadata = {
        "benchmark": "dialogue_feedback_control",
        "created_at": datetime.now(UTC).isoformat(),
        "repetitions_per_arm": args.repetitions,
        "turns_per_conversation": args.turns,
        "arms": ["legacy", args.candidate_policy],
        "ablation_dimension": "intervention selection policy",
        "participant": {
            "type": "adaptive_llm_simulation",
            "model": simulator_model,
            "temperature": 0.2,
            "reasoning_excluded": True,
        },
        "seed_available": False,
        "isolation": {
            "worker_process_per_arm": True,
            "temporary_database_per_arm": True,
            "production_database_unchanged": True,
        },
        "arm_order": [{"policy": run["policy"], "repetition": run["repetition"]} for run in runs],
    }
    scorecard = _scorecard(runs, candidate_policy=args.candidate_policy)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (out_dir / "telemetry_receipts.json").write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    (out_dir / "scorecard.json").write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    (out_dir / "completion_audit.json").write_text(
        json.dumps(_completion_audit(runs), indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out_dir": str(out_dir), "decision": scorecard["decision"]}, indent=2))


if __name__ == "__main__":
    main()
