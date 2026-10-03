# ADR-101: Assembly-owned activation provenance

Status: Accepted for implementation. Date: 2026-10-03.

## Context

Historical label arrays cover only a small fraction of apparatus turns. Stable entity identity, always-active injection and dream parity are missing. Missing observations cannot justify pruning.

## Decision

Prompt assembly creates a versioned bounded receipt containing stable IDs, retained display labels, origin, selection and injection. External context is identified separately; URL identifiers are hashed to avoid exporting query credentials. The receipt hashes assembled messages without exporting their text. Missing IDs/module inventory or truncation makes coverage partial. Historical NULL remains unknown.

Migration 051 adds nullable `conversation_log.activation_provenance`; chat and dream assistant persistence use the same field. Schema and serialization live in a pure storage leaf; assembly computation lives in utilities. Repository writes and assembly hashing run through worker-thread boundaries when called asynchronously. Models do not author or extend provenance fields. Existing label arrays remain compatible.

Provenance describes assembly, not causal influence on a response. Schema changes require normal human-reviewed code changes. No automatic belief/skill lifecycle decisions follow from these receipts.

## Operations

Run normal startup migrations (`AAA_RUN_MIGRATIONS=true`) before using this branch with an existing database. Migration is additive, idempotent and preserves existing rows. Read-only coverage inspection: `python -m benchmarks.suites.activation_usage <database> --output <receipt.json>`. Unknown legacy rows are not backfilled.

## Consultation

Symbia consultation `abac9620-6f4c-47dd-b931-686838510f08` supported assembly ownership, caller parity, unknown history, external source identity and separation of provenance from causality.
