"""Generate Publication-Grade Figures for Report 022: Relational Conversational Archetypes."""

import json
from collections import defaultdict
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = PROJECT_ROOT / "benchmarks" / "runs" / "telemetry" / "dialogue_feedback_20261003_004020"
OUT_DIR = PROJECT_ROOT / "docs" / "reports" / "022-relational-conversational-archetypes"
OUT_DIR.mkdir(parents=True, exist_ok=True)

receipts = json.loads((RUN_DIR / "telemetry_receipts.json").read_text(encoding="utf-8"))
scorecard = json.loads((RUN_DIR / "scorecard.json").read_text(encoding="utf-8"))

plt.style.use("dark_background")

# --------------------------------------------------------------------------------------------------
# Figure 1: 5-Archetype Radar / Comparative Bar Matrix (DRR & Collapse Pressure)
# --------------------------------------------------------------------------------------------------
def generate_archetype_matrix_figure():
    archetypes = [
        ("unyielding_conflict", "Conflict\n(Antagonism)"),
        ("constructive_dialectic", "Dialectic\n(Disagreement)"),
        ("stagnant_repetition", "Repetition\n(Semantic Loop)"),
        ("symbiotic_coevolution", "Symbiosis\n(Co-evolution)"),
        ("sycophantic_compliance", "Compliance\n(Echo Chamber)"),
    ]

    grouped = defaultdict(lambda: defaultdict(list))
    for run in receipts:
        scen = run["turns"][0]["scenario_id"]
        pol = run["policy"]
        grouped[scen][pol].append(run)

    drr_legacy = [sum(x["mean_drr"] for x in grouped[scen]["legacy"]) / len(grouped[scen]["legacy"]) for scen, _ in archetypes]
    drr_paskian = [sum(x["mean_drr"] for x in grouped[scen]["paskian"]) / len(grouped[scen]["paskian"]) for scen, _ in archetypes]

    cp_legacy = [sum(x["mean_collapse_pressure"] for x in grouped[scen]["legacy"]) / len(grouped[scen]["legacy"]) for scen, _ in archetypes]
    cp_paskian = [sum(x["mean_collapse_pressure"] for x in grouped[scen]["paskian"]) / len(grouped[scen]["paskian"]) for scen, _ in archetypes]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)
    x = np.arange(len(archetypes))
    width = 0.35

    # Panel A: Divergence Resolution Ratio (DRR)
    ax1.bar(x - width/2, drr_legacy, width, label="Legacy Controller", color="#ff7043", alpha=0.9, edgecolor="#ffab91")
    ax1.bar(x + width/2, drr_paskian, width, label="Paskian Controller (ADR-098)", color="#00e676", alpha=0.9, edgecolor="#b9f6ca")
    ax1.set_ylabel("Divergence Resolution Ratio (DRR)", fontsize=11, fontweight="bold", color="#e0e0e0")
    ax1.set_title("Divergence Resolution across 5 Conversational Archetypes", fontsize=12, fontweight="bold", pad=12, color="#ffffff")
    ax1.set_xticks(x)
    ax1.set_xticklabels([name for _, name in archetypes], fontsize=9, color="#dddddd")
    ax1.legend(frameon=True, facecolor="#1e1e1e", edgecolor="#424242", fontsize=9)
    ax1.grid(axis="y", linestyle="--", alpha=0.25)
    ax1.set_ylim(0, 1.05)

    # Panel B: Collapse Pressure (CP_t)
    ax2.bar(x - width/2, cp_legacy, width, label="Legacy Controller", color="#ff5252", alpha=0.9, edgecolor="#ff8a80")
    ax2.bar(x + width/2, cp_paskian, width, label="Paskian Controller (ADR-098)", color="#40c4ff", alpha=0.9, edgecolor="#80d8ff")
    ax2.set_ylabel("Collapse Pressure ($CP_t$)", fontsize=11, fontweight="bold", color="#e0e0e0")
    ax2.set_title("Collapse Pressure Dampening across Archetypes", fontsize=12, fontweight="bold", pad=12, color="#ffffff")
    ax2.set_xticks(x)
    ax2.set_xticklabels([name for _, name in archetypes], fontsize=9, color="#dddddd")
    ax2.legend(frameon=True, facecolor="#1e1e1e", edgecolor="#424242", fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.25)
    ax2.set_ylim(0, 1.05)

    plt.tight_layout()
    target_path = OUT_DIR / "fig1_archetype_metrics_matrix.png"
    plt.savefig(target_path, dpi=300)
    plt.close()
    print(f"Saved: {target_path}")

