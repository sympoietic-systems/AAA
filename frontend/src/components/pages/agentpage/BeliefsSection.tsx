import { useState, useEffect, useRef, memo } from "react"
import { getBeliefs, getAgent } from "../../../api/client"
import type { BeliefsResponse, BeliefNodeInfo } from "../../../api/client"
import { NewBeliefForm } from "./beliefs/NewBeliefForm"
import { BeliefDetail } from "./beliefs/BeliefDetail"

// ─── Helpers ───────────────────────────────────────────────

function getCategoryColor(c: string) {
  switch (c.toLowerCase()) {
    case "foundational": return "#4ade80"
    case "ontological": return "#a78bfa"
    case "methodological": return "#facc15"
    default: return "#60a5fa"
  }
}

function getStageColor(s: string) {
  switch (s) {
    case "nucleation": return "#f59e0b"
    case "accretion": return "#fb923c"
    case "crystallized": return "#4ade80"
    case "senescence": return "#94a3b8"
    case "collapsed": return "#ef4444"
    default: return "#6c6c8a"
  }
}

function getStageLabel(s: string) {
  switch (s) {
    case "nucleation": return "nucleating"
    case "accretion": return "accreting"
    case "crystallized": return "crystallized"
    case "senescence": return "senescing"
    case "collapsed": return "collapsed"
    case "faded": return "faded"
    default: return s
  }
}

// ─── Ecosystem Metric ─────────────────────────────────────

function EcoMetric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <span className="w-[calc(50%-0.5rem)] md:w-auto">
      <span className="text-[#666]">{label}:</span>{" "}
      <span className={accent ? "text-[#4ade80] font-bold" : "text-[#ccc]"}>{value}</span>
    </span>
  )
}

// ─── Collapsible Section Wrapper ──────────────────────────

function CollapsibleSection({
  label, count, icon, iconColor, children, defaultOpen = true,
}: {
  label: string; count: number; icon: string; iconColor?: string; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 w-full text-left cursor-pointer select-none pb-0.5"
      >
        <span className="text-[9px] text-[#666] font-mono leading-none">{open ? "▼" : "▶"}</span>
        <span style={{ color: iconColor }} className="text-[10px]">{icon}</span>
        <span className="text-[#6c6c8a] font-mono text-[9px] uppercase tracking-wider">{label}</span>
        <span className="text-[9px] text-[#444] ml-0.5">({count})</span>
      </button>
      {open && <div className="space-y-0.5">{children}</div>}
    </div>
  )
}

// ─── Compact Node List Item ───────────────────────────────

function NodeListItem({
  b, isSelected, ghost, stageBadge, stageBadgeColor,
}: {
  b: BeliefNodeInfo; isSelected: boolean; ghost?: boolean; stageBadge?: string; stageBadgeColor?: string
}) {
  const catColor = getCategoryColor(b.category)
  const stage = b.lifecycle_stage || "crystallized"
  const isProto = stage === "nucleation" || stage === "accretion"
  const isGhost = ghost || stage === "collapsed" || stage === "faded"

  return (
    <div
      data-belief-id={b.id}
      data-selected={isSelected ? "true" : undefined}
      className={`
        flex items-center gap-1.5 px-1.5 py-1 cursor-pointer
        border-l-2 transition-colors
        ${isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}
        ${isGhost ? "opacity-50" : isProto ? "opacity-75" : ""}
      `}
    >
      <span className="text-[9px] leading-none shrink-0" style={{ color: isProto ? getStageColor(stage) : isGhost ? "#ef4444" : catColor }}>
        {isProto ? "◇" : isGhost ? "◆" : "●"}
      </span>
      {isGhost && <span className="text-[8px] shrink-0">👻</span>}
      <span className={`font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb] ${isGhost ? "line-through" : ""}`}>
        {b.label} <span className="text-[#555] text-[9px] font-normal">v{b.version}</span>
      </span>
      {stageBadge && stageBadgeColor && (
        <span
          className="text-[8px] uppercase font-mono px-1 py-px rounded shrink-0"
          style={{ color: stageBadgeColor, border: `1px solid ${stageBadgeColor}40`, backgroundColor: `${stageBadgeColor}10` }}
        >
          {stageBadge}
        </span>
      )}
      <span className="text-[8px] font-mono text-[#555] shrink-0 hidden md:inline">
        m:{isProto ? b.ontological_mass.toFixed(3) : b.ontological_mass.toFixed(1)}
      </span>
      <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">
        {(b.confidence * 100).toFixed(0)}%
      </span>
    </div>
  )
}

interface BeliefsSectionProps {
  initialSelectedId?: string
}

