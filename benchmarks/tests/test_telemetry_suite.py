"""
Unit tests for the Cybernetic Telemetry Benchmark Suite.
"""

import json
from pathlib import Path
import tempfile
import numpy as np
import pytest

from benchmarks.common.loader import DialogueDataset, load_dataset, resolve_embeddings
from benchmarks.suites.telemetry.evaluator import evaluate_sequence, compute_statistics
from benchmarks.suites.telemetry.comparator import compare_runs
from benchmarks.suites.telemetry.runner import TelemetryBenchmarkSuite


@pytest.fixture
def mock_linear_dialogue():
    return [
        {"id": 1, "speaker": "human", "content": "How does cybernetic homeostasis work?", "parent_message_id": None},
        {"id": 2, "speaker": "apparatus", "content": "Homeostasis maintains internal invariants against perturbation.", "parent_message_id": 1},
        {"id": 3, "speaker": "human", "content": "What about Gordon Pask's conversation theory?", "parent_message_id": 2},
        {"id": 4, "speaker": "apparatus", "content": "Pask models learning as conversational coupling and conceptual closure.", "parent_message_id": 3},
        {"id": 5, "speaker": "human", "content": "Can you explain mutual perturbation index?", "parent_message_id": 4},
        {"id": 6, "speaker": "apparatus", "content": "MPI is the geometric mean of forward and reverse perturbations.", "parent_message_id": 5},
    ]


@pytest.fixture
def mock_branched_dialogue():
    return [
        {"id": 1, "speaker": "human", "content": "Root concept", "parent_message_id": None},
        {"id": 2, "speaker": "apparatus", "content": "Root answer", "parent_message_id": 1},
        {"id": 3, "speaker": "human", "content": "Branch A query", "parent_message_id": 2},
        {"id": 4, "speaker": "apparatus", "content": "Branch A answer", "parent_message_id": 3},
        {"id": 5, "speaker": "human", "content": "Branch B query", "parent_message_id": 2},
        {"id": 6, "speaker": "apparatus", "content": "Branch B answer", "parent_message_id": 5},
        {"id": 7, "speaker": "human", "content": "Branch B extension", "parent_message_id": 6},
    ]


def test_loader_linear(mock_linear_dialogue):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump({"messages": mock_linear_dialogue}, tf)
        tmp_path = tf.name

    try:
        ds = load_dataset(Path(tmp_path))
        assert len(ds.messages) == 6
        assert not ds.is_branched
        assert ds.messages[0].speaker == "human"
        assert ds.messages[1].speaker == "apparatus"
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_loader_branched(mock_branched_dialogue):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        json.dump({"messages": mock_branched_dialogue}, tf)
        tmp_path = tf.name

    try:
        # Trace to node 4 (Branch A leaf)
        ds_a = load_dataset(Path(tmp_path), target_node=4)
        assert ds_a.is_branched
        assert ds_a.selected_node == 4
        assert [m.id for m in ds_a.messages] == [1, 2, 3, 4]

        # Trace to longest branch (Branch B leaf 7)
        ds_b = load_dataset(Path(tmp_path), longest_path=True)
        assert ds_b.selected_node == 7
        assert [m.id for m in ds_b.messages] == [1, 2, 5, 6, 7]
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_evaluator_metrics(mock_linear_dialogue):
    np.random.seed(42)
    embeddings = np.random.randn(len(mock_linear_dialogue), 384).astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms

    results = evaluate_sequence(mock_linear_dialogue, embeddings)
    assert len(results) == len(mock_linear_dialogue)

    for r in results:
        m = r["metrics"]
        assert "pairwise_similarity" in m
        assert "conceptual_novelty" in m
        assert "paskian_health" in m
        assert "homeostatic_state" in m
        if m["paskian_health"] is not None:
            assert 0.0 <= m["paskian_health"] <= 1.0

    stats = compute_statistics(results)
    assert stats["regimes"]["flowing"] + stats["regimes"]["stagnant"] + stats["regimes"]["disrupted"] == len(results)


def test_comparator_detects_changed_metrics(mock_linear_dialogue):
    np.random.seed(42)
    emb_a = np.random.randn(6, 384).astype(np.float32)
    emb_a /= np.linalg.norm(emb_a, axis=1, keepdims=True)

    emb_b = emb_a.copy()
    emb_b += np.linspace(0.1, 0.9, 6)[:, None]
    emb_b /= np.linalg.norm(emb_b, axis=1, keepdims=True)

    results_a = evaluate_sequence(mock_linear_dialogue, emb_a)
    results_b = evaluate_sequence(mock_linear_dialogue, emb_b)

    comp = compare_runs(results_a, results_b, delta_threshold=0.03)
    assert "all_deltas" in comp
    assert len(comp["all_deltas"]) > 0

    deltas = comp["all_deltas"]
    for i in range(len(deltas) - 1):
        assert deltas[i].abs_delta >= deltas[i + 1].abs_delta


def test_visualizer_and_runner(tmp_path, mock_linear_dialogue):
    ds_file = tmp_path / "test_dialogue.json"
    with open(ds_file, "w", encoding="utf-8") as f:
        json.dump({"messages": mock_linear_dialogue}, f)

    eval_out = tmp_path / "eval_run"
    res = TelemetryBenchmarkSuite.evaluate(ds_file, name="unit_test", out_dir=eval_out)

    assert (eval_out / "metadata.json").exists()
    assert (eval_out / "run.log").exists()
    assert (eval_out / "telemetry_receipts.json").exists()
    assert (eval_out / "summary.md").exists()
    assert (eval_out / "telemetry_oscilloscope.png").exists()
    assert (eval_out / "telemetry_audit_dashboard.png").exists() or (eval_out / "telemetry_audit_dashboard.html").exists()

    comp_out = tmp_path / "comp_run"
    comp_res = TelemetryBenchmarkSuite.compare(eval_out, eval_out, name="self_diff", out_dir=comp_out)

    assert (comp_out / "metadata.json").exists()
    assert (comp_out / "run.log").exists()
    assert (comp_out / "comparison_summary.md").exists()
    assert (comp_out / "differential_changes.png").exists() or (comp_out / "differential_changes.html").exists()
