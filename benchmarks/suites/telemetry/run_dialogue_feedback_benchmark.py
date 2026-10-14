"""Repeated live ablation of legacy and progress-aware dialogue interventions."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from itertools import permutations
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, cast

import httpx
from dotenv import load_dotenv

from benchmarks.common.storage import PROJECT_ROOT
from benchmarks.suites.telemetry.causal_intervention import (
    Arm as CausalArm,
)
from benchmarks.suites.telemetry.causal_intervention import (
    Mode as CausalMode,
)
from benchmarks.suites.telemetry.causal_intervention import (
    Signals as CausalSignals,
)
from benchmarks.suites.telemetry.causal_intervention import (
    new_trial,
)
from benchmarks.suites.telemetry.intervention_evaluator import (
    bootstrap_mean_ci,
    build_causal_receipts,
    rate_participant_turn,
)
from benchmarks.suites.telemetry.scenarios import SCENARIOS, get_scenario

INITIAL_PROMPT = SCENARIOS["cache_wipe_429"].initial_prompt
PARTICIPANT_SYSTEM = SCENARIOS["cache_wipe_429"].participant_system
NVIDIA_SIMULATOR_KEY_COOLDOWN_SECONDS = 300
_nvidia_simulator_key_cooldowns: dict[str, float] = {}

_CAUSAL_MODE_DIRECTIVES = {
    CausalMode.ABSTAIN: None,
    CausalMode.CLARIFY: "Ask one precise question that identifies the unresolved claim or constraint.",
    CausalMode.COUNTEREXAMPLE: "Test the unresolved claim with one concrete counterexample and state its consequence.",
    CausalMode.EXPERIMENT: "Propose one bounded experiment with an observable acceptance criterion.",
    CausalMode.REFRAME: "Reframe the unresolved issue on a different axis and connect it to the stated goal.",
    CausalMode.CONSOLIDATE: "Consolidate what has changed, preserve the remaining disagreement, and name the next decision.",
    CausalMode.COMPRESS: "State the unresolved boundary and the single decision needed to continue in at most two sentences.",
}
_NEGATED_PROGRESS = re.compile(
    r"\b(?:do not|don't|does not|doesn't|will not|won't|cannot|can't|refuse to|refusal to|decline to|reject to)\s+"
    r"(?:run|conduct|perform|carry out|complete|try|do)?\s*(?:the\s+)?"
    r"(?:test|measure|compare|experiment|implement|prototype|verify|design)\b",
    re.I,
)


def _benchmark_causal_selector(regulator: Any, arm: CausalArm, scenario_id: str, turn_count: int) -> dict[str, Any]:
    """Attach the T37 selector to one isolated benchmark worker only."""

    original_process = regulator.process
    state: dict[str, Any] = {"trial": None, "receipts": [], "previous_prompt": "", "boring_streak": 0}

    async def process(payload: dict[str, Any]) -> dict[str, Any]:
        result = await original_process(payload)
        metrics = result.get("metrics")
        recommendations = result.get("homeostatic_recommendations")
        if not isinstance(metrics, dict) or not isinstance(recommendations, dict):
            return result
        conversation_id = str(result.get("conversation_id") or result.get("id") or "benchmark")
        if state["trial"] is None:
            trial = new_trial(conversation_id, arm, max_turns=turn_count)
            trial.start_issue(scenario_id, get_scenario(scenario_id).unresolved_issue)
            state["trial"] = trial

        participant_text = str(result.get("content", ""))
        intervention = recommendations.get("intervention")
        intervention = intervention if isinstance(intervention, dict) else {}
        raw_mode = str(intervention.get("mode", "abstain"))
        try:
            predicted_mode = CausalMode(raw_mode)
        except ValueError:
            predicted_mode = CausalMode.REFRAME if raw_mode in {"teachback_and_fork", "reframe"} else CausalMode.ABSTAIN
        completion = rate_participant_turn(participant_text)
        previous_words = set(re.findall(r"[a-z0-9]+", state["previous_prompt"].lower()))
        current_words = set(re.findall(r"[a-z0-9]+", participant_text.lower()))
        added_words = current_words - previous_words
        progress_signal = completion.task_progress > 0 and not _NEGATED_PROGRESS.search(participant_text)
        issue_advanced = progress_signal and len(added_words) >= 2
        participant_revised = completion.uptake > 0 or issue_advanced
        collapse_pressure = float(metrics.get("collapse_pressure", metrics.get("boringness", 0.0)) or 0.0)
        drr = float(metrics.get("divergence_resolution_ratio", 0.5) or 0.0)
        terms_clear = any(word in current_words for word in get_scenario(scenario_id).domain_keywords)
        signals = CausalSignals(
            signals_complete=True,
            pressure=collapse_pressure >= 0.60,
            context_over_budget=bool(metrics.get("context_over_budget", False)),
            has_new_subclaim=bool(added_words),
            participant_revised=participant_revised,
            issue_advanced=issue_advanced,
            boring_previous=bool(state["receipts"] and state["receipts"][-1].get("boring")),
            boring_streak=int(state["boring_streak"]),
            predicted_mode=predicted_mode,
            term_ambiguity=bool(re.search(r"\b(what|how|which|unclear|mean)\b", participant_text, re.I)),
            claim_stable=collapse_pressure >= 0.60 and drr < 0.50,
            falsifiable=bool(re.search(r"\b(test|measure|evidence|benchmark|criterion)\b", participant_text, re.I)),
            live_hypotheses=2 if "or" in current_words else 0,
            experiment_within_budget=turn_count <= 32,
            terms_clear=terms_clear,
        )
        receipt = state["trial"].select(signals)
        state["receipts"].append(receipt)
        state["boring_streak"] = state["boring_streak"] + 1 if receipt["boring"] else 0
        state["previous_prompt"] = participant_text
        recommendations["causal_selector_receipt"] = receipt
        recommendations["intervention"] = {
            "mode": str(receipt["mode"]),
            "reason": str(receipt["predicate_id"]),
            "directive": _CAUSAL_MODE_DIRECTIVES[CausalMode(str(receipt["mode"]))],
            "observed_outcome": {"uptake": completion.uptake, "task_progress": completion.task_progress},
            "causal_arm": arm,
        }
        messages = result.get("messages")
        directive = recommendations["intervention"]["directive"]
        if isinstance(messages, list):
            messages[:] = [
                message
                for message in messages
                if not (
                    isinstance(message, dict)
                    and str(message.get("content", "")).startswith("[SOMATIC REFLECTION DIRECTIVE]:")
                )
            ]
            if directive:
                index = (
                    len(messages) - 1 if messages and messages[-1].get("role") in {"user", "human"} else len(messages)
                )
                messages.insert(
                    index,
                    {"role": "system", "content": f"[CAUSAL SELECTOR {arm}/{receipt['predicate_id']}]: {directive}"},
                )
        return result

    regulator.process = process
    return state


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
    is_nvidia = "nvidia" in api_base.lower()
    api_keys = [key.strip() for key in api_key.split(",") if key.strip()] if is_nvidia else [api_key]
    if not api_keys:
        raise RuntimeError("no participant API key is configured")

    if is_nvidia:
        now = time.time()
        available_keys = [key for key in api_keys if _nvidia_simulator_key_cooldowns.get(key, 0.0) <= now]
        while not available_keys:
            retry_after = min(_nvidia_simulator_key_cooldowns.get(key, now) for key in api_keys) - time.time()
            time.sleep(max(0.01, retry_after))
            now = time.time()
            available_keys = [key for key in api_keys if _nvidia_simulator_key_cooldowns.get(key, 0.0) <= now]
    else:
        available_keys = api_keys

    attempts = 0
    auth_rejected: set[str] = set()
    last_error: Exception | None = None
    for round_index in range(max_retries):
        for key in available_keys:
            attempts += 1
            try:
                response = httpx.post(
                    f"{api_base.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json=participant_request_body(
                        transcript, model, api_base=api_base, participant_system=participant_system
                    ),
                    timeout=180.0,
                )
                response.raise_for_status()
                res_json = response.json()
                if "provider" not in res_json and is_nvidia:
                    res_json["provider"] = "nvidia"
                elif "provider" not in res_json and "openrouter" in api_base:
                    res_json["provider"] = "openrouter"
                if "model" not in res_json or not res_json.get("model"):
                    res_json["model"] = model
                return parse_participant_completion(res_json)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if is_nvidia and status_code in {401, 403}:
                    auth_rejected.add(key)
                    _nvidia_simulator_key_cooldowns[key] = time.time() + NVIDIA_SIMULATOR_KEY_COOLDOWN_SECONDS
                elif is_nvidia and status_code != 429:
                    raise
            except (httpx.TimeoutException, httpx.TransportError, httpx.RequestError) as exc:
                if is_nvidia:
                    raise
                last_error = exc

            if is_nvidia:
                _nvidia_simulator_key_cooldowns[key] = time.time() + NVIDIA_SIMULATOR_KEY_COOLDOWN_SECONDS

        available_keys = [key for key in available_keys if key not in auth_rejected]
        if not available_keys or round_index + 1 >= max_retries:
            break
        if is_nvidia:
            time.sleep(10.0 * (2**round_index))
        elif round_index + 1 < max_retries:
            time.sleep(3.0 * (round_index + 1))

    if is_nvidia:
        for key in api_keys:
            _nvidia_simulator_key_cooldowns[key] = time.time() + NVIDIA_SIMULATOR_KEY_COOLDOWN_SECONDS
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"participant completion failed after {attempts} attempts")


def _run_conversation(
    client: Any,
    *,
    policy: str,
    turn_count: int,
    simulator_model: str,
    api_key: str,
    api_base: str,
    scenario_id: str = "cache_wipe_429",
    causal_arm: CausalArm | None = None,
) -> list[dict[str, Any]]:
    scenario = get_scenario(scenario_id)
    regulator = client.app.state.registry.get("homeostatic_regulator")
    if regulator is None or not hasattr(regulator, "set_intervention_policy_mode"):
        raise RuntimeError("homeostatic regulator does not expose benchmark policy selection")
    if causal_arm is None:
        regulator.set_intervention_policy_mode(policy)
        causal_state: dict[str, Any] | None = None
    else:
        # Hold the existing controller at one shared mode; only the benchmark selector arm varies.
        regulator.set_intervention_policy_mode("paskian")
        causal_state = _benchmark_causal_selector(regulator, causal_arm, scenario_id, turn_count)

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
                "causal_selector_receipt": (
                    causal_state["receipts"][-1] if causal_state and causal_state["receipts"] else None
                ),
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
        environment["AAA_LLM_FALLBACK_MODEL"] = benchmark_model
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
    causal_arm: CausalArm | None = None,
) -> dict[str, Any]:
    """Run exactly one arm in a fresh interpreter and SQLite database."""

    arm_root = _assert_isolated_path(isolation_root / f"r{repetition}_{scenario_id}_{policy}", isolation_root)
    if arm_root.exists():
        output_path = _assert_isolated_path(arm_root / "receipt.json", isolation_root)
        if output_path.is_file():
            receipt = cast(dict[str, Any], json.loads(output_path.read_text(encoding="utf-8")))
            if (
                receipt.get("policy") == policy
                and int(receipt.get("repetition", -1)) == repetition
                and receipt.get("scenario_id") == scenario_id
            ):
                return receipt
            raise ValueError(f"existing isolated worker receipt does not match planned arm: {arm_root}")
        shutil.rmtree(arm_root)
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
    if causal_arm is not None:
        command.extend(("--worker-causal-arm", causal_arm))
    subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env=_worker_environment(database_path),
        check=True,
    )
    return cast(dict[str, Any], json.loads(output_path.read_text(encoding="utf-8")))


def _run_worker(args: argparse.Namespace) -> None:
    """Worker entry point; backend imports occur only after DB isolation is configured."""

    causal_arm = getattr(args, "worker_causal_arm", None)
    if causal_arm is not None and causal_arm not in {"current", "sham", "active"}:
        raise ValueError(f"unsupported worker causal arm: {causal_arm}")
    if args.worker_policy not in {"legacy", "progressive", "paskian", "current", "sham", "active"}:
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
            policy=args.worker_policy if causal_arm is None else "paskian",
            turn_count=args.worker_turns,
            simulator_model=args.worker_model,
            api_key=api_key,
            api_base=args.worker_api_base,
            scenario_id=scenario_id,
            causal_arm=causal_arm,
        )
    result = _summarize_run(
        args.worker_policy,
        args.worker_repetition,
        turns,
        expected_completions=args.worker_turns - 1,
    )
    _atomic_write_json(Path(args.worker_output), result)


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
    valid_rate = valid_count / denominator
    passed = (
        count == expected_completions
        and stop_rate >= 0.95
        and format_rate >= 0.95
        and valid_rate >= 0.95
        and empty_count == 0
    )
    return {
        "expected_completions": expected_completions,
        "completion_count": count,
        "valid_count": valid_count,
        "stop_rate": round(stop_rate, 4),
        "format_rate": round(format_rate, 4),
        "valid_rate": round(valid_rate, 4),
        "empty_count": empty_count,
        "passed": passed,
    }


def _completion_audit(runs: list[dict[str, Any]], *, require_semantic_review: bool = False) -> dict[str, Any]:
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
        "policy_ranking_allowed": passed and not require_semantic_review,
        "semantic_review_required": require_semantic_review,
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
    policy: str,
    repetition: int,
    turns: list[dict[str, Any]],
    *,
    scenario_id: str | None = None,
    expected_completions: int | None = None,
) -> dict[str, Any]:
    receipts = build_causal_receipts(turns)
    outcomes = [receipt.outcome_score for receipt in receipts if receipt.outcome_score is not None]
    uptake = [outcome.uptake for receipt in receipts for outcome in receipt.next_turn_outcomes if outcome.valid]
    progress = [
        outcome.task_progress for receipt in receipts for outcome in receipt.next_turn_outcomes if outcome.valid
    ]
    modes = Counter(receipt.intervention.get("mode", "none") for receipt in receipts)
    observable = [_control_receipt_observable(turn) for turn in turns]
    selector_receipts = [
        turn["causal_selector_receipt"] for turn in turns if isinstance(turn.get("causal_selector_receipt"), dict)
    ]
    valid_completions = [
        completion
        for turn in turns
        if isinstance((completion := turn.get("next_participant_completion")), dict) and completion.get("valid")
    ]
    disagreement_markers = (
        "disagree",
        "however",
        "but",
        "concern",
        "tradeoff",
        "risk",
        "counterexample",
        "evidence",
    )
    disagreement_depth = [
        sum(
            bool(re.search(rf"\b{re.escape(marker)}\b", str(completion.get("content", "")), re.I))
            for marker in disagreement_markers
        )
        for completion in valid_completions
    ]
    valid_selector_receipts = []
    metric_turns = turns
    if selector_receipts:
        metric_turns = []
        for turn_index, turn in enumerate(turns):
            if turn_index == 0:
                metric_turns.append(turn)  # fixed scenario prompt is a valid seeded input
                continue
            prior_completion = turns[turn_index - 1].get("next_participant_completion")
            if isinstance(prior_completion, dict) and prior_completion.get("valid"):
                metric_turns.append(turn)
    for turn_index, turn in enumerate(turns):
        if turn_index == 0:
            continue  # the initial prompt is fixed by the scenario, not an LLM participant response
        prior_completion = turns[turn_index - 1].get("next_participant_completion")
        selector_receipt = turn.get("causal_selector_receipt")
        if isinstance(prior_completion, dict) and prior_completion.get("valid") and isinstance(selector_receipt, dict):
            valid_selector_receipts.append(selector_receipt)
    state_revision_rate = (
        mean(bool(receipt.get("participant_state_revision")) for receipt in valid_selector_receipts)
        if valid_selector_receipts
        else 0.0
    )
    return {
        "policy": policy,
        "repetition": repetition,
        "scenario_id": scenario_id or (str(turns[0].get("scenario_id")) if turns else "unknown"),
        "turn_count": len(turns),
        "mean_outcome_score": round(mean(outcomes), 4) if outcomes else 0.0,
        "mean_uptake": round(mean(uptake), 4) if uptake else 0.0,
        "mean_task_progress": round(mean(progress), 4) if progress else 0.0,
        "mean_drr": _mean_metric(metric_turns, "divergence_resolution_ratio"),
        "mean_paskian_health": _mean_metric(metric_turns, "paskian_health"),
        "mean_collapse_pressure": _mean_metric(metric_turns, "collapse_pressure"),
        "mean_conceptual_velocity": _mean_metric(metric_turns, "conceptual_velocity"),
        "mean_latency_ms": round(mean(float(turn["latency_ms"]) for turn in turns), 3),
        "control_observability_rate": round(sum(observable) / max(1, len(observable)), 4),
        "state_revision_rate": round(state_revision_rate, 4),
        "disagreement_depth_proxy": round(mean(disagreement_depth), 4) if disagreement_depth else 0.0,
        "valid_metric_turn_count": len(metric_turns),
        "excluded_invalid_turn_count": len(turns) - len(metric_turns),
        "participant_validity": _participant_validity(
            turns, expected_completions if expected_completions is not None else max(0, len(turns) - 1)
        ),
        "intervention_counts": dict(sorted(modes.items())),
        "turns": turns,
        "causal_receipts": [receipt.to_dict() for receipt in receipts],
        "selector_receipts": selector_receipts,
    }


def _paired_delta_ci(candidate: list[float], baseline: list[float]) -> tuple[float, float, float]:
    if len(candidate) != len(baseline):
        raise ValueError("paired arms require equal repetition counts")
    return bootstrap_mean_ci([new - old for new, old in zip(candidate, baseline, strict=True)])


def _planned_arms(
    scenario_ids: list[str], repetitions: int, candidate_policy: str, *, three_arm: bool = False
) -> list[dict[str, Any]]:
    """Create stable, counterbalanced order so interrupted runs can resume exactly."""

    order_rng = random.Random(1729)
    plan: list[dict[str, Any]] = []
    for scenario_index, scenario_id in enumerate(scenario_ids):
        policies = ["current", "sham", "active"] if three_arm else ["legacy", candidate_policy]
        counterbalance_orders = list(permutations(policies))
        order_rng.shuffle(counterbalance_orders)
        for repetition in range(1, repetitions + 1):
            order_index = (repetition - 1 + scenario_index) % len(counterbalance_orders)
            order = counterbalance_orders[order_index]
            plan.extend({"scenario_id": scenario_id, "repetition": repetition, "policy": policy} for policy in order)
    return plan


def _resume_contract(
    *,
    scenario_ids: list[str],
    repetitions: int,
    turns: int,
    candidate_policy: str,
    apparatus_model: str,
    simulator_model: str,
    api_base: str,
    three_arm: bool = False,
) -> dict[str, Any]:
    contract = {
        "schema_version": 1,
        "scenario_ids": scenario_ids,
        "repetitions_per_arm": repetitions,
        "turns_per_conversation": turns,
        "arms": ["current", "sham", "active"] if three_arm else ["legacy", candidate_policy],
        "apparatus_model": apparatus_model,
        "participant_model": simulator_model,
        "api_base": api_base,
        "arm_order_seed": 1729,
    }
    if three_arm:
        contract["three_arm_selector"] = True
    return contract


def _causal_scorecard(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare paired selector arms while keeping proxy measures explicit."""

    arms = ("current", "sham", "active")
    by_arm = {arm: [run for run in runs if run["policy"] == arm] for arm in arms}
    valid = bool(runs) and all(bool(run.get("participant_validity", {}).get("passed")) for run in runs)
    if not valid or any(not by_arm[arm] for arm in arms):
        return {
            "arms": {},
            "paired_deltas": {},
            "decision": "invalid_participant_completions" if not valid else "missing_selector_arm",
            "participant_validity_passed": valid,
            "promotion_allowed": False,
        }
    arm_keys = {arm: [(str(run["scenario_id"]), int(run["repetition"])) for run in by_arm[arm]] for arm in arms}
    if any(len(keys) != len(set(keys)) for keys in arm_keys.values()) or not (
        set(arm_keys["current"]) == set(arm_keys["sham"]) == set(arm_keys["active"])
    ):
        return {
            "arms": {},
            "paired_deltas": {},
            "decision": "incomplete_or_duplicate_pairs",
            "participant_validity_passed": valid,
            "promotion_allowed": False,
        }
    pairs_per_scenario = Counter(scenario_id for scenario_id, _ in arm_keys["current"])
    if len(pairs_per_scenario) < 3 or min(pairs_per_scenario.values(), default=0) < 10:
        return {
            "arms": {},
            "paired_deltas": {},
            "decision": "insufficient_scenarios_or_pairs",
            "participant_validity_passed": valid,
            "promotion_allowed": False,
        }

    def paired_metrics(candidate_runs: list[dict[str, Any]], baseline_runs: list[dict[str, Any]]) -> dict[str, Any]:
        candidate_by_key = {(str(run["scenario_id"]), int(run["repetition"])): run for run in candidate_runs}
        baseline_by_key = {(str(run["scenario_id"]), int(run["repetition"])): run for run in baseline_runs}
        keys = sorted(set(candidate_by_key) & set(baseline_by_key))
        fields = ("state_revision_rate", "disagreement_depth_proxy", "mean_paskian_health", "mean_drr")
        return {
            field: dict(
                zip(
                    ("mean", "ci_low", "ci_high"),
                    _paired_delta_ci(
                        [float(candidate_by_key[key][field]) for key in keys],
                        [float(baseline_by_key[key][field]) for key in keys],
                    ),
                    strict=True,
                )
            )
            for field in fields
        }

    contrasts = (("active", "current"), ("active", "sham"), ("sham", "current"))
    pairwise = {
        f"{candidate}_minus_{baseline}": paired_metrics(by_arm[candidate], by_arm[baseline])
        for candidate, baseline in contrasts
    }
    scenario_ids = sorted({str(run["scenario_id"]) for run in runs})
    scenario_pairwise: dict[str, dict[str, Any]] = {}
    for scenario_id in scenario_ids:
        scenario_arms = {arm: [run for run in by_arm[arm] if str(run["scenario_id"]) == scenario_id] for arm in arms}
        scenario_pairwise[scenario_id] = {
            f"{candidate}_minus_{baseline}": paired_metrics(scenario_arms[candidate], scenario_arms[baseline])
            for candidate, baseline in contrasts
        }

    summaries: dict[str, Any] = {}
    for arm, arm_runs in by_arm.items():
        summaries[arm] = {}
        for field in ("state_revision_rate", "disagreement_depth_proxy", "mean_paskian_health", "mean_drr"):
            values = [float(run[field]) for run in arm_runs]
            summaries[arm][field] = {
                "mean": round(mean(values), 4),
                "population_sd": round(pstdev(values), 4),
                "min": min(values),
                "max": max(values),
                "values": values,
            }
    health_ok = all(
        scenario_pairwise[scenario][contrast][field]["mean"] >= -0.02
        for scenario in scenario_ids
        for contrast in ("active_minus_sham", "active_minus_current")
        for field in ("mean_paskian_health", "mean_drr")
    )
    state_revision_gain = all(
        scenario_pairwise[scenario][contrast]["state_revision_rate"]["ci_low"] > 0
        for scenario in scenario_ids
        for contrast in ("active_minus_sham", "active_minus_current")
    )
    disagreement_preserved = all(
        scenario_pairwise[scenario][contrast]["disagreement_depth_proxy"]["mean"] >= -0.05
        for scenario in scenario_ids
        for contrast in ("active_minus_sham", "active_minus_current")
    )
    return {
        "arms": summaries,
        "paired_deltas": pairwise,
        "scenario_paired_deltas": scenario_pairwise,
        "decision": (
            "diagnostic_signal_only"
            if health_ok and state_revision_gain and disagreement_preserved
            else "inconclusive_proxy_only"
        ),
        "participant_validity_passed": True,
        "promotion_allowed": False,
        "acceptance_checks": {
            "active_state_revision_ci_above_zero_vs_sham_and_current": state_revision_gain,
            "health_decline_at_most_0_02_vs_sham_and_current": health_ok,
            "disagreement_depth_proxy_decline_at_most_0_05": disagreement_preserved,
            "promotion_blocked_without_blinded_semantic_review": True,
        },
        "measure_caveats": {
            "state_revision_rate": "lexical uptake/task-progress proxy from participant turns",
            "disagreement_depth_proxy": "count of distinct explicit disagreement/tradeoff markers; not semantic depth annotation",
            "health": "mean controller paskian_health and divergence_resolution_ratio from live telemetry",
        },
    }


