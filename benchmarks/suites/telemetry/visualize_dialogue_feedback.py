"""Render the dialogue feedback ablation scorecard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, required=True)
    parser.add_argument("--activation", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    scorecard = json.loads(args.scorecard.read_text(encoding="utf-8"))
    activation = json.loads(args.activation.read_text(encoding="utf-8"))
    metrics = [
        ("Uptake", "mean_uptake"),
        ("DRR", "mean_drr"),
        ("Pask health", "mean_paskian_health"),
        ("Collapse", "mean_collapse_pressure"),
        ("Velocity", "mean_conceptual_velocity"),
    ]
    legacy = [scorecard["arms"]["legacy"][key]["mean"] for _, key in metrics]
    progressive = [scorecard["arms"]["progressive"][key]["mean"] for _, key in metrics]

    plt.style.use("dark_background")
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5), facecolor="#000000")
    x_values = np.arange(len(metrics))
    width = 0.36
    axes[0].bar(x_values - width / 2, legacy, width, label="Legacy", color="#ffb000")
    axes[0].bar(x_values + width / 2, progressive, width, label="Progressive", color="#00d084")
    axes[0].set_xticks(x_values, [label for label, _ in metrics], rotation=18, ha="right")
    axes[0].set_ylim(0, 1)
    axes[0].set_title("Live adaptive dialogue: arm means")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="y", alpha=0.18)

    rates = [activation["focus_false_positive_rate"], activation["loop_false_negative_rate"]]
    axes[1].bar(["Focus false positive", "Loop false negative"], rates, color=["#00d084", "#ffb000"])
    axes[1].axhline(10, color="white", linestyle="--", linewidth=1, alpha=0.65, label="10% focus ceiling")
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Rate (%)")
    axes[1].set_title("Adaptive-persistence retrieval gate")
    axes[1].legend(frameon=False)
    axes[1].grid(axis="y", alpha=0.18)

    for axis in axes:
        axis.set_facecolor("#000000")
        axis.spines["top"].set_visible(False)
        axis.spines["right"].set_visible(False)
    figure.suptitle("Dialogue feedback control: accepted gate and rejected intervention ladder", fontsize=14)
    figure.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(args.out, dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


if __name__ == "__main__":
    main()
