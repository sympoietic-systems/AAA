import os
import sqlite3
from unittest.mock import AsyncMock

import numpy as np
from fastapi.testclient import TestClient

from backend.storage.database import get_db_path, init_db
from backend.storage.repositories.memory_node import MemoryNodeRepository
from backend.storage.repositories.message import MessageRepository
from backend.storage.repositories.note import NoteRepository


def test_search_endpoint(client: TestClient):
    # Set up auth header if password exists
    password = os.environ.get("AAA_PASSWORD", "").strip()
    if password:
        client.headers.update({"Authorization": f"Bearer {password}"})

    # Setup database file and run migrations if needed
    db_path = get_db_path("data/aaa_test.db")
    init_db(db_path)

    # Clear old entries via direct sqlite connection (bypasses with_connection context)
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM notes")
    conn.execute("DELETE FROM memory_nodes")
    conn.execute("DELETE FROM consolidation_checkpoints")
    conn.execute("DELETE FROM conversation_metrics")
    conn.execute("DELETE FROM conversation_log")
    conn.execute("DELETE FROM conversations")

    # Insert required foreign key records first
    conn.execute(
        "INSERT INTO conversations (id, agent_id, title) VALUES ('conv-1', 'antigravity', 'Test Conversation')"
    )
    conn.execute(
        "INSERT INTO consolidation_checkpoints (id, conversation_id, message_count, summary) VALUES (1, 'conv-1', 0, 'Test Summary')"
    )
    conn.commit()
    conn.close()

    # Instantiate repositories
    message_repo = MessageRepository(db_path)
    note_repo = NoteRepository(db_path)
    memory_node_repo = MemoryNodeRepository(db_path)

    # Initialize app state repositories
    client.app.state.message_repo = message_repo
    client.app.state.note_repo = note_repo
    client.app.state.memory_node_repo = memory_node_repo

    # Set up mocks for embedder and structural scorer
    # embedder is EmbedderModule: route uses embedder.service.encode_async()
    embedder = AsyncMock()
    mock_emb = np.zeros(384, dtype=np.float32)
    mock_emb[0] = 1.0
    embedder.service = AsyncMock()
    embedder.service.encode_async = AsyncMock(return_value=mock_emb)
    client.app.state.embedder = embedder

    # structural_scorer is StructuralScorerModule: route uses structural_scorer._scorer.score_async()
    structural_scorer = AsyncMock()
    mock_sig = np.zeros(16, dtype=np.float32)
    mock_sig[0] = 1.0
    structural_scorer._scorer = AsyncMock()
    structural_scorer._scorer.score_async = AsyncMock(return_value=mock_sig)
    client.app.state.structural_scorer = structural_scorer

    emb_bytes = mock_emb.tobytes()
    sig_bytes = mock_sig.tobytes()

    # 1. Insert dummy message
    msg = message_repo.insert(
        speaker="human",
        content="This is a test message talking about rhizomes and autopoiesis.",
        embedding=emb_bytes,
        embedding_model="all-MiniLM-L6-v2",
        embedding_dim=384,
        conversation_id="conv-1",
        structural_signature=sig_bytes,
    )

    # 2. Insert dummy note
    note_repo.create_note(
        id="note-1",
        asset_type="conversation_message",
        asset_id=str(msg.id),
        conversation_id="conv-1",
        selected_text="rhizomes",
        comment="This note highlights the rhizomatic connection.",
        visibility="shared",
    )

    # 3. Insert dummy memory node
    memory_node_repo.save_nodes(
        conversation_id="conv-1",
        checkpoint_id=1,
        nodes=[
            {
                "id": "mem-1",
                "type": "concept",
                "scar": "autopoiesis-scar",
                "intra_active_text": "An autopoietic membrane of cognitive resonance.",
                "intensity": 0.9,
                "glitch_potential": 0.8,
            }
        ],
    )

    # 4. Insert glitch metrics
    conn_insert = sqlite3.connect(db_path)
    conn_insert.execute(
        """INSERT INTO conversation_metrics
           (message_id, s_t, novelty, deficit, surprise_index)
           VALUES (?, ?, ?, ?, ?)""",
        (msg.id, 0.0, 0.8, 0.7, 0.9),
    )
    conn_insert.commit()
    conn_insert.close()

    # --- Test Baseline Text Keyword Mode ---
    response = client.get("/api/search?q=rhizome")
    if response.status_code != 200:
        print("FAIL BODY:", response.text)
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 2  # Match message and note

    types = [r["type"] for r in results]
    assert "message" in types
    assert "note" in types

    # Test conversation scope filtering
    response = client.get("/api/search?q=rhizome&conversation_id=conv-2")
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 0  # No matches in conv-2

    # --- Test Semantic Mode ---
    response = client.get("/api/search?q=rhizome&mode=semantic")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["type"] == "message"

    # --- Test Diffractive Mode ---
    response = client.get("/api/search?q=autopoiesis&mode=diffractive")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["type"] == "message"

    # --- Test Glitch Salience Mode ---
    response = client.get("/api/search?mode=glitch")
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert results[0]["type"] == "message"
    assert results[0]["relevance_score"] >= 0.7  # Max metric score (surprise=0.9, novelty=0.8, deficit=0.7)
