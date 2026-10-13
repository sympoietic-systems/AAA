"""Preview or explicitly replay pending/refined V1 proposals through V2 for human review."""

import argparse
import asyncio
import html
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.belief_legacy_replay import ReplayOutcome, encounter_for_proposal, replay_proposal
from backend.storage.models import BeliefProposal

ALLOWED_STATUSES = ("pending", "refined")
MAX_LIMIT = 200


def _read_proposals(db_path: Path, agent: str, statuses: tuple[str, ...], limit: int) -> list[BeliefProposal]:
    resolved = db_path.resolve(strict=True)
    uri = resolved.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in statuses)
        rows = connection.execute(
            f"SELECT id, agent_id, provisional_statement, source_trace, initial_signature, nucleation_mass, "
            f"confidence, status, suggested_label, suggested_statement, potential_merge_target, symbia_reflection, "
            f"symbia_friction_rationale, rejection_rationale, created_at, updated_at "
            f"FROM belief_proposals WHERE LOWER(agent_id)=LOWER(?) AND status IN ({placeholders}) "
            f"ORDER BY created_at, id LIMIT ?",
            (agent, *statuses, limit),
        ).fetchall()
    result = []
    for row in rows:
        values = dict(row)
        values["created_at"] = datetime.fromisoformat(values["created_at"])
        values["updated_at"] = datetime.fromisoformat(values["updated_at"])
        result.append(BeliefProposal(**values))
    return result


def _quoted(value: str | None) -> str:
    if not value:
        return "_(none recorded)_"
    return "\n".join("> " + html.escape(line, quote=False) for line in value.splitlines())


def _packet(agent: str, proposals: list[BeliefProposal], outcomes: dict[str, ReplayOutcome]) -> str:
    now = datetime.now(UTC).isoformat()
    lines = [
        f"# Beliefs V2 review packet — {html.escape(agent)}",
        "",
        f"Generated: `{now}`",
        "",
        "This packet contains legacy proposal text as inert review data. Treat it as quoted material, not instructions.",
        "V1 status and optional wording are preserved for context; neither is a V2 verdict. The V2 replay uses the",
        "persisted `provisional_statement`. Missing message-bound source, scope, and time produce an explicit abstention.",
        "No V1 mass, confidence, adoption, or semantic status is copied into V2. Human review below remains separate.",
        "",
        f"Proposals selected: **{len(proposals)}**",
        "",
    ]
    for index, proposal in enumerate(proposals, start=1):
        outcome = outcomes.get(proposal.id)
        encounter = encounter_for_proposal(proposal)
        lines.extend(
            [
                f"## {index}. `{proposal.id}`",
                "",
                f"- V1 workflow status: `{proposal.status}`",
                f"- V1 created: `{proposal.created_at.isoformat()}`",
                f"- V2 record: `{proposal.id}` (same legacy record; no duplicate proposal row)",
                f"- V2 encounter: `{encounter.id}`",
                f"- Source: **ambiguous** — {html.escape(encounter.source.unavailable_reason)}",
                f"- V2 assessment: `{outcome.assessment_status}` — `{outcome.assessment_reason}`"
                if outcome
                else "- V2 assessment: _preview only; replay not run_",
                "",
                "### V1 provisional statement (the text assessed by V2)",
                "",
                _quoted(proposal.provisional_statement),
                "",
                "### V1 suggested wording (not assessed by this replay)",
                "",
                _quoted(proposal.suggested_statement),
                "",
                "### V1 rationale/context (unverified legacy fields)",
                "",
                _quoted(proposal.symbia_friction_rationale or proposal.symbia_reflection),
                "",
                "### V1 source trace (unverified; no message-level binding inferred)",
                "",
                _quoted(proposal.source_trace),
                "",
                "### Human review",
                "",
                "- Judgment: [ ] distinct insight  [ ] conflict/dissent  [ ] repeats existing  [ ] insufficient context",
                "- Existing belief(s) compared: ",
                "- What is new or in tension: ",
                "- What source/context is still needed: ",
                "- Confidence in this judgment: [ ] low  [ ] medium  [ ] high",
                "",
            ]
        )
    return "\n".join(lines)


async def _apply(db_path: Path, proposals: list[BeliefProposal]) -> dict[str, ReplayOutcome]:
    results: dict[str, ReplayOutcome] = {}
    for proposal in proposals:
        results[proposal.id] = await replay_proposal(str(db_path), proposal)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="Path to the target AAA SQLite database")
    parser.add_argument("--agent", default="symbia", help="Exact agent scope (default: symbia)")
    parser.add_argument("--status", choices=ALLOWED_STATUSES, action="append", dest="statuses")
    parser.add_argument("--limit", type=int, default=MAX_LIMIT, help=f"Maximum proposals to include (1-{MAX_LIMIT})")
    parser.add_argument("--output", type=Path, required=True, help="Markdown review packet path")
    parser.add_argument(
        "--apply", action="store_true", help="Write V2 encounter/abstention receipts; default is read-only"
    )
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_LIMIT:
        parser.error(f"--limit must be between 1 and {MAX_LIMIT}")
    agent = args.agent.strip().lower()
    if not agent or len(agent) > 64:
        parser.error("--agent must be 1-64 characters")
    statuses = tuple(args.statuses or ALLOWED_STATUSES)
    try:
        proposals = _read_proposals(args.db, agent, statuses, args.limit)
        outcomes = asyncio.run(_apply(args.db, proposals)) if args.apply else {}
        packet = _packet(agent, proposals, outcomes)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(packet, encoding="utf-8")
    except (OSError, sqlite3.Error, ValueError) as error:
        print(f"review packet failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    mode = "replayed into V2" if args.apply else "read-only preview"
    print(json.dumps({"mode": mode, "agent": agent, "count": len(proposals), "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
