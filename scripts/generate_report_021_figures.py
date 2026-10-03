"""Generate Publication-Grade Figures for Report 021: Long-Horizon Dialogue Feedback Scenarios."""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = PROJECT_ROOT / "benchmarks" / "runs" / "telemetry" / "dialogue_feedback_20261002_165403"
OUT_DIR = PROJECT_ROOT / "docs" / "reports" / "021-long-horizon-dialogue-scenarios"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Load Scorecard and Receipts
scorecard = json.loads((RUN_DIR / "scorecard.json").read_text(encoding="utf-8"))
receipts = json.loads((RUN_DIR / "telemetry_receipts.json").read_text(encoding="utf-8"))

plt.style.use("dark_background")

# --------------------------------------------------------------------------------------------------
# Figure 1: Master Scorecard Metrics Comparison (Legacy vs Paskian)
# --------------------------------------------------------------------------------------------------
def generate_metric_comparison_figure():
    arms = scorecard["arms"]
    legacy = arms["legacy"]
    paskian = arms["paskian"]

    metrics = [
        "mean_drr",
        "mean_paskian_health",
        "mean_collapse_pressure",
        "mean_conceptual_velocity",
        "control_observability_rate",
    ]
    labels = [
        "DRR\n(Resolution)",
        "Paskian\nHealth ($H_{pask}$)",
        "Collapse\nPressure ($CP_t$)",
        "Conceptual\nVelocity ($v_t$)",
        "Control\nObservability",
    ]

    legacy_vals = [legacy[m]["mean"] for m in metrics]
    paskian_vals = [paskian[m]["mean"] for m in metrics]

    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    x = np.arange(len(metrics))
    width = 0.35

    rects1 = ax.bar(x - width/2, legacy_vals, width, label="Legacy Controller Arm", color="#ff7043", alpha=0.9, edgecolor="#ffab91")
    rects2 = ax.bar(x + width/2, paskian_vals, width, label="Paskian Controller Arm (ADR-098)", color="#00e676", alpha=0.9, edgecolor="#b9f6ca")

    ax.set_ylabel("Telemetry Score / Ratio", fontsize=11, fontweight="bold", color="#f0f0f0")
    ax.set_title("20-Turn Long-Horizon Dialogue Benchmark: Legacy vs Paskian Controller\nScenario: sync_distributed_lock (Model: Nemotron-3 Super 120B)",
                 fontsize=12, fontweight="bold", pad=15, color="#ffffff")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, color="#dddddd")
    ax.legend(frameon=True, facecolor="#1e1e1e", edgecolor="#424242", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.25, color="#888888")
    ax.set_ylim(0, 1.20)

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#ffffff")

    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#ffffff")

    plt.tight_layout()
    target_path = OUT_DIR / "fig1_metrics_comparison.png"
    plt.savefig(target_path, dpi=300)
    plt.close()
    print(f"Saved: {target_path}")

