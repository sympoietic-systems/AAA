import json
from datetime import UTC, datetime, timedelta

import pytest

from backend.modules.response_quality import SAMPLE_VERSION
from scripts.backfill_response_quality import (
    load_checkpoint,
    new_checkpoint,
    receipt_is_current,
    source_identity,
    summarize,
)


def test_v139_checkpoint_freezes_time_window_and_source_identity(tmp_path):
    output = tmp_path / "audit.json"
    now = datetime(2026, 10, 13, 12, tzinfo=UTC)
    first = new_checkpoint(14, "https://aaa.example/api", now)
    output.write_text(json.dumps(first), encoding="utf-8")

    resumed = load_checkpoint(output, 14, "https://aaa.example/api", now + timedelta(days=3))

    assert resumed["window"] == first["window"]
    assert resumed["window"]["start"] == "2026-09-29T12:00:00+00:00"
    assert resumed["window"]["end"] == "2026-10-13T12:00:00+00:00"


def test_v139_legacy_or_mismatched_checkpoint_is_rejected(tmp_path):
    output = tmp_path / "audit.json"
    output.write_text(json.dumps({"records": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match="new output path"):
        load_checkpoint(output, 14, "https://aaa.example/api", datetime.now(UTC))

    output.write_text(json.dumps(new_checkpoint(14, "https://aaa.example/api", datetime.now(UTC))), encoding="utf-8")
    with pytest.raises(ValueError, match="original arguments"):
        load_checkpoint(output, 7, "https://aaa.example/api", datetime.now(UTC))


def test_v139_summary_counts_only_current_snapshot_and_mode():
    records = {
        "1": {"status": "degraded", "mode": "audit"},
        "2": {"status": "sound", "mode": "apply"},
        "3": {"status": "unavailable", "mode": "audit"},
        "99": {"status": "sound", "mode": "audit"},
    }

    assert summarize(records, [1, 2, 3], "audit") == {"degraded": 1, "unavailable": 1, "not_attempted": 1}
    assert summarize(records, [1, 2, 3], "apply") == {"sound": 1, "not_attempted": 2}


def test_v139_failed_or_stale_receipts_are_retryable():
    good = {
        "status": "sound",
        "mode": "audit",
        "content_hash": "abc",
        "sample_version": SAMPLE_VERSION,
    }
    failed = {**good, "status": "unavailable"}
    changed = {**good, "content_hash": "different"}

    assert receipt_is_current(good, "audit", "abc")
    assert not receipt_is_current(failed, "audit", "abc")
    assert not receipt_is_current(changed, "audit", "abc")


def test_v139_source_identity_drops_credentials_and_query():
    assert source_identity("https://person:secret@AAA.example:8443/api?token=hidden") == "https://aaa.example:8443/api"
