"""Score the active diffractive policy against labeled focus and loop corpora."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from backend.modules.retrieval.diffractive_activation import decide_diffractive_activation


def evaluate(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    streak = 0
    active = False
    for turn in turns:
        metrics = turn.get("metrics") or {}
        pressure = metrics.get("collapse_pressure")
        if pressure is None:
            continue
        streak = streak + 1 if pressure >= 0.55 else 0
        decision = decide_diffractive_activation(
            collapse_pressure=float(pressure),
            rolling_entropy=float(metrics.get("rolling_entropy") or 0.5),
            vitality=float(metrics.get("vitality") or 0.5),
            streak=streak,
            currently_active=active,
        )
        active = decision.active
        rows.append({"score": decision.score, "active": active, "reason": decision.reason})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.scorecard.read_text(encoding="utf-8"))
    focus = evaluate(source["focus_turns"])
    loop = evaluate(source["loop_turns"])
    result = {
        "proposal": focus[0]["reason"] if focus else "unknown",
        "focus_false_positive_rate": round(100 * sum(row["active"] for row in focus) / max(1, len(focus)), 1),
        "loop_false_negative_rate": round(100 * sum(not row["active"] for row in loop) / max(1, len(loop)), 1),
        "focus": focus,
        "loop": loop,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"focus", "loop"}}))


if __name__ == "__main__":
    main()
