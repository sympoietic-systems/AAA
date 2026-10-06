import asyncio
import hashlib
import json
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from backend.modules import pdf_extraction as pdf
from backend.modules.digester import SimpleChunkDigester
from backend.modules.docling_worker import convert
from backend.services.research.acquisition import AcquisitionPolicy, AcquisitionRuntime
from backend.services.research.evidence_store import ResearchEvidenceStore

GOOD = "A readable extraction with normal word spacing and a complete paragraph for the test."
BAD = " ".join(["JoinedTogetherWithoutAnyWordSeparatorsInTheParagraph"] * 5)


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    for key in tuple(__import__("os").environ):
        if key.startswith("AAA_DOCLING_"):
            monkeypatch.delenv(key)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "source.pdf"
    path.write_bytes(b"%PDF-1.4 frozen source")
    return path


def candidate(text=GOOD):
    return pdf.PDFObservation("docling", text, pdf.text_issues(text), "test-version")


def test_disabled_does_not_spawn_even_for_degraded_text(source):
    with patch.object(pdf, "_run_docling") as worker:
        result = pdf.extract_pdf(source, lambda path: BAD)
    assert result == BAD
    assert result.extraction.fallback_outcome == "disabled"
    worker.assert_not_called()


def test_disabled_preserves_standard_exception(source):
    def fail(path):
        raise ValueError("standard failed")

    with pytest.raises(ValueError, match="standard failed"):
        pdf.extract_pdf(source, fail)


def test_healthy_enabled_standard_never_calls_docling(source, monkeypatch):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")
    with patch.object(pdf, "_run_docling") as worker:
        result = pdf.extract_pdf(source, lambda path: GOOD)
    assert result == GOOD
    assert result.extraction.fallback_outcome == "not_needed"
    worker.assert_not_called()


@pytest.mark.parametrize(
    "text,issue",
    [
        ("", "empty_text"),
        ("a short note", "sparse_text"),
        (BAD, "joined_words"),
        ("broken \ufffd" * 15, "corrupted_characters"),
        ("\n".join(["# body text marked as heading"] * 25), "excessive_headings"),
    ],
)
def test_quality_signals_are_observable(text, issue):
    assert issue in pdf.text_issues(text)


def test_quarter_heading_density_is_degraded():
    text = "\n".join(["# suspicious body line"] * 26 + ["An ordinary body line with normal spacing."] * 74)
    assert "excessive_headings" in pdf.text_issues(text)


def test_degraded_standard_selects_acceptable_fallback_and_retains_both(source, monkeypatch):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")
    better = candidate(GOOD * 4)
    with (
        patch.object(pdf, "_run_docling", return_value=better) as worker,
        patch.object(SimpleChunkDigester, "_extract_pdf_standard", return_value=BAD),
    ):
        result = SimpleChunkDigester._extract_pdf(source)
    assert result == better.text
    assert result.extraction.observations[0].text == BAD
    assert result.extraction.selected.method == "docling"
    assert result.extraction.byte_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    assert worker.call_args.args[2] is False


def test_empty_standard_enables_ocr_only_when_allowed(source, monkeypatch):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")
    for setting, expected in (("true", True), ("false", False)):
        monkeypatch.setenv("AAA_DOCLING_OCR_ENABLED", setting)
        with patch.object(pdf, "_run_docling", return_value=candidate()) as worker:
            result = pdf.extract_pdf(source, lambda path: "")
        assert result == GOOD
        assert worker.call_args.args[2] is expected


def test_unavailable_docling_retains_standard(source, monkeypatch, caplog):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")
    with patch.object(pdf, "_run_docling", side_effect=pdf.DoclingFailure("dependency_missing")):
        result = pdf.extract_pdf(source, lambda path: BAD)
    assert result == BAD
    assert result.extraction.fallback_outcome == "dependency_missing"
    assert "retaining standard" in caplog.text


def test_both_parsers_fail_propagates_original_failure(source, monkeypatch):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")

    def fail(path):
        raise ValueError("standard failed")

    with (
        patch.object(pdf, "_run_docling", side_effect=pdf.DoclingFailure("worker_timeout")),
        pytest.raises(ValueError, match="standard failed"),
    ):
        pdf.extract_pdf(source, fail)


