import { useState, useEffect } from "react"
import type { SkillInfo, SkillsResponse } from "../api/client"
import { getSkills } from "../api/client"

const CATEGORY_COLORS: Record<string, string> = {
  perception: "#4ade80",
  memory: "#60a5fa",
  reasoning: "#facc15",
  action: "#f87171",
}

function SkillRow({ skill }: { skill: SkillInfo }) {
  const color = CATEGORY_COLORS[skill.category] || "#888"
  return (
    <div className="py-1.5 border-b border-[#1a1a1a] last:border-b-0">
      <div className="flex items-center gap-1.5">
        <span
          style={{ color: skill.status ? color : "#ef4444" }}
          className="text-[8px] leading-none"
        >
          {skill.status ? "\u25CF" : "\u25CB"}
        </span>
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
    </div>
  )
}

function SectionHeader({
  label,
  count,
  open,
  onToggle,
}: {
  label: string
  count: number
  open: boolean
  onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center gap-1.5 py-1 text-left hover:text-[#aaa] text-[#888] text-xs transition-colors"
    >
      <span className="text-[10px]">{open ? "\u25BC" : "\u25B6"}</span>
      <span>
        {label}
      </span>
      <span className="text-[#444]">({count})</span>
    </button>
  )
}

export function SidePanel() {
  const [collapsed, setCollapsed] = useState(true)
  const [data, setData] = useState<SkillsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pipelineOpen, setPipelineOpen] = useState(false)
  const [skillsOpen, setSkillsOpen] = useState(false)

  useEffect(() => {
    getSkills()
      .then(setData)
      .catch((e) => setError(e.message))
  }, [])

  const hasSkills = (data?.on_demand.length ?? 0) > 0

  return (
    <div
      className={`
        border-[#222] bg-[#0c0c0c]
        md:border-l md:border-t-0 md:h-full
        border-t
        flex flex-col shrink-0
        overflow-hidden
        transition-all duration-200
        ${collapsed ? "md:w-9 w-full" : "md:w-120 w-full"}
      `}
    >
      {/* ---- collapsed: thin toggle strip ---- */}
      {collapsed && (
        <button
          onClick={() => setCollapsed(false)}
          className="
            flex items-center gap-1.5 shrink-0
            text-xs text-[#555] hover:text-[#888]
            transition-colors
            md:flex-col md:justify-start md:gap-2 md:py-3 md:px-0
            md:h-full
            flex-row justify-start py-2 px-3
            select-none
          "
        >
          <span className="text-[10px]">{"\u25C0"}</span>
          <span className="md:[writing-mode:vertical-rl] md:text-[10px] md:tracking-wider text-[11px]">
            pipeline
          </span>
        </button>
      )}

      {/* ---- open: header bar + content ---- */}
      {!collapsed && (
        <>
          <div className="flex items-center shrink-0 px-3 py-2 border-b border-[#222]">
            <button
              onClick={() => setCollapsed(true)}
              className="flex items-center gap-1.5 text-[10px] text-[#555] hover:text-[#888] transition-colors"
            >
              <span>{"\u25B6"}</span>
              <span>close</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 pb-3">
            {error && (
              <p className="text-[10px] text-[#ef4444] my-2">
                Failed to load: {error}
              </p>
            )}

            {!data && !error && (
              <p className="text-[10px] text-[#555] animate-pulse mt-2">loading...</p>
            )}

            {data && (
              <div className="flex flex-col gap-1 mt-1">
                <SectionHeader
                  label="Pipeline"
                  count={data.pipeline.length}
                  open={pipelineOpen}
                  onToggle={() => setPipelineOpen(!pipelineOpen)}
                />
                {pipelineOpen && (
                  <div className="pl-3">
                    {data.pipeline.map((s) => (
                      <SkillRow key={s.name} skill={s} />
                    ))}
                  </div>
                )}

                {hasSkills && (
                  <>
                    <SectionHeader
                      label="Skills"
                      count={data.on_demand.length}
                      open={skillsOpen}
                      onToggle={() => setSkillsOpen(!skillsOpen)}
                    />
                    {skillsOpen && (
                      <div className="pl-3">
                        {data.on_demand.map((s) => (
                          <SkillRow key={s.name} skill={s} />
                        ))}
                      </div>
                    )}
                  </>
                )}

                {!hasSkills && (
                  <p className="text-[10px] text-[#444] mt-1">
                    no on-demand skills available
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
