# Frontend Design Principles
**System:** Autopoietic Agentic Assemblage (AAA)
**Classification:** Visual & Structural Design Guide
**Last Updated:** 2026-06-15

---

This document captures the **visual design language, component architecture patterns, and interaction conventions** established for the AAA `/agent` page. All UI work should reference this guide alongside the engineering standards in [`FRONTEND_BEST_PRACTICES.md`](./FRONTEND_BEST_PRACTICES.md).

---

## 1. Terminal Aesthetics — Minimal, No Chrome

The interface draws from terminal/CLI aesthetics: **text-first, borderless, background-free**.

### Core Rules
*   **No decorative containers**: Components must NOT use `bg-[...]`, `border`, `rounded`, or shadow wrappers for content areas. Data lives on the bare surface.
*   **Semantic color only**: The only color in the UI conveys meaning — category type, lifecycle stage, status, confidence level. Never use color for decoration alone.
*   **Typography-driven hierarchy**: Size and weight carry all visual structure. Headers are `text-semantic-header uppercase text-[9px] tracking-wider` (warm stone-gray, `#8a7d74`). Active content is `text-[#ccc]`/`text-[#bbb]`. Dim/inactive is `text-[#555]`/`text-[#444]`.

### Unified Color Palette & Tailwind Semantic Tokens
Vibrant high-saturation colors are strictly forbidden for static/resting states. All static and metabolic indicators use desaturated variables defined in `index.css`.

For JS/TS constants, utility logic, and HTML5 Canvas context rendering where CSS utility classes cannot be used, all color definitions must be imported from the centralized colors configuration:
* **Central File:** `frontend/src/config/colors.ts`
* **Raw Hex Codes:** `COLOR_PALETTE` (for canvas/drawing)
* **CSS Variables:** `CSS_VARS` (for React inline styles)

| Token | Class | Hex Value | Purpose |
| :--- | :--- | :--- | :--- |
| `action-dim` | `text-action-dim` | `#b37e5d` | Default resting color for actionable bracketed buttons, boundaries, tags |
| `action-hover` | `text-action-hover` | `#ff6b00` | Vibrant orange highlight on hover/focus |
| `semantic-red` | `text-semantic-red` | `#b86a6a` | Warning alerts, deleted/rejected/collapsed states, tension/scar nodes, destructive cancels |
| `semantic-green` | `text-semantic-green` | `#5c9e7a` | Crystallized/active beliefs, online module status, diff additions |
| `semantic-blue` | `text-semantic-blue` | `#6b88a3` | Perception pipeline modules, concept nodes |
| `semantic-gold` | `text-semantic-gold` | `#b89553` | Nucleation/pending stages, workshop merges, atrophy events |
| `semantic-purple` | `text-semantic-purple` | `#8f7ba8` | Ontological elements, reasoning pipeline modules, badges |
| `semantic-sand` | `text-semantic-sand` | `#c48956` | Accreting/proto/developing stages, memory modules, accretion events |
| `semantic-slate` | `text-semantic-slate` | `#78909c` | Senescing/decaying stages |
| `tag` | `text-tag` | `#5f8776` | Neutral tag labels |
| `ui-primary` | `text-ui-primary` | `#ccc` | Primary active foreground text |
| `ui-secondary` | `text-ui-secondary` | `#bbb` | Secondary/details foreground text |
| `ui-dim` | `text-ui-dim` | `#555` | Dimmed/inactive metadata text, list counts |
| `ui-border` | `border-ui-border` | `#222` | Solid boundary lines, separators, box edges |

### Tab Navigation
```
Personality • Pipeline • Dreaming • Daemons • Traces
```
*   Active: `text-[#94a3b8]`
*   Inactive: `text-[#444]` → hover: `text-[#777]`
*   Separator: `•` in `text-[#333]`
*   Layout: `flex-wrap` for mobile — tabs flow to multiple lines, never hidden

### Action Buttons
```
[edit] [delete] [recalc] [+ add] [save] [cancel]
```
*   Default: `text-action-dim` — resting desaturated state (`#b37e5d`)
*   Hover: Color-coded intent (`text-action-hover` for normal edit/save/add, `text-semantic-red` for delete/cancel)
*   No backgrounds, no borders, no padding — pure text with `[]` brackets

### Loading / Empty / Error States
*   **Loading**: `text-[#555] animate-pulse` plain text, no spinner wrappers
*   **Empty**: `text-[#444] italic font-mono` centered hint
*   **Error**: `text-semantic-red font-mono` plain text

