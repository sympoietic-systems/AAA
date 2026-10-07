"""Prepare an unlabelled parser review packet; never manufacture review results."""

import argparse
import hashlib
import html
import json
from pathlib import Path


def prepare_review(run, output):
    telemetry_path = run / "telemetry_receipts.json"
    telemetry_bytes = telemetry_path.read_bytes()
    telemetry = json.loads(telemetry_bytes)
    groups = {}
    for receipt in telemetry["receipts"]:
        if receipt["status"] not in ("complete", "partial"):
            continue
        if receipt["route"] not in ("current", "docling_native", "docling_ocr"):
            continue
        artifact = (run / receipt["output"]).resolve()
        if artifact.parent != run.resolve():
            raise ValueError("Parser artifact outside run")
        payload = json.loads(artifact.read_bytes())
        groups.setdefault(receipt["source_sha256"], []).append((receipt, artifact, payload))
    output.mkdir(parents=True, exist_ok=False)
    samples, mapping, sections = [], [], []
    for source_hash, arms in sorted(groups.items()):
        if len(arms) < 2:
            continue
        if len({arm[0]["route"] for arm in arms}) != len(arms):
            raise ValueError("Duplicate parser route for source")
        # Assignment is stable for this packet, but labels reveal no parser name.
        arms.sort(key=lambda arm: hashlib.sha256(telemetry_bytes + arm[0]["route"].encode()).hexdigest())
        panels = []
        candidates = []
        for label, (receipt, artifact, payload) in zip("ABC"[: len(arms)], arms, strict=True):
            artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
            candidates.append(
                {
                    "label": label,
                    "artifact_sha256": artifact_hash,
                    "conversion_status": receipt["status"],
                    "reading_order_errors": None,
                    "heading_errors": None,
                    "missing_or_corrupted_passages": None,
                    "citation_errors": None,
                    "examples_with_pdf_page": [],
                }
            )
            mapping.append(
                {
                    "source_sha256": source_hash,
                    "label": label,
                    "route": receipt["route"],
                    "artifact": str(artifact),
                    "artifact_sha256": artifact_hash,
                }
            )
            panels.append(f"<article><h3>Extract {label}</h3><pre>{html.escape(payload['markdown'])}</pre></article>")
        source = arms[0][0]["source_path"]
        samples.append(
            {"source_path": source, "source_sha256": source_hash, "preferred_extract": None, "candidates": candidates}
        )
        sections.append(
            f"<section><h2>{html.escape(Path(source).name)}</h2>"
            f'<p>Original: {html.escape(source)}</p><div class="panels">{"".join(panels)}</div></section>'
        )
    packet = {
        "schema_version": 1,
        "telemetry_sha256": hashlib.sha256(telemetry_bytes).hexdigest(),
        "reviewer": None,
        "reviewed_at": None,
        "status": "pending",
        "instructions": "Compare each extract against the original PDF. Do not consult the route mapping or "
        "telemetry before recording judgments. Record page-numbered examples; null is unreviewed, "
        "zero means checked with no observed error. Preference alone is not an accuracy score.",
        "samples": samples,
        "promotion": "BLOCKED",
    }
    (output / "review_template.json").write_text(json.dumps(packet, indent=2), encoding="utf-8")
    (output / "route_mapping.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Parser review</title>'
    page += "<style>body{background:#111;color:#eee;font:16px system-ui;margin:24px}"
    page += ".panels{display:grid;grid-template-columns:1fr 1fr;gap:20px}pre{white-space:pre-wrap;"
    page += "overflow-wrap:anywhere;max-height:75vh;overflow:auto;background:#222;padding:16px}"
    page += "@media(max-width:800px){.panels{grid-template-columns:1fr}}</style>"
    page += "<h1>PDF parser accuracy review</h1><p>" + html.escape(packet["instructions"]) + "</p>"
    page += "<p>Record judgments in review_template.json. This packet contains no completed quality ratings.</p>"
    page += "".join(sections) + "</html>"
    (output / "review.html").write_text(page, encoding="utf-8")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    packet = prepare_review(args.run, args.output)
    print(json.dumps({"samples": len(packet["samples"]), "status": packet["status"]}))


if __name__ == "__main__":
    main()
