"""
Restrained Cyberpunk Telemetry Dashboard & Oscilloscope Visualizer.
Implements high-density 14-panel audit cards and 5-tier multi-turn oscilloscopes.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from benchmarks.common.visualizer import (
    BG_COLOR,
    PANEL_BG,
    TEXT_COLOR,
    SUBTEXT_COLOR,
    COLOR_GREEN,
    COLOR_GREEN_ALT,
    COLOR_ORANGE,
    COLOR_ORANGE_ALT,
    COLOR_ICE_CYAN,
    COLOR_SLATE,
    COLOR_VIOLET,
    MPL_GRID_COLOR,
    MPL_BORDER_COLOR,
    capture_html_screenshot,
    make_grid,
    to_circ,
    to_pts,
)

# Curated metric colors (used identically for Before & Now traces on each card)
METRIC_CARD_SPECS = [
    {
        "key": "pairwise_similarity",
        "fallback": "s_t",
        "title": "1. PAIRWISE SIMILARITY (s_t)",
        "desc": "Reciprocal displacement coherence normalized by sum of active weights.",
        "badge": "MANIFOLD COHERENCE",
        "color": COLOR_ICE_CYAN,
        "zones": [
            {"top": 0.70, "bottom": 1.00, "label": "HIGH COHERENCE ZONE [0.70 - 1.00]", "color": "rgba(56, 189, 248, 0.04)"},
            {"top": 0.00, "bottom": 0.30, "label": "DISASSOCIATION BASIN [0.00 - 0.30]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "deficit",
        "fallback": "homeostatic_deficit",
        "title": "2. CONVERSATIONAL DEFICIT",
        "desc": "Allostatic load tracking perturbation, velocity, and entropy deficits.",
        "badge": "ALLOSTATIC DEFICIT",
        "color": COLOR_ORANGE,
        "zones": [
            {"top": 0.70, "bottom": 1.00, "label": "CRITICAL DEFICIT STRAIN [0.70 - 1.00]", "color": "rgba(255, 107, 0, 0.05)"},
            {"top": 0.00, "bottom": 0.30, "label": "HOMEOSTATIC BALANCE [0.00 - 0.30]", "color": "rgba(16, 185, 129, 0.04)"},
        ],
    },
    {
        "key": "vitality",
        "fallback": "conversation_vitality",
        "title": "3. CONVERSATIONAL VITALITY",
        "desc": "Allostatic vitality measuring dialectic liveliness: 1.0 - Deficit with unclamped entropy.",
        "badge": "ALLOSTATIC VITALITY",
        "color": COLOR_GREEN,
        "zones": [
            {"top": 0.60, "bottom": 1.00, "label": "HIGH VITALITY ZONE [0.60 - 1.00]", "color": "rgba(16, 185, 129, 0.04)"},
            {"top": 0.00, "bottom": 0.30, "label": "METABOLIC COLLAPSE [0.00 - 0.30]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "forward_perturbation",
        "fallback": "fp_t",
        "title": "4. FORWARD PERTURBATION (fP_t)",
        "desc": "Agent-induced displacement shift on human thought vector: 1 - cos(Δa, Δh).",
        "badge": "AGENT PERTURBATION",
        "color": COLOR_ORANGE_ALT,
        "zones": [
            {"top": 0.40, "bottom": 0.70, "label": "ACTIVE DIALECTIC PERTURBATION [0.40 - 0.70]", "color": "rgba(251, 146, 60, 0.04)"},
        ],
    },
    {
        "key": "mutual_perturbation",
        "fallback": "mpi",
        "title": "5. MUTUAL PERTURBATION INDEX (MPI)",
        "desc": "Bilateral dialectic geometric coupling mean: sqrt(rP_t * fP_t).",
        "badge": "RECIPROCAL COUPLING",
        "color": COLOR_GREEN,
        "zones": [
            {"top": 0.50, "bottom": 0.80, "label": "CONSTRUCTIVE COUPLING [0.50 - 0.80]", "color": "rgba(16, 185, 129, 0.04)"},
            {"top": 0.00, "bottom": 0.20, "label": "DECOUPLED BASIN [0.00 - 0.20]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "reverse_perturbation",
        "fallback": "rp_t",
        "title": "6. REVERSE PERTURBATION (rP_t)",
        "desc": "Human-induced trajectory shift in agent thought vector: 1 - cos(Δh, Δa).",
        "badge": "TRAJECTORY TENSION",
        "color": COLOR_ORANGE,
        "zones": [
            {"top": 0.40, "bottom": 0.70, "label": "ACTIVE TENSION [0.40 - 0.70]", "color": "rgba(255, 107, 0, 0.04)"},
        ],
    },
    {
        "key": "conceptual_novelty",
        "fallback": "n_t",
        "title": "7. CONCEPTUAL NOVELTY (N_t)",
        "desc": "Semantic displacement from context centroid EMA: ||v_t - c_t||_2.",
        "badge": "SEMANTIC DISPLACEMENT",
        "color": COLOR_ICE_CYAN,
        "zones": [
            {"top": 0.70, "bottom": 1.00, "label": "PARADIGM EXPLORATION [0.70 - 1.00]", "color": "rgba(56, 189, 248, 0.04)"},
            {"top": 0.00, "bottom": 0.40, "label": "REPETITIVE STAGNATION BASIN [0.00 - 0.40]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "collapse_pressure",
        "fallback": "boringness",
        "title": "8. COLLAPSE PRESSURE (BORINGNESS)",
        "desc": "Allostatic stagnation alarm tracking perturbation, entropy, and novelty deficits.",
        "badge": "STAGNATION REGULATION",
        "color": COLOR_ORANGE,
        "zones": [
            {"top": 0.65, "bottom": 1.00, "label": "SEDATION INTERRUPT [0.65]", "color": "rgba(239, 68, 68, 0.06)"},
            {"top": 0.00, "bottom": 0.40, "label": "FLOWING CEILING [0.40]", "color": "rgba(16, 185, 129, 0.04)"},
        ],
    },
    {
        "key": "divergence_resolution_ratio",
        "fallback": "drr",
        "title": "9. DIVERGENCE RESOLUTION RATIO (DRR)",
        "desc": "Ratio of resolved dialectic tension to open systemic divergence: min(1.0, D_res / D_open).",
        "badge": "DIALECTIC HOMEOSTASIS",
        "color": COLOR_GREEN,
        "zones": [
            {"top": 0.70, "bottom": 1.00, "label": "BALANCED RESOLUTION [0.70 - 1.00]", "color": "rgba(16, 185, 129, 0.04)"},
            {"top": 0.00, "bottom": 0.40, "label": "FRAGMENTATION BASIN [0.00 - 0.40]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "paskian_health",
        "fallback": "h_pask",
        "title": "10. GORDON PASK CYBERNETIC HEALTH (H_pask)",
        "desc": "Composite dialectic viability across novelty, entropy variety, and reciprocal learning.",
        "badge": "ORGANIZATIONAL CLOSURE",
        "color": COLOR_GREEN,
        "zones": [
            {"top": 0.60, "bottom": 1.00, "label": "HIGH VITALITY ZONE [0.60 - 1.00]", "color": "rgba(16, 185, 129, 0.04)"},
            {"top": 0.00, "bottom": 0.30, "label": "METABOLIC COLLAPSE BASIN [0.00 - 0.30]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "conceptual_velocity",
        "fallback": "v_t",
        "title": "11. CONCEPTUAL VELOCITY (v_t)",
        "desc": "Instantaneous semantic displacement speed normalized against absolute reference scale.",
        "badge": "SEMANTIC SPEED",
        "color": COLOR_ORANGE_ALT,
        "zones": [
            {"top": 0.65, "bottom": 1.00, "label": "RAPID DRIFT ZONE [0.65 - 1.00]", "color": "rgba(251, 146, 60, 0.04)"},
            {"top": 0.00, "bottom": 0.20, "label": "STAGNATION BASIN [0.00 - 0.20]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "surprise_index",
        "fallback": "s_t",
        "title": "12. PREDICTIVE RESIDUAL TREND SURPRISE (S_t)",
        "desc": "Forecasting error z-score from Holt linear trend EMA with calibrated variance prior.",
        "badge": "MOMENTUM DISCONTINUITY",
        "color": COLOR_VIOLET,
        "zones": [
            {"top": 0.70, "bottom": 1.00, "label": "HIGH DISCONTINUITY [0.70 - 1.00]", "color": "rgba(167, 139, 250, 0.04)"},
            {"top": 0.00, "bottom": 0.30, "label": "PREDICTABLE CONTINUITY [0.00 - 0.30]", "color": "rgba(16, 185, 129, 0.04)"},
        ],
    },
    {
        "key": "coupling_coherence",
        "fallback": "c_t",
        "title": "13. TRAJECTORY CROSS-CORRELATION (C_t)",
        "desc": "Directional half-wave rectified displacement alignment: max(0, cos theta).",
        "badge": "DIRECTIONAL COUPLING",
        "color": COLOR_SLATE,
        "zones": [
            {"top": 0.60, "bottom": 1.00, "label": "SYNCHRONIZED COUPLING [0.60 - 1.00]", "color": "rgba(100, 116, 139, 0.05)"},
            {"top": 0.00, "bottom": 0.20, "label": "DIALECTIC DECOUPLING [0.00 - 0.20]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
    {
        "key": "agent_self_divergence",
        "fallback": "d_self",
        "title": "14. RECURSIVE SELF-ECHO DIVERGENCE (D_self)",
        "desc": "Speaker-isolated agent anti-looping metric with compact window and repeat penalty.",
        "badge": "AGENT SELF-DIVERGENCE",
        "color": COLOR_ICE_CYAN,
        "zones": [
            {"top": 0.70, "bottom": 1.00, "label": "HIGH EVOLUTION DIVERGENCE [0.70 - 1.00]", "color": "rgba(56, 189, 248, 0.04)"},
            {"top": 0.00, "bottom": 0.30, "label": "RECURSIVE ECHO BASIN [0.00 - 0.30]", "color": "rgba(239, 68, 68, 0.04)"},
        ],
    },
]


def render_14_panel_comparison_dashboard(
    run_a_name: str,
    run_b_name: str,
    turns_a: List[dict],
    turns_b: List[dict],
    comparison: Dict[str, Any],
    out_dir: Path,
    custom_name: str = "",
) -> Tuple[Path, Path]:
    """
    Renders the 14-panel audit dashboard:
    - 2-column x 7-row card grid (1720x3380 canvas).
    - Restrained cyberpunk color scheme (greyscale, terminal green, hot orange).
    - Same-hue metric tracking: Before is dotted with hollow circles, Now is solid with filled circles.
    - Card stat bars, qualitative threshold zones, and bottom summary scorecard.
    """
    if isinstance(out_dir, Path) and out_dir.suffix in (".png", ".html"):
        if not custom_name:
            custom_name = out_dir.stem
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    num_turns = max(len(turns_a), len(turns_b), 10)

    def extract_vals(turns: list, key: str, fallback: str = "") -> List[float]:
        res = []
        for t in turns:
            m = t.get("metrics", {})
            v = m.get(key)
            if v is None and fallback:
                v = m.get(fallback)
            res.append(float(v) if v is not None else 0.0)
        return res

    all_deltas_map = {d.key: d for d in comparison.get("all_deltas", [])}
    cards_html = []

    for spec in METRIC_CARD_SPECS:
        key = spec["key"]
        fallback = spec["fallback"]
        color = spec["color"]
        title = spec["title"]
        desc = spec["desc"]
        badge = spec["badge"]
        zones = spec["zones"]

        series_a = extract_vals(turns_a, key, fallback)
        series_b = extract_vals(turns_b, key, fallback)

        delta_obj = all_deltas_map.get(key)
        delta_val = delta_obj.delta if delta_obj else (np.mean(series_b) - np.mean(series_a) if series_a and series_b else 0.0)
        abs_delta = abs(delta_val)
        is_changed = abs_delta >= 0.05

        # Card border style: highlight if metric changed significantly
        card_border_style = f"border: 1px solid {COLOR_ORANGE}; box-shadow: 0 0 15px rgba(255, 107, 0, 0.25);" if is_changed else "border: 1px solid rgba(255,255,255,0.11);"
        badge_style = f"background: rgba(255,107,0,0.15); color: {COLOR_ORANGE}; border: 1px solid rgba(255,107,0,0.4);" if is_changed else f"background: rgba(255,255,255,0.06); color: {TEXT_COLOR}; border: 1px solid rgba(255,255,255,0.15);"
        alert_badge = f'<span style="background: rgba(255,107,0,0.2); color: {COLOR_ORANGE}; font-size: 8.5px; padding: 2px 6px; border-radius: 3px; font-weight: 800; margin-left: 6px;">SHIFT DETECTED</span>' if is_changed else ""

        # Background zones
        zones_html = []
        for z in zones:
            y_top = 188 - (z["top"] * (188 - 22))
            height = (z["top"] - z["bottom"]) * (188 - 22)
            zones_html.append(f'<rect x="65" y="{y_top:.1f}" width="680" height="{height:.1f}" fill="{z["color"]}" />')
            zones_html.append(f'<text x="735" y="{y_top + 12:.1f}" fill="rgba(255,255,255,0.3)" font-size="9" text-anchor="end">{z["label"]}</text>')

        # Polylines & Markers (SAME COLOR: Before is Dotted, Now is Solid)
        traces_html = []
        if series_a:
            traces_html.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.7" points="{to_pts(series_a, left=65, right=745, top=22, bottom=188)}" />'
            )
            traces_html.append(to_circ(series_a, color=color, r=3.2, hollow=True, left=65, right=745, top=22, bottom=188))
        if series_b:
            traces_html.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="2.8" points="{to_pts(series_b, left=65, right=745, top=22, bottom=188)}" />'
            )
            traces_html.append(to_circ(series_b, color=color, r=3.8, hollow=False, left=65, right=745, top=22, bottom=188))

        # Terminal & Delta strings
        t_a_val = series_a[-1] if series_a else 0.0
        t_b_val = series_b[-1] if series_b else 0.0
        delta_color = COLOR_ORANGE if delta_val > 0.02 else (COLOR_GREEN if delta_val < -0.02 else SUBTEXT_COLOR)
        sign = "+" if delta_val >= 0 else ""

        if series_a:
            stat_bar_html = f"""<span>Terminal T{num_turns}: <strong class="card-stat-val">Now: {t_b_val:.3f}</strong> vs <strong class="card-stat-val">Before: {t_a_val:.3f}</strong></span>
        <span>Mean Shift Delta: <strong style="color: {delta_color}; font-weight: 800;">{sign}{delta_val:.3f}</strong></span>"""
        else:
            mean_b = np.mean(series_b) if series_b else 0.0
            stat_bar_html = f"""<span>Terminal T{num_turns}: <strong class="card-stat-val">{t_b_val:.3f}</strong></span>
        <span>Trajectory Mean: <strong style="color: {TEXT_COLOR}; font-weight: 800;">{mean_b:.3f}</strong></span>"""

        card_html = f"""
    <div class="panel-card" style="{card_border_style}">
      <div class="card-top">
        <div>
          <div class="panel-title">{title} {alert_badge}</div>
          <div class="panel-desc">{desc}</div>
        </div>
        <span class="card-badge" style="{badge_style}">{badge}</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        {"".join(zones_html)}
        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}
        {"".join(traces_html)}
      </svg>

      <div class="card-stat-bar">
        {stat_bar_html}
      </div>
    </div>"""
        cards_html.append(card_html)

    # Scorecard bottom bar
    scorecards = []
    key_metrics_for_footer = [
        ("pairwise_similarity", "FINAL SIMILARITY (s_t)", COLOR_ICE_CYAN),
        ("deficit", "FINAL DEFICIT", COLOR_ORANGE),
        ("vitality", "FINAL VITALITY", COLOR_GREEN),
        ("paskian_health", "FINAL PASK HEALTH", COLOR_GREEN),
        ("conceptual_velocity", "FINAL VELOCITY (v_t)", COLOR_ORANGE_ALT),
        ("surprise_index", "FINAL SURPRISE (S_t)", COLOR_VIOLET),
        ("coupling_coherence", "COUPLING COHERENCE", COLOR_SLATE),
        ("agent_self_divergence", "AGENT SELF-DIVERGENCE", COLOR_ICE_CYAN),
    ]

    for km, km_title, km_color in key_metrics_for_footer:
        va = extract_vals(turns_a, km)
        vb = extract_vals(turns_b, km)
        last_a = va[-1] if va else 0.0
        last_b = vb[-1] if vb else 0.0
        if va:
            val_str = f'NOW: <span style="color: {km_color};">{last_b:.3f}</span> // BEFORE: {last_a:.3f}'
        else:
            val_str = f'VAL: <span style="color: {km_color};">{last_b:.3f}</span>'
        scorecards.append(f"""
    <div class="score-card">
      <div class="score-title" style="color: {km_color};">{km_title}</div>
      <div class="score-val">{val_str}</div>
      <div class="score-sub">T{num_turns} terminal dialectic status</div>
    </div>""")

    if custom_name:
        prefix = custom_name
    elif run_a_name:
        prefix = f"comparison_{run_a_name}_vs_{run_b_name}"
    else:
        prefix = f"audit_{run_b_name}"
    html_file = out_dir / f"{prefix}.html"
    png_file = out_dir / f"{prefix}.png"

    if run_a_name:
        header_title = f'CYBERNETIC TELEMETRY AUDIT <span class="badge-primary">{run_a_name} vs. {run_b_name}</span>'
        header_subtitle = "Calibrated 14-metric dialectic comparison dashboard across multi-turn conversational trajectories."
        header_meta = f"""Run A (Before): <span>{run_a_name}</span> ({len(turns_a)} turns)<br/>
      Run B (Now): <span>{run_b_name}</span> ({len(turns_b)} turns)<br/>
      Status: <span>CALIBRATED RESTYLED CYBERPUNK</span>"""
        legend_content = f"""    <div class="legend-item">
      <span class="line-sample-solid"></span>
      <span class="dot-sample-solid"></span>
      <span><strong>Now [{run_b_name}]:</strong> Solid Line + Filled Circle (Same Hue Per Metric)</span>
    </div>
    <div class="legend-item">
      <span class="line-sample-dashed"></span>
      <span class="dot-sample-hollow"></span>
      <span><strong>Before [{run_a_name}]:</strong> Dotted Line + Hollow Circle (Same Hue Per Metric)</span>
    </div>
    <div class="legend-item">
      <span style="color: {COLOR_ORANGE}; font-weight: 700;">[SHIFT DETECTED]: Highlighted Border (|Δ| >= 0.05)</span>
    </div>"""
    else:
        header_title = f'CYBERNETIC TELEMETRY AUDIT <span class="badge-primary">{run_b_name}</span>'
        header_subtitle = "Calibrated 14-metric dialectic trajectory audit across conversational turns."
        header_meta = f"""Dataset: <span>{run_b_name}</span> ({len(turns_b)} turns)<br/>
      Regime: <span>HOMEOSTATIC AUDIT</span><br/>
      Status: <span>CALIBRATED RESTYLED CYBERPUNK</span>"""
        legend_content = f"""    <div class="legend-item">
      <span class="line-sample-solid"></span>
      <span class="dot-sample-solid"></span>
      <span><strong>Trajectory Trace:</strong> Solid Line + Filled Markers (Calibrated Normalized Space)</span>
    </div>
    <div class="legend-item">
      <span style="color: {COLOR_GREEN}; font-weight: 700;">[STATUS]: 14 Homeostatic Regimes Monitored</span>
    </div>"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cybernetic Telemetry Audit: {run_b_name}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background-color: {BG_COLOR}; color: {TEXT_COLOR}; font-family: 'JetBrains Mono', monospace;
    width: 1720px; height: 3380px; padding: 26px 34px; display: flex; flex-direction: column;
    justify-content: space-between; position: relative;
    background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0);
    background-size: 24px 24px;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid rgba(255,255,255,0.12); padding-bottom: 14px;
  }}
  .title-area h1 {{
    font-size: 21px; font-weight: 800; letter-spacing: 1px; color: #ffffff;
    display: flex; align-items: center; gap: 12px;
  }}
  .badge-primary {{
    background: rgba(16, 185, 129, 0.15); color: {COLOR_GREEN}; border: 1px solid rgba(16, 185, 129, 0.4);
    font-size: 11px; padding: 3px 10px; border-radius: 4px; font-weight: 700; letter-spacing: 0.8px;
  }}
  .subtitle {{
    font-size: 11.5px; color: {SUBTEXT_COLOR}; margin-top: 4px; font-family: 'Inter', sans-serif;
  }}
  .header-meta {{
    text-align: right; font-size: 10.5px; color: #717684; line-height: 1.6;
  }}
  .header-meta span {{ color: {COLOR_GREEN}; font-weight: 600; }}

  /* Legend Bar */
  .legend-bar {{
    display: flex; justify-content: space-between; align-items: center;
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px; padding: 7px 18px; margin-top: 10px; font-size: 11px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; }}
  .line-sample-solid {{ width: 24px; height: 3px; background: {COLOR_GREEN}; border-radius: 2px; display: inline-block; }}
  .line-sample-dashed {{ width: 24px; height: 3px; border-top: 2px dashed {COLOR_SLATE}; display: inline-block; }}
  .dot-sample-solid {{ width: 8px; height: 8px; background: {COLOR_GREEN}; border-radius: 50%; display: inline-block; }}
  .dot-sample-hollow {{ width: 8px; height: 8px; border: 2px solid {COLOR_SLATE}; background: {BG_COLOR}; border-radius: 50%; display: inline-block; }}

  /* 14-Panel Grid */
  .panels-container {{
    display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(7, 1fr);
    gap: 12px; margin: 12px 0; flex: 1;
  }}
  .panel-card {{
    background: {PANEL_BG}; border-radius: 8px; padding: 10px 16px;
    display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 6px 20px rgba(0,0,0,0.45); position: relative; overflow: hidden;
  }}
  .panel-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, {COLOR_GREEN}, {COLOR_ICE_CYAN}, {COLOR_ORANGE});
  }}
  .card-top {{
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2px;
  }}
  .panel-title {{
    font-size: 12.5px; font-weight: 800; letter-spacing: 0.8px; color: #ffffff; display: flex; align-items: center;
  }}
  .panel-desc {{
    font-size: 9.5px; color: {SUBTEXT_COLOR}; font-family: 'Inter', sans-serif; margin-top: 2px; line-height: 1.3;
  }}
  .card-badge {{
    font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 3px; letter-spacing: 0.5px; white-space: nowrap;
  }}
  .svg-plot {{ width: 100%; height: 215px; }}

  .card-stat-bar {{
    display: flex; justify-content: space-between; align-items: center;
    border-top: 1px solid rgba(255,255,255,0.07); padding-top: 5px; font-size: 10.5px; color: {SUBTEXT_COLOR};
  }}
  .card-stat-val {{ color: #ffffff; font-weight: 700; }}

  /* Scorecard Bottom Row */
  .scorecard-row {{
    display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; margin-top: 6px;
  }}
  .score-card {{
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 5px; padding: 6px 10px;
  }}
  .score-title {{ font-size: 9px; font-weight: 700; letter-spacing: 0.5px; }}
  .score-val {{ font-size: 10.5px; font-weight: 800; color: #ffffff; margin: 2px 0; }}
  .score-sub {{ font-size: 8.5px; color: {SUBTEXT_COLOR}; font-family: 'Inter', sans-serif; }}

  .footer-row {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 9.5px; color: #525866; border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 8px; margin-top: 8px;
  }}
</style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="title-area">
      <h1>{header_title}</h1>
      <div class="subtitle">{header_subtitle}</div>
    </div>
    <div class="header-meta">
      {header_meta}
    </div>
  </div>

  <!-- Legend Bar -->
  <div class="legend-bar">
    {legend_content}
    <div class="legend-item">
      <span style="color: #717684; font-size: 10px;">Domain: [0.00, 1.00] Normalized Dialectic Space</span>
    </div>
  </div>

  <!-- 14-Panel Grid -->
  <div class="panels-container">
    {"".join(cards_html)}
  </div>

  <!-- Scorecard Row -->
  <div class="scorecard-row">
    {"".join(scorecards)}
  </div>

  <!-- Footer -->
  <div class="footer-row">
    <div>SYSTEM KEY: SAME METRIC COLOR ACROSS BEFORE/NOW (DOTTED = BEFORE, SOLID = NOW) // HIGHLIGHTED BORDERS = METRICS WITH SIGNIFICANT SHIFT</div>
    <div>GENERATED AUTONOMOUSLY VIA AAA TELEMETRY SUITE // SAVED IN: {out_dir.name}/</div>
  </div>

</body>
</html>"""

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    if capture_html_screenshot(html_file, png_file, width=1720, height=3380):
        print(f"  Generated 14-Panel Audit PNG: {png_file.name}")
    else:
        print(f"  Notice: Headless snapshot skipped; interactive HTML saved at {html_file.name}")

    return html_file, png_file


def render_single_audit_dashboard(
    dataset_name: str,
    turns: List[dict],
    out_dir: Path,
    custom_name: str = "telemetry_audit_dashboard",
) -> Tuple[Path, Path]:
    """Renders the 14-panel audit dashboard for a single conversation."""
    return render_14_panel_comparison_dashboard(
        run_a_name="",
        run_b_name=dataset_name,
        turns_a=[],
        turns_b=turns,
        comparison={"all_deltas": []},
        out_dir=out_dir,
        custom_name=custom_name,
    )


# Compatibility alias
plot_differential_changes = render_14_panel_comparison_dashboard


def plot_telemetry_oscilloscope(dataset_name: str, turns: List[dict], out_path: Path):
    """Single-dialogue 5-tier oscilloscope for single runs."""
    n_turns = len(turns)
    x = np.arange(1, n_turns + 1)

    def extract(key, fallback=None):
        vals = []
        for t in turns:
            v = t["metrics"].get(key)
            if v is None and fallback:
                v = t["metrics"].get(fallback)
            vals.append(v if v is not None else 0.0)
        return np.array(vals, dtype=float)

    novelty = extract("conceptual_novelty")
    velocity = extract("conceptual_velocity")
    surprise = extract("surprise_index")
    pask = extract("paskian_health")
    vitality = extract("vitality")
    deficit = extract("deficit")
    fp = extract("forward_perturbation")
    rp = extract("reverse_perturbation")
    mpi = extract("mutual_perturbation")
    entropy = extract("rolling_entropy")
    self_div = extract("agent_self_divergence")
    similarity = extract("pairwise_similarity")
    collapse = extract("collapse_pressure", "boringness")
    regimes = [t["metrics"].get("homeostatic_state", "flowing") for t in turns]
    phase_shifts = [len(t.get("phase_shifts", [])) > 0 for t in turns]

    fig, axes = plt.subplots(5, 1, figsize=(18, 15), sharex=True, gridspec_kw={"height_ratios": [1.2, 1.2, 1.1, 1.1, 1.0]})
    fig.patch.set_facecolor(BG_COLOR)
    for ax in axes:
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=SUBTEXT_COLOR, labelsize=9)
        ax.grid(True, linestyle="--", alpha=0.25, color=MPL_GRID_COLOR)
        for spine in ax.spines.values():
            spine.set_color(MPL_BORDER_COLOR)
        ax.xaxis.label.set_color(TEXT_COLOR)
        ax.yaxis.label.set_color(TEXT_COLOR)
        ax.title.set_color(TEXT_COLOR)

    fig.suptitle(
        f"CYBERNETIC TELEMETRY OSCILLOSCOPE: {dataset_name}\n"
        f"Horizon: T1 -> T{n_turns} | Calibrated 14-Dimension Telemetry Suite",
        fontsize=13, fontweight="bold", color=TEXT_COLOR, y=0.985
    )

    # Panel 1: Kinematics
    ax1 = axes[0]
    ax1.set_title("1. Kinematics & Trajectory Curvature", loc="left", fontsize=11, fontweight="bold", color=COLOR_ICE_CYAN)
    ax1.plot(x, novelty, color=COLOR_ICE_CYAN, lw=2.0, label=f"Novelty $N_t$ (μ={np.mean(novelty):.3f})")
    ax1.plot(x, velocity, color=COLOR_ORANGE_ALT, lw=2.0, label=f"Velocity $v_t$ (μ={np.mean(velocity):.3f})")
    ax1.plot(x, surprise, color=COLOR_VIOLET, lw=1.8, label=f"Surprise $S_t$ (μ={np.mean(surprise):.3f})")
    ax1.set_ylim(-0.02, 1.05)
    ax1.set_ylabel("Index [0, 1]", color=SUBTEXT_COLOR, fontsize=9)
    ax1.legend(loc="upper right", frameon=True, facecolor=PANEL_BG, edgecolor=MPL_BORDER_COLOR, fontsize=8.5, labelcolor=TEXT_COLOR)

    # Panel 2: Viability
    ax2 = axes[1]
    ax2.set_title("2. Cybernetic Viability & Paskian Homeostasis", loc="left", fontsize=11, fontweight="bold", color=COLOR_GREEN)
    ax2.plot(x, pask, color=COLOR_GREEN, lw=2.2, label=f"Pask Health $H_{{pask}}$ (μ={np.mean(pask):.3f})")
    ax2.plot(x, vitality, color=COLOR_ICE_CYAN, lw=2.0, label=f"Vitality $V_t$ (μ={np.mean(vitality):.3f})")
    ax2.plot(x, deficit, color="#EF4444", lw=1.8, linestyle="--", label=f"Deficit $D_t$ (μ={np.mean(deficit):.3f})")
    ax2.axhspan(0.45, 0.70, color=COLOR_GREEN, alpha=0.07, label="Homeostatic Viability Band [0.45, 0.70]")
    ax2.set_ylim(-0.02, 1.05)
    ax2.set_ylabel("Health / Load", color=SUBTEXT_COLOR, fontsize=9)
    ax2.legend(loc="upper right", frameon=True, facecolor=PANEL_BG, edgecolor=MPL_BORDER_COLOR, fontsize=8.5, labelcolor=TEXT_COLOR)

    # Panel 3: Perturbation
    ax3 = axes[2]
    ax3.set_title("3. Directional Perturbations & Reciprocal Coupling", loc="left", fontsize=11, fontweight="bold", color=COLOR_ORANGE)
    ax3.plot(x, fp, color=COLOR_ORANGE_ALT, lw=1.8, label=f"Forward Perturbation $fP_t$ (μ={np.mean(fp):.3f})")
    ax3.plot(x, rp, color=COLOR_ORANGE, lw=1.8, label=f"Reverse Perturbation $rP_t$ (μ={np.mean(rp):.3f})")
    ax3.plot(x, mpi, color=COLOR_GREEN, lw=2.0, label=f"Mutual Perturbation $MPI$ (μ={np.mean(mpi):.3f})")
    ax3.set_ylim(-0.02, 1.05)
    ax3.set_ylabel("Perturbation", color=SUBTEXT_COLOR, fontsize=9)
    ax3.legend(loc="upper right", frameon=True, facecolor=PANEL_BG, edgecolor=MPL_BORDER_COLOR, fontsize=8.5, labelcolor=TEXT_COLOR)

    # Panel 4: Topology
    ax4 = axes[3]
    ax4.set_title("4. Semantic Topology & Spectral Entropy", loc="left", fontsize=11, fontweight="bold", color=COLOR_VIOLET)
    ax4.plot(x, entropy, color=COLOR_VIOLET, lw=2.0, label=f"Spectral Entropy $H_{{ent}}$ (μ={np.mean(entropy):.3f})")
    ax4.plot(x, self_div, color=COLOR_ICE_CYAN, lw=1.8, label=f"Self-Divergence $D_{{self}}$ (μ={np.mean(self_div):.3f})")
    ax4.plot(x, similarity, color=COLOR_SLATE, lw=1.8, label=f"Similarity $s_t$ (μ={np.mean(similarity):.3f})")
    ax4.set_ylim(-0.02, 1.05)
    ax4.set_ylabel("Dispersion", color=SUBTEXT_COLOR, fontsize=9)
    ax4.legend(loc="upper right", frameon=True, facecolor=PANEL_BG, edgecolor=MPL_BORDER_COLOR, fontsize=8.5, labelcolor=TEXT_COLOR)

    # Panel 5: Regimes
    ax5 = axes[4]
    ax5.set_title("5. Collapse Pressure ($CP_t$), Homeostatic Regimes & Phase Shifts", loc="left", fontsize=11, fontweight="bold", color=COLOR_ORANGE)
    ax5.plot(x, collapse, color=COLOR_ORANGE, lw=2.0, label=f"Collapse Pressure (μ={np.mean(collapse):.3f})")
    ax5.axhline(0.65, color="#EF4444", linestyle="--", lw=1.5, label="Stagnation Line (0.65)")

    for i, reg in enumerate(regimes):
        if reg == "stagnant":
            ax5.axvspan(i + 0.5, i + 1.5, color="#EF4444", alpha=0.45)
        elif reg == "disrupted":
            ax5.axvspan(i + 0.5, i + 1.5, color="#F59E0B", alpha=0.45)

    shift_indices = [i + 1 for i, s in enumerate(phase_shifts) if s]
    if shift_indices:
        ax5.scatter(shift_indices, [0.95] * len(shift_indices), marker="|", color=COLOR_ICE_CYAN, s=35, alpha=0.75, label=f"Phase Shift Event ({len(shift_indices)})")

    ax5.set_ylim(-0.02, 1.05)
    ax5.set_ylabel("Pressure", color=SUBTEXT_COLOR, fontsize=9)
    ax5.set_xlabel("Dialogue Turn (Chronological Step)", color=TEXT_COLOR, fontsize=10, fontweight="bold")
    ax5.set_xlim(1, n_turns)

    legend_elements = [
        plt.Line2D([0], [0], color=COLOR_ORANGE, lw=2, label=f"Collapse Pressure (μ={np.mean(collapse):.3f})"),
        plt.Line2D([0], [0], color="#EF4444", lw=1.5, linestyle="--", label="Stagnation (0.65)"),
        Patch(facecolor=COLOR_GREEN, alpha=0.3, label=f"Flowing: {regimes.count('flowing')}/{n_turns}"),
        Patch(facecolor="#EF4444", alpha=0.5, label=f"Stagnant: {regimes.count('stagnant')}/{n_turns}"),
        plt.Line2D([0], [0], marker="|", color=COLOR_ICE_CYAN, lw=0, markersize=10, label=f"Phase Shifts: {len(shift_indices)}"),
    ]
    ax5.legend(handles=legend_elements, loc="upper right", frameon=True, facecolor=PANEL_BG, edgecolor=MPL_BORDER_COLOR, fontsize=8.5, labelcolor=TEXT_COLOR)

    plt.tight_layout(rect=[0, 0.01, 1, 0.96])
    plt.savefig(out_path, dpi=160, facecolor=BG_COLOR, edgecolor="none")
    plt.close()
    print(f"  Generated oscilloscope: {out_path.name}")


def plot_quartile_stability(dataset_name: str, turns: List[dict], out_path: Path):
    """Generates quartile stability bar charts for long conversations (>= 40 turns)."""
    n = len(turns)
    if n < 40:
        return
    q_len = n // 4
    q_ranges = [(0, q_len), (q_len, 2 * q_len), (2 * q_len, 3 * q_len), (3 * q_len, n)]
    q_labels = ["Q1 [Start]", "Q2 [Early]", "Q3 [Late]", "Q4 [Terminal]"]

    metrics = [
        ("pairwise_similarity", "Similarity (s_t)", COLOR_ICE_CYAN),
        ("deficit", "Deficit (D_t)", COLOR_ORANGE),
        ("vitality", "Vitality (V_t)", COLOR_GREEN),
        ("paskian_health", "Pask Health (H_pask)", COLOR_GREEN_ALT),
        ("conceptual_novelty", "Novelty (N_t)", COLOR_ICE_CYAN),
        ("collapse_pressure", "Collapse Pressure", COLOR_ORANGE),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.patch.set_facecolor(BG_COLOR)

    for idx, (m_key, m_label, m_col) in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=SUBTEXT_COLOR, labelsize=9)
        ax.grid(True, linestyle="--", alpha=0.25, color=MPL_GRID_COLOR)
        for spine in ax.spines.values():
            spine.set_color(MPL_BORDER_COLOR)
        ax.set_title(m_label, color=TEXT_COLOR, fontsize=10.5, fontweight="bold")
        ax.set_ylim(-0.02, 1.05)

        means = []
        for start, end in q_ranges:
            vals = [t["metrics"].get(m_key, 0.0) for t in turns[start:end] if t["metrics"].get(m_key) is not None]
            means.append(float(np.mean(vals)) if vals else 0.0)

        bars = ax.bar(q_labels, means, color=m_col, alpha=0.85, width=0.55, edgecolor=m_col)
        for b in bars:
            yval = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2.0, yval + 0.03, f"{yval:.3f}", ha="center", va="bottom", color=TEXT_COLOR, fontsize=8.5, fontweight="bold")

    fig.suptitle(
        f"LONG-HORIZON QUARTILE STABILITY MATRIX: {dataset_name} ({n} turns)",
        fontsize=12.5, fontweight="bold", color=TEXT_COLOR, y=0.98
    )
    plt.tight_layout(rect=[0, 0.02, 1, 0.95])
    plt.savefig(out_path, dpi=160, facecolor=BG_COLOR, edgecolor="none")
    plt.close()
    print(f"  Generated quartile stability plot: {out_path.name}")
