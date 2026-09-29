"""Run a bounded, text-only speed and instruction-adherence comparison."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from benchmarks.common.storage import PROJECT_ROOT, create_run_directory, save_run_metadata, setup_run_logger

Task = tuple[str, str]

TASKS: tuple[Task, ...] = (
    (
        "json",
        "Return only valid JSON with exactly these keys: risk (string), priority (integer 1-5), "
        "actions (array of exactly 3 short strings). Assess this: retrying a failed payment without idempotency.",
    ),
    (
        "bullets",
        "Return exactly three markdown bullet lines. Each line must start with [A], [B], or [C] in order, "
        "contain 5 to 8 words, and propose a safe response to an HTTP 429.",
    ),
    (
        "math",
        "Solve and answer in exactly two lines. Line 1 must be `17`. Line 2 must explain the calculation "
        "in at most 12 words: a queue has 23 jobs, processes 9, then receives 3.",
    ),
    (
        "code",
        "Return Python code only, no Markdown fence. Define `def clamp(value, lower, upper):` that returns "
        "value constrained inclusively to lower and upper, with no imports.",
    ),
)


def _quality_pass(task: str, content: str) -> bool:
    """Score only auditable, task-specific adherence; this is not a general quality claim."""

    normalized = content.strip()
    if task == "json":
        try:
            data = json.loads(normalized)
        except json.JSONDecodeError:
            return False
        return (
            isinstance(data, dict)
            and set(data) == {"risk", "priority", "actions"}
            and isinstance(data["risk"], str)
            and isinstance(data["priority"], int)
            and 1 <= data["priority"] <= 5
            and isinstance(data["actions"], list)
            and len(data["actions"]) == 3
            and all(isinstance(action, str) for action in data["actions"])
        )
    if task == "bullets":
        lines = normalized.splitlines()
        labels = ["[A]", "[B]", "[C]"]
        return len(lines) == 3 and all(
            line.removeprefix("- ").startswith(f"{label} ")
            and 5 <= len(line.removeprefix("- ").removeprefix(f"{label} ").split()) <= 8
            for label, line in zip(labels, lines, strict=True)
        )
    if task == "math":
        lines = normalized.splitlines()
        return len(lines) == 2 and lines[0].strip() == "17" and len(lines[1].split()) <= 12
    if task == "code":
        return (
            "def clamp(value, lower, upper):" in normalized
            and "```" not in normalized
            and "import " not in normalized
            and "return " in normalized
        )
    raise ValueError(f"unknown task {task}")


NVIDIA_GENERAL_MODELS: dict[str, str] = {
    "nemotron_ultra": "nvidia/nemotron-3-ultra-550b-a55b",
    "glm_flash": "z-ai/glm-5-3-flash",
    "kimi_k3": "moonshotai/kimi-k3",
    "deepseek_flash": "deepseek-ai/deepseek-v4.1-flash",
}


def _model_configs(selected_nvidia_models: tuple[str, ...]) -> dict[str, tuple[str, str, str]]:
    configs = {
        "mimo_v2_6_pro": (
            "https://openrouter.ai/api/v1",
            os.environ.get("AAA_LLM_API_KEY", "").strip(),
            "xiaomi/mimo-v2.6-pro",
        ),
    }
    nvidia_base = os.environ.get("AAA_NVIDIA_API_BASE", "https://integrate.api.nvidia.com/v1").rstrip("/")
    nvidia_key = os.environ.get("AAA_NVIDIA_API_KEY", "").strip()
    for lane in selected_nvidia_models:
        configs[lane] = (nvidia_base, nvidia_key, NVIDIA_GENERAL_MODELS[lane])
    return configs


async def _run_call(
    client: httpx.AsyncClient,
    *,
    lane: str,
    api_base: str,
    api_key: str,
    model: str,
    task: Task,
    pass_number: int,
) -> dict[str, Any]:
    task_name, prompt = task
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 500,
    }
    if lane == "mimo_v2_6_pro":
        body["reasoning"] = {"exclude": True}
    elif lane != "kimi_k3":
        body["chat_template_kwargs"] = {"enable_thinking": False}

    started = time.perf_counter()
    try:
        response = await client.post(
            f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        return {
            "lane": lane,
            "model": model,
            "task": task_name,
            "pass": pass_number,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "quality_pass": False,
            "error": type(error).__name__,
        }

    data = response.json()
    choices = data.get("choices") if isinstance(data.get("choices"), list) else []
    message = choices[0].get("message", {}) if choices and isinstance(choices[0], dict) else {}
    content = str(message.get("content") or "").strip()
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return {
        "lane": lane,
        "model": str(data.get("model") or model),
        "provider": data.get("provider"),
        "task": task_name,
        "pass": pass_number,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "quality_pass": _quality_pass(task_name, content),
        "output_tokens": usage.get("completion_tokens"),
        "response": content,
    }


def _summary(rows: list[dict[str, Any]], lanes: list[str]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for lane in lanes:
        items = [row for row in rows if row["lane"] == lane]
        successful = [row for row in items if "error" not in row]
        latencies = [float(row["latency_ms"]) for row in successful]
        summary[lane] = {
            "calls": len(items),
            "successful_calls": len(successful),
            "quality_passes": sum(bool(row["quality_pass"]) for row in successful),
            "quality_rate": round(sum(bool(row["quality_pass"]) for row in successful) / len(successful), 3)
            if successful
            else None,
            "mean_latency_ms": round(statistics.mean(latencies), 2) if latencies else None,
            "median_latency_ms": round(statistics.median(latencies), 2) if latencies else None,
            "min_latency_ms": round(min(latencies), 2) if latencies else None,
            "max_latency_ms": round(max(latencies), 2) if latencies else None,
            "errors": sum("error" in row for row in items),
        }
    return summary


async def run(
    passes: int, timeout_seconds: float, selected_nvidia_models: tuple[str, ...]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    configs = _model_configs(selected_nvidia_models)
    missing = [lane for lane, (_, api_key, _) in configs.items() if not api_key]
    if missing:
        raise RuntimeError(f"missing API key for benchmark lane(s): {', '.join(missing)}")

    rows: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        for pass_number in range(1, passes + 1):
            for lane, (api_base, api_key, model) in configs.items():
                for task in TASKS:
                    rows.append(
                        await _run_call(
                            client,
                            lane=lane,
                            api_base=api_base,
                            api_key=api_key,
                            model=model,
                            task=task,
                            pass_number=pass_number,
                        )
                    )
    protocol = {
        "task_count": len(TASKS),
        "passes_per_model": passes,
        "calls_per_model": len(TASKS) * passes,
        "temperature": 0,
        "max_tokens": 500,
        "request_timeout_seconds": timeout_seconds,
        "reasoning": "disabled for both lanes",
        "quality_metric": "deterministic task-specific instruction and format adherence",
        "nvidia_models": list(selected_nvidia_models),
    }
    return protocol, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--passes", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument(
        "--nvidia-models",
        default="nemotron_ultra",
        help=f"Comma-separated NVIDIA lanes: {', '.join(NVIDIA_GENERAL_MODELS)}",
    )
    args = parser.parse_args()
    load_dotenv(PROJECT_ROOT / ".env")
    selected_nvidia_models = tuple(filter(None, args.nvidia_models.split(",")))
    unknown = sorted(set(selected_nvidia_models).difference(NVIDIA_GENERAL_MODELS))
    if unknown:
        parser.error(f"unknown NVIDIA model lane(s): {', '.join(unknown)}")
    run_dir = create_run_directory("model_comparison", "live", "mimo_pro_vs_nvidia_general")
    logger = setup_run_logger(run_dir)
    protocol, rows = asyncio.run(run(args.passes, args.timeout_seconds, selected_nvidia_models))
    summary = _summary(rows, list(_model_configs(selected_nvidia_models)))
    metadata = {"protocol": protocol, "summary": summary}
    save_run_metadata(run_dir, metadata)
    (run_dir / "telemetry_receipts.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    logger.info("Benchmark complete: %s", run_dir)
    logger.info("Summary: %s", json.dumps(summary))


if __name__ == "__main__":
    main()
