"""Optional standard-first PDF routing; extraction signals never certify truth."""

import hashlib
import importlib.metadata
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from pdfminer.pdfexceptions import PDFException

logger = logging.getLogger(__name__)
MAX_TEXT = 2_000_000
MAX_BYTES = 25 * 1024 * 1024
_slot = threading.BoundedSemaphore(1)


def _number(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        logger.warning("Invalid numeric PDF setting %s; using default", name)
        return default
    return max(minimum, min(value, maximum))


@dataclass(frozen=True)
class PDFSettings:
    enabled: bool = False
    ocr_enabled: bool = True
    timeout_seconds: int = 180
    threads: int = 2
    python: str = sys.executable
    artifacts_path: str = ""

    @classmethod
    def from_env(cls) -> "PDFSettings":
        return cls(
            enabled=os.environ.get("AAA_DOCLING_ENABLED", "false").strip().lower() in {"true", "1", "yes"},
            ocr_enabled=os.environ.get("AAA_DOCLING_OCR_ENABLED", "true").strip().lower() in {"true", "1", "yes"},
            timeout_seconds=_number("AAA_DOCLING_TIMEOUT_SECONDS", 180, 1, 300),
            threads=_number("AAA_DOCLING_THREADS", 2, 1, 2),
            python=os.environ.get("AAA_DOCLING_PYTHON", "").strip() or sys.executable,
            artifacts_path=os.environ.get("AAA_DOCLING_ARTIFACTS_PATH", "").strip(),
        )

    def fingerprint(self) -> str:
        contract = {"settings": asdict(self), "quality_version": 1}
        return hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()


def text_issues(text: str, *, check_headings: bool = True) -> tuple[str, ...]:
    """Observable, language-limited heuristics; not semantic accuracy scores."""
    if not text.strip():
        return ("empty_text",)
    issues = []
    visible = sum(not character.isspace() for character in text)
    if visible < 40:
        issues.append("sparse_text")
    bad = sum(character == "\ufffd" or (ord(character) < 32 and character not in "\n\r\t") for character in text)
    if bad / max(1, visible) > 0.01:
        issues.append("corrupted_characters")
    latin_tokens = re.findall(r"[A-Za-z]+", text)
    long_tokens = sum(len(token) >= 30 for token in latin_tokens)
    if long_tokens >= 3 and long_tokens / max(1, len(latin_tokens)) > 0.1:
        issues.append("joined_words")
    lines = [line for line in text.splitlines() if line.strip()]
    if check_headings and len(lines) >= 20 and sum(line.startswith("#") for line in lines) / len(lines) >= 0.25:
        issues.append("excessive_headings")
    return tuple(issues)


@dataclass(frozen=True)
class PDFObservation:
    method: str
    text: str
    issues: tuple[str, ...]
    parser_version: str | None = None
    ocr_used: bool = False


@dataclass(frozen=True)
class PDFExtraction:
    observations: tuple[PDFObservation, ...]
    selected_index: int
    byte_hash: str | None
    config_hash: str
    fallback_outcome: str

    @property
    def selected(self) -> PDFObservation:
        return self.observations[self.selected_index]

    @property
    def retained_characters(self) -> int:
        return sum(len(observation.text) for observation in self.observations)


class PDFText(str):
    """String-compatible result retaining distinct parser representations."""

    extraction: PDFExtraction

    def __new__(cls, extraction: PDFExtraction) -> "PDFText":
        value = super().__new__(cls, extraction.selected.text)
        value.extraction = extraction
        return value


class DoclingFailure(RuntimeError):
    """Safe category, without paths or raw third-party error text."""


def _run_docling(path: Path, settings: PDFSettings, ocr: bool, byte_hash: str) -> PDFObservation:
    if not _slot.acquire(timeout=2):
        raise DoclingFailure("worker_busy")
    try:
        with tempfile.TemporaryDirectory(prefix="aaa-docling-") as directory:
            output = Path(directory) / "result.json"
            command = [
                settings.python,
                str(Path(__file__).with_name("docling_worker.py")),
                "--source",
                str(path),
                "--output",
                str(output),
                "--threads",
                str(settings.threads),
                "--byte-hash",
                byte_hash,
            ]
            if ocr:
                command.append("--ocr")
            if settings.artifacts_path:
                command.extend(["--artifacts-path", settings.artifacts_path])
            allowed = {
                "PATH",
                "SYSTEMROOT",
                "WINDIR",
                "HOME",
                "USERPROFILE",
                "TEMP",
                "TMP",
                "TMPDIR",
                "LANG",
                "LC_ALL",
                "LD_LIBRARY_PATH",
                "HF_HOME",
                "HF_HUB_CACHE",
                "HF_HUB_OFFLINE",
                "XDG_CACHE_HOME",
            }
            environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
            environment.update(OMP_NUM_THREADS=str(settings.threads), MKL_NUM_THREADS=str(settings.threads))
            error_log = Path(directory) / "worker.log"
            with error_log.open("w", encoding="utf-8") as stream:
                try:
                    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=stream, env=environment)
                except OSError as exc:
                    raise DoclingFailure("worker_start_failed") from exc
                try:
                    code = process.wait(timeout=settings.timeout_seconds)
                except subprocess.TimeoutExpired as exc:
                    process.kill()
                    process.wait()
                    raise DoclingFailure("worker_timeout") from exc
            if code != 0:
                from backend.core.logging_config import mask_secrets

                with error_log.open("rb") as stream:
                    stream.seek(max(0, error_log.stat().st_size - 65536))
                    details = stream.read(65536).decode("utf-8", errors="replace")
                logger.error("Docling worker failed: %s", mask_secrets(details))
            if not output.exists() or output.stat().st_size > 12_000_000:
                raise DoclingFailure("worker_output_unavailable")
            try:
                payload = json.loads(output.read_bytes())
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise DoclingFailure("worker_output_invalid") from exc
            if not isinstance(payload, dict):
                raise DoclingFailure("worker_output_invalid")
            if code != 0 or payload.get("status") != "complete":
                category = payload.get("category")
                safe_categories = {
                    "dependency_missing",
                    "worker_busy",
                    "conversion_failed",
                    "input_rejected",
                    "output_limit",
                    "unexpected_failure",
                }
                raise DoclingFailure(
                    category if isinstance(category, str) and category in safe_categories else "conversion_failed"
                )
            text = payload.get("text")
            if not isinstance(text, str) or len(text) > MAX_TEXT or payload.get("byte_hash") != byte_hash:
                raise DoclingFailure("worker_output_invalid")
            version = payload.get("parser_version")
            return PDFObservation(
                "docling",
                text,
                text_issues(text, check_headings=False),
                version if isinstance(version, str) else None,
                ocr,
            )
    finally:
        _slot.release()


