import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

root_path = str(Path(__file__).resolve().parents[2])
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from backend.api.deps import get_note_repo, verify_password  # noqa: E402
from backend.main import app  # noqa: E402
from backend.storage.database import init_db  # noqa: E402
from backend.storage.repositories.conversation.conversation import ConversationRepository  # noqa: E402
from backend.storage.repositories.conversation.message import MessageRepository  # noqa: E402
from backend.storage.repositories.conversation.note import NoteRepository  # noqa: E402


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "notes_test.db"
    init_db(str(db_file))
    return str(db_file)


def _insert_test_msg(msg_repo, conv_id: str, content: str, speaker: str = "apparatus"):
    return msg_repo.insert(
        speaker=speaker,
        content=content,
        embedding=b"",
        embedding_model="test",
        embedding_dim=0,
        conversation_id=conv_id,
    )


def test_create_note_normalizes_message_asset_type(test_db):
    conv_repo = ConversationRepository(test_db)
    msg_repo = MessageRepository(test_db)
    note_repo = NoteRepository(test_db)

    conv = conv_repo.create("conv-1", "symbia", "Test Conversation")
    msg = _insert_test_msg(
        msg_repo,
        conv_id=conv.id,
        content="This is an autopoietic system with cybernetic feedback.",
        speaker="apparatus",
    )

    note = note_repo.create_note(
        id="note-uuid-1",
        asset_type="message",  # frontend sends "message"
        asset_id=str(msg.id),
        conversation_id=conv.id,
        selected_text="cybernetic feedback",
        comment="Crucial concept",
        visibility="personal",
    )

    # Note must be saved as conversation_message
    assert note["asset_type"] == "conversation_message"
    assert note["id"] == "note-uuid-1"

    # Message content in conversation_log must be wrapped in mark
    updated_msg = msg_repo.get_by_id(msg.id)
    assert updated_msg is not None
    assert "<mark" in updated_msg.content
    assert "cybernetic feedback" in updated_msg.content

    # get_notes_by_conversation must return the note on refresh
    notes = note_repo.get_notes_by_conversation(conv.id)
    assert len(notes) == 1
    assert notes[0]["id"] == "note-uuid-1"
    assert notes[0]["comment"] == "Crucial concept"

    # get_notes_by_asset must also work with both "conversation_message" and "message"
    by_cm = note_repo.get_notes_by_asset("conversation_message", str(msg.id))
    assert len(by_cm) == 1
    by_msg = note_repo.get_notes_by_asset("message", str(msg.id))
    assert len(by_msg) == 1


def test_get_notes_by_conversation_legacy_compatibility(test_db):
    note_repo = NoteRepository(test_db)

    # Insert raw legacy note with asset_type='message' via direct sqlite connection
    conn = sqlite3.connect(test_db)
    conn.execute(
        """INSERT INTO notes (id, asset_type, asset_id, conversation_id, selected_text, comment, visibility)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("legacy-note-1", "message", "42", "conv-legacy", "legacy text", "legacy comment", "shared"),
    )
    conn.commit()
    conn.close()

    notes = note_repo.get_notes_by_conversation("conv-legacy")
    assert len(notes) == 1
    assert notes[0]["id"] == "legacy-note-1"
    assert notes[0]["comment"] == "legacy comment"


def test_delete_note_removes_marks(test_db):
    conv_repo = ConversationRepository(test_db)
    msg_repo = MessageRepository(test_db)
    note_repo = NoteRepository(test_db)

    conv = conv_repo.create("conv-del", "symbia", "Delete Test")
    msg = _insert_test_msg(
        msg_repo,
        conv_id=conv.id,
        content="Testing note deletion and mark removal.",
        speaker="human",
    )

    note_repo.create_note(
        id="note-del-1",
        asset_type="conversation_message",
        asset_id=str(msg.id),
        conversation_id=conv.id,
        selected_text="mark removal",
        comment="To be removed",
    )

    msg_with_mark = msg_repo.get_by_id(msg.id)
    assert "<mark" in msg_with_mark.content

    note_repo.delete_note("note-del-1")

    # Mark must be stripped from message content
    msg_after_del = msg_repo.get_by_id(msg.id)
    assert "<mark" not in msg_after_del.content
    assert "mark removal" in msg_after_del.content

    # Notes list must now be empty
    assert len(note_repo.get_notes_by_conversation(conv.id)) == 0


def test_api_note_create_and_fetch_by_conversation(test_db):
    conv_repo = ConversationRepository(test_db)
    msg_repo = MessageRepository(test_db)
    note_repo = NoteRepository(test_db)

    conv = conv_repo.create("conv-api", "symbia", "API Test")
    msg = _insert_test_msg(
        msg_repo,
        conv_id=conv.id,
        content="API test message content.",
        speaker="human",
    )

    app.dependency_overrides[get_note_repo] = lambda: note_repo
    app.dependency_overrides[verify_password] = lambda: None

    client = TestClient(app)
    try:
        # POST /notes with asset_type="message" and conversation_id
        res = client.post(
            "/api/notes",
            json={
                "asset_type": "message",
                "asset_id": str(msg.id),
                "conversation_id": conv.id,
                "selected_text": "test message",
                "comment": "API note comment",
                "visibility": "shared",
            },
        )
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["asset_type"] == "conversation_message"
        assert data["comment"] == "API note comment"

        # GET /notes?conversation_id=...
        get_res = client.get(f"/api/notes?conversation_id={conv.id}")
        assert get_res.status_code == 200
        notes = get_res.json()
        assert len(notes) == 1
        assert notes[0]["id"] == data["id"]
        assert notes[0]["selected_text"] == "test message"

        # GET /conversations/{conversation_id}/notes
        conv_res = client.get(f"/api/conversations/{conv.id}/notes")
        assert conv_res.status_code == 200
        assert len(conv_res.json()) == 1
    finally:
        app.dependency_overrides.clear()
