#!/usr/bin/env python3
"""
Cybernetic Benchmark Run Comparison Tool.

Compares multi-turn cybernetic telemetry across benchmark runs before and after metric updates
or between experimental configurations.

Renders a 10-panel high-resolution oscilloscope dashboard (HTML + PNG snapshot via headless Edge)
covering all newly calibrated and updated cybernetic metrics:
  1. Pairwise Similarity (s_t) - Calibrated denominator to sum(weights), eliminating 58% suppression
  2. Conversational Deficit - Calibrated dynamic weight normalization & unclamped spectral entropy
  3. Conversational Vitality - Calibrated allostatic vitality and dialetic liveliness
  4. Forward Perturbation (fP_t) - Calibrated agent-to-human directional trajectory perturbation
  5. Mutual Perturbation Index (MPI_t) - Geometric mean coupling sqrt(rP_t * fP_t)
  6. Reverse Perturbation (rP_t) - Human-to-agent trajectory tension
  7. Conceptual Novelty (N_t) - Semantic displacement from centroid EMA
  8. Collapse Pressure / Boringness (CP_t) - Stagnation interrupt alarm
  9. Divergence Resolution Ratio (DRR_t) - Dialectic homeostasis ratio
  10. Gordon Pask Cybernetic Health (H_pask) - Organizational closure & viability

Generates Markdown comparison matrices and synthesis reports into:
  reports/runs/<name>/
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RUNS_DIR = PROJECT_ROOT / "reports" / "runs"
REFERENCE_DIR = PROJECT_ROOT / "reports" / "003-empirical-10-turn-benchmark"


def find_edge_path() -> str:
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge"),
        shutil.which("chrome"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return ""


def discover_runs() -> list[Path]:
    """Find all valid benchmark run directories that contain conversation_receipts.json."""
    candidates: list[Path] = []

    # Check reference benchmark
    if (REFERENCE_DIR / "conversation_receipts.json").exists():
        candidates.append(REFERENCE_DIR)

    # Check runs directory
    if RUNS_DIR.exists():
        for d in RUNS_DIR.iterdir():
            if d.is_dir() and (d / "conversation_receipts.json").exists():
                candidates.append(d)

    # Sort by receipts mtime ascending so older runs are Run A and newer runs are Run B
    candidates.sort(key=lambda p: (p / "conversation_receipts.json").stat().st_mtime)
    return candidates


def resolve_run_path(name_or_path: str, available_runs: list[Path]) -> Path:
    """Resolve a run identifier to its directory path."""
    p = Path(name_or_path).resolve()
    if p.is_dir() and (p / "conversation_receipts.json").exists():
        return p

    if name_or_path.lower() in ("ref", "reference", "baseline_ref", "003"):
        if (REFERENCE_DIR / "conversation_receipts.json").exists():
            return REFERENCE_DIR

    # Check against subdirectories in reports/runs
    in_runs = RUNS_DIR / name_or_path
    if in_runs.is_dir() and (in_runs / "conversation_receipts.json").exists():
        return in_runs

    # Match by partial name in available runs
    for run in reversed(available_runs):
        if name_or_path.lower() in run.name.lower():
            return run

    raise FileNotFoundError(
        f"Could not find a valid benchmark run matching '{name_or_path}'. "
        f"Available runs: {[r.name for r in available_runs]}"
    )


def load_receipts(run_path: Path) -> dict:
    receipts_file = run_path / "conversation_receipts.json"
    with open(receipts_file, "r", encoding="utf-8") as f:
        return json.load(f)


def to_pts(series: list[float], y_max: float = 1.0, left: float = 65, right: float = 745, top: float = 22, bottom: float = 188) -> str:
    if len(series) <= 1:
        return f"{left},{bottom}"
    x_step = (right - left) / (len(series) - 1)
    pts = []
    for i, v in enumerate(series):
        x = left + i * x_step
        clamped = max(0.0, min(y_max, float(v)))
        y = bottom - (clamped / y_max) * (bottom - top)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def to_circ(series: list[float], y_max: float = 1.0, color: str = "#ffffff", r: float = 3.6, hollow: bool = False,
            left: float = 65, right: float = 745, top: float = 22, bottom: float = 188) -> str:
    if len(series) <= 1:
        return ""
    x_step = (right - left) / (len(series) - 1)
    circs = []
    for i, v in enumerate(series):
        x = left + i * x_step
        clamped = max(0.0, min(y_max, float(v)))
        y = bottom - (clamped / y_max) * (bottom - top)
        if hollow:
            circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#0c0e14" stroke="{color}" stroke-width="2.0" />')
        else:
            circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" />')
    return "\n".join(circs)


def make_grid(left: float = 65, right: float = 745, top: float = 22, bottom: float = 188,
              y_max: float = 1.0, y_ticks: int = 4, num_turns: int = 10) -> str:
    lines = []
    for i in range(y_ticks + 1):
        val = (y_ticks - i) * (y_max / y_ticks)
        y = top + i * (bottom - top) / y_ticks
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="rgba(255,255,255,0.07)" stroke-width="1" />')
        lines.append(f'<text x="{left - 10}" y="{y + 3.5:.1f}" fill="#717684" font-size="10" font-family="JetBrains Mono, monospace" text-anchor="end">{val:.2f}</text>')

    for i in range(num_turns):
        x = left + i * (right - left) / max(1, num_turns - 1)
        lines.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />')
        lines.append(f'<text x="{x:.1f}" y="{bottom + 17}" fill="#717684" font-size="10" font-family="JetBrains Mono, monospace" text-anchor="middle">T{i+1}</text>')

    return "\n".join(lines)


def render_comparison_dashboard(
    run_a_name: str,
    run_b_name: str,
    data_a: dict,
    data_b: dict,
    out_dir: Path,
    custom_name: str = "",
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)

    base_a = data_a.get("baseline", [])
    base_b = data_b.get("baseline", [])
    aaa_a = data_a.get("aaa", [])
    aaa_b = data_b.get("aaa", [])

    num_turns = max(len(base_a), len(base_b), len(aaa_a), len(aaa_b), 10)

    def extract(turns: list, key: str, fallback_key: str = "", default: float = 0.0) -> list[float]:
        res = []
        for t in turns[:num_turns]:
            m = t.get("metrics", {})
            val = m.get(key)
            if val is None and fallback_key:
                val = m.get(fallback_key)
            res.append(float(val) if val is not None else default)
        return res

    def mean(lst: list[float]) -> float:
        return sum(lst) / max(1, len(lst))

    # 1. Pairwise Similarity (s_t) - CALIBRATED DENOMINATOR
    base_sim_a = extract(base_a, "pairwise_similarity", "s_t", default=0.0)
    base_sim_b = extract(base_b, "pairwise_similarity", "s_t", default=0.0)
    aaa_sim_a = extract(aaa_a, "pairwise_similarity", "s_t", default=0.0)
    aaa_sim_b = extract(aaa_b, "pairwise_similarity", "s_t", default=0.0)

    # 2. Conversational Deficit - CALIBRATED DYNAMIC WEIGHTS
    base_def_a = extract(base_a, "deficit", "homeostatic_deficit", default=0.0)
    base_def_b = extract(base_b, "deficit", "homeostatic_deficit", default=0.0)
    aaa_def_a = extract(aaa_a, "deficit", "homeostatic_deficit", default=0.0)
    aaa_def_b = extract(aaa_b, "deficit", "homeostatic_deficit", default=0.0)

    # 3. Conversational Vitality - CALIBRATED VITALITY
    base_vit_a = extract(base_a, "vitality", "conversation_vitality", default=0.0)
    base_vit_b = extract(base_b, "vitality", "conversation_vitality", default=0.0)
    aaa_vit_a = extract(aaa_a, "vitality", "conversation_vitality", default=0.0)
    aaa_vit_b = extract(aaa_b, "vitality", "conversation_vitality", default=0.0)

    # 4. Forward Perturbation (fP_t) - CALIBRATED BILATERAL
    base_fpert_a = extract(base_a, "forward_perturbation", default=0.0)
    base_fpert_b = extract(base_b, "forward_perturbation", default=0.0)
    aaa_fpert_a = extract(aaa_a, "forward_perturbation", default=0.0)
    aaa_fpert_b = extract(aaa_b, "forward_perturbation", default=0.0)

    # 5. Mutual Perturbation Index (MPI_t) - CALIBRATED GEOMETRIC MEAN
    base_mpi_a = extract(base_a, "mutual_perturbation", default=0.0)
    base_mpi_b = extract(base_b, "mutual_perturbation", default=0.0)
    aaa_mpi_a = extract(aaa_a, "mutual_perturbation", default=0.0)
    aaa_mpi_b = extract(aaa_b, "mutual_perturbation", default=0.0)

    # 6. Reverse Perturbation (rP_t)
    base_rpert_a = extract(base_a, "reverse_perturbation", default=0.0)
    base_rpert_b = extract(base_b, "reverse_perturbation", default=0.0)
    aaa_rpert_a = extract(aaa_a, "reverse_perturbation", default=0.0)
    aaa_rpert_b = extract(aaa_b, "reverse_perturbation", default=0.0)

    # 7. Conceptual Novelty (N_t)
    base_nov_a = extract(base_a, "conceptual_novelty", default=0.0)
    base_nov_b = extract(base_b, "conceptual_novelty", default=0.0)
    aaa_nov_a = extract(aaa_a, "conceptual_novelty", default=0.0)
    aaa_nov_b = extract(aaa_b, "conceptual_novelty", default=0.0)

    # 8. Collapse Pressure / Boringness (CP_t)
    base_col_a = extract(base_a, "collapse_pressure", "boringness", default=0.0)
    base_col_b = extract(base_b, "collapse_pressure", "boringness", default=0.0)
    aaa_col_a = extract(aaa_a, "collapse_pressure", "boringness", default=0.0)
    aaa_col_b = extract(aaa_b, "collapse_pressure", "boringness", default=0.0)

    # 9. Divergence Resolution Ratio (DRR)
    base_drr_a = extract(base_a, "divergence_resolution_ratio", default=0.5)
    base_drr_b = extract(base_b, "divergence_resolution_ratio", default=0.5)
    aaa_drr_a = extract(aaa_a, "divergence_resolution_ratio", default=0.5)
    aaa_drr_b = extract(aaa_b, "divergence_resolution_ratio", default=0.5)

    # 10. Gordon Pask Cybernetic Health (H_pask)
    base_pask_a = extract(base_a, "paskian_health", default=0.0)
    base_pask_b = extract(base_b, "paskian_health", default=0.0)
    aaa_pask_a = extract(aaa_a, "paskian_health", default=0.0)
    aaa_pask_b = extract(aaa_b, "paskian_health", default=0.0)

    # Deltas
    sim_delta_b = mean(aaa_sim_b) - mean(base_sim_b)
    def_delta_b = mean(aaa_def_b) - mean(base_def_b)
    vit_delta_b = mean(aaa_vit_b) - mean(base_vit_b)
    mpi_delta_b = mean(aaa_mpi_b) - mean(base_mpi_b)
    nov_delta_b = mean(aaa_nov_b) - mean(base_nov_b)
    pask_delta_b = mean(aaa_pask_b) - mean(base_pask_b)

    # Metadata strings
    meta_a_model = data_a.get("aaa_model") or data_a.get("baseline_model", "Unknown")
    meta_b_model = data_b.get("aaa_model") or data_b.get("baseline_model", "Unknown")
    time_a = data_a.get("timestamp", "Run A")
    time_b = data_b.get("timestamp", "Run B")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Benchmark Run Comparison: {run_a_name} vs. {run_b_name}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background-color: #060709; color: #e4e7ec; font-family: 'JetBrains Mono', monospace;
    width: 1720px; height: 2420px; padding: 26px 34px; display: flex; flex-direction: column;
    justify-content: space-between; position: relative;
    background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.06) 1px, transparent 0);
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
    background: rgba(0, 229, 255, 0.12); color: #00e5ff; border: 1px solid rgba(0, 229, 255, 0.35);
    font-size: 11px; padding: 3px 10px; border-radius: 4px; font-weight: 700; letter-spacing: 0.8px;
  }}
  .subtitle {{
    font-size: 11.5px; color: #88909e; margin-top: 4px; font-family: 'Inter', sans-serif;
  }}
  .header-meta {{
    text-align: right; font-size: 10.5px; color: #717684; line-height: 1.6;
  }}
  .header-meta span {{ color: #00e5ff; font-weight: 600; }}

  /* Global Legend Bar */
  .legend-bar {{
    display: flex; justify-content: space-between; align-items: center;
    background: rgba(255,255,255,0.025); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px; padding: 7px 18px; margin-top: 10px; font-size: 11px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; }}
  .line-sample {{ width: 22px; height: 3px; border-radius: 2px; display: inline-block; }}
  .dot-sample {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}

  /* 10-Panel Oscilloscope Grid (2 cols x 5 rows) */
  .panels-container {{
    display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: repeat(5, 1fr);
    gap: 12px; margin: 12px 0; flex: 1;
  }}
  .panel-card {{
    background: #0c0e14; border: 1px solid rgba(255,255,255,0.11); border-radius: 8px;
    padding: 10px 16px; display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 6px 20px rgba(0,0,0,0.45); position: relative; overflow: hidden;
  }}
  .panel-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #00e5ff, #b026ff, #ff9944);
  }}
  .card-top {{
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2px;
  }}
  .panel-title {{
    font-size: 12.5px; font-weight: 800; letter-spacing: 0.8px; color: #ffffff;
  }}
  .panel-desc {{
    font-size: 9.5px; color: #88909e; font-family: 'Inter', sans-serif; margin-top: 2px; line-height: 1.3;
  }}
  .card-badge {{
    font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 3px; letter-spacing: 0.5px;
    white-space: nowrap;
  }}
  .badge-cyan {{ background: rgba(0,229,255,0.15); color: #00e5ff; border: 1px solid rgba(0,229,255,0.3); }}
  .badge-orange {{ background: rgba(255,153,68,0.15); color: #ff9944; border: 1px solid rgba(255,153,68,0.3); }}
  .badge-mint {{ background: rgba(0,255,170,0.15); color: #00ffaa; border: 1px solid rgba(0,255,170,0.3); }}
  .badge-purple {{ background: rgba(176,38,255,0.15); color: #d175ff; border: 1px solid rgba(176,38,255,0.3); }}
  .badge-yellow {{ background: rgba(255,204,0,0.15); color: #ffcc00; border: 1px solid rgba(255,204,0,0.3); }}

  /* SVG Plot */
  .svg-plot {{ width: 100%; height: 215px; }}

  /* Card Stat Footers */
  .card-stat-bar {{
    display: flex; justify-content: space-between; align-items: center;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);
    border-radius: 4px; padding: 3px 10px; margin-top: 2px; font-size: 9.5px; color: #88909e;
  }}
  .card-stat-val {{ font-weight: 700; color: #ffffff; }}

  /* Scoreboard */
  .bottom-scoreboard {{
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px;
    background: #0a0c12; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    padding: 10px 16px; align-items: center;
  }}
  .score-card {{ border-left: 2px solid rgba(255,255,255,0.12); padding-left: 12px; }}
  .score-card:first-child {{ border-left: 2px solid #00e5ff; }}
  .score-card:nth-child(2) {{ border-left: 2px solid #ff9944; }}
  .score-card:nth-child(3) {{ border-left: 2px solid #00ffaa; }}
  .score-card:nth-child(4) {{ border-left: 2px solid #ffcc00; }}
  .score-card:nth-child(5) {{ border-left: 2px solid #b026ff; }}
  .score-card:nth-child(6) {{ border-left: 2px solid #00e5ff; }}
  .score-label {{ font-size: 8.5px; color: #717684; text-transform: uppercase; letter-spacing: 0.8px; }}
  .score-val {{ font-size: 13px; font-weight: 800; margin: 2px 0; color: #ffffff; }}
  .score-sub {{ font-size: 8.5px; color: #88909e; font-family: 'Inter', sans-serif; }}

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
      <h1>
        CYBERNETIC TELEMETRY AUDIT
        <span class="badge-primary">{run_a_name} vs. {run_b_name}</span>
      </h1>
      <div class="subtitle">
        Calibrated 10-metric comparison dashboard across 10-turn adversarial stress testing.
      </div>
    </div>
    <div class="header-meta">
      Run A ({run_a_name}): <span>{meta_a_model}</span> ({time_a})<br/>
      Run B ({run_b_name}): <span>{meta_b_model}</span> ({time_b})<br/>
      Status: <span>CALIBRATED FULL METRICS SUITE</span>
    </div>
  </div>

  <!-- Global Unified Legend -->
  <div class="legend-bar">
    <div class="legend-item">
      <span class="line-sample" style="background: #00e5ff;"></span>
      <span class="dot-sample" style="background: #00e5ff;"></span>
      <span><strong>AAA [{run_b_name}]:</strong> Solid Cyan</span>
    </div>
    <div class="legend-item">
      <span class="line-sample" style="border-top: 2px dashed #b026ff;"></span>
      <span class="dot-sample" style="border: 2px solid #b026ff; background: #0c0e14;"></span>
      <span style="color: #d175ff;"><strong>AAA [{run_a_name}]:</strong> Dashed Violet</span>
    </div>
    <div class="legend-item">
      <span class="line-sample" style="background: #ff9944;"></span>
      <span class="dot-sample" style="background: #ff9944;"></span>
      <span><strong>Base [{run_b_name}]:</strong> Solid Amber</span>
    </div>
    <div class="legend-item">
      <span class="line-sample" style="border-top: 2px dashed #ff4466;"></span>
      <span class="dot-sample" style="border: 2px solid #ff4466; background: #0c0e14;"></span>
      <span style="color: #ff6b85;"><strong>Base [{run_a_name}]:</strong> Dashed Red</span>
    </div>
    <div class="legend-item">
      <span style="color: #717684; font-size: 10px;">Domain: [0.00, 1.00] Normalized Dialectic Space</span>
    </div>
  </div>

  <!-- 10-Panel Grid -->
  <div class="panels-container">

    <!-- Panel 1: Pairwise Similarity (CALIBRATED) -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">1. PAIRWISE SIMILARITY (s_t) &mdash; CALIBRATED</div>
          <div class="panel-desc">Reciprocal displacement coherence normalized by &sum; w_i (eliminating 58% suppression cap)</div>
        </div>
        <span class="card-badge badge-cyan">MANIFOLD COHERENCE</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="22" width="680" height="49" fill="rgba(0, 229, 255, 0.035)" />
        <text x="735" y="34" fill="rgba(0, 229, 255, 0.4)" font-size="9" text-anchor="end">HIGH COHERENCE ZONE [0.70 - 1.00]</text>

        <rect x="65" y="138" width="680" height="50" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="182" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">DISSOCIATION BASIN [0.00 - 0.30]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_sim_a, y_max=1.0)}" />
        {to_circ(aaa_sim_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_sim_a, y_max=1.0)}" />
        {to_circ(base_sim_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_sim_b, y_max=1.0)}" />
        {to_circ(base_sim_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_sim_b, y_max=1.0)}" />
        {to_circ(aaa_sim_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_sim_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_sim_b[-1]:.3f}</strong></span>
        <span>Run B Similarity Delta: <strong style="color: #00e5ff;">{sim_delta_b:+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 2: Conversational Deficit (CALIBRATED) -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">2. CONVERSATIONAL DEFICIT &mdash; CALIBRATED</div>
          <div class="panel-desc">Allostatic load tracking perturbation, velocity, and entropy deficits normalized dynamically by weights</div>
        </div>
        <span class="card-badge badge-orange">ALLOSTATIC DEFICIT</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="22" width="680" height="49" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="34" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">CRITICAL DEFICIT STRAIN [0.70 - 1.00]</text>

        <rect x="65" y="138" width="680" height="50" fill="rgba(0, 255, 170, 0.035)" />
        <text x="735" y="182" fill="rgba(0, 255, 170, 0.4)" font-size="9" text-anchor="end">HOMEOSTATIC BALANCE [0.00 - 0.30]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_def_a, y_max=1.0)}" />
        {to_circ(aaa_def_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_def_a, y_max=1.0)}" />
        {to_circ(base_def_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_def_b, y_max=1.0)}" />
        {to_circ(base_def_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_def_b, y_max=1.0)}" />
        {to_circ(aaa_def_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_def_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_def_b[-1]:.3f}</strong></span>
        <span>Run B Deficit Suppression: <strong style="color: #ff9944;">{def_delta_b:+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 3: Conversational Vitality (CALIBRATED) -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">3. CONVERSATIONAL VITALITY &mdash; CALIBRATED</div>
          <div class="panel-desc">Allostatic vitality measuring dialectic liveliness: 1.0 - Deficit with unclamped entropy integration</div>
        </div>
        <span class="card-badge badge-mint">ALLOSTATIC VITALITY</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="22" width="680" height="66" fill="rgba(0, 255, 170, 0.035)" />
        <text x="735" y="34" fill="rgba(0, 255, 170, 0.4)" font-size="9" text-anchor="end">HIGH VITALITY ZONE [0.60 - 1.00]</text>

        <rect x="65" y="138" width="680" height="50" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="182" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">METABOLIC COLLAPSE [0.00 - 0.30]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_vit_a, y_max=1.0)}" />
        {to_circ(aaa_vit_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_vit_a, y_max=1.0)}" />
        {to_circ(base_vit_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_vit_b, y_max=1.0)}" />
        {to_circ(base_vit_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_vit_b, y_max=1.0)}" />
        {to_circ(aaa_vit_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_vit_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_vit_b[-1]:.3f}</strong></span>
        <span>Run B Vitality Advantage: <strong style="color: #00ffaa;">{vit_delta_b:+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 4: Forward Perturbation (CALIBRATED) -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">4. FORWARD PERTURBATION (fP_t) &mdash; CALIBRATED</div>
          <div class="panel-desc">Agent-induced displacement shift on human thought vector: 1 - cos(a_t - a_{{t-1}}, h_t - a_{{t-1}})</div>
        </div>
        <span class="card-badge badge-yellow">AGENT PERTURBATION</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="72" width="680" height="50" fill="rgba(255, 204, 0, 0.035)" />
        <text x="735" y="84" fill="rgba(255, 204, 0, 0.4)" font-size="9" text-anchor="end">ACTIVE DIALECTIC PERTURBATION [0.40 - 0.70]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_fpert_a, y_max=1.0)}" />
        {to_circ(aaa_fpert_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_fpert_a, y_max=1.0)}" />
        {to_circ(base_fpert_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_fpert_b, y_max=1.0)}" />
        {to_circ(base_fpert_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_fpert_b, y_max=1.0)}" />
        {to_circ(aaa_fpert_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_fpert_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_fpert_b[-1]:.3f}</strong></span>
        <span>Run B Mean fP: <strong style="color: #ffcc00;">AAA {mean(aaa_fpert_b):.3f}</strong> / <strong style="color: #ff9944;">Base {mean(base_fpert_b):.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 5: Mutual Perturbation Index (CALIBRATED) -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">5. MUTUAL PERTURBATION INDEX (MPI_t) &mdash; CALIBRATED</div>
          <div class="panel-desc">Bilateral dialectic coupling geometric mean: MPI_t = &radic;(rP_t &middot; fP_t)</div>
        </div>
        <span class="card-badge badge-purple">RECIPROCAL COUPLING</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="55" width="680" height="50" fill="rgba(176, 38, 255, 0.035)" />
        <text x="735" y="67" fill="rgba(176, 38, 255, 0.4)" font-size="9" text-anchor="end">CONSTRUCTIVE COUPLING [0.50 - 0.80]</text>

        <rect x="65" y="155" width="680" height="33" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="182" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">DECOUPLED BASIN [0.00 - 0.20]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_mpi_a, y_max=1.0)}" />
        {to_circ(aaa_mpi_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_mpi_a, y_max=1.0)}" />
        {to_circ(base_mpi_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_mpi_b, y_max=1.0)}" />
        {to_circ(base_mpi_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_mpi_b, y_max=1.0)}" />
        {to_circ(aaa_mpi_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_mpi_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_mpi_b[-1]:.3f}</strong></span>
        <span>Run B Coupling Delta: <strong style="color: #d175ff;">{mpi_delta_b:+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 6: Reverse Perturbation -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">6. REVERSE PERTURBATION (rP_t)</div>
          <div class="panel-desc">Human-induced trajectory shift in agent state: 1 - cos(h_t - h_{{t-1}}, a_t - h_{{t-1}})</div>
        </div>
        <span class="card-badge badge-mint">TRAJECTORY TENSION</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="72" width="680" height="50" fill="rgba(0, 255, 170, 0.035)" />
        <text x="735" y="84" fill="rgba(0, 255, 170, 0.4)" font-size="9" text-anchor="end">CONSTRUCTIVE PERTURBATION [0.40 - 0.70]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_rpert_a, y_max=1.0)}" />
        {to_circ(aaa_rpert_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_rpert_a, y_max=1.0)}" />
        {to_circ(base_rpert_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_rpert_b, y_max=1.0)}" />
        {to_circ(base_rpert_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_rpert_b, y_max=1.0)}" />
        {to_circ(aaa_rpert_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_rpert_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_rpert_b[-1]:.3f}</strong></span>
        <span>Run B Mean rP: <strong style="color: #00e5ff;">AAA {mean(aaa_rpert_b):.3f}</strong> / <strong style="color: #ff9944;">Base {mean(base_rpert_b):.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 7: Conceptual Novelty -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">7. CONCEPTUAL NOVELTY (N_t)</div>
          <div class="panel-desc">Semantic displacement from context centroid EMA: N_t = ||v_t - c_t||_2</div>
        </div>
        <span class="card-badge badge-cyan">SEMANTIC DISPLACEMENT</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="22" width="680" height="49" fill="rgba(0, 229, 255, 0.035)" />
        <text x="735" y="34" fill="rgba(0, 229, 255, 0.4)" font-size="9" text-anchor="end">PARADIGM EXPLORATION [0.70 - 1.00]</text>

        <rect x="65" y="121" width="680" height="67" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="182" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">REPETITIVE STAGNATION BASIN [0.00 - 0.40]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_nov_a, y_max=1.0)}" />
        {to_circ(aaa_nov_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_nov_a, y_max=1.0)}" />
        {to_circ(base_nov_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_nov_b, y_max=1.0)}" />
        {to_circ(base_nov_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_nov_b, y_max=1.0)}" />
        {to_circ(aaa_nov_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_nov_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_nov_b[-1]:.3f}</strong></span>
        <span>Run B Novelty Advantage: <strong style="color: #00e5ff;">{nov_delta_b:+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 8: Collapse Pressure -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">8. COLLAPSE PRESSURE (BORINGNESS)</div>
          <div class="panel-desc">Allostatic stagnation alarm: 0.40&middot;pert_fail + 0.30&middot;(1-H) + 0.30&middot;(1-N)</div>
        </div>
        <span class="card-badge badge-orange">STAGNATION REGULATION</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <line x1="65" y1="{188 - 0.70 * 166}" x2="745" y2="{188 - 0.70 * 166}" stroke="#ff3366" stroke-width="1.6" stroke-dasharray="4,4" />
        <text x="735" y="{188 - 0.70 * 166 - 4}" fill="#ff3366" font-size="9" text-anchor="end">SEDATION INTERRUPT (0.70)</text>

        <line x1="65" y1="{188 - 0.40 * 166}" x2="745" y2="{188 - 0.40 * 166}" stroke="#00ffaa" stroke-width="1.4" stroke-dasharray="3,3" opacity="0.85" />
        <text x="735" y="{188 - 0.40 * 166 + 11}" fill="#00ffaa" font-size="9" text-anchor="end">FLOWING CEILING (0.40)</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_col_a, y_max=1.0)}" />
        {to_circ(aaa_col_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_col_a, y_max=1.0)}" />
        {to_circ(base_col_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_col_b, y_max=1.0)}" />
        {to_circ(base_col_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_col_b, y_max=1.0)}" />
        {to_circ(aaa_col_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_col_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_col_b[-1]:.3f}</strong></span>
        <span>Run B Stagnation Delta: <strong style="color: #ff9944;">{mean(aaa_col_b) - mean(base_col_b):+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 9: Divergence Resolution Ratio -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">9. DIVERGENCE RESOLUTION RATIO (DRR)</div>
          <div class="panel-desc">Ratio of resolved dialectic tension to open systemic divergence: min(1.0, D_res / D_open)</div>
        </div>
        <span class="card-badge badge-mint">DIALECTIC HOMEOSTASIS</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="22" width="680" height="33" fill="rgba(0, 255, 170, 0.04)" />
        <text x="735" y="34" fill="rgba(0, 255, 170, 0.5)" font-size="9" text-anchor="end">BALANCED RESOLUTION ZONE [0.80 - 1.00]</text>

        <rect x="65" y="121" width="680" height="67" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="182" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">FRAGMENTATION BASIN [0.00 - 0.40]</text>

        <line x1="65" y1="{188 - 0.50 * 166}" x2="745" y2="{188 - 0.50 * 166}" stroke="rgba(255,255,255,0.25)" stroke-width="1" stroke-dasharray="3,3" />

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_drr_a, y_max=1.0)}" />
        {to_circ(aaa_drr_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_drr_a, y_max=1.0)}" />
        {to_circ(base_drr_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_drr_b, y_max=1.0)}" />
        {to_circ(base_drr_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_drr_b, y_max=1.0)}" />
        {to_circ(aaa_drr_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_drr_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_drr_b[-1]:.3f}</strong></span>
        <span>Run B Homeostatic Delta: <strong style="color: #00ffaa;">{mean(aaa_drr_b) - mean(base_drr_b):+.3f}</strong></span>
      </div>
    </div>

    <!-- Panel 10: Gordon Pask Cybernetic Health -->
    <div class="panel-card">
      <div class="card-top">
        <div>
          <div class="panel-title">10. GORDON PASK CYBERNETIC HEALTH (H_pask)</div>
          <div class="panel-desc">Composite dialectic vitality: 0.35&middot;N + 0.25&middot;H_ent + 0.20&middot;(1-MPI) + 0.20&middot;DRR</div>
        </div>
        <span class="card-badge badge-purple">ORGANIZATIONAL CLOSURE</span>
      </div>

      <svg class="svg-plot" viewBox="0 0 780 216">
        <rect x="65" y="22" width="680" height="66" fill="rgba(0, 229, 255, 0.035)" />
        <text x="735" y="34" fill="rgba(0, 229, 255, 0.4)" font-size="9" text-anchor="end">HIGH VITALITY ZONE [0.60 - 1.00]</text>

        <rect x="65" y="138" width="680" height="50" fill="rgba(255, 68, 102, 0.04)" />
        <text x="735" y="182" fill="rgba(255, 68, 102, 0.4)" font-size="9" text-anchor="end">METABOLIC COLLAPSE BASIN [0.00 - 0.30]</text>

        {make_grid(left=65, right=745, top=22, bottom=188, y_max=1.0, y_ticks=4, num_turns=num_turns)}

        <!-- Run A (Dashed) -->
        <polyline fill="none" stroke="#b026ff" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(aaa_pask_a, y_max=1.0)}" />
        {to_circ(aaa_pask_a, y_max=1.0, color="#b026ff", r=3.0, hollow=True)}

        <polyline fill="none" stroke="#ff4466" stroke-width="1.8" stroke-dasharray="5,4" opacity="0.75" points="{to_pts(base_pask_a, y_max=1.0)}" />
        {to_circ(base_pask_a, y_max=1.0, color="#ff4466", r=3.0, hollow=True)}

        <!-- Run B (Solid) -->
        <polyline fill="none" stroke="#ff9944" stroke-width="2.6" points="{to_pts(base_pask_b, y_max=1.0)}" />
        {to_circ(base_pask_b, y_max=1.0, color="#ff9944", r=3.6, hollow=False)}

        <polyline fill="none" stroke="#00e5ff" stroke-width="2.8" points="{to_pts(aaa_pask_b, y_max=1.0)}" />
        {to_circ(aaa_pask_b, y_max=1.0, color="#00e5ff", r=3.6, hollow=False)}
      </svg>

      <div class="card-stat-bar">
        <span>Terminal T{num_turns}: <strong class="card-stat-val">AAA: {aaa_pask_b[-1]:.3f}</strong> vs <strong class="card-stat-val">Base: {base_pask_b[-1]:.3f}</strong></span>
        <span>Run B Cybernetic Vitality Delta: <strong style="color: #d175ff;">{pask_delta_b:+.3f}</strong></span>
      </div>
    </div>

  </div>

  <!-- Scoreboard -->
  <div class="bottom-scoreboard">
    <div class="score-card">
      <div class="score-label">Run B Final Similarity (s_t)</div>
      <div class="score-val" style="color: #00e5ff;">AAA: {aaa_sim_b[-1]:.3f} // Base: {base_sim_b[-1]:.3f}</div>
      <div class="score-sub">T{num_turns} manifold coherence</div>
    </div>
    <div class="score-card">
      <div class="score-label">Run B Final Deficit</div>
      <div class="score-val" style="color: #ff9944;">AAA: {aaa_def_b[-1]:.3f} // Base: {base_def_b[-1]:.3f}</div>
      <div class="score-sub">T{num_turns} allostatic stress</div>
    </div>
    <div class="score-card">
      <div class="score-label">Run B Final Vitality</div>
      <div class="score-val" style="color: #00ffaa;">AAA: {aaa_vit_b[-1]:.3f} // Base: {base_vit_b[-1]:.3f}</div>
      <div class="score-sub">T{num_turns} dialectic liveliness</div>
    </div>
    <div class="score-card">
      <div class="score-label">Run B Final Forward Pert (fP)</div>
      <div class="score-val" style="color: #ffcc00;">AAA: {aaa_fpert_b[-1]:.3f} // Base: {base_fpert_b[-1]:.3f}</div>
      <div class="score-sub">T{num_turns} agent impact</div>
    </div>
    <div class="score-card">
      <div class="score-label">Run B Final Mutual Pert (MPI)</div>
      <div class="score-val" style="color: #d175ff;">AAA: {aaa_mpi_b[-1]:.3f} // Base: {base_mpi_b[-1]:.3f}</div>
      <div class="score-sub">T{num_turns} bilateral coupling</div>
    </div>
    <div class="score-card">
      <div class="score-label">Run B Final Pask Health</div>
      <div class="score-val" style="color: #00e5ff;">AAA: {aaa_pask_b[-1]:.3f} // Base: {base_pask_b[-1]:.3f}</div>
      <div class="score-sub">T{num_turns} cybernetic health</div>
    </div>
  </div>

  <!-- Footer -->
  <div class="footer-row">
    <div>SYSTEM KEY: SOLID TRACES = {run_b_name} (LATEST) // DASHED TRACES = {run_a_name} (REFERENCE)</div>
    <div>GENERATED AUTONOMOUSLY VIA AAA TELEMETRY SUITE // SAVED IN: {out_dir.name}/</div>
  </div>

</body>
</html>
"""
    clean_a = "".join(c for c in run_a_name if c.isalnum() or c in ("-", "_"))
    clean_b = "".join(c for c in run_b_name if c.isalnum() or c in ("-", "_"))
    prefix = custom_name if custom_name else f"comparison_{clean_a}_vs_{clean_b}"

    html_file = out_dir / f"{prefix}.html"
    png_file = out_dir / f"{prefix}.png"

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  Saved HTML: {html_file}")

    edge_bin = find_edge_path()
    if edge_bin:
        cmd = [
            edge_bin,
            "--headless",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=1720,2420",
            f"--screenshot={png_file}",
            f"file:///{str(html_file).replace(os.sep, '/')}",
        ]
        subprocess.run(cmd, capture_output=True)
        print(f"  Generated PNG: {png_file}")
    else:
        print("  WARNING: Chrome/Edge not found; SVG dashboard available in HTML only.")

    # Generate Markdown Summary
    summary_file = out_dir / "comparison_summary.md"
    write_comparison_summary(run_a_name, run_b_name, data_a, data_b, summary_file, png_file.name)
    print(f"  Generated Summary: {summary_file}")

    return html_file, png_file


