import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from benchmarks.suites.research_parser import compare, run_worker, verify_source


def source_document(tmp_path):
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.4 frozen fixture")
    return {"source_path": str(path), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_changed_source_rejected_before_worker(tmp_path):
    document = source_document(tmp_path)
    path = tmp_path / "source.pdf"
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        verify_source(document)


def test_successful_extraction_cannot_promote_without_review(tmp_path):
    document = source_document(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": [document]}))
    with patch("benchmarks.suites.research_parser.run_worker", return_value={"status": "complete"}) as worker:
        result = compare(manifest, tmp_path / "run", sys.executable)
    assert worker.call_count == 3
    assert result["promotion"] == "BLOCKED"
    assert result["quality_review"] == "pending"
    assert result["known_cost_usd"] is None


def test_deadline_kills_and_waits_before_returning(tmp_path):
    import subprocess

    with patch("benchmarks.suites.research_parser.subprocess.Popen") as spawn:
        process = spawn.return_value
        process.wait.side_effect = [subprocess.TimeoutExpired("worker", 1), -9]
        result = run_worker(sys.executable, tmp_path / "source.pdf", "current", tmp_path / "result.json", 1)
    assert result["status"] == "timeout"
    process.kill.assert_called_once()
    assert process.wait.call_count == 2
    assert result["output"] is None
    assert "-m" not in spawn.call_args.args[0]


def test_failed_worker_cannot_publish_evidence(tmp_path):
    output = tmp_path / "result.json"
    output.write_text('{"partial": true}')
    with patch("benchmarks.suites.research_parser.subprocess.Popen") as spawn:
        spawn.return_value.wait.return_value = 1
        result = run_worker(sys.executable, tmp_path / "source.pdf", "current", output, 1)
    assert result["status"] == "failed"
    assert result["output"] is None


def test_invalid_bounds_rejected_before_output(tmp_path):
    with pytest.raises(ValueError, match="bounds"):
        compare(tmp_path / "missing.json", tmp_path / "run", sys.executable, timeout=601)
    assert not (tmp_path / "run").exists()


def test_worker_cli_starts_without_project_package_imports():
    from benchmarks.suites import research_parser

    result = subprocess.run(
        [sys.executable, "-I", str(Path(research_parser.__file__).resolve()), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "--worker" in result.stdout


@pytest.mark.parametrize("payload", ['{"markdown":""}', "broken-json", "[]"])
def test_success_exit_without_valid_evidence_is_failed(tmp_path, payload):
    output = tmp_path / "result.json"
    output.write_text(payload)
    with patch("benchmarks.suites.research_parser.subprocess.Popen") as spawn:
        spawn.return_value.wait.return_value = 0
        result = run_worker(sys.executable, tmp_path / "source.pdf", "current", output, 1)
    assert result["status"] == "failed"
    assert result["output"] is None


def test_partial_conversion_retains_partial_status(tmp_path):
    output = tmp_path / "result.json"
    output.write_text(json.dumps({"markdown": "retained", "conversion_status": "ConversionStatus.PARTIAL_SUCCESS"}))
    with patch("benchmarks.suites.research_parser.subprocess.Popen") as spawn:
        spawn.return_value.wait.return_value = 0
        result = run_worker(sys.executable, tmp_path / "source.pdf", "docling_native", output, 1)
    assert result["status"] == "partial"
    assert result["output"] == output.name


def test_completed_receipt_survives_later_worker_failure(tmp_path):
    document = source_document(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": [document]}))
    output = tmp_path / "run"
    with (
        patch(
            "benchmarks.suites.research_parser.run_worker",
            side_effect=[{"status": "complete"}, RuntimeError("second worker unavailable")],
        ),
        pytest.raises(RuntimeError, match="unavailable"),
    ):
        compare(manifest, output, sys.executable)
    checkpoint = json.loads((output / "telemetry_receipts.json").read_text())
    assert len(checkpoint["receipts"]) == 1
    assert checkpoint["run_status"] == "running"
    assert checkpoint["promotion"] == "BLOCKED"


def test_total_deadline_prevents_more_workers(tmp_path):
    document = source_document(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"documents": [document]}))
    with (
        patch("benchmarks.suites.research_parser.time.monotonic", side_effect=[0, 2, 2, 2]),
        patch("benchmarks.suites.research_parser.run_worker") as worker,
    ):
        result = compare(manifest, tmp_path / "run", sys.executable, total_timeout=1)
    worker.assert_not_called()
    assert len(result["receipts"]) == 3
    assert all(r["status"] == "deadline_exceeded" for r in result["receipts"])
    assert result["promotion"] == "BLOCKED"


def test_summary_cannot_infer_accuracy_or_missing_memory(tmp_path):
    from benchmarks.suites.research_parser import summarize

    (tmp_path / "artifact.json").write_text(json.dumps({"markdown": "text", "peak_working_set_bytes": None}))
    (tmp_path / "telemetry_receipts.json").write_text(
        json.dumps(
            {"receipts": [{"route": "current", "status": "complete", "elapsed_seconds": 1, "output": "artifact.json"}]}
        )
    )
    result = summarize(tmp_path)
    assert result["accuracy"] is None and result["promotion"] == "BLOCKED"
    assert result["arms"]["current"]["peak_bytes"] == []
