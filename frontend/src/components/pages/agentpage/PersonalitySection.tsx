import { useState } from "react"
import { TraitsPanel } from "./TraitsPanel"
import { CommitmentsPanel } from "./CommitmentsPanel"
import { ExpertisePanel } from "./ExpertisePanel"
import { BeliefsSection } from "./BeliefsSection"
import { SkillsSection } from "./SkillsSection"

/* ── Pure routing shell — each sub-tab fetches its own data ── */

type SubTabId = "traits" | "commitments" | "expertise" | "beliefs" | "skills"

const SUB_TABS: { id: SubTabId; label: string }[] = [
  { id: "traits", label: "Traits & Health" },
  { id: "commitments", label: "Commitments" },
  { id: "expertise", label: "Expertise" },
  { id: "beliefs", label: "Beliefs" },
  { id: "skills", label: "Skills" },
]

interface PersonalitySectionProps {
  initialSelectedId?: string
  initialSubTab?: string
}

export function PersonalitySection({ initialSelectedId, initialSubTab }: PersonalitySectionProps) {
  const [subTab, setSubTab] = useState<SubTabId>(() => {
    if (initialSubTab && SUB_TABS.some(t => t.id === initialSubTab)) {
      return initialSubTab as SubTabId
    }
    return "traits"
  })

  return (
    <div>
      {/* Sub-tab bar — terminal-like, minimal, wraps on mobile */}
      <div className="flex flex-wrap gap-x-2 gap-y-1 mb-4 text-[10px] select-none px-4">
        {SUB_TABS.map((tab, i) => (
          <span key={tab.id} className="flex items-center gap-x-2 whitespace-nowrap">
            {i > 0 && <span className="text-[#333]">•</span>}
            <button
              onClick={() => setSubTab(tab.id)}
              className={`cursor-pointer transition-colors ${
                subTab === tab.id
                  ? "text-[#94a3b8]"
                  : "text-[#444] hover:text-[#777]"
              }`}
            >
              {tab.label}
            </button>
          </span>
        ))}
      </div>

      {/* Sub-tab content — each component is self-supporting */}
      <div className="px-4 py-2">
        {subTab === "traits" && <TraitsPanel />}
        {subTab === "commitments" && <CommitmentsPanel />}
        {subTab === "expertise" && <ExpertisePanel />}
        {subTab === "beliefs" && <BeliefsSection initialSelectedId={initialSelectedId} />}
        {subTab === "skills" && <SkillsSection initialSelectedId={initialSelectedId} />}
      </div>
    </div>
  )
}
