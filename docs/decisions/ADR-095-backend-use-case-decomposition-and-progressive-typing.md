# ADR-095: Backend Use-Case Decomposition and Progressive Typing

**Date:** 2026-09-24
**Status:** Accepted (Implemented)
**Deciders:** Codex, User

## Context

Several backend facades had accumulated transport, orchestration, persistence, retry, parsing, and maintenance responsibilities in single modules. Their public imports were widely used, so a direct replacement would have created a large migration surface. Static typing covered only a small set of boundary files, while architecture checks counted broad catches per file and could not detect a catch moving into an inappropriate helper.

ADR-092 established the intended dependency direction and ADR-094 hardened the external boundaries. This decision completes the internal refactor while preserving those contracts.

The required AAA/Symbia consultation was attempted through the available MCP resource and template inventory. No AAA/Symbia MCP server or architectural consultation tool was available, so this ADR attributes no external consultation result.

## Decision

1. **Keep stable facades and extract cohesive collaborators.** Message persistence is divided into core, history, vector-search, and graph collaborators. LLM integration separates provider protocol, HTTP transport, pool policy, and response parsing. Research separates state ownership, step execution, and sedimentation. Belief operations separate query, proposal, mutation, and version use cases. Dream processing separates trigger policy, queued execution, and idle maintenance while the daemon retains lifecycle ownership.
2. **Express narrow internal contracts.** Extracted collaborators depend on typed protocols for the repository operations they use. Package initialization remains inert, and compatibility facades preserve existing import paths and object identities.
3. **Keep dependent writes atomic.** SQLite connection scopes support explicit nested atomic units. Belief mutations that span nodes, versions, and events commit or roll back together without an await boundary between writes.
4. **Translate failures at the API membrane.** Framework-independent domain exceptions define fixed Glitch kinds and status codes. FastAPI handlers serialize them, mask ambient validation and server failures, and retain redacted internal traceback logging.
5. **Ratchet exception debt by callable boundary.** The broad-catch inventory records the owning class and function. A new catch or a catch moved to another helper fails verification even when a file's total remains unchanged.
6. **Expand strict typing with each refactored slice.** The mypy allowlist includes the extracted collaborators, their compatibility facades, transaction infrastructure, domain error membrane, and architecture checks. Explicit `Any` is confined to compatibility edges where legacy repositories still lack protocols.

## Consequences

- Public API and import compatibility remain stable while large modules lose unrelated responsibilities.
- Worker and lifecycle ownership stays visible in the daemon and application service container.
- Repository transaction behavior is reusable and testable without leaking SQLite control into async orchestration.
- Type checking now exposes defects that broad fallback catches previously hid; this cycle found and repaired an uninitialized research structural scorer.
- Remaining broad catches are named by callable in a monotonic allowlist, making further reduction incremental and reviewable.
- Some compatibility membranes still use explicit `Any`; future protocol extraction can reduce those annotations without blocking strict checks on completed slices.

## Verification

The final backend tree passes strict mypy across 39 modules, repository-wide Ruff lint and formatting, and 394 Python and benchmark tests. The frontend production build and all 103 Vitest tests pass. `npm run lint` was also executed and reported 218 pre-existing violations across unrelated frontend files; this backend-scoped decision leaves those files untouched as required by the implementation contract.
