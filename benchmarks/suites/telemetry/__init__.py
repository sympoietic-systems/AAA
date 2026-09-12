"""
Telemetry benchmark suite: 14 calibrated cybernetic dimensions, allostasis, Paskian viability.
"""

from .runner import TelemetryBenchmarkSuite
from .evaluator import evaluate_sequence, compute_statistics, METRIC_KEYS
from .comparator import compare_runs, MetricDelta
from .visualizer import (
    render_14_panel_comparison_dashboard,
    render_single_audit_dashboard,
    plot_telemetry_oscilloscope,
    plot_quartile_stability,
    plot_differential_changes,
)
from .live import run_baseline_llm, run_aaa_apparatus

__all__ = [
    "TelemetryBenchmarkSuite",
    "evaluate_sequence",
    "compute_statistics",
    "METRIC_KEYS",
    "compare_runs",
    "MetricDelta",
    "render_14_panel_comparison_dashboard",
    "render_single_audit_dashboard",
    "plot_telemetry_oscilloscope",
    "plot_quartile_stability",
    "plot_differential_changes",
    "run_baseline_llm",
    "run_aaa_apparatus",
]
