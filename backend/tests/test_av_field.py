import sqlite3

import numpy as np
from fastapi.testclient import TestClient

from backend.storage.database import get_db_path, init_db
from backend.storage.repositories.message import MessageRepository


def _fresh_repo() -> MessageRepository:
    db_path = get_db_path("data/aaa_test.db")
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM conversation_log")
    conn.execute("DELETE FROM conversations")
    conn.execute("INSERT INTO conversations (id, agent_id, title) VALUES ('conv-av', 'antigravity', 'AV')")
    conn.commit()
    conn.close()
    return MessageRepository(db_path)


def test_av_field_empty_safe(client: TestClient):
    # V14: empty corpus never 500s; covariance is 16x16, nodes empty.
    client.app.state.message_repo = _fresh_repo()
    r = client.get("/api/av/field")
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"] == []
    assert len(body["dims"]) == 16
    assert len(body["covariance"]) == 16 and len(body["covariance"][0]) == 16


def test_av_field_returns_vec16_and_covariance(client: TestClient):
    repo = _fresh_repo()
    for i in range(3):
        vec = np.arange(16, dtype=np.float32) + i
        repo.insert(
            agent_id="antigravity",
            speaker="apparatus",
            content=f"m{i}",
            embedding=b"",
            embedding_model="",
            embedding_dim=0,
            conversation_id="conv-av",
            structural_signature=vec.tobytes(),
        )
    client.app.state.message_repo = repo
    body = client.get("/api/av/field").json()
    assert len(body["nodes"]) == 3
    assert all(len(n["vec16"]) == 16 for n in body["nodes"])
    assert len(body["covariance"]) == 16


def test_av_field_resonance_links(client: TestClient):
    # Two near-identical signatures resonate (cosine ≥ threshold); one orthogonal does not.
    repo = _fresh_repo()
    base = np.ones(16, dtype=np.float32)
    sigs = [base, base * 1.01, np.eye(16, dtype=np.float32)[0]]  # 0≈1 resonant, 2 orthogonal
    for i, vec in enumerate(sigs):
        repo.insert(
            agent_id="antigravity",
            speaker="apparatus",
            content=f"r{i}",
            embedding=b"",
            embedding_model="",
            embedding_dim=0,
            conversation_id="conv-av",
            structural_signature=vec.tobytes(),
        )
    client.app.state.message_repo = repo
    links = client.get("/api/av/field").json()["links"]
    assert len(links) == 1
    assert links[0]["weight"] >= 0.92
    assert {links[0]["a"], links[0]["b"]}.isdisjoint({})  # ids present
    assert links[0]["a"] != links[0]["b"]  # no self-links


def test_av_breath_shape(client: TestClient):
    b = client.get("/api/av/breath").json()
    assert b["kind"] in ("exhale", "inhale", "silence")
    assert 0.0 <= b["phase"] <= 1.0
    assert isinstance(b["seed"], int)


def test_av_cut_ages_and_stays_bounded(client, tmp_path, monkeypatch):
    from backend.api.routes import av

    monkeypatch.setattr(av, "_HYSTERESIS_PATH", tmp_path / "h.json")

    # V17: many cuts never saturate 0/1.
    last = None
    for _ in range(200):
        last = client.post("/api/av/cut", json={"axisA": 3, "axisB": 9, "source": "human"}).json()
    for v in last["params"].values():
        assert 0.0 < v < 1.0
    assert len(last["hash"]) == 12

    # V15: next field load reflects the accumulated params.
    client.app.state.message_repo = _fresh_repo()
    field = client.get("/api/av/field").json()
    assert field["params"] == last["params"]

    # V16: no history/replay/undo endpoint exists.
    assert client.get("/api/av/history").status_code == 404


def test_av_cut_source_shape(client, tmp_path, monkeypatch):
    from backend.api.routes import av

    # V18: human concentrates delta on few knobs, breath spreads across all.
    monkeypatch.setattr(av, "_HYSTERESIS_PATH", tmp_path / "human.json")
    h = client.post("/api/av/cut", json={"axisA": 1, "axisB": 2, "source": "human"}).json()
    moved_h = sum(1 for v in h["params"].values() if abs(v - 0.5) > 1e-6)

    monkeypatch.setattr(av, "_HYSTERESIS_PATH", tmp_path / "breath.json")
    b = client.post("/api/av/cut", json={"axisA": 1, "axisB": 2, "source": "breath"}).json()
    moved_b = sum(1 for v in b["params"].values() if abs(v - 0.5) > 1e-6)

    assert moved_h < moved_b
