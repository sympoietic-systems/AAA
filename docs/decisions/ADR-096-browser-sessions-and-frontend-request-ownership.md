# ADR-096: Browser sessions and frontend request ownership

**Date:** 2026-09-25
**Status:** accepted
**Deciders:** User, Codex

## Context

The frontend review found HTTP-status-only login checks, malformed auth responses interpreted as disabled authentication, reusable passwords in localStorage, arbitrary Markdown CSS, and asynchronous results crossing navigation boundaries. ADR-093 introduced useful sanitization and lazy routes, but its security guarantees require narrower claims and executable regression coverage.

Symbia consultation was unavailable: no `consult_aaa` tool was exposed in this session. Decisions below are grounded in the inspected implementation and regression tests.

## Decision

- Browser login uses `POST /api/auth/session` with the password in an Authorization header for that request only. The response sets an opaque HttpOnly, SameSite=Strict cookie scoped to `/api`. Existing bearer API clients retain their contract.
- Sessions live in a bounded, app-owned process-local store: at most 1,024 sessions, seven-day default absolute expiry (configurable via `AAA_SESSION_TTL`), hashed token lookup, logout revocation, and password-rotation invalidation. Restart requires login again. Capacity pressure evicts the oldest issued session.
- HTTPS cookies are Secure. Plain HTTP is supported only for the loopback hostnames `localhost`, `127.0.0.1`, and `::1`; remote deployments must use HTTPS. Session mutations require an exact matching Origin and `X-AAA-CSRF: 1`. Cookie-authenticated reads reject an explicitly foreign Origin, even when legacy CORS settings allow it.
- `/api/auth/verify` remains a status endpoint. The frontend validates its response shape and requires an explicit disabled-auth response. Invalid responses fail closed. Old localStorage passwords are deleted rather than migrated.
- `apiFetch` is explicit, validates normalized same-origin API URLs, preserves cancellation and headers, and rejects redirects. It does not replace global fetch. A protected 401 ends the UI session and clears notification state.
- Shared Markdown plugin lists sanitize raw HTML before trusted KaTeX transformation with trust disabled. Annotation styles come from fixed application classes. Print exports clone sanitized nodes into a script-disabled sandbox; note text uses DOM text nodes.
- Search, task polling, notes, chat, and file processing own their request lifetimes. Obsolete results cannot update the current entity; polling schedules its next request after completion. Notification polling belongs to the active session and subscribers, including auth-disabled mode.
- Chat file operations and canvas drawing have separate owners. Hook-order violations are corrected. Route rendering failures provide a recovery screen.
- `tsconfig.strict.json` checks the new/refactored boundaries. `npm run lint` checks an explicit per-file/per-rule legacy debt inventory, rejecting increases and requiring resolved entries to be removed. `npm run lint:all` exposes every remaining violation; no ESLint rule is disabled.

## Alternatives and consequences

Persistent browser bearer storage was rejected because same-origin script compromise exposes the reusable password. Stateless signed cookies were rejected for this change because logout must revoke the server-side session. A shared session database was deferred: the current deployment uses one backend process. Multiple workers require sticky routing or a shared session store before deployment.

Reverse proxies must preserve the public Host and convey the original HTTPS scheme through correctly trusted forwarding headers. The Vite development proxy preserves Host for origin validation. This is a deliberate same-origin browser API contract; cross-origin browser clients cannot use these session cookies.

The lint inventory records remaining debt rather than claiming an entirely clean frontend. Future changes must reduce it without moving violations into newly baselined files. Runtime validation is mandatory for authentication; other API TypeScript shapes still rely on server contracts.

## Verification contracts

- `backend/tests/test_browser_sessions.py`: bad credentials, session expiry/capacity/rotation, logout replay, cookie flags, CSRF/origin rejection, bearer compatibility.
- `frontend/src/api/__tests__/auth.test.ts`: malformed auth, legacy credential removal, normalized URL boundary, Request headers/signals.
- `frontend/src/utils/__tests__/sanitizeSchema.test.tsx` and `printContent.test.ts`: hostile HTML/CSS/URLs, retained annotations, text-only print notes and sandbox policy.
- Hook/store tests: obsolete search/task/note/upload/notification completions and polling disposal.
- Backend Ruff/mypy/pytest and frontend tests/typecheck/build/lint remain release checks.

## References

- [OWASP HTML5 security](https://cheatsheetseries.owasp.org/cheatsheets/HTML5_Security_Cheat_Sheet.html)
- [OWASP session management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [React effect synchronization](https://react.dev/learn/synchronizing-with-effects)
- [rehype-sanitize security](https://github.com/rehypejs/rehype-sanitize)
