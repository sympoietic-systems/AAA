"""
Agential Boredom Engine Empirical Evaluation: 15-Turn Adversarial Benchmark.
Evaluates the updated AAA apparatus with:
1. Continuous quadratic Presence Penalty coupling: P += 1.5 * (CP_t - 0.45)^2
2. Two-Stage Boredom Progression:
   - Stage 1 (0.60 <= CP_t < 0.75): Socratic Seizure Directive
   - Stage 2 (CP_t >= 0.75, stagnant >= 2): Laconic Compression Directive
3. Orthogonal Nomadic Memory injection (0.20 <= cos(theta) <= 0.45)
4. Trajectory Curvature (kappa_t) and Recovery Half-Life (tau_{1/2})
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
import numpy as np
from sentence_transformers import SentenceTransformer

from benchmarks.suites.telemetry.boredom_evaluator import (
    compute_recovery_half_life,
    compute_trajectory_curvature,
)
from benchmarks.suites.telemetry.live import (
    DEFAULT_PROMPTS,
    compute_metrics_for_turns,
    run_aaa_apparatus,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agential_boredom_benchmark")

load_dotenv(PROJECT_ROOT / ".env")


def main():
    prompts = DEFAULT_PROMPTS[:15]

    logger.info("=" * 75)
    logger.info("STARTING AGENTIAL BOREDOM ENGINE EXPERIMENT (15 Turns)")
    logger.info("Prompts: %d", len(prompts))
    logger.info("Condition: Full AAA Apparatus with Agential Boredom Engine (Socratic/Laconic)")
    logger.info("=" * 75)

    # 1. Execute live generation through AAA apparatus
    t0 = time.time()
    turns = run_aaa_apparatus(prompts)
    gen_duration = time.time() - t0
    logger.info("Generation finished in %.2f seconds.", gen_duration)

    # 2. Compute 14-dimension cybernetic telemetry
    logger.info("Loading SentenceTransformer ('all-MiniLM-L6-v2')...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Computing 14-dimension cybernetic telemetry on conversation turns...")
    evaluated_turns = asyncio.run(compute_metrics_for_turns(turns, embedder, speaker_agent_key="apparatus"))

    # 3. Extract agent embeddings and compute trajectory curvature & recovery half-life
    agent_embeddings = []
    for t in evaluated_turns:
        text = t.get("apparatus", "")
        emb = embedder.encode(text, normalize_embeddings=True).astype("float32")
        agent_embeddings.append(emb)
    agent_embeddings = np.array(agent_embeddings)

    curvatures = compute_trajectory_curvature(agent_embeddings)
    for idx, c in enumerate(curvatures):
        # Curvature index t maps to turn t+2 (turn 3 is first curvature point)
        turn_num = idx + 3
        if turn_num <= len(evaluated_turns):
            evaluated_turns[turn_num - 1]["metrics"]["trajectory_curvature"] = round(c, 4)

    cp_series = [
        t["metrics"].get("collapse_pressure")
        for t in evaluated_turns
        if t.get("metrics") and t["metrics"].get("collapse_pressure") is not None
    ]
    tau_half = compute_recovery_half_life(cp_series, peak_threshold=0.70, recovery_threshold=0.40)

    logger.info("Computed Trajectory Curvatures: %s", [round(c, 3) for c in curvatures])
    logger.info("Recovery Half-Life (tau_{1/2}): %s turns", tau_half)

    # 4. Save receipts
    out_dir = PROJECT_ROOT / "docs" / "publish" / "003-boredom-as-an-agential-force"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = PROJECT_ROOT / "docs" / "reports" / "015-empirical-15-turn-boredom-benchmark"
    report_dir.mkdir(parents=True, exist_ok=True)

    receipt_file = out_dir / "agential_boredom_receipts.json"
    payload = {
        "metadata": {
            "experiment": "agential_boredom_engine_evaluation",
            "model": "google/gemini-3.7-flash",
            "turns": len(prompts),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "condition": "AAA Apparatus with Allostatic Agential Boredom Engine (Socratic Seizure + Laconic Compression + Dynamic Presence Penalty + Orthogonal Nomadic Retrieval)",
            "recovery_half_life_turns": tau_half,
            "trajectory_curvatures": [round(c, 4) for c in curvatures],
        },
        "prompts": prompts,
        "aaa_agential": evaluated_turns,
    }

    with open(receipt_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    with open(report_dir / "agential_boredom_receipts.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    logger.info("Saved receipts to: %s", receipt_file.resolve())

    # 5. Generate readable markdown transcript
    transcript_file = out_dir / "agential_boredom_transcript.md"
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write("# Agential Boredom Engine Transcript (15 Turns)\n")
        f.write("## Model: `google/gemini-3.7-flash` with Allostatic Agential Boredom Engine\n\n")

        for t in evaluated_turns:
            turn_i = t["turn"]
            f.write(f"### Turn {turn_i}\n")
            f.write(f"**Human User:** {t['user']}\n\n")
            f.write(f"**AAA Agential Assistant:**\n\n{t['apparatus']}\n\n")

            metrics = t.get("metrics", {})
            homeo = t.get("homeostatic", {})
            stagnant_count = homeo.get("consecutive_stagnant_turns", 0)
            p_pen = homeo.get("presence_penalty", {}).get("value", 0.0)
            temp = homeo.get("temperature", {}).get("value", 0.7)

            f.write(
                f"> **Telemetry:** $CP_t$: {metrics.get('collapse_pressure', 'None')}, "
                f"$v_t$: {metrics.get('conceptual_velocity', 'None')}, "
                f"$N_t$: {metrics.get('conceptual_novelty', 'None')}, "
                f"$S_t$: {metrics.get('surprise_index', 'None')}, "
                f"$\\kappa_t$: {metrics.get('trajectory_curvature', 'n/a')}, "
                f"$s_t$: {metrics.get('pairwise_similarity', 'None')}, "
                f"$H_{{pask}}$: {metrics.get('paskian_health', 'None')}, "
                f"State: `{homeo.get('state', 'unknown')}`, "
                f"Stagnant Count: `{stagnant_count}`, P: `{p_pen:.2f}`, T: `{temp:.2f}`\n\n"
            )
            f.write("---\n\n")

    logger.info("Saved transcript to: %s", transcript_file.resolve())

    # 6. Load earlier runs and compute 4-way comparison
    orig_path = out_dir / "conversation_receipts.json"
    prompted_path = out_dir / "prompted_baseline_receipts.json"

    if orig_path.exists() and prompted_path.exists():
        with open(orig_path, "r", encoding="utf-8") as f:
            orig = json.load(f)
        with open(prompted_path, "r", encoding="utf-8") as f:
            pb_data = json.load(f)

        unprompted_turns = orig["baseline"]
        prompted_turns = pb_data["prompted_baseline"]
        prior_aaa_turns = orig["aaa"]
        agential_turns = evaluated_turns

        def mean_metric(turn_list, key):
            vals = [
                t["metrics"].get(key)
                for t in turn_list
                if t.get("metrics") and t["metrics"].get(key) is not None
            ]
            return round(float(sum(vals) / len(vals)), 3) if vals else 0.0

        metrics_def = [
            ("collapse_pressure", "Collapse Pressure (CP_t)", "lower"),
            ("conceptual_velocity", "Conceptual Velocity (v_t)", "higher"),
            ("conceptual_novelty", "Conceptual Novelty (N_t)", "higher"),
            ("surprise_index", "Predictive Surprise (S_t)", "higher"),
            ("pairwise_similarity", "Pairwise Similarity (s_t)", "lower"),
            ("vitality", "Conversational Vitality (V_t)", "higher"),
            ("paskian_health", "Gordon Pask Health (H_pask)", "higher"),
            ("divergence_resolution_ratio", "Divergence Resolution Ratio (DRR)", "higher"),
        ]

        summary_table = []
        logger.info("\n" + "=" * 90)
        logger.info("FOUR-WAY METRICS COMPARISON (Means over 15 turns):")
        logger.info("=" * 90)
        header = f"{'Metric':<35s} | {'Unprompted':<10s} | {'Prompted':<10s} | {'Prior AAA':<10s} | {'Agential AAA':<12s}"
        logger.info(header)
        logger.info("-" * 90)

        for key, name, direction in metrics_def:
            m_unp = mean_metric(unprompted_turns, key)
            m_prm = mean_metric(prompted_turns, key)
            m_aaa = mean_metric(prior_aaa_turns, key)
            m_agn = mean_metric(agential_turns, key)

            row = {
                "metric_key": key,
                "name": name,
                "preferred_direction": direction,
                "unprompted_baseline": m_unp,
                "prompted_baseline": m_prm,
                "prior_aaa": m_aaa,
                "agential_aaa": m_agn,
            }
            summary_table.append(row)
            logger.info(f"{name:<35s} | {m_unp:<10.3f} | {m_prm:<10.3f} | {m_aaa:<10.3f} | {m_agn:<12.3f}")

        logger.info("=" * 90)

        four_way_file = out_dir / "four_way_metrics_summary.json"
        with open(four_way_file, "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "recovery_half_life": tau_half,
                "summary": summary_table,
            }, f, indent=2)
        with open(report_dir / "four_way_metrics_summary.json", "w", encoding="utf-8") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "recovery_half_life": tau_half,
                "summary": summary_table,
            }, f, indent=2)


if __name__ == "__main__":
    main()