function BeliefsSectionComponent({ initialSelectedId }: BeliefsSectionProps) {
  const [data, setData] = useState<BeliefsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState<boolean>(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getBeliefs(null as any)
      .then(setData)
      .catch(e => setError(e.message || "Failed to fetch beliefs"))

    getAgent()
      .then(info => setAgentFlux(!!info.agent_flux))
      .catch(() => setAgentFlux(false))
  }, [])

  // Auto-select belief when initialSelectedId changes or data is loaded
  useEffect(() => {
    if (initialSelectedId && data) {
      const rawBeliefs = data.beliefs || []
      const rawProtos = data.proto_beliefs || []
      const rawGhosts = data.ghosts || []
      const all = [...rawBeliefs, ...rawProtos, ...rawGhosts]
      const matched = all.find(b => b.id === initialSelectedId || b.label === initialSelectedId)
      if (matched) {
        setSelectedId(matched.id)
      }
    }
  }, [initialSelectedId, data])

  // Scroll to detail on mobile when a belief is selected or is adding
  useEffect(() => {
    if ((!selectedId && !isAdding) || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedId, isAdding])

  if (error && !data) return <p className="text-[10px] text-[#ef4444] font-mono">{error}</p>
  if (!data) return <p className="text-[10px] text-[#444] font-mono">waiting for data...</p>

  const { beliefs: rawBeliefs, proto_beliefs: rawProtos, ghosts: rawGhosts, somatic, ecosystem } = data

  const isSkillBelief = (b: BeliefNodeInfo) => b.label?.startsWith("skill:") ?? false
  const beliefs = (rawBeliefs || []).filter(b => !isSkillBelief(b))
  const proto_beliefs = (rawProtos || []).filter(b => !isSkillBelief(b))
  const ghosts = (rawGhosts || []).filter(b => !isSkillBelief(b))

  const allBeliefs = [...beliefs, ...proto_beliefs, ...ghosts]
  const selected = (selectedId ? allBeliefs.find(b => b.id === selectedId) : null) || null

  const handleUpdate = (updatedBelief: BeliefNodeInfo) => {
    setData(prev => {
      if (!prev) return null
      const updateList = (list: BeliefNodeInfo[]) =>
        (list || []).map(b => b.id === updatedBelief.id ? updatedBelief : b)
      
      return {
        ...prev,
        beliefs: updateList(prev.beliefs),
        proto_beliefs: updateList(prev.proto_beliefs),
        ghosts: updateList(prev.ghosts),
      }
    })
  }

  const handleCreateSuccess = (newBelief: BeliefNodeInfo) => {
    setData(prev => {
      if (!prev) return null
      const isProto = newBelief.lifecycle_stage === "nucleation" || newBelief.lifecycle_stage === "accretion"
      const isGhost = newBelief.lifecycle_stage === "collapsed" || newBelief.lifecycle_stage === "faded"
      
      return {
        ...prev,
        beliefs: !isProto && !isGhost ? [...(prev.beliefs || []), newBelief] : (prev.beliefs || []),
        proto_beliefs: isProto ? [...(prev.proto_beliefs || []), newBelief] : (prev.proto_beliefs || []),
        ghosts: isGhost ? [...(prev.ghosts || []), newBelief] : (prev.ghosts || []),
      }
    })
    setIsAdding(false)
    setSelectedId(newBelief.id)
  }

  const handleDeleteSuccess = (beliefId: string) => {
    setData(prev => {
      if (!prev) return null
      const filterList = (list: BeliefNodeInfo[]) =>
        (list || []).filter(b => b.id !== beliefId)
      return {
        ...prev,
        beliefs: filterList(prev.beliefs),
        proto_beliefs: filterList(prev.proto_beliefs),
        ghosts: filterList(prev.ghosts),
      }
    })
    setSelectedId(null)
  }

  // Event delegation: click anywhere in the list container
  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-belief-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-belief-id")
    if (id) {
      setIsAdding(false)
      setSelectedId(prev => prev === id ? null : id)
    }
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      {/* Somatic */}
      {somatic && (
        <div className="mb-3 bg-[#0c0c12] border border-[#222]/40 rounded p-2 font-mono text-[10px] space-y-1">
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Somatic Reservoir State ]</div>
          <div className="flex justify-between items-center">
            <span className="text-[#888]">Somatic Shock (Ad):</span>
            <span className="text-[#ccc] font-bold">{somatic.somatic_reservoir_ad.toFixed(3)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#888]">Matrix Warping:</span>
            <span className="text-[#ccc] font-bold">{somatic.matrix_warping.toFixed(3)}</span>
          </div>
          {somatic.immunological_directive_active && (
            <div className="mt-1 px-1.5 py-0.5 bg-[#ef4444]/15 border border-[#ef4444]/40 text-[#ef4444] text-[9px] font-bold uppercase tracking-wider rounded animate-pulse text-center">
              Immunological Response Triggered
            </div>
          )}
        </div>
      )}

      {/* Ecosystem — single line on desktop, 2-column grid on mobile */}
      {ecosystem && (
        <div className="mb-3 bg-[#0c0c12] border border-[#222]/40 rounded p-2 font-mono text-[10px]">
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Ecosystem Health ]</div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 md:gap-x-6">
            <EcoMetric label="Diversity" value={ecosystem.diversity.toFixed(2)} />
            <EcoMetric label="Coherence" value={ecosystem.coherence.toFixed(2)} />
            <EcoMetric label="Tension" value={ecosystem.tension.toFixed(2)} />
            <EcoMetric label="Plasticity" value={ecosystem.plasticity.toFixed(2)} />
            <EcoMetric label="Ghosts" value={`${ecosystem.ghost_count}/${ecosystem.active_count}`} />
            <EcoMetric label="Vitality" value={ecosystem.eco_vitality.toFixed(3)} accent />
          </div>
        </div>
      )}

      {/* Category legend */}
      <div className="mb-2 flex items-center justify-between text-[9px] font-mono text-[#555] border-b border-[#222]/30 pb-1.5">
        <span className="text-[#6c6c8a] uppercase tracking-wider">[ Nodes ]</span>
        <div className="flex gap-1.5 md:gap-2">
          <span className="text-[#4ade80] flex items-center gap-0.5"><span className="text-[11px]">●</span><span className="hidden md:inline">found</span></span>
          <span className="text-[#a78bfa] flex items-center gap-0.5"><span className="text-[11px]">●</span><span className="hidden md:inline">ont</span></span>
          <span className="text-[#facc15] flex items-center gap-0.5"><span className="text-[11px]">●</span><span className="hidden md:inline">meth</span></span>
          <span className="text-[#f59e0b] flex items-center gap-0.5"><span className="text-[11px]">◇</span><span className="hidden md:inline">proto</span></span>
        </div>
      </div>

      {/* Two-panel layout: list + detail */}
      <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-300px)]">
        {/* ── Left: Node list ── */}
        <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0">
          {agentFlux && (
            <button
              onClick={() => {
                setSelectedId(null)
                setIsAdding(true)
              }}
              className="w-full mb-2.5 py-1 px-3 border border-[#a78bfa]/20 hover:border-[#a78bfa]/40 bg-[#a78bfa]/5 hover:bg-[#a78bfa]/10 text-[#a78bfa] text-[10px] font-mono transition-all text-center cursor-pointer select-none uppercase tracking-wider rounded font-bold"
            >
              + add new belief
            </button>
          )}
          <div
            onClick={handleListClick}
            className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none"
          >
            {proto_beliefs.length > 0 && (
              <CollapsibleSection label="Incubating Proto-Beliefs" count={proto_beliefs.length} icon="◇" iconColor="#f59e0b">
                {proto_beliefs.map(b => {
                  const s = b.lifecycle_stage || "accretion"
                  return <NodeListItem key={b.id} b={b} isSelected={selectedId === b.id} stageBadge={getStageLabel(s)} stageBadgeColor={getStageColor(s)} />
                })}
              </CollapsibleSection>
            )}

            {beliefs.map(b => (
              <NodeListItem key={b.id} b={b} isSelected={selectedId === b.id} />
            ))}

            {ghosts.length > 0 && (
              <CollapsibleSection label="Spectral Ghosts" count={ghosts.length} icon="👻" defaultOpen={false}>
                {ghosts.map(b => (
                  <NodeListItem key={b.id} b={b} isSelected={selectedId === b.id} ghost />
                ))}
              </CollapsibleSection>
            )}
          </div>
        </div>

        {/* ── Right: Detail panel ── */}
        <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
          {isAdding ? (
            <NewBeliefForm
              onCancel={() => setIsAdding(false)}
              onCreate={handleCreateSuccess}
            />
          ) : (
            <BeliefDetail
              belief={selected}
              activeBeliefs={beliefs}
              onUpdate={handleUpdate}
              onDelete={handleDeleteSuccess}
              onReload={() => {
                getBeliefs(null as any)
                  .then(setData)
                  .catch(e => setError(e.message || "Failed to fetch beliefs"))
              }}
              agentFlux={agentFlux}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export const BeliefsSection = memo(BeliefsSectionComponent)
