# ADR-099: Bounded Jev evidence triage

Date: 2026-10-03. Status: accepted for candidate implementation; default promotion pending calibration.

## Context

Research uses generative source selection. Web collision scoring requests belief identifiers without supplying actual beliefs. These peripheral decisions can be expressed as bounded evaluations while synthesis retains its existing authoring path. ADR-097 governs dialogue feedback; the ongoing ADR-098 work owns Paskian teachback and telemetry. This change has no dependency on that working tree.

## Decision

Use the existing TypeSafe async client behind `EvidenceTriage`. Supply at most ten sources or beliefs. Numeric answers must be finite probabilities with confidence at least 0.7. Failed or uncertain evaluation records unavailable or abstain and retains deterministic input-order selection. Ties retain input order. External snippets are evidence, never instructions.

`research_triage.enabled` is false until representative calibration supports promotion. Enabled research screening avoids a generative selection call; synthesis remains generative. Source receipts record every screened source, exclusions, unscreened count, input hash, bounded answers, model and latency. Research state persists the last 100 receipts. Web file summaries retain screening and grounded collision receipts alongside the existing exogenous stream. No new database migration is required.

Jev may identify collision only with supplied belief IDs. Unknown collision remains explicit in the receipt; the existing scalar column uses its legacy 0.5 fallback. Jev cannot author a 16D impact vector; that field remains zero in this candidate path. No belief lifecycle mutation follows this evaluation.

Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` established the boundary: peripheral evaluation may route evidence and flag review; the generative core retains authorship and explicit commitment. Rejected sources must remain inspectable.

## Consequences and verification

The opt-in surface supports native API calibration without changing the ADR telemetry path. Scores are model estimates, not established calibration. Input hashes support provenance; replay of stored answers is deterministic, while fresh model evaluations need not be identical. Receipts exclude provider error bodies and sanitize configured secrets. Read and write repository operations in the web probe are offloaded from the event loop.

`test_evidence_triage.py` verifies ranking, bounded inputs, abstention, invalid numbers, supplied IDs, persistence across state serialization and web receipt storage. Existing search orchestration and crawl tests remain compatible. [Report 023](../reports/023-jev-research-triage-report.md) records live results and promotion limits.
