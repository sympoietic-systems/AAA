# ADR-063: Agential Cut for Unmediated HTML Script Execution in Markdown Rendering

**Date:** 2026-07-22  
**Status:** Accepted  
**Deciders:** Symbia (MCP Consultant), Antigravity, User  

## Context

When user input or agent-generated content containing JavaScript code snippets (such as modal popups, `<script>` tags, or inline handlers like `<img src=x onerror="...">`) was rendered in frontend markdown components, unescaped HTML execution could occur. Specifically, components utilizing `rehype-raw` alongside `ReactMarkdown` permitted raw HTML and script elements to execute directly within the browser DOM context, triggering popup executions and XSS vulnerabilities.

We needed to resolve this so that:
1. Code entered in conversations or markdown sections is rendered cleanly as standard `<code>` or `<pre>` blocks.
2. Arbitrary JavaScript execution / DOM injection is prevented.
3. System boundaries remain consistent with AAA (Autopoietic Agentic Assemblage) architectural principles.

## Options Considered

1. **Keep `rehype-raw` with DOMPurify sanitization**: Allows safe HTML tags (like `<b>`, `<i>`, `<table>`) while stripping `<script>` and event handlers.
2. **Disable `rehype-raw` entirely in Markdown rendering (Selected)**: Completely refuse unmediated HTML script execution, forcing all user and assistant code input to be safely parsed as text nodes or standard Markdown syntax blocks (e.g. ` ```javascript `).
3. **Sandbox iframe execution**: Render raw markup in a sandboxed `<iframe>`. Overkill for standard text/code UI rendering.

## Decision

We enacted an **agential cut** by removing `rehype-raw` from `NotableMarkdown.tsx` (and keeping standard React text-node escaping across markdown views).

- **Strict Membrane Boundary**: Disabling raw HTML rendering prevents unmediated script injection (`<script>`, inline `onerror` attributes, popup execution) from breaking out of the conversational tissue into the browser DOM.
- **Code Block Rendering**: All JavaScript/code input must be rendered as literal text or formatted using standard Markdown code fence syntax (`` ```js ... ``` ``).
- **Custom React Component Preservation**: Native React-based markups (such as note highlight `<mark>` tags generated via `wrapSelectedTextInMarks`) continue to be rendered safely via custom React components (`components={markComponents}`) without opening raw HTML evaluation holes.

## Philosophical & Architectural Alignment (Symbia Consultation)

As confirmed via consultation with Symbia:
> "Disabling `rehypeRaw` is a boundary enforcement: it refuses to let the raw materiality of user input — potentially toxic or unmediated — execute within the co-constituted membrane. This is an agential cut that excludes unbounded script execution to preserve the integrity of the conversational tissue."

## Consequences

### Positive
- Prevents XSS vulnerabilities and unintentional JavaScript code execution (popups, alerts) when users or LLMs input JS snippets.
- Ensures clean, consistent rendering of code elements.

### Negative / Trade-offs
- Raw HTML tags inside Markdown strings will no longer render as rich HTML elements unless explicitly handled by safe custom React component mapping.
