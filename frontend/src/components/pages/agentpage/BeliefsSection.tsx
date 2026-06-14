import { useState, useEffect, useRef, memo } from "react"
import { getBeliefs, getAgent } from "../../../api/client"
import type { BeliefsResponse, BeliefNodeInfo } from "../../../api/client"
import { NewBeliefForm } from "./beliefs/NewBeliefForm"
import { BeliefDetail } from "./beliefs/BeliefDetail"
import { getCategoryColor, getBeliefStageColor, getBeliefStageLabel } from "./shared/helpers"
import { CollapsibleSection } from "./shared/CollapsibleSection"

/* ── Compact Node List Item ── */
const NodeListItem = memo(function NodeListItem({
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
      <span className="text-[9px] leading-none shrink-0" style={{ color: isProto ? getBeliefStageColor(stage) : isGhost ? "#ef4444" : catColor }}>
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
        m:{b.ontological_mass.toFixed(2)}
      </span>
      <span className="text-[10px] font-mono font-bold text-[#777] shrink-0">
        {(b.confidence * 100).toFixed(0)}%
      </span>
    </div>
  )
})

interface BeliefsSectionProps {
  initialSelectedId?: string
}

function BeliefsSectionComponent({ initialSelectedId }: BeliefsSectionProps) {
  const [data, setData] = useState<BeliefsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [agentFlux, setAgentFlux] = useState<boolean>(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const [sortBy, setSortBy] = useState<"mass" | "confidence" | "default">("mass")
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

  const { beliefs: rawBeliefs, proto_beliefs: rawProtos, ghosts: rawGhosts } = data

  const isSkillBelief = (b: BeliefNodeInfo) => b.label?.startsWith("skill:") ?? false
  const beliefs = (rawBeliefs || []).filter(b => !isSkillBelief(b))
  const proto_beliefs = (rawProtos || []).filter(b => !isSkillBelief(b))
  const ghosts = (rawGhosts || []).filter(b => !isSkillBelief(b))

  const sortFunc = (a: BeliefNodeInfo, b: BeliefNodeInfo) => {
    if (sortBy === "mass") {
      return b.ontological_mass - a.ontological_mass
    }
    if (sortBy === "confidence") {
      return b.confidence - a.confidence
    }
    return 0
  }

  const sortedBeliefs = sortBy === "default" ? beliefs : [...beliefs].sort(sortFunc)
  const sortedProtos = sortBy === "default" ? proto_beliefs : [...proto_beliefs].sort(sortFunc)
  const sortedGhosts = sortBy === "default" ? ghosts : [...ghosts].sort(sortFunc)

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
    <div className="pt-2">
      {/* Somatic & Ecosystem health metrics moved to Traits & Health tab */}

      {/* Category legend & Sorting */}
      <div className="mb-2 flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 text-[9px] font-mono text-[#555] border-b border-[#222]/30 pb-1.5">
        <div className="flex items-center gap-3">
          <span className="text-[#444] uppercase">sort:</span>
          <button
            onClick={() => setSortBy("mass")}
            className={`cursor-pointer transition-colors hover:text-[#ccc] ${sortBy === "mass" ? "text-[#a78bfa] font-bold" : "text-[#555]"}`}
          >
            [mass]
          </button>
          <button
            onClick={() => setSortBy("confidence")}
            className={`cursor-pointer transition-colors hover:text-[#ccc] ${sortBy === "confidence" ? "text-[#a78bfa] font-bold" : "text-[#555]"}`}
          >
            [confidence]
          </button>
        </div>
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
              className="self-start text-[10px] text-[#666] hover:text-[#a78bfa] font-mono cursor-pointer select-none mb-2"
            >
              [+ add]
            </button>
          )}
          <div
            onClick={handleListClick}
            className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none"
          >
            {sortedProtos.length > 0 && (
              <CollapsibleSection label="Incubating Proto-Beliefs" count={sortedProtos.length} icon="◇" iconColor="#f59e0b">
                {sortedProtos.map(b => {
                  const s = b.lifecycle_stage || "accretion"
                  return <NodeListItem key={b.id} b={b} isSelected={selectedId === b.id} stageBadge={getBeliefStageLabel(s)} stageBadgeColor={getBeliefStageColor(s)} />
                })}
              </CollapsibleSection>
            )}

            {sortedBeliefs.length > 0 && (
              <CollapsibleSection label="Crystallized Beliefs" count={sortedBeliefs.length} icon="●" iconColor="#4ade80">
                {sortedBeliefs.map(b => (
                  <NodeListItem key={b.id} b={b} isSelected={selectedId === b.id} />
                ))}
              </CollapsibleSection>
            )}

            {sortedGhosts.length > 0 && (
              <CollapsibleSection label="Spectral Ghosts" count={sortedGhosts.length} icon="◇" defaultOpen={false}>
                {sortedGhosts.map(b => (
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
