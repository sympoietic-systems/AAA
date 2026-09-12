#!/usr/bin/env python3
"""
Generate before-and-after oscilloscope telemetry plot across all newly calibrated metrics:
1. Conceptual Novelty (N_t)
2. Collapse Pressure / Boringness (CP_t)
3. Divergence Resolution Ratio (DRR_t)
4. Gordon Pask Cybernetic Health (H_pask)
5. Conceptual Velocity (v_t)
6. Reverse Perturbation (rP_t)

Saves HTML and renders high-resolution PNG into reports/runs/
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from reports.runs import (  # noqa: F401
    full_suite_calibrated,
)
from importlib.machinery import SourceFileLoader

# Load compare_runs dynamically
compare_script = PROJECT_ROOT / "reports" / "003-empirical-10-turn-benchmark" / "compare_runs.py"
compare_runs = SourceFileLoader("compare_runs", str(compare_script)).load_module()

def main():
    runs_dir = PROJECT_ROOT / "reports" / "runs"
    ref_dir = PROJECT_ROOT / "reports" / "003-empirical-10-turn-benchmark"
    
    # Target run: eval_calibrated if available, else eval_updated
    target_dir = runs_dir / "eval_calibrated"
    if not target_dir.exists():
        target_dir = runs_dir / "eval_updated"

    out_dir = runs_dir / "full_suite_calibrated"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[AUDIT] Comparing Reference: {ref_dir.name} vs Target: {target_dir.name}")
    data_a = compare_runs.load_receipts(ref_dir)
    data_b = compare_runs.load_receipts(target_dir)

    # Print CLI tables
    compare_runs.print_cli_table(ref_dir.name, target_dir.name, data_a, data_b)

    # Render multi-panel dashboard
    html_file, png_file = compare_runs.render_comparison_dashboard(
        ref_dir.name,
        target_dir.name,
        data_a,
        data_b,
        out_dir,
        custom_name="full_suite_calibrated"
    )

    # Also update legacy file name in runs/ if desired
    legacy_html = runs_dir / "003_metrics_update_before_vs_after.html"
    legacy_png = runs_dir / "003_metrics_update_before_vs_after.png"
    if html_file.exists():
        with open(html_file, "r", encoding="utf-8") as src, open(legacy_html, "w", encoding="utf-8") as dst:
            dst.write(src.read())
    if png_file.exists():
        import shutil
        shutil.copy2(png_file, legacy_png)

    print(f"\nSUCCESS: Generated multi-metric dashboard in {out_dir}:")
    print(f"  Plot: {png_file}")
    print(f"  HTML: {html_file}")

if __name__ == "__main__":
    main()
