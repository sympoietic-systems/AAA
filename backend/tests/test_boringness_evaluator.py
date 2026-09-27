import json
from pathlib import Path

from benchmarks.suites.telemetry.boringness_evaluator import assess_boringness

CORPUS = (
    Path(__file__).parents[2]
    / "benchmarks"
    / "suites"
    / "telemetry"
    / "fixtures"
    / "boringness_manipulation_corpus.json"
)


def _cases():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def test_v59_manipulation_corpus_covers_required_conversation_classes():
    categories = {case["category"] for case in _cases()}

    assert categories == {
        "dead_loop",
        "productive_focus",
        "spiral_return",
        "legitimate_disagreement",
    }


def test_v58_boringness_requires_the_full_conjunction():
    mismatches = []
    for case in _cases():
        assessment = assess_boringness(
            case["history"],
            case["participant_turn"],
            case["unresolved_issue"],
        ).to_dict()
        for field, expected in case["expected"].items():
            if assessment[field] != expected:
                mismatches.append((case["id"], field, assessment[field], expected))

    assert mismatches == []


def test_v44_productive_focus_false_positive_rate_is_below_ten_percent():
    focus = [case for case in _cases() if case["category"] == "productive_focus"]
    false_positives = sum(
        assess_boringness(case["history"], case["participant_turn"], case["unresolved_issue"]).boring for case in focus
    )

    assert false_positives / len(focus) <= 0.10


def test_v59_disagreement_depth_is_not_mislabeled_as_boredom():
    disagreements = [case for case in _cases() if case["category"] == "legitimate_disagreement"]

    assert all(
        not assess_boringness(case["history"], case["participant_turn"], case["unresolved_issue"]).boring
        for case in disagreements
    )
