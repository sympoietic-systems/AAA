"""
AAA Modular Benchmarking Platform.

Provides extensible benchmark suites across cybernetic telemetry, memory,
agents, and belief metabolism, with unified run tracking, structured logging,
and restrained cyberpunk visualizations.
"""

from benchmarks.common.base import BaseBenchmarkSuite, RunMetadata
from benchmarks.common.loader import DialogueDataset, DialogueMessage, load_dataset, resolve_embeddings
from benchmarks.suites.telemetry import (
    TelemetryBenchmarkSuite,
    compare_runs,
    compute_statistics,
    evaluate_sequence,
    plot_telemetry_oscilloscope,
    render_14_panel_comparison_dashboard,
    render_single_audit_dashboard,
)

# Compatibility alias
Benchmarker = TelemetryBenchmarkSuite

__all__ = [
    "BaseBenchmarkSuite",
    "RunMetadata",
    "DialogueDataset",
    "DialogueMessage",
    "load_dataset",
    "resolve_embeddings",
    "TelemetryBenchmarkSuite",
    "Benchmarker",
    "evaluate_sequence",
    "compute_statistics",
    "compare_runs",
    "render_14_panel_comparison_dashboard",
    "render_single_audit_dashboard",
    "plot_telemetry_oscilloscope",
]
