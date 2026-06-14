# Frontend Refactoring Plan — June 2026

**Branch:** `refactor/frontend-perf-and-ui-repository`  
**Status:** Not yet created  
**Based on:** [Frontend Code Audit Report](#) findings + [FRONTEND_BEST_PRACTICES.md](./FRONTEND_BEST_PRACTICES.md) + [FRONTEND_DESIGN_PRINCIPLES.md](./FRONTEND_DESIGN_PRINCIPLES.md)

---

## Overview

This plan addresses all findings from the comprehensive frontend audit, organized as a step-by-step sequence. Each step is small, independently verifiable, and ends with a build + lint check. No step depends on later steps, so we can stop at any phase boundary.

### Verification After Every Step

```powershell
cd frontend
npm run build    # TypeScript compilation — MUST pass
npm run lint     # ESLint — MUST pass (0 errors, 0 warnings)
```

Then visually verify in browser: `npm run dev` → confirm the affected panels still render and function.

---

## Phase 0 — Setup

### Step 0.1: Create Feature Branch
```powershell
git checkout feature/dynamic-personality-cascade
git pull
git checkout -b refactor/frontend-perf-and-ui-repository
```

**Verify:** `git branch` shows `* refactor/frontend-perf-and-ui-repository`

---

## Phase 1: P0 — Add `React.memo` to Missing Components

*Risk: Very Low. Purely additive — just wrapping existing component exports.*

### Step 1.1: Memo `BeliefDetail.tsx` (588 lines)
**File:** `frontend/src/components/pages/agentpage/beliefs/BeliefDetail.tsx`

- Add `memo` to the React import on line 1
- Wrap the default export with `memo()`

```tsx
// Before:
import { useState, useEffect, useRef } from "react"
// ...
export default function BeliefDetail({ ... }) { ... }

// After:
import { useState, useEffect, useRef, memo } from "react"
// ...
export default memo(function BeliefDetail({ ... }) { ... })
```

**Verify:** `npm run build` + `npm run lint` → visit `/agent?tab=personality&sub=beliefs`, click a belief. Detail panel loads. Click another belief — first detail should NOT flicker/re-render.

### Step 1.2: Memo `SkillDetail.tsx` (353 lines)
**File:** `frontend/src/components/pages/agentpage/skills/SkillDetail.tsx`

- Same pattern: add `memo` import, wrap default export

**Verify:** Same as above, but for Skills tab. Click skill → detail appears. Click another skill → no flicker.

### Step 1.3: Memo `SystemPromptViewer.tsx` (322 lines)
**File:** `frontend/src/components/panels/contextviewer/SystemPromptViewer.tsx`

- Convert `export function SystemPromptViewer` → `export const SystemPromptViewer = memo(function SystemPromptViewer`
- Add `memo` to import from React (currently imports `React, useEffect, useState`)

**Verify:** Open context viewer on a message → system prompt tab renders.

### Step 1.4: Memo `ConversationLandingPage.tsx` (275 lines)
**File:** `frontend/src/components/pages/landing/ConversationLandingPage.tsx`

- Add `memo` import, wrap export

**Verify:** Navigate to home (`/`) → landing page renders with conversation list.

### Step 1.5: Memo `DiffractiveZoneViewer.tsx` (290 lines)
**File:** `frontend/src/components/panels/contextviewer/DiffractiveZoneViewer.tsx`

- Already imports `React, useEffect, useState, useMemo` — add `memo`
- Wrap export

**Verify:** Open context viewer on a message → diffractive zone tab renders.

### Step 1.6: Memo Remaining Context Viewer Components
**Files:**
- `frontend/src/components/panels/contextviewer/ContextViewer.tsx` (101 lines)
- `frontend/src/components/panels/contextviewer/SedimentSectionViewer.tsx` (258 lines)
- `frontend/src/components/panels/contextviewer/FileSectionViewer.tsx` (183 lines)
- `frontend/src/components/panels/contextviewer/HistorySectionViewer.tsx` (107 lines)

**Verify:** Open each tab in the context viewer — all render correctly.

---

## Phase 2: P0 — Migrate `useTelemetry.ts` to `useSyncExternalStore`

*Risk: Medium. Changes the subscription mechanism for all 5 telemetry hooks. The pub-sub store itself (`telemetryStore.ts`) is untouched — only the React binding layer changes.*

### Step 2.1: Refactor `useTelemetryMetrics`
**File:** `frontend/src/hooks/useTelemetry.ts`

Replace the manual `useState` + `useEffect` pattern with `useSyncExternalStore`:

```tsx
// Before (lines 29-47):
import { useState, useEffect } from "react"
// ...
export function useTelemetryMetrics(enabled: boolean) {
  const [state, setState] = useState<...>(() => metricsState)
  useEffect(() => {
    if (!enabled) return
    setState(metricsState)
    const unsubscribe = subscribeMetrics(() => {
      setState({ ...metricsState })
    })
    return unsubscribe
  }, [enabled])
  return { metrics: state.data, ... }
}

// After:
import { useSyncExternalStore } from "react"
import { useEffect } from "react"
// ...
const EMPTY_METRICS: TelemetryStateSlice<MetricsResponse> = { data: null, loading: false, error: null }

export function useTelemetryMetrics(enabled: boolean) {
  const state = useSyncExternalStore(
    enabled ? subscribeMetrics : () => () => {},
    () => metricsState
  )
  const effectiveState = enabled ? state : EMPTY_METRICS
  return {
    metrics: effectiveState.data,
    metricsLoading: effectiveState.loading,
    metricsError: effectiveState.error,
    refreshMetrics: refreshMetricsForce
  }
}
```

**Important:** `useSyncExternalStore` takes `subscribe` + `getSnapshot`. When `enabled=false`, pass a no-op subscribe so the hook returns a stable snapshot without subscribing.

**Verify:** `npm run build` + `npm run lint` → open a conversation, expand right panel → VitalitySection metrics poll and display. Collapse section → polling stops. Expand again → polling resumes.

### Step 2.2: Refactor `useTelemetryDaemon`
Same pattern as Step 2.1, for the daemon status hook.

**Verify:** Visit `/agent?tab=dreaming` → dreaming section polls daemon status. Verify state updates on poll cycle.

### Step 2.3: Refactor `useTelemetryScheduler`
Same pattern, for the scheduler status hook.

**Verify:** Visit `/agent?tab=daemons` → startup section polls scheduler status.

### Step 2.4: Refactor `useTelemetryBeliefs`
Same pattern, for the per-conversation beliefs hook. Need to handle the `conversationId` parameter (use `useSyncExternalStore` inside — the subscribe function is stable as long as `conversationId` doesn't change within an effect cycle).

```tsx
export function useTelemetryBeliefs(conversationId: string | null, enabled: boolean) {
  const activeId = conversationId || ""
  const getSnapshot = () => (beliefsState[activeId] || { data: null, loading: false, error: null })
  
  const state = useSyncExternalStore(
    (enabled && activeId) ? (cb: () => void) => {
      const unsub = subscribeBeliefs(activeId, cb)
      return unsub
    } : () => () => {},
    getSnapshot
  )
  // ...
}
```

**Verify:** Open a conversation → expand right panel → AttractorsSection polls beliefs for that conversation. Switch conversations → old polling stops, new polling starts.

### Step 2.5: Refactor `useTelemetryTokens`
Same pattern as Step 2.4, for the tokens hook.

**Verify:** Open a conversation → expand right panel → TokensSection polls token counts. Verify display updates.

---

## Phase 3: P1 — Fix Inline `|| []` with Module-Level Constants

*Risk: Very Low. Just replacing inline empty arrays with stable references.*

### Step 3.1: Fix `App.tsx` line 515
**File:** `frontend/src/App.tsx`

```tsx
// Before (line 515):
tags={activeConv?.tags || []}

// After — add at top of module:
const EMPTY_STRING_ARRAY: string[] = []
// Then at line 515:
tags={activeConv?.tags ?? EMPTY_STRING_ARRAY}
```

**Verify:** Build + lint. Open a conversation with no tags → tags bar empty. Add a tag → tag appears.

### Step 3.2: Fix `AttractorsSection.tsx` line 35
```tsx
// Before:
const b = [...(beliefs.beliefs || []), ...(beliefs.proto_beliefs || []), ...(beliefs.ghosts || [])].find(...)

// After — add module-level:
const EMPTY_BELIEF_ARRAY: any[] = []
// Then:
const b = [
  ...(beliefs.beliefs ?? EMPTY_BELIEF_ARRAY), 
  ...(beliefs.proto_beliefs ?? EMPTY_BELIEF_ARRAY), 
  ...(beliefs.ghosts ?? EMPTY_BELIEF_ARRAY)
].find(...)
```

**Verify:** Right panel → Attractors section renders attractor labels.

### Step 3.3: Fix `PipelineSection.tsx` line 95
```tsx
// Add module-level constant, then at line 95:
const items = grouped[cat.key] ?? EMPTY_ARRAY
```

**Verify:** `/agent?tab=pipeline` → all 4 categories render their module lists.

### Step 3.4: Fix `ExpertisePanel.tsx` line 149
```tsx
// Same pattern:
const items = grouped[level] ?? EMPTY_ARRAY
```

**Verify:** `/agent?tab=personality&sub=expertise` → all level groups render.

### Step 3.5: Fix `ConnectionCloud.tsx` line 778
```tsx
// Add module-level EMPTY_NOTES constant, then:
const nodeNotes = notesMap.get(node.dbId ?? -1) ?? EMPTY_NOTES
```

**Verify:** DAG renders with nodes. Hover over nodes with no notes — no crash.

### Step 3.6: Fix `MetadataCards.tsx` lines 163-164
```tsx
// Add module-level NUMBER_ARRAY constant, then:
const vec = metadata.state_vector_impact ?? EMPTY_NUMBER_ARRAY
const implicatedNodes = metadata.belief_nodes_implicated ?? EMPTY_NUMBER_ARRAY
```

**Verify:** Open a file in SedimentSection → metadata card renders.

---

## Phase 4: P1 — Build New Reusable UI Components

*Risk: Low. New files, no existing code modified. Only the barrel export touches existing structure.*

### Step 4.1: Create `TerminalHeader` Component
**File:** `frontend/src/components/UI/TerminalHeader.tsx`

```tsx
import { memo } from "react"

interface TerminalHeaderProps {
  children: React.ReactNode
  className?: string
}

function TerminalHeaderComponent({ children, className = "" }: TerminalHeaderProps) {
  return (
    <div className={`text-[#6c6c8a] uppercase text-[9px] tracking-wider ${className}`}>
      {children}
    </div>
  )
}

export const TerminalHeader = memo(TerminalHeaderComponent)
```

The design doc specifies exactly this style for all section headers (FRONTEND_DESIGN_PRINCIPLES.md §1, §7, §11, §12, §13).

**Verify:** `npm run build` (component compiles; no usages yet, so no visual verification needed).

### Step 4.2: Create `TerminalButton` Component
**File:** `frontend/src/components/UI/TerminalButton.tsx`

```tsx
import { memo } from "react"

type Intent = "save" | "delete" | "edit" | "neutral" | "cyan" | "purple"

const INTENT_HOVER: Record<Intent, string> = {
  save:    "#4ade80",
  delete:  "#ef4444",
  edit:    "#a78bfa",
  neutral: "#888",
  cyan:    "#00e5ff",
  purple:  "#a78bfa",
}

interface TerminalButtonProps {
  children: React.ReactNode
  intent?: Intent
  onClick?: () => void
  disabled?: boolean
  className?: string
}

function TerminalButtonComponent({
  children, intent = "neutral", onClick, disabled, className = ""
}: TerminalButtonProps) {
  const hoverColor = INTENT_HOVER[intent]

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`text-[10px] text-[#666] font-mono cursor-pointer select-none transition-colors disabled:text-[#333] disabled:cursor-not-allowed ${className}`}
      style={{ color: "#666" }}
      onMouseEnter={e => { if (!disabled) (e.target as HTMLElement).style.color = hoverColor }}
      onMouseLeave={e => { if (!disabled) (e.target as HTMLElement).style.color = "#666" }}
    >
      [{children}]
    </button>
  )
}

