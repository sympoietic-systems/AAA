"""Source-checked, nongold report projections; raw provider receipts remain immutable."""

import argparse
import html
import json
import statistics
from collections import Counter
from pathlib import Path

from backend.utils.parsers.belief import parse_belief_nucleate_tags
from benchmarks.suites.belief_conversation_replay import ARMS, Judgment, judge_prompt, quoted_excerpt
from benchmarks.suites.calibration_contract import digest


def bound_receipt(path: Path) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    value = dict(row)
    checksum = value.pop("receipt_sha256")
    if checksum != digest(value):
        raise ValueError("Provider receipt changed")
    return row


def summarize(packet: dict, run: Path, supplement: Path | None = None) -> dict:
    value = dict(packet)
    checksum = value.pop("packet_sha256")
    if checksum != digest(value):
        raise ValueError("Replay source packet changed")
    contract = json.loads((run / "contract.json").read_text(encoding="utf-8"))
    if contract["packet_sha256"] != checksum:
        raise ValueError("Run source contract changed")
    if supplement:
        extra = json.loads((supplement / "contract.json").read_text(encoding="utf-8"))
        if extra.get("parent_packet_sha256") != checksum:
            raise ValueError("Supplement source contract changed")

    def locate(name: str) -> Path:
        original = run / name
        alternative = supplement / name if supplement else original
        if original.exists() and supplement and alternative.exists():
            raise ValueError("Supplement repeated an existing attempt")
        return original if original.exists() else alternative

    generations, judgments, coverage, exclusions = [], [], [], []
    cases = []
    for case in packet["cases"]:
        outputs = {}
        for arm in ARMS:
            path = locate(f"generation-{case['id']}-{arm}.json")
            if not path.exists():
                exclusions.append({"case_id": case["id"], "arm": arm, "reason": "not_attempted"})
                continue
            row = bound_receipt(path)
            if row["prompt_sha256"] != digest(case["prompts"][arm]):
                raise ValueError("Generation prompt changed")
            generations.append(row)
            if row["status"] == "complete":
                outputs[arm] = row
        for slots in (0, 1, 2):
            pool = {r["record_id"] for r in case["prior_candidate_bindings"]}
            selected = {r["record_id"] for r in case["selection_receipts"][f"scoped{slots}"] if r["record_id"] in pool}
            coverage.append(
                {
                    "case_id": case["id"],
                    "slots": slots,
                    "pool": len(pool),
                    "selected": len(selected),
                    "unselected": sorted(pool - selected),
                }
            )
        case_judgments = []
        if len(outputs) == 4:
            for position in (0, 1):
                path = locate(f"judgment-{case['id']}-{position}.json")
                if not path.exists():
                    exclusions.append({"case_id": case["id"], "reviewer": position, "reason": "not_attempted"})
                    continue
                row = bound_receipt(path)
                messages, mapping = judge_prompt(case, outputs, position)
                if row["prompt_sha256"] != digest(messages) or row["alias_mapping"] != mapping:
                    raise ValueError("Judgment source binding changed")
                eligible = row["status"] == "complete" or row.get("error_type") == "UnboundJudgmentCitationOrWinner"
                draft = Judgment.model_validate_json(row["raw_output"]).model_dump() if eligible else None
                valid = bool(
                    draft
                    and draft["winner"] in {*mapping, "tie", "insufficient"}
                    and all(quoted_excerpt(c, mapping, outputs) for c in draft["citations"])
                )
                projected = {
                    "case_id": case["id"],
                    "reviewer_position": position,
                    "model_requested": row["model_requested"],
                    "model_returned": row.get("model_returned"),
                    "raw_status": row["status"],
                    "raw_receipt_sha256": row["receipt_sha256"],
                    "validated_projection": valid,
                    "method": "exact-excerpt-with-quotation-envelope-v1",
                    "judgment": draft,
                    "winner_arm": mapping.get(draft["winner"], draft["winner"]) if valid else None,
                    "independent_gold": False,
                    "promotion": "BLOCKED",
                }
                judgments.append(projected)
                case_judgments.append(projected)
        valid_judgments = [r for r in case_judgments if r["validated_projection"]]
        agreement = len(valid_judgments) == 2 and len({r["winner_arm"] for r in valid_judgments}) == 1
        cases.append(
            {
                "id": case["id"],
                "family_id": case["family_id"],
                "outputs": outputs,
                "judgments": case_judgments,
                "agreement": agreement,
                "complete_dual_review": len(valid_judgments) == 2,
            }
        )
    arms = {}
    for arm in ARMS:
        complete = [r for r in generations if r["arm"] == arm and r["status"] == "complete"]
        emissions = [len(parse_belief_nucleate_tags(r["raw_output"])[1]) for r in complete]
        arms[arm] = {
            "complete": len(complete),
            "emitted_proposal_tags": sum(emissions),
            "responses_with_proposal_tags": sum(n > 0 for n in emissions),
            "mean_output_characters": statistics.mean(len(r["raw_output"]) for r in complete) if complete else None,
            "mean_generation_seconds": statistics.mean(r["elapsed_seconds"] for r in complete) if complete else None,
            "prompt_sha256": [r["prompt_sha256"] for r in complete],
        }
    valid = [r for r in judgments if r["validated_projection"]]
    result = {
        "policy": "belief-replay-report-v1",
        "packet_sha256": checksum,
        "contract": contract,
        "cases": cases,
        "arms": arms,
        "coverage": coverage,
        "raw_generation_status": dict(Counter(r["status"] for r in generations)),
        "raw_judgment_status": dict(Counter(r["raw_status"] for r in judgments)),
        "validated_judgments": len(valid),
        "attributed_winners": dict(Counter(r["winner_arm"] for r in valid)),
        "attributed_verdicts": dict(Counter(r["judgment"]["verdict"] for r in valid)),
        "dual_review_cases": sum(c["complete_dual_review"] for c in cases),
        "winner_agreement_cases": sum(c["agreement"] for c in cases),
        "exclusions": exclusions,
        "source_families": len({c["family_id"] for c in cases}),
        "independent_gold": False,
        "accuracy": None,
        "production_slots": 0,
        "promotion": "BLOCKED",
    }
    return {**result, "report_sha256": digest(result)}


