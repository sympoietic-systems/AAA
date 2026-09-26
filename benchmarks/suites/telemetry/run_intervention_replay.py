"""Audit legacy conversation receipts against the causal receipt contract."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = (
    PROJECT_ROOT / "docs" / "reports" / "015-empirical-15-turn-boredom-benchmark" / "agential_boredom_receipts.json"
)


def audit_legacy_receipts(source: Path) -> dict[str, Any]:
    raw = json.loads(source.read_text(encoding="utf-8"))
    turns = raw.get("aaa_agential", [])
    outcome_scores = []
    for index in range(len(turns)):
        next_prompts = [turns[item].get("user", "") for item in range(index + 1, min(len(turns), index + 3))]
        from benchmarks.suites.telemetry.intervention_evaluator import rate_participant_turn

        ratings = [rate_participant_turn(prompt) for prompt in next_prompts]
        if ratings:
            outcome_scores.append(mean(rating.joint_progress for rating in ratings))

    required = {
        "trigger_metrics",
        "intervention",
        "requested_controls",
        "applied_controls",
        "response_metrics",
        "next_turn_outcomes",
    }
    missing = sorted(required - set().union(*(turn.keys() for turn in turns))) if turns else sorted(required)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(source.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "turn_count": len(turns),
        "causal_contract_complete": not missing,
        "missing_fields": missing,
        "legacy_outcome_proxy": {
            "mean": round(mean(outcome_scores), 4) if outcome_scores else None,
            "scored_turns": len(outcome_scores),
            "interpretation": "descriptive only; legacy receipts do not preserve pre/post causal ordering",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = audit_legacy_receipts(args.input.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