def extract_pdf(path: Path, standard: Callable[[Path], str]) -> PDFText:
    settings = PDFSettings.from_env()
    byte_hash = None
    if settings.enabled and path.is_file() and 0 < path.stat().st_size <= MAX_BYTES:
        byte_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    standard_error: Exception | None = None
    try:
        standard_text = standard(path)
    except (OSError, ValueError, ImportError, RuntimeError, PDFException) as exc:
        if not settings.enabled:
            raise
        logger.exception("Standard PDF extraction failed; trying opt-in fallback")
        standard_error = exc
        standard_text = ""
    if settings.enabled and len(standard_text) > MAX_TEXT:
        raise ValueError("PDF extraction exceeds text boundary")
    issues = ("standard_failed",) if standard_error else text_issues(standard_text)
    if byte_hash:
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != byte_hash:
                issues += ("source_changed",)
                byte_hash = None
        except OSError:
            issues += ("input_unavailable",)
            byte_hash = None
    try:
        version = importlib.metadata.version("pdfplumber")
    except importlib.metadata.PackageNotFoundError:
        version = None
        logger.warning("Standard parser version unavailable")
    observation = PDFObservation("pdfplumber", standard_text, issues, version)
    observations = [observation]
    selected = 0
    outcome = "disabled" if not settings.enabled else "not_needed"
    if "source_changed" in issues or "input_unavailable" in issues:
        outcome = issues[-1]
    elif settings.enabled and issues:
        outcome = "input_rejected"
        try:
            resolved = path.resolve(strict=True)
            if resolved.suffix.lower() != ".pdf" or not 0 < resolved.stat().st_size <= MAX_BYTES:
                raise DoclingFailure("input_rejected")
            raw = resolved.read_bytes()
            if not raw[:1024].lstrip().startswith(b"%PDF-"):
                raise DoclingFailure("input_rejected")
            if hashlib.sha256(raw).hexdigest() != byte_hash:
                raise DoclingFailure("source_changed")
            fallback = _run_docling(resolved, settings, settings.ocr_enabled and not standard_text.strip(), byte_hash)
            observations.append(fallback)
            # Do not accept clean-looking but substantially truncated output.
            enough_text = len(fallback.text.strip()) >= len(standard_text.strip()) * 0.5
            if not fallback.issues and enough_text:
                selected = 1
                outcome = "selected"
            else:
                outcome = "quality_rejected"
        except (DoclingFailure, OSError) as exc:
            outcome = str(exc) if isinstance(exc, DoclingFailure) else "input_unavailable"
            if outcome == "source_changed":
                byte_hash = None
            logger.warning("Docling fallback unavailable (%s); retaining standard observation", outcome)
    result = PDFExtraction(tuple(observations), selected, byte_hash, settings.fingerprint(), outcome)
    logger.info(
        "PDF extraction route=%s fallback=%s standard_issues=%s config=%s",
        result.selected.method,
        outcome,
        issues,
        result.config_hash,
    )
    if standard_error is not None and selected == 0:
        raise standard_error
    return PDFText(result)


def retained_characters(content: str) -> int:
    return content.extraction.retained_characters if isinstance(content, PDFText) else len(content)
