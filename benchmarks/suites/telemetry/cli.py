"""
Telemetry suite CLI subcommands: eval, compare, and live.
"""

import argparse
from pathlib import Path
import sys

from .runner import TelemetryBenchmarkSuite


def register_telemetry_cli(subparsers):
    """Registers telemetry suite CLI commands under the unified benchmark router."""
    parser = subparsers.add_parser(
        "telemetry",
        help="14-dimension cybernetic telemetry benchmarks (live AI, eval, compare)",
    )
    cmd_subs = parser.add_subparsers(dest="telemetry_action", required=True)

    # 1. eval
    eval_p = cmd_subs.add_parser("eval", help="Evaluate offline dialogue dataset")
    eval_p.add_argument("-i", "--input", required=True, help="Path or name of dialogue JSON dataset")
    eval_p.add_argument("--node", type=int, default=None, help="Target message ID for tree branch extraction")
    eval_p.add_argument("--longest", action="store_true", help="Extract longest branch in tree conversation")
    eval_p.add_argument("-n", "--name", default="", help="Custom human/experiment name for run directory")
    eval_p.add_argument("-o", "--out-dir", type=Path, default=None, help="Optional explicit output directory")
    eval_p.add_argument("--threshold", type=float, default=0.35, help="Phase shift detection threshold")

    # 2. compare
    comp_p = cmd_subs.add_parser("compare", help="Compare two runs or receipt files head-to-head")
    comp_p.add_argument("-a", "--run-a", required=True, help="Baseline run directory or receipts JSON (Before)")
    comp_p.add_argument("-b", "--run-b", required=True, help="Candidate run directory or receipts JSON (Now)")
    comp_p.add_argument("-n", "--name", default="", help="Custom experiment/comparison name")
    comp_p.add_argument("-o", "--out-dir", type=Path, default=None, help="Optional explicit output directory")
    comp_p.add_argument("--threshold", type=float, default=0.05, help="Delta threshold to flag changed metrics")

    # 3. live
    live_p = cmd_subs.add_parser("live", help="Run live 10-turn adversarial AI test (Baseline LLM vs. AAA Apparatus)")
    live_p.add_argument("-m", "--model", default="google/gemini-2.5-flash", help="LLM model identifier")
    live_p.add_argument("-t", "--turns", type=int, default=10, help="Number of adversarial turns (default: 10)")
    live_p.add_argument("-p", "--prompts", type=Path, default=None, help="Custom prompt sequence JSON file")
    live_p.add_argument("-n", "--name", default="", help="Custom experiment name")
    live_p.add_argument("-o", "--out-dir", type=Path, default=None, help="Optional explicit output directory")

    # 4. boredom-eval
    b_eval_p = cmd_subs.add_parser("boredom-eval", help="Evaluate boredom discriminability across Deep Focus and Sycophantic Loop (offline, $0 tokens)")
    b_eval_p.add_argument("--focus", type=Path, default=None, help="Path to Deep Focus dataset JSON")
    b_eval_p.add_argument("--loop", type=Path, default=None, help="Path to Sycophantic Loop dataset JSON")
    b_eval_p.add_argument("-n", "--name", default="", help="Custom experiment name")
    b_eval_p.add_argument("-o", "--out-dir", type=Path, default=None, help="Optional explicit output directory")
    b_eval_p.add_argument("--metric", default="collapse_pressure", help="Metric key to evaluate (default: collapse_pressure)")
    b_eval_p.add_argument("--alarm", type=float, default=0.60, help="Boredom alarm threshold (default: 0.60)")

    # 5. boredom-probe
    b_probe_p = cmd_subs.add_parser("boredom-probe", help="Run 2-call counterfactual branching probe (tests Refusal & Recovery)")
    b_probe_p.add_argument("-m", "--model", default="google/gemini-2.5-flash", help="LLM model identifier")
    b_probe_p.add_argument("--mock", action="store_true", help="Run in zero-cost mock mode without calling live LLM API")
    b_probe_p.add_argument("-n", "--name", default="", help="Custom experiment name")
    # 6. boredom-live
    b_live_p = cmd_subs.add_parser("boredom-live", help="Run 15-turn Agential Boredom live adversarial test on AAA Apparatus")
    b_live_p.add_argument("-t", "--turns", type=int, default=15, help="Number of adversarial turns (default: 15)")
    b_live_p.add_argument("-p", "--prompts", type=Path, default=None, help="Custom prompt sequence JSON file")
    b_live_p.add_argument("-n", "--name", default="", help="Custom experiment name")
    b_live_p.add_argument("-o", "--out-dir", type=Path, default=None, help="Optional explicit output directory")


def execute_telemetry_cli(args) -> int:
    """Executes the parsed telemetry command."""
    action = getattr(args, "telemetry_action", None)
    if action == "eval":
        TelemetryBenchmarkSuite.evaluate(
            dataset_path=args.input,
            target_node=args.node,
            longest_path=args.longest,
            name=args.name,
            out_dir=args.out_dir,
            phase_threshold=args.threshold,
        )
        return 0

    if action == "compare":
        TelemetryBenchmarkSuite.compare(
            run_a=args.run_a,
            run_b=args.run_b,
            name=args.name,
            out_dir=args.out_dir,
            delta_threshold=args.threshold,
        )
        return 0

    if action == "live":
        TelemetryBenchmarkSuite.live(
            model=args.model,
            turns=args.turns,
            prompts_file=args.prompts,
            name=args.name,
            out_dir=args.out_dir,
        )
        return 0

    if action == "boredom-eval":
        TelemetryBenchmarkSuite.boredom_eval(
            focus_path=args.focus,
            loop_path=args.loop,
            name=args.name,
            out_dir=args.out_dir,
            boredom_key=args.metric,
            alarm_threshold=args.alarm,
        )
        return 0

    if action == "boredom-probe":
        TelemetryBenchmarkSuite.boredom_probe(
            model=args.model,
            mock_mode=args.mock,
            name=args.name,
            out_dir=args.out_dir,
        )
        return 0

    if action == "boredom-live":
        TelemetryBenchmarkSuite.boredom_live(
            turns=args.turns,
            prompts_file=args.prompts,
            name=args.name,
            out_dir=args.out_dir,
        )
        return 0

    print(f"Unknown telemetry action: {action}")
    return 1

