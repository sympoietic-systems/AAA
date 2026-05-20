import { useState, useEffect } from "react"
import type { AttachmentInfo, SkillInfo, SkillsResponse, MetricsResponse, TokenResponse } from "../api/client"
import { getSkills, getMetrics, getTokens } from "../api/client"

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

function TokensSection() {
  const [tokens, setTokens] = useState<TokenResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  useEffect(() => {
    const poll = () => {
      getTokens().then(setTokens).catch((e) => setError(e.message))
    }
    poll()
    const interval = setInterval(poll, 5000)
    return () => clearInterval(interval)
  }, [])

  if (error && !tokens) {
    return <p className="text-[9px] text-[#ef4444]">{error}</p>
  }

  if (!tokens) {
    return <p className="text-[9px] text-[#444]">waiting for data...</p>
  }

  const { conversations, system_prompt_tokens, grand_total_tokens } = tokens

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[8px] leading-none text-[#60a5fa]">{"\u25CF"}</span>
        <span className="text-[10px] text-[#888]">tokens</span>
        <span className="text-[9px] ml-auto text-[#60a5fa]">
          {grand_total_tokens.toLocaleString()} total
        </span>
      </div>

      <div className="text-[9px] text-[#666] mb-1">
        system: {system_prompt_tokens.toLocaleString()}
      </div>

      {conversations.length === 0 && (
        <p className="text-[9px] text-[#555]">no conversations</p>
      )}

      {conversations.slice(0, detailOpen ? undefined : 3).map((c) => (
        <div key={c.conversation_id} className="py-1 border-b border-[#1a1a1a] last:border-b-0">
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-[#aaa] truncate flex-1">
              {c.title || c.conversation_id.slice(0, 8)}
            </span>
            <span className="text-[8px] text-[#60a5fa] font-bold">
              {c.total_tokens.toLocaleString()}
            </span>
          </div>
          <div className="flex gap-3 mt-0.5">
            <span className="text-[8px] text-[#666]">
              usr:{c.user_tokens.toLocaleString()}
            </span>
            <span className="text-[8px] text-[#666]">
              agt:{c.agent_tokens.toLocaleString()}
            </span>
            {c.thinking_tokens > 0 && (
              <span className="text-[8px] text-[#666]">
                thk:{c.thinking_tokens.toLocaleString()}
              </span>
            )}
          </div>
        </div>
      ))}

      {conversations.length > 3 && (
        <button
          onClick={() => setDetailOpen(!detailOpen)}
          className="text-[8px] text-[#555] hover:text-[#888] mt-1"
        >
          {detailOpen ? "show less" : `+${conversations.length - 3} more`}
        </button>
      )}

      <div className="text-[8px] text-[#555] mt-1.5">
        grand total: {grand_total_tokens.toLocaleString()} tok
      </div>
    </div>
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

  const vitality = metrics?.latest?.conversation_vitality
  const paskHealth = metrics?.latest?.paskian_health
  const state = metrics?.recommendations?.state ?? "unknown"
  const stateColor =
    state === "healthy" ? "#4ade80" :
    state === "compensating" ? "#facc15" :
    state === "critical" ? "#ef4444" : "#555"

  const renderBar = (label: string, fullName: string, value: number | null | undefined, max: number, hint: string) => {
    const pct = value != null ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
    const display = value != null ? (value < 0.01 ? value.toFixed(4) : value.toFixed(3)) : "\u2014"
    return (
      <div className="flex items-center gap-1.5 group relative" key={label}>
        <span className="w-7 text-[9px] text-[#555] text-right">{label}</span>
        <div className="w-12 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
          <div className="h-full rounded-sm bg-[#4ade80]" style={{ width: `${pct}%`, opacity: 0.6 }} />
        </div>
        <span className="text-[9px] text-[#666] w-10 text-right">{display}</span>
        <div className="
          absolute bottom-full left-0 mb-1 px-2 py-1
          bg-[#1a1a1a] border border-[#333] rounded
          text-[10px] text-[#aaa] leading-snug
          whitespace-nowrap z-50
          opacity-0 group-hover:opacity-100
          transition-opacity duration-150
          pointer-events-none
        ">
          <div className="text-[#4ade80] text-[11px] font-bold">{fullName}</div>
          <div className="text-[#888]">{display} / {max}</div>
          <div className="text-[#666] max-w-48 whitespace-normal">{hint}</div>
        </div>
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
          {state} {vitality != null ? `vit:${vitality.toFixed(2)}` : ""}{paskHealth != null ? ` ph:${paskHealth.toFixed(2)}` : ""}
        </span>
      </div>

      {error && <p className="text-[9px] text-[#ef4444]">{error}</p>}

      {metrics?.latest && (
        <div className="space-y-0.5">
          {renderBar("sim", "pairwise similarity", metrics.latest.pairwise_similarity, 1.0,
            "Is this input repeating the previous one? >0.85 = near-duplicate")}
          {renderBar("nov", "conceptual novelty", metrics.latest.conceptual_novelty, 1.0,
            "Has anything similar been said before? <0.15 = concept exhaustion")}
          {renderBar("ent", "rolling entropy", metrics.latest.rolling_entropy, 0.25,
            "Is the conversation monotonous over time? <0.01 = entropy collapse")}
          {renderBar("coup", "coupling coherence", metrics.latest.coupling_coherence, 1.0,
            "Is the agent responding to the human? <0.15 = dissociation, >0.85 = echo")}
          {renderBar("divr", "agent self-divergence", metrics.latest.agent_self_divergence, 1.0,
            "Is the agent repeating itself? <0.15 = self-loop")}
          {renderBar("rP", "reverse perturbation", metrics.latest.reverse_perturbation, 1.0,
            "Did the agent's last response reshape the human? <0.10 = stagnant")}
          {renderBar("srp", "surprise index", metrics.latest.surprise_index, 1.0,
            "Distance from expected phase space? >0.40 = phase disruption")}
          {renderBar("mpi", "mutual perturbation", metrics.latest.mutual_perturbation, 1.0,
            "Product of coupling x reverse perturbation. <0.05 = deadlock")}
          {renderBar("bore", "boringness", metrics.latest.boringness, 1.0,
            "Joint failure to perturb in either direction? >0.60 = Paskian boredom")}
          {renderBar("vel", "conceptual velocity", metrics.latest.conceptual_velocity, 1.0,
            "Is the entailment mesh drifting? <0.02 = frozen, >0.80 = noise")}
          {renderBar("drr", "divergence resolution ratio", metrics.latest.divergence_resolution_ratio, 1.0,
            "Does perturbation lead to resolution? Positive = convergence, negative = rejection")}
        </div>
      )}

      {!metrics && !error && (
        <p className="text-[9px] text-[#444]">waiting for data...</p>
      )}

      {metrics?.latest?.phase_shifts && metrics.latest.phase_shifts.length > 0 && (
        <div className="mt-1.5">
          <span className="text-[9px] text-[#facc15]">phase shifts:</span>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {metrics.latest.phase_shifts.map((s, i) => (
              <span key={i} className="text-[8px] text-[#facc15] border border-[#332200] px-1 rounded">
                {s.event} {s.direction === "rise" ? "\u2191" : "\u2193"}{s.delta.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
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

export function SidePanel({ uploadedFiles = [] }: { uploadedFiles?: AttachmentInfo[] }) {
  const [collapsed, setCollapsed] = useState(true)
  const [data, setData] = useState<SkillsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pipelineOpen, setPipelineOpen] = useState(false)
  const [skillsOpen, setSkillsOpen] = useState(false)
  const [healthOpen, setHealthOpen] = useState(true)
  const [tokensOpen, setTokensOpen] = useState(true)
  const [sedimentOpen, setSedimentOpen] = useState(true)

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

            <div className="flex flex-col gap-1 mt-1">
              <SectionHeader
                label="Tokens"
                count={0}
                open={tokensOpen}
                onToggle={() => setTokensOpen(!tokensOpen)}
              />
              {tokensOpen && (
                <div className="pl-3">
                  <TokensSection />
                </div>
              )}
            </div>

            {uploadedFiles.length > 0 && (
              <div className="flex flex-col gap-1 mt-1">
                <SectionHeader
                  label="Sediment"
                  count={uploadedFiles.length}
                  open={sedimentOpen}
                  onToggle={() => setSedimentOpen(!sedimentOpen)}
                />
                {sedimentOpen && (
                  <div className="pl-3">
                    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
                      {uploadedFiles.map((f) => (
                        <div key={f.file_name} className="flex items-center gap-1.5 py-1 border-b border-[#1a1a1a] last:border-b-0">
                          <span className="text-xs">{f.file_type === "pdf" ? "\uD83D\uDCC4" : f.file_type === "md" ? "\uD83D\uDCDD" : "\uD83D\uDCC4"}</span>
                          <span className="text-[10px] text-[#aaa] truncate flex-1">{f.file_name}</span>
                          {f.token_count > 0 && (
                            <span className="text-[8px] text-[#666]">
                              {f.token_count >= 1000 ? `${(f.token_count / 1000).toFixed(1)}k` : f.token_count} tok
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
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