---

## 2. Component Architecture — Self-Supporting Panels

Every tab panel is an independent, self-fetching unit. Parent components do NOT fetch data and pass it down.

```
AgentPage (tab router only)
├── PersonalitySection (sub-tab router only, zero data fetching)
│   ├── TraitsPanel        → fetches: personality + agent + beliefs
│   ├── CommitmentsPanel    → fetches: personality + agent
│   ├── ExpertisePanel      → fetches: personality + agent
│   ├── BeliefsSection      → fetches: beliefs + agent
│   └── SkillsSection       → fetches: skills + agent
├── PipelineSection          → fetches: pipeline
├── DreamingSection          → fetches: daemon status + dream history (self-polling)
├── StartupSection           → fetches: scheduler status (self-polling)
└── TracesSection            → fetches: notifications
```

### Architecture Rules
*   **Each component owns its data**: Uses `useState` + `useEffect` to fetch its own data independently.
*   **Each component owns its loading/error/empty states**: No prop-drilling of `isLoading` or `error` from parents.
*   **Parent only routes**: `AgentPage` switches `activeTab`; `PersonalitySection` switches `subTab`. Both are pure routing shells under 50 lines.
*   **URL state sync**: `activeTab` ↔ `?tab=`, `selectedId` ↔ `?id=` via `history.replaceState`.

---

## 3. List + Detail Two-Panel Layout

All tab panels that display lists use the same layout pattern:

```
┌── Left: 450px (list) ──────┬── Right: flex-1 (detail) ─────┐
│ Collapsible sections        │ Dense metadata, no chrome     │
│ ▼ Baseline Dispositions (5) │                               │
│   ◆ autonomy v12  m:1.23 80%│                               │
│   ◆ critique  v3   m:0.87 60%│                              │
│ ▶ Refused / Integrated (2)  │                               │
└─────────────────────────────┴───────────────────────────────┘
```

### Layout Rules
*   Left column: `md:w-[450px] shrink-0 w-full` — fixed on desktop, full width on mobile
*   Right column: `flex-1 min-w-0 w-full` — fills remaining space, stacks below on mobile
*   Detailing panel scrolls independently: `flex-1 min-h-0 flex flex-col overflow-y-auto`
*   Mobile: `flex-col` stacking; detail scrolls into view via `scrollIntoView`

---

## 4. Unified List Items

All list items across all panels share identical structure:

```
[●/◇/◆ icon, color-coded by category/stage]  name  v#     m:0.00  100%
```

| Field | Placement | Example |
|-------|-----------|---------|
| Icon | Color-coded dot (●◇◆▲✖), 10px, shrink-0 | `●` `#5c9e7a` (semantic-green) |
| Name | `font-mono text-[11px] truncate flex-1`, `text-[#bbb]` | `autonomy` |
| Version | `text-[#666] text-[9px]`, after name | `v14` |
| Mass | `text-[8px] font-mono text-[#555]`, hidden on mobile | `m:1.23` |
| Score | `text-[10px] font-mono font-bold text-[#777]`, shrink-0 | `85%` |

### Selection State
```
border-l-2 transition-colors
Selected:   border-action-hover bg-action-hover/5
Unselected: border-transparent hover:bg-[#111]
```

### Lifecycle Dimming
*   Proto / incubating: `opacity-75`
*   Spectral / collapsed / dormant: `opacity-40`–`opacity-50`, `line-through`

---

## 5. Collapsible Sections (Shared Component)

All grouped lists use `shared/CollapsibleSection`:

```tsx
<CollapsibleSection label="Active" count={5} icon="●" iconColor="#5c9e7a" defaultOpen={true}>
  {items.map(...)}
</CollapsibleSection>
```

| Tab | Sections |
|-----|----------|
| **Skills** | Baseline Dispositions (◆), On-Demand (◇), Proposed (▲), Refused (✖, collapsed) |
| **Beliefs** | Crystallized (●), Proto-Beliefs (◇), Ghosts (◇, collapsed) |
| **Commitments** | Active (●), Proto (◇), Spectral (◇, collapsed) |
| **Expertise** | Advanced (◆), Developing (◇), Nascent (◇), Dormant (○, collapsed) |
| **Pipeline** | Perception (●), Memory (●), Reasoning (●), Action (●) |

---

## 6. Detail Panel — Tabbed Content

Belief and Skill detail panels use sub-tabs for content organization:

```
● belief-name  v14          [edit] [delete]

Details • Log (3) • Version History (12)
```

