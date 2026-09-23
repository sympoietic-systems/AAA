import json
import sqlite3

import pytest

from backend.storage.migrations import run_all_migrations
from backend.storage.repositories.conversation.message import MessageRepository
from backend.utils.vector import build_history_message


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    run_all_migrations(conn)
    yield conn
    conn.close()


def test_insert_and_retrieve_active_skills_and_beliefs(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    run_all_migrations(conn)
    conn.close()

    repo = MessageRepository(db_path)
    skills = ["skill-creation", "system-design"]
    beliefs = ["glitch-as-voice", "symbiomemetic-partnership"]

    msg = repo.insert(
        speaker="apparatus",
        content="Response text",
        embedding=b"",
        embedding_model="",
        embedding_dim=0,
        conversation_id="conv-1",
        active_skills=skills,
        active_beliefs=beliefs,
    )

    assert msg.id is not None
    assert msg.active_skills == json.dumps(skills)
    assert msg.active_beliefs == json.dumps(beliefs)

    rows = repo.get_recent_with_metrics(limit=5, conversation_id="conv-1")
    assert len(rows) == 1
    row = rows[0]
    assert row["active_skills"] == json.dumps(skills)
    assert row["active_beliefs"] == json.dumps(beliefs)

    hist_msg = build_history_message(row, None)
    assert hist_msg.active_skills == skills
    assert hist_msg.active_beliefs == beliefs


def test_old_messages_without_active_items():
    row = {
        "id": 1,
        "timestamp": "2026-09-18T12:00:00",
        "speaker": "apparatus",
        "content": "Test",
        "context_sent": None,
        "active_skills": None,
        "active_beliefs": None,
    }

    hist_msg = build_history_message(row, None)
    assert hist_msg.active_skills == []
    assert hist_msg.active_beliefs == []