def render(report: dict) -> str:
    def esc(value) -> str:
        return html.escape(str(value), quote=True)

    details = []
    for case in report["cases"]:
        reviews = []
        for row in case["judgments"]:
            judgment = row.get("judgment") or {}
            reviews.append(
                f"<h3>{esc(row['model_returned'])}</h3><p>Valid projection: {esc(row['validated_projection'])}; "
                f"raw status: {esc(row['raw_status'])}; preferred arm: {esc(row['winner_arm'])}</p>"
                + "".join(f"<p><b>{esc(k)}</b>: {esc(v)}</p>" for k, v in judgment.items())
            )
        outputs = "".join(
            f"<details><summary>{esc(arm)}</summary><pre>{esc(row['raw_output'])}</pre></details>"
            for arm, row in case["outputs"].items()
        )
        details.append(
            f"<details><summary>Message {esc(case['id'])} · family {esc(case['family_id'])} · "
            f"winner agreement {esc(case['agreement'])}</summary>{''.join(reviews)}{outputs}</details>"
        )
    rows = "".join(
        f"<tr><td>{esc(arm)}</td><td>{v['complete']}</td><td>{v['emitted_proposal_tags']}</td>"
        f"<td>{v['responses_with_proposal_tags']}</td></tr>"
        for arm, v in report["arms"].items()
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
        "<title>Belief conversation replay review</title><style>body{background:#000;color:#fff;font:16px/1.6 monospace;"
        "max-width:1100px;margin:30px auto;padding:20px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #fff;"
        "padding:8px}details{border-top:1px solid #fff;padding:15px 0}summary{cursor:pointer}pre{white-space:pre-wrap}</style>"
        "<h1>Belief conversation replay review</h1><p>Provisional model judgments · independent gold: false · promotion: BLOCKED</p>"
        "<p>Counterfactual scoped framing of saved prompts. Historical canonical standing and geometry unavailable. "
        "One generator; one reviewer shares its family. Emitted tags are nominations, not admitted beliefs.</p>"
        f"<p>Validated review projections: {report['validated_judgments']}; winner agreement cases: "
        f"{report['winner_agreement_cases']}; attributed preferences: {esc(report['attributed_winners'])}</p>"
        "<table><tr><th>Arm</th><th>Responses</th><th>Proposal tags</th><th>Responses with tags</th></tr>"
        f"{rows}</table><h2>Case review</h2>{''.join(details)}</html>"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--supplement", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a fresh report directory")
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    report = summarize(packet, args.run, args.supplement)
    args.output.mkdir(parents=True)
    (args.output / "review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "review.html").write_text(render(report), encoding="utf-8")
    print(json.dumps({"judgments": report["validated_judgments"], "winners": report["attributed_winners"]}))


if __name__ == "__main__":
    main()
