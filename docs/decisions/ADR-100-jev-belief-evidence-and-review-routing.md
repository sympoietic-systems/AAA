# ADR-100: Jev belief evidence and review routing

Date: 2026-10-03. Status: accepted for dry-run evaluation; runtime promotion withheld.

## Context

The existing tension table has read and update APIs but no semantic producer. Structural vector similarity nominates related territory; it cannot establish contradiction. Proposal triage also needs an explicit evidence boundary while ADR-098 changes belief-engine behavior in another working tree.

## Decision

`BeliefTriage` has no repository or write port. It compares supplied statements through the shared sensory evaluator and emits contradiction, endorsement, orthogonal or abstain evidence with separate contradiction and absorbability estimates. Candidate recommendations request review. No acceptance, rejection, collapse, absorption, folding or commitment follows from Jev output.

Belief pairs are nominated from at most 64 valid 16D vectors, evaluated sequentially with a maximum of 20 pairs. Proposal routing compares at most ten targets. Similarity is recorded separately from semantic evidence. Inputs reject malformed, zero or non-finite vectors and invalid mass. Stored-answer replay produces the same recommendation without another model call.

Mass changes stakes: confidence floor 0.85 at mass ≥0.8, otherwise 0.7. The high-mass band [0.70, 0.85) remains watchlist evidence without an edge. Mass affects priority only; the tension magnitude is the unweighted contradiction estimate. Absorbability confidence gates absorption review separately, so uncertainty about merging cannot suppress strong contradiction evidence. Conflicting relation and contradiction answers abstain.

Prior pair evidence is recorded as provenance but never sent as classifier context. Receipts do not become priors. Fresh classifications can disagree with previous evidence and remain inspectable.

The benchmark CLI reads checkpointed SQLite snapshots with URI read-only mode. Its only matrix application path creates a fresh independent copy; there is no option to update the source. Receipts are written before copy application. The copy validates statement hashes, mass and vector similarity, then atomically upserts qualified contradiction edges. Other relations and proposal-only identifiers cannot create edges. Belief/proposal tables stay unchanged. Existing edges are preserved when new evidence abstains; this is an evidence producer, not an ontology repair process.

Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` required separation of measured signal from mass priority, a watchlist band, prior evidence outside model context and reported abstention. The implemented service follows those conditions.

## Consequences

The live calibration found unresolved-reference false positives, so runtime integration into the belief engine or commitment filter is withheld. The prototype is usable for inspected evidence and offline review. The existing cosine-only commitment guard remains a known limitation for a future calibrated change. [Report 024](../reports/024-jev-belief-routing-and-tension-report.md) records failures alongside successful wiring and snapshot purity.
