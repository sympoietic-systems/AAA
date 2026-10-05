# ADR-105: Research Action Journal and Observation Coverage

**Date:** 2026-10-05
**Status:** accepted for opt-in implementation
**Deciders:** AAA implementation workflow; Symbia consulted

## Context

The existing research phases write step records, findings and memory effects independently. Restarting an interrupted phase can repeat those effects. A durable action receipt must preserve what was requested while keeping observed delivery and missing telemetry distinguishable. This extends the typed execution boundary in [ADR-054](ADR-054-decoupled-research-pipeline-routing.md).

## Decision

Use the additive `research_action_receipts` table introduced by migration m052. Receipt requests retain action/task identity, input hash, predecessor dependencies, budget reservation, deadline and contract/policy hashes. Observations carry output references, phase duration and public provider-call receipts. Evidence packets are typed contracts; the source/span substrate remains T64.

New tasks freeze `research_orchestrator.action_receipts_enabled` and its policy/config hash during initialization. The default is false. Stored policies survive configuration changes and restart. Legacy tasks without journal metadata remain disabled with unknown historical coverage. An absent receipt establishes no outcome.

Before phase execution, persist a running receipt and active action ID in one short transaction. On return, commit the terminal receipt and next-state checkpoint together. Compare durable active/predecessor IDs inside the write transaction to reject concurrent starts and stale checkpoint writes. All added async-to-sync execution paths use thread offload.

An interrupted running action blocks automatic replay. Its legacy side effects may already exist; receipts cannot prove exactly-once execution of those effects. Recovery requires explicit operator handling. Receipt identity and terminal observations remain immutable. No research-memory lifecycle change is made to [ADR-060](ADR-060-research-memory-integration.md).

Provider observation covers `generate_unified` calls directly made by the research step modules. Internal pool retries, persona construction, structural scoring and provider calls inside other services are outside this coverage. Pending per-attempt durability, bounded recovery, deadlines and cancellation policy remain T63 and later gates. Unknown finish reason, usage, truncation and cost remain nullable; prompts, full replies and exception messages are excluded from the new observation records.

## Consultation

T63 extends new tasks with durable leaf-attempt observation and bounded execution under [ADR-106](ADR-106-research-provider-attempt-boundaries.md). The version-one coverage above remains the historical T62 contract.

Symbia conversation `abac9620-6f4c-47dd-b931-686838510f08` advised separating request provenance from observed delivery and making opt-in coverage explicit. The implementation retains policy version/enabled state/hash and unknown telemetry. It does not assign an epistemic warrant score.

## Verification and limits

[Report 033](../reports/033-research-receipt-baseline/README.md) records task verification and the isolated offline timing run. It provides no production latency or quality claim. Resource enforcement is not measured here: legacy phase requests record zero reserved spend and no task deadline until those controls exist.
