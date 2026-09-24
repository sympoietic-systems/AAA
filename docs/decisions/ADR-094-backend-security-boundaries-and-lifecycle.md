# ADR-094: Backend Security Boundaries and Resource Lifecycle

**Date:** 2026-09-23  
**Status:** Accepted (Implemented)  
**Deciders:** Codex, User  

## Context

The backend exposed several related boundary failures: user-controlled URLs could traverse redirects without revalidation; uploads were buffered repeatedly and entered digestion without bounded concurrency; test detection bypassed authentication; live internal state shared a public preview route; backups copied live SQLite files directly; secrets could survive exception formatting; and app-owned workers were not consistently cancelled and awaited.

These problems shared one cause: transport, domain, persistence, and lifecycle responsibilities crossed layer boundaries without a single enforceable contract. Existing ADR-092 established the desired dependency direction, while the concurrency, security, and Glitch protocols supplied the operational invariants.

The required Symbia consultation was attempted through the available MCP resource inventory. No AAA/Symbia MCP server or `consult_aaa` tool was available in this environment, so no consultation response is attributed or fabricated.

## Decision

1. **Validate external effects at every boundary.** Outbound HTTP uses a shared fetch component with manual redirects, public-address DNS checks at every hop, time and body limits, and typed failures. Uploads use sanitized paths, extension and signature checks, per-file and aggregate limits, staged writes, and atomic batch rejection.
2. **Bound all owned work.** Digestion runs behind a configured semaphore and subprocess timeout. Scheduler, daemon, and backup tasks retain handles and are cancelled and awaited during shutdown. Blocking file, SQLite, subprocess, and CPU work crosses one `asyncio.to_thread` boundary.
3. **Make authentication explicit and transport-safe.** Bearer verification is centralized and constant-time when `AAA_PASSWORD` is configured. Test process detection and query-string credentials are rejected. Public preview data comes only from a curated pool; live state has a separate authenticated route.
4. **Treat SQLite backup as a database operation.** Backups use SQLite's online backup API, pass `PRAGMA integrity_check`, and replace the destination atomically before retention pruning.
5. **Redact at final output sinks.** Formatted log records and persisted error fields pass through secret masking. Client errors retain stable Glitch structure while suppressing paths, SQL, credentials, and tracebacks.
6. **Restore the agential cut.** Framework-neutral Pydantic contracts live in `backend/contracts.py`. Services accept protocols or domain values and do not import FastAPI or API modules. API request models and query parameters enforce explicit size, identifier, token, and pagination bounds.
7. **Keep package initialization inert.** Package `__init__.py` files avoid eager cross-package re-exports that can create import cycles.

## Consequences

- Requests that exceed documented bounds now fail at the API membrane with validation errors.
- Active HTML and SVG uploads are rejected even when their signatures otherwise match an allowlist.
- Clients must send authentication in the `Authorization` header; export downloads use authenticated fetch and blob URLs.
- Anonymous preview consumers receive curated lines only. Consumers of live preview state must use `/api/preview/live` with authentication.
- Failed uploads, fetches, digestion jobs, and backups leave explicit terminal states or typed errors rather than partial success.
- The service layer can be imported and tested without FastAPI, reducing circular import risk.
- Operators gain new configuration limits for uploads, outbound fetches, digestion workers, timeouts, and backup retention.

## Verification

The implementation is covered by focused tests for SSRF and redirect handling, streamed upload rejection and atomicity, digestion timeout/concurrency, authentication boundaries, SQLite restore integrity, secret redaction, service imports, and request/query bounds. The final tree passes 349 Python tests, repository-wide Ruff lint and format checks, and the frontend TypeScript/Vite production build.
