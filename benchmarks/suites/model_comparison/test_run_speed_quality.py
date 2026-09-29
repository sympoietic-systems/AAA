import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from benchmarks.suites.model_comparison.run_speed_quality import _quality_pass


def test_quality_accepts_valid_markdown_bullets_and_branch_clamp() -> None:
    assert _quality_pass(
        "bullets",
        "- [A] Wait briefly then retry the request\n"
        "- [B] Implement exponential backoff for retries\n"
        "- [C] Respect rate limits and adjust frequency",
    )
    assert _quality_pass(
        "code",
        "def clamp(value, lower, upper):\n"
        "    if value < lower:\n"
        "        return lower\n"
        "    if value > upper:\n"
        "        return upper\n"
        "    return value\n",
    )
