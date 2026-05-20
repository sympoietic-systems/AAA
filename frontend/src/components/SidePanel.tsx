import { useState, useEffect } from "react"
import type { SkillInfo, SkillsResponse, MetricsResponse } from "../api/client"
import { getSkills, getMetrics } from "../api/client"

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
      <span>{label}</span>
      <span className="text-[#444]">({count})</span>
    </button>
  )
}

function HealthSection() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const poll = () => {
      getMetrics().then(setMetrics).catch((e) => setError(e.message))
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])

  const deficit = metrics?.latest?.homeostatic_deficit
  const state = metrics?.recommendations?.state ?? "unknown"
  const stateColor =
    state === "healthy" ? "#4ade80" :
    state === "compensating" ? "#facc15" :
    state === "critical" ? "#ef4444" : "#555"

  const renderBar = (label: string, value: number | null | undefined, max: number) => {
    const pct = value != null ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
    const display = value != null ? (value < 0.01 ? value.toFixed(4) : value.toFixed(3)) : "\u2014"
    return (
      <div className="flex items-center gap-1.5" key={label}>
        <span className="w-7 text-[9px] text-[#555] text-right">{label}</span>
        <div className="w-16 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
          <div className="h-full rounded-sm bg-[#4ade80]" style={{ width: `${pct}%`, opacity: 0.6 }} />
        </div>
        <span className="text-[9px] text-[#666] w-10 text-right">{display}</span>
      </div>
    )
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span
          className="text-[8px] leading-none"
          style={{ color: stateColor }}
        >
          {"\u25CF"}
        </span>
        <span className="text-[10px] text-[#888]">vitality</span>
        <span className="text-[9px] ml-auto" style={{ color: stateColor }}>
          {state} {deficit != null ? `\u0394:${deficit.toFixed(2)}` : ""}
        </span>
      </div>

      {error && <p className="text-[9px] text-[#ef4444]">{error}</p>}

      {metrics?.latest && (
        <div className="space-y-0.5">
          {renderBar("sim", metrics.latest.pairwise_similarity, 1.0)}
          {renderBar("nov", metrics.latest.conceptual_novelty, 1.0)}
          {renderBar("ent", metrics.latest.rolling_entropy, 0.25)}
          {renderBar("coup", metrics.latest.coupling_coherence, 1.0)}
          {renderBar("divr", metrics.latest.agent_self_divergence, 1.0)}
        </div>
      )}

      {!metrics && !error && (
        <p className="text-[9px] text-[#444]">waiting for data...</p>
      )}

      {metrics?.recommendations?.triggered_flags && metrics.recommendations.triggered_flags.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {metrics.recommendations.triggered_flags.map((f) => (
            <span key={f} className="text-[8px] text-[#f87171] border border-[#3a1a1a] px-1 rounded">
              {f}
            </span>
          ))}
        </div>
      )}

      {metrics?.recommendations?.temperature?.delta !== undefined && metrics.recommendations.temperature.delta !== 0 && (
        <div className="mt-1 text-[9px] text-[#666]">
          param: T{metrics.recommendations.temperature.value.toFixed(2)}
          {metrics.recommendations.temperature.clamped ? " (clamped)" : ""}
        </div>
      )}
    </div>
  )
}

export function SidePanel() {
  const [collapsed, setCollapsed] = useState(true)
  const [data, setData] = useState<SkillsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pipelineOpen, setPipelineOpen] = useState(false)
  const [skillsOpen, setSkillsOpen] = useState(false)
  const [healthOpen, setHealthOpen] = useState(true)

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

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Vitality"
                count={0}
                open={healthOpen}
                onToggle={() => setHealthOpen(!healthOpen)}
              />
              {healthOpen && (
                <div className="pl-3">
                  <HealthSection />
                </div>
              )}
            </div>

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
