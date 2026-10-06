"""Isolated optional converter. Cross-process lock precedes heavy imports."""

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import logging
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

MAX_TEXT = 2_000_000
MAX_BYTES = 25 * 1024 * 1024


@contextmanager
def conversion_slot() -> Iterator[bool]:
    checkout = hashlib.sha256(str(Path(__file__).resolve().parents[2]).encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / f"aaa-docling-{checkout}.lock"
    with lock_path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        acquired = False
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            stream.seek(0)
            try:
                if sys.platform == "win32":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except BlockingIOError:
                time.sleep(0.05)
            except OSError as exc:
                if sys.platform != "win32" or exc.errno not in {13, 36}:
                    raise
                time.sleep(0.05)
        try:
            yield acquired
        finally:
            if acquired:
                stream.seek(0)
                if sys.platform == "win32":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def convert(source: Path, byte_hash: str, threads: int, ocr: bool, artifacts_path: str) -> dict[str, Any]:
    path = source.resolve(strict=True)
    if path.suffix.lower() != ".pdf" or not 0 < path.stat().st_size <= MAX_BYTES:
        return {"status": "failed", "category": "input_rejected"}
    raw = path.read_bytes()
    if not raw[:1024].lstrip().startswith(b"%PDF-") or hashlib.sha256(raw).hexdigest() != byte_hash:
        return {"status": "failed", "category": "input_rejected"}
    with conversion_slot() as acquired:
        if not acquired:
            return {"status": "failed", "category": "worker_busy"}
        try:
            base = importlib.import_module("docling.datamodel.base_models")
            options_module = importlib.import_module("docling.datamodel.pipeline_options")
            converter_module = importlib.import_module("docling.document_converter")
        except ImportError:
            logging.exception("Optional Docling dependency unavailable")
            return {"status": "failed", "category": "dependency_missing"}
        options = options_module.PdfPipelineOptions()
        options.do_ocr = ocr
        options.enable_remote_services = False
        options.accelerator_options = options_module.AcceleratorOptions(num_threads=threads, device="cpu")
        if artifacts_path:
            options.artifacts_path = Path(artifacts_path)
        converter = converter_module.DocumentConverter(
            format_options={base.InputFormat.PDF: converter_module.PdfFormatOption(pipeline_options=options)}
        )
        result = converter.convert(path, max_num_pages=100, max_file_size=MAX_BYTES)
        if str(result.status) != "ConversionStatus.SUCCESS" or result.errors:
            return {"status": "failed", "category": "conversion_failed"}
        text = result.document.export_to_markdown()
        if not isinstance(text, str) or len(text) > MAX_TEXT:
            return {"status": "failed", "category": "output_limit"}
        if hashlib.sha256(path.read_bytes()).hexdigest() != byte_hash:
            return {"status": "failed", "category": "input_rejected"}
        return {
            "status": "complete",
            "text": text,
            "byte_hash": byte_hash,
            "parser_version": importlib.metadata.version("docling"),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--byte-hash", required=True)
    parser.add_argument("--threads", type=int, choices=(1, 2), default=2)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--artifacts-path", default="")
    args = parser.parse_args()
    try:
        payload = convert(args.source, args.byte_hash, args.threads, args.ocr, args.artifacts_path)
    except (OSError, ValueError, RuntimeError):
        logging.exception("Isolated PDF conversion failed")
        payload = {"status": "failed", "category": "unexpected_failure"}
    args.output.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    if payload["status"] != "complete":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