@pytest.mark.parametrize("fallback", [candidate(BAD), candidate(GOOD)])
def test_bad_or_substantially_truncated_fallback_does_not_replace_standard(source, monkeypatch, fallback):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")
    with patch.object(pdf, "_run_docling", return_value=fallback):
        result = pdf.extract_pdf(source, lambda path: BAD * 5)
    assert result == BAD * 5
    assert len(result.extraction.observations) == 2
    assert result.extraction.fallback_outcome == "quality_rejected"


def test_changed_source_cannot_enter_fallback(source, monkeypatch):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")

    def standard(path):
        path.write_bytes(b"%PDF-1.4 changed source")
        return BAD

    with patch.object(pdf, "_run_docling") as worker:
        result = pdf.extract_pdf(source, standard)
    assert result == BAD
    assert result.extraction.fallback_outcome == "source_changed"
    worker.assert_not_called()


def test_environment_bounds_and_fail_closed_switch(monkeypatch):
    monkeypatch.setenv("AAA_DOCLING_ENABLED", "mistyped")
    monkeypatch.setenv("AAA_DOCLING_THREADS", "100")
    monkeypatch.setenv("AAA_DOCLING_TIMEOUT_SECONDS", "999")
    settings = pdf.PDFSettings.from_env()
    assert not settings.enabled
    assert settings.threads == 2
    assert settings.timeout_seconds == 300
    monkeypatch.setenv("AAA_DOCLING_TIMEOUT_SECONDS", "invalid")
    assert pdf.PDFSettings.from_env().timeout_seconds == 180


def test_worker_deadline_kills_and_reaps_before_releasing_slot(source):
    settings = pdf.PDFSettings(timeout_seconds=1)
    with patch.object(pdf.subprocess, "Popen") as spawn:
        spawn.return_value.wait.side_effect = [subprocess.TimeoutExpired("worker", 1), -9]
        with pytest.raises(pdf.DoclingFailure, match="timeout"):
            pdf._run_docling(source, settings, False, "hash")
    spawn.return_value.kill.assert_called_once()
    assert spawn.return_value.wait.call_count == 2
    assert pdf._slot.acquire(blocking=False)
    pdf._slot.release()


def test_worker_does_not_inherit_provider_secrets(source, monkeypatch):
    monkeypatch.setenv("AAA_NVIDIA_API_KEY", "secret-never-forwarded")
    monkeypatch.setenv("HF_TOKEN", "another-secret")
    with patch.object(pdf.subprocess, "Popen") as spawn:
        spawn.return_value.wait.return_value = 0
        with pytest.raises(pdf.DoclingFailure, match="output_unavailable"):
            pdf._run_docling(source, pdf.PDFSettings(), False, "hash")
    environment = spawn.call_args.kwargs["env"]
    assert "AAA_NVIDIA_API_KEY" not in environment
    assert "HF_TOKEN" not in environment


def test_worker_accepts_legitimate_markdown_heading_density(source):
    text = "\n".join(["## Meaningful section heading"] * 26 + [GOOD] * 74)
    assert pdf.text_issues(text) == ("excessive_headings",)
    with patch.object(pdf.subprocess, "Popen") as spawn:

        def complete(timeout):
            command = spawn.call_args.args[0]
            output = Path(command[command.index("--output") + 1])
            output.write_text(json.dumps({"status": "complete", "text": text, "byte_hash": "hash"}))
            return 0

        spawn.return_value.wait.side_effect = complete
        observation = pdf._run_docling(source, pdf.PDFSettings(), False, "hash")
    assert observation.text == text
    assert observation.issues == ()


def test_worker_rejects_non_pdf_before_importing_docling(source):
    source.write_bytes(b"not a PDF")
    with patch("backend.modules.docling_worker.importlib.import_module") as importer:
        result = convert(source, hashlib.sha256(source.read_bytes()).hexdigest(), 2, False, "")
    assert result["category"] == "input_rejected"
    importer.assert_not_called()


def test_conversion_lease_serializes_independent_processes(tmp_path):
    marker = tmp_path / "acquired"
    code = (
        "import pathlib,sys,time\n"
        "from backend.modules.docling_worker import conversion_slot\n"
        "with conversion_slot() as acquired:\n"
        " pathlib.Path(sys.argv[1]).write_text(str(acquired))\n"
        " if acquired and sys.argv[2] != 'none':\n"
        "  while not pathlib.Path(sys.argv[2]).exists(): time.sleep(0.05)\n"
    )
    release = tmp_path / "release"
    first = subprocess.Popen([sys.executable, "-c", code, str(marker), str(release)])
    try:
        deadline = time.monotonic() + 5
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert marker.read_text() == "True"
        second_marker = tmp_path / "second"
        second = subprocess.run([sys.executable, "-c", code, str(second_marker), "none"], timeout=5)
        assert second.returncode == 0
        assert second_marker.read_text() == "False"
        release.touch()
        assert first.wait(timeout=5) == 0
    finally:
        if first.poll() is None:
            first.kill()
            first.wait()


