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
