import json
from collections import defaultdict
from pathlib import Path

RUN_PATH = Path("benchmarks/runs/telemetry/dialogue_feedback_20261003_004020/telemetry_receipts.json")
receipts = json.loads(RUN_PATH.read_text(encoding="utf-8"))

grouped = defaultdict(lambda: defaultdict(list))
for run in receipts:
    scen = run["turns"][0]["scenario_id"]
    pol = run["policy"]
    grouped[scen][pol].append(run)

output_lines = []
for scen in [
    "unyielding_conflict",
    "constructive_dialectic",
    "stagnant_repetition",
    "symbiotic_coevolution",
    "sycophantic_compliance",
]:
    pols = grouped[scen]
    output_lines.append(f"### {scen}")
    for pol in ["legacy", "paskian"]:
        runs = pols[pol]
        drr = sum(x["mean_drr"] for x in runs) / len(runs)
        hp = sum(x["mean_paskian_health"] for x in runs) / len(runs)
        cp = sum(x["mean_collapse_pressure"] for x in runs) / len(runs)
        vel = sum(x["mean_conceptual_velocity"] for x in runs) / len(runs)
        lat = sum(x["mean_latency_ms"] for x in runs) / len(runs)
        output_lines.append(
            f"  {pol:8s}: DRR={drr:.3f}, Hpask={hp:.3f}, CP={cp:.3f}, Vel={vel:.3f}, Lat={lat/1000:.1f}s"
        )

print("\n".join(output_lines))
Path("benchmarks/runs/telemetry/dialogue_feedback_20261003_004020/archetype_summary.txt").write_text(
    "\n".join(output_lines) + "\n", encoding="utf-8"
)
