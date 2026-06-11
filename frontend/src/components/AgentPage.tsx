import { useState } from "react"
import { BeliefsSection } from "./agentpage/BeliefsSection"
import { DreamingSection } from "./agentpage/DreamingSection"
import { StartupSection } from "./agentpage/StartupSection"
import { SkillsSection } from "./agentpage/SkillsSection"

type TabId = "beliefs" | "dreaming" | "daemons" | "skills"

const TABS: { id: TabId; label: string }[] = [
  { id: "beliefs", label: "Beliefs" },
    { id: "skills", label: "Skills" },
  { id: "dreaming", label: "Dreaming" },
  { id: "daemons", label: "Daemons" },
]

interface Props {
  onGoHome: () => void
  onGoConversation?: () => void
}

export function AgentPage({ onGoHome, onGoConversation }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("beliefs")

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <span className="text-[11px] text-[#444] tracking-widest uppercase select-none">
          <span className="text-[#a892ee]">■</span>
          <span className="ml-2">symbia</span>
          <span className="text-[#333] mx-2">//</span>
          <span>agent</span>
        </span>
        <div className="flex items-center gap-4">
          <button
            onClick={onGoHome}
            className="text-[11px] text-[#444] hover:text-[#888] transition-colors cursor-pointer select-none"
          >
            [home]
          </button>
          {onGoConversation && (
            <button
              onClick={onGoConversation}
              className="text-[11px] text-[#444] hover:text-[#888] transition-colors cursor-pointer select-none"
            >
              [back to chat]
            </button>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-[#2d2d3d] gap-1 px-4 py-1.5 shrink-0 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-2.5 py-0.5 text-[11px] rounded font-bold tracking-wide uppercase transition-all duration-200 border whitespace-nowrap cursor-pointer select-none ${
              activeTab === tab.id
                ? "bg-[#1e1e2e] text-[#94a3b8] border-[#475569]/40"
                : "text-[#94a3b8]/40 border-transparent hover:text-[#94a3b8]/70 hover:bg-[#111]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {activeTab === "beliefs" && <BeliefsSection />}
        {activeTab === "skills" && <SkillsSection />}
        {activeTab === "dreaming" && <DreamingSection />}
        {activeTab === "daemons" && <StartupSection />}
      </div>
    </div>
  )
}
