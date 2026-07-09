import { useState, useEffect } from "react"
import { DreamingSection } from "./DreamingSection"
import { PersonalitySection } from "./PersonalitySection"
import { StartupSection } from "./StartupSection"
import { PipelineSection } from "./PipelineSection"
import { TracesSection } from "./TracesSection"
import { TerminalTabs, HeaderContainer, HeaderIndicator, HeaderLogo, HeaderSeparator, HeaderLabel, HeaderActionButton, CreasesDropdown, UnifiedFooter } from "../../UI"

type TabId = "personality" | "dreaming" | "daemons" | "pipeline" | "traces"

const TABS: { key: TabId; label: string }[] = [
  { key: "personality", label: "Personality" },
  { key: "pipeline", label: "Pipeline" },
  { key: "dreaming", label: "Dreaming" },
  { key: "daemons", label: "Daemons" },
  { key: "traces", label: "Traces" },
]

interface Props {
  onGoHome: () => void
}

export function AgentPage({ onGoHome }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>(() => {
    const params = new URLSearchParams(window.location.search)
    let tab = params.get("tab")
    if (tab) {
      // Legacy URLs: redirect old tab names to personality with sub-tab
      if (tab === "beliefs" || tab === "belief") return "personality"
      if (tab === "skills" || tab === "skill") return "personality"
      if (tab === "trace") return "traces"
      if (TABS.some((t) => t.key === tab)) return tab as TabId
    }
    return "personality"
  })

  const [initialSelectedId, setInitialSelectedId] = useState<string | undefined>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get("id") || undefined
  })

  // Derive initial sub-tab from URL: /agent?tab=beliefs&id=X → sub=beliefs
  const [initialSubTab, setInitialSubTab] = useState<string | undefined>(() => {
    const params = new URLSearchParams(window.location.search)
    const tab = params.get("tab")
    if (tab === "beliefs" || tab === "belief") return "beliefs"
    if (tab === "skills" || tab === "skill") return "skills"
    // Also support explicit sub param: ?tab=personality&sub=beliefs
    const sub = params.get("sub")
    if (sub) return sub
    return undefined
  })

  // Sync state changes back to search parameters for refreshing/bookmarking
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    params.set("tab", activeTab)
    if (initialSelectedId) {
      params.set("id", initialSelectedId)
    } else {
      params.delete("id")
    }
    // Keep sub param if navigating from a legacy URL
    if (params.has("sub") && activeTab !== "personality") {
      params.delete("sub")
    }
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, "", newUrl)
  }, [activeTab, initialSelectedId])

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Header — single line */}
      <HeaderContainer>
        <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none flex items-center gap-1.5">
          <HeaderIndicator intent="purple" />
          <HeaderLogo href="/nodes" />
          <HeaderSeparator />
          <HeaderLabel intent="purple">agent</HeaderLabel>
        </span>
        <div className="flex items-center gap-4">
          <CreasesDropdown />
          <HeaderActionButton href="/search">
            ⌕ search
          </HeaderActionButton>
          <HeaderActionButton href="/research">
            research
          </HeaderActionButton>
        </div>
      </HeaderContainer>

      {/* Tab bar — terminal-like, minimal, wraps on mobile */}
      <TerminalTabs
        tabs={TABS}
        active={activeTab}
        onChange={(key) => { setActiveTab(key as TabId); setInitialSelectedId(undefined) }}
        className="px-4 py-2 shrink-0 text-[11px] select-none"
      />

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {activeTab === "personality" && (
          <PersonalitySection
            initialSelectedId={initialSubTab ? initialSelectedId : undefined}
            initialSubTab={initialSubTab}
          />
        )}
        {activeTab === "pipeline" && <PipelineSection />}
        {activeTab === "dreaming" && <DreamingSection />}
        {activeTab === "daemons" && <StartupSection />}
        {activeTab === "traces" && (
          <TracesSection
            onNavigateToEntity={(type, id) => {
              if (type.startsWith("skill") || type.startsWith("belief") ||
                  type.startsWith("commitment") || type.startsWith("expertise") || type === "personality") {
                setActiveTab("personality")
                if (type.startsWith("skill")) setInitialSubTab("skills")
                else if (type.startsWith("commitment") || type.startsWith("expertise") || type === "personality") {
                  setInitialSubTab(undefined)
                } else {
                  setInitialSubTab("beliefs")
                }
                setInitialSelectedId(id)
              } else {
                setInitialSelectedId(id)
              }
            }}
          />
        )}
      </div>
      <UnifiedFooter />
    </div>
  )
}