export const TerminalButton = memo(TerminalButtonComponent)
```

> **Note:** The `[` `]` brackets are automatically added. Pass just the label text.

**Verify:** `npm run build` — compiles.

### Step 4.3: Create `KeyValueGrid` Component
**File:** `frontend/src/components/UI/KeyValueGrid.tsx`

```tsx
import { memo } from "react"

interface KVItem {
  key: string
  value: string | number
  valueColor?: string
}

interface KeyValueGridProps {
  items: KVItem[]
  className?: string
}

function KeyValueGridComponent({ items, className = "" }: KeyValueGridProps) {
  if (items.length === 0) return null

  return (
    <div className={`flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] font-mono text-[#888] ${className}`}>
      {items.map((item, i) => (
        <span key={i}>
          <span className="text-[#555]">{item.key}:</span>{" "}
          <span
            className={item.valueColor ? "" : "text-[#94a3b8]"}
            style={item.valueColor ? { color: item.valueColor } : undefined}
          >
            {item.value}
          </span>
        </span>
      ))}
    </div>
  )
}

export const KeyValueGrid = memo(KeyValueGridComponent)
```

**Verify:** `npm run build` — compiles.

### Step 4.4: Create `TerminalTabs` Component
**File:** `frontend/src/components/UI/TerminalTabs.tsx`

```tsx
import { memo } from "react"

