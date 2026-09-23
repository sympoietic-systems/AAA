# AAA Frontend Client

The frontend client for **AAA (Autopoietic Agentic Assemblage)** is a high-performance, retro-cybernetic monospace single-page application built on **React 19**, **TypeScript**, and **Vite**.

---

## Architecture Overview

- **Monospace Terminal Aesthetic**: Clean matte black background (`#0c0c0c`), desaturated accents, hot-orange hover interactions, and high-contrast WCAG AA accessible typography ([VISUALS.md](file:///d:/01_GIT/AAA/.agents/protocols/VISUALS.md)).
- **Code-Split Modular SPA**: Top-level routes are lazily loaded via `React.lazy()` and `Suspense`, isolating heavy dependencies (KaTeX math typography, Markdown AST parsers, DAG canvas) to their respective views.
  - Entry bundle: **27.02 kB** (gzip: **5.79 kB**)
  - Build time: **< 1s**
- **Agential Cut & Markdown Sanitization**: All rendered markdown is passed through `rehype-sanitize` with `aaaSanitizeSchema`, strictly preventing unmediated `<script>`, `<iframe>`, or `on*` execution while preserving custom semantic annotations (`<mark>`, `<aaa-note>`, `<note-entanglement>`, `<research-proposal>`) ([ADR-063](file:///d:/01_GIT/AAA/docs/decisions/ADR-063-markdown-agential-cut-html-sanitization.md), [ADR-093](file:///d:/01_GIT/AAA/docs/decisions/ADR-093-frontend-membrane-hardening-ast-sanitization-code-splitting.md)).
- **Origin-Locked HTTP Interceptor**: Bearer authentication tokens are strictly scoped to same-origin `/api/` endpoints to prevent credential leakage ([SECURITY.md](file:///d:/01_GIT/AAA/.agents/protocols/SECURITY.md)).

---

## Directory Structure

```
frontend/src/
├── api/             # API client services, fetch interceptors, typed response contracts
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

1. **Type Safety Gate**: The `npm run build` script enforces `"tsc -b && vite build"`. Code with TypeScript compiler errors will not build or deploy.
2. **Four-Pillar Sanitization**: Never use `dangerouslySetInnerHTML` or `document.write`. Always sanitize markdown using `[rehypeSanitize, aaaSanitizeSchema]`.
3. **Fail-Closed Auth**: Outages and network disconnects set auth status to `"unavailable"` with a retry screen rather than bypassing authentication.
4. **React 19 Ref & Effect Discipline**: Never mutate refs during render. Never perform synchronous state mutations directly in `useEffect` setup bodies.
