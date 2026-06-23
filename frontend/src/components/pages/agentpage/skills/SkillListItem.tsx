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
    ? "text-semantic-purple" 
    : isMerged
      ? "text-semantic-purple/80"
      : isCollapsed 
        ? "text-semantic-red" 
        : isProposed 
          ? "text-semantic-purple" 
          : "text-semantic-green"
        
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
        ${isSelected ? "border-action-hover bg-action-hover/5" : "border-transparent hover:bg-[#111]"}
      `}
    >
      <span className={`text-[10px] shrink-0 ${iconColor}`}>
        {icon}
      </span>
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-ui-secondary">
        {s.name} <span className="text-ui-dim text-[9px] font-normal">v{s.version}</span>
      </span>
      <span className="text-[8px] font-mono text-ui-dim shrink-0 hidden md:inline">
        m:{s.ontological_mass.toFixed(2)}
      </span>
      <span className="text-[10px] font-mono font-bold text-ui-dim shrink-0">
        {(s.confidence * 100).toFixed(0)}%
      </span>
    </div>
  )
})
