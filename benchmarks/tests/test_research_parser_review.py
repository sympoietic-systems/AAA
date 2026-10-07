import json

from benchmarks.suites.research_parser_review import prepare_review


def test_packet_preserves_unreviewed_status_and_escapes_pdf_text(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    receipts = []
    for route in ("current", "docling_native"):
        filename = route + ".json"
        (run / filename).write_text(json.dumps({"markdown": '<script>alert("PDF")</script>'}))
        receipts.append(
            {
                "source_sha256": "frozen",
                "source_path": "original.pdf",
                "route": route,
                "status": "complete",
                "output": filename,
            }
        )
    (run / "telemetry_receipts.json").write_text(json.dumps({"receipts": receipts}))
    output = tmp_path / "review"
    packet = prepare_review(run, output)
    assert packet["status"] == "pending"
    assert packet["reviewer"] is None
    assert packet["promotion"] == "BLOCKED"
    assert len(packet["samples"]) == 1
    assert packet["samples"][0]["preferred_extract"] is None
    assert all(candidate["heading_errors"] is None for candidate in packet["samples"][0]["candidates"])
    page = (output / "review.html").read_text()
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert "docling_native" not in page


def test_failed_candidates_do_not_enter_review(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "telemetry_receipts.json").write_text(json.dumps({"receipts": [{"status": "timeout"}]}))
    packet = prepare_review(run, tmp_path / "review")
    assert packet["samples"] == []
    assert packet["promotion"] == "BLOCKED"


def test_all_three_routes_enter_review_with_partial_status(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    receipts = []
    for route in ("current", "docling_native", "docling_ocr"):
        (run / (route + ".json")).write_text(json.dumps({"markdown": "content"}))
        receipts.append(
            {
                "route": route,
                "source_sha256": "frozen",
                "source_path": "original.pdf",
                "status": "partial" if route == "docling_ocr" else "complete",
                "output": route + ".json",
            }
        )
    (run / "telemetry_receipts.json").write_text(json.dumps({"receipts": receipts}))
    packet = prepare_review(run, tmp_path / "review")
    candidates = packet["samples"][0]["candidates"]
    assert {c["label"] for c in candidates} == {"A", "B", "C"}
    assert sum(c["conversion_status"] == "partial" for c in candidates) == 1
    assert packet["promotion"] == "BLOCKED"
