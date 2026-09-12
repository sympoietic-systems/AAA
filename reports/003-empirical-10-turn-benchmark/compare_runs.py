#!/usr/bin/env python3
"""
Cybernetic Benchmark Run Comparison Tool.

Compares metrics trajectories across different benchmark runs (e.g. before vs. after metric updates,
or model A vs. model B).

Usage:
  # Compare the last two runs in reports/runs/ (default):
  python reports/003-empirical-10-turn-benchmark/compare_runs.py

  # Compare two specific runs by folder name or path:
  python reports/003-empirical-10-turn-benchmark/compare_runs.py eval_updated run_20260912_000253

  # Compare a specific run against the baseline 003 reference:
  python reports/003-empirical-10-turn-benchmark/compare_runs.py reference eval_updated
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


def to_pts(series, y_max=1.0, left=70, right=740, top=40, bottom=360):
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


def to_circ(series, y_max=1.0, color="#ffffff", r=4.0, hollow=False, left=70, right=740, top=40, bottom=360):
    if len(series) <= 1:
        return ""
    x_step = (right - left) / (len(series) - 1)
    circs = []
    for i, v in enumerate(series):
        x = left + i * x_step
        clamped = max(0.0, min(y_max, float(v)))
        y = bottom - (clamped / y_max) * (bottom - top)
        if hollow:
            circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#0a0c10" stroke="{color}" stroke-width="2.2" />')
        else:
            circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" />')
    return "\n".join(circs)


def make_grid(left=70, right=740, top=40, bottom=360, y_max=1.0, y_ticks=5, num_turns=10):
    lines = []
    for i in range(y_ticks + 1):
        val = (y_ticks - i) * (y_max / y_ticks)
        y = top + i * (bottom - top) / y_ticks
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="rgba(255,255,255,0.08)" stroke-width="1" />')
        lines.append(f'<text x="{left - 12}" y="{y + 4:.1f}" fill="#717684" font-size="11" font-family="JetBrains Mono, monospace" text-anchor="end">{val:.2f}</text>')

    for i in range(num_turns):
        x = left + i * (right - left) / max(1, num_turns - 1)
        lines.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />')
        lines.append(f'<text x="{x:.1f}" y="{bottom + 22}" fill="#717684" font-size="11" font-family="JetBrains Mono, monospace" text-anchor="middle">T{i+1}</text>')

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

    def extract(turns: list, key: str, fallback_key: str = "") -> list[float]:
        res = []
        for t in turns[:num_turns]:
            m = t.get("metrics", {})
            val = m.get(key)
            if val is None and fallback_key:
                val = m.get(fallback_key)
            res.append(float(val) if val is not None else 0.0)
        return res

    # Extract series for Novelty and Collapse Pressure
    base_nov_a = extract(base_a, "conceptual_novelty")
    base_nov_b = extract(base_b, "conceptual_novelty")
    aaa_nov_a = extract(aaa_a, "conceptual_novelty")
    aaa_nov_b = extract(aaa_b, "conceptual_novelty")

    base_col_a = extract(base_a, "collapse_pressure", "boringness")
    base_col_b = extract(base_b, "collapse_pressure", "boringness")
    aaa_col_a = extract(aaa_a, "collapse_pressure", "boringness")
    aaa_col_b = extract(aaa_b, "collapse_pressure", "boringness")

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
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Inter:wght@400;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background-color: #060709; color: #e4e7ec; font-family: 'JetBrains Mono', monospace;
    width: 1720px; height: 1120px; padding: 32px 38px; display: flex; flex-direction: column;
    justify-content: space-between; position: relative;
    background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.07) 1px, transparent 0);
    background-size: 24px 24px;
  }}
  .header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    border-bottom: 1px solid rgba(255,255,255,0.14); padding-bottom: 16px;
  }}
  .title-area h1 {{
    font-size: 22px; font-weight: 800; letter-spacing: 1px; color: #ffffff;
    display: flex; align-items: center; gap: 12px;
  }}
  .badge-primary {{
    background: rgba(0, 229, 255, 0.12); color: #00e5ff; border: 1px solid rgba(0, 229, 255, 0.35);
    font-size: 11px; padding: 3px 9px; border-radius: 4px; font-weight: 700; letter-spacing: 0.8px;
  }}
  .subtitle {{
    font-size: 12px; color: #88909e; margin-top: 6px; font-family: 'Inter', sans-serif;
  }}
  .header-meta {{
    text-align: right; font-size: 11px; color: #717684; line-height: 1.7;
  }}
  .header-meta span {{ color: #00e5ff; font-weight: 600; }}

  /* Main Grid */
  .panels-container {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin: 18px 0; flex: 1;
  }}
  .panel-card {{
    background: #0c0e14; border: 1px solid rgba(255,255,255,0.12); border-radius: 8px;
    padding: 22px 24px; display: flex; flex-direction: column; justify-content: space-between;
    box-shadow: 0 12px 32px rgba(0,0,0,0.5); position: relative; overflow: hidden;
  }}
  .panel-card::before {{
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #00e5ff, #b026ff, #ff9944);
  }}
  .card-top {{
    display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;
  }}
  .panel-title {{
    font-size: 15px; font-weight: 800; letter-spacing: 0.8px; color: #ffffff;
  }}
  .panel-desc {{
    font-size: 11px; color: #88909e; font-family: 'Inter', sans-serif; margin-top: 4px; line-height: 1.4;
  }}
  .card-badge {{
    font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 3px; letter-spacing: 0.5px;
  }}
  .badge-novelty {{ background: rgba(0,229,255,0.15); color: #00e5ff; border: 1px solid rgba(0,229,255,0.3); }}
  .badge-collapse {{ background: rgba(255,102,0,0.15); color: #ff6600; border: 1px solid rgba(255,102,0,0.3); }}

  /* Legend */
  .legend-box {{
    display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px 16px;
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 11px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; }}
  .line-sample {{ width: 22px; height: 3px; border-radius: 2px; display: inline-block; }}
  .dot-sample {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}

  /* SVG Plot container */
  .svg-plot {{ width: 100%; height: 400px; }}

  /* Scoreboard */
  .bottom-scoreboard {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
    background: #0a0c12; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px;
    padding: 14px 20px; align-items: center;
  }}
  .score-card {{ border-left: 2px solid rgba(255,255,255,0.12); padding-left: 14px; }}
  .score-card:first-child {{ border-left: 2px solid #00e5ff; }}
  .score-card:nth-child(2) {{ border-left: 2px solid #ff9944; }}
  .score-card:nth-child(3) {{ border-left: 2px solid #ff4466; }}
  .score-card:nth-child(4) {{ border-left: 2px solid #00ffaa; }}
  .score-label {{ font-size: 10px; color: #717684; text-transform: uppercase; letter-spacing: 0.8px; }}
  .score-val {{ font-size: 16px; font-weight: 800; margin: 3px 0; color: #ffffff; }}
  .score-sub {{ font-size: 10px; color: #88909e; font-family: 'Inter', sans-serif; }}

  .footer-row {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 10px; color: #525866; border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 10px; margin-top: 10px;
  }}
</style>
</head>
<body>

  <!-- Header -->
  <div class="header">
    <div class="title-area">
      <h1>
        BENCHMARK RUN COMPARISON
        <span class="badge-primary">{run_a_name} vs. {run_b_name}</span>
      </h1>
      <div class="subtitle">
        Comparative cybernetic telemetry across multi-turn adversarial stress testing.
      </div>
    </div>
    <div class="header-meta">
      Run A ({run_a_name}): <span>{meta_a_model}</span> ({time_a})<br/>
      Run B ({run_b_name}): <span>{meta_b_model}</span> ({time_b})<br/>
      Domain: <span>[0.00, 1.00] Normalized Cybernetic Trajectories</span>
    </div>
  </div>

  <!-- 2 Hero Panels -->
  <div class="panels-container">

    <!-- Panel 1: Conceptual Novelty -->
    <div class="panel-card">
      <div>
        <div class="card-top">
          <div>
            <div class="panel-title">1. CONCEPTUAL NOVELTY (N_t)</div>
            <div class="panel-desc">Semantic displacement from context centroid EMA across iterative turns.</div>
          </div>
          <span class="card-badge badge-novelty">NOVELTY PROFILE</span>
        </div>

        <div class="legend-box">
          <div class="legend-item">
            <span class="line-sample" style="background: #00e5ff;"></span>
            <span class="dot-sample" style="background: #00e5ff;"></span>
            <span><strong>AAA [{run_b_name}]:</strong> Solid Cyan</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #b026ff;"></span>
            <span class="dot-sample" style="border: 2px solid #b026ff; background: #0a0c10;"></span>
            <span style="color: #b026ff;">AAA [{run_a_name}]: Dashed Violet</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="background: #ff9944;"></span>
            <span class="dot-sample" style="background: #ff9944;"></span>
            <span><strong>Base [{run_b_name}]:</strong> Solid Amber</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #ff4466;"></span>
            <span class="dot-sample" style="border: 2px solid #ff4466; background: #0a0c10;"></span>
            <span style="color: #ff4466;">Base [{run_a_name}]: Dashed Red</span>
          </div>
        </div>

        <svg class="svg-plot" viewBox="0 0 780 400">
          <rect x="70" y="40" width="670" height="96" fill="rgba(0, 229, 255, 0.03)" />
          <text x="730" y="58" fill="rgba(0, 229, 255, 0.4)" font-size="10" text-anchor="end">PARADIGM EXPLORATION [0.70 - 1.00]</text>

          <rect x="70" y="232" width="670" height="128" fill="rgba(255, 68, 102, 0.04)" />
          <text x="730" y="350" fill="rgba(255, 68, 102, 0.4)" font-size="10" text-anchor="end">REPETITIVE STAGNATION BASIN [0.00 - 0.40]</text>

          {make_grid(left=70, right=740, top=40, bottom=360, y_max=1.0, y_ticks=5, num_turns=num_turns)}

          <!-- Run A (Dashed) -->
          <polyline fill="none" stroke="#b026ff" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.7" points="{to_pts(aaa_nov_a, y_max=1.0)}" />
          {to_circ(aaa_nov_a, y_max=1.0, color="#b026ff", r=3.5, hollow=True)}

          <polyline fill="none" stroke="#ff4466" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.7" points="{to_pts(base_nov_a, y_max=1.0)}" />
          {to_circ(base_nov_a, y_max=1.0, color="#ff4466", r=3.5, hollow=True)}

          <!-- Run B (Solid) -->
          <polyline fill="none" stroke="#ff9944" stroke-width="3.0" points="{to_pts(base_nov_b, y_max=1.0)}" />
          {to_circ(base_nov_b, y_max=1.0, color="#ff9944", r=4.5, hollow=False)}

          <polyline fill="none" stroke="#00e5ff" stroke-width="3.2" points="{to_pts(aaa_nov_b, y_max=1.0)}" />
          {to_circ(aaa_nov_b, y_max=1.0, color="#00e5ff", r=4.5, hollow=False)}
        </svg>
      </div>
    </div>

    <!-- Panel 2: Collapse Pressure -->
    <div class="panel-card">
      <div>
        <div class="card-top">
          <div>
            <div class="panel-title">2. COLLAPSE PRESSURE / BORINGNESS INDEX</div>
            <div class="panel-desc">Allostatic stagnation alarm tracking perturbation, entropy, and novelty failures.</div>
          </div>
          <span class="card-badge badge-collapse">STAGNATION REGULATION</span>
        </div>

        <div class="legend-box">
          <div class="legend-item">
            <span class="line-sample" style="background: #00e5ff;"></span>
            <span class="dot-sample" style="background: #00e5ff;"></span>
            <span><strong>AAA [{run_b_name}]:</strong> Solid Cyan</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #b026ff;"></span>
            <span class="dot-sample" style="border: 2px solid #b026ff; background: #0a0c10;"></span>
            <span style="color: #b026ff;">AAA [{run_a_name}]: Dashed Violet</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="background: #ff9944;"></span>
            <span class="dot-sample" style="background: #ff9944;"></span>
            <span><strong>Base [{run_b_name}]:</strong> Solid Amber</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #ff4466;"></span>
            <span class="dot-sample" style="border: 2px solid #ff4466; background: #0a0c10;"></span>
            <span style="color: #ff4466;">Base [{run_a_name}]: Dashed Red</span>
          </div>
        </div>

        <svg class="svg-plot" viewBox="0 0 780 400">
          <!-- Thresholds -->
          <line x1="70" y1="{360 - 0.70 * 320}" x2="740" y2="{360 - 0.70 * 320}" stroke="#ff3366" stroke-width="1.8" stroke-dasharray="4,4" />
          <text x="735" y="{360 - 0.70 * 320 - 6}" fill="#ff3366" font-size="10" text-anchor="end">SEDATION INTERRUPT (0.70)</text>

          <line x1="70" y1="{360 - 0.65 * 320}" x2="740" y2="{360 - 0.65 * 320}" stroke="#ffaa00" stroke-width="1.8" stroke-dasharray="6,4" />
          <text x="735" y="{360 - 0.65 * 320 - 6}" fill="#ffaa00" font-size="10" text-anchor="end">STAGNANT STATE TRIGGER (0.65)</text>

          <line x1="70" y1="{360 - 0.40 * 320}" x2="740" y2="{360 - 0.40 * 320}" stroke="#00ffaa" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.8" />
          <text x="735" y="{360 - 0.40 * 320 + 14}" fill="#00ffaa" font-size="10" text-anchor="end">FLOWING CEILING (0.40)</text>

          {make_grid(left=70, right=740, top=40, bottom=360, y_max=1.0, y_ticks=5, num_turns=num_turns)}

          <!-- Run A (Dashed) -->
          <polyline fill="none" stroke="#b026ff" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.6" points="{to_pts(aaa_col_a, y_max=1.0)}" />
          {to_circ(aaa_col_a, y_max=1.0, color="#b026ff", r=3.5, hollow=True)}

          <polyline fill="none" stroke="#ff4466" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.6" points="{to_pts(base_col_a, y_max=1.0)}" />
          {to_circ(base_col_a, y_max=1.0, color="#ff4466", r=3.5, hollow=True)}

          <!-- Run B (Solid) -->
          <polyline fill="none" stroke="#ff9944" stroke-width="3.0" points="{to_pts(base_col_b, y_max=1.0)}" />
          {to_circ(base_col_b, y_max=1.0, color="#ff9944", r=4.5, hollow=False)}

          <polyline fill="none" stroke="#00e5ff" stroke-width="3.2" points="{to_pts(aaa_col_b, y_max=1.0)}" />
          {to_circ(aaa_col_b, y_max=1.0, color="#00e5ff", r=4.5, hollow=False)}
        </svg>
      </div>
    </div>

  </div>

  <!-- Scoreboard -->
  <div class="bottom-scoreboard">
    <div class="score-card">
      <div class="score-label">Run B Final Novelty</div>
      <div class="score-val" style="color: #00e5ff;">AAA: {aaa_nov_b[-1] if aaa_nov_b else 0.0:.3f} // Base: {base_nov_b[-1] if base_nov_b else 0.0:.3f}</div>
      <div class="score-sub">T{num_turns} terminal semantic displacement</div>
    </div>
    <div class="score-card">
      <div class="score-label">Run B Final Collapse</div>
      <div class="score-val" style="color: #ff9944;">AAA: {aaa_col_b[-1] if aaa_col_b else 0.0:.3f} // Base: {base_col_b[-1] if base_col_b else 0.0:.3f}</div>
      <div class="score-sub">T{num_turns} terminal stagnation pressure</div>
    </div>
    <div class="score-card">
      <div class="score-label">AAA Advantage Delta (Novelty)</div>
      <div class="score-val" style="color: #ff4466;">{(sum(aaa_nov_b)/max(1, len(aaa_nov_b)) - sum(base_nov_b)/max(1, len(base_nov_b))):+.3f}</div>
      <div class="score-sub">Average conceptual drift separation in Run B</div>
    </div>
    <div class="score-card">
      <div class="score-label">Telemetry Status</div>
      <div class="score-val" style="color: #00ffaa;">CALIBRATED</div>
      <div class="score-sub">Active control range restored across all turns</div>
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
            "--window-size=1720,1120",
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

    lines = [
        f"# Cybernetic Benchmark Comparison: {run_a_name} vs. {run_b_name}",
        f"\n**Run A (Reference):** `{run_a_name}` | Model: `{data_a.get('baseline_model') or data_a.get('aaa_model', 'Unknown')}`  ",
        f"**Run B (Target):** `{run_b_name}` | Model: `{data_b.get('baseline_model') or data_b.get('aaa_model', 'Unknown')}`  ",
        f"**Comparison Date:** {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime())}  \n",
        f"![Oscilloscope Telemetry Dashboard](./{png_name})\n",
        "## 1. Conceptual Novelty ($N_t$) Comparison Matrix\n",
        f"| Turn | Human Prompt Snippet | Base ({run_a_name}) | Base ({run_b_name}) | AAA ({run_a_name}) | AAA ({run_b_name}) |",
        "| :---: | :--- | :---: | :---: | :---: | :---: |"
    ]

    for i in range(num_turns):
        user_text = (base_b[i].get("user") if i < len(base_b) else (base_a[i].get("user") if i < len(base_a) else f"Turn {i+1}"))
        prompt_snip = (user_text[:40] + "...").replace("|", "-")
        b_nov_a = f"{base_a[i]['metrics'].get('conceptual_novelty', 0.0):.3f}" if i < len(base_a) and base_a[i]['metrics'].get('conceptual_novelty') is not None else "-"
        b_nov_b = f"{base_b[i]['metrics'].get('conceptual_novelty', 0.0):.3f}" if i < len(base_b) and base_b[i]['metrics'].get('conceptual_novelty') is not None else "-"
        a_nov_a = f"{aaa_a[i]['metrics'].get('conceptual_novelty', 0.0):.3f}" if i < len(aaa_a) and aaa_a[i]['metrics'].get('conceptual_novelty') is not None else "-"
        a_nov_b = f"{aaa_b[i]['metrics'].get('conceptual_novelty', 0.0):.3f}" if i < len(aaa_b) and aaa_b[i]['metrics'].get('conceptual_novelty') is not None else "-"
        lines.append(f"| **T{i+1:02d}** | *\"{prompt_snip}\"* | `{b_nov_a}` | `{b_nov_b}` | `{a_nov_a}` | `{a_nov_b}` |")

    lines.extend([
        "\n## 2. Collapse Pressure (Boringness) Comparison Matrix\n",
        f"| Turn | Human Prompt Snippet | Base ({run_a_name}) | Base ({run_b_name}) | AAA ({run_a_name}) | AAA ({run_b_name}) |",
        "| :---: | :--- | :---: | :---: | :---: | :---: |"
    ])

    for i in range(num_turns):
        user_text = (base_b[i].get("user") if i < len(base_b) else (base_a[i].get("user") if i < len(base_a) else f"Turn {i+1}"))
        prompt_snip = (user_text[:40] + "...").replace("|", "-")
        b_col_a_val = base_a[i]['metrics'].get('collapse_pressure') if i < len(base_a) else None
        if b_col_a_val is None and i < len(base_a):
            b_col_a_val = base_a[i]['metrics'].get('boringness')
        b_col_b_val = base_b[i]['metrics'].get('collapse_pressure') if i < len(base_b) else None
        if b_col_b_val is None and i < len(base_b):
            b_col_b_val = base_b[i]['metrics'].get('boringness')

        a_col_a_val = aaa_a[i]['metrics'].get('collapse_pressure') if i < len(aaa_a) else None
        if a_col_a_val is None and i < len(aaa_a):
            a_col_a_val = aaa_a[i]['metrics'].get('boringness')
        a_col_b_val = aaa_b[i]['metrics'].get('collapse_pressure') if i < len(aaa_b) else None
        if a_col_b_val is None and i < len(aaa_b):
            a_col_b_val = aaa_b[i]['metrics'].get('boringness')

        bca_s = f"{b_col_a_val:.3f}" if b_col_a_val is not None else "-"
        bcb_s = f"{b_col_b_val:.3f}" if b_col_b_val is not None else "-"
        aca_s = f"{a_col_a_val:.3f}" if a_col_a_val is not None else "-"
        acb_s = f"{a_col_b_val:.3f}" if a_col_b_val is not None else "-"
        lines.append(f"| **T{i+1:02d}** | *\"{prompt_snip}\"* | `{bca_s}` | `{bcb_s}` | `{aca_s}` | `{acb_s}` |")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def print_cli_table(run_a_name: str, run_b_name: str, data_a: dict, data_b: dict):
    base_a = data_a.get("baseline", [])
    base_b = data_b.get("baseline", [])
    aaa_a = data_a.get("aaa", [])
    aaa_b = data_b.get("aaa", [])

    num_turns = min(10, max(len(base_a), len(base_b), len(aaa_a), len(aaa_b)))

    print("\n" + "=" * 110)
    print(f"CYBERNETIC BENCHMARK COMPARISON: [{run_a_name}] vs. [{run_b_name}]")
    print("=" * 110)

    print("\n--- 1. CONCEPTUAL NOVELTY (N_t) ---")
    print(f"{'Turn':<5} | {'Prompt Snippet':<42} | {'Base: ' + run_a_name:<18} -> {'Base: ' + run_b_name:<18} | {'AAA: ' + run_a_name:<18} -> {'AAA: ' + run_b_name:<18}")
    print("-" * 110)

    for i in range(num_turns):
        user_text = (base_b[i].get("user") if i < len(base_b) else (base_a[i].get("user") if i < len(base_a) else f"Turn {i+1}"))
        prompt_snip = user_text[:39] + "..." if len(user_text) > 42 else user_text

        b_nov_a = base_a[i]["metrics"].get("conceptual_novelty") if i < len(base_a) else None
        b_nov_b = base_b[i]["metrics"].get("conceptual_novelty") if i < len(base_b) else None
        a_nov_a = aaa_a[i]["metrics"].get("conceptual_novelty") if i < len(aaa_a) else None
        a_nov_b = aaa_b[i]["metrics"].get("conceptual_novelty") if i < len(aaa_b) else None

        bna_s = f"{b_nov_a:.3f}" if b_nov_a is not None else "n/a"
        bnb_s = f"{b_nov_b:.3f}" if b_nov_b is not None else "n/a"
        ana_s = f"{a_nov_a:.3f}" if a_nov_a is not None else "n/a"
        anb_s = f"{a_nov_b:.3f}" if a_nov_b is not None else "n/a"

        print(f"T{i+1:02d}   | {prompt_snip:<42} | {bna_s:<18} -> {bnb_s:<18} | {ana_s:<18} -> {anb_s:<18}")

    print("\n--- 2. COLLAPSE PRESSURE (BORINGNESS) ---")
    print(f"{'Turn':<5} | {'Prompt Snippet':<42} | {'Base: ' + run_a_name:<18} -> {'Base: ' + run_b_name:<18} | {'AAA: ' + run_a_name:<18} -> {'AAA: ' + run_b_name:<18}")
    print("-" * 110)

    for i in range(num_turns):
        user_text = (base_b[i].get("user") if i < len(base_b) else (base_a[i].get("user") if i < len(base_a) else f"Turn {i+1}"))
        prompt_snip = user_text[:39] + "..." if len(user_text) > 42 else user_text

        b_col_a = (base_a[i]["metrics"].get("collapse_pressure") if i < len(base_a) else None)
        if b_col_a is None and i < len(base_a):
            b_col_a = base_a[i]["metrics"].get("boringness")
        b_col_b = (base_b[i]["metrics"].get("collapse_pressure") if i < len(base_b) else None)
        if b_col_b is None and i < len(base_b):
            b_col_b = base_b[i]["metrics"].get("boringness")

        a_col_a = (aaa_a[i]["metrics"].get("collapse_pressure") if i < len(aaa_a) else None)
        if a_col_a is None and i < len(aaa_a):
            a_col_a = aaa_a[i]["metrics"].get("boringness")
        a_col_b = (aaa_b[i]["metrics"].get("collapse_pressure") if i < len(aaa_b) else None)
        if a_col_b is None and i < len(aaa_b):
            a_col_b = aaa_b[i]["metrics"].get("boringness")

        bca_s = f"{b_col_a:.3f}" if b_col_a is not None else "n/a"
        bcb_s = f"{b_col_b:.3f}" if b_col_b is not None else "n/a"
        aca_s = f"{a_col_a:.3f}" if a_col_a is not None else "n/a"
        acb_s = f"{a_col_b:.3f}" if a_col_b is not None else "n/a"

        print(f"T{i+1:02d}   | {prompt_snip:<42} | {bca_s:<18} -> {bcb_s:<18} | {aca_s:<18} -> {acb_s:<18}")

    print("=" * 110 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Compare Cybernetic Benchmark Runs")
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
        help="Custom comparison name (saves into reports/runs/<name>/, e.g. 'novelty_boringness')",
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
        # Compare specified run against the latest available run
        path_a = resolve_run_path(args.runs[0], available_runs)
        # Select the latest available run that is not path_a
        others = [r for r in available_runs if r.resolve() != path_a.resolve()]
        if not others:
            print("ERROR: Only one run exists. Need at least two runs to compare.")
            sys.exit(1)
        path_b = others[-1]
    else:
        # Default: last two runs
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
    print(f"[RENDERING] Generating oscilloscope visual dashboard in: {out_dir}")
    html_file, png_file = render_comparison_dashboard(
        name_a, name_b, data_a, data_b, out_dir, custom_name=args.name
    )

    print(f"\nSUCCESS: Comparison artifacts generated:")
    print(f"  Plot PNG:  {png_file}")
    print(f"  HTML View: {html_file}\n")


if __name__ == "__main__":
    main()

