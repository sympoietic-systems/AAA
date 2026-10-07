"""Frozen local PDF comparisons. Candidate dependencies never enter production."""

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time
from pathlib import Path

MAX_BYTES = 25 * 1024 * 1024
MAX_OUTPUT_BYTES = 20 * 1024 * 1024
ROUTES = ("current", "docling_native", "docling_ocr")


def verify_source(document):
    path = Path(document["source_path"]).resolve(strict=True)
    if path.suffix.lower() != ".pdf" or not 0 < path.stat().st_size <= MAX_BYTES:
        raise ValueError("PDF input exceeds corpus boundary")
    if hashlib.sha256(path.read_bytes()).hexdigest() != document["source_sha256"]:
        raise ValueError("Frozen corpus source changed")
    with path.open("rb") as stream:
        if not stream.read(1024).lstrip().startswith(b"%PDF-"):
            raise ValueError("Corpus source is not a PDF")
    return path


def extract(path, route):
    if route == "current":
        # Script workers avoid benchmarks/__init__'s unrelated embedding imports.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from backend.modules.digester import SimpleChunkDigester

        return {
            "markdown": SimpleChunkDigester().extract(path, "pdf"),
            "structured": None,
            "version": importlib.metadata.version("pdfplumber"),
            "quality": "unreviewed",
        }
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import AcceleratorOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = route == "docling_ocr"
    options.enable_remote_services = False
    options.accelerator_options = AcceleratorOptions(num_threads=2, device="cpu")
    options.document_timeout = 180
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    result = converter.convert(path, max_num_pages=100, max_file_size=MAX_BYTES)
    return {
        "markdown": result.document.export_to_markdown(),
        "structured": result.document.export_to_dict(),
        "conversion_status": str(result.status),
        "conversion_errors": [str(error.error_message) for error in result.errors],
        "version": importlib.metadata.version("docling"),
        "quality": "unreviewed",
    }


