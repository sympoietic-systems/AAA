"""
Unified CLI Router for AAA Benchmarking Platform.

Usage:
  # Explicit suite routing:
  python -m benchmarks.cli telemetry eval -i benchmarks/data/dialogues/dialogue_1555_branched_all_messages.json
  python -m benchmarks.cli telemetry compare -a run_A -b run_B
  python -m benchmarks.cli telemetry live --turns 10 --model google/gemini-2.5-flash

  # Shorthand (defaults to telemetry suite):
  python -m benchmarks.cli eval -i benchmarks/data/dialogues/dialogue_3527_all_messages.json
  python -m benchmarks.cli compare -a run_A -b run_B
"""

import argparse
import sys
from benchmarks.suites.telemetry.cli import register_telemetry_cli, execute_telemetry_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchmarks",
        description="AAA Modular Benchmarking Platform: Cybernetic Telemetry, Memory, Agents, & Belief Systems",
    )
    subparsers = parser.add_subparsers(dest="suite_name", help="Benchmark suite name")

    # Register suites
    register_telemetry_cli(subparsers)

    return parser


def main():
    # Shorthand support: if first arg is an action, prepend 'telemetry'
    argv = sys.argv[1:]
    if argv and argv[0] in ("eval", "compare", "live", "boredom-eval", "boredom-probe"):
        argv = ["telemetry"] + argv

    parser = build_parser()
    if not argv:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args(argv)

    if args.suite_name == "telemetry":
        sys.exit(execute_telemetry_cli(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
