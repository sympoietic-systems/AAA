"""Revalidate this saved run and regenerate the linked audit receipt without provider calls."""

import importlib
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
review_module = importlib.import_module("benchmarks.suites.belief_auto_review")

report = ROOT / "docs/reports/051-belief-v2-automated-review"
run = Path(__file__).resolve().parent
packet = json.loads((ROOT / "docs/reports/049-belief-v2-review-corpus/review-packet.json").read_text(encoding="utf-8"))
frozen = json.loads((run / "frozen-provisional.json").read_text(encoding="utf-8"))
review_module.validate_provisional(packet, frozen)
(run / "review.html").write_text(review_module.render_review(frozen), encoding="utf-8")
rows = [r for c in frozen["cases"] for r in c["reviewers"]]
families = {}
for c in frozen["cases"]:
    families.setdefault(c["family_id"], Counter())[c["review_outcome"]] += 1
docs = [
    report / "README.md",
    ROOT / "docs/decisions/ADR-117-provisional-automated-belief-review.md",
    ROOT / "docs/systems/BELIEF_SPEC.md",
]
links_checked = 0
for doc in docs:
    for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
        if ":" in target or target.startswith("#"):
            continue
        resolved = doc.parent / target.split("#")[0]
        if resolved != report / "verification.json":
            assert resolved.exists(), (doc.name, target)
        links_checked += 1
files = (
    list(report.glob("*"))
    + docs
    + [ROOT / "benchmarks/suites/belief_auto_review.py", ROOT / "benchmarks/tests/test_belief_auto_review.py"]
)
for directory in (ROOT / "benchmarks/runs/belief-auto-review").glob("2026-10-08-t4-v*"):
    files.extend(p for p in directory.rglob("*") if p.is_file() and p.suffix in {".json", ".html", ".py"})
values = dotenv_values(ROOT / ".env")
secrets = [
    part
    for key, value in values.items()
    if value and ("API_KEY" in key or key == "AAA_PASSWORD")
    for part in value.split(",")
    if part
]
for file in files:
    if file.is_file():
        text = file.read_text(encoding="utf-8")
        assert all(secret not in text for secret in secrets), "Configured secret found in artifact"
receipt = {
    "checked_at": datetime.now(UTC).isoformat(),
    "source_packet": "docs/reports/049-belief-v2-review-corpus/review-packet.json",
    "run": str(run.relative_to(ROOT)).replace("\\", "/"),
    "base_packet_sha256": frozen["base_packet_sha256"],
    "frozen_sha256": frozen["frozen_sha256"],
    "artifact_validation": "passed",
    "configured_secret_scan": "passed",
    "documentation_links_checked": links_checked,
    "cases": len(frozen["cases"]),
    "reviewer_slots": len(rows),
    "case_outcomes": frozen["coverage"],
    "reviewer_outcomes": dict(Counter(r["status"] for r in rows)),
    "model_outcomes": dict(Counter(r["model_requested"] + ":" + r["status"] for r in rows)),
    "effective_relations": dict(Counter(r["annotation"]["relation"] for r in rows if r["status"] == "reviewed")),
    "failure_groups": dict(Counter(r.get("reason") or r["status"] for r in rows if r["status"] != "reviewed")),
    "family_outcomes": {key: dict(value) for key, value in families.items()},
    "partition_counts": dict(Counter(c["split"] for c in frozen["cases"])),
    "independent_gold": False,
    "adoption_authority": "none",
    "promotion": "BLOCKED",
    "limits": [
        "Reviewer coverage partial",
        "Legacy author independence unknown",
        "Bounded lexical excerpts",
        "No production belief writes, migrations or deployment",
        "No runtime integration certification",
    ],
}
(report / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "validated_cases": len(frozen["cases"]),
            "coverage": frozen["coverage"],
            "links_checked": links_checked,
            "secret_scan": "passed",
        }
    )
)
