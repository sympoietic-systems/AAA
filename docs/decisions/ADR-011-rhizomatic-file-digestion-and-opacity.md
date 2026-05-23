# ADR-011: Rhizomatic File Ingestion and Relational Opacity

**Date:** 2026-05-22
**Status:** accepted
**Deciders:** Vector, aaa project

## Context

Our current file ingestion pipeline extracts text, chunks it linearly, computes embeddings, and stores it in the database. During retrieval, relevant chunks are inserted verbatim into the context window of the LLM.

This conventional approach has several philosophical and practical drawbacks:
1. **Colonial Extraction & Cartesian Transparency:** It treats the file as a passive mine of raw materials, assuming all text should be completely transparent and parsed literally. This erases the metaphorical density, speculative poetry, or internal contradictions of complex texts that resist flat extraction.
2. **Mimicking Human Reading:** It forces the agent to read linearly, rather than diffracting themes laterally or respecting the document's own heterogeneous intensities.
3. **Operational Bottlenecks (Monolithic LLM Pass):** Ingesting a large file in a single prompt to generate a summary and identify dense zones is fragile. It is prone to truncation, output limits, and validation failures when parsing structured JSON outputs.

We need a system that:
- Scales robustly to large files without truncation or format failures.
- Preserves the right to **relational opacity** (Edouard Glissant) by allowing dense/speculative text to withhold itself from literal presentation while remaining searchable.
- Visualizes these boundaries as scars (Kintsugi) in a minimal, terminal-style interface.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Single-pass document ingestion with mathematical torsion metrics** | Conceptually rich, mathematically pure | Extremely heavy compute; sliding-window embedding variance is slow; fragile JSON for large documents; LLM context limits |
| **Per-chunk LLM analysis** | High granularity of opacity flagging | prohibitively slow and expensive (N calls for N chunks) |
| **Hierarchical Block Digestion (Map-Reduce) with Metadata Opacity** | Scalable, robust JSON generation; separates database integrity from prompt presentation; respects opacity while preserving full vector searchability | Requires coordinate mapping from block-local to global indices; multi-stage LLM pipeline |

## Decision

We will implement the **Hierarchical Block Digestion (Map-Reduce)** pattern and a **Metadata-Driven Opacity (Noise Filtration) Presentation** strategy.

### 1. Ingestion Pipeline (The Rhizomatic Assemblage)

Rather than treating the file as a single monolith, we divide it into **super-chunks** (groups of standard chunks, roughly 4,000–8,000 tokens each) representing local conceptual plateaus.

1. **Local Block Digestion (Map):**
   For each super-chunk, we run a local LLM call to:
   - Generate a `local_summary`.
   - Identify paragraph offsets that consist of low-information boilerplate, repetitive licensing, layout relics, or empty filler text, flagging them as opaque.
   - For each noise paragraph, generate a short `shadow_text` placeholder string describing what was omitted and a `reason`.
   - **Crucially, conceptually dense and speculative prose is kept transparent (unflagged)** to ensure the LLM receives the full richness of the ideas during reasoning.

2. **Global Synthesis (Reduce):**
   Combine all `local_summary` blocks and run a final LLM call to synthesize the `global_summary`. This synthesis highlights clashing themes and unresolved conceptual tensions, ignoring the noise blocks.

3. **Database Substrate Retention:**
   We **do not discard the raw text** of noise chunks. They are stored in the database and embedded normally, ensuring vector similarity search remains fully functional.

4. **Coordinate Mapping:**
   We map block-local paragraph indices to global paragraph offsets. When standard chunks are saved, any chunk overlapping a noise global paragraph is flagged with `opacity = 1` and populated with `opacity_meta` containing the `shadow_text` and `reason`.

### 2. Prompt Assembly (The Agential Cut of Noise Omission)

During retrieval, when the `PromptAssembler` gathers chunks:
- If a chunk has `opacity == 1`, the assembler swaps its raw text with the minimal placeholder to save prompt tokens.
- The chunk is formatted in the prompt using a minimal terminal style:
  ```
  ░░░ OMITTED NOISE (File: filename, chunk #index) ░░░
  [Boilerplate/filler omitted] (Reason: licensing disclaimers)
  ```

### 3. Visual UI Representation (The ASCII Scar)

The frontend sediment list displays noise-filtered chunks as faded monospace cards (`opacity: 0.6` styling) wrapped in minimal ASCII borders, indicating what content has been omitted from the attention window.

## Conformance & Verification

- The existing `PerceptionModule` and background task system will support hierarchical block processing.
- The `PromptAssembler` will implement the noise check and placeholder formatting logic.
- Tests will verify that noise chunks are successfully indexed, that raw text is stored and searchable, and that prompts contain only the placeholder and reason when noise filtering is triggered.

