# Research V2 implementation progress

Snapshot: 2026-10-06, branch `codex/research-v2`. Root [SPEC.md](../../SPEC.md) owns task status. The [research contract](../systems/RESEARCH_SPEC.md) owns requirements. This guide connects the completed implementation to its operating instructions and verification records; it does not certify a deployed VPS or a finished release.

## Implemented and tested

| Task | Current capability | Verification record |
| --- | --- | --- |
| T62 | Durable action receipts, frozen task policy, restart/replay lineage | [Report 033](../reports/033-research-receipt-baseline/README.md) |
| T63 | Bounded provider attempts, cancellation and late-result rejection, explicit partial outcomes | [Report 034](../reports/034-research-provider-reliability/README.md) |
| T64 | Source versions, exact representation spans, claims, contrary links, exclusions, export/import provenance | [Report 035](../reports/035-research-evidence-substrate/README.md) |
| T65 | Shared fetch clients, bounded acquisition workers, origin-aware cache and deadlines | [Report 036](../reports/036-research-acquisition/README.md) |
| T66 | Finite action scheduling, prerequisites, persisted routing decisions, witnessed reflection guards | [Report 037](../reports/037-research-finite-actions/README.md) |
| T67 | Durable human branch proposals, source review, edited approval, decline and expiry | [Report 038](../reports/038-research-branch-proposals/README.md) |
| T68 | Approved isolated child gathering, shared family budgets, raw-evidence archives, parent-owned merge | [Report 039](../reports/039-approved-research-children/README.md) |
| T73 | Optional standard-first Docling PDF fallback with bounded CPU worker and preserved parser observations | [Report 040](../reports/040-docling-fallback/README.md) |

Reports describe verification at each task's completion. Their test counts overlap and must not be added together. Later implementation can extend behavior described by an earlier report; for example, T67 stopped at proposal approval and T68 added child execution.

## Operator settings and boundaries

Subresearch defaults to `off`. An explicit per-task `propose` request can create a review checkpoint after qualifying source contact; approval authorizes the reviewed child scopes and allocations. Exactly two child lines gather under their parent's deadline and shared resource ceilings. Children cannot create grandchildren or perform final synthesis. Monetary provider ceilings must be configured as described in Report 039 before family calls are admitted. Missing billing metadata remains unknown.

`bounded_auto` remains gated by independent evaluation. Enabling manual stepping, approving a proposal, or enabling Docling does not authorize automatic branching. The [manual-mode guide](RESEARCH_MANUAL_MODE.md) covers phase stepping; proposal review is a separate durable checkpoint.

PDF extraction uses pdfplumber first. `AAA_DOCLING_ENABLED=false` is the default. Follow the [Docling guide](DOCLING.md) to install its separate environment, configure interpreter/model paths, and enable fallback. A degraded or failed standard extraction may invoke the CPU worker; unsuccessful fallback retains available standard output. Both successful parser observations retain separate source versions and character coordinates. A parser route is not an independent accuracy label.

Use [JSON export/import](RESEARCH_EXPORT_IMPORT.md) to preserve durable provenance. Imported evidence and child archives do not confer execution authority or recreate approval. Existing tasks retain their frozen policy rather than adopting new defaults silently.

## Remaining evaluation gates

| Task | Work still required |
| --- | --- |
| T69 | Independently labeled held-out source pools, actual Jev comparison, downstream support/coverage review; no Jev promotion yet |
| T70 | Independent parser annotations and review, genuine scan/OCR coverage, measured accuracy/resource/license fit |
| T71 | Integrated release comparison and ablations, reviewed quality/latency/cost evidence, failure/restart evaluation |
| T72 | Automatic branching only after T71 branch calibration and an explicit bounded covenant |

The supplied PDF corpus enabled local native-text routing checks and a side-by-side review packet. It contains no genuine scanned-PDF test case and has not received independent accuracy labels. T73 is the separately authorized opt-in mechanism; it does not complete T70 or establish a general speedup.

Live LLM testing/debugging uses NVIDIA under the user's instruction. The user separately authorized Jev's endpoint for the T69 comparison. Local Docling conversion uses document models on CPU and makes no LLM provider call.

Repository-wide verification still encounters existing failures outside the completed slice. Report 040 records the latest focused passes and global limitations. No production migration, VPS deployment, or release approval is implied by this progress snapshot.
