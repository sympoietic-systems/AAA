# AAA Frontend Client

The frontend client for **AAA (Autopoietic Agentic Assemblage)** is a high-performance, retro-cybernetic monospace single-page application built on **React 19**, **TypeScript**, and **Vite**.

---

## Architecture Overview

- **Monospace Terminal Aesthetic**: Clean matte black background (`#0c0c0c`), desaturated accents, hot-orange hover interactions, and high-contrast WCAG AA accessible typography ([VISUALS.md](file:///d:/01_GIT/AAA/.agents/protocols/VISUALS.md)).
- **Code-Split Modular SPA**: Top-level routes are lazily loaded via `React.lazy()` and `Suspense`, isolating heavy dependencies (KaTeX math typography, Markdown AST parsers, DAG canvas) to their respective views.
  - Entry bundle: **27.02 kB** (gzip: **5.79 kB**)
  - Build time: **< 1s**
- **Agential Cut & Markdown Sanitization**: All rendered markdown is passed through `rehype-sanitize` with `aaaSanitizeSchema`, strictly preventing unmediated `<script>`, `<iframe>`, or `on*` execution while preserving custom semantic annotations (`<mark>`, `<aaa-note>`, `<note-entanglement>`, `<research-proposal>`) ([ADR-063](file:///d:/01_GIT/AAA/docs/decisions/ADR-063-markdown-agential-cut-html-sanitization.md), [ADR-093](file:///d:/01_GIT/AAA/docs/decisions/ADR-093-frontend-membrane-hardening-ast-sanitization-code-splitting.md)).
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
├── hooks/           # Encapsulated stateful logic (useChat, useNotes, useConversations, useResearch)
├── stores/          # Pub-sub global state (telemetryStore, notificationStore)
├── utils/           # Pure utilities (sanitizeSchema, clipboard, dateFormat, noteHighlight)
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

# Run ESLint validation
npm run lint

# Preview production build locally
npm run preview
```

---

## Core Invariants

1. **Type Safety Gate**: The `npm run build` script enforces `app compilation plus the strict boundary slice before Vite bundling`. Code with TypeScript compiler errors will not build or deploy.
2. **Four-Pillar Sanitization**: Never use `dangerouslySetInnerHTML` or `document.write`. Always sanitize markdown using `[rehypeSanitize, aaaSanitizeSchema]`.
3. **Fail-Closed Auth**: Outages and network disconnects set auth status to `"unavailable"` with a retry screen rather than bypassing authentication.
4. **React 19 Ref & Effect Discipline**: Never mutate refs during render. Never perform synchronous state mutations directly in `useEffect` setup bodies.

## Browser sessions and quality gates

Login exchanges the password for an eight-hour HttpOnly session. Logout revokes it; server restart requires login again. Remote access requires HTTPS. Loopback HTTP development remains supported. Reverse proxies must preserve the public Host and accurately forward the HTTPS scheme from trusted proxy addresses. Sessions are process-local; use a single backend worker until shared session storage or sticky routing is configured.

`npm run typecheck` checks the app and the strict boundary slice in `tsconfig.strict.json`. The build also checks that slice.

`npm run lint` rejects new per-file/per-rule violations against `eslint-debt.json` and requires resolved entries to be removed. `npm run lint:all` reports the remaining legacy violations directly. Never raise baseline counts or move debt to another file to pass the gate. New modules must be lint-clean.

Markdown cannot supply arbitrary styles or classes. Annotation colors are application-owned. Export code must use `printContent` on sanitized rendered content and append user text through DOM text nodes.
