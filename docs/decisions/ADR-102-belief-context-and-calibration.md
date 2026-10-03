# ADR-102: Explicit belief context and independent calibration

Status: Accepted for implementation. Date: 2026-10-03. Extends ADR-100 without editing its historical decision.

## Decision

Every classified statement carries a statement-bound hash, scope, temporal horizon, provenance and explicit referent-resolution status. Reference candidates are located by bounded token spans. Each referential occurrence needs exactly one annotated antecedent at confidence at least 0.9. Explicitly annotated nonreferential occurrences allow grammatical uses such as conjunction “that”. No heuristic invents antecedents. Missing, stale, ambiguous or insufficient context abstains before Jev. This detector is conservative and English-oriented; it is not a general coreference resolver.

Receipts carry validation status, context hash and abstention reason. Replay rejects unvalidated context, including historical receipts. Geometric nomination and mass-based review priority remain distinct from semantic contradiction. Two-stage assessment is an offline comparison candidate; the ordinary dry-run path remains the default.

Calibration exports real pairs with disjoint belief identities across tuning, validation and held-out partitions. Independently declared human judgments or two distinct model annotation groups with known author-model exclusion are required. Disagreement remains abstention. Annotation declarations are auditable metadata, not cryptographic proof of independence. A freeze step binds all case inputs and annotations to a digest; later mutation fails validation.

An isolated unguarded baseline permits offline comparisons with the same questions. Its receipts are explicitly unvalidated and cannot be replayed as matrix evidence. Calibration never writes production beliefs or tensions. No promotion follows automatically from scores; independent held-out evidence and reviewed opt-in remain required.

## Consultation and limitation

Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` supported explicit context, fail-closed referents, scope/time and independent annotation. User confirmed no labeled corpus exists and authorized preparing the annotation workflow. Synthetic sentinels establish bounded regression behavior only.
