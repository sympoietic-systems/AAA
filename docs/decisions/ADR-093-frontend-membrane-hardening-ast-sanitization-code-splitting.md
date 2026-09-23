# ADR-093: Frontend Membrane Hardening, Zero-XSS AST Sanitization, and Monolith Code-Splitting

**Date:** 2026-09-23  
**Status:** Accepted (Implemented)  
**Deciders:** Antigravity, Symbia (MCP Consultant), User  

## Context

Following an external architecture and security review alongside production profiling, several critical vulnerabilities and architectural debts were identified in the AAA frontend (`frontend/`):

1. **P1 XSS Risk via Unmediated Markdown Execution & Export**:
   - `NotableMarkdown.tsx` enabled `rehype-raw` without a sanitization schema, allowing `<script>`, `<iframe>`, `<object>`, and `on*` inline event handlers to survive markdown transformation into the DOM.
   - `ResearchTaskPage.tsx` copied unsanitized HTML into `window.open` via `document.write`, creating an executable XSS vector during PDF/print export and directly violating [ADR-063](ADR-063-markdown-agential-cut-html-sanitization.md).
   - Additional markdown rendering sites (`MessageBubble.tsx`, `MetadataCards.tsx`, `SedimentSection.tsx`, `ResearchDetailPanel.tsx`) lacked centralized sanitization rules.
2. **P1 Origin Leakage on API Authorization**:
   - The global `fetch` interceptor in `src/api/http.ts` appended `Authorization: Bearer <password>` to all requests indiscriminately, leaking user credentials to external URLs fetched by the client (such as web research probes or media).
3. **P1 Plaintext Passwords in Download URLs**:
   - Conversation export downloads appended `?token=<password>` in query parameters (`src/api/conversations.ts`), exposing credentials in browser history, proxy logs, and referrers.
4. **P2 Fail-Open Auth Vulnerability**:
   - `checkAuthStatus()` in `src/api/auth.ts` collapsed network errors to `authEnabled: false`, causing the client to unlock and expose protected screens when the backend was temporarily offline or unreachable.
5. **Initial Bundle Monolith (1,076 kB)**:
   - `App.tsx` directly defined and rendered the ~600-line `NodesPage` workspace layout, statically importing `NodeExplorer`, `SidePanel`, `ConnectionCloud`, KaTeX fonts, and markdown parsers. The entry bundle weighed over 1 MB before initial paint.
6. **Hidden Type Compilation Failures**:
   - `package.json` ran `"build": "vite build"`, which skipped `tsc -b`. 34 hidden TypeScript compilation errors existed across the client codebase.
7. **Full-Page Relinquishment on Internal Navigation**:
   - Internal links across headers and research views used native `<a href>` anchors, triggering full browser reloads that wiped in-memory React state and caused network re-authentication churn.

---

## Options Considered

### Markdown Sanitization
- **Option A (AST Sanitization via `rehype-sanitize` with Custom Schema)**: Parse markdown to HAST, apply an explicit tag/attribute allowlist, and strip dangerous script/iframe tags while preserving semantic tags (`<mark>`, `<aaa-note>`, `<note-entanglement>`, `<research-proposal>`). *(Selected)*
- **Option B (DOMPurify Post-Processing)**: Pass rendered HTML strings through DOMPurify. Incurs double-serialization overhead and breaks custom React component bindings (`components={...}`).
- **Option C (Strict Text Only)**: Disable raw HTML entirely. Rejects standard semantic markings and highlights required for conversational sediment and entanglement notes.

### Monolith Code Splitting
- **Option A (Extract `NodesPage` + Rollup `manualChunks`)**: Move the entire workspace layout into a dedicated lazy-loaded component (`NodesPage.tsx`) and configure Rollup chunk splitting for React, KaTeX, and Markdown libraries. *(Selected)*
- **Option B (Micro-frontends)**: Separate apps for `/nodes`, `/agent`, and `/research`. Unnecessary operational overhead for a unified SPA.

---

## Decision

We enacted a comprehensive hardening pass across security membranes, component modularity, and compilation boundaries:

