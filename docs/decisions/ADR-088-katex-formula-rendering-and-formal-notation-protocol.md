# ADR-088: KaTeX Mathematical Formula Rendering and Formal Notation Protocol

**Date:** 2026-09-18  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-063](ADR-063-markdown-agential-cut-html-sanitization.md), [ADR-037](ADR-037-frontend-component-hierarchy-and-modularity.md), [ADR-048](ADR-048-dynamic-autopoietic-personality-cascade.md)  

---

## Context

In dialogue and autonomous research, Symbia and the interlocutor frequently explore formal disciplines, including second-order cybernetics, information theory, differential geometry, and boundary logic (such as George Spencer-Brown's *Laws of Form*). 

However, two related breakdown points impaired legibility:
1. **Frontend Rendering Deficit:**  
   The frontend markdown rendering pipeline utilized `react-markdown` configured exclusively with `remark-gfm` and `remark-breaks`. Math delimiters (`$...$` for inline and `$$...$$` for display blocks) were not parsed, leaving raw LaTeX strings, escaped backslashes, and curly braces exposed directly in chat bubbles and markdown sections.
2. **Exotic Formalism Mnemonic Degradation:**  
   When representing non-standard notations that lack native LaTeX/KaTeX glyphs (notably Spencer-Brown's boundary crosses in the calculus of indications), the language model attempted ad-hoc overline hacks (`\left. \overline{...} \right|`) which routinely suffered escaped-character degradation—turning thin spaces (`\,`) into literal commas `, ,` and negative thin spaces (`\!`) into exclamation marks `!`, producing illegible mathematical gibberish.

---

## Decision

We have implemented a coordinated two-sided solution encompassing frontend typography rendering and agent operational protocol alignment:

### 1. Frontend KaTeX Rendering Pipeline
We installed and integrated `remark-math` (AST math node extraction), `rehype-katex` (HTML math tree transform), and `katex` (typesetting engine) across the frontend:
- **Global Stylesheet:** Imported `katex/dist/katex.min.css` in `frontend/src/main.tsx`.
- **Display & Contrast Rules:** Added dark-mode compatibility and horizontal overflow handling (`overflow-x: auto`) for `.katex-display` blocks in `frontend/src/index.css`.
- **Universal Markdown Integration:** Enabled `[remarkGfm, remarkBreaks, remarkMath]` and `[rehypeRaw, rehypeKatex]` across all conversational and research markdown surfaces:
  - `MessageBubble.tsx`: Both human and agent conversation streams, including expandable system messages.
  - `NotableMarkdown.tsx`: Long-form reports, daily notes, and highlighted text selections.
  - `MarkdownSection.tsx` and `ResearchDetailPanel.tsx`: Autonomous research stage summaries, synthesis cards, and step execution logs.

### 2. Operational Protocol 12: Formal and Mathematical Notation
In `config/personality/identity.yaml`, under `personality.operational_protocols.conversation`, we added Protocol 12:
```yaml
12. Formal and Mathematical Notation:
    - Express mathematical equations, cybernetic models, and formal relationships using
      standard LaTeX ($...$ for inline, $$...$$ for display blocks).
    - For formalisms that lack standard typographic symbols (such as Spencer-Brown's
      boundary crosses in Laws of Form), use conceptual words and terms (e.g., "Mark",
      "Cross", "Void") or clean boundary notation () () = () rather than attempting
      ad-hoc ASCII or broken overbar/spacing hacks.
```

By explicitly directing the model to leverage standard conceptual words (*Mark*, *Cross*, *Void*) or canonical parenthetical boundary logic notation (`() () = ()`, `(()) = `) when standard typographical symbols are unavailable, we eliminate OCR/macro hallucinations while ensuring universal clarity.

---

## Consequences

### Positive
- All mathematical and cybernetic expressions across all conversations, research stages, and notes are rendered with crisp mathematical typography.
- Historical and branched conversations automatically benefit from rendered math without data migration.
- Formula spacing bugs and unescaped delimiter artifacts in non-standard logics are eliminated.

### Negative / Trade-offs
- Additional bundle weight: KaTeX fonts and engine add ~100KB gzipped to the frontend client build. Handled efficiently via Vite chunk splitting.
