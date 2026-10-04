# AAA Frontend Client

The frontend client for **AAA (Autopoietic Agentic Assemblage)** is a high-performance, retro-cybernetic monospace single-page application built on **React 19**, **TypeScript**, and **Vite**.

---

## Architecture Overview

- **Monospace Terminal Aesthetic**: Clean matte black background (`#0c0c0c`), desaturated accents, hot-orange hover interactions, and high-contrast WCAG AA accessible typography ([VISUALS.md](../.agents/protocols/VISUALS.md)).
- **Code-Split Modular SPA**: Top-level routes are lazily loaded via `React.lazy()` and `Suspense`, isolating heavy dependencies (KaTeX math typography, Markdown AST parsers, DAG canvas) to their respective views.
- **Markdown Policy**: Rendering sites that accept raw HTML share `safeHtmlPlugins` or `safeMathPlugins`. These apply `aaaSanitizeSchema` before trusted KaTeX transformation. Arbitrary inline styles and classes are removed; semantic annotations retain application-owned styles. Other Markdown views use ReactMarkdown without raw HTML support. See [ADR-096](../docs/decisions/ADR-096-browser-sessions-and-frontend-request-ownership.md).
- **Explicit Session Transport**: `apiFetch` targets normalized same-origin `/api/` URLs without overriding global fetch. Browsers use expiring HttpOnly sessions; passwords are never persisted. See [ADR-096](../docs/decisions/ADR-096-browser-sessions-and-frontend-request-ownership.md).

---

## Directory Structure

```
frontend/src/
├── api/             # API client services, explicit transport, typed response contracts
├── components/      # UI components and view layouts
│   ├── pages/       # Route-level views (NodesPage, ResearchPage, AgentPage, SearchPage, LoginPage)
│   ├── panels/      # Resizable side panels (ConnectionCloud, SidePanel, SearchTab, SedimentSection)
│   ├── shared/      # Cross-cutting components (NotableMarkdown, ConversationTitleBar, NotesSection)
│   └── UI/          # Base terminal primitives (UnifiedHeader, UnifiedFooter, TerminalButton)
├── config/          # Visual tokens, palette constants, and CSS variable mappings
├── hooks/           # Chat, conversation files, notes, archive search, and research state
├── stores/          # Pub-sub global state (telemetryStore, notificationStore)
├── utils/           # Markdown policy, print export, clipboard, dates, annotation helpers
└── App.tsx          # Root router, auth state machine, and offline recovery membrane
```

---

## Development & Build Commands

All commands should be executed from the `frontend/` directory (or via root runner scripts):

```bash
# Start local development server with HMR
npm run dev

# Run full TypeScript type-check and Vite production build
npm run build

# Run Vitest unit & integration test suite
npm test

# Check the app and strict boundary types
npm run typecheck

# Reject lint regressions against the explicit legacy debt inventory
npm run lint

# Show every remaining legacy lint violation
npm run lint:all

# Preview production build locally
npm run preview
```

---

## Core Invariants

1. **Type Safety Gate**: The `npm run build` script checks the app and the strict boundary slice before Vite bundling. Code with TypeScript compiler errors will not build or deploy.
2. **Untrusted Content**: Raw HTML requires the shared Markdown sanitization policy. Do not enable KaTeX trust or allow arbitrary CSS. Print sanitized rendered content through `printContent`; append user text as DOM text nodes.
3. **Fail-Closed Auth**: Outages and network disconnects set auth status to `"unavailable"` with a retry screen rather than bypassing authentication.
4. **React 19 Ref & Effect Discipline**: Never mutate refs during render. Never perform synchronous state mutations directly in `useEffect` setup bodies.

## Browser sessions and quality gates

Login exchanges the password for a seven-day HttpOnly session (configurable via AAA_SESSION_TTL). Logout revokes it; server restart requires login again. Remote access requires HTTPS. Loopback HTTP development remains supported. Reverse proxies must preserve the public Host and accurately forward the HTTPS scheme from trusted proxy addresses. Sessions are process-local; use a single backend worker until shared session storage or sticky routing is configured.

`npm run typecheck` checks the app and the strict boundary slice in `tsconfig.strict.json`. The build also checks that slice.

`npm run lint` rejects new per-file/per-rule violations against `eslint-debt.json` and requires resolved entries to be removed. `npm run lint:all` reports the remaining legacy violations directly. Never raise baseline counts or move debt to another file to pass the gate. New modules must be lint-clean.

Markdown cannot supply arbitrary styles or classes. Annotation colors are application-owned. Export code must use `printContent` on sanitized rendered content and append user text through DOM text nodes.

During iteration, run the tests for the boundary being changed, for example `npm test -- src/api/__tests__/auth.test.ts` or `npm test -- src/hooks/__tests__/useConversationFiles.test.ts`. A frontend-only edit does not require a full backend test run. For session-auth changes, use `uv run pytest backend/tests/test_browser_sessions.py backend/tests/test_auth_boundary.py -q` from the repository root.

`useConversationFiles` owns uploads and indexing polling; `ConnectionCloudRenderer` owns canvas drawing. Async result commits must belong to the current entity/request lifetime. Notification polling starts only with an active session and subscribers, including auth-disabled mode.
