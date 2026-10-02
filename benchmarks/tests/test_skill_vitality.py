import hashlib
import sqlite3
from datetime import UTC, datetime

import pytest

from benchmarks.suites.skill_vitality import assess_probes, audit, probe_plan


def test_audit_reads_snapshot_without_mutation_or_lifetime_claim(tmp_path):
    db = tmp_path / "snapshot.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            "CREATE TABLE skill_nodes(id,name,lifecycle_stage,always_active,last_used_at,created_at,content); CREATE TABLE skill_versions(skill_id); CREATE TABLE conversation_log(active_skills);"
        )
        conn.execute("INSERT INTO skill_nodes VALUES('s','skill','crystallized',0,NULL,'2026-01-01','boundary')")
        conn.executemany("INSERT INTO conversation_log VALUES(?)", [(' ["skill","skill"] ',), ("invalid",)])
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    result = audit(db, as_of=datetime(2026, 10, 3, tzinfo=UTC))
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before
    assert result["skills"][0]["observed_activations"] == 1
    assert result["invalid_activation_rows"] == 1
    assert result["skills"][0]["dormancy_candidate"]
    plan = probe_plan(result)
    assert all(p["execution"] == "NOT RUN" for p in plan)
    with pytest.raises(ValueError):
        assess_probes(plan, [{"id": plan[0]["id"], "outcome": "PASS"}])
    assessed = assess_probes(plan, [{"id": plan[0]["id"], "outcome": "FAIL", "receipt": "evidence.json"}])
    assert assessed[0]["outcome"] == "FAIL"
    assert assessed[1]["outcome"] == "UNASSESSED"


@pytest.mark.asyncio
async def test_live_probes_keep_failures_and_do_not_claim_forkability(tmp_path):
    from benchmarks.suites.skill_vitality import execute_probes

    db = tmp_path / "probe.db"
    with sqlite3.connect(db) as conn:
        conn.executescript("CREATE TABLE skill_nodes(id,content); INSERT INTO skill_nodes VALUES('s','boundary');")
    plan = [
        {
            "id": "p",
            "skill_id": "s",
            "skill_name": "skill",
            "content_sha256": hashlib.sha256(b"boundary").hexdigest(),
            "challenge": "challenge",
            "outcome": "UNASSESSED",
        }
    ]

    class Provider:
        async def generate(self, messages, **params):
            assert messages[0]["content"] == "boundary"
            assert params["thinking_override"] is False
            raise RuntimeError("unavailable")

    provider = Provider()
    result = await execute_probes(db, plan, provider, {"skill"})
    assert result[0]["execution"] == "FAILED"
    assert result[0]["outcome"] == "UNASSESSED"