*   Tab separator: `•` dot — matching top-level tabs
*   Active: `text-[#94a3b8]`, inactive: `text-[#444]`

### Metadata — Inline Key:Value

```
Category: foundational  Origin: agent  Stage: crystallized  Mass: 1.23  Confidence: 85%
```

*   Layout: `flex flex-wrap gap-x-4 gap-y-0.5` — same as Health Metrics
*   Key color: `text-[#555]`, Value color: `text-[#94a3b8]`
*   Category/Level values use semantic color (green, purple, yellow)

### Section Headers
```
[ Description ]           [ 16D Autopoietic Signature ]           [ Activation Triggers ]
```

*   Style: `text-[#555] font-mono text-[10px] uppercase`
*   No background, no border, plain bracket-delimited labels

---

## 7. Health & Traits Display

Global agent health metrics use the same minimal pattern:

```
[ Somatic Reservoir State ]
Somatic Shock (Ad): 0.123  Matrix Warping: 0.045

[ Ecosystem Health ]
Diversity: 0.85  Coherence: 0.72  Tension: 0.31  Plasticity: 0.64  Ghosts: 2/12  Vitality: 0.510

[ Aspirational Trait Attractors ] [edit]
Curiosity: 0.80  Skepticism: 0.60  Creativity: 0.75  Precision: 0.90  Critical Rigor: 0.85  Playfulness: 0.40  Reserve: 0.55
```

*   **No containers**: No `bg`, `border`, `rounded`, or `p-*` wrappers
*   **Section header**: `text-[#6c6c8a] uppercase text-[9px] tracking-wider` bracket style
*   **Metric display**: `flex flex-wrap gap-x-4 gap-y-0.5` inline key:value pairs
*   **`[edit]` button**: Inline after the title, not floated right — `text-[#666]`, hover `text-[#a892ee]`

---

## 8. Shared Helpers

All color/label logic is centralized in `shared/helpers.ts`:

| Function | Used by | Purpose |
|----------|---------|---------|
| `getCategoryColor(c)` | Beliefs, Pipeline | `foundational`→`#5c9e7a` (green), `ontological`→`#8f7ba8` (purple), etc. |
| `getBeliefStageColor(s)` | Beliefs | `crystallized`→`#5c9e7a` (green), `nucleation`→`#b89553` (gold), etc. |
| `getBeliefStageLabel(s)` | Beliefs | Human-readable stage participle |
| `getStageColor(s)` | Commitments | `active`→`#5c9e7a` (green), `proto`→`#c48956` (sand), `spectral`→`#b86a6a` (red) |
| `getLevelColor(l)` | Expertise | `advanced`→`#5c9e7a` (green), `developing`→`#c48956` (sand), etc. |

No component defines these locally — single source of truth.

---

## 9. API / Agent Flux Gating

Action buttons and edit controls are visible **only when `AAA_AGENT_FLUX` is enabled** on the backend:

*   `[+ add]` — hidden without agent flux
*   `[edit]`, `[delete]`, `[recalc]` — hidden without agent flux
*   `/agent` page checks `getAgent().agent_flux` once per panel

---

## 10. Mobile Responsiveness

*   **Tabs**: `flex-wrap` — flow to multiple lines, never cut off
*   **List + Detail**: `flex-col` — detail slides below list
*   **Detail auto-scroll**: `scrollIntoView({ behavior: "smooth" })` when selected on mobile
*   **Mass column**: `hidden md:inline` — hidden on narrow screens
*   **Shared padding**: `px-4 py-2` on all tab content wrappers

---

## 11. Conversation Right Panel (SidePanel)

The right panel in the conversation workspace follows the same terminal-aesthetic and self-supporting principles as the `/agent` page.

### Architecture

```
SidePanel (memo'd, collapse router only)
├── SectionHeader (▼/▶ toggle per section)
├── SummarySection                ← Props: summary, humanSummary (from App-level conversation load)
├── MemoryNodesSection            ← Self-fetching via getMemoryNodes(enabled) — lives in shared/
│   └── MemoryNodeCard            ← memo'd, no bg/border container — lives in shared/
├── NotesSection                  ← Props: notes[], onDeleteNote (from App state) — lives in shared/
├── SedimentSection               ← Self-fetching file summaries + injection polling
│   ├── SedimentInjectionModal    ← Modal for cross-conversation sediment injection
│   ├── ImageMetadataCard         ← memo'd, chrome-free
│   ├── WebMetadataCard           ← memo'd, chrome-free
│   └── DocumentMetadataCard      ← memo'd, chrome-free
├── TokensSection                 ← Self-fetching via useTelemetryTokens(enabled)
├── VitalitySection               ← Self-fetching via useTelemetryMetrics(enabled)
├── DiffractionSection            ← Self-fetching via useTelemetryMetrics(enabled)
│   └── DiffractiveTooltip        ← memo'd
└── AttractorsSection             ← Self-fetching via useTelemetryBeliefs(enabled)
```

