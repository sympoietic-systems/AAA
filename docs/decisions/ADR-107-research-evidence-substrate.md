# ADR-107: Research Evidence Substrate

Date: 2026-10-06. Status: accepted for opt-in implementation. Symbia consulted.

## Contract

Receipt-enabled new tasks freeze policy v3 + contract revision 1 atomically. Existing policies retain coverage; disabled tasks retain legacy behavior. Contract revisions cannot remove hard rubric items or increase existing resource ceilings.

m055 stores immutable task-scoped contracts, source versions, exact representation spans, claims and decision receipts. Source version includes representation text hash and parser quality; original byte hash remains unknown unless observed. Unicode offsets count representation characters. Raw-byte coordinates rejected for text-only sources. Segment quality equals source quality; claims retain source lineage and extraction limitations.

Citation resolution and semantic support remain separate. Legacy digest learnings become unverified interpretations with `no_anchor_in_legacy`; no invented supporting quote. Contrary segment references and unresolved objections survive export. Empty acquisition records unavailable evidence with a reason; unknown parser method/score stays null. Selected indexed document context names breadcrumbs, separators and missing original bytes explicitly.

Acquired evidence may survive a deadline. Decision admission requires current running action, active task ownership, unexpired deadline and matching contract/policy hashes. Historical evidence cannot replace current task decisions.

JSON 2.1 includes self-contained evidence; exact `evidence://` locators resolve offline against exported representations. Markdown exposes provenance and support status. Imported evidence preserves original task identity in a read-only archive, without local action receipts or adopted semantic authority. Re-export retains origin identity. Legacy imports acquire no invented anchors.

## Verification and limits

[Report 035](../reports/035-research-evidence-substrate/README.md) owns verification results. Symbia conversation `abac9620-6f4c-47dd-b931-686838510f08`: span matching locates evidence; semantic review independently required; uncertainty and contrary evidence remain visible.

This substrate does not establish calibrated parser quality, semantic support or release readiness. T65 handles acquisition efficiency; T66/T71 enforce scheduling and completion contracts; T70 evaluates parser adoption. No parser-quality score or byte provenance inferred from a successful fetch.