interface Tab {
  key: string
  label: string
  badge?: number
}

interface TerminalTabsProps {
  tabs: Tab[]
  active: string
  onChange: (key: string) => void
  className?: string
}

function TerminalTabsComponent({ tabs, active, onChange, className = "" }: TerminalTabsProps) {
  if (tabs.length === 0) return null

  return (
    <div className={`flex flex-wrap items-center gap-0 ${className}`}>
      {tabs.map((tab, i) => (
        <span key={tab.key} className="flex items-center gap-0">
          {i > 0 && <span className="text-[#333] mx-1 select-none">•</span>}
          <button
            onClick={() => onChange(tab.key)}
            className={`font-mono text-[10px] transition-colors cursor-pointer select-none ${
              active === tab.key
                ? "text-[#94a3b8]"
                : "text-[#444] hover:text-[#777]"
            }`}
          >
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span className="ml-0.5 text-[#555]">({tab.badge})</span>
            )}
          </button>
        </span>
      ))}
    </div>
  )
}

export const TerminalTabs = memo(TerminalTabsComponent)
```

**Verify:** `npm run build` — compiles.

### Step 4.5: Create `DotIcon` Component
**File:** `frontend/src/components/UI/DotIcon.tsx`

```tsx
import { memo } from "react"

const DOT_MAP: Record<string, string> = {
  circle:   "●",
  diamond:  "◆",
  triangle: "▲",
  cross:    "✖",
  open:     "◇",
}

