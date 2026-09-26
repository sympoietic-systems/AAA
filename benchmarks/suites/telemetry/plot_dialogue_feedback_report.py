"""Render the human-readable figures for dialogue feedback Report 019."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUN = ROOT / "benchmarks" / "runs" / "telemetry" / "dialogue_feedback_20260926_040006"
DEFAULT_OUTPUT = ROOT / "docs" / "reports" / "019-dialogue-feedback-control"

CYAN = "#22d3ee"
ORANGE = "#fb923c"
GREEN = "#4ade80"
RED = "#fb7185"
PURPLE = "#c084fc"
GRID = "#334155"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"


def _setup() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#050505",
            "axes.facecolor": "#050505",
            "savefig.facecolor": "#050505",
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "axes.titlecolor": TEXT,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": TEXT,
            "font.family": "DejaVu Sans",
            "font.size": 10,
        }
    )


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _turn_series(runs: list[dict[str, Any]], policy: str, key: str) -> np.ndarray:
    rows = []
    for run in runs:
        if run["policy"] == policy:
            rows.append(
                [float(value) if (value := turn["metrics"].get(key)) is not None else np.nan for turn in run["turns"]]
            )
    return np.asarray(rows)


def _control_series(runs: list[dict[str, Any]], policy: str, key: str) -> np.ndarray:
    rows = []
    for run in runs:
        if run["policy"] == policy:
            values = []
            for receipt in run["causal_receipts"]:
                value = receipt["requested_controls"].get(key)
                if key == "reasoning_effort":
                    value = {"low": 0.0, "medium": 0.5, "high": 1.0}.get(value, 0.5)
                values.append(float(value or 0.0))
            rows.append(values)
    return np.asarray(rows)


def _plot_mean(ax: Any, data: np.ndarray, color: str, label: str) -> None:
    turns = np.arange(1, data.shape[1] + 1)
    avg = np.full(data.shape[1], np.nan)
    low = np.full(data.shape[1], np.nan)
    high = np.full(data.shape[1], np.nan)
    populated = ~np.all(np.isnan(data), axis=0)
    avg[populated] = np.nanmean(data[:, populated], axis=0)
    low[populated] = np.nanmin(data[:, populated], axis=0)
    high[populated] = np.nanmax(data[:, populated], axis=0)
    ax.plot(turns, avg, color=color, marker="o", linewidth=2.2, label=label)
    ax.fill_between(turns, low, high, color=color, alpha=0.12)


def _finish_axis(ax: Any, title: str, ylabel: str) -> None:
    ax.set_title(title, loc="left", fontweight="bold", pad=10)
    ax.set_xlabel("Conversation turn")
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(1, 9))
    ax.grid(color=GRID, alpha=0.45, linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)


def plot_dialogue_trajectories(runs: list[dict[str, Any]], output: Path) -> None:
    panels = [
        ("boringness", "Boringness", "higher = more repetition"),
        ("divergence_resolution_ratio", "Divergence resolution ratio", "higher = tension resolved"),
        ("paskian_health", "Paskian dialogue health", "higher = healthier coupling"),
        ("conceptual_velocity", "Conceptual velocity", "semantic movement"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    for ax, (key, title, ylabel) in zip(axes.flat, panels, strict=True):
        _plot_mean(ax, _turn_series(runs, "legacy", key), ORANGE, "Legacy")
        _plot_mean(ax, _turn_series(runs, "progressive", key), CYAN, "Progressive")
        _finish_axis(ax, title, ylabel)
        ax.set_ylim(-0.03, 1.03)
    axes[0, 0].legend(frameon=False, ncol=2, loc="upper right")
    fig.suptitle("What happened inside the dialogue", fontsize=18, fontweight="bold", x=0.06, ha="left")
    fig.text(
        0.06,
        0.935,
        "Lines are turn means across three conversations; shaded regions show the observed repetition range.",
        color=MUTED,
    )
    fig.tight_layout(rect=(0.04, 0.03, 0.98, 0.91))
    fig.savefig(output / "dialogue-metric-trajectories.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_control_trajectories(runs: list[dict[str, Any]], output: Path) -> None:
    panels = [
        ("temperature", "Requested temperature", "temperature"),
        ("presence_penalty", "Requested presence penalty", "penalty"),
        ("max_tokens", "Requested completion budget", "tokens"),
        ("reasoning_effort", "Requested reasoning effort", "0 medium / 1 high"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), sharex=True)
    for ax, (key, title, ylabel) in zip(axes.flat, panels, strict=True):
        _plot_mean(ax, _control_series(runs, "legacy", key), ORANGE, "Legacy")
        _plot_mean(ax, _control_series(runs, "progressive", key), CYAN, "Progressive")
        _finish_axis(ax, title, ylabel)
    axes[0, 0].legend(frameon=False, ncol=2, loc="upper right")
    fig.suptitle("What the controller asked the model to change", fontsize=18, fontweight="bold", x=0.06, ha="left")
    fig.text(
        0.06,
        0.935,
        "Requested values from causal receipts. Some sampling fields were unsupported on reasoning-enabled turns.",
        color=MUTED,
    )
    fig.tight_layout(rect=(0.04, 0.03, 0.98, 0.91))
    fig.savefig(output / "control-parameter-trajectories.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_causal_summary(runs: list[dict[str, Any]], scorecard: dict[str, Any], output: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    keys = ["mean_uptake", "mean_task_progress", "mean_drr", "mean_paskian_health", "mean_collapse_pressure"]
    labels = ["Uptake", "Task progress", "DRR", "Paskian health", "Collapse pressure"]
    delta = scorecard["progressive_minus_legacy"]
    values = [delta[key]["mean"] for key in keys]
    lows = [delta[key]["mean"] - delta[key]["ci_low"] for key in keys]
    highs = [delta[key]["ci_high"] - delta[key]["mean"] for key in keys]
    colors = [
        GREEN if value > 0 and key != "mean_collapse_pressure" else RED for key, value in zip(keys, values, strict=True)
    ]
    y = np.arange(len(keys))
    axes[0].barh(y, values, color=colors, alpha=0.85)
    axes[0].errorbar(values, y, xerr=[lows, highs], fmt="none", ecolor=TEXT, capsize=4, linewidth=1.2)
    axes[0].axvline(0, color=TEXT, linewidth=1)
    axes[0].set_yticks(y, labels)
    axes[0].invert_yaxis()
    axes[0].set_title("Progressive − legacy effect", loc="left", fontweight="bold")
    axes[0].set_xlabel("Paired mean difference with 95% bootstrap interval")
    axes[0].grid(axis="x", color=GRID, alpha=0.45)
    axes[0].spines[["top", "right"]].set_visible(False)

    modes: dict[str, Counter[str]] = defaultdict(Counter)
    for run in runs:
        for receipt in run["causal_receipts"]:
            modes[run["policy"]][receipt["intervention"]["mode"]] += 1
    names = sorted(set(modes["legacy"]) | set(modes["progressive"]))
    x = np.arange(len(names))
    width = 0.36
    axes[1].bar(x - width / 2, [modes["legacy"][name] for name in names], width, color=ORANGE, label="Legacy")
    axes[1].bar(
        x + width / 2,
        [modes["progressive"][name] for name in names],
        width,
        color=CYAN,
        label="Progressive",
    )
    axes[1].set_xticks(x, names, rotation=25, ha="right")
    axes[1].set_ylabel("Selections across 24 turns")
    axes[1].set_title("Which intervention modes actually fired", loc="left", fontweight="bold")
    axes[1].grid(axis="y", color=GRID, alpha=0.45)
    axes[1].spines[["top", "right"]].set_visible(False)
    axes[1].legend(frameon=False)

    fig.suptitle(
        "Did the changed controller improve the conversation?", fontsize=18, fontweight="bold", x=0.05, ha="left"
    )
    fig.text(0.05, 0.91, "Uptake rose, but task progress did not; collapse pressure worsened.", color=MUTED)
    fig.tight_layout(rect=(0.03, 0.02, 0.98, 0.88))
    fig.savefig(output / "causal-effect-and-interventions.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    runs = _load(args.run_dir / "telemetry_receipts.json")
    scorecard = _load(args.run_dir / "scorecard.json")
    _setup()
    plot_dialogue_trajectories(runs, args.output_dir)
    plot_control_trajectories(runs, args.output_dir)
    plot_causal_summary(runs, scorecard, args.output_dir)


if __name__ == "__main__":
    main()
