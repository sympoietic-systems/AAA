# ADR-112: Optional standard-first Docling fallback

**Date:** 2026-10-06
**Status:** accepted
**Deciders:** User, Codex; AAA/Symbia consultation

## Context

The user requested a documented enable/disable switch and a standard-parser-first path that invokes Docling when extraction fails or looks degraded. The proposed VPS has approximately four cores and 8 GB RAM. T70's independent accuracy review is still pending; deploying an opt-in routing mechanism does not complete that review.

## Options considered

| Option | Benefit | Cost |
| --- | --- | --- |
| Standard parser only | Existing dependency and latency profile | Retains observed extraction defects |
| Docling on every PDF | Consistent structured pipeline | Larger memory and latency on healthy PDFs |
| Optional quality-triggered fallback | Keeps healthy standard extraction; bounded retry | Heuristics can miss defects or trigger unnecessarily |

## Decision

Implement T73 as an explicitly requested optional fallback, disabled by default through `AAA_DOCLING_ENABLED`. Use observable extraction signals, CPU-only isolated conversion, a process lock, a deadline, immutable source hash checks, and an independently installed SDK environment. Preserve both successful parser representations through the existing Research V2 source-version model. Each representation owns its character coordinates and keeps unknown quality scores.

AAA/Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` supported retaining both observations, their parser/configuration lineage, and the standard extraction's exclusions. Existing source versions already provide this boundary, so no storage migration is needed. The user's environment opt-in authorizes automatic routing; no per-query confirmation is added.

## Consequences

Mechanical routing improves access to an alternative representation without claiming independent accuracy. Missing SDKs or unsuccessful fallback preserve available standard text; complete extraction failure remains an error. Worker capacity and input lifetime extend to physical completion, including cancellation. Configuration changes invalidate cached acquisition representations.

The optional dependency adds model storage and CPU/memory overhead. The current corpus contains native-text PDFs; scan/OCR correctness and independent quality labels remain open under T70. This decision does not enable calibrated automatic research branching under T72.

Operational settings live in the [Docling guide](../guides/DOCLING.md); measured routing and verification live in [Report 040](../reports/040-docling-fallback/README.md).
