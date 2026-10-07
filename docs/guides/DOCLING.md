# Optional Docling PDF fallback

AAA runs its existing font-aware pdfplumber parser first. Docling is an optional CPU fallback for failed or mechanically degraded extraction. It defaults to disabled. No LLM provider is involved in this conversion.

## Install and enable

Use a separate Python environment so Docling's PyTorch and document-model dependencies do not change AAA's main environment. The tested SDK version is 2.134.0. Example for a Linux checkout at `/srv/aaa`:

```bash
cd /srv/aaa
uv venv --python 3.12 .venv-docling
uv pip install --python .venv-docling/bin/python "docling==2.134.0" --extra-index-url https://download.pytorch.org/whl/cpu
.venv-docling/bin/docling-tools models download --output-dir backend/data/docling-models
```

Set these values in the checkout's `.env`, replacing paths with your deployment paths:

```dotenv
AAA_DOCLING_ENABLED=true
AAA_DOCLING_PYTHON=/srv/aaa/.venv-docling/bin/python
AAA_DOCLING_ARTIFACTS_PATH=/srv/aaa/backend/data/docling-models
AAA_DOCLING_THREADS=2
AAA_DOCLING_TIMEOUT_SECONDS=180
AAA_DOCLING_OCR_ENABLED=true
```

Restart the backend and upload workers to reload `.env`. On Windows, the interpreter path ends in `.venv-docling/Scripts/python.exe`. The interpreter must have Docling installed; the main AAA interpreter does not need it. The artifacts path is optional: without it, Docling uses its normal model cache and may download model weights on first use. Prefetching avoids those downloads consuming the conversion timeout.

To disable the fallback, set `AAA_DOCLING_ENABLED=false` and restart. Disabled extraction never launches the Docling worker. `.env.example` includes the defaults; the local implementation checkout's `.env` also defaults to disabled.

See the publisher's [installation instructions](https://docling-project.github.io/docling/getting_started/installation/) and [advanced options](https://docling-project.github.io/docling/usage/advanced_options/) for model storage and SDK configuration. AAA disables Docling remote conversion services. Model downloads still require network access unless the artifacts are available locally.

## Routing and failure behavior

Quality contract version 1 requests fallback when standard extraction raises an expected parser/I/O exception or reports any of these signals:

| Signal | Trigger |
| --- | --- |
| Empty text | No non-whitespace text |
| Sparse text | Fewer than 40 non-whitespace characters |
| Corrupted characters | Replacement/control characters exceed 1% of visible characters; normal whitespace excluded |
| Joined words | At least three Latin-letter tokens of 30 or more letters, exceeding 10% of Latin tokens |
| Excessive headings | At least 20 nonempty lines, with 25% or more beginning with `#` |

These checks detect some extraction defects. They do not measure semantic accuracy, validate citations, or reliably detect all languages, tables, or column-order errors. A clean standard result stays on the standard route.

The fallback runs OCR only when standard text is empty and `AAA_DOCLING_OCR_ENABLED=true`. Setting that flag to false allows native Docling extraction but disables OCR. Docling output is selected only when it passes the empty, sparse, corrupted-character, and joined-word checks and retains at least half the standard result's stripped character count. The heading-density check applies only to standard extraction: Docling deliberately emits Markdown headings. Both successful parser outputs remain separate observations even when the fallback is rejected.

Missing dependencies, a busy worker, timeout, invalid input, conversion failure, or rejected fallback quality keep the standard result and log the failure category. If standard extraction raised an exception and no fallback was accepted, the original exception propagates. Unexpected standard-parser errors propagate rather than being silently treated as poor quality.

Research V2 records each parser representation as a separate source version, with its own text spans, parser version, configuration fingerprint, and warnings. Both refer to the same original PDF byte hash when available. Parser quality and layout scores remain unknown. Selecting Docling does not discard the standard observation's exclusions or mark the result as verified. Acquisition cache keys include the configuration fingerprint and quality contract version; cache size counts all retained representations.

## Bounds and a 4-core / 8-GB VPS

Start with two CPU threads and one conversion at a time. This is a provisional operating configuration, not a measured guarantee for your VPS. The local comparison used about 1.7–2.0 GB peak working set for native Docling conversion; document structure, OCR, and the rest of AAA can increase demand. Monitor total memory and conversion deadlines before raising load. Model files need separate disk space.

The worker enforces a 25-MiB PDF limit, a 100-page conversion limit, and a two-million-character output limit. Enabling the router also applies the character limit to standard extraction. Thread count is clamped to 1–2; timeout defaults to 180 seconds and is clamped to 1–300 seconds. Invalid numeric settings log a warning and use defaults.

A process-local semaphore and an OS file lock allow one Docling conversion per checkout when workers share the OS temporary directory. Capacity waits are bounded to two seconds. Separate containers or different checkouts need deployment-level coordination if they share a memory budget. The deadline kills and reaps the worker before releasing its local slot. Async cancellation retains the temporary input until physical parsing exits. The PDF hash is checked before and after extraction to reject fallback on changed input.

No VPS deployment was performed. [Report 040](../reports/040-docling-fallback/README.md) records the local routing checks. T70 benchmark implementation is complete for the supplied native-text corpus. The user deferred independent parser-accuracy review and real scanned-PDF coverage to future T75. [Report 043](../reports/043-parser-evaluation/README.md) records the comparison and non-promotion decision.
