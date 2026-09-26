"""Repeated live ablation of legacy and progress-aware dialogue interventions."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import Counter
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


def _simulated_participant(transcript: list[dict[str, str]], *, model: str, api_key: str, api_base: str) -> str:
    response = httpx.post(
        f"{api_base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": participant_messages(transcript),
            "temperature": 0.2,
            "max_tokens": 180,
        },
        timeout=90.0,
    )
    response.raise_for_status()
    return str(response.json()["choices"][0]["message"]["content"]).strip()


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
                "max_tokens": 450,
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
            }
        )
        transcript.extend(({"role": "user", "content": prompt}, {"role": "assistant", "content": reply}))
        if turn_number < turn_count:
            prompt = _simulated_participant(
                transcript,
                model=simulator_model,
                api_key=api_key,
                api_base=api_base,
            )
    return turns


def _mean_metric(turns: list[dict[str, Any]], key: str) -> float:
    values = [float(turn["metrics"][key]) for turn in turns if turn.get("metrics", {}).get(key) is not None]
    return round(mean(values), 4) if values else 0.0


def _summarize_run(policy: str, repetition: int, turns: list[dict[str, Any]]) -> dict[str, Any]:
    receipts = build_causal_receipts(turns, turns)
    outcomes = [receipt.outcome_score for receipt in receipts if receipt.outcome_score is not None]
    progress = [outcome.task_progress for receipt in receipts for outcome in receipt.next_turn_outcomes]
    modes = Counter(receipt.intervention.get("mode", "none") for receipt in receipts)
    observable = [bool(receipt.requested_controls) and bool(receipt.applied_controls) for receipt in receipts]
    return {
        "policy": policy,
        "repetition": repetition,
        "turn_count": len(turns),
        "mean_outcome_score": round(mean(outcomes), 4) if outcomes else 0.0,
        "mean_task_progress": round(mean(progress), 4) if progress else 0.0,
        "mean_drr": _mean_metric(turns, "divergence_resolution_ratio"),
        "mean_paskian_health": _mean_metric(turns, "paskian_health"),
        "mean_collapse_pressure": _mean_metric(turns, "collapse_pressure"),
        "mean_conceptual_velocity": _mean_metric(turns, "conceptual_velocity"),
        "mean_latency_ms": round(mean(float(turn["latency_ms"]) for turn in turns), 3),
        "control_observability_rate": round(sum(observable) / max(1, len(observable)), 4),
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
    progress_confident = deltas["mean_task_progress"]["ci_low"] > 0.0
    if not health_ok or not drr_ok:
        decision = "reject_regression"
    elif outcome_confident and progress_confident:
        decision = "accept"
    else:
        decision = "inconclusive"
    return {
        "arms": arm_summary,
        "progressive_minus_legacy": deltas,
        "decision": decision,
        "acceptance_checks": {
            "paskian_health_decline_at_most_0_02": health_ok,
            "drr_decline_at_most_0_02": drr_ok,
            "outcome_gain_ci_above_zero": outcome_confident,
            "task_progress_gain_ci_above_zero": progress_confident,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--turns", type=int, default=8)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
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
                runs.append(_summarize_run(policy, repetition, turns))

    metadata = {
        "benchmark": "dialogue_feedback_control",
        "created_at": datetime.now(UTC).isoformat(),
        "repetitions_per_arm": args.repetitions,
        "turns_per_conversation": args.turns,
        "arms": ["legacy", "progressive"],
        "ablation_dimension": "intervention selection policy",
        "participant": {"type": "adaptive_llm_simulation", "model": simulator_model, "temperature": 0.2},
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
