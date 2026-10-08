"""Reproduce this report's descriptive counts from the saved API projections.

Run: python docs/reports/045-belief-month-review/analyze.py
Naive production timestamps are interpreted as UTC; events are API-capped.
Uses only the Python standard library. Does not contact production.
"""

import collections
import datetime as dt
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def timestamp(value):
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=dt.timezone.utc) if result.tzinfo is None else result


def counter(rows, key):
    return dict(collections.Counter(row.get(key) for row in rows))


def chart(counts, name, title):
    items = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    height = 100 + len(items) * 38
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img" aria-label="{html.escape(title)}">',
             '<rect width="100%" height="100%" fill="#000"/>',
             f'<text x="25" y="35" fill="white" font-family="monospace" font-size="20">{html.escape(title)}</text>']
    maximum = max(counts.values())
    for i, (label, value) in enumerate(items):
        y = 70 + i * 38
        width = 540 * value / maximum
        parts.extend([f'<text x="25" y="{y + 18}" fill="white" font-family="monospace" font-size="15">{html.escape(label)}</text>',
                      f'<rect x="260" y="{y}" width="{width}" height="24" fill="white"/>',
                      f'<text x="{275 + width:.1f}" y="{y + 18}" fill="white" font-family="monospace" font-size="15">{value:,}</text>'])
    parts.append('</svg>')
    (ROOT / "assets" / name).write_text("\n".join(parts), encoding="utf-8")


def main():
    metadata = read("collection-metadata.json")
    beliefs = read("production-beliefs-snapshot.json")
    proposals = read("production-proposals-snapshot.json")
    events = read("production-belief-events-30d.json")
    start = timestamp(metadata["interval_start_inclusive_utc"])
    end = timestamp(metadata["interval_end_inclusive_utc"])
    assert all(start <= timestamp(row["timestamp"]) <= end for row in events)
    assert len({row["id"] for row in events}) == len(events)
    incubating = [row for row in proposals if row["proposal_status"] in ("pending", "refined")]
    recent_updated = [row for row in proposals if start <= timestamp(row["updated_at"]) <= end]
    visible = beliefs["beliefs"]
    nonatrophy = [row for row in events if row["event_type"] != "atrophy"]
    per_belief = counter(events, "belief_id")
    daily = dict(sorted(collections.Counter(row["timestamp"][:10] for row in events).items()))
    summary = {
        "interval": [start.isoformat(), end.isoformat()],
        "timestamp_assumption": "Naive API timestamps interpreted as UTC",
        "visible_beliefs": len(visible), "lifecycle_stages": counter(visible, "lifecycle_stage"),
        "confidence_values": sorted(set(row["confidence"] for row in visible)),
        "mass_range": [min(row["ontological_mass"] for row in visible), max(row["ontological_mass"] for row in visible)],
        "crystallized_below_local_turn_floor": sum(row["ontological_mass"] < 0.55 for row in visible),
        "proposals_all_time": len(proposals), "proposal_statuses_all_time": counter(proposals, "proposal_status"),
        "proposals_updated_in_interval": len(recent_updated),
        "updated_proposal_statuses": counter(recent_updated, "proposal_status"),
        "incubating": len(incubating),
        "incubating_with_merge_target": sum(bool(row.get("potential_merge_target")) for row in incubating),
        "incubating_merge_target_counts": counter(incubating, "potential_merge_target"),
        "returned_events": len(events), "event_types": counter(events, "event_type"),
        "source_types": counter(events, "source_type"),
        "non_atrophy_events": len(nonatrophy), "non_atrophy_source_types": counter(nonatrophy, "source_type"),
        "atrophy_fraction_of_returned": 1 - len(nonatrophy) / len(events),
        "beliefs_at_100_event_cap": sum(value == 100 for value in per_belief.values()),
        "returned_event_time_range": [min(row["timestamp"] for row in events), max(row["timestamp"] for row in events)],
        "daily_returned_events": daily,
        "support_with_negative_generic_impact": sum(row["delta_confidence"] < 0 for row in events if row["event_type"] == "support"),
        "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob("*.json"))},
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (ROOT / "assets").mkdir(exist_ok=True)
    chart(summary["non_atrophy_source_types"], "non-atrophy-sources.svg", "Returned non-atrophy events by source (capped sample)")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("sha256", "daily_returned_events")}, indent=2))


if __name__ == "__main__":
    main()
