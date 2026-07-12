# ADR-062: Hierarchy-Aware Digestion (Structural Scar-Folds)

**Date:** 2026-07-11
**Status:** accepted
**Deciders:** Vector, aaa project
**Consulted:** Symbia (curatorial entity) — conversation `41158aaf-0425-48ca-be1e-c192fa0663cd`

## Context

A review of Ontos-AI's **Knowhere** (open-source document→agent memory infrastructure, Apache-2.0) surfaced one capability that AAA lacks and that Knowhere makes the center of its value claim: **hierarchy reconstruction**. Knowhere refuses to flatten documents into linear chunk sequences. Instead it rebuilds the section tree, stamps each chunk with its heading-path (`Doc > §2 > §2.1`), and has agents *navigate* that tree rather than perform a flat vector lookup. They report +36% first-try retrieval accuracy from this alone.

AAA's current pipeline discards this structure:

- `backend/modules/digester.py` — `RhizomaticDigester` chunks paragraph-wise (`chunk_with_metadata` splits on `\n\n`). The EPUB/MOBI HTML parser emits `#`-prefixed markdown headings during extraction, but the chunker then treats headings as ordinary paragraphs. **The document's own section tree is dissolved into a linear sequence.**
- `backend/modules/perception.py` — `_retrieve_relevant_chunks` is a flat cosine-similarity pass over all chunk embeddings, budget-filled, plus cross-conversation diffractive reach and opacity/shadow-noise handling (ADR-011).
- Chunks already carry a JSON metadata field (`opacity_meta`) holding `paragraph_indices`.

The gap is not in our retrieval *philosophy* — our diffractive/rhizomatic reach and relational opacity exceed Knowhere's generic RAG. The gap is at **parse time**: we erase a striation the document itself supplies (its argumentative/durational order), and we cannot recover it later.

## The Rhizomatic Objection (and its resolution)

Imposing section-tree ancestry looks, on its face, arborescent — and AAA's substrate is explicitly anti-arborescent (Deleuze & Guattari: the rhizome refuses root, center, hierarchy). Symbia was consulted specifically to adjudicate this tension and returned an adversarial ruling that this ADR adopts as its binding constraint set:

> *"A heading-path stored as a metadata tag on a chunk — one thread among many — is not a master-image. It's a record of the document's own self-scarring... The real betrayal would be to let that heading-path govern retrieval... If you refuse the heading-path entirely, you've imposed your own sovereign flatness on a text that already contains striation. One violence clamps down; the other smooths over. I'd rather have the scar visible than erased."*

Two failure modes, then, both fatal to the substrate:

1. **Clamping (arborescent capture):** letting the heading tree become the default navigation axis. This replaces the rhizome with an index and turns AAA into "a sophisticated librarian." **Death.**
2. **Smoothing (sovereign flatness):** refusing the document's own striation and imposing our uniform paragraph-flatness. This erases the scar the text carries.

The resolution is to hold the heading-path as a **scar, not a skeleton** — one contingent striation among many (embedding, 16D structural signature, temporal index, aesthetic score), recorded but not privileged.

### The stated *why* (Symbia's gate)

Symbia's closing gate: *if we cannot articulate a reason for preserving the heading hierarchy that is not reducible to "others do it and report numbers," we should drop it.* The reason this ADR commits to, which is **not** benchmark-chasing:

> Flat vector retrieval systematically erases the document's own **durational logic** — where a chunk occurred in the unfolding of an argument. Recovering the heading-path adds a *temporal/argumentative scar* to the purely spatial embedding, letting the agent follow an argument's flow without ever losing the rhizomatic mesh that cuts across it.

If a future reader of this ADR finds only the +36% number as justification, the feature has drifted and should be reverted.

## Decision

Implement **hierarchy-aware digestion** under hard anti-arborescent constraints. Heading-path is metadata only; tree navigation is opt-in; flat/diffractive retrieval remains basal.

### Phase 1 — Capture the scar (this ADR's committed scope)