@pytest.fixture
def evidence_repo(tmp_path):
    from backend.tests.test_research_evidence import repo

    return repo.__wrapped__(tmp_path)


def test_research_retains_both_versions_and_parser_scoped_unicode_spans(evidence_repo):
    extraction = pdf.PDFExtraction(
        (pdf.PDFObservation("pdfplumber", BAD, ("joined_words",)), candidate(GOOD + " α🙂")),
        1,
        "a" * 64,
        "config",
        "selected",
    )
    result = pdf.PDFText(extraction)
    store = ResearchEvidenceStore(evidence_repo)
    observed = datetime.now(UTC)
    artifact, segments = store.record_text("task", "https://example.org/paper.pdf", result, observed_at=observed)
    bundle = evidence_repo.export_bundle("task")
    assert len(bundle["sources"]) == 2
    assert {row["artifact"]["original_byte_hash"] for row in bundle["sources"]} == {"a" * 64}
    assert artifact.quality.method == "docling"
    assert artifact.quality.score is None
    assert artifact.quality.layout_preserved is None
    assert segments[0].text == result
    assert "standard:joined_words" in artifact.quality.warnings
    assert store.packet(artifact, segments=segments).excluded_evidence
    store.record_text("task", "https://example.org/paper.pdf", result, observed_at=observed)
    assert len(evidence_repo.export_bundle("task")["sources"]) == 2


async def test_cache_bounds_count_alternative_representation_and_settings_changes(monkeypatch):
    runtime = AcquisitionRuntime(AcquisitionPolicy(cache_characters=100), validator=lambda url: url)
    extraction = pdf.PDFExtraction((candidate(GOOD), candidate(GOOD)), 0, None, "config", "quality_rejected")
    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return pdf.PDFText(extraction)

    try:
        for _ in range(2):
            await runtime.fetch("https://example.org/paper.pdf", {}, datetime.now(UTC) + timedelta(seconds=5), loader)
        assert calls == 2
        assert not runtime._cache
        runtime.policy = AcquisitionPolicy(cache_characters=1000)
        await runtime.fetch("https://example.org/paper.pdf", {}, datetime.now(UTC) + timedelta(seconds=5), loader)
        monkeypatch.setenv("AAA_DOCLING_ENABLED", "true")
        await runtime.fetch("https://example.org/paper.pdf", {}, datetime.now(UTC) + timedelta(seconds=5), loader)
        assert calls == 4
    finally:
        await runtime.aclose()


async def test_cancelled_pdf_fetch_keeps_input_until_physical_parser_exit():
    from backend.services.research.sensory_affordances import select_and_fetch

    started = threading.Event()
    release = threading.Event()
    paths = []

    def blocking_parser(path, file_type):
        paths.append(path)
        started.set()
        assert release.wait(5)
        assert path.exists()
        return GOOD

    response = SimpleNamespace(status_code=200, content=b"%PDF-1.4 fixture")
    with (
        patch("backend.utils.security.validate_safe_url", side_effect=lambda url: url),
        patch("backend.modules.retrieval.safe_http.safe_fetch", new=AsyncMock(return_value=response)),
        patch.object(SimpleChunkDigester, "extract", side_effect=blocking_parser),
    ):
        task = asyncio.create_task(select_and_fetch("https://example.org/file.pdf", config={}))
        try:
            assert await asyncio.to_thread(started.wait, 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert paths[0].exists()
        finally:
            release.set()
        deadline = time.monotonic() + 3
        while paths[0].exists() and time.monotonic() < deadline:
            await asyncio.sleep(0.02)
        assert not paths[0].exists()


def test_pdf_fallback_adds_no_broad_catch_debt():
    from backend.quality.architecture import debt_growth, scan_broad_catches

    root = Path(__file__).parents[2]
    baseline = json.loads(Path(__file__).with_name("architecture_debt.json").read_text())["broad_catch_boundaries"]
    growth = debt_growth(scan_broad_catches(root), baseline)
    assert not any(
        "modules/pdf_extraction.py" in item or "modules/docling_worker.py" in item or "modules/digester.py" in item
        for item in growth
    )