interface DotIconProps {
  type?: keyof typeof DOT_MAP
  color: string
  className?: string
}

function DotIconComponent({ type = "circle", color, className = "" }: DotIconProps) {
  return (
    <span
      className={`text-[10px] shrink-0 leading-none select-none ${className}`}
      style={{ color }}
    >
      {DOT_MAP[type]}
    </span>
  )
}

export const DotIcon = memo(DotIconComponent)
```

**Verify:** `npm run build` — compiles.

### Step 4.6: Create `TerminalInput` Component
**File:** `frontend/src/components/UI/TerminalInput.tsx`

```tsx
import { memo } from "react"

interface TerminalInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
  type?: "text" | "search"
}

function TerminalInputComponent({
  value, onChange, placeholder, className = "", type = "text"
}: TerminalInputProps) {
  return (
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={`bg-transparent border-b border-[#222]/40 py-0.5 text-xs text-[#ddd] font-mono outline-none focus:border-[#4ade80] placeholder:text-[#444] ${className}`}
    />
  )
}

export const TerminalInput = memo(TerminalInputComponent)
```

**Verify:** `npm run build` — compiles.

### Step 4.7: Create Barrel Export `UI/index.ts`
**File:** `frontend/src/components/UI/index.ts`

```tsx
export { Tooltip } from "./Tooltip"
export { VectorVisualizer } from "./VectorVisualizer"
export { AutopoieticCoordinates } from "./AutopoieticCoordinates"
export { StructuralAutopoieticGlyph } from "./StructuralAutopoieticGlyph"
export { TerminalHeader } from "./TerminalHeader"
export { TerminalButton } from "./TerminalButton"
export { KeyValueGrid } from "./KeyValueGrid"
export { TerminalTabs } from "./TerminalTabs"
export { DotIcon } from "./DotIcon"
export { TerminalInput } from "./TerminalInput"
```

**Verify:** `npm run build` — all exports resolve. `npm run lint` — no unused export warnings.

---

## Phase 5: P1 — Adopt `TerminalHeader`, `TerminalButton`, `KeyValueGrid`

*Risk: Medium. Replaces duplicated strings with component calls. Each file change is isolated.*

### Step 5.1: Adopt in `MetadataCards.tsx`
**File:** `frontend/src/components/panels/sidepanel/MetadataCards.tsx`

Replace all 12 occurrences of `<div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ ... ]</div>` with `<TerminalHeader>[ ... ]</TerminalHeader>`.

Import: `import { TerminalHeader, VectorVisualizer } from "../../UI"`

**Verify:** Build + lint. Open SedimentSection with files → all metadata cards render headers identically.

### Step 5.2: Adopt in `DreamingSection.tsx`
Replace section header with `<TerminalHeader>`.

**Verify:** `/agent?tab=dreaming` → headers render.

### Step 5.3: Adopt in `TraitsPanel.tsx`
Replace section header with `<TerminalHeader>`.

**Verify:** `/agent?tab=personality&sub=traits` → headers render.

### Step 5.4: Adopt in `HealthMetrics.tsx`
Replace section headers with `<TerminalHeader>`.

**Verify:** Somatic + Ecosystem headers render in TraitsPanel.

### Step 5.5: Adopt `TerminalButton` in `SkillDetail.tsx`
Find `[save]` `[cancel]` `[edit]` `[delete]` buttons → replace with `<TerminalButton intent="save">save</TerminalButton>` etc.

**Verify:** Skills detail → edit mode → save/cancel buttons render with correct hover colors.

### Step 5.6: Adopt `TerminalButton` in `BeliefDetail.tsx`
Same pattern: replace all bracket buttons.

**Verify:** Belief detail → edit → buttons render.

### Step 5.7: Adopt `KeyValueGrid` in `BeliefDetail.tsx` (2 locations)
Lines 296 and 484: replace `flex flex-wrap gap-x-4 gap-y-0.5` blocks with `<KeyValueGrid items={[...]} />`.

**Verify:** Belief detail metadata renders with identical layout and colors.

### Step 5.8: Adopt `KeyValueGrid` in `SkillDetail.tsx`, `PipelineSection.tsx`, `ExpertisePanel.tsx`, `CommitmentsPanel.tsx`
Same pattern in each detail panel's metadata section.

**Verify:** Each detail panel renders metadata identically.

### Step 5.9: Adopt `KeyValueGrid` in `MetadataCards.tsx` (3 locations)
Replace the metadata row blocks in ImageMetadataCard, WebMetadataCard, DocumentMetadataCard.

**Verify:** All metadata cards render.

---

## Phase 6: P1 — Adopt `TerminalTabs`, `DotIcon`, `TerminalInput`

### Step 6.1: Adopt `TerminalTabs` in `BeliefDetail.tsx`
Replace the `Details • Log (3) • Version History (12)` sub-tab bar with `<TerminalTabs>`.

**Verify:** Belief detail → click through tabs → active styling correct.

### Step 6.2: Adopt `TerminalTabs` in `SkillDetail.tsx`
Same for `Details • Version` sub-tabs.

**Verify:** Skill detail → tab switching works.

### Step 6.3: Adopt `TerminalTabs` in `AgentPage.tsx`
The top-level `Personality • Pipeline • Dreaming • Daemons • Traces` tabs.

**Verify:** `/agent` page → all tabs switch correctly, active highlight, URL sync.

### Step 6.4: Adopt `DotIcon` in List Items
Replace `<span className="text-[10px] shrink-0" style={{ color }}>●</span>` patterns with `<DotIcon color={color} />` in:
- `BeliefsSection.tsx` — belief list items
- `SkillsSection.tsx` / `SkillListItem.tsx` — skill list items
- `PipelineSection.tsx` — module list items
- `CommitmentsPanel.tsx` — commitment list items
- `ExpertisePanel.tsx` — expertise list items
- `AttractorsSection.tsx` — attractor items
- `TracesSection.tsx` — trace items
- `DreamingSection.tsx` / `StartupSection.tsx` — status dots

**Verify:** All list items across all panels render with correct colored dots.

### Step 6.5: Adopt `TerminalInput` in Title Bars and Search
Replace `bg-transparent border-b border-[#222]/40 ...` input patterns:
- `NodeExplorer.tsx` — title input
- `NotesSection.tsx` — search input
- `SpectralEchoes.tsx` — justification input

**Verify:** All inputs render, focus with green border.

---

## Phase 7: P1 — Adopt `TerminalButton` Across Remaining Codebase

### Step 7.1: `NodeExplorer.tsx` — Action Buttons
Replace `[home]`, `[#generate_title]`, `[retry]`, `[dismiss]`, `[#del]` bracket buttons with `<TerminalButton>`.

**Verify:** Center column buttons all render with correct hover colors.

### Step 7.2: `ConnectionCloud.tsx` — Canvas Controls
Replace zoom `[ + ]` `[ − ]` `[ ⟲ ]`, settling toggle, context menu `[delete node]`, commit modal `[cancel]`/`[commit branch to DAG]`, resonance `[close]`/`[confirm]`/`[dismiss]`/`[remove link]`.

**Verify:** Canvas controls all render with correct hover colors.

### Step 7.3: `SpectralEchoes.tsx` — Action Buttons
Replace `[link]` `[ignore]` `[cancel]` `[confirm link]`.

**Verify:** Spectral echoes buttons render.

### Step 7.4: `SedimentSection.tsx` — Buttons
Replace `[+ inject]`, modal buttons.

**Verify:** Sediment section buttons render.

### Step 7.5: Remaining Buttons
Scan for any remaining `text-[#666]` bracket-text buttons:
- `CreasesDropdown.tsx` — `[jump]` `[read]`
- `TracesSection.tsx` — `[jump]`
- `NewBeliefForm.tsx` / `NewSkillForm.tsx` — form buttons
- `SedimentSection.tsx` — inject/summary buttons

**Verify:** Build + lint pass. Full visual sweep.

---

## Phase 8: P1 — Split `api/client.ts` into Domain Files

*Risk: Medium-High. Touches every import in the codebase. Requires careful barrel re-export to maintain backward compatibility.*

### Decomposition Strategy

Current: `api/client.ts` (1492 lines, ~125 exports) — all API functions + all TypeScript interfaces in one file.

**New structure:**
```
api/
├── types.ts                 ← All interfaces (~350 lines)
├── auth.ts                  ← checkAuthStatus, verifyPassword, logout
├── conversations.ts         ← sendMessage, saveMessage, generateResponse, getHistory,
│                              listConversations, getConversation, deleteConversation,
│                              deleteMessage, renameConversation, generateConversationTitle,
│                              addConversationTag, removeConversationTag, getAllUniqueTags,
│                              getMemoryNodes
├── files.ts                 ← uploadFiles, getConversationFiles, deleteConversationFile, reprocessFile
├── tree.ts                  ← commitBranch, getConversationTree, getMessagePath,
│                              getMessageThinking, getMessageContext
├── notes.ts                 ← createNote, getNotes, updateNote, deleteNote
├── beliefs.ts               ← getBeliefs, createBelief, updateBelief, deleteBelief, revertBelief,
│                              getBeliefProposals, vetBeliefProposal, refineBeliefProposal,
│                              synthesizeMergeStatement
├── skills.ts                ← getSkills, getPipeline, getDbSkills, getSkillContent,
│                              updateSkill, createSkill, deleteSkill, getSkillEvents
├── personality.ts           ← getPersonality, updateCommitment, updateExpertise,
│                              updateAspirationalTraits, recalculateCommitmentVector,
│                              recalculateExpertiseVector
├── telemetry.ts             ← getMetrics, getTokens, getDaemonStatus, getSchedulerStatus,
│                              getRecentDreams, getAgent, getHealth, getFileSummary
├── sediment.ts              ← listSedimentFiles, injectSediment, getConversationInjections,
│                              removeSedimentInjection
├── links.ts                 ← createResonanceLink, confirmResonanceLink, deleteResonanceLink,
│                              getSpectralSuggestions
├── notifications.ts         ← getNotification, getNotifications, createNotification,
│                              markNotificationRead, markNotificationUnread, dismissNotification,
│                              dismissNotificationByMatch, clearNotifications, markAllNotificationsRead
└── index.ts                 ← Barrel re-export of everything (mirrors old client.ts exports)
```

### Step 8.1: Create `api/types.ts`
Extract ALL interfaces and type-only exports (no functions). Keep `BASE` constant and fetch interceptor at module level — these stay in each domain file via a shared import.

- `MetricsInfo`, `HomeostaticRecommendations`, `AttachmentInfo`, `ChatMessage`, `AgentInfo`
- `ConversationTreeNode`, `ConversationTreeLink`
- `ImageMetadata`, `WebMetadata`, `DocumentMetadata`
- `SkillInfo`, `SkillsResponse`, `DbSkillInfo`, `DbSkillsResponse`, `WorkshopResponse`
- `MetricsResponse`, `DiffractiveSourceInfo`, `DiffractiveInfo`, `BeliefEventInfo`, `BeliefNodeInfo`
- `SomaticStateInfo`, `EcosystemSnapshot`, `BeliefsResponse`, `BeliefProposalInfo`
- `ConversationTagInfo`, `MemoryNodeInfo`, `ConversationInfo`
- `ConversationTokenInfo`, `TokenResponse`, `ConversationFile`, `ConversationFilesResponse`
- `SchedulerStatusResponse`, `DaemonStatusResponse`, `DreamEntry`, `DreamHistoryResponse`
- `NoteInfo`, `SedimentFileInfo`, `SedimentInjectionInfo`
- `SpectralSuggestion`, `SkillEventInfo`, `SedimentNotification`
- `BasinBelief`, `PersonalityCommitment`, `PersonalityExpertise`, `PersonalityResponse`

**Verify:** `npm run build` — types file compiles (no imports yet, no consumers).

### Step 8.2: Create Shared `BASE` + Fetch Interceptor Module
**File:** `api/http.ts`

```ts
export const BASE = "/api"

const originalFetch = window.fetch
window.fetch = async (input, init?) => {
  const urlStr = typeof input === "string" ? input : input instanceof URL ? input.toString() : (input as Request).url
  if (urlStr.includes("/api/")) {
    const password = localStorage.getItem("aaa_password")
    if (password) {
      const headers = new Headers(init?.headers || {})
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${password}`)
      }
      return originalFetch(input, { ...init, headers })
    }
  }
  return originalFetch(input, init)
}
```

Each domain file imports `{ BASE } from "./http"`.

**Verify:** `npm run build` — compiles.

### Step 8.3: Create Domain Files (One File Per Step)
Create each domain file with its functions and type imports from `./types`. After EACH file:

**Verify:** `npm run build` — file compiles standalone.

Order (least dependencies first):
1. `api/auth.ts`
2. `api/telemetry.ts`
3. `api/conversations.ts`
4. `api/files.ts`
5. `api/tree.ts`
6. `api/notes.ts`
7. `api/beliefs.ts`
8. `api/skills.ts`
9. `api/personality.ts`
10. `api/sediment.ts`
11. `api/links.ts`
12. `api/notifications.ts`

### Step 8.4: Create `api/index.ts` Barrel Export
Re-export everything from all domain files. This is the new entry point — `api/client.ts` will be deprecated.

**Verify:** `npm run build` — barrel compiles. All exports resolve.

### Step 8.5: Update All Imports Across Codebase (~30 files)
Replace `from "../api/client"` → `from "../api"` (or `"../../api"` etc.) across the entire frontend.

**Strategy:** Use find-and-replace for the import path change:
```
Search:  from "../../api/client"  → Replace: from "../../api"
Search:  from "../../../api/client" → Replace: from "../../../api"
Search:  from "../../../../api/client" → Replace: from "../../../../api"
Search:  from "../api/client"  → Replace: from "../api"
```

**Verify:** `npm run build` + `npm run lint` — MUST pass with zero errors. If any import resolution fails, `tsc` will catch it.

### Step 8.6: Replace `client.ts` with Re-export Shim
Change `api/client.ts` to a simple re-export:

```ts
export * from "./index"
```

This ensures any remaining references (e.g., dynamic imports, uncaught paths) still work during the transition. Can be removed in a future cleanup pass.

**Verify:** `npm run build` + `npm run lint` — passes.

### Step 8.7: Visual Sweep — Full Application
Open every page and panel — verify all API calls still work (no 404s, no undefined imports).

---

## Phase 9: P2 — Decompose `ConnectionCloud.tsx` (1307 → ~500 lines)

*Risk: Medium. Canvas rendering must not break. Overlays are UI chrome only — safe to extract.*

### Decomposition Strategy

```
panels/leftpanel/
├── ConnectionCloud.tsx            ← Core: canvas, force simulation, zoom/pan (shrinks to ~500 lines)
├── ConnectionCloudOverlays.tsx    ← All UI chrome overlays: tooltip, context menu, commit modal, resonance overlay, zoom controls (~300 lines)
└── ConnectionCloudSimulation.ts   ← Pure math helpers: computeSettledLayout, getDistanceToSegment, tree→sim graph conversion (~200 lines)
```

### Step 9.1: Extract `ConnectionCloudSimulation.ts`
Pure functions (no React, no state):
- `computeSettledLayout()` (lines 47-61)
- `getDistanceToSegment()` (lines 63-?)
- `SimNode`, `SimLink` interfaces (lines 19-43) — move from inline to types file
- Any other pure layout/math helpers

**Verify:** `npm run build` — compilation ok (no consumers yet).

### Step 9.2: Extract `ConnectionCloudOverlays.tsx`
All overlay UI that renders on top of the canvas:

```tsx
// Props: all overlay state from parent
interface OverlaysProps {
  contextMenu, setContextMenu, handleDeleteNode
  hoveredNode, dimensions, zoom, pan
  committingNode, setCommittingNode, commitContent, setCommitContent, handleCommitSubmit, isCommitLoading
  selectedLink, selectedLinkPos, setSelectedLink, setSelectedLinkPos
  conversationId, refreshTree, handleZoomIn, handleZoomOut, handleResetZoom
}
```

Contains:
- `ConnectionCloudContextMenu` (lines 1152-1165)
- `ConnectionCloudZoomControls` (lines 1168-1175)
- `ConnectionCloudHoverTooltip` (lines 1178-1200)
- `ConnectionCloudCommitModal` (lines 1202-1231)
- `ConnectionCloudResonanceOverlay` (lines 1234-1298)

All sub-components memo'd.

**Verify:** `npm run build` — compiles.

### Step 9.3: Integrate into `ConnectionCloud.tsx`
- Import `ConnectionCloudOverlays` and `ConnectionCloudSimulation`
- Remove extracted code, replace with component calls
- Keep canvas rendering, event handlers, force simulation loop

**Verify:** `npm run build` + `npm run lint` → visual test: DAG renders, zoom works, tooltip appears, context menu works, commit modal opens, resonance overlay shows.

---

## Phase 10: P3 — Decompose `useChat.ts` (839 → ~300 lines)

*Risk: Medium. Core chat logic — must preserve all behavior exactly.*

### Decomposition Strategy

```
hooks/
├── useChat.ts                ← Core: send, regenerate, message state, URL sync (~300 lines)
├── useChatHelpers.ts         ← Pure utility functions: estimateTokens, getAncestorPathIds
├── useChatTree.ts            ← Derived tree computations: selectedNode, parentNode, siblingNodes, childNodes, history, treeNodes (~200 lines)
└── useChatFiles.ts           ← File management: upload, delete, reprocess, file state, isIndexing (~150 lines)
```

### Step 10.1: Extract `useChatHelpers.ts`
Pure functions with no React dependencies:
- `estimateTokens()` (lines 18-21)
- `getAncestorPathIds()` (lines 23-53)

**Verify:** `npm run build` — compiles.

### Step 10.2: Extract `useChatFiles.ts`
Custom hook managing all file-related state:

```ts
export function useChatFiles(conversationId: string, messages: ChatMessage[], setMessages: ...) {
  // useState: files, isUploading
  // useEffect: fetch files when conversation changes
  // Functions: upload, deleteFile, reprocess, refreshFiles
  return { files, isUploading, upload, deleteFile, reprocess }
}
```

**Verify:** `npm run build` — hook compiles.

### Step 10.3: Extract `useChatTree.ts`
Custom hook deriving all tree navigation data:

```ts
export function useChatTree(
  messages: ChatMessage[],
  links: ConversationTreeLink[],
  activeMessageId: number | null,
  treeNodes: ConversationTreeNode[]
) {
  // useMemo: selectedNode, parentNode, siblingNodes, childNodes, history
  // useCallback: navigateToMessage
  return { selectedNode, parentNode, siblingNodes, childNodes, history, navigateToMessage }
}
```

**Verify:** `npm run build` — hook compiles.

### Step 10.4: Integrate into `useChat.ts`
Replace extracted code with sub-hook calls. `useChat` becomes a thin orchestrator.
Each sub-hook verifiable independently.

**Verify:** `npm run build` + `npm run lint` → visual test: full chat flow (send message, receive response, navigate tree, upload files, delete files).

---

## Phase 11: P3 — Decompose `MessageBubble.tsx` (891 → ~400 lines)

*Risk: Medium-High. Complex note/tooltip/selection interactions. Design doc explicitly says "separate pass planned".*

### Decomposition Strategy

```
nodeexplorer/
├── MessageBubble.tsx         ← Core: markdown rendering, speaker header, thinking toggle (~400 lines)
├── VitalityBar.tsx           ← Vitality metrics bar with SIM/NOV/ENT/... indicators (~200 lines)
├── MessageThinking.tsx       ← Collapsible thinking display with markdown (~100 lines)
└── MessageNotes.tsx          ← Note selection, highlighting, create/edit/delete (~200 lines)
```

### Step 11.1: Extract `VitalityBar.tsx`
Already a function component within `MessageBubble.tsx` (lines 30-108 area). Move to own file with proper props interface. Memo'd.

**Verify:** `npm run build` — compiles. MessageBubble imports it.

### Step 11.2: Extract `MessageThinking.tsx`
The collapsible thinking section with lazy-loading via `getMessageThinking()`. Pass `messageId`, `thinking` text.

**Verify:** `npm run build` — compiles. Thinking toggle still works in messages.

### Step 11.3: Extract `MessageNotes.tsx`
Note selection/annotation logic — the most complex part. Handles text selection, note creation, editing, deletion, visibility badges.

**Verify:** `npm run build` → visual test: select text in message → add note → note appears with correct color badge → edit/delete works.

### Step 11.4: Integrate into `MessageBubble.tsx`
`MessageBubble` shrinks to core markdown rendering + assembling the sub-components.

**Verify:** Full visual sweep: messages render with markdown, thinking, vitality, notes — all unchanged.

---

## Phase 12: Final Verification

### Step 12.1: Full Build + Lint
```powershell
cd frontend
npm run build
npm run lint
```
Both must pass with zero errors.

### Step 12.2: Visual Sweep — All Panels
Manually verify in browser (`npm run dev`):

| Page | What to Check |
|------|---------------|
| `/` (landing) | Conversation list renders, no regressions |
| Chat workspace | Left panel (DAG + SpectralEchoes), center (NodeExplorer), right (SidePanel) — all render |
| `/agent?tab=personality&sub=traits` | Health + traits display |
| `/agent?tab=personality&sub=commitments` | List + detail, edit/delete buttons |
| `/agent?tab=personality&sub=expertise` | List + detail |
| `/agent?tab=personality&sub=beliefs` | List + detail with sub-tabs |
| `/agent?tab=personality&sub=skills` | List + detail with sub-tabs |
| `/agent?tab=pipeline` | Module list + detail |
| `/agent?tab=dreaming` | Daemon status + dream log |
| `/agent?tab=daemons` | Scheduler status |
| `/agent?tab=traces` | Notification traces + jump |

**Key checks:**
- No visual regressions (headers, buttons, metadata look identical)
- No console errors
- Telemetry polling starts/stops on panel expand/collapse
- Switching conversations doesn't leak polling
- `React.memo` prevents unnecessary renders (verify with React DevTools profiler)
- All API calls work across all panels (no 404s from API split)

### Step 12.3: Commit
```powershell
git add -A
git commit -m "refactor(frontend): comprehensive refactor — React.memo, useSyncExternalStore, EMPTY_ARRAY constants, 6 UI primitives, API domain split, file decomposition"
```

### Step 12.4: Merge Back
```powershell
git checkout feature/dynamic-personality-cascade
git merge refactor/frontend-perf-and-ui-repository
```

---

## Risk Summary

| Phase | Risk | Rollback Strategy |
|-------|------|-------------------|
| 1 (React.memo) | Very Low | Revert file changes — purely additive |
| 2 (useSyncExternalStore) | Medium | Revert `useTelemetry.ts` — store untouched |
| 3 (\|\| [] constants) | Very Low | Revert per-file |
| 4 (New UI components) | None | Delete new files |
| 5-7 (Adoption) | Medium | Each file change isolated; revert individually |
| 8 (Split API client) | Medium-High | Barrel export preserves backward compat; `git checkout -- api/client.ts` |
| 9 (Split ConnectionCloud) | Medium | Canvas core untouched; overlays are UI-only |
| 10 (Split useChat) | Medium | Sub-hooks extract pure derivations; core send/load unchanged |
| 11 (Split MessageBubble) | Medium-High | Complex note interactions — test thoroughly |
| 12 (Verification) | None | — |

## Total Files Touched

| Phase | Files Created | Files Modified |
|-------|---------------|----------------|
| 1 | 0 | 8 |
| 2 | 0 | 1 |
| 3 | 0 | 6 |
| 4 | 7 (`UI/*.tsx` + `index.ts`) | 0 |
| 5 | 0 | ~6 |
| 6 | 0 | ~12 |
| 7 | 0 | ~8 |
| 8 | 13 (`api/types.ts` + `api/http.ts` + 12 domain files + `api/index.ts`) | ~30 (all imports) + 1 (`client.ts` → shim) |
| 9 | 2 (`ConnectionCloudOverlays.tsx`, `ConnectionCloudSimulation.ts`) | 1 (`ConnectionCloud.tsx`) |
| 10 | 3 (`useChatHelpers.ts`, `useChatTree.ts`, `useChatFiles.ts`) | 1 (`useChat.ts`) |
| 11 | 3 (`VitalityBar.tsx`, `MessageThinking.tsx`, `MessageNotes.tsx`) | 1 (`MessageBubble.tsx`) |
| 12 | 0 | 0 |
| **Total** | **28** | **~75** |

## Estimated Effort

~5–6 hours for implementation, ~1 hour for visual sweep verification across all 12 phases.
