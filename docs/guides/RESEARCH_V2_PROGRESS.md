# Research V2 implementation progress

Snapshot: 2026-10-07, Research V2 rollout. Root [SPEC.md](../../SPEC.md) owns task status. The [research contract](../systems/RESEARCH_SPEC.md) owns requirements. This guide connects the completed implementation to its operating instructions and verification records; the user will deploy and review research quality in production. See [rollout instructions](RESEARCH_V2_ROLLOUT.md).

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
| T69 | Jev comparison completed; candidate not adopted for research selection; standard selector restored | [Report 042](../reports/042-jev-experimental-promotion/README.md) |
| T70 | Bounded native/OCR parser comparisons and three-arm review; no default promotion; independent scan review deferred to T75 | [Report 043](../reports/043-parser-evaluation/README.md) |
| T71 | Repository verification, automated NVIDIA comparison and explicitly authorized assumption-based rollout | [Report 044](../reports/044-research-release-evaluation/README.md) |
| T72 | Unchecked Allow branching checkbox, frozen dispatch consent and bounded witnessed child gathering | [ADR 113](../decisions/ADR-113-research-v2-authorized-rollout.md) |
| T73 | Optional standard-first Docling PDF fallback with bounded CPU worker and preserved parser observations | [Report 040](../reports/040-docling-fallback/README.md) |
| T74 | Automated provisional source labeling, checkpointed resume, explicit annotator provenance | [Report 041](../reports/041-research-provisional-labeling/README.md) |

Reports describe verification at each task's completion. Their test counts overlap and must not be added together. Later implementation can extend behavior described by an earlier report; for example, T67 stopped at proposal approval and T68 added child execution.

## Operator settings and boundaries

Subresearch defaults to `off`. An explicit per-task `propose` request can create a review checkpoint after qualifying source contact; approval authorizes the reviewed child scopes and allocations. Exactly two child lines gather under their parent's deadline and shared resource ceilings. Children cannot create grandchildren or perform final synthesis. NVIDIA reservations use the configured zero-price assumption; other provider ceilings must be configured as described in Report 039 before family calls are admitted. Missing billing metadata remains unknown.

Checking **Allow branching** at creation explicitly requests `bounded_auto`. Trusted user dispatch freezes a covenant allowing at most two qualified children under the parent deadline and shared resource limits. Source witnesses and separated scopes remain required. Restart does not renew consent. Model-authored tasks cannot request this mode. The user authorized this rollout before independent branch calibration; that calibration remains unknown. The [manual-mode guide](RESEARCH_MANUAL_MODE.md) covers phase stepping; proposal review is a separate durable checkpoint.

PDF extraction uses pdfplumber first. `AAA_DOCLING_ENABLED=false` is the default. Follow the [Docling guide](DOCLING.md) to install its separate environment, configure interpreter/model paths, and enable fallback. A degraded or failed standard extraction may invoke the CPU worker; unsuccessful fallback retains available standard output. Both successful parser observations retain separate source versions and character coordinates. A parser route is not an independent accuracy label.

Use [JSON export/import](RESEARCH_EXPORT_IMPORT.md) to preserve durable provenance. Imported evidence and child archives do not confer execution authority or recreate approval. Existing tasks retain their frozen policy rather than adopting new defaults silently.

## Remaining evaluation gates

The [automated labeling command](RESEARCH_LABELING.md) prepares provisional source annotations and preserves per-query failures for resume. Its default calibration gates remain strict. The user withdrew T69 experimental activation after reviewing the abstentions; research selection uses the standard selector. Independent quality review remains a limitation of the authorized rollout. See [Jev operating instructions](RESEARCH_JEV.md).

| Task | Work still required |
| --- | --- |
| T75 (future TODO) | User-deferred genuine scans and independent parser references/review; OCR/specialists, VPS resource/cost/model-license certification |
| Production quality review | Compare source support, useful coverage, contrary retention and branch value using independently reviewed cases. No claim of quality superiority is established. |

The supplied PDF corpus enabled local native-text routing checks and a side-by-side review packet. It contains no genuine scanned-PDF test case and has not received independent accuracy labels; the user deferred those requirements to future T75 on 2026-10-07. T73 is the separately authorized opt-in mechanism; its routing checks do not establish independent parser accuracy or a general speedup.

Live LLM testing/debugging uses NVIDIA under the user's instruction. The user separately authorized Jev's endpoint for the T69 comparison. Local Docling conversion uses document models on CPU and makes no LLM provider call.

Repository verification and rollout evidence are recorded in [Report 044](../reports/044-research-release-evaluation/README.md). Backend lint, formatting, configured strict typing and the complete backend suite pass. Frontend typing, tests, build and the configured lint ratchet pass. Raw frontend ESLint still reports accepted legacy debt; this is not a zero-error frontend certification.

The final NVIDIA replay produced a legacy report and a V2 partial result after an execution timeout. Its single captured-source case does not establish better research or full production latency. V2 action receipts are enabled for new tasks; persisted tasks retain their policy. Jev stays disabled, Docling stays default-off, and branching stays off unless selected at creation. No VPS deployment has been performed.
