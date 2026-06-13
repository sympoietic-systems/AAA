import { useState, useEffect, useRef, memo } from "react"
import { getBeliefs } from "../../../api/client"
import type { BeliefsResponse, BeliefNodeInfo } from "../../../api/client"
import { StructuralAutopoieticGlyph } from "../../UI/StructuralAutopoieticGlyph"

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

function getCatDesc(cat: string) {
  switch (cat.toLowerCase()) {
    case "foundational":
      return "Core stabilizing beliefs. High ontological mass, resistant to perturbation."
    case "ontological":
      return "Beliefs regarding the nature of being, reality, and conceptual definitions."
    case "methodological":
      return "Operational rules, reasoning patterns, and system methodologies."
    default:
      return "Epistemological or general perceptual beliefs."
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
        {b.label}
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

// ─── Belief Detail Panel ──────────────────────────────────

function BeliefDetail({ belief }: { belief: BeliefNodeInfo | null }) {
  if (!belief) {
    return (
      <div className="flex-1 min-h-0 flex items-center justify-center border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50">
        <span className="text-[11px] text-[#444] italic font-mono">select a node to inspect</span>
      </div>
    )
  }

  const b = belief
  const catColor = getCategoryColor(b.category)
  const stage = b.lifecycle_stage || "crystallized"
  const stageColor = getStageColor(stage)
  const isProto = stage === "nucleation" || stage === "accretion"
  const isGhost = stage === "collapsed" || stage === "faded"

  let vec: number[] = []
  try { if (b.vector_16d) vec = JSON.parse(b.vector_16d) } catch { }

  return (
    <div className={`flex-1 min-h-0 flex flex-col overflow-y-auto pr-1.5 border border-[#1f1f2e]/20 rounded bg-[#0a0a10]/50 p-2.5 gap-2.5 text-[11px] font-sans ${isGhost ? "opacity-55" : ""}`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#1f1f2e]/30 pb-1.5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[11px] shrink-0" style={{ color: catColor }}>●</span>
          <span className="font-mono text-[11px] font-bold text-[#ccc] truncate">{b.label}</span>
        </div>
        <span
          className="text-[9px] uppercase font-mono px-1.5 py-px rounded border shrink-0 ml-2"
          style={{ color: catColor, borderColor: `${catColor}40`, backgroundColor: `${catColor}10` }}
        >
          {b.category}
        </span>
      </div>

      {/* Statement */}
      <div className="shrink-0">
        <div className="text-[#555] font-mono text-[10px] uppercase">[ Statement ]</div>
        <div className="text-[#ccc] text-[11px] italic font-serif leading-relaxed mt-0.5">
          "{b.statement}"
        </div>
      </div>

      {/* Metadata grid */}
      <div className="shrink-0 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono text-[#888]">
        <div><span className="text-[#444]">Category:</span> <span style={{ color: catColor }}>{b.category}</span></div>
        <div><span className="text-[#444]">Origin:</span> <span className="text-[#aaa]">{b.origin === "emergent" ? "agent" : b.origin === "authored" ? "user" : b.origin}</span></div>
        <div><span className="text-[#444]">Stage:</span> <span style={{ color: stageColor }}>{getStageLabel(stage)}</span></div>
        <div><span className="text-[#444]">Mass:</span> <span className="text-[#aaa]">{isProto ? b.ontological_mass.toFixed(3) : b.ontological_mass.toFixed(1)}</span></div>
        <div className="col-span-2"><span className="text-[#444]">Confidence:</span> <span className="text-[#aaa] font-bold">{(b.confidence * 100).toFixed(0)}%</span></div>
      </div>

      <div className="shrink-0 text-[10px] font-mono text-[#6c6c8a] leading-snug">
        {getCatDesc(b.category)}
      </div>

      {/* Vector */}
      {vec.length > 0 && (
        <div className="shrink-0 mb-1">
          <div className="text-[#555] font-mono text-[10px] uppercase mb-1">[ 16D Autopoietic Signature ]</div>
          <StructuralAutopoieticGlyph
            signature={vec}
            isStagnant={false}
          />
        </div>
      )}

      {/* Metabolism log — scrolls naturally in parent container */}
      <div className="flex flex-col mt-2 shrink-0">
        <div className="text-[#555] font-mono text-[10px] uppercase shrink-0">[ Metabolism Log ]</div>
        {b.events.length === 0 ? (
          <div className="text-[11px] text-[#444] italic mt-0.5">No metabolic events logged</div>
        ) : (
          <div className="mt-1 space-y-1.5">
            {b.events.map((e) => {
              const isPos = e.delta_confidence >= 0
              const diffStr = isPos ? `+${e.delta_confidence.toFixed(3)}` : `${e.delta_confidence.toFixed(3)}`
              return (
                <div key={e.id} className="text-[11px] border-b border-[#222]/30 pb-1 last:border-b-0 leading-normal">
                  <div className="flex items-center justify-between text-[#888]">
                    <span className="font-mono text-[10px]">{new Date(e.timestamp).toLocaleTimeString()}</span>
                    <span className={`font-mono text-[10px] font-bold ${isPos ? "text-[#4ade80]" : "text-[#f87171]"}`}>{diffStr}</span>
                  </div>
                  <div className="text-[#ccc] mt-0.5">
                    <span className="text-[#6c6c8a] font-mono text-[10px] mr-1">[{e.source_type}:{e.source_id}]</span>
                    {e.description}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────

function BeliefsSectionComponent() {
  const [data, setData] = useState<BeliefsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    getBeliefs(null as any)
      .then(setData)
      .catch(e => setError(e.message || "Failed to fetch beliefs"))
  }, [])

  // Scroll to detail on mobile when a belief is selected
  useEffect(() => {
    if (!selectedId || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedId])

  if (error && !data) return <p className="text-[10px] text-[#ef4444] font-mono">{error}</p>
  if (!data) return <p className="text-[10px] text-[#444] font-mono">waiting for data...</p>

  const { beliefs: rawBeliefs, proto_beliefs: rawProtos, ghosts: rawGhosts, somatic, ecosystem } = data

  const isSkillBelief = (b: BeliefNodeInfo) => b.label?.startsWith("skill:") ?? false
  const beliefs = (rawBeliefs || []).filter(b => !isSkillBelief(b))
  const proto_beliefs = (rawProtos || []).filter(b => !isSkillBelief(b))
  const ghosts = (rawGhosts || []).filter(b => !isSkillBelief(b))

  const allBeliefs = [...beliefs, ...proto_beliefs, ...ghosts]
  const selected = (selectedId ? allBeliefs.find(b => b.id === selectedId) : null) || null

  // Event delegation: click anywhere in the list container
  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-belief-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-belief-id")
    setSelectedId(prev => prev === id ? null : id)
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
        <div
          onClick={handleListClick}
          className="md:w-[38%] shrink-0 w-full space-y-0.5 overflow-y-auto pr-1 select-none"
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

        {/* ── Right: Detail panel ── */}
        <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0">
          <BeliefDetail belief={selected} />
        </div>
      </div>
    </div>
  )
}

export const BeliefsSection = memo(BeliefsSectionComponent)
