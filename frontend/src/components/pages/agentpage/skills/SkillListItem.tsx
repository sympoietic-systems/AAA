import { memo } from "react"
import type { DbSkillInfo } from "../../../../api/client"

interface SkillListItemProps {
  s: DbSkillInfo
  isSelected: boolean
  isBaseline: boolean
}

export const SkillListItem = memo(function SkillListItem({ s, isSelected, isBaseline }: SkillListItemProps) {
  const isCollapsed = s.lifecycle_stage === "collapsed"
  const isProposed = s.lifecycle_stage === "nucleation"
  const isMerged = isCollapsed && s.changelog?.startsWith("Merged")
  
  const iconColor = isBaseline 
    ? "text-[#a78bfa]" 
    : isMerged
      ? "text-[#c084fc]"
      : isCollapsed 
        ? "text-[#ef4444]" 
        : isProposed 
          ? "text-[#a78bfa]" 
          : "text-[#4ade80]"
        
  const icon = isBaseline 
    ? "◆" 
    : isMerged
      ? "⎋"
      : isCollapsed 
        ? "✖" 
        : isProposed 
          ? "▲" 
          : "◇"

  return (
    <div
      data-skill-name={s.name}
      data-selected={isSelected ? "true" : undefined}
      className={`
        flex items-center gap-1.5 px-1.5 py-1 cursor-pointer
        border-l-2 transition-colors
        ${isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}
      `}
    >
      <span className={`text-[10px] shrink-0 ${iconColor}`}>
        {icon}
      </span>
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">
        {s.name} <span className="text-[#666] text-[9px] font-normal">v{s.version}</span>
      </span>
      <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">
        m:{s.ontological_mass.toFixed(2)}
      </span>
      <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">
        {(s.confidence * 100).toFixed(0)}%
      </span>
    </div>
  )
})