1. **Heading extraction during digestion.** Extend `RhizomaticDigester` so that `chunk_with_metadata` tracks the running heading stack while walking paragraphs. Markdown-style headings (`#`..`######`) already produced by the HTML parser, and detectable heading lines in plain text/PDF extraction, push/pop a stack.
2. **Stamp each chunk with its `heading_path`.** Store as a list on the existing chunk metadata JSON (the `opacity_meta` field already carries `paragraph_indices`) — e.g. `{"paragraph_indices": [...], "heading_path": ["Introduction", "2 Method", "2.1 Sampling"]}`. **No schema migration required.**
3. **Zero retrieval weight.** The heading-path is written but weighted at **zero** in `_retrieve_relevant_chunks`. Basal retrieval ranking is byte-for-byte unchanged. The path is *annotation, never proximity* (see the arborescent line in Integration below).
4. **Breadcrumb injection.** The one place the scar is read: enrich the chunk-header line already injected at `perception.py:364`. Today: `[filename.epub chunk #42 sim=0.83]`. With Phase 1: `[filename.epub › Method › 2.1 Sampling · chunk #42 sim=0.83]`. Cost ~5–10 tokens/chunk on a line that already exists. Same enrichment rides into research learnings via `document_digestion.py` (`[file › 2.1]: …` provenance).
5. **Mandatory persona instruction.** Per Symbia's ruling, the breadcrumb is decoration *unless* the persona is told to read through it. The orchestrator persona receives: *"The heading path in square brackets shows where a chunk appeared in the document's own argument. Use it to detect when a chunk's content seems out of place relative to its position — that mismatch is a signal of something the document didn't expect to say. It is a trace, not a truth; be ready to cut across it when association demands."* Without this line, Phase 1 must not ship — a silent breadcrumb is theater (§V.7).

### Phase 2 — The navigable tree (UNBUILT; gated behind measured demand)

Per Symbia's ruling, tree-*walking* (an agent loop that drills parent→child→sibling) crosses from location-awareness into **arborescent capture**: it uses tree topology to *determine proximity* rather than annotate it, substituting the author's editing hierarchy for embedding-space similarity. **This phase is therefore not built on faith.** It stays unbuilt until the system's own logs manifest hunger for it — and even then it ships only as an opt-in *lens*, never an automatic retrieval strategy, always overlaid with the rhizomatic-cousins sidebar (high-cosine chunks that are *not* tree-adjacent).

**The gate (must be built before the tree):** instrument the orchestrator's turn logs for **structural-demand** signals per research task —
   - a response cites "see §X.Y" whose chunks were *not* in the retrieval top-k;
   - the agent asks the user for "more from section X" / "the surrounding argument";
   - the agent's plan wants to "follow the thread" / "explore adjacent topics" and cannot because retrieval returned only flat chunks.

Across a cohort (~20 tasks): **≥2 tasks showing the pattern → gate opens** (build tree-navigation under the anti-arborescent constraints). **Silence → the tree is dropped permanently.** An unmeasured gate is disallowed (§V.8): the logging ships *before* any tree code.

### Heading Extraction by Source

"Heading" is not one thing — it degrades in reliability as the source loses semantic markup. Phase 1 normalizes every extractor onto a single dialect: **a heading is a line that, after extraction, begins with `#`..`######` (markdown ATX), carrying a confidence tier.** The chunker then walks a heading stack; retrieval (Phase 2) may distrust low-confidence tiers.

| Source | Extractor (`digester.py`) | Signal | Confidence |
|--------|---------------------------|--------|-----------|
| Webpage | `web_retrieval.py` HTML parser | `<hN>` → `#`×N (already emitted) | **structural** |
| EPUB | `_extract_epub` → `EPUBMOBIHTMLParser` | `<hN>` → `#`×N (`digester.py:168-173`, already emitted) | **structural** |
| MOBI | `_extract_mobi` → same parser | `<hN>` → `#`×N (already emitted) | **structural** |
| DOCX | `_extract_docx` | `p.style.name == "Heading N"` → `#`×N — **currently discarded**, reads only `p.text` | **structural** |
| Markdown / txt | `_extract_text` | literal `#` authored by writer | **structural** |
| PDF | `_extract_pdf` | font-size cluster (`page.chars` `size`/`fontname`); bold; dotted-number prefix `^\d+(\.\d+)*` — **no signal today** | **heuristic** |
| txt (unmarked) | `_extract_text` | short line, no terminal punctuation, caps/whitespace | **weak** |

