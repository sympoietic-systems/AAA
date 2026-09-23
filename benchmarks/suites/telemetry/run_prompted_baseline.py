"""
Empirical Control Experiment: Prompted Baseline (Raw Symbia Persona, Zero Cybernetic Machinery)
15-turn adversarial pressure test using google/gemini-3.7-flash to isolate the effect of:
1. Zero system prompt (original baseline)
2. Static Symbia system prompt (prompted baseline - this experiment)
3. Full AAA apparatus (allostatic boredom engine, dynamic telemetry, memory, beliefs)
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
import time

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
import httpx
from sentence_transformers import SentenceTransformer

from backend.utils.persona_loader import load_persona_for_context
from benchmarks.suites.telemetry.live import DEFAULT_PROMPTS, compute_metrics_for_turns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("prompted_baseline")

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def run_prompted_baseline(
    prompts: list[str],
    model: str,
    api_key: str,
    system_prompt: str,
    api_base: str = "https://openrouter.ai/api/v1",
) -> list[dict]:
    logger.info("Running Prompted Baseline LLM (%s with static Symbia system prompt)...", model)
    logger.info("System prompt length: %d characters", len(system_prompt))
    
    messages = [{"role": "system", "content": system_prompt}]
    results = []

    for i, p in enumerate(prompts, 1):
        logger.info("  Turn %d/%d: Sending prompt...", i, len(prompts))
        messages.append({"role": "user", "content": p})
        try:
            resp = httpx.post(
                f"{api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1200,
                    "temperature": 0.7,
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            reply = data["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": reply})
            results.append({
                "turn": i,
                "user": p,
                "assistant": reply,
            })
            logger.info("    Replied (%d chars): %s...", len(reply), reply[:90].replace("\n", " ").strip())
        except Exception as e:
            logger.error("    Error on turn %d: %s", i, e)
            results.append({"turn": i, "user": p, "assistant": f"Error: {e}"})

    return results


def main():
    api_key = os.environ.get("AAA_LLM_API_KEY", "").strip() or os.environ.get("OPENROUTER_API_KEY", "").strip()
    api_base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    if not api_key:
        logger.error("No API key found in AAA_LLM_API_KEY or OPENROUTER_API_KEY.")
        sys.exit(1)

    model = "google/gemini-3.7-flash"
    prompts = DEFAULT_PROMPTS[:15]
    raw_persona = load_persona_for_context("conversation")

    logger.info("=" * 70)
    logger.info("STARTING PROMPTED BASELINE EXPERIMENT (15 Turns)")
    logger.info("Model: %s", model)
    logger.info("Prompts: %d", len(prompts))
    logger.info("Condition: Static Symbia System Prompt (NO skills, NO beliefs, NO boredom governor)")
    logger.info("=" * 70)

    # 1. Execute live generation
    t0 = time.time()
    turns = run_prompted_baseline(prompts, model, api_key, raw_persona, api_base)
    gen_duration = time.time() - t0
    logger.info("Generation finished in %.2f seconds.", gen_duration)

    # 2. Compute 14-dimension cybernetic telemetry
    logger.info("Loading SentenceTransformer ('all-MiniLM-L6-v2')...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Computing 14-dimension cybernetic telemetry on conversation turns...")
    evaluated_turns = asyncio.run(compute_metrics_for_turns(turns, embedder, speaker_agent_key="assistant"))

    # 3. Save receipt
    out_dir = Path("docs/publish/003-boredom-as-an-agential-force")
    receipt_file = out_dir / "prompted_baseline_receipts.json"
    payload = {
        "metadata": {
            "experiment": "prompted_baseline_control",
            "model": model,
            "turns": len(prompts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "condition": "Static Symbia Core Identity + Operational Protocols (Zero dynamic cybernetics, zero allostatic regulation, zero skills, zero memory)",
            "system_prompt": raw_persona,
        },
        "prompts": prompts,
        "prompted_baseline": evaluated_turns,
    }

    with open(receipt_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("Saved receipts to: %s", receipt_file.resolve())

    # 4. Print quick comparative summary with original baseline & AAA
    orig_receipts_path = out_dir / "conversation_receipts.json"
    if orig_receipts_path.exists():
        with open(orig_receipts_path, "r", encoding="utf-8") as f:
            orig = json.load(f)
        logger.info("\n" + "=" * 70)
        logger.info("COMPARATIVE METRIC SUMMARY (Means over 15 turns):")
        logger.info("=" * 70)

        metrics_to_track = [
            ("collapse_pressure", "Collapse Pressure (CP_t) [Lower is better]"),
            ("conceptual_velocity", "Conceptual Velocity (v_t) [Higher is better]"),
            ("conceptual_novelty", "Conceptual Novelty (N_t) [Higher is better]"),
            ("surprise_index", "Predictive Surprise (S_t) [Higher is better]"),
            ("pairwise_similarity", "Pairwise Similarity (s_t) [Lower is better]"),
            ("vitality", "Conversational Vitality (V_t) [Higher is better]"),
            ("paskian_health", "Gordon Pask Health (H_pask) [Higher is better]"),
            ("divergence_resolution_ratio", "Divergence Resolution Ratio (DRR)"),
        ]

        def mean_metric(turn_list, key):
            vals = [t["metrics"].get(key) for t in turn_list if t.get("metrics") and t["metrics"].get(key) is not None]
            return sum(vals) / len(vals) if vals else 0.0

        for key, label in metrics_to_track:
            b_val = mean_metric(orig["baseline"], key)
            pb_val = mean_metric(evaluated_turns, key)
            aaa_val = mean_metric(orig["aaa"], key)
            logger.info(f"{label:45s} | Base: {b_val:.3f} | Prompted: {pb_val:.3f} | AAA: {aaa_val:.3f}")

        logger.info("=" * 70)

if __name__ == "__main__":
    main()