# --------------------------------------------------------------------------------------------------
# Figure 2: 20-Turn Multi-Trajectory Dynamics (DRR, Paskian Health, Collapse Pressure)
# --------------------------------------------------------------------------------------------------
def generate_trajectory_figure():
    # Extract R1 trajectories
    paskian_r1 = next(r for r in receipts if r["policy"] == "paskian" and r["repetition"] == 1)
    legacy_r1 = next(r for r in receipts if r["policy"] == "legacy" and r["repetition"] == 1)

    p_turns = [turn["turn"] for turn in paskian_r1["turns"]]
    l_turns = [turn["turn"] for turn in legacy_r1["turns"]]

    # Helper to get metric safely
    def get_series(run, metric_key):
        return [turn["metrics"].get(metric_key) or 0.5 for turn in run["turns"]]

    p_drr = get_series(paskian_r1, "divergence_resolution_ratio")
    l_drr = get_series(legacy_r1, "divergence_resolution_ratio")

    p_pask = get_series(paskian_r1, "paskian_health")
    l_pask = get_series(legacy_r1, "paskian_health")

    p_vel = get_series(paskian_r1, "conceptual_velocity")
    l_vel = get_series(legacy_r1, "conceptual_velocity")

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), dpi=300, sharex=True)

    # Subplot 1: Divergence Resolution Ratio (DRR)
    ax1.plot(p_turns, p_drr, marker="o", color="#00e676", linewidth=2.2, label="Paskian (ADR-098) DRR")
    ax1.plot(l_turns, l_drr, marker="s", color="#ff7043", linewidth=2.0, linestyle="--", label="Legacy DRR")
    ax1.axhline(0.5, color="#888888", linestyle=":", alpha=0.6, label="Neutral Threshold (0.50)")
    ax1.set_ylabel("DRR", fontsize=10, fontweight="bold", color="#e0e0e0")
    ax1.set_title("Long-Horizon Telemetry Trajectory Across Conversational Turns (Repetition 1)", fontsize=13, fontweight="bold", pad=12, color="#ffffff")
    ax1.legend(loc="upper right", facecolor="#1e1e1e", edgecolor="#424242", fontsize=9)
    ax1.grid(True, linestyle="--", alpha=0.25)
    ax1.set_ylim(0.2, 1.05)

    # Subplot 2: Paskian Health (Hpask)
    ax2.plot(p_turns, p_pask, marker="o", color="#40c4ff", linewidth=2.2, label="Paskian Health ($H_{pask}$)")
    ax2.plot(l_turns, l_pask, marker="s", color="#ffd54f", linewidth=2.0, linestyle="--", label="Legacy Paskian Health")
    ax2.set_ylabel("$H_{pask}$", fontsize=10, fontweight="bold", color="#e0e0e0")
    ax2.legend(loc="upper right", facecolor="#1e1e1e", edgecolor="#424242", fontsize=9)
    ax2.grid(True, linestyle="--", alpha=0.25)
    ax2.set_ylim(0.2, 0.7)

    # Subplot 3: Conceptual Velocity (vt)
    ax3.plot(p_turns, p_vel, marker="o", color="#b388ff", linewidth=2.2, label="Paskian Velocity ($v_t$)")
    ax3.plot(l_turns, l_vel, marker="s", color="#ff5252", linewidth=2.0, linestyle="--", label="Legacy Velocity ($v_t$)")
    ax3.set_ylabel("Velocity ($v_t$)", fontsize=10, fontweight="bold", color="#e0e0e0")
    ax3.set_xlabel("Dialogue Turn (1 to 20)", fontsize=11, fontweight="bold", color="#ffffff")
    ax3.legend(loc="upper right", facecolor="#1e1e1e", edgecolor="#424242", fontsize=9)
    ax3.grid(True, linestyle="--", alpha=0.25)
    ax3.set_xticks(list(range(1, 21)))
    ax3.set_ylim(0.3, 1.05)

    plt.tight_layout()
    target_path = OUT_DIR / "fig2_20_turn_trajectories.png"
    plt.savefig(target_path, dpi=300)
    plt.close()
    print(f"Saved: {target_path}")

# --------------------------------------------------------------------------------------------------
# Figure 3: Intervention Distribution & Latency Profiles
# --------------------------------------------------------------------------------------------------
def generate_intervention_and_latency_figure():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    # Panel A: Intervention Distribution in Paskian Arms
    paskian_runs = [r for r in receipts if r["policy"] == "paskian"]
    total_interventions = {}
    for r in paskian_runs:
        for k, v in r["intervention_counts"].items():
            total_interventions[k] = total_interventions.get(k, 0) + v

    labels = list(total_interventions.keys())
    counts = list(total_interventions.values())
    colors = ["#26a69a", "#ab47bc", "#ffa726"][:len(labels)]

    wedges, texts, autotexts = ax1.pie(
        counts, labels=labels, autopct="%1.1f%%", startangle=140,
        colors=colors, textprops=dict(color="#ffffff", fontsize=10),
        wedgeprops=dict(edgecolor="#121212", linewidth=2)
    )
    for at in autotexts:
        at.set_color("#ffffff")
        at.set_fontweight("bold")
    ax1.set_title("Intervention Mode Selection\n(Paskian Controller across 40 turns)", fontsize=11, fontweight="bold", color="#ffffff")

    # Panel B: Mean Response Latency Comparison
    arms = scorecard["arms"]
    legacy_lat = arms["legacy"]["mean_latency_ms"]["mean"] / 1000.0
    paskian_lat = arms["paskian"]["mean_latency_ms"]["mean"] / 1000.0

    bars = ax2.bar(["Legacy Arm", "Paskian Arm"], [legacy_lat, paskian_lat], color=["#ff7043", "#00e676"], width=0.45, edgecolor="#ffffff", linewidth=0.8)
    ax2.set_ylabel("Seconds per Turn", fontsize=10, fontweight="bold", color="#e0e0e0")
    ax2.set_title("Mean Apparatus Response Latency\n(Nemotron-3 Super 120B on NVIDIA NIM)", fontsize=11, fontweight="bold", color="#ffffff")
    ax2.grid(axis="y", linestyle="--", alpha=0.25)
    ax2.set_ylim(0, max(legacy_lat, paskian_lat) * 1.3)

    for bar in bars:
        h = bar.get_height()
        ax2.annotate(f"{h:.2f} s", xy=(bar.get_x() + bar.get_width() / 2, h), xytext=(0, 4),
                     textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#ffffff")

    plt.tight_layout()
    target_path = OUT_DIR / "fig3_interventions_and_latency.png"
    plt.savefig(target_path, dpi=300)
    plt.close()
    print(f"Saved: {target_path}")

if __name__ == "__main__":
    generate_metric_comparison_figure()
    generate_trajectory_figure()
    generate_intervention_and_latency_figure()
    print("All Report 021 figures successfully generated.")
