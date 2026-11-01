import asyncio
import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.deps import get_message_repo
from backend.api.router import router as api_router
from backend.services.release_readiness import _REQUIRED_MIGRATIONS, build_release_readiness
from backend.storage.activation import ActivationTrace
from benchmarks.suites.release_readiness_preflight import fetch_preflight, validate_base_url


def make_database(path: Path, now: datetime) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE _migrations (name TEXT PRIMARY KEY)")
    conn.executemany("INSERT INTO _migrations(name) VALUES (?)", [(name,) for name in _REQUIRED_MIGRATIONS])
    conn.execute(
        """CREATE TABLE conversation_log (
            id INTEGER PRIMARY KEY, speaker TEXT NOT NULL, timestamp TEXT NOT NULL,
            activation_provenance TEXT, generation_receipt TEXT,
            quality_status TEXT NOT NULL, quality_receipt TEXT
        )"""
    )
    trace = ActivationTrace(coverage="complete", prompt_sha256="0" * 64, entries=[]).model_dump_json()
    conn.execute(
        """INSERT INTO conversation_log VALUES (1, 'apparatus', ?, ?, ?, 'sound', ?)""",
        ((now - timedelta(days=1)).isoformat(), trace, '{"finish_reason":"stop"}', '{"status":"sound"}'),
    )
    conn.execute(
        """INSERT INTO conversation_log VALUES (2, 'apparatus', ?, NULL, NULL, 'unassessed', NULL)""",
        ((now - timedelta(days=2)).isoformat(),),
    )
    conn.execute(
        """INSERT INTO conversation_log VALUES (3, 'apparatus', ?, NULL, NULL, 'degraded', NULL)""",
        ((now - timedelta(days=60)).isoformat(),),
    )
    conn.commit()
    conn.close()


def test_v140_preflight_is_read_only_and_counts_only_recent_receipts(tmp_path, monkeypatch):
    database = tmp_path / "runtime.db"
    now = datetime(2026, 10, 13, tzinfo=UTC)
    make_database(database, now)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    monkeypatch.setenv("AAA_BUILD_REVISION", "abcdef123456")
    config = {"belief_review": {"assessment": {"enabled": False}}}

    receipt = build_release_readiness(config, str(database), 30, now=now)

    assert receipt["read_only"] is True
    assert receipt["build_revision"] == "abcdef123456"
    assert receipt["effective_flags"]["belief_assessment_enabled"] is False
    assert receipt["recent_assistant_rows"] == 2
    assert receipt["activation_provenance"]["counts"] == {"complete": 1, "unknown": 1}
    assert receipt["generation_receipts"] == {"available": True, "present": 1, "missing": 1}
    assert receipt["response_quality"]["status_counts"] == {"sound": 1, "unassessed": 1}
    assert receipt["response_quality"]["receipt_present"] == 1
    assert receipt["missing_migrations"] == []
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_v140_unknown_revision_and_missing_schema_remain_explicit(tmp_path, monkeypatch):
    database = tmp_path / "old.db"
    conn = sqlite3.connect(database)
    conn.execute("CREATE TABLE conversation_log (id INTEGER PRIMARY KEY, speaker TEXT, timestamp TEXT)")
    conn.execute("INSERT INTO conversation_log VALUES (1, 'apparatus', '2026-10-12T00:00:00+00:00')")
    conn.commit()
    conn.close()
    monkeypatch.delenv("AAA_BUILD_REVISION", raising=False)

    receipt = build_release_readiness({}, str(database), 30, now=datetime(2026, 10, 13, tzinfo=UTC))

    assert receipt["build_revision"] is None
    assert receipt["config_flags_sha256"]
    assert receipt["migration_table_available"] is False
    assert receipt["applied_migrations"] is None
    assert receipt["missing_migrations"] is None
    assert receipt["activation_provenance"]["available"] is False
    assert receipt["activation_provenance"]["counts"] is None
    assert receipt["response_quality"]["receipt_present"] is None


def test_v140_release_readiness_endpoint_requires_global_auth_and_returns_receipt(tmp_path, monkeypatch):
    database = tmp_path / "api.db"
    now = datetime.now(UTC)
    make_database(database, now)
    repo = MagicMock()
    repo.db_path = str(database)
    monkeypatch.setenv("AAA_PASSWORD", "release-secret")
    app = FastAPI()
    app.include_router(api_router)
    app.state.config = {"research_triage": {"enabled": False}}
    app.dependency_overrides[get_message_repo] = lambda: repo

    with TestClient(app) as client:
        denied = client.get("/api/release-readiness")
        accepted = client.get("/api/release-readiness", headers={"Authorization": "Bearer release-secret"})

    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["read_only"] is True
    assert accepted.json()["effective_flags"]["research_triage_enabled"] is False


def test_v140_preflight_command_validates_target_and_fetches_bounded_window():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/release-readiness"
        assert request.url.params["days"] == "14"
        return httpx.Response(200, json={"read_only": True, "build_revision": None})

    async def exercise() -> dict:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_preflight(client, "https://aaa.example/api", 14)

    assert validate_base_url("https://aaa.example/api") == "https://aaa.example/api"
    with pytest.raises(ValueError, match="credentials"):
        validate_base_url("https://user:secret@aaa.example/api")
    assert asyncio.run(exercise()) == {"read_only": True, "build_revision": None}
