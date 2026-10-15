"""Isolated EmbeddingGemma 2 versus MiniLM text retrieval/storage benchmark.

Each model runs in a separate CPU process and writes vectors only to a fresh
benchmark-local SQLite WAL file. Production embedding configuration is never
read or changed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

import numpy as np
import psutil  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = ROOT / "benchmarks" / "data" / "embedding_mrl_retrieval_v1.json"


class ModelProfile(TypedDict):
    model_id: str
    dimensions: list[int]


MODELS: dict[str, ModelProfile] = {
    "minilm": {"model_id": "sentence-transformers/all-MiniLM-L6-v2", "dimensions": [384]},
    "embeddinggemma2": {"model_id": "google/embeddinggemma-2", "dimensions": [128, 256, 512, 768]},
}
MAX_FIXTURE_BYTES = 1_000_000
_EXPECTED_DATASET_SHA256 = "1414bf0bb9b127fe65e0a2b813ab1d3dd471cd82909873f6e240770f985f3c51"


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_dataset(
    path: Path = DEFAULT_DATASET,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], str]:
    if path.stat().st_size > MAX_FIXTURE_BYTES:
        raise ValueError("retrieval fixture exceeds size limit")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(packet, dict) or packet.get("schema_version") != 1:
        raise ValueError("unsupported retrieval fixture schema")
    documents, queries = packet.get("documents"), packet.get("queries")
    if not isinstance(documents, list) or not isinstance(queries, list) or not 1 <= len(queries) <= 100:
        raise ValueError("fixture must contain documents and 1..100 queries")
    doc_ids: set[str] = set()
    for document in documents:
        if not isinstance(document, dict) or not isinstance(document.get("id"), str):
            raise ValueError("document must have a string ID")
        identifier = document["id"]
        if identifier in doc_ids or len(identifier) > 100:
            raise ValueError("document IDs must be unique and bounded")
        if not all(
            isinstance(document.get(field), str) and len(document[field]) <= 8000 for field in ("title", "text")
        ):
            raise ValueError("document title and text must be bounded strings")
        doc_ids.add(identifier)
    query_ids: set[str] = set()
    for query in queries:
        if not isinstance(query, dict) or not isinstance(query.get("id"), str):
            raise ValueError("query must have a string ID")
        identifier = query["id"]
        relevant = query.get("relevant_ids")
        if identifier in query_ids or len(identifier) > 100 or not isinstance(query.get("text"), str):
            raise ValueError("query IDs and text must be valid")
        if not isinstance(relevant, list) or not relevant or not set(relevant) <= doc_ids:
            raise ValueError("each query needs known relevant document IDs")
        query_ids.add(identifier)
    dataset_sha = canonical_sha256({"documents": documents, "queries": queries})
    if dataset_sha != _EXPECTED_DATASET_SHA256:
        raise ValueError("frozen retrieval fixture checksum mismatch")
    return packet, documents, queries, dataset_sha


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * fraction) - 1)], 3)


def score_retrieval(
    document_vectors: np.ndarray,
    query_vectors: np.ndarray,
    document_ids: list[str],
    queries: list[dict[str, Any]],
    *,
    ks: tuple[int, ...] = (1, 3, 5),
) -> dict[str, Any]:
    if document_vectors.ndim != 2 or query_vectors.ndim != 2 or document_vectors.shape[1] != query_vectors.shape[1]:
        raise ValueError("document and query vectors must be two-dimensional with matching dimensions")
    if len(document_ids) != document_vectors.shape[0] or len(queries) != query_vectors.shape[0]:
        raise ValueError("vector counts must match document and query rows")
    if not np.isfinite(document_vectors).all() or not np.isfinite(query_vectors).all():
        raise ValueError("embedding vectors must be finite")
    scores = query_vectors @ document_vectors.T
    per_query: list[dict[str, Any]] = []
    reciprocal_ranks = []
    recall_hits = dict.fromkeys(ks, 0.0)
    total_relevant = 0
    for row_index, query in enumerate(queries):
        ranked_indices = sorted(range(len(document_ids)), key=lambda i: (-float(scores[row_index, i]), document_ids[i]))
        ranked_ids = [document_ids[i] for i in ranked_indices]
        relevant = set(query["relevant_ids"])
        total_relevant += len(relevant)
        first_rank = next((rank for rank, doc_id in enumerate(ranked_ids, 1) if doc_id in relevant), None)
        reciprocal_ranks.append(1.0 / first_rank if first_rank else 0.0)
        for k in ks:
            recall_hits[k] += len(relevant & set(ranked_ids[:k]))
        per_query.append(
            {
                "query_id": query["id"],
                "first_relevant_rank": first_rank,
                "top_ids": ranked_ids[: max(ks)],
            }
        )
    count = max(total_relevant, 1)
    return {
        **{f"recall_at_{k}": round(recall_hits[k] / count, 4) for k in ks},
        "mrr": round(statistics.mean(reciprocal_ranks), 4) if reciprocal_ranks else None,
        "query_count": len(queries),
        "relevant_document_count": total_relevant,
        "per_query": per_query,
    }


def write_vector_store(path: Path, namespace: str, document_ids: list[str], vectors: np.ndarray) -> dict[str, Any]:
    import sqlite3

    if path.exists():
        raise ValueError("vector store must be a fresh isolated benchmark file")
    if vectors.ndim != 2 or len(document_ids) != vectors.shape[0] or not np.isfinite(vectors).all():
        raise ValueError("invalid vectors for benchmark store")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute(
            "CREATE TABLE embeddings(namespace TEXT NOT NULL, document_id TEXT NOT NULL, dimension INTEGER NOT NULL, vector BLOB NOT NULL, PRIMARY KEY(namespace, document_id))"
        )
        started = time.perf_counter()
        with connection:
            connection.executemany(
                "INSERT INTO embeddings(namespace, document_id, dimension, vector) VALUES (?, ?, ?, ?)",
                [
                    (namespace, identifier, int(vectors.shape[1]), np.asarray(vector, dtype=np.float32).tobytes())
                    for identifier, vector in zip(document_ids, vectors, strict=True)
                ],
            )
        write_ms = round((time.perf_counter() - started) * 1000, 3)
        wal_path = Path(str(path) + "-wal")
        db_before = path.stat().st_size
        wal_before = wal_path.stat().st_size if wal_path.exists() else 0
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        db_after = path.stat().st_size
        wal_after = wal_path.stat().st_size if wal_path.exists() else 0
        return {
            "namespace": namespace,
            "document_count": vectors.shape[0],
            "dimension": vectors.shape[1],
            "raw_vector_bytes": int(vectors.nbytes),
            "sqlite_write_ms": write_ms,
            "database_bytes_before_checkpoint": db_before,
            "wal_bytes_before_checkpoint": wal_before,
            "total_bytes_before_checkpoint": db_before + wal_before,
            "database_bytes_after_checkpoint": db_after,
            "wal_bytes_after_checkpoint": wal_after,
            "total_bytes_after_checkpoint": db_after + wal_after,
            "storage_path": path.name,
        }
    finally:
        connection.close()


def _normalize_rows(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if not np.isfinite(norms).all() or np.any(norms <= 1e-12):
        raise ValueError("truncated embedding has a non-finite or zero norm")
    normalized: np.ndarray = vectors / norms
    return normalized


def _encode(model: Any, model_key: str, texts: list[str], *, is_query: bool, dimension: int) -> np.ndarray:
    common: dict[str, Any] = {
        "normalize_embeddings": True,
        "convert_to_numpy": True,
        "show_progress_bar": False,
        "batch_size": 16,
    }
    if model_key == "embeddinggemma2":
        common["normalize_embeddings"] = False
        common["prompt_name"] = "SearchQuery" if is_query else "Document"
        common["truncate_dim"] = dimension
        vectors = np.asarray(model.encode(texts, **common), dtype=np.float32)
        return _normalize_rows(vectors)
    vectors = model.encode_query(texts, **common) if is_query else model.encode_document(texts, **common)
    vectors = np.asarray(vectors, dtype=np.float32)
    if vectors.shape[1] != dimension:
        raise ValueError("MiniLM output dimension differs from frozen profile")
    return vectors


def _worker(model_key: str, output_dir: Path, fixture_path: Path) -> dict[str, Any]:
    if model_key not in MODELS:
        raise ValueError("unknown model key")
    packet, documents, queries, fixture_sha = load_dataset(fixture_path)
    model_info = MODELS[model_key]
    stage = "model_discovery"
    try:
        import torch
        from huggingface_hub import model_info as get_model_info
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(2)
        process = psutil.Process()
        rss_before_load = process.memory_info().rss
        remote_info = get_model_info(model_info["model_id"])
        revision = str(remote_info.sha)
        kwargs: dict[str, Any] = {"device": "cpu", "revision": revision}
        if model_key == "embeddinggemma2":
            # Official text-only setup omits the optional vision/audio encoders.
            kwargs["config_kwargs"] = {"vision_config": None, "audio_config": None}
        stage = "model_load"
        model = SentenceTransformer(model_info["model_id"], **kwargs)
        rss_after_load = process.memory_info().rss
        if int(model.get_embedding_dimension()) != max(model_info["dimensions"]):
            raise ValueError("loaded model base dimension differs from benchmark profile")
        query_texts = [query["text"] for query in queries]
        document_texts = [f"title: {document['title']} | text: {document['text']}" for document in documents]
        rows = []
        stage = "inference"
        for dimension in model_info["dimensions"]:
            query_started = time.perf_counter()
            query_vectors = _encode(model, model_key, query_texts, is_query=True, dimension=dimension)
            query_latency_ms = round((time.perf_counter() - query_started) * 1000, 3)
            document_started = time.perf_counter()
            document_vectors = _encode(model, model_key, document_texts, is_query=False, dimension=dimension)
            document_latency_ms = round((time.perf_counter() - document_started) * 1000, 3)
            if query_vectors.shape[1] != dimension or document_vectors.shape[1] != dimension:
                raise ValueError("query/document dimension mismatch")
            if not np.allclose(np.linalg.norm(query_vectors, axis=1), 1.0, atol=1e-3):
                raise ValueError("query embeddings are not normalized")
            if not np.allclose(np.linalg.norm(document_vectors, axis=1), 1.0, atol=1e-3):
                raise ValueError("document embeddings are not normalized")
            retrieval = score_retrieval(
                document_vectors,
                query_vectors,
                [document["id"] for document in documents],
                queries,
            )
            namespace = f"{model_key}:{revision[:12]}:{dimension}d:cosine-f32"
            store_path = output_dir / "storage" / f"{model_key}-{dimension}d.sqlite3"
            stage = "storage"
            storage = write_vector_store(
                store_path, namespace, [document["id"] for document in documents], document_vectors
            )
            stage = "inference"
            rows.append(
                {
                    "model_key": model_key,
                    "model_id": model_info["model_id"],
                    "model_revision": revision,
                    "dimension": dimension,
                    "namespace": namespace,
                    "device": "cpu",
                    "dtype": "float32_output",
                    "query_prompt": "SearchQuery" if model_key == "embeddinggemma2" else None,
                    "document_prompt": "Document" if model_key == "embeddinggemma2" else None,
                    "text_only_encoders": ["text"] if model_key == "embeddinggemma2" else None,
                    "query_encode_latency_ms": query_latency_ms,
                    "document_encode_latency_ms": document_latency_ms,
                    "rss_before_model_load_bytes": rss_before_load,
                    "rss_after_model_load_bytes": rss_after_load,
                    "rss_delta_model_load_bytes": max(0, rss_after_load - rss_before_load),
                    "rss_after_encode_bytes": process.memory_info().rss,
                    "fixture_sha256": fixture_sha,
                    "retrieval": retrieval,
                    "storage": storage,
                }
            )
        return {
            "status": "complete",
            "model_key": model_key,
            "model_id": model_info["model_id"],
            "software": {
                package: importlib.metadata.version(package)
                for package in ("sentence-transformers", "transformers", "torch", "numpy")
            },
            "rows": rows,
        }
    except Exception as error:  # noqa: BLE001 - isolate model access/load failures; only the class leaves this process.
        return {
            "status": "failed",
            "model_key": model_key,
            "model_id": model_info["model_id"],
            "failure_stage": stage,
            "failure_class": type(error).__name__[:80],
            "rows": [],
        }


def _write_run(output: Path, packet: dict[str, Any], fixture_sha: str, worker_results: list[dict[str, Any]]) -> None:
    rows = [row for result in worker_results for row in result.get("rows", [])]
    metadata = {
        "schema_version": 1,
        "run_id": output.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset_id": packet["dataset_id"],
        "fixture_sha256": fixture_sha,
        "label_provenance": packet.get("label_provenance"),
        "runtime_embedding_config_changed": False,
        "production_database_touched": False,
        "worker_status": {result["model_key"]: result["status"] for result in worker_results},
        "software": {result["model_key"]: result.get("software") for result in worker_results},
        "records": [
            {
                "model_key": row["model_key"],
                "dimension": row["dimension"],
                "recall_at_1": row["retrieval"]["recall_at_1"],
                "recall_at_3": row["retrieval"]["recall_at_3"],
                "recall_at_5": row["retrieval"]["recall_at_5"],
                "mrr": row["retrieval"]["mrr"],
                "query_encode_latency_ms": row["query_encode_latency_ms"],
                "document_encode_latency_ms": row["document_encode_latency_ms"],
                "rss_delta_model_load_bytes": row["rss_delta_model_load_bytes"],
                "storage": row["storage"],
            }
            for row in rows
        ],
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (output / "telemetry_receipts.json").write_text(json.dumps(worker_results, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# EmbeddingGemma 2 vs MiniLM retrieval and storage",
        "",
        f"Fixture: `{packet['dataset_id']}` (`{fixture_sha}`)",
        f"Labels: {packet.get('label_provenance')}",
        "",
        "| Model | Dim | Recall@1 | Recall@3 | Recall@5 | MRR | Query ms | Document ms | Model RSS delta | Raw vector bytes | SQLite bytes after checkpoint |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        storage = row["storage"]
        lines.append(
            f"| {row['model_key']} | {row['dimension']} | {row['retrieval']['recall_at_1']} | "
            f"{row['retrieval']['recall_at_3']} | {row['retrieval']['recall_at_5']} | {row['retrieval']['mrr']} | "
            f"{row['query_encode_latency_ms']} | {row['document_encode_latency_ms']} | "
            f"{row['rss_delta_model_load_bytes']} | {storage['raw_vector_bytes']} | {storage['total_bytes_after_checkpoint']} |"
        )
    if not rows:
        lines.extend(["| No model completed | — | — | — | — | — | — | — | — | — | — |"])
    lines.extend(
        [
            "",
            "This synthetic corpus is a harness check, not a broad external retrieval benchmark. SQLite files contain only benchmark IDs and vectors in isolated model/dimension namespaces. No production vectors or database are read or migrated.",
            "",
        ]
    )
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    run_log = {
        "run_id": output.name,
        "dataset_sha256": fixture_sha,
        "completed_models": sum(result["status"] == "complete" for result in worker_results),
        "failed_models": sum(result["status"] == "failed" for result in worker_results),
        "completed_model_dimensions": len(rows),
    }
    (output / "run.log").write_text(json.dumps(run_log, sort_keys=True) + "\n", encoding="utf-8")


def run_suite(output: Path, fixture_path: Path = DEFAULT_DATASET) -> dict[str, Any]:
    if output.exists():
        raise ValueError("benchmark output directory must be fresh")
    packet, _, _, fixture_sha = load_dataset(fixture_path)
    output.mkdir(parents=True, exist_ok=False)
    worker_results = []
    for model_key in MODELS:
        command = [
            sys.executable,
            "-m",
            "benchmarks.suites.telemetry.embedding_mrl_retrieval",
            "--worker",
            model_key,
            "--output-dir",
            str(output),
            "--fixture-path",
            str(fixture_path),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=7200, check=False)
        except subprocess.TimeoutExpired:
            worker_results.append(
                {"status": "failed", "model_key": model_key, "failure_class": "TimeoutExpired", "rows": []}
            )
            continue
        receipt_path = output / f"worker-{model_key}.json"
        if completed.returncode != 0 or not receipt_path.exists():
            worker_results.append(
                {"status": "failed", "model_key": model_key, "failure_class": "WorkerExit", "rows": []}
            )
            continue
        worker_results.append(json.loads(receipt_path.read_text(encoding="utf-8")))
    _write_run(output, packet, fixture_sha, worker_results)
    return {"run_dir": str(output.resolve()), "results": worker_results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--worker", choices=tuple(MODELS))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--fixture-path", type=Path, default=DEFAULT_DATASET)
    args = parser.parse_args()
    packet, _, _, fixture_sha = load_dataset(args.fixture_path)
    if args.worker:
        if args.output_dir is None:
            parser.error("worker requires --output-dir")
        result = _worker(args.worker, args.output_dir, args.fixture_path)
        (args.output_dir / f"worker-{args.worker}.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        if result["status"] == "failed":
            raise SystemExit(1)
        return
    if args.validate_only:
        print(json.dumps({"dataset_id": packet["dataset_id"], "fixture_sha256": fixture_sha, "models": MODELS}))
        return
    if args.output is None:
        parser.error("--output is required unless --validate-only is used")
    result = run_suite(args.output, args.fixture_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
