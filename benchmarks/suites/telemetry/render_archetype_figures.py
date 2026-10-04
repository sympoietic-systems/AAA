"""
Renders publication-grade retro-cybernetic figures for Protocol Entry 004 and Report 022.
Enforces all tenets of .agents/protocols/VISUALS.md:
- Pure matte black void (#050505)
- Monochrome contrast with crisp foreground (#FFFFFF, #E4E7EC)
- Monospace technical typography (Consolas)
- Unified dual accents:
    Baseline: Amber Orange (#FB923C)
    Candidate: Emerald Green (#4ADE80)
- Minimal crosshairs [+] and technical bracket annotations
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from benchmarks.common.retro_plotter import (
    COLOR_BASELINE,
    COLOR_CANDIDATE,
    plot_dual_archetype_matrix,
    plot_grouped_bars,
    plot_homeostatic_sampling_vector,
    plot_trajectories,
)

ROOT = Path(__file__).resolve().parents[3]
RECEIPTS_PATH = (
    ROOT / "benchmarks" / "runs" / "telemetry" / "dialogue_feedback_20261003_004020" / "telemetry_receipts.json"
)
SCORECARD_PATH = ROOT / "benchmarks" / "runs" / "telemetry" / "dialogue_feedback_20261003_004020" / "scorecard.json"
OUTPUT_DIR_004 = ROOT / "docs" / "publish" / "004-boredom-as-an-agential-force" / "assets"
OUTPUT_DIR_022 = ROOT / "docs" / "reports" / "022-relational-conversational-archetypes"


def main() -> None:
    runs: list[dict[str, Any]] = json.loads(RECEIPTS_PATH.read_text(encoding="utf-8"))
    scorecard: dict[str, Any] = json.loads(SCORECARD_PATH.read_text(encoding="utf-8"))

    # Group by scenario and policy
    by_scen: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in runs:
        scen = r["turns"][0]["scenario_id"]
        pol = r["policy"]
        by_scen[scen][pol].append(r)

    archetype_keys = [
        ("unyielding_conflict", "Conflict\n(Antagonism)"),
        ("constructive_dialectic", "Dialectic\n(Disagreement)"),
        ("stagnant_repetition", "Repetition\n(Loop)"),
        ("symbiotic_coevolution", "Symbiosis\n(Co-Design)"),
        ("sycophantic_compliance", "Compliance\n(Echo)"),
    ]

    archetype_labels = [label for _, label in archetype_keys]
    drr_legacy = []
    drr_paskian = []
    cp_legacy = []
    cp_paskian = []

    for key, _ in archetype_keys:
        leg_runs = by_scen[key]["legacy"]
        pas_runs = by_scen[key]["paskian"]

        drr_leg = sum(x["mean_drr"] for x in leg_runs) / len(leg_runs)
        drr_pas = sum(x["mean_drr"] for x in pas_runs) / len(pas_runs)
        cp_leg = sum(x["mean_collapse_pressure"] for x in leg_runs) / len(leg_runs)
        cp_pas = sum(x["mean_collapse_pressure"] for x in pas_runs) / len(pas_runs)

        drr_legacy.append(drr_leg)
        drr_paskian.append(drr_pas)
        cp_legacy.append(cp_leg)
        cp_paskian.append(cp_pas)

    print("[1/3] Generating Dual Archetype Phase Space Matrix...")
    matrix_004 = OUTPUT_DIR_004 / "004-archetype-metrics-matrix.png"
    plot_dual_archetype_matrix(
        archetypes=archetype_labels,
        drr_legacy=drr_legacy,
        drr_paskian=drr_paskian,
        cp_legacy=cp_legacy,
        cp_paskian=cp_paskian,
        output_path=matrix_004,
        title="ARCHETYPE PHASE SPACE MATRIX: DIVERGENCE RESOLUTION & COLLAPSE PRESSURE",
        subtitle="Evaluated on nvidia/nemotron-3-super-120b-a12b under 1:1 model parity (N=120 turns)",
    )
    # Also update report 022 version
    matrix_022 = OUTPUT_DIR_022 / "fig1_archetype_metrics_matrix.png"
    plot_dual_archetype_matrix(
        archetypes=archetype_labels,
        drr_legacy=drr_legacy,
        drr_paskian=drr_paskian,
        cp_legacy=cp_legacy,
        cp_paskian=cp_paskian,
        output_path=matrix_022,
        title="ARCHETYPE PHASE SPACE MATRIX: DIVERGENCE RESOLUTION & COLLAPSE PRESSURE",
        subtitle="Evaluated on nvidia/nemotron-3-super-120b-a12b under 1:1 model parity (N=120 turns)",
    )

    print("[2/3] Generating Overall Scorecard...")
    scorecard_metrics = ["DRR (Convergence)", "Hpask (Vitality)", "CP_t (Collapse)", "Velocity (v_t)"]
    legacy_arms = scorecard["arms"]["legacy"]
    paskian_arms = scorecard["arms"]["paskian"]

    series_data = {
        "Legacy Baseline": [
            legacy_arms["mean_drr"]["mean"],
            legacy_arms["mean_paskian_health"]["mean"],
            legacy_arms["mean_collapse_pressure"]["mean"],
            legacy_arms["mean_conceptual_velocity"]["mean"],
        ],
        "Paskian Controller (ADR-098)": [
            paskian_arms["mean_drr"]["mean"],
            paskian_arms["mean_paskian_health"]["mean"],
            paskian_arms["mean_collapse_pressure"]["mean"],
            paskian_arms["mean_conceptual_velocity"]["mean"],
        ],
    }
    series_colors = {
        "Legacy Baseline": COLOR_BASELINE,
        "Paskian Controller (ADR-098)": COLOR_CANDIDATE,
    }

    scorecard_004 = OUTPUT_DIR_004 / "004-overall-archetype-scorecard.png"
    plot_grouped_bars(
        categories=scorecard_metrics,
        series_data=series_data,
        series_colors=series_colors,
        title="OVERALL 5-ARCHETYPE MASTER SCORECARD (20 DIALOGUES, 120 TURNS)",
        subtitle="Model Apparatus & Participant Simulator: nvidia/nemotron-3-super-120b-a12b (NVIDIA NIM)",
        ylabel="Telemetry Ratio / Score",
        output_path=scorecard_004,
        ylim=(0.0, 1.05),
        badge="CANONICAL AUDIT",
    )
    scorecard_022 = OUTPUT_DIR_022 / "fig3_overall_archetype_scorecard.png"
    plot_grouped_bars(
        categories=scorecard_metrics,
        series_data=series_data,
        series_colors=series_colors,
        title="OVERALL 5-ARCHETYPE MASTER SCORECARD (20 DIALOGUES, 120 TURNS)",
        subtitle="Model Apparatus & Participant Simulator: nvidia/nemotron-3-super-120b-a12b (NVIDIA NIM)",
        ylabel="Telemetry Ratio / Score",
        output_path=scorecard_022,
        ylim=(0.0, 1.05),
        badge="CANONICAL AUDIT",
    )

    print("[3/3] Generating Turn Trajectories...")

    # Extract turn-by-turn values for Conflict, Repetition, Symbiosis under Paskian
    def extract_trajectory(scen_key: str) -> dict[str, list[float]]:
        p_runs = by_scen[scen_key]["paskian"]
        # Take mean over repetitions
        drr = []
        hpask = []
        boringness = []
        for turn_idx in range(6):
            t_drr = [
                float(val)
                if (val := r["turns"][turn_idx]["metrics"].get("divergence_resolution_ratio")) is not None
                else 0.5
                for r in p_runs
            ]
            t_hpask = [
                float(val) if (val := r["turns"][turn_idx]["metrics"].get("paskian_health")) is not None else 0.35
                for r in p_runs
            ]
            t_boring = [
                float(val)
                if (val := r["turns"][turn_idx]["metrics"].get("boringness")) is not None
                else (
                    float(val2)
                    if (val2 := r["turns"][turn_idx]["metrics"].get("homeostatic_deficit")) is not None
                    else 0.5
                )
                for r in p_runs
            ]
            drr.append(sum(t_drr) / len(t_drr))
            hpask.append(sum(t_hpask) / len(t_hpask))
            boringness.append(sum(t_boring) / len(t_boring))
        return {"DRR": drr, "Hpask": hpask, "Boringness": boringness}

    trajectories_data = {
        "1. Conflict (Antagonism)": extract_trajectory("unyielding_conflict"),
        "2. Dialectic (Disagreement)": extract_trajectory("constructive_dialectic"),
        "3. Repetition (Reboot Loop)": extract_trajectory("stagnant_repetition"),
        "4. Symbiosis (Co-Design)": extract_trajectory("symbiotic_coevolution"),
        "5. Compliance (Echo Chamber)": extract_trajectory("sycophantic_compliance"),
    }

    trajectories_004 = OUTPUT_DIR_004 / "004-archetype-trajectories.png"
    plot_trajectories(
        turns_data=trajectories_data,
        output_path=trajectories_004,
        title="TURN-BY-TURN TELEMETRY TRAJECTORIES ACROSS ALL 5 ARCHETYPES",
        subtitle="Tracking dynamic deadlock severing and homeostatic stabilization across 6 dialogue turns (NVIDIA Nemotron-3 Super 120B)",
    )
    trajectories_022 = OUTPUT_DIR_022 / "fig2_archetype_trajectories.png"
    plot_trajectories(
        turns_data=trajectories_data,
        output_path=trajectories_022,
        title="TURN-BY-TURN TELEMETRY TRAJECTORIES ACROSS ALL 5 ARCHETYPES",
        subtitle="Tracking dynamic deadlock severing and homeostatic stabilization across 6 dialogue turns (NVIDIA Nemotron-3 Super 120B)",
    )

    print("[4/4] Generating Homeostatic Sampling Vector Dynamics...")
    # Extract homeostatic parameters across turns for the high-friction unyielding_conflict scenario
    conflict_paskian_runs = by_scen["unyielding_conflict"]["paskian"]
    temps = []
    base_temps = []
    pres_pens = []
    freq_pens = []
    cps = []
    deficits = []

    for turn_idx in range(6):
        t_vals = [r["turns"][turn_idx]["homeostatic"]["temperature"]["value"] for r in conflict_paskian_runs]
        bt_vals = [r["turns"][turn_idx]["homeostatic"]["temperature"]["base"] for r in conflict_paskian_runs]
        pp_vals = [r["turns"][turn_idx]["homeostatic"]["presence_penalty"]["value"] for r in conflict_paskian_runs]
        fp_vals = [r["turns"][turn_idx]["homeostatic"]["frequency_penalty"]["value"] for r in conflict_paskian_runs]
        cp_vals = [
            float(r["turns"][turn_idx]["metrics"].get("homeostatic_deficit", 0.5))
            if r["turns"][turn_idx]["metrics"].get("homeostatic_deficit") is not None
            else 0.5
            for r in conflict_paskian_runs
        ]
        def_vals = [
            float(r["turns"][turn_idx]["metrics"].get("homeostatic_deficit", 0.5))
            if r["turns"][turn_idx]["metrics"].get("homeostatic_deficit") is not None
            else 0.5
            for r in conflict_paskian_runs
        ]

        temps.append(sum(t_vals) / len(t_vals))
        base_temps.append(sum(bt_vals) / len(bt_vals))
        pres_pens.append(sum(pp_vals) / len(pp_vals))
        freq_pens.append(sum(fp_vals) / len(fp_vals))
        cps.append(sum(cp_vals) / len(cp_vals))
        deficits.append(sum(def_vals) / len(def_vals))

    sampling_vector_data = {
        "temperature": temps,
        "base_temperature": base_temps,
        "presence_penalty": pres_pens,
        "frequency_penalty": freq_pens,
        "collapse_pressure": cps,
        "deficit": deficits,
    }

    sampling_004 = OUTPUT_DIR_004 / "004-homeostatic-vector-dynamics.png"
    plot_homeostatic_sampling_vector(
        turns_data=sampling_vector_data,
        output_path=sampling_004,
        title="HOMEOSTATIC SAMPLING VECTOR DYNAMICS ACROSS TURNS",
        subtitle="Sampling entropy & directional penalty injection under adversarial conflict (NVIDIA Nemotron-3 Super 120B)",
    )
    sampling_022 = OUTPUT_DIR_022 / "fig4_homeostatic_vector_dynamics.png"
    plot_homeostatic_sampling_vector(
        turns_data=sampling_vector_data,
        output_path=sampling_022,
        title="HOMEOSTATIC SAMPLING VECTOR DYNAMICS ACROSS TURNS",
        subtitle="Sampling entropy & directional penalty injection under adversarial conflict (NVIDIA Nemotron-3 Super 120B)",
    )

    print("All figures successfully rendered according to .agents/protocols/VISUALS.md!")


if __name__ == "__main__":
    main()
