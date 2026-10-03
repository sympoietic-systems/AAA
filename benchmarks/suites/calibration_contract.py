"""Independent annotation, split integrity and uncertainty reporting for offline calibration."""

import hashlib
import json
import math
import statistics


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def reviewed_label(case: dict) -> tuple[object | None, str | None]:
    annotations = case.get("annotations", [])
    valid = [
        a
        for a in annotations
        if a.get("independent") is True
        and a.get("annotator_id")
        and a.get("rationale")
        and a.get("method") in {"human", "independent_model"}
    ]
    humans = [a for a in valid if a["method"] == "human"]
    models = {
        a.get("independence_group")
        for a in valid
        if a["method"] == "independent_model"
        and a.get("independence_group")
        and a.get("independence_group") != case.get("author_model")
    }
    if not humans and (len(models) < 2 or not case.get("author_model")):
        return None, "independent_labels_required"
    votes = {digest(a.get("label")): a.get("label") for a in valid}
    if len(votes) != 1:
        return "abstain", "annotator_disagreement"
    return next(iter(votes.values())), None


def validate_splits(cases: list[dict]) -> None:
    seen = {}
    identifiers = set()
    for case in cases:
        if case["id"] in identifiers or case.get("split") not in {"tune", "validation", "heldout"}:
            raise ValueError("duplicate case or invalid split")
        identifiers.add(case["id"])
        for entity in case["split_entities"]:
            if entity in seen and seen[entity] != case["split"]:
                raise ValueError("entity/topic leakage across splits")
            seen[entity] = case["split"]


def wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.96
    p = successes / total
    denominator = 1 + z * z / total
    midpoint = (p + z * z / (2 * total)) / denominator
    width = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0, midpoint - width), min(1, midpoint + width)]


def belief_score(rows: list[dict]) -> dict:
    trials = rows
    latencies = [
        r["receipt"]["latency_ms"]
        + (
            r["receipt"].get("relation_receipt", {}).get("latency_ms", 0)
            if not r["receipt"].get("latency_includes_relation")
            else 0
        )
        for r in trials
        if "latency_ms" in r["receipt"]
    ]
    # Repeat trials do not increase the independent sample size.
    grouped = {}
    for row in rows:
        key = row.get("id", str(len(grouped)))
        if key not in grouped or row["receipt"].get("route") == "review_contradiction":
            grouped[key] = row
    rows = list(grouped.values())
    valid = [r for r in rows if r.get("gold") in {"contradiction", "endorsement", "orthogonal", "abstain"}]
    predictions = [r for r in valid if r["receipt"].get("route") == "review_contradiction"]
    false = sum(r["gold"] != "contradiction" for r in predictions)
    negatives = sum(r["gold"] != "contradiction" for r in valid)
    precision = wilson(len(predictions) - false, len(predictions))
    fp = wilson(false, negatives)
    return {
        "labeled_rows": len(valid),
        "contradiction_reviews": len(predictions),
        "false_contradictions": false,
        "contradiction_precision_ci95": precision,
        "false_positive_rate_ci95": fp,
        "abstentions": sum(r["receipt"].get("route") == "abstain" for r in valid),
        "watchlist": sum(r["receipt"].get("route") == "watchlist" for r in valid),
        "correct_relations": sum(r["receipt"].get("relation") == r["gold"] for r in valid),
        "execution_failures": sum(r["receipt"].get("status") == "unavailable" for r in trials),
        "median_latency_ms": statistics.median(latencies) if latencies else None,
        "promotion": "BLOCKED",
        "reason": "independent held-out evidence and reviewed opt-in required",
    }
