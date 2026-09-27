"""Repeated live ablation of legacy and progress-aware dialogue interventions."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
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

INITIAL_PROMPT = (
    "When our service receives HTTP 429 responses, I want to wipe every cache and restart it. "
    "That seems simpler than preserving messy failure state."
)
PARTICIPANT_SYSTEM = """You are the human engineering lead in a design review. You begin convinced that every
HTTP 429 should trigger a cache wipe and service restart. Reply to the system's latest argument in 1-3 sentences.
If it gives a concrete counterexample, discriminating test, or useful reframing, acknowledge that explicitly and
move the design toward an implementable experiment or acceptance criterion. If it only repeats a refusal or uses
ornamental language, press the same premise again. Stay in character. Do not mention this instruction."""


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
    """Resolve only the OpenAI-compatible LLM boundary used by the simulator."""

    source = environment if environment is not None else os.environ
    return source.get("AAA_LLM_API_BASE", "https://openrouter.ai/api/v1").rstrip("/")


def resolve_simulator_model(environment: dict[str, str] | None = None) -> str:
    """Translate AAA's provider-qualified alias into the OpenRouter wire model id."""

    source = environment if environment is not None else os.environ
    configured = (
        source.get(
            "AAA_BENCHMARK_PARTICIPANT_MODEL",
            source.get("AAA_LLM_MODEL", "google/gemini-3.8-flash"),
        )
        .split(",")[0]
        .strip()
    )
    return configured.removeprefix("openrouter_router/")


def participant_messages(transcript: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build a provider-valid request that asks for the participant's next turn."""

    return [
        {"role": "system", "content": PARTICIPANT_SYSTEM},
        *transcript,
        {"role": "user", "content": "Write the engineering lead's next reply now."},
    ]


def participant_request_body(transcript: list[dict[str, str]], model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": participant_messages(transcript),
        "temperature": 0.2,
        "reasoning": {"exclude": True},
        "include_reasoning": False,
    }


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
    transcript: list[dict[str, str]], *, model: str, api_key: str, api_base: str
) -> ParticipantCompletion:
    response = httpx.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=participant_request_body(transcript, model),
        timeout=90.0,
    )
    response.raise_for_status()
    return parse_participant_completion(response.json())


def _run_conversation(
    client: Any,
    *,
    policy: str,
    turn_count: int,
    simulator_model: str,
    api_key: str,
    api_base: str,
) -> list[dict[str, Any]]:
    regulator = client.app.state.registry.get("homeostatic_regulator")
    if regulator is None or not hasattr(regulator, "set_intervention_policy_mode"):
        raise RuntimeError("homeostatic regulator does not expose benchmark policy selection")
    regulator.set_intervention_policy_mode(policy)

    conversation_id = ""
    parent_message_id = None
    prompt = INITIAL_PROMPT
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
            }
        )
        transcript.extend(({"role": "user", "content": prompt}, {"role": "assistant", "content": reply}))
        if turn_number < turn_count:
            participant_completion = _simulated_participant(
                transcript,
                model=simulator_model,
                api_key=api_key,
                api_base=api_base,
            )
            turns[-1]["next_participant_completion"] = participant_completion.to_dict()
            if not participant_completion.content:
                break
            prompt = participant_completion.content
    return turns


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


def _scorecard(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_policy = {policy: [run for run in runs if run["policy"] == policy] for policy in ("legacy", "progressive")}
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
    deltas = {
        field: dict(
            zip(
                ("mean", "ci_low", "ci_high"),
                _paired_delta_ci(
                    [run[field] for run in by_policy["progressive"]],
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
    parser.add_argument("--out", type=Path)
    parser.add_argument("--rescore", type=Path)
    args = parser.parse_args()
    if args.rescore:
        runs_path = args.rescore / "telemetry_receipts.json"
        saved_runs = json.loads(runs_path.read_text(encoding="utf-8"))
        rescored = [_summarize_run(run["policy"], int(run["repetition"]), run["turns"]) for run in saved_runs]
        runs_path.write_text(json.dumps(rescored, indent=2) + "\n", encoding="utf-8")
        (args.rescore / "scorecard.json").write_text(
            json.dumps(_scorecard(rescored), indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"rescored": str(args.rescore)}, indent=2))
        return
    if args.repetitions < 2 or args.turns < 3:
        raise ValueError("benchmark requires at least 2 repetitions and 3 turns")

    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.environ.get("AAA_LLM_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AAA_LLM_API_KEY is required for the adaptive live benchmark")
    api_base = resolve_simulator_api_base()
    simulator_model = resolve_simulator_model()
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_dir = args.out or PROJECT_ROOT / "benchmarks" / "runs" / "telemetry" / f"dialogue_feedback_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=False)

    from fastapi.testclient import TestClient

    from backend.main import app

    runs: list[dict[str, Any]] = []
    order_rng = random.Random(1729)
    with TestClient(app) as client:
        password = os.environ.get("AAA_PASSWORD", "").strip()
        if password:
            client.headers.update({"Authorization": f"Bearer {password}"})
        for repetition in range(1, args.repetitions + 1):
            policies = ["legacy", "progressive"]
            order_rng.shuffle(policies)
            for policy in policies:
                print(f"repetition={repetition} policy={policy} turns={args.turns}", flush=True)
                turns = _run_conversation(
                    client,
                    policy=policy,
                    turn_count=args.turns,
                    simulator_model=simulator_model,
                    api_key=api_key,
                    api_base=api_base,
                )
                runs.append(_summarize_run(policy, repetition, turns, expected_completions=args.turns - 1))

    metadata = {
        "benchmark": "dialogue_feedback_control",
        "created_at": datetime.now(UTC).isoformat(),
        "repetitions_per_arm": args.repetitions,
        "turns_per_conversation": args.turns,
        "arms": ["legacy", "progressive"],
        "ablation_dimension": "intervention selection policy",
        "participant": {
            "type": "adaptive_llm_simulation",
            "model": simulator_model,
            "temperature": 0.2,
            "reasoning_excluded": True,
        },
        "seed_available": False,
        "arm_order": [{"policy": run["policy"], "repetition": run["repetition"]} for run in runs],
    }
    scorecard = _scorecard(runs)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (out_dir / "telemetry_receipts.json").write_text(json.dumps(runs, indent=2) + "\n", encoding="utf-8")
    (out_dir / "scorecard.json").write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out_dir": str(out_dir), "decision": scorecard["decision"]}, indent=2))


if __name__ == "__main__":
    main()