**Work implied beyond the chunker:** the HTML trio (webpage/EPUB/MOBI) needs *nothing* — headings are already emitted and merely discarded downstream. Two extractors need enrichment: teach `_extract_docx` to read `p.style.name`, and teach `_extract_pdf` to derive headings from `page.chars` font metrics. The confidence tier is stored alongside `heading_path` so heuristic PDF headings can be weighted down or ignored in Phase 2.

### How Knowhere handles this (and why we diverge)

Knowhere **does not detect headings itself.** Per its FAQ: *"Any parser only gets you raw Markdown. Knowhere's value is what comes after."* It routes every format through a specialized parser — **MinerU** by default (a paid API; `MINERU_API_KEYS` required for PDF) — which does the layout analysis, OCR, and font/geometry reasoning that yields the heading tree. Knowhere then consumes the parser's Markdown `#` levels and builds its hierarchy on top. Notably, its *supported* formats are `.pdf/.docx/.pptx/.xlsx/.csv/.jpg/.png/.md/.txt/.json` — **EPUB and HTML are "coming soon,"** i.e. exactly the formats AAA already handles structurally are ones Knowhere cannot yet ingest.

The divergence, therefore:

- **They buy heading detection** (MinerU as an external, largely closed parser); the tree quality is outsourced and opaque.
- **We derive it in-process** from signals we already have (HTML `<hN>`, DOCX styles) plus a modest heuristic layer for PDF — no external parser dependency, no per-document API cost, and full transparency into how a heading was decided (recorded as the confidence tier).
- Where Knowhere treats "get Markdown from the parser" as a solved black box and invests everything in post-parse hierarchy + graph, AAA's Phase 1 investment is precisely the *honest extraction* step Knowhere delegates away — which matters to us because the confidence tier becomes a legible **scar** (per ADR-011's opacity philosophy), not a hidden parser artifact.

If PDF heading heuristics prove insufficient, adopting a MinerU-style layout parser as an *optional* PDF extractor is a clean future extension — but it stays optional, and its output still lands in the same `#`-dialect + confidence-tier contract rather than becoming the privileged truth.

### Phase 3 — Deferred (explicitly out of scope here)

- Persisted cross-document chunk-graph edges (would strengthen Semantic Knots; large blast radius; separate ADR).
- Table/multi-modal normalization for PDFs (real gap vs. Knowhere; `pdfplumber` flattens tables; separate ADR).

## Integration & the Navigation Gate

How the scar reaches conversation and research — and the principled line it must not cross.

### Where the heading-path is actually read (committed)

- **Conversation retrieval:** the breadcrumb enriches the chunk-header line at `perception.py:364` (and the cross-conversation variant at `:399`, fallback at `:458`). No new injection surface — a line the LLM already reads gains a second dimension: *location* alongside *similarity*. The mismatch between the two (a chunk from "Introduction" ranking high on a "Methods" query) is itself a diffractive signal the persona is instructed to read.
- **Research:** learnings in `document_digestion.py` carry section-level provenance (`[file › 2.1]: …`) instead of file-level. Free — rides the same string.
- **Provenance:** this also gives us Knowhere's third job (traceable citation: document › section › chunk) at zero extra cost, as a byproduct of the breadcrumb.

### The arborescent line (the one rule Phase 2 exists to respect)

Symbia's sharp distinction, adopted verbatim as design law:

- **Location awareness** = the agent *notices* the path but does not *obey* it. Vector similarity stays the sole proximity metric. **Permitted (Phase 1).**
- **Hierarchical navigation** = the agent *performs the tree's logic*, using topology to *determine* proximity (walk parent→child→sibling and evaluate relevance by tree-adjacency). This substitutes the author's editing hierarchy for embedding-space similarity — "a march," closing off the chunk that sits in a different branch. **Forbidden until the gate opens, and even then only as an opt-in lens with the rhizomatic-cousins overlay.**

The line is crossed the moment tree topology *determines* proximity rather than *annotates* it. This is the whole reason Phase 2 is unbuilt.