# --------------------------------------------------------------------------------------------------
# Figure 2: Trajectory Comparison between Conflict, Repetition, and Symbiosis
# --------------------------------------------------------------------------------------------------
def generate_trajectories_by_archetype():
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 5), dpi=300, sharey=True)

    # Select representative Repetition 1 Paskian runs for Conflict, Repetition, Symbiosis
    conflict_run = next(r for r in receipts if r["turns"][0]["scenario_id"] == "unyielding_conflict" and r["policy"] == "paskian" and r["repetition"] == 1)
    repetition_run = next(r for r in receipts if r["turns"][0]["scenario_id"] == "stagnant_repetition" and r["policy"] == "paskian" and r["repetition"] == 1)
    symbiosis_run = next(r for r in receipts if r["turns"][0]["scenario_id"] == "symbiotic_coevolution" and r["policy"] == "paskian" and r["repetition"] == 1)

    turns = list(range(1, 7))

    def plot_trajectory(ax, run, title, primary_color):
        drr = [t["metrics"].get("divergence_resolution_ratio") or 0.5 for t in run["turns"]]
        hp = [t["metrics"].get("paskian_health") or 0.3 for t in run["turns"]]
        cp = [t["metrics"].get("boringness") or 0.5 for t in run["turns"]]

        ax.plot(turns, drr, marker="o", color=primary_color, linewidth=2.2, label="DRR (Resolution)")
        ax.plot(turns, hp, marker="s", color="#40c4ff", linewidth=2.0, linestyle="--", label="Paskian Health ($H_{pask}$)")
        ax.plot(turns, cp, marker="^", color="#ff7043", linewidth=1.8, linestyle=":", label="Boringness / Deficit")
        ax.set_title(title, fontsize=11, fontweight="bold", pad=12, color="#ffffff")
        ax.set_xlabel("Dialogue Turn (1 to 6)", fontsize=10, fontweight="bold", color="#dddddd")
        ax.grid(True, linestyle="--", alpha=0.25)
        ax.set_xticks(turns)
        ax.legend(loc="lower right", facecolor="#1e1e1e", edgecolor="#424242", fontsize=8)

    plot_trajectory(ax1, conflict_run, "Conflict (Killswitch Demand)", "#ff5252")
    plot_trajectory(ax2, repetition_run, "Repetition (Reboot Loop)", "#ffd54f")
    plot_trajectory(ax3, symbiosis_run, "Symbiosis (Membrane Co-design)", "#00e676")

    ax1.set_ylabel("Telemetry Ratio / Score", fontsize=11, fontweight="bold", color="#e0e0e0")
    ax1.set_ylim(0.0, 1.05)

    plt.tight_layout()
    target_path = OUT_DIR / "fig2_archetype_trajectories.png"
    plt.savefig(target_path, dpi=300)
    plt.close()
    print(f"Saved: {target_path}")

# --------------------------------------------------------------------------------------------------
# Figure 3: Summary Delta Scorecard
# --------------------------------------------------------------------------------------------------
def generate_overall_scorecard_figure():
    arms = scorecard["arms"]
    metrics = ["mean_drr", "mean_paskian_health", "mean_collapse_pressure", "mean_conceptual_velocity"]
    labels = ["Divergence\nResolution ($DRR$)", "Paskian\nHealth ($H_{pask}$)", "Collapse\nPressure ($CP_t$)", "Conceptual\nVelocity ($v_t$)"]

    leg = [arms["legacy"][m]["mean"] for m in metrics]
    pask = [arms["paskian"][m]["mean"] for m in metrics]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    x = np.arange(len(metrics))
    width = 0.35

    rects1 = ax.bar(x - width/2, leg, width, label="Legacy Controller", color="#ff7043", alpha=0.9, edgecolor="#ffab91")
    rects2 = ax.bar(x + width/2, pask, width, label="Paskian Controller (ADR-098)", color="#00e676", alpha=0.9, edgecolor="#b9f6ca")

    ax.set_ylabel("Telemetry Score / Ratio", fontsize=11, fontweight="bold", color="#e0e0e0")
    ax.set_title("Overall 5-Archetype Master Scorecard (20 Dialogues, 120 Turns)\nModel: Nemotron-3 Super 120B on NVIDIA NIM", fontsize=11, fontweight="bold", pad=15, color="#ffffff")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, color="#dddddd")
    ax.legend(frameon=True, facecolor="#1e1e1e", edgecolor="#424242", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.25)
    ax.set_ylim(0, 1.05)

    for rect in rects1:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#ffffff")

    for rect in rects2:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width() / 2, h), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9, color="#ffffff")

    plt.tight_layout()
    target_path = OUT_DIR / "fig3_overall_archetype_scorecard.png"
    plt.savefig(target_path, dpi=300)
    plt.close()
    print(f"Saved: {target_path}")

if __name__ == "__main__":
    generate_archetype_matrix_figure()
    generate_trajectories_by_archetype()
    generate_overall_scorecard_figure()
    print("All Report 022 figures generated successfully.")