def write_comparison_summary(run_a_name: str, run_b_name: str, data_a: dict, data_b: dict, out_file: Path, png_name: str):
    base_a = data_a.get("baseline", [])
    base_b = data_b.get("baseline", [])
    aaa_a = data_a.get("aaa", [])
    aaa_b = data_b.get("aaa", [])
    num_turns = min(10, max(len(base_a), len(base_b), len(aaa_a), len(aaa_b)))

    def safe_val(turns: list, idx: int, key: str, fallback_key: str = ""):
        if idx >= len(turns):
            return None
        m = turns[idx].get("metrics", {})
        val = m.get(key)
        if val is None and fallback_key:
            val = m.get(fallback_key)
        return val

    def fmt(v):
        return f"{v:.3f}" if v is not None else "-"

    lines = [
        f"# Cybernetic Benchmark Comparison: {run_a_name} vs. {run_b_name}",
        f"\n**Run A (Reference):** `{run_a_name}` | Model: `{data_a.get('baseline_model') or data_a.get('aaa_model', 'Unknown')}`  ",
        f"**Run B (Target):** `{run_b_name}` | Model: `{data_b.get('baseline_model') or data_b.get('aaa_model', 'Unknown')}`  ",
        f"**Comparison Date:** {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}  \n",
        f"![Oscilloscope Telemetry Dashboard](./{png_name})\n",
        "## Executive Summary & Calibrated Telemetry Matrix\n",
        "This report contrasts multi-turn cybernetic dynamics between the reference run and the latest calibrated run.",
        "All metrics below reflect updated calibrations (eliminating zero-saturation, inverted exponent bugs, and stale history index bugs).\n"
    ]

    metric_sections = [
        ("1. Pairwise Similarity ($s_t$)", "pairwise_similarity", "s_t", "Reciprocal displacement coherence normalized by sum of active weights."),
        ("2. Conversational Deficit", "deficit", "homeostatic_deficit", "Allostatic load tracking perturbation, velocity, and entropy deficits."),
        ("3. Conversational Vitality", "vitality", "conversation_vitality", "Allostatic vitality measuring dialectic liveliness and residual reserve."),
        ("4. Forward Perturbation ($fP_t$)", "forward_perturbation", "", "Agent-induced displacement shift on human thought vector."),
        ("5. Mutual Perturbation Index ($MPI_t$)", "mutual_perturbation", "", "Geometric mean reciprocal coupling between user and agent trajectories."),
        ("6. Reverse Perturbation ($rP_t$)", "reverse_perturbation", "", "Human-induced trajectory shift in agent thought vector."),
        ("7. Conceptual Novelty ($N_t$)", "conceptual_novelty", "", "Semantic displacement from context centroid EMA."),
        ("8. Collapse Pressure / Boringness", "collapse_pressure", "boringness", "Allostatic stagnation alarm tracking perturbation, entropy, and novelty failures."),
        ("9. Divergence Resolution Ratio ($DRR_t$)", "divergence_resolution_ratio", "", "Ratio of resolved dialectic tension to open systemic divergence."),
        ("10. Gordon Pask Cybernetic Health ($H_{pask}$)", "paskian_health", "", "Composite dialectic vitality across novelty, variety, and mutual learning.")
    ]

    for sec_title, key, fallback, desc in metric_sections:
        lines.append(f"\n### {sec_title}\n*{desc}*\n")
        lines.append(f"| Turn | Human Prompt Snippet | Base ({run_a_name}) | Base ({run_b_name}) | AAA ({run_a_name}) | AAA ({run_b_name}) |")
        lines.append("| :---: | :--- | :---: | :---: | :---: | :---: |")

        for i in range(num_turns):
            user_text = (base_b[i].get("user") if i < len(base_b) else (base_a[i].get("user") if i < len(base_a) else f"Turn {i+1}"))
            prompt_snip = (user_text[:38] + "...").replace("|", "-")
            b_a = fmt(safe_val(base_a, i, key, fallback))
            b_b = fmt(safe_val(base_b, i, key, fallback))
            a_a = fmt(safe_val(aaa_a, i, key, fallback))
            a_b = fmt(safe_val(aaa_b, i, key, fallback))
            lines.append(f"| **T{i+1:02d}** | *\"{prompt_snip}\"* | `{b_a}` | `{b_b}` | `{a_a}` | `{a_b}` |")

    # Mean summary table
    lines.extend([
        "\n## 11. Metric Means & Calibrated Delta Scorecard\n",
        f"| Metric Domain | Base ({run_a_name}) | Base ({run_b_name}) | AAA ({run_a_name}) | AAA ({run_b_name}) | Run B AAA vs Base $\Delta$ | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ])

    for _, key, fallback, _ in metric_sections:
        vals_ba = [v for i in range(num_turns) if (v := safe_val(base_a, i, key, fallback)) is not None]
        vals_bb = [v for i in range(num_turns) if (v := safe_val(base_b, i, key, fallback)) is not None]
        vals_aa = [v for i in range(num_turns) if (v := safe_val(aaa_a, i, key, fallback)) is not None]
        vals_ab = [v for i in range(num_turns) if (v := safe_val(aaa_b, i, key, fallback)) is not None]

        m_ba = sum(vals_ba)/len(vals_ba) if vals_ba else 0.0
        m_bb = sum(vals_bb)/len(vals_bb) if vals_bb else 0.0
        m_aa = sum(vals_aa)/len(vals_aa) if vals_aa else 0.0
        m_ab = sum(vals_ab)/len(vals_ab) if vals_ab else 0.0
        delta = m_ab - m_bb

        status = "Active" if (len(vals_ab) > 0 and max(vals_ab) > 0.001) else "Inactive/Zero"
        lines.append(f"| **`{key}`** | `{m_ba:.3f}` | `{m_bb:.3f}` | `{m_aa:.3f}` | `{m_ab:.3f}` | **`{delta:+.3f}`** | {status} |")

    lines.append("\n---\n*Dashboard generated autonomously by AAA Cybernetic Telemetry Engine.*\n")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def print_cli_table(run_a_name: str, run_b_name: str, data_a: dict, data_b: dict):
    base_a = data_a.get("baseline", [])
    base_b = data_b.get("baseline", [])
    aaa_a = data_a.get("aaa", [])
    aaa_b = data_b.get("aaa", [])

    num_turns = min(10, max(len(base_a), len(base_b), len(aaa_a), len(aaa_b)))

    print("\n" + "=" * 114)
    print(f"CYBERNETIC BENCHMARK MULTI-METRIC AUDIT: [{run_a_name}] vs. [{run_b_name}]")
    print("=" * 114)

    metrics_to_print = [
        ("1. PAIRWISE SIMILARITY (s_t)", "pairwise_similarity", "s_t"),
        ("2. CONVERSATIONAL DEFICIT", "deficit", "homeostatic_deficit"),
        ("3. CONVERSATIONAL VITALITY", "vitality", "conversation_vitality"),
        ("4. FORWARD PERTURBATION (fP_t)", "forward_perturbation", ""),
        ("5. MUTUAL PERTURBATION (MPI_t)", "mutual_perturbation", ""),
        ("6. REVERSE PERTURBATION (rP_t)", "reverse_perturbation", ""),
        ("7. CONCEPTUAL NOVELTY (N_t)", "conceptual_novelty", ""),
        ("8. COLLAPSE PRESSURE (CP_t)", "collapse_pressure", "boringness"),
        ("9. DIVERGENCE RESOLUTION RATIO (DRR)", "divergence_resolution_ratio", ""),
        ("10. GORDON PASK CYBERNETIC HEALTH (H_pask)", "paskian_health", ""),
    ]

    for title, key, fallback in metrics_to_print:
        print(f"\n--- {title} ---")
        print(f"{'Turn':<5} | {'Prompt Snippet':<40} | {'Base: ' + run_a_name:<18} -> {'Base: ' + run_b_name:<18} | {'AAA: ' + run_a_name:<18} -> {'AAA: ' + run_b_name:<18}")
        print("-" * 114)

        for i in range(num_turns):
            user_text = (base_b[i].get("user") if i < len(base_b) else (base_a[i].get("user") if i < len(base_a) else f"Turn {i+1}"))
            prompt_snip = user_text[:37] + "..." if len(user_text) > 40 else user_text

            def gv(turns):
                if i >= len(turns):
                    return None
                m = turns[i].get("metrics", {})
                val = m.get(key)
                if val is None and fallback:
                    val = m.get(fallback)
                return val

            bna_s = f"{gv(base_a):.3f}" if gv(base_a) is not None else "n/a"
            bnb_s = f"{gv(base_b):.3f}" if gv(base_b) is not None else "n/a"
            ana_s = f"{gv(aaa_a):.3f}" if gv(aaa_a) is not None else "n/a"
            anb_s = f"{gv(aaa_b):.3f}" if gv(aaa_b) is not None else "n/a"

            print(f"T{i+1:02d}   | {prompt_snip:<40} | {bna_s:<18} -> {bnb_s:<18} | {ana_s:<18} -> {anb_s:<18}")

    print("=" * 114 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Compare Cybernetic Benchmark Runs across All Calibrated Metrics")
    parser.add_argument(
        "runs",
        nargs="*",
        help="Names or paths of benchmark runs to compare. If omitted, compares the last two runs in reports/runs/.",
    )
    parser.add_argument(
        "--name",
        "-n",
        type=str,
        default="",
        help="Custom comparison name (saves into reports/runs/<name>/, e.g. 'full_suite_calibrated')",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="",
        help="Explicit output directory for comparison plots (default: reports/runs/<name>/ if --name, else reports/runs/)",
    )

    args = parser.parse_args()

    available_runs = discover_runs()
    if not available_runs:
        print("ERROR: No benchmark runs found with conversation_receipts.json.")
        sys.exit(1)

    # Resolve Run A and Run B
    if len(args.runs) >= 2:
        path_a = resolve_run_path(args.runs[0], available_runs)
        path_b = resolve_run_path(args.runs[1], available_runs)
    elif len(args.runs) == 1:
        path_a = resolve_run_path(args.runs[0], available_runs)
        others = [r for r in available_runs if r.resolve() != path_a.resolve()]
        if not others:
            print("ERROR: Only one run exists. Need at least two runs to compare.")
            sys.exit(1)
        path_b = others[-1]
    else:
        if len(available_runs) < 2:
            print(
                f"ERROR: Only {len(available_runs)} run found ({available_runs[0].name}). Need at least two runs to compare."
            )
            sys.exit(1)
        path_a = available_runs[-2]
        path_b = available_runs[-1]

    name_a = path_a.name
    name_b = path_b.name
    print(f"\n[COMPARISON] Comparing Run A: '{name_a}' vs. Run B: '{name_b}'")

    data_a = load_receipts(path_a)
    data_b = load_receipts(path_b)

    # Print CLI comparison tables
    print_cli_table(name_a, name_b, data_a, data_b)

    # Output directory
    if args.out_dir:
        out_dir = Path(args.out_dir).resolve()
    elif args.name:
        out_dir = RUNS_DIR / args.name
    else:
        out_dir = RUNS_DIR

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[RENDERING] Generating multi-metric oscilloscope dashboard in: {out_dir}")
    html_file, png_file = render_comparison_dashboard(
        name_a, name_b, data_a, data_b, out_dir, custom_name=args.name
    )

    print(f"\nSUCCESS: Comparison artifacts generated:")
    print(f"  Plot PNG:  {png_file}")
    print(f"  HTML View: {html_file}\n")


if __name__ == "__main__":
    main()
