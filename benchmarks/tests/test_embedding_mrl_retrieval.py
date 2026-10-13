from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from benchmarks.suites.telemetry import embedding_mrl_retrieval as benchmark


def test_t90_fixture_is_frozen_and_has_retrieval_labels() -> None:
    packet, documents, queries, digest = benchmark.load_dataset()
    assert len(documents) == 30
    assert len(queries) == 10
    assert digest == "1414bf0bb9b127fe65e0a2b813ab1d3dd471cd82909873f6e240770f985f3c51"
    assert packet["label_provenance"].startswith("hand-authored synthetic")
    assert all(set(query["relevant_ids"]) <= {document["id"] for document in documents} for query in queries)


def test_t90_fixture_rejects_duplicate_document_ids_before_checksum(tmp_path: Path) -> None:
    packet, documents, queries, _ = benchmark.load_dataset()
    broken = {**packet, "documents": [*documents, documents[0]]}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(broken), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        benchmark.load_dataset(path)


def test_t90_retrieval_metrics_are_deterministic_with_id_ties() -> None:
    documents = np.asarray([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    queries = np.asarray([[1.0, 0.0]], dtype=np.float32)
    scored = benchmark.score_retrieval(
        documents,
        queries,
        ["d02", "d01", "d03"],
        [{"id": "q1", "relevant_ids": ["d01"]}],
    )
    assert scored["recall_at_1"] == 1.0
    assert scored["recall_at_3"] == 1.0
    assert scored["mrr"] == 1.0
    assert scored["per_query"][0]["top_ids"] == ["d01", "d02", "d03"]


def test_t90_v142_mrl_vector_is_normalized_after_truncation() -> None:
    vectors = np.asarray([[0.6, 0.8], [3.0, 4.0]], dtype=np.float32)
    normalized = benchmark._normalize_rows(vectors)
    assert np.allclose(np.linalg.norm(normalized, axis=1), 1.0, atol=1e-6)
    with pytest.raises(ValueError, match="zero norm"):
        benchmark._normalize_rows(np.asarray([[0.0, 0.0]], dtype=np.float32))


def test_t90_sqlite_store_keeps_only_ids_and_vectors_in_namespace(tmp_path: Path) -> None:
    path = tmp_path / "isolated.sqlite3"
    vectors = np.asarray([[0.6, 0.8], [1.0, 0.0]], dtype=np.float32)
    result = benchmark.write_vector_store(path, "gemma:r1:2d:cosine-f32", ["a", "b"], vectors)
    assert result["raw_vector_bytes"] == vectors.size * 4
    assert result["dimension"] == 2
    assert result["total_bytes_after_checkpoint"] >= result["raw_vector_bytes"]
    with sqlite3.connect(path) as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(embeddings)")]
        rows = connection.execute(
            "SELECT namespace, document_id, dimension, vector FROM embeddings ORDER BY document_id"
        ).fetchall()
    assert columns == ["namespace", "document_id", "dimension", "vector"]
    assert all(row[0] == "gemma:r1:2d:cosine-f32" and row[2] == 2 for row in rows)
    stored = {row[1]: np.frombuffer(row[3], dtype=np.float32).tolist() for row in rows}
    assert stored == {"a": vectors[0].tolist(), "b": vectors[1].tolist()}
    with pytest.raises(ValueError, match="fresh"):
        benchmark.write_vector_store(path, "other", ["a", "b"], vectors)
