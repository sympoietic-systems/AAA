import { useState } from "react"
import type { SkillInfo } from "../../api/client"
import telemetrySchemas from "../../config/telemetry_schemas.json"

const { CATEGORY_COLORS } = telemetrySchemas as { CATEGORY_COLORS: Record<string, string> }

interface SkillRowProps {
  skill: SkillInfo
}

export function SkillRow({ skill }: SkillRowProps) {
  const [open, setOpen] = useState(false)
  const color = CATEGORY_COLORS[skill.category] || "#888"
  const hasChildren = skill.children && skill.children.length > 0

  return (
    <div className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
      <div className="flex items-center gap-1.5">
        {hasChildren ? (
          <button
            onClick={() => setOpen(!open)}
            className="text-[8px] leading-none hover:opacity-80"
            style={{ color: skill.status ? color : "#ef4444" }}
          >
            {open ? "▼" : "▶"}
          </button>
        ) : (
          <span
            style={{ color: skill.status ? color : "#ef4444" }}
            className="text-[8px] leading-none"
          >
            {skill.status ? "●" : "○"}
          </span>
        )}
        <span className="text-[#4ade80] text-xs font-bold">{skill.name}</span>
        <span
          className="text-[9px] px-1 py-px rounded border ml-auto"
          style={{ borderColor: color + "60", color }}
        >
          {skill.category}
        </span>
      </div>
      <p className="text-[10px] text-[#666] mt-0.5 ml-2.5 leading-snug">
        {skill.description}
      </p>
      {skill.triggers.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-0.5 ml-2.5">
          {skill.triggers.map((t) => (
            <span
              key={t}
              className="text-[8px] text-[#555] border border-[#222] px-1 rounded"
            >
              {t}
            </span>
          ))}
        </div>
      )}
      {hasChildren && open && (
        <div className="mt-0.5 ml-4 pl-2 border-l border-[#222]">
          {skill.children.map((child) => (
            <SkillRow key={child.name} skill={child} />
          ))}
        </div>
      )}
    </div>
  )
}
