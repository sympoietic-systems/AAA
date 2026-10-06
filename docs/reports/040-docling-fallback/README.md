# Report 040: Optional standard-first Docling fallback

Date: 2026-10-06. Task: T73. Architecture: [ADR-112](../../decisions/ADR-112-standard-first-docling-fallback.md). Operations: [Docling guide](../../guides/DOCLING.md).

T73 implements the user's requested environment switch and quality-triggered PDF fallback. Standard pdfplumber extraction always runs first. Docling runs in an isolated CPU worker only when enabled and triggered. Research V2 retains both successful representations, their parser lineage, independent character spans, and warnings; quality scores remain unknown.

## Corpus and receipts

The supplied directory `D:/07_RESEARCH/POM/Input/processed` contains three frozen native-text PDFs, totaling 43 pages. Original PDFs were read in place and checked against their SHA-256 hashes. No source PDF was copied into this report. The canonical small routing receipts are [telemetry_receipts.json](telemetry_receipts.json); private full-text observations and intermediate probes remain in ignored benchmark runs.

The 23-page PDF triggered fallback for excessive standard-parser headings; the 15-page PDF stayed on the standard route; the 5-page PDF triggered fallback for joined words. The final accepted Docling representations have no mechanical degradation flags. Their semantic accuracy has not been independently established.

| PDF pages | Standard signal | Selected route | Total extraction time |
| --- | --- | --- | --- |
| 23 | Excessive headings | Docling | 68.19 s |
| 15 | None | pdfplumber | 1.44 s |
| 5 | Joined words | Docling | 26.80 s |

These are individual local Windows routing measurements with Docling 2.134.0 and pdfplumber 0.11.9, CPU threads set to two, and cached model weights. They are not throughput estimates or a VPS capacity guarantee. No LLM calls were made. Billing was not measured; the nullable cost field is not a zero-cost claim. OCR on genuine scanned documents was not tested by this corpus.

## Verification

- 217 tests passed across Research V2, PDF fallback, safe HTTP, web retrieval, ebook digestion, and rhizomatic digestion. One existing third-party MOBI `imghdr` deprecation warning remains.
- Backend Ruff lint passed. All eight changed Python files passed format checks.
- Strict typing passed for the router, worker, acquisition runtime, and evidence store. Linux-platform typing passed for the two new parser modules; Linux runtime and VPS deployment were not exercised.
- Tests cover default-off behavior, healthy standard extraction, failure/OCR routing, rejected/truncated fallback, worker timeout and reaping, independent-process capacity locking, secret exclusion from child environments, immutable source hashes, parser-specific Unicode spans, cache budgeting/settings invalidation, and temporary-input ownership during async cancellation.
- A 35% heading threshold missed the observed standard heading density. The corrected 25% threshold initially rejected legitimate Docling Markdown headings; a worker-output regression now keeps that check specific to standard extraction. Both discoveries are recorded in SPEC B99/V120.

Repository-wide verification remains blocked by existing failures: boredom coupling, sync-route debt, six broad-catch debt entries in unchanged modules, seven unrelated formatting files, and the unparameterized `asyncio.Task` in `backend/services/keyed_lock.py`. The final full-suite attempt stopped after three failures with 37 tests passed. No new fallback catch-debt allowance was added; the existing standard-parser entry was renamed with its unchanged count.

## Remaining gates

T73 is complete for the requested opt-in mechanism. T70 still requires independent parser-accuracy annotation and scanned-PDF coverage. T69–T72 retain their existing calibration/release gates; this fallback does not promote any model or enable automatic research branching. The runtime default remains disabled until the operator installs the SDK, sets the deployment paths, and explicitly enables it.