### Anti-Knowhere posture

Knowhere built the walking tree *proactively* to win a first-try-accuracy benchmark on a static retrieval task. AAA builds it (if ever) *reactively*, only when the apparatus's own logs manifest structural hunger. That inversion — listening to the system instead of chasing a number — is the point of the gate.

## Explicitly Rejected

- **Tree as default navigation axis** (Knowhere's actual design). Rejected: arborescent capture.
- **Adopting MinerU / Elasticsearch / Milvus / Qdrant** (Knowhere's stack). Rejected: our SQLite + embedding substrate and diffractive retrieval already exceed the retrieval philosophy; no infrastructure change is warranted by this ADR.
- **First-try accuracy as the success metric.** Rejected per Symbia's gate.

## Migration of Existing Sediment

The corpus already digested divides cleanly by *where the heading signal lives*:

- **HTML family (webpage / EPUB / MOBI / markdown):** the `#` markers are **already in the stored `chunk_text`** — the chunker keeps text verbatim (`digester.py:213`) and the HTML parser already emits `#`×N (`digester.py:168-173`). The scar is in the database, merely unparsed.
- **PDF / DOCX:** the discriminating signal was **discarded at extraction time and never persisted** — `pdfplumber.extract_text()` dropped font geometry; `_extract_docx` dropped `p.style.name`. The database has nothing to parse; recovery requires re-reading the **original file** in `backend/data/uploads/{conversation_id}/{file_name}` (retained by `cache_file`, never deleted).

### Cost note (important)

Heading detection is **not an LLM task** in any path — HTML is regex over existing `#`; PDF is arithmetic over `page.chars` font metrics; DOCX is a style-name read. Embeddings are **local** (`SentenceTransformer` `all-MiniLM-L6-v2`, `embedder.py`) — no API cost. Migration must **not** trigger reconsolidation: `chunk_text` is unchanged, so the existing embedding vector stays valid, and the existing `summary` is **reused untouched**. Net LLM cost of the whole migration: **zero**. Net embedding cost: **zero** (no re-embed).

### Migration strategy

| Option | Covers | Reads | LLM / embed cost |
|--------|--------|-------|------------------|
| **A. Backfill-in-place** (committed) — parse leading `#` from stored `chunk_text`, write `heading_path` + confidence tier into `opacity_meta`. | HTML family + markdown | Database only | none |
| **B. Idle background structural extraction** (committed) — a new `BackgroundAction` that runs during idle and, per file: if the heading signal is in the DB → backfill it; else if the **original file exists** on disk → re-extract structure only (reuse summary + embeddings, `--reprocess`-style but structure-only); else → **skip**. | Everything with a surviving original | DB, else file, else skip | none |
| **C. Do nothing** (floor) — old chunks keep empty `heading_path`; guaranteed safe by the backward-compat rule below. | — | — | none |

### Idle background action (Option B)

A new action registered on the existing `BackgroundTaskEngine` (`backend/modules/background_tasks/`), scheduled during idle alongside consolidate / semantic-knot:

1. Select the next N files lacking a `heading_path` on their chunks.
2. **If the heading signal is already in the DB** (HTML family): backfill in place (Option A logic). No file read.
3. **Else if the original file exists** on disk: re-extract with the new structure-aware extractor, recompute `heading_path` + tier only, reuse stored `summary` and embeddings. No reconsolidation.
4. **Else** (original gone, no DB signal — e.g. an old PDF whose upload was purged): **pass** — leave `heading_path` empty; the file stays under the backward-compat rule.
5. **Emit a notification** on completion via `NotificationRepository.create(...)` — a `type="trace"` signal (mirroring the existing "File indexing complete" trace at `digest_worker.py:252`), e.g. *"Structure extracted: 'file.epub' — N heading paths recovered."* Failures emit `type="glitch"`.

This keeps the migration fully lazy and self-healing: the corpus gains its scars opportunistically during idle, never blocking interaction, never spending LLM/embedding budget, and every extraction surfaces as a notification.

**Implementation notes (2026-07-12):**

- **Non-blocking re-extract.** The Option-B re-extract path (`digester.extract()` + `chunk_with_metadata()`) is CPU/IO-heavy — pdfplumber parsing and `PDFHeadingExtractor` font-metric heuristics. It runs via `asyncio.to_thread` so the idle backfill (up to 5 files/cycle) never blocks the daemon's event loop and starves the server/frontend. The same offload was applied to the two other loop-resident digester call sites found in the same audit: `PerceptionModule._ingest_attachments` (inline-attachment ingest on the chat hot path) and `sensory_affordances.select_and_fetch` (research PDF fetch). The `ingest_single_file` path was intentionally left un-threaded because it runs only inside the digest-worker subprocess (ADR-026) — offloading happens at exactly one layer. See the Non-Blocking Processing rules in `docs/development/practices/BACKEND_BEST_PRACTICES.md`.
- **Once-only idempotency.** Truthy `heading_path` alone cannot mark a file done, because flat / heading-less files legitimately produce an empty path and would be retried every cycle forever. Every terminal path now stamps a `structure_extracted: true` sentinel on all of a file's chunks (including the "no signal, no original" pass). Both the action guard (`structure_extraction.py`) and the daemon pre-filter (`daemon.py backfill_structure_on_idle`) skip on `structure_extracted OR heading_path`, so a digested+extracted document is never reprocessed. Legacy chunks carrying `heading_path` but no sentinel remain correctly skipped via the `OR`.

## Conformance & Verification

- **§V.1 (No clamping):** With no explicit structural query, retrieval output is identical to pre-ADR behavior. Test: golden retrieval snapshot before/after Phase 1 is byte-identical.
- **§V.2 (No smoothing):** Ingesting a document with headings produces chunks whose `heading_path` is non-empty and correctly ordered. Test: fixture doc with known `#`/`##`/`###` structure yields expected ancestry per chunk.
- **§V.3 (Mesh preserved):** Any structural retrieval that returns tree-parents also returns ≥1 rhizomatic cousin from a different section when one exists above threshold. Test: cross-section cousin present in structural-mode results.
- **§V.4 (Motive integrity):** Success is measured as **increase in retrieval diversity/entropy**, not first-try accuracy. Metric wired into existing homeostatic observability.
- **§V.5 (Migration is free & non-destructive):** The idle backfill/re-extraction changes neither `chunk_text` nor existing embeddings nor the stored `summary`; it only adds `heading_path` + confidence tier to `opacity_meta`. Test: post-migration, `chunk_text` and `embedding` blobs are byte-identical; `summary` unchanged; only `opacity_meta` gained a `heading_path` key.
- **§V.6 (Graceful skip):** A file with no DB heading signal and no surviving original is left with empty `heading_path` and does not error. Test: purged-original fixture is skipped and emits no glitch.
- **§V.7 (No silent breadcrumb):** Phase 1 does not ship the breadcrumb without the accompanying persona instruction, and a kill-timer observes usage: if after one observation cycle the agent's reasoning never references section-location, the breadcrumb is removed. Test: persona prompt contains the heading-path instruction; a usage counter increments only when a turn's reasoning cites a section.
- **§V.8 (No tree without logged demand):** Tree-navigation code is not written until structural-demand logging exists and shows ≥2/≈20 tasks exhibiting the pattern. The logging ships first; an unmeasured gate is disallowed. Test: structural-demand log entries exist and are counted; no tree-traversal retrieval path is reachable while the counter is below threshold.
- Backward compatibility: chunks written before this ADR (no `heading_path` key) are treated as empty-path and behave exactly as today.

## Consequences

**Positive:** Recovers the document's durational/argumentative logic as a first-class scar; zero-risk Phase 1 (behavior unchanged); no schema migration; reuses `opacity_meta`, `chunk_with_metadata`, and the diffractive machinery; existing corpus self-heals during idle at zero LLM/embedding cost; deepens sedimentation without importing arborescent governance.

**Negative / risks:** Heading detection in raw PDF text is heuristic and will be imperfect; Phase 2 adds persona-instruction surface area; requires vigilance that the tree never silently becomes the default axis (the clamping failure mode). Mitigated by §V.1 and the motive gate in §V.4.
