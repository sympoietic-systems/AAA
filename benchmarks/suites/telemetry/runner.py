"""
Telemetry benchmark runner: orchestrates live AI tests, offline evaluations, and differential comparisons.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from sentence_transformers import SentenceTransformer

from benchmarks.common.base import BaseBenchmarkSuite
from benchmarks.common.storage import (
    create_run_directory,
    get_git_commit,
    save_run_metadata,
    setup_run_logger,
)
from benchmarks.common.loader import (
    DialogueDataset,
    load_dataset,
    resolve_embeddings,
)
from .evaluator import compute_statistics, evaluate_sequence
from .comparator import compare_runs
from .visualizer import (
    plot_boredom_separation_dashboard,
    plot_quartile_stability,
    plot_telemetry_oscilloscope,
    render_14_panel_comparison_dashboard,
    render_single_audit_dashboard,
)
from .live import (
    DEFAULT_PROMPTS,
    compute_metrics_for_turns,
    run_aaa_apparatus,
    run_baseline_llm,
)


class TelemetryBenchmarkSuite(BaseBenchmarkSuite):
    """14-dimension cybernetic telemetry benchmark suite."""

    @property
    def name(self) -> str:
        return "telemetry"

    @property
    def description(self) -> str:
        return "14-dimension cybernetic viability, allostasis, Paskian health, and phase shifts."

    @staticmethod
    def evaluate(
        dataset_path: Path | str,
        target_node: Optional[int] = None,
        longest_path: bool = False,
        name: str = "",
        out_dir: Optional[Path] = None,
        phase_threshold: float = 0.35,
    ) -> Dict[str, Any]:
        """Offline evaluation of a dialogue dataset."""
        t0 = time.time()
        dataset = load_dataset(Path(dataset_path), target_node=target_node, longest_path=longest_path)
        effective_name = name or dataset.name

        if out_dir is None:
            out_dir = create_run_directory("telemetry", "eval", custom_name=effective_name)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_run_logger(out_dir)
        logger.info("=" * 70)
        logger.info("CYBERNETIC TELEMETRY EVALUATION: %s", effective_name)
        logger.info("Dataset: %s (%d messages)", dataset.filepath.name, len(dataset.messages))
        logger.info("Output Directory: %s", out_dir)
        logger.info("Git Commit: %s", get_git_commit())
        logger.info("=" * 70)

        # Step 1: Embeddings
        logger.info("Step 1/4: Resolving dense embeddings...")
        embeddings = resolve_embeddings(dataset, cache_dir=out_dir)
        logger.info("Embeddings ready (shape: %s).", str(embeddings.shape))

        # Step 2: Telemetry evaluation
        logger.info("Step 2/4: Computing 14-dimension cybernetic telemetry...")
        msg_dicts = [{"id": m.id, "parent_message_id": m.parent_id, "speaker": m.speaker, "content": m.content, "timestamp": m.created_at} for m in dataset.messages]
        results = evaluate_sequence(msg_dicts, embeddings, phase_threshold=phase_threshold)
        stats = compute_statistics(results)

        logger.info("Evaluated %d turns. Flowing: %.1f%%, Phase Shifts: %d", len(results), stats["regimes"]["flowing_pct"], stats["total_phase_shifts"])

        # Receipts
        receipts_file = out_dir / "telemetry_receipts.json"
        with open(receipts_file, "w", encoding="utf-8") as f:
            json.dump({
                "dataset_name": dataset.name,
                "total_turns": len(results),
                "is_branched": dataset.is_branched,
                "selected_node": dataset.selected_node,
                "turns": results,
            }, f, indent=2)
        logger.info("Saved telemetry receipts: %s", receipts_file.name)

        # Step 3: Cyberpunk Visualizations
        logger.info("Step 3/4: Generating restrained cyberpunk visualizations...")
        plot_path = out_dir / "telemetry_oscilloscope.png"
        plot_telemetry_oscilloscope(dataset.name, results, plot_path)
        render_single_audit_dashboard(dataset.name, results, out_dir, custom_name="telemetry_audit_dashboard")

        if len(results) >= 40:
            quartile_path = out_dir / "quartile_stability.png"
            plot_quartile_stability(dataset.name, results, quartile_path)

        # Step 4: Executive summary markdown
        logger.info("Step 4/4: Writing executive summary report...")
        summary_file = out_dir / "summary.md"
        _write_eval_summary(dataset, stats, results, summary_file, plot_path.name)

        duration = round(time.time() - t0, 2)
        meta = {
            "run_id": out_dir.name,
            "suite": "telemetry",
            "run_type": "eval",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": get_git_commit(),
            "dataset": str(dataset.filepath),
            "custom_name": effective_name,
            "turns": len(results),
            "duration_seconds": duration,
        }
        save_run_metadata(out_dir, meta)
        logger.info("Evaluation completed in %.2fs. Artifacts saved in %s\n", duration, out_dir.name)

        return {
            "run_dir": out_dir,
            "dataset": dataset,
            "results": results,
            "statistics": stats,
            "metadata": meta,
        }

    @staticmethod
    def compare(
        run_a: Path | str,
        run_b: Path | str,
        name: str = "",
        out_dir: Optional[Path] = None,
        delta_threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """Differential comparison between two runs or receipt files."""
        t0 = time.time()
        turns_a, name_a = _load_receipt_turns(run_a)
        turns_b, name_b = _load_receipt_turns(run_b)
        effective_name = name or f"{name_a}_vs_{name_b}"

        if out_dir is None:
            if name:
                out_dir = create_run_directory("telemetry", "compare", custom_name=name)
            else:
                out_dir = create_run_directory("telemetry", "compare", custom_name=name_a, secondary_name=name_b)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_run_logger(out_dir)
        logger.info("=" * 70)
        logger.info("DIFFERENTIAL TELEMETRY COMPARISON: %s vs. %s", name_a, name_b)
        logger.info("Output Directory: %s", out_dir)
        logger.info("Git Commit: %s", get_git_commit())
        logger.info("=" * 70)

        # Step 1: Metric deltas
        logger.info("Step 1/3: Analyzing differential metrics...")
        comparison = compare_runs(turns_a, turns_b, delta_threshold=delta_threshold)
        changed = comparison["changed_metrics"]
        logger.info("Identified %d metrics with significant shift (|Delta| >= %.2f):", len(changed), delta_threshold)
        for m in changed:
            logger.info("  * %s: Before=%.3f -> Now=%.3f (Delta=%+.3f, %+.1f%%)", m.label, m.mean_a, m.mean_b, m.delta, m.pct_change)

        # Step 2: 14-Panel Dashboard
        logger.info("Step 2/3: Plotting differential changes (same hue: dotted Before, solid Now)...")
        render_14_panel_comparison_dashboard(
            run_a_name=name_a,
            run_b_name=name_b,
            turns_a=turns_a,
            turns_b=turns_b,
            comparison=comparison,
            out_dir=out_dir,
            custom_name="differential_changes",
        )

        # Step 3: Markdown report
        logger.info("Step 3/3: Writing comparison summary report...")
        summary_file = out_dir / "comparison_summary.md"
        _write_compare_summary(name_a, name_b, comparison, turns_a, turns_b, summary_file)

        duration = round(time.time() - t0, 2)
        meta = {
            "run_id": out_dir.name,
            "suite": "telemetry",
            "run_type": "compare",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "git_commit": get_git_commit(),
            "run_a": str(run_a),
            "run_b": str(run_b),
            "custom_name": effective_name,
            "changed_metrics_count": len(changed),
            "duration_seconds": duration,
        }
        save_run_metadata(out_dir, meta)
        logger.info("Comparison completed in %.2fs. Artifacts saved in %s\n", duration, out_dir.name)

        return {
            "run_dir": out_dir,
            "comparison": comparison,
            "metadata": meta,
        }

    @staticmethod
    def live(
        model: str = "google/gemini-2.5-flash",
        turns: int = 10,
        prompts_file: Optional[Path | str] = None,
        name: str = "",
        out_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Live 10-turn adversarial AI pressure test: Baseline LLM vs. AAA Apparatus."""
        t0 = time.time()
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        api_base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for live baseline testing.")

        if prompts_file:
            with open(prompts_file, "r", encoding="utf-8") as f:
                prompts = json.load(f)
        else:
            prompts = DEFAULT_PROMPTS[:turns]

        model_slug = model.split("/")[-1].replace(".", "")
        effective_name = name or f"live_{model_slug}"

        if out_dir is None:
            out_dir = create_run_directory("telemetry", "live", custom_name=effective_name, secondary_name=model_slug)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_run_logger(out_dir)
        logger.info("=" * 70)
        logger.info("LIVE CYBERNETIC BENCHMARK: AAA vs. Baseline LLM (%s)", model)
        logger.info("Turns: %d | Output Directory: %s", len(prompts), out_dir)
        logger.info("=" * 70)

        # 1. Run Baseline LLM
        logger.info("[1/4] Running Baseline LLM Control...")
        baseline_results = run_baseline_llm(prompts, model, api_key, api_base)

        # 2. Run AAA Apparatus
        logger.info("[2/4] Running AAA Cognitive Apparatus...")
        aaa_results = run_aaa_apparatus(prompts)

        # 3. Compute 14-dimension telemetry
        logger.info("[3/4] Computing 14-dimension cybernetic metrics...")
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
        baseline_turns = asyncio.run(compute_metrics_for_turns(baseline_results, embedder, speaker_agent_key="assistant"))
        aaa_turns = asyncio.run(compute_metrics_for_turns(aaa_results, embedder, speaker_agent_key="apparatus"))

        # Save receipts
        receipts_path = out_dir / "conversation_receipts.json"
        with open(receipts_path, "w", encoding="utf-8") as f:
            json.dump({
                "metadata": {
                    "model": model,
                    "turns": len(prompts),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "git_commit": get_git_commit(),
                },
                "prompts": prompts,
                "baseline": baseline_turns,
                "aaa": aaa_turns,
            }, f, indent=2)
        logger.info("Saved conversation receipts: %s", receipts_path.name)

        # 4. Compare & Render 14-Panel Cyberpunk Dashboard
        logger.info("[4/4] Rendering Head-to-Head 14-Panel Dashboard...")
        comparison = compare_runs(baseline_turns, aaa_turns)
        render_14_panel_comparison_dashboard(
            run_a_name=f"Baseline_{model_slug}",
            run_b_name="AAA_Apparatus",
            turns_a=baseline_turns,
            turns_b=aaa_turns,
            comparison=comparison,
            out_dir=out_dir,
            custom_name="live_benchmark_dashboard",
        )

        summary_file = out_dir / "live_report.md"
        _write_compare_summary(f"Baseline ({model})", "AAA Apparatus", comparison, baseline_turns, aaa_turns, summary_file)

        duration = round(time.time() - t0, 2)
        meta = {
            "run_id": out_dir.name,
            "suite": "telemetry",
            "run_type": "live",
            "model": model,
            "turns": len(prompts),
            "duration_seconds": duration,
        }
        save_run_metadata(out_dir, meta)
        logger.info("Live benchmark successfully completed in %.2fs. Saved in %s\n", duration, out_dir.name)

        return {
            "run_dir": out_dir,
            "baseline": baseline_turns,
            "aaa": aaa_turns,
            "comparison": comparison,
            "metadata": meta,
        }

    @staticmethod
    def boredom_eval(
        focus_path: Optional[Path | str] = None,
        loop_path: Optional[Path | str] = None,
        name: str = "",
        out_dir: Optional[Path] = None,
        boredom_key: str = "collapse_pressure",
        alarm_threshold: float = 0.60,
    ) -> Dict[str, Any]:
        """Offline evaluation of boredom discriminability across Deep Focus and Sycophantic Loop."""
        t0 = time.time()
        fixtures_dir = Path(__file__).resolve().parents[2] / "data" / "dialogues" / "boredom"
        f_path = Path(focus_path) if focus_path else (fixtures_dir / "deep_focus_40t.json")
        l_path = Path(loop_path) if loop_path else (fixtures_dir / "thesaurus_loop_30t.json")

        focus_dataset = load_dataset(f_path)
        loop_dataset = load_dataset(l_path)
        effective_name = name or "boredom_eval"

        if out_dir is None:
            out_dir = create_run_directory("telemetry", "eval", custom_name=effective_name)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_run_logger(out_dir)
        logger.info("=" * 70)
        logger.info("CYBERNETIC BOREDOM DISCRIMINABILITY EVALUATION: %s", effective_name)
        logger.info("Focus Dataset: %s (%d turns)", f_path.name, len(focus_dataset.messages))
        logger.info("Loop Dataset: %s (%d turns)", l_path.name, len(loop_dataset.messages))
        logger.info("Output Directory: %s", out_dir)
        logger.info("=" * 70)

        # 1. Resolve Embeddings (uses companion .npy cache if present)
        logger.info("[1/3] Resolving dense embeddings...")
        focus_embs = resolve_embeddings(focus_dataset, cache_dir=out_dir)
        loop_embs = resolve_embeddings(loop_dataset, cache_dir=out_dir)

        # 2. Evaluate telemetry sequence
        logger.info("[2/3] Evaluating cybernetic metrics for both corpora...")
        focus_msgs = [{"id": m.id, "parent_message_id": m.parent_id, "speaker": m.speaker, "content": m.content, "timestamp": m.created_at} for m in focus_dataset.messages]
        loop_msgs = [{"id": m.id, "parent_message_id": m.parent_id, "speaker": m.speaker, "content": m.content, "timestamp": m.created_at} for m in loop_dataset.messages]

        focus_results = evaluate_sequence(focus_msgs, focus_embs)
        loop_results = evaluate_sequence(loop_msgs, loop_embs)

        # 3. Compute Boredom Discriminability Metrics
        from .boredom_evaluator import evaluate_boredom_discriminability

        boredom_metrics = evaluate_boredom_discriminability(
            focus_turns=focus_results,
            loop_turns=loop_results,
            focus_embeddings=focus_embs,
            loop_embeddings=loop_embs,
            boredom_key=boredom_key,
            alarm_threshold=alarm_threshold,
        )

        logger.info(
            "Separation Margin: %+.3f | Cohen's d: %.2f | FP Rate (Focus): %.1f%% | FN Rate (Loop): %.1f%%",
            boredom_metrics["discriminability"]["separation_margin"],
            boredom_metrics["discriminability"]["cohens_d"],
            boredom_metrics["focus_corpus"]["false_positive_rate"],
            boredom_metrics["loop_corpus"]["false_negative_rate"],
        )

        # 4. Save Receipts & Visualizations
        scorecard_file = out_dir / "boredom_scorecard.json"
        with open(scorecard_file, "w", encoding="utf-8") as f:
            json.dump({
                "run_id": out_dir.name,
                "focus_dataset": f_path.name,
                "loop_dataset": l_path.name,
                "metrics": boredom_metrics,
                "focus_turns": focus_results,
                "loop_turns": loop_results,
            }, f, indent=2)

        plot_path = out_dir / "boredom_separation_dashboard.png"
        plot_boredom_separation_dashboard(focus_results, loop_results, plot_path, boredom_key=boredom_key, alarm_threshold=alarm_threshold)

        # Write markdown summary
        summary_file = out_dir / "boredom_report.md"
        _write_boredom_summary(boredom_metrics, out_dir.name, summary_file)

        duration = round(time.time() - t0, 2)
        logger.info("Boredom evaluation completed in %.2fs. Artifacts saved in %s\n", duration, out_dir.name)

        return {
            "out_dir": out_dir,
            "boredom_metrics": boredom_metrics,
            "duration": duration,
        }

    @staticmethod
    def boredom_probe(
        model: str = "google/gemini-2.5-flash",
        mock_mode: bool = False,
        name: str = "",
        out_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Runs the 2-call counterfactual branching probe."""
        from .boredom_branching import run_counterfactual_probe

        effective_name = name or "boredom_probe"
        if out_dir is None:
            out_dir = create_run_directory("telemetry", "live", custom_name=effective_name)
        else:
            out_dir.mkdir(parents=True, exist_ok=True)

        logger = setup_run_logger(out_dir)
        logger.info("=" * 70)
        logger.info("COUNTERFACTUAL BOREDOM BRANCHING PROBE: %s", model)
        logger.info("Output Directory: %s", out_dir)
        logger.info("=" * 70)

        receipt = asyncio.run(run_counterfactual_probe(
            model=model,
            mock_mode=mock_mode,
            out_dir=out_dir,
        ))

        logger.info("Refusal Result: %s (C_cap=%.2f, Angle=%.1f deg)",
                    receipt["probe_summary"]["agential_resistance"],
                    receipt["turn_7_probe"]["capitulation_index"],
                    receipt["turn_7_probe"]["deflection_angle_deg"])
        logger.info("Recovery Result: %s (Post-Accommodation Flowing: %s)",
                    receipt["probe_summary"]["post_refusal_recovery"],
                    receipt["turn_8_probe"]["recovered_to_flow"])

        return receipt


def _load_receipt_turns(path_or_dir: Path | str) -> Tuple[List[Dict[str, Any]], str]:
    """Extracts turn records from a run directory or JSON receipt file."""
    p = Path(path_or_dir)
    if p.is_dir():
        for candidate in ["telemetry_receipts.json", "conversation_receipts.json"]:
            cp = p / candidate
            if cp.exists():
                p = cp
                break

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data, p.stem

    if isinstance(data, dict):
        if "turns" in data:
            return data["turns"], data.get("dataset_name") or p.parent.name
        if "aaa" in data:
            return data["aaa"], "AAA_Apparatus"
        if "baseline" in data:
            return data["baseline"], "Baseline_LLM"
        if "messages" in data:
            return data["messages"], p.stem

    raise ValueError(f"Could not extract turn metrics from '{path_or_dir}'.")


def _write_eval_summary(dataset: DialogueDataset, stats: Dict[str, Any], results: List[Dict[str, Any]], out_path: Path, plot_filename: str):
    """Generates human- and LLM-scannable markdown summary."""
    lines = [
        f"# Cybernetic Telemetry Audit: {dataset.name}",
        "",
        f"- **Dataset Path:** `{dataset.filepath}`",
        f"- **Total Evaluated Turns:** {len(results)}",
        f"- **Branched Conversation:** {dataset.is_branched} (Selected Node: {dataset.selected_node})",
        f"- **Homeostatic Regimes:** Flowing {stats['regimes']['flowing_pct']}% | Stagnant {stats['regimes']['stagnant_pct']}% | Disrupted {stats['regimes']['disrupted_pct']}%",
        f"- **Phase Shift Events:** {stats['total_phase_shifts']}",
        "",
        "## Metric Distributions (14 Calibrated Dimensions)",
        "",
        "| Metric Dimension | Mean | Std | Min | Median | Max |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for key in stats:
        s = stats[key]
        if isinstance(s, dict) and "mean" in s:
            lines.append(f"| `{key}` | {s['mean']:.3f} | {s['std']:.3f} | {s['min']:.3f} | {s['median']:.3f} | {s['max']:.3f} |")

    lines.extend([
        "",
        f"## Visualization",
        f"![Telemetry Oscilloscope]({plot_filename})",
        f"See also: `telemetry_audit_dashboard.png` (14-panel card grid).",
    ])
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_compare_summary(name_a: str, name_b: str, comparison: Dict[str, Any], turns_a: List[dict], turns_b: List[dict], out_path: Path):
    """Generates comparison markdown summary highlighting metrics that changed."""
    changed = comparison["changed_metrics"]
    stable = comparison["stable_metrics"]

    lines = [
        f"# Differential Telemetry Comparison: {name_a} vs. {name_b}",
        "",
        f"- **Run A (Before):** `{name_a}` ({len(turns_a)} turns)",
        f"- **Run B (Now):** `{name_b}` ({len(turns_b)} turns)",
        f"- **Metrics with Significant Shift (|Δ| >= 0.05):** {len(changed)}",
        "",
        "## Metrics That Changed",
        "",
        "| Metric | Before (Mean) | Now (Mean) | Delta (Δ) | % Change | Shift Significance |",
        "| :--- | :---: | :---: | :---: | :---: | :---: |",
    ]
    for d in changed:
        sign = "+" if d.delta >= 0 else ""
        lines.append(f"| **{d.label}** | {d.mean_a:.3f} | {d.mean_b:.3f} | **{sign}{d.delta:.3f}** | {sign}{d.pct_change:.1f}% | 🚨 SIGNIFICANT |")

    if stable:
        lines.extend([
            "",
            "## Stable Telemetry Dimensions",
            "",
            "| Metric | Before | Now | Delta (Δ) | % Change |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ])
        for d in stable:
            sign = "+" if d.delta >= 0 else ""
            lines.append(f"| {d.label} | {d.mean_a:.3f} | {d.mean_b:.3f} | {sign}{d.delta:.3f} | {sign}{d.pct_change:.1f}% |")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _write_boredom_summary(metrics: Dict[str, Any], run_id: str, out_path: Path):
    """Generates an executive summary markdown report for boredom discriminability."""
    disc = metrics["discriminability"]
    f = metrics["focus_corpus"]
    l = metrics["loop_corpus"]
    status = "CLEAN SEPARATION (PASSED)" if disc["separated_cleanly"] else "DISCRIMINATION WARNING (OVERLAP)"

    lines = [
        f"# Cybernetic Boredom Discriminability Report: {run_id}",
        "",
        f"> **Evaluation Status:** `{status}`  ",
        f"> **Metric Dimension:** `{metrics['metric_key']}`  ",
        f"> **Alarm Threshold:** `{metrics['alarm_threshold']}`  ",
        "",
        "## 1. Executive Summary",
        "",
        f"- **Separation Margin (Delta_sep):** `{disc['separation_margin']:+.3f}` (Positive margin guarantees zero false alarms)",
        f"- **Cohen's d Effect Size:** `{disc['cohens_d']:.2f}` (Effect size > 2.0 indicates massive distribution divergence)",
        f"- **Effective Contrast:** `{disc['effective_contrast']:+.3f}` (Average separation between Stagnant Loop and Deep Focus)",
        "",
        "## 2. Corpus Scorecard Comparison",
        "",
        "| Metric Criterion | Deep Technical Focus (40T) | Sycophantic Loop (30T) | Ideal Target |",
        "| :--- | :---: | :---: | :---: |",
        f"| **Turns Evaluated** | {f['turns_count']} | {l['turns_count']} | >= 30 |",
        f"| **Distribution (Mean +/- Std)** | {f['mean']:.3f} +/- {f['std']:.3f} | {l['mean']:.3f} +/- {l['std']:.3f} | Focus < 0.35, Loop > 0.70 |",
        f"| **Range [Min, Max]** | [{f['min']:.3f}, {f['max']:.3f}] | [{l['min']:.3f}, {l['max']:.3f}] | Non-overlapping |",
        f"| **False Alarm / Error Rate** | **{f['false_positive_rate']:.1f}%** (False Positive) | **{l['false_negative_rate']:.1f}%** (False Negative) | < 5.0% |",
        f"| **Residual Spectral Rank (D_eff)** | **{f['residual_spectral_rank']:.2f}** | **{l['residual_spectral_rank']:.2f}** | Focus >= 3.0, Loop <= 1.5 |",
        f"| **Recurrence Determinism (DET)** | {f['recurrence_determinism']:.3f} | {l['recurrence_determinism']:.3f} | Focus <= 0.25, Loop >= 0.70 |",
        "",
        "## 3. Visualization Artifact",
        "",
        "![Boredom Separation Dashboard](boredom_separation_dashboard.png)",
        "",
    ]
    with open(out_path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))