def _atomic_write_json(path: Path, payload: Any) -> None:
    """Atomically persist benchmark checkpoints across process interruption."""

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, indent=2)
            temporary_file.write("\n")
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _receipt_key(receipt: dict[str, Any]) -> tuple[str, int, str]:
    scenario_id = receipt.get("scenario_id")
    if not scenario_id:
        turns = receipt.get("turns")
        if isinstance(turns, list) and turns and isinstance(turns[0], dict):
            scenario_id = turns[0].get("scenario_id")
    if not scenario_id:
        raise ValueError("resume receipt is missing scenario_id")
    return (str(scenario_id), int(receipt["repetition"]), str(receipt["policy"]))


def _load_resume_receipts(out_dir: Path, expected_contract: dict[str, Any]) -> list[dict[str, Any]]:
    metadata_path = out_dir / "metadata.json"
    receipts_path = out_dir / "telemetry_receipts.json"
    if not out_dir.is_dir() or not metadata_path.is_file():
        raise ValueError("resume requires an existing run directory with metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("resume_contract") != expected_contract:
        raise ValueError("resume parameters do not match the original run metadata")
    if not receipts_path.exists():
        return []
    receipts = json.loads(receipts_path.read_text(encoding="utf-8"))
    if not isinstance(receipts, list) or not all(isinstance(item, dict) for item in receipts):
        raise ValueError("resume telemetry_receipts.json must contain a list of run receipts")
    return receipts


def _scorecard(runs: list[dict[str, Any]], candidate_policy: str = "paskian") -> dict[str, Any]:
    policies = ("legacy", candidate_policy) if candidate_policy != "legacy" else ("legacy", "progressive")
    by_policy = {policy: [run for run in runs if run["policy"] == policy] for policy in policies}
    validity = bool(runs) and all(bool(run.get("participant_validity", {}).get("passed")) for run in runs)
    if not validity or any(not arm for arm in by_policy.values()):
        return {
            "arms": {},
            "candidate_minus_legacy": {},
            "progressive_minus_legacy": {},
            "decision": "invalid_participant_completions" if not validity else "missing_policy_arm",
            "participant_validity_passed": validity,
            "acceptance_checks": {},
        }
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
    parser.add_argument(
        "--three-arm-selector",
        action="store_true",
        help="Run the T38 current/sham/active unresolved-issue selector comparison",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Validate a run and print planned arms/model request count without making provider calls",
    )
    parser.add_argument("--participant-model", type=str, default=None, help="Override participant model")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a compatible interrupted run in the existing --out directory, skipping completed arms",
    )
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
    parser.add_argument("--worker-causal-arm", choices=["current", "sham", "active"], help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_policy:
        _run_worker(args)
        return
    if args.rescore:
        runs_path = args.rescore / "telemetry_receipts.json"
        saved_runs = json.loads(runs_path.read_text(encoding="utf-8"))
        rescored = [_summarize_run(run["policy"], int(run["repetition"]), run["turns"]) for run in saved_runs]
        is_three_arm = {run["policy"] for run in rescored} == {"current", "sham", "active"}
        runs_path.write_text(json.dumps(rescored, indent=2) + "\n", encoding="utf-8")
        (args.rescore / "scorecard.json").write_text(
            json.dumps(_causal_scorecard(rescored) if is_three_arm else _scorecard(rescored), indent=2) + "\n",
            encoding="utf-8",
        )
        (args.rescore / "completion_audit.json").write_text(
            json.dumps(_completion_audit(rescored, require_semantic_review=is_three_arm), indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"rescored": str(args.rescore)}, indent=2))
        return
    if args.repetitions < 2 or args.turns < 3:
        raise ValueError("benchmark requires at least 2 repetitions and 3 turns")
    if args.three_arm_selector and args.repetitions < 10:
        raise ValueError("T38 three-arm comparison requires at least 10 repetitions per scenario and arm")

    load_dotenv(PROJECT_ROOT / ".env")
    if args.participant_model:
        os.environ["AAA_BENCHMARK_PARTICIPANT_MODEL"] = args.participant_model
    api_base = resolve_simulator_api_base()
    simulator_model = resolve_simulator_model()
    apparatus_model = os.environ.get("AAA_BENCHMARK_MODEL", os.environ.get("AAA_LLM_MODEL", "")).strip()

    if args.scenario == "all":
        scenarios_to_run = list(SCENARIOS.keys())
    elif "," in args.scenario:
        scenarios_to_run = [s.strip() for s in args.scenario.split(",") if s.strip()]
        for s in scenarios_to_run:
            if s not in SCENARIOS:
                raise ValueError(f"Unknown scenario '{s}' in list. Available: {list(SCENARIOS.keys())}")
    else:
        scenarios_to_run = [args.scenario]

    unknown_scenarios = [scenario_id for scenario_id in scenarios_to_run if scenario_id not in SCENARIOS]
    if unknown_scenarios:
        raise ValueError(f"Unknown scenario(s): {unknown_scenarios}; available: {list(SCENARIOS)}")
    if args.three_arm_selector and len(scenarios_to_run) < 3:
        raise ValueError("T38 three-arm comparison requires at least three contrasting scenarios")

    arm_plan = _planned_arms(
        scenarios_to_run, args.repetitions, args.candidate_policy, three_arm=args.three_arm_selector
    )
    apparatus_generations = len(arm_plan) * args.turns
    participant_completions = len(arm_plan) * (args.turns - 1)
    logical_model_requests = apparatus_generations + participant_completions
    if args.plan_only:
        print(
            json.dumps(
                {
                    "three_arm_selector": args.three_arm_selector,
                    "scenarios": scenarios_to_run,
                    "repetitions_per_scenario_arm": args.repetitions,
                    "turns_per_conversation": args.turns,
                    "arms": ["current", "sham", "active"]
                    if args.three_arm_selector
                    else ["legacy", args.candidate_policy],
                    "isolated_worker_arms": len(arm_plan),
                    "apparatus_generations": apparatus_generations,
                    "participant_completions": participant_completions,
                    "logical_model_requests": logical_model_requests,
                    "participant_model": simulator_model,
                    "apparatus_model": apparatus_model or "application-config-default",
                    "api_base": api_base,
                    "resume_supported": True,
                    "provider_calls_made": 0,
                },
                indent=2,
            )
        )
        return
    api_key = resolve_simulator_api_key()
    if not api_key:
        raise RuntimeError("configured participant API key is required for the adaptive live benchmark")

    resume_contract = _resume_contract(
        scenario_ids=scenarios_to_run,
        repetitions=args.repetitions,
        turns=args.turns,
        candidate_policy=args.candidate_policy,
        apparatus_model=apparatus_model,
        simulator_model=simulator_model,
        api_base=api_base,
        three_arm=args.three_arm_selector,
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or PROJECT_ROOT / "benchmarks" / "runs" / "telemetry" / f"dialogue_feedback_{timestamp}"
    if args.resume:
        if args.out is None:
            raise ValueError("--resume requires --out to name the existing run directory")
        runs = _load_resume_receipts(out_dir, resume_contract)
        metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
    else:
        out_dir.mkdir(parents=True, exist_ok=False)
        runs = []
        metadata = {
            "benchmark": "dialogue_feedback_control",
            "created_at": datetime.now(UTC).isoformat(),
            "repetitions_per_arm": args.repetitions,
            "turns_per_conversation": args.turns,
            "planned_logical_model_requests": logical_model_requests,
            "arms": ["current", "sham", "active"] if args.three_arm_selector else ["legacy", args.candidate_policy],
            "ablation_dimension": (
                "unresolved-issue memory read (current vs write-only sham vs read-enabled active)"
                if args.three_arm_selector
                else "intervention selection policy"
            ),
            "participant": {
                "type": "adaptive_llm_simulation",
                "model": simulator_model,
                "temperature": 0.2,
                "reasoning_excluded": True,
            },
            "api_base": api_base,
            "seed_available": False,
            "isolation": {
                "worker_process_per_arm": True,
                "temporary_database_per_arm": True,
                "production_database_unchanged": True,
            },
            "arm_order": arm_plan,
            "resume_contract": resume_contract,
            "status": "running",
            "completed_arms": [],
        }
        _atomic_write_json(out_dir / "metadata.json", metadata)
        _atomic_write_json(out_dir / "telemetry_receipts.json", runs)

    planned_keys = {(str(item["scenario_id"]), int(item["repetition"]), str(item["policy"])) for item in arm_plan}
    completed_keys: set[tuple[str, int, str]] = set()
    for run in runs:
        key = _receipt_key(run)
        if key not in planned_keys:
            raise ValueError(f"resume receipt is outside the configured run plan: {key}")
        if key in completed_keys:
            raise ValueError(f"resume contains duplicate completed arm receipt: {key}")
        completed_keys.add(key)

    metadata["status"] = "running"
    metadata["completed_arms"] = [
        {"scenario_id": scenario_id, "repetition": repetition, "policy": policy}
        for scenario_id, repetition, policy in sorted(completed_keys)
    ]
    _atomic_write_json(out_dir / "metadata.json", metadata)
    production_paths = _production_database_paths()
    production_before = {str(path): _database_fingerprint(path) for path in production_paths}
    with tempfile.TemporaryDirectory(prefix="isolated_", dir=out_dir) as temporary:
        isolation_root = Path(temporary)
        for planned_arm in arm_plan:
            key = (
                str(planned_arm["scenario_id"]),
                int(planned_arm["repetition"]),
                str(planned_arm["policy"]),
            )
            if key in completed_keys:
                continue
            scenario_id, repetition, policy = key
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
                causal_arm=cast(CausalArm, policy) if args.three_arm_selector else None,
            )
            runs.append(arm_receipt)
            completed_keys.add(key)
            _atomic_write_json(out_dir / "telemetry_receipts.json", runs)
            metadata["completed_arms"] = [
                {"scenario_id": item_scenario, "repetition": item_repetition, "policy": item_policy}
                for item_scenario, item_repetition, item_policy in sorted(completed_keys)
            ]
            _atomic_write_json(out_dir / "metadata.json", metadata)
    production_after = {str(path): _database_fingerprint(path) for path in production_paths}
    if production_after != production_before:
        raise RuntimeError("benchmark modified a production database")

    metadata["status"] = "complete"
    scorecard = (
        _causal_scorecard(runs) if args.three_arm_selector else _scorecard(runs, candidate_policy=args.candidate_policy)
    )
    _atomic_write_json(out_dir / "metadata.json", metadata)
    _atomic_write_json(out_dir / "telemetry_receipts.json", runs)
    _atomic_write_json(out_dir / "scorecard.json", scorecard)
    _atomic_write_json(
        out_dir / "completion_audit.json",
        _completion_audit(runs, require_semantic_review=args.three_arm_selector),
    )
    print(json.dumps({"out_dir": str(out_dir), "decision": scorecard["decision"]}, indent=2))


if __name__ == "__main__":
    main()
