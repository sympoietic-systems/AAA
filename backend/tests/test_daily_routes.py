from datetime import datetime
from fastapi.testclient import TestClient
from backend.main import app
from backend.storage.database import get_connection, get_db_path


def test_daily_endpoints():
    client = TestClient(app)

    from backend.storage.database import init_db, get_db_path
    from backend.bootstrap.repositories import _init_repos

    db_path = get_db_path("data/aaa_test.db")
    conn = init_db(str(db_path))

    repos = _init_repos({"database": {"path": str(db_path)}})
    for k, v in repos.items():
        setattr(app.state, k, v)




    # Insert test conversation and message
    conn.execute("INSERT OR IGNORE INTO conversations (id, title, agent_id) VALUES (?, ?, ?)", ("test-conv-1", "Test Conv", "symbia"))
    conn.execute(
        "INSERT INTO conversation_log (timestamp, agent_id, conversation_id, speaker, content, embedding, embedding_model, embedding_dim) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ("2026-07-23 10:00:00", "symbia", "test-conv-1", "user", "Hello daily test", b"", "test", 0)
    )


    # Insert test consolidation checkpoint and memory node
    conn.execute(
        "INSERT OR IGNORE INTO consolidation_checkpoints (id, conversation_id, message_count, summary, created_at) VALUES (?, ?, ?, ?, ?)",
        (1, "test-conv-1", 1, "test summary", "2026-07-23 10:05:00")
    )

    conn.execute(
        "INSERT OR IGNORE INTO memory_nodes (id, conversation_id, checkpoint_id, node_type, intensity, intra_active_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("mn-test-1", "test-conv-1", 1, "concept", 0.8, "Test memory node text", "2026-07-23 10:05:00")
    )


    # Insert test belief node and belief event
    conn.execute(
        "INSERT OR IGNORE INTO belief_nodes (id, agent_id, label, statement, origin, confidence, ontological_mass, vector_16d, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("b-1", "symbia", "test belief", "statement", "emergent", 0.9, 1.0, "[]", "2026-07-23 10:10:00", "2026-07-23 10:10:00")
    )

    conn.execute(
        "INSERT OR IGNORE INTO belief_events (id, timestamp, belief_id, source_type, event_type, impact_score, rationale) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("be-test-1", "2026-07-23 10:10:00", "b-1", "user", "crystallization", 0.9, "Test belief rationale")
    )



    conn.commit()
    conn.close()

    # 2. Test GET /api/agent/daily/index
    res_index = client.get("/api/agent/daily/index")
    assert res_index.status_code == 200
    data_index = res_index.json()
    assert "dates" in data_index
    dates = [d["date"] for d in data_index["dates"]]
    assert "2026-07-23" in dates

    # 3. Test GET /api/agent/daily/2026-07-23
    res_detail = client.get("/api/agent/daily/2026-07-23")
    assert res_detail.status_code == 200
    data_detail = res_detail.json()
    assert data_detail["date"] == "2026-07-23"
    assert data_detail["metrics"]["memory_node_count"] >= 1
    assert len(data_detail["memory_nodes"]) >= 1
    assert data_detail["memory_nodes"][0]["intra_active_text"] == "Test memory node text"

    # 4. Test POST /api/agent/daily/2026-07-23/summarize
    res_sum = client.post("/api/agent/daily/2026-07-23/summarize")
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert data_sum["date"] == "2026-07-23"
    assert len(data_sum["summary"]) > 0

    # 5. Verify cached summary on subsequent detail fetch
    res_detail_cached = client.get("/api/agent/daily/2026-07-23")
    assert res_detail_cached.status_code == 200
    assert res_detail_cached.json()["summary"] == data_sum["summary"]
