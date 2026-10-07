# 043 — T70 parser evaluation

Date: 2026-10-07. Scope: offline benchmark implementation, native-text comparison and review preparation. Branch: `codex/research-v2`. No production parser default changed and no VPS deployment performed.

T70 is complete for the supplied corpus and bounded tooling. The user has no genuine scanned corpus or independent references available and explicitly requested these be recorded as future TODOs. Root SPEC T75 owns that deferred evaluation. T70 completion does not certify Docling accuracy or OCR readiness.

## Corpus and verified observations

Three user-supplied PDFs contain 43 pages with native text. Sources remain in `D:/07_RESEARCH/POM/Input/processed`; original byte hashes were rechecked against the frozen manifest before reporting. The comparison receipts were produced on 2026-10-06 and are preserved in the ignored `benchmarks/runs/research/t70_comparison_20261006_direct/telemetry_receipts.json`. Source text was not copied into this report. The summary below is calculated from those receipts and successful worker artifacts.

| Route | Completed / attempts | Other outcomes | Median attempt time, seconds | Observed successful-worker peak range, MiB |
| --- | ---: | --- | ---: | ---: |
| pdfplumber | 3 / 3 | None | 1.550 | 72.1–174.0 |
| Docling native | 3 / 3 | None | 31.726 | 1581.2–1881.5 |
| Docling OCR enabled | 2 / 3 | One timeout | 39.785 | 1805.6–2076.3 |

Times include process startup and unsuccessful attempts. Memory ranges cover only successful workers with recorded Windows peak working set; they exclude the timed-out worker and do not establish an 8-GB VPS capacity guarantee. There were no LLM calls. Monetary compute cost and independent accuracy remain unknown. Package/model license approval remains pending; package metadata alone does not establish model-weight license suitability.

These observations do not establish that OCR improved extraction: all inputs already have native text. Native Docling costs more time and memory in this small run, and no independent reading-order, heading, passage or citation scores are available. Keep pdfplumber as the standard parser; retain the separately authorized, default-off standard-first Docling fallback from T73.

## Tooling and review

The benchmark verifies PDF signature, size and immutable bytes; isolates conversions in serial workers; kills and reaps timed-out workers; bounds each attempt and the total run; checkpoints each receipt; and preserves partial, failed and deadline-exceeded outcomes. Raw parser representations stay separate. Successful exit without valid nonempty text cannot publish a completed extraction. Metadata records manifest hash, route set and deadline settings.

The review generator includes native and OCR arms, retains partial conversion status, hides route names behind stable A/B/C labels, escapes PDF text, and rejects artifact paths outside the run. It produces an unreviewed packet with null error fields and page-example slots. The final packet at `benchmarks/runs/research/t70_final_review_20261007` contains three PDFs and eight extracts; the timed-out OCR arm contributes no extract. Its status remains pending and promotion remains blocked.

Reproduce a comparison using the production interpreter and a separate installed Docling interpreter:

```powershell
python benchmarks/suites/research_parser.py --manifest <frozen-manifest.json> --candidate-python <docling-python.exe> --output <new-run-directory> --timeout 240 --total-timeout 1800
python benchmarks/suites/research_parser.py --summarize-run <run-directory> --output <summary.json>
python benchmarks/suites/research_parser_review.py --run <run-directory> --output <new-review-directory>
```

## Future TODO — T75

Obtain genuine scanned/image-only documents and independent page-numbered reference transcriptions. Review reading order, headings, missing/corrupted passages and citation locators. Compare suitable OCR/specialist candidates on that frozen set. Measure conversion peak resources and concurrent application load on the actual VPS, and review package plus model-weight licenses and cost before any default parser promotion. T71 must report this unresolved evidence honestly.

## Verification

42 focused parser and PDF fallback regression tests passed. All four benchmark Python files passed Ruff lint and format checks. Frozen source hashes, eight review extracts and the receipt-derived summary CLI were checked. `git diff --check` passed. Generated verification artifacts remain uncommitted; prior cleanup was blocked by policy. Repository-wide baseline limitations remain in Report 040. This benchmark adds no backend runtime module or frontend change.
