# Frontend Design Principles
**System:** Autopoietic Agentic Assemblage (AAA)
**Classification:** Visual & Structural Design Guide
**Last Updated:** 2026-06-14

---

This document captures the **visual design language, component architecture patterns, and interaction conventions** established for the AAA `/agent` page. All UI work should reference this guide alongside the engineering standards in [`FRONTEND_BEST_PRACTICES.md`](./FRONTEND_BEST_PRACTICES.md).

---

## 1. Terminal Aesthetics — Minimal, No Chrome

The interface draws from terminal/CLI aesthetics: **text-first, borderless, background-free**.

### Core Rules
*   **No decorative containers**: Components must NOT use `bg-[...]`, `border`, `rounded`, or shadow wrappers for content areas. Data lives on the bare surface.
*   **Semantic color only**: The only color in the UI conveys meaning — category type, lifecycle stage, status, confidence level. Never use color for decoration alone.
*   **Typography-driven hierarchy**: Size and weight carry all visual structure. Headers are `text-[#6c6c8a] uppercase text-[9px] tracking-wider`. Active content is `text-[#ccc]`/`text-[#bbb]`. Dim/inactive is `text-[#555]`/`text-[#444]`.

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
*   Default: `text-[#666]` — invisible until needed
*   Hover: color-coded intent (`#4ade80` save, `#ef4444` delete, `#a78bfa` edit)
*   No backgrounds, no borders, no padding — pure text with `[]` brackets

### Loading / Empty / Error States
*   **Loading**: `text-[#555] animate-pulse` plain text, no spinner wrappers
*   **Empty**: `text-[#444] italic font-mono` centered hint
*   **Error**: `text-[#ef4444] font-mono` plain text

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
├── DreamingSection          → fetches: daemon status (self-polling)
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
| Icon | Color-coded dot (●◇◆▲✖), 10px, shrink-0 | `●` `#4ade80` |
| Name | `font-mono text-[11px] truncate flex-1`, `text-[#bbb]` | `autonomy` |
| Version | `text-[#666] text-[9px]`, after name | `v14` |
| Mass | `text-[8px] font-mono text-[#555]`, hidden on mobile | `m:1.23` |
| Score | `text-[10px] font-mono font-bold text-[#777]`, shrink-0 | `85%` |

### Selection State
```
border-l-2 transition-colors
Selected:   border-[#a78bfa] bg-[#1a1a2e]/50
Unselected: border-transparent hover:bg-[#111]
```

### Lifecycle Dimming
*   Proto / incubating: `opacity-75`
*   Spectral / collapsed / dormant: `opacity-40`–`opacity-50`, `line-through`

---

## 5. Collapsible Sections (Shared Component)

All grouped lists use `shared/CollapsibleSection`:

```tsx
<CollapsibleSection label="Active" count={5} icon="●" iconColor="#4ade80" defaultOpen={true}>
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
| `getCategoryColor(c)` | Beliefs, Pipeline | `foundational`→`#4ade80`, `ontological`→`#a78bfa`, etc. |
| `getBeliefStageColor(s)` | Beliefs | `crystallized`→`#4ade80`, `nucleation`→`#f59e0b`, etc. |
| `getBeliefStageLabel(s)` | Beliefs | Human-readable stage participle |
| `getStageColor(s)` | Commitments | `active`→`#4ade80`, `proto`→`#f59e0b`, `spectral`→`#ef4444` |
| `getLevelColor(l)` | Expertise | `advanced`→`#4ade80`, `developing`→`#f59e0b`, etc. |

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
├── MemoryNodesSection            ← Self-fetching via getMemoryNodes(enabled)
│   └── MemoryNodeCard            ← memo'd, no bg/border container
├── NotesSection                  ← Props: notes[], onDeleteNote (from App state)
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
├── DreamingSection.tsx        ← Self-fetching: daemon status (10s poll)
├── StartupSection.tsx         ← Self-fetching: scheduler status (10s poll)
├── TracesSection.tsx          ← Self-fetching: notifications
│
├── shared/
│   ├── CollapsibleSection.tsx  ← Reusable ▼/▶ section (memo'd)
│   ├── HealthMetrics.tsx       ← Somatic + Ecosystem display (memo'd)
│   └── helpers.ts             ← getCategoryColor, getStageColor, getLevelColor, etc.
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
