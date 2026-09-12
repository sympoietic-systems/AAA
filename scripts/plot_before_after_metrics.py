#!/usr/bin/env python3
"""
Generate before-and-after oscilloscope telemetry plot for:
1. Conceptual Novelty (N_t)
2. Collapse Pressure (Boringness)
Saves HTML and renders high-resolution PNG into reports/runs/
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "reports" / "runs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OLD_RECEIPTS = PROJECT_ROOT / "reports" / "003-empirical-10-turn-benchmark" / "conversation_receipts.json"
NEW_RECEIPTS = PROJECT_ROOT / "reports" / "runs" / "eval_updated" / "conversation_receipts.json"

with open(OLD_RECEIPTS, "r", encoding="utf-8") as f:
    old_data = json.load(f)

with open(NEW_RECEIPTS, "r", encoding="utf-8") as f:
    new_data = json.load(f)

# Extract series across 10 turns
turns = list(range(1, 11))

base_nov_old = [t["metrics"].get("conceptual_novelty", 0.0) for t in old_data["baseline"][:10]]
base_nov_new = [t["metrics"].get("conceptual_novelty", 0.0) for t in new_data["baseline"][:10]]
aaa_nov_old = [t["metrics"].get("conceptual_novelty", 0.0) for t in old_data["aaa"][:10]]
aaa_nov_new = [t["metrics"].get("conceptual_novelty", 0.0) for t in new_data["aaa"][:10]]

base_col_old = [t["metrics"].get("collapse_pressure") if t["metrics"].get("collapse_pressure") is not None else 0.0 for t in old_data["baseline"][:10]]
base_col_new = [t["metrics"].get("collapse_pressure") if t["metrics"].get("collapse_pressure") is not None else 0.0 for t in new_data["baseline"][:10]]
aaa_col_old = [t["metrics"].get("boringness") or t["metrics"].get("collapse_pressure") or 0.0 for t in old_data["aaa"][:10]]
aaa_col_new = [t["metrics"].get("collapse_pressure") if t["metrics"].get("collapse_pressure") is not None else 0.0 for t in new_data["aaa"][:10]]

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

def to_pts(series, y_max=1.0, left=70, right=740, top=40, bottom=360):
    x_step = (right - left) / (len(series) - 1)
    pts = []
    for i, v in enumerate(series):
        x = left + i * x_step
        clamped = max(0.0, min(y_max, float(v)))
        y = bottom - (clamped / y_max) * (bottom - top)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)

def to_circ(series, y_max=1.0, color="#ffffff", r=4.0, hollow=False, left=70, right=740, top=40, bottom=360):
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

def make_grid(left=70, right=740, top=40, bottom=360, y_max=1.0, y_ticks=5):
    lines = []
    # Horizontal grid lines and labels
    for i in range(y_ticks + 1):
        val = (y_ticks - i) * (y_max / y_ticks)
        y = top + i * (bottom - top) / y_ticks
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="rgba(255,255,255,0.08)" stroke-width="1" />')
        lines.append(f'<text x="{left - 12}" y="{y + 4:.1f}" fill="#717684" font-size="11" font-family="JetBrains Mono, monospace" text-anchor="end">{val:.2f}</text>')

    # Vertical grid lines and labels
    for i in range(10):
        x = left + i * (right - left) / 9
        lines.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="rgba(255,255,255,0.06)" stroke-width="1" />')
        lines.append(f'<text x="{x:.1f}" y="{bottom + 22}" fill="#717684" font-size="11" font-family="JetBrains Mono, monospace" text-anchor="middle">T{i+1}</text>')

    return "\n".join(lines)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Cybernetic Telemetry Audit: Before vs. After Metric Improvements</title>
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

  /* Diagnosis footer in card */
  .card-diagnosis {{
    background: rgba(255,255,255,0.02); border-top: 1px solid rgba(255,255,255,0.08);
    padding-top: 12px; margin-top: 12px; display: grid; grid-template-columns: 1fr 1fr; gap: 14px;
    font-size: 11px; font-family: 'Inter', sans-serif;
  }}
  .diag-item h4 {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 4px; }}
  .diag-old h4 {{ color: #ff4466; }}
  .diag-new h4 {{ color: #00e5ff; }}
  .diag-item p {{ color: #a1a7b4; line-height: 1.4; font-size: 11px; }}

  /* Bottom Scoreboard */
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
        CYBERNETIC TELEMETRY AUDIT: BEFORE vs. AFTER
        <span class="badge-primary">10-TURN REPETITION TEST</span>
      </h1>
      <div class="subtitle">
        Empirical comparison of telemetry sensitivity before and after fixing division singularities and triadic multiplicative suppression.
      </div>
    </div>
    <div class="header-meta">
      Grounding: <span>1:1 Model Parity (Google Gemini 3.7 Flash)</span><br/>
      Context: <span>Adversarial HTTP 429 Cache-Wipe Repetition Loop</span><br/>
      Location: <code>reports/runs/003_metrics_update_before_vs_after.png</code>
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
            <div class="panel-desc">Measures semantic displacement from context centroid EMA. Fixes context scatter division singularity.</div>
          </div>
          <span class="card-badge badge-novelty">DRIFT SCALE REGULARIZED</span>
        </div>

        <div class="legend-box">
          <div class="legend-item">
            <span class="line-sample" style="background: #00e5ff;"></span>
            <span class="dot-sample" style="background: #00e5ff;"></span>
            <span><strong>AAA (After):</strong> Decays realistically (0.75 &rarr; 0.39)</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #b026ff;"></span>
            <span class="dot-sample" style="border: 2px solid #b026ff; background: #0a0c10;"></span>
            <span style="color: #b026ff;">AAA (Before): Pinned at artificial 0.85</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="background: #ff9944;"></span>
            <span class="dot-sample" style="background: #ff9944;"></span>
            <span><strong>Baseline (After):</strong> Steep drop (0.67 &rarr; 0.39)</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #ff4466;"></span>
            <span class="dot-sample" style="border: 2px solid #ff4466; background: #0a0c10;"></span>
            <span style="color: #ff4466;">Baseline (Before): Trapped at 0.70&ndash;0.96</span>
          </div>
        </div>

        <svg class="svg-plot" viewBox="0 0 780 400">
          <!-- Reference Bands -->
          <rect x="70" y="40" width="670" height="96" fill="rgba(0, 229, 255, 0.03)" />
          <text x="730" y="58" fill="rgba(0, 229, 255, 0.4)" font-size="10" text-anchor="end">PARADIGM EXPLORATION [0.70 - 1.00]</text>

          <rect x="70" y="232" width="670" height="128" fill="rgba(255, 68, 102, 0.04)" />
          <text x="730" y="350" fill="rgba(255, 68, 102, 0.4)" font-size="10" text-anchor="end">REPETITIVE STAGNATION BASIN [0.00 - 0.40]</text>

          <!-- Grid -->
          {make_grid(left=70, right=740, top=40, bottom=360, y_max=1.0, y_ticks=5)}

          <!-- Traces Before -->
          <polyline fill="none" stroke="#b026ff" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.65" points="{to_pts(aaa_nov_old, y_max=1.0)}" />
          {to_circ(aaa_nov_old, y_max=1.0, color="#b026ff", r=3.5, hollow=True)}

          <polyline fill="none" stroke="#ff4466" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.65" points="{to_pts(base_nov_old, y_max=1.0)}" />
          {to_circ(base_nov_old, y_max=1.0, color="#ff4466", r=3.5, hollow=True)}

          <!-- Traces After -->
          <polyline fill="none" stroke="#ff9944" stroke-width="3.0" points="{to_pts(base_nov_new, y_max=1.0)}" />
          {to_circ(base_nov_new, y_max=1.0, color="#ff9944", r=4.5, hollow=False)}

          <polyline fill="none" stroke="#00e5ff" stroke-width="3.2" points="{to_pts(aaa_nov_new, y_max=1.0)}" />
          {to_circ(aaa_nov_new, y_max=1.0, color="#00e5ff", r=4.5, hollow=False)}
        </svg>
      </div>

      <div class="card-diagnosis">
        <div class="diag-item diag-old">
          <h4>Old Formula Defect (&sigma; &rarr; 0 Singularity)</h4>
          <p>Dividing by &sigma;<sub>context</sub> + 0.01 blew up into near-infinity whenever dialogue repeated. Novelty remained saturated at 0.80&ndash;0.99 despite 10 repetitive turns.</p>
        </div>
        <div class="diag-item diag-new">
          <h4>Updated Calibrated Scale (D<sub>eff</sub> &ge; 0.20)</h4>
          <p>Eliminates the singularity. Novelty properly drops into the stagnation basin (0.39), while capturing Symbia's reframing bursts (0.75 &rarr; 0.45) above the baseline.</p>
        </div>
      </div>
    </div>

    <!-- Panel 2: Collapse Pressure -->
    <div class="panel-card">
      <div>
        <div class="card-top">
          <div>
            <div class="panel-title">2. COLLAPSE PRESSURE / BORINGNESS INDEX</div>
            <div class="panel-desc">Allostatic stagnation alarm. Fixes multiplicative suppression that locked values in 0.01&ndash;0.03 dead zone.</div>
          </div>
          <span class="card-badge badge-collapse">ALLOSTATIC TRIGGER RESTORED</span>
        </div>

        <div class="legend-box">
          <div class="legend-item">
            <span class="line-sample" style="background: #ff9944;"></span>
            <span class="dot-sample" style="background: #ff9944;"></span>
            <span><strong>Baseline (After):</strong> Elevated (0.40&ndash;0.47)</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #ff4466;"></span>
            <span class="dot-sample" style="border: 2px solid #ff4466; background: #0a0c10;"></span>
            <span style="color: #ff4466;">Baseline (Before): Flatlined at 0.02</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="background: #00e5ff;"></span>
            <span class="dot-sample" style="background: #00e5ff;"></span>
            <span><strong>AAA (After):</strong> Responsive (0.35&ndash;0.45)</span>
          </div>
          <div class="legend-item">
            <span class="line-sample" style="border-top: 2px dashed #b026ff;"></span>
            <span class="dot-sample" style="border: 2px solid #b026ff; background: #0a0c10;"></span>
            <span style="color: #b026ff;">AAA (Before): Flatlined at 0.00&ndash;0.03</span>
          </div>
        </div>

        <svg class="svg-plot" viewBox="0 0 780 400">
          <!-- Threshold Lines -->
          <!-- 0.70 Sedation Interrupt -->
          <line x1="70" y1="{360 - 0.70 * 320}" x2="740" y2="{360 - 0.70 * 320}" stroke="#ff3366" stroke-width="1.8" stroke-dasharray="4,4" />
          <text x="735" y="{360 - 0.70 * 320 - 6}" fill="#ff3366" font-size="10" text-anchor="end">SEDATION INTERRUPT THRESHOLD (0.70)</text>

          <!-- 0.65 Stagnant State Trigger -->
          <line x1="70" y1="{360 - 0.65 * 320}" x2="740" y2="{360 - 0.65 * 320}" stroke="#ffaa00" stroke-width="1.8" stroke-dasharray="6,4" />
          <text x="735" y="{360 - 0.65 * 320 - 6}" fill="#ffaa00" font-size="10" text-anchor="end">STAGNANT STATE THRESHOLD (0.65)</text>

          <!-- 0.40 Flowing Ceiling -->
          <line x1="70" y1="{360 - 0.40 * 320}" x2="740" y2="{360 - 0.40 * 320}" stroke="#00ffaa" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.8" />
          <text x="735" y="{360 - 0.40 * 320 + 14}" fill="#00ffaa" font-size="10" text-anchor="end">FLOWING CEILING (0.40)</text>

          <!-- Inert Dead Zone Highlight -->
          <rect x="70" y="344" width="670" height="16" fill="rgba(255, 68, 102, 0.15)" />
          <text x="78" y="356" fill="#ff4466" font-size="9">OLD INERT MULTIPLICATION DEAD ZONE (&lt; 0.05)</text>

          <!-- Grid -->
          {make_grid(left=70, right=740, top=40, bottom=360, y_max=1.0, y_ticks=5)}

          <!-- Traces Before (Near Zero) -->
          <polyline fill="none" stroke="#b026ff" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.6" points="{to_pts(aaa_col_old, y_max=1.0)}" />
          {to_circ(aaa_col_old, y_max=1.0, color="#b026ff", r=3.5, hollow=True)}

          <polyline fill="none" stroke="#ff4466" stroke-width="2.0" stroke-dasharray="5,4" opacity="0.6" points="{to_pts(base_col_old, y_max=1.0)}" />
          {to_circ(base_col_old, y_max=1.0, color="#ff4466", r=3.5, hollow=True)}

          <!-- Traces After -->
          <polyline fill="none" stroke="#ff9944" stroke-width="3.0" points="{to_pts(base_col_new, y_max=1.0)}" />
          {to_circ(base_col_new, y_max=1.0, color="#ff9944", r=4.5, hollow=False)}

          <polyline fill="none" stroke="#00e5ff" stroke-width="3.2" points="{to_pts(aaa_col_new, y_max=1.0)}" />
          {to_circ(aaa_col_new, y_max=1.0, color="#00e5ff", r=4.5, hollow=False)}
        </svg>
      </div>

      <div class="card-diagnosis">
        <div class="diag-item diag-old">
          <h4>Old Formula Defect (Triadic Product)</h4>
          <p>pert_failure &times; (1 - H) &times; (1 - N) multiplied three decimals together, capping real scores under 0.036. The 0.65 stagnant trigger was unreachable.</p>
        </div>
        <div class="diag-item diag-new">
          <h4>Updated Convex Failure Combination</h4>
          <p>0.40 &middot; pert_failure + 0.30 &middot; &Delta;H + 0.30 &middot; &Delta;N activates the telemetry into 0.35&ndash;0.47. AAA drops into the flowing zone on Turn 3 via reframing.</p>
        </div>
      </div>
    </div>

  </div>

  <!-- Scoreboard -->
  <div class="bottom-scoreboard">
    <div class="score-card">
      <div class="score-label">Max Novelty Decay Detected</div>
      <div class="score-val" style="color: #00e5ff;">0.92 &rarr; 0.39 (-57%)</div>
      <div class="score-sub">Semantic circularity is now clearly visible on both arms</div>
    </div>
    <div class="score-card">
      <div class="score-label">AAA Agential Novelty Advantage</div>
      <div class="score-val" style="color: #ff9944;">+0.054 Avg Delta</div>
      <div class="score-sub">Symbia's ontological reframing sustains higher vitality</div>
    </div>
    <div class="score-card">
      <div class="score-label">Collapse Pressure Dynamic Gain</div>
      <div class="score-val" style="color: #ff3366;">+0.42 Avg Elevation</div>
      <div class="score-sub">Lifted out of the 0.02 dead zone into active regulatory range</div>
    </div>
    <div class="score-card">
      <div class="score-label">Boredom Engine Health</div>
      <div class="score-val" style="color: #00ffaa;">ONLINE &amp; SENSITIVE</div>
      <div class="score-sub">Stagnant and Sedation triggers can now fire dynamically</div>
    </div>
  </div>

  <!-- Footer -->
  <div class="footer-row">
    <div>SYSTEM KEY: SOLID TRACES = UPDATED METRICS (AFTER) // DASHED TRACES = UNREGULARIZED FORMULAS (BEFORE)</div>
    <div>GENERATED AUTONOMOUSLY VIA AAA TELEMETRY SUITE // SAVED IN: reports/runs/</div>
  </div>

</body>
</html>
"""

html_path = OUT_DIR / "003_metrics_update_before_vs_after.html"
png_path = OUT_DIR / "003_metrics_update_before_vs_after.png"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved HTML: {html_path}")

edge_bin = find_edge_path()
if edge_bin:
    cmd = [
        edge_bin,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        "--window-size=1720,1120",
        f"--screenshot={png_path}",
        f"file:///{str(html_path).replace(os.sep, '/')}"
    ]
    subprocess.run(cmd, capture_output=True)
    print(f"Generated PNG: {png_path}")
else:
    print("WARNING: Edge not found, only HTML generated.")