def run_worker(python, source, route, output, timeout):
    """Wait for physical worker exit before scheduling the next candidate."""
    command = [
        str(python),
        str(Path(__file__).resolve()),
        "--worker",
        "--source",
        str(source),
        "--route",
        route,
        "--output",
        str(output),
    ]
    started = time.perf_counter()
    log = output.with_suffix(".log")
    with log.open("w", encoding="utf-8") as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=stream)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            return {
                "status": "timeout",
                "elapsed_seconds": time.perf_counter() - started,
                "output": None,
                "log": log.name,
            }
    valid = code == 0 and output.exists() and output.stat().st_size <= MAX_OUTPUT_BYTES
    if valid:
        try:
            payload = json.loads(output.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        valid = isinstance(payload.get("markdown"), str) and bool(payload["markdown"].strip())
        status = "complete" if valid else "failed"
        if valid and (
            payload.get("conversion_errors")
            or payload.get("conversion_status", "ConversionStatus.SUCCESS") != "ConversionStatus.SUCCESS"
        ):
            status = "partial"
    else:
        status = "failed"
    return {
        "status": status,
        "exit_code": code,
        "elapsed_seconds": time.perf_counter() - started,
        "output": output.name if valid else None,
        "log": log.name,
    }


def compare(manifest, output, candidate_python, routes=ROUTES, timeout=240, total_timeout=1800):
    if not 1 <= timeout <= 600 or not routes or any(route not in ROUTES for route in routes):
        raise ValueError("Invalid comparison bounds")
    if not 1 <= total_timeout <= 3600 or len(set(routes)) != len(routes):
        raise ValueError("Invalid total deadline or duplicate routes")
    manifest_bytes = manifest.read_bytes()
    corpus = json.loads(manifest_bytes)
    documents = corpus["documents"]
    if not 1 <= len(documents) <= 20:
        raise ValueError("Corpus must contain 1-20 PDFs")
    sources = [(document, verify_source(document)) for document in documents]
    output.mkdir(parents=True, exist_ok=False)
    receipts = []
    result = {
        "schema_version": 1,
        "corpus_manifest": str(manifest.resolve()),
        "corpus_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "receipts": receipts,
        "run_status": "running",
        "promotion": "BLOCKED",
        "quality_review": "pending",
        "known_cost_usd": None,
        "cost_note": "Local compute cost unmeasured",
        "ocr_note": "OCR enabled does not establish scanned-PDF accuracy; corpus/reference review required",
    }
    checkpoint(output, result)
    (output / "metadata.json").write_text(
        json.dumps(
            {
                "corpus_manifest_sha256": result["corpus_manifest_sha256"],
                "routes": list(routes),
                "per_worker_timeout_seconds": timeout,
                "total_timeout_seconds": total_timeout,
                "independent_quality_review": "pending",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    deadline = time.monotonic() + total_timeout
    for document, source in sources:
        for route in routes:
            target = output / f"{document['source_sha256'][:16]}_{route}.json"
            python = sys.executable if route == "current" else candidate_python
            remaining = deadline - time.monotonic()
            receipt = (
                run_worker(python, source, route, target, min(timeout, remaining))
                if remaining > 0
                else {"status": "deadline_exceeded", "elapsed_seconds": 0, "output": None, "log": None}
            )
            # The same bytes must still be present after the worker finishes.
            verify_source(document)
            receipts.append(
                {"source_sha256": document["source_sha256"], "source_path": str(source), "route": route, **receipt}
            )
            checkpoint(output, result)
    result["run_status"] = (
        "completed_with_failures" if any(r["status"] != "complete" for r in receipts) else "completed"
    )
    checkpoint(output, result)
    return result


def summarize(run):
    """Summarize measured attempts; successful conversion is not reviewed accuracy."""
    result = json.loads((run / "telemetry_receipts.json").read_bytes())
    arms = {}
    for receipt in result["receipts"]:
        arm = arms.setdefault(receipt["route"], {"attempts": 0, "statuses": {}, "seconds": [], "peak_bytes": []})
        arm["attempts"] += 1
        status = receipt["status"]
        arm["statuses"][status] = arm["statuses"].get(status, 0) + 1
        arm["seconds"].append(receipt["elapsed_seconds"])
        if receipt.get("output"):
            artifact = (run / receipt["output"]).resolve(strict=True)
            if artifact.parent != run.resolve():
                raise ValueError("Parser artifact outside run")
            payload = json.loads(artifact.read_bytes())
            peak = payload.get("peak_working_set_bytes")
            if isinstance(peak, int) and not isinstance(peak, bool) and peak > 0:
                arm["peak_bytes"].append(peak)
    return {"arms": arms, "promotion": "BLOCKED", "accuracy": None, "known_cost_usd": None}


def checkpoint(output, result):
    temporary = output / "telemetry_receipts.pending.json"
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    temporary.replace(output / "telemetry_receipts.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--route", choices=ROUTES)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--summarize-run", type=Path)
    parser.add_argument("--candidate-python", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--total-timeout", type=int, default=1800)
    args = parser.parse_args()
    if args.summarize_run:
        args.output.write_text(json.dumps(summarize(args.summarize_run), indent=2), encoding="utf-8")
    elif args.worker:
        if args.source is None or args.route is None:
            parser.error("worker requires source and route")
        started = time.perf_counter()
        result = extract(args.source, args.route)
        result["extraction_seconds"] = time.perf_counter() - started
        try:
            import psutil
        except ImportError:
            result["peak_working_set_bytes"] = None
            result["resource_warning"] = "psutil_unavailable"
        else:
            memory = psutil.Process().memory_info()
            result["peak_working_set_bytes"] = getattr(memory, "peak_wset", None)
            result["resident_bytes_at_export"] = memory.rss
        package = "pdfplumber" if args.route == "current" else "docling"
        metadata = importlib.metadata.metadata(package)
        result["package_license_metadata"] = metadata.get("License-Expression") or metadata.get("License")
        result["license_review"] = "pending_including_model_weights"
        payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
        if len(payload) > MAX_OUTPUT_BYTES:
            raise ValueError("Parser output exceeds evidence boundary")
        args.output.write_bytes(payload)
    else:
        if args.manifest is None or args.candidate_python is None:
            parser.error("comparison requires manifest and candidate-python")
        result = compare(
            args.manifest, args.output, args.candidate_python, timeout=args.timeout, total_timeout=args.total_timeout
        )
        print(
            json.dumps(
                {"promotion": result["promotion"], "statuses": [receipt["status"] for receipt in result["receipts"]]}
            )
        )


if __name__ == "__main__":
    main()