### 1. Zero-XSS AST Sanitization Pipeline ([ADR-063](ADR-063-markdown-agential-cut-html-sanitization.md) Realization)
- Created `frontend/src/utils/sanitizeSchema.ts` exporting `aaaSanitizeSchema`, extending GitHub's default schema to allow:
  - `<mark data-note-id>`
  - `<aaa-note id type>`
  - `<note-entanglement>`
  - `<research-proposal id>`
- Enforced `[rehypeSanitize, aaaSanitizeSchema]` across all 5 markdown rendering sites:
  - `NotableMarkdown.tsx`
  - `MessageBubble.tsx`
  - `MetadataCards.tsx`
  - `SedimentSection.tsx`
  - `ResearchDetailPanel.tsx`
- Banned `<script>`, `<iframe>`, `<object>`, `<embed>`, and all `on*` inline handlers.

### 2. Sandboxed DOM Print Iframe
- Replaced `window.open` + `document.write` in `ResearchTaskPage.tsx` with a hidden sandboxed printing iframe that clones already-sanitized DOM nodes, eliminating string evaluation and popups.

### 3. Origin-Locked API Interceptor
- Hardened `http.ts` with `isSameOriginApiRequest(input)`:
  - Verifies exact match against `window.location.origin`.
  - Requires request path prefix `/api/`.
  - Preserves user-supplied `Request` headers and `AbortSignal`.
- Third-party endpoints never receive bearer authorization tokens.

### 4. Token-less Export Downloads
- Rewrote `downloadExport` in `src/api/conversations.ts` to perform authorized `fetch` requests and trigger downloads via in-memory blob URLs (`URL.createObjectURL(blob)`), completely eliminating `?token=<password>`.

### 5. Fail-Closed Auth State Machine
- Redesigned `checkAuthStatus()` to return:
  ```ts
  export type AuthStatus = "checking" | "authenticated" | "locked" | "disabled" | "unavailable"
  ```
- Network failures fail closed to `"unavailable"`. `App.tsx` renders a dedicated offline state with connection retry rather than bypassing authentication.

### 6. Monolith Extraction & Code Splitting
- Extracted the entire `/nodes` workspace from `App.tsx` into `src/components/pages/nodeexplorer/NodesPage.tsx` (630 lines).
- `App.tsx` reduced from 727 lines to 150 lines, serving purely as a top-level route coordinator with `Suspense`.
- Configured Rollup `manualChunks` in `vite.config.ts`:
  - `vendor-react`: `react`, `react-dom`, `react-router-dom`
  - `vendor-katex`: `katex`
  - `vendor-markdown`: `react-markdown`, `remark-*`, `rehype-*`

### 7. Client-Side SPA Navigation
- Updated `UnifiedHeader.tsx` (`HeaderActionButton` and `HeaderLogo`) to support `to?: string` and automatically route via React Router's `<Link>` component for internal paths.
- Converted relative anchors in `ResearchTaskPage.tsx` and `ResearchProposalCard.tsx` to `<Link>`.

### 8. Strict Verification & Invariant Enforcement
- Updated `package.json` build script to `"build": "tsc -b && vite build"`.
- Resolved all 34 pre-existing TypeScript compiler errors.
- Fixed React 19 ref mutation invariants and cascading render warnings across hooks (`useNotes`, `useChat`, `useResearch`, `usePanelResizer`).
- Enforced WCAG AA contrast for `--color-ui-dim` (`#7e8590`) and added `:focus-visible` styling in `index.css`.

---

## Consequences

### Positive
- **Guaranteed AST-Level XSS Immunity**: Hostile scripts or iframes embedded in notes, LLM responses, or sediment are sanitized before DOM instantiation.
- **Credential Isolation**: Bearer tokens are strictly isolated to same-origin `/api/` endpoints.
- **Massive Initial Load Speedup**:
  - Entry bundle reduced by **97.5%** (from **1,076.0 kB** down to **27.02 kB**, gzip: **5.79 kB**).
  - Production build completes in **701 ms**.
- **Continuous Type Safety**: CI and production builds fail if any TypeScript type violation exists.
- **Preserved App State**: SPA routing eliminates jarring full-page refreshes.
- **Clean Invariant Record**: All 103 frontend vitest tests and 316 backend tests pass with zero regressions.

### Negative / Trade-offs
- Markdown cannot render arbitrary external iframes or embedded objects without explicitly adding them to `aaaSanitizeSchema`.
