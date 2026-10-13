# ADR-129: Immutable linked belief lineage

Status: accepted for local T16 implementation, 2026-10-13. Production rollout remains T18.

## Decision

Revision does not edit an adopted belief in place. An authenticated operator command creates a new pending proposal with a distinct identity and an immutable `revision` link to its adopted predecessor. The candidate starts with zero mass and confidence and carries no copied evidence. Its decision binds the new statement hash; the link records the predecessor hash, operator command and timestamp. The predecessor statement, adoption receipt, assessments and dissent remain available without alteration. A revision cannot adopt its own candidate.

Supersession requires a distinct, currently adopted target plus current source and target statement hashes and review versions. It changes only the source's canonical standing to `superseded`, while retaining the original adoption receipt and content. The immutable link records both statements' hashes and the command decision. Direct state writes cannot supersede outside this linked workshop path.

Resurfacing appends an operator command and decision while preserving the current adopted/superseded standing. It rejects assessment links and changes no statement, mass, confidence or warrant. Re-surfacing is attention history, not evidence.

Migration 069 adds an immutable, agent-scoped link table. No historical records are semantically reclassified and no legacy links are inferred. Merge remains deferred because it destroys distinctions without a separately reviewed merge contract. Application rollback disables these new commands while retaining schema and lineage history.

## Philosophical grounding

The adopted belief remains a historically situated node, not mutable text. A revision creates another node in relation to it, keeping prior warrant and dissent addressable. Resurfacing marks renewed attention without presenting that attention as new evidence. Operator provenance uses the existing authenticated shared-credential contract; no cryptographic or individual identity is fabricated. Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` supported immutable prior nodes, typed lineage, retained dissent, no silent merge and no warrant from resurfacing. Her suggestion to hash a distinct operator identity is not adopted because the current credential does not identify separate people.

See [BELIEF_SPEC](../systems/BELIEF_SPEC.md), [contract](../architecture/BELIEFS_V2_CONTRACT.md) and [operator guide](../guides/belief-workshop-review.md).
