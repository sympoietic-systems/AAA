import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Load scorecard
scorecard_path = Path("benchmarks/runs/telemetry/dialogue_feedback_20261002_151610/scorecard.json")
data = json.loads(scorecard_path.read_text(encoding="utf-8"))

arms = data["arms"]
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
    "Paskian\nHealth",
    "Collapse\nPressure",
    "Conceptual\nVelocity",
    "Control\nObservability",
]

legacy_vals = [legacy[m]["mean"] for m in metrics]
paskian_vals = [paskian[m]["mean"] for m in metrics]

# Set dark cybernetic style
plt.style.use('dark_background')
fig, ax = plt.subplots(figsize=(9, 5), dpi=300)

x = np.arange(len(metrics))
width = 0.35

rects1 = ax.bar(x - width/2, legacy_vals, width, label='Legacy Arm', color='#ff9800', alpha=0.85, edgecolor='#ffa726')
rects2 = ax.bar(x + width/2, paskian_vals, width, label='Paskian (ADR-098)', color='#00e676', alpha=0.85, edgecolor='#69f0ae')

ax.set_ylabel('Score / Telemetry Ratio', fontsize=11, fontweight='bold', color='#e0e0e0')
ax.set_title('ADR-098 Ablation: Legacy vs Paskian Controller (Nemotron-3 Super 120B)', fontsize=12, fontweight='bold', pad=15, color='#ffffff')
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=10, color='#cccccc')
ax.legend(frameon=True, facecolor='#1e1e1e', edgecolor='#424242')
ax.grid(axis='y', linestyle='--', alpha=0.3, color='#888888')
ax.set_ylim(0, 1.15)

def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4),  # 4 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, color='#ffffff')

autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
out_file = Path("docs/reports/020-paskian-teachback/legacy-vs-paskian-metrics.png")
plt.savefig(out_file, dpi=300)
print(f"Chart saved to {out_file}")