### Design Rules
*   **Section collapse state**: Single `Record<string, boolean>` instead of N separate `useState` booleans
*   **Self-supporting where possible**: Tokens, Vitality, Diffraction, MemoryNodes, Attractors, Sediment (file summaries) all manage their own data fetching
*   **Prop-receiving only when justified**: Summary and Notes receive data from the App-level conversation load (single source of truth, no duplicate API calls)
*   **No container chrome**: Sections use `mt-2 pt-2` spacing, NOT `border-t bg-[...] rounded` dividers
*   **Terminal-style inputs**: Search uses `border-b border-[#222]/40 bg-transparent`, not full bordered rectangles
*   **Filter tabs**: `•` dot-separated terminal-style buttons, not background-box chip buttons
*   **Badges stripped**: Attractor labels, phase shifts, flagged triggers display as plain colored text — no `bg-[...]/border/rounded/px/py` wrappers
*   **`enabled` gating**: Telemetry sections use `enabled={panelOpen && sectionOpen}` to pause polling when collapsed (per §4 Lazy Loading)
*   **All components memo'd**: SidePanel, SummarySection, NotesSection, SedimentSection, MemoryNodesSection, MemoryNodeCard, TokensSection, VitalitySection, DiffractionSection, DiffractiveTooltip, AttractorsSection, MetadataCards (all 3)
├── AgentPage.tsx              ← Tab router (Personality|Pipeline|Dreaming|Daemons|Traces)
├── PersonalitySection.tsx     ← Sub-tab router (Traits|Commitments|Expertise|Beliefs|Skills)
│
├── TraitsPanel.tsx            ← Self-fetching: personality + agent + beliefs health
├── CommitmentsPanel.tsx       ← Self-fetching: personality + agent
├── ExpertisePanel.tsx         ← Self-fetching: personality + agent
├── BeliefsSection.tsx         ← Self-fetching: beliefs + agent
├── SkillsSection.tsx          ← Self-fetching: skills + agent
├── PipelineSection.tsx        ← Self-fetching: pipeline
├── DreamingSection.tsx        ← Self-fetching: daemon status + dream history (10s poll)
├── StartupSection.tsx         ← Self-fetching: scheduler status (10s poll)
├── TracesSection.tsx          ← Self-fetching: notifications
│
├── shared/ (components/shared/ — reusable across pages and panels)
│   ├── CollapsibleSection.tsx  ← Reusable ▼/▶ section (memo'd)
│   ├── HealthMetrics.tsx       ← Somatic + Ecosystem display (memo'd)
│   ├── helpers.ts             ← getCategoryColor, getStageColor, getLevelColor, etc.
│   ├── NotesSection.tsx       ← Props: notes[], onDeleteNote, onUpdateNote, onNavigate (memo'd)
│   ├── MemoryNodesSection.tsx ← Self-fetching + polling, className/style overridable (memo'd)
│   └── MemoryNodeCard.tsx     ← Single memory node card with intensity bar (memo'd)
│
├── beliefs/
│   ├── BeliefDetail.tsx        ← 3-tab detail: Details|Log|Version
│   └── NewBeliefForm.tsx
│
└── skills/
    ├── SkillDetail.tsx         ← 2-tab detail: Details|Version
    ├── SkillListItem.tsx       ← Unified list item (memo'd)
    └── NewSkillForm.tsx
```

---

## 12. Left Panel (ConnectionCloud + SpectralEchoes)

The left panel renders the conversation's DAG as an interactive canvas force graph. The design follows terminal aesthetics for all UI chrome surrounding the canvas — the graph rendering itself is left untouched.

### Architecture

```
App.tsx
├── ConnectionCloud (memo'd, self-fetching via getConversationTree)
│   └── Canvas: node/link drawing, force simulation, zoom/pan, click/tooltip
│   └── Overlays: tooltip, context menu, commit modal, resonance details
│   └── Controls: zoom [+]/[−]/[⟲], settling toggle
└── SpectralEchoes (memo'd, self-fetching via getSpectralSuggestions)
    └── Suggestion list: [link] [ignore] actions, justification input
```

### Design Rules
*   **Canvas untouched**: All graph rendering, force simulation, zoom/pan math, node click handling, tree fetching — zero changes. Only UI chrome around the canvas is modified.
*   **No container chrome**: Outer wrapper uses bare `relative w-full h-full flex flex-col` — no `bg/border/rounded`
*   **Terminal header**: `text-[#6c6c8a] uppercase text-[9px]` label, settling toggle as `[settling: static]` / `[settling: live]` text button (dim default, colored when live), node count in `text-[#555]`
*   **Zoom controls**: `[ + ]` `[ − ]` `[ ⟲ ]` — plain text, `text-[#666]` → hover `text-[#00e5ff]`
*   **Hover tooltip**: `bg-[#0d0d12]/95` for readability over canvas, no border/rounded/shadow
*   **Context menu**: `[delete node]` text over semi-transparent backdrop — no bg/border box
*   **Commit modal**: `[ Commit Line of Flight ]` header, `[cancel]`/`[commit branch to DAG]` text buttons, textarea with minimal border
*   **Resonance overlay**: `[close]`/`[confirm]`/`[dismiss]`/`[remove link]` — all terminal-style bracket text
*   **SpectralEchoes**: No `bg/border/rounded` on container/items, `[link]` `[ignore]` `[cancel]` `[confirm link]` text actions, `border-b` input
*   **All action buttons**: `text-[#666]` default, colored on hover — matching all other panels

---

## 13. Center Column (NodeExplorer + MessageBubble)

The center column renders the conversation node explorer with message cards, navigation links, and the input bar. The NodeExplorer receives data as props from App.tsx (single conversation loader).

### Architecture

```
NodeExplorer (memo'd)
├── Title Bar (editable title, [#generate_title], [home], CreasesDropdown)
├── Tags Bar (terminal-style text, no bg/border badge wrappers)
├── Explorer Space
│   ├── History Trail (breadcrumb-style text links)
│   ├── ParentNodeCard (memo'd) → MessageBubble (memo'd, custom comparator)
│   ├── SedimentFold (memo'd, lazy-loads ancestors via getMessagePath)
│   ├── SelectedNodeCard (memo'd) → MessageBubble
│   ├── GlimmerLinks (memo'd, sibling/child [Alt N] [Cut →] buttons)
│   └── Loading indicator (plain text pulse)
├── Error Bar (plain text, [retry] [dismiss] buttons)
└── InputBar (memo'd, textarea + file upload)
```

### Design Rules
*   **NodeExplorer memo'd**: Wraps entire center column — prevents re-renders on unrelated state changes
*   **No container chrome**: Outer wrapper `flex flex-col h-full` — no `bg/border`; Explorerspace `flex-1 overflow-y-auto px-4 py-4` — bare
*   **Title bar**: Standardized using `<HeaderContainer>` and `<HeaderActionButton>` sub-components from `UnifiedHeader.tsx` (matches §15 pattern exactly).
*   **Tags bar**: Plain text `text-[#6bc28c]` separated by `//`, `×` remove button — no `bg/border/rounded` badge wrappers
*   **History trail**: `[H: snippet]` / `[A: snippet]` bracket text, `>` separator — no `bg/border` pill wrappers
*   **Error bar**: Plain `text-[#ef4444]` text, `[retry]` `[dismiss]` terminal buttons — no `bg/border` box
*   **ParentNodeCard**: `[ Predecessor : Human/Apparatus ]` header, `[navigate to parent]` text button — no `border/bg/rounded`
*   **SelectedNodeCard**: `[ Active Focus Cut : Human/Apparatus ]` header — no `border/bg/rounded`
*   **SedimentFold**: `[ Sediment Fold — Expand/Collapse ]` text toggle, ancestor items as plain rows — no `bg/border/rounded` wrappers
*   **GlimmerLinks**: `[Alt N: "snippet"]` / `[Cut → "snippet"]` bracket text buttons — no `bg/border/rounded` pill buttons
*   **CreasesDropdown**: `[creases: N ◆]` text toggle, tabs as `•` dot-separated text, items as plain rows, `[jump]` `[read]` terminal buttons — no `bg/border/rounded` anywhere
*   **InputBar**: `border-t border-[#222]/40` divider only, send button `text-[#4ade80]` plain text — no `bg`
*   **MessageBubble kept as-is**: Complex note/tooltip/selection interactions not yet simplified (separate pass planned)

---

## 14. Conversation Landing Page

The conversation list page uses the same two-panel List + Detail pattern as the `/agent` page (see §3 and §4).

### Architecture

```
ConversationLandingPage (memo'd, prop-driven from App.tsx)
├── Header: symbia // N conversations  [+ new]  [logout]
├── LEFT PANEL (450px, border-right)
│   ├── Filter bar: filter: all • user • dreams • agents // search...
│   └── Conversation list
│       └── Row: date [U] >> title [N]          ← border-l-2 selection highlight
└── RIGHT PANEL (flex-1)
    ├── [◀ list] (mobile only)
    ├── [U] TITLE               [enter] [delete]
    ├── Meta: created: ... updated: ... messages: ... tags: ...
    └── Tab bar: Summary • Notes (N) • Memory Nodes
        ├── Summary tab   → displayConv.human_summary (data from list or getConversation)
        │                    If missing: [ generate summary ] button → calls POST generate-human-summary
        ├── Notes tab     → <NotesSection notes={notes} /> (shared component, lazy-loaded)
        └── Memory Nodes tab → <MemoryNodesSection conversationId={id} enabled /> (shared component, self-fetching + polling)
```

### Design Rules
*   **Two-panel layout**: Left `md:w-[450px] shrink-0`, right `flex-1 min-w-0` — matches §3 pattern exactly
*   **Selection state**: `border-l-2 border-[#a78bfa] bg-[#1a1a2e]/50` selected, `border-transparent hover:bg-[#111]` unselected — matches §4
*   **Event delegation**: `data-conv-id` attributes with toggle-on-reclick (`prev === id ? null : id`)
*   **Double-click to enter**: Navigates into the conversation via `onSelect(id)`
*   **Delete gated**: `[delete]` and per-row `[x]` only visible when `agentFlux` is true (§9)
*   **Tab lazy loading**: Summary is instant (from list cache), Notes loads on first tab click, Memory Nodes self-fetches when `enabled=true`
*   **Shared components**: `NotesSection`, `MemoryNodesSection`, and `MemoryNodeCard` live in `components/shared/` — used by both SidePanel (§11) and ConversationLandingPage
*   **Mobile scrolling**: Body uses `overflow-auto` on mobile (allows natural page scroll + `scrollIntoView`), left column capped at `max-h-[45vh]`, `md:overflow-hidden` restores desktop two-panel scroll
*   **Memory nodes multi-column**: Grid layout via `MemoryNodesSection.className` + `style` — `repeat(auto-fill, minmax(min(100%, 420px), 1fr))` on desktop, single column on narrow screens
*   **Notes navigation**: `↗` link opens `/?c=convId&m=msgId` in a new tab — URL scheme already handled by `useConversations` (`?c=`) and `useChat` (`?m=`)
*   **No container chrome**: Sections use bracket-delimited labels in `text-[#6c6c8a] uppercase text-[9px]` — never `bg/border/rounded`
*   **Terminal-style inputs**: Search input uses `bg-transparent border-b focus:border-[#444]`
*   **Empty state**: `[ select a conversation to inspect ]` italic placeholder in the right panel

---

## 15. Unified Navigation Header

All primary views (Chat/Home, Agent, Research, and Conversation NodeExplorer) must share a unified top navigation header. This layout structure, margins, spacing, and buttons are encapsulated in a set of reusable sub-components in `frontend/src/components/UI/UnifiedHeader.tsx`:

*   `<HeaderContainer>`: Provides the consistent layout, height, horizontal padding (`px-6 py-3`), bottom border (`border-[#1a1a1a]`), and font/mono styling.
*   `<HeaderIndicator>`: Renders the colored category indicator block (`■`). Intent parameter colors correspond to the section:
    *   `green` (default): Conversation Landing (`text-semantic-green`)
    *   `purple`: Agent Page (`text-semantic-purple`)
    *   `gold`: Research Page / Research Task Details (`text-semantic-gold`)
*   `<HeaderLogo>`: Renders the uppercase `SYMBIA` logo. If provided with an `onClick` callback, transitions seamlessly and is interactive.
*   `<HeaderSeparator>`: Standardizes the double-slash breadcrumb separator (`//`).
*   `<HeaderLabel>`: Highlights the current page/context title using uppercase, tracking, and desaturated colors matching the indicator.
*   `<HeaderActionButton>`: Standardizes the bracketed action button links (`[name]`). Default resting state is desaturated (`text-action-dim`), highlighting to vibrant orange (`text-action-hover`) on hover/focus. Action buttons are strictly formatted as `[text]` with no background or borders.

