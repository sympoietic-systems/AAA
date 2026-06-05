import { useState } from "react"
import type { BeliefsResponse, BeliefNodeInfo } from "../../api/client"

interface BeliefsSectionProps {
  data: BeliefsResponse | null
  error: string | null
}

function getCategoryColor(category: string) {
  switch (category.toLowerCase()) {
    case "foundational": return "#4ade80"
    case "ontological": return "#a78bfa"
    case "methodological": return "#facc15"
    default: return "#60a5fa"
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

function BeliefTooltip({
  title,
  category,
  mass,
  confidence,
  statement,
  origin,
  lastEvent,
}: {
  title: string
  category: string
  mass: number
  confidence: number
  statement: string
  origin?: string
  lastEvent?: string
}) {
  const color = getCategoryColor(category)

  return (
    <div className="
      absolute bottom-full left-0 mb-2 px-2.5 py-2
      bg-[#0f0f15] border border-[#2e2e42] rounded
      text-[10px] text-[#c0caf5] font-sans leading-relaxed
      whitespace-normal w-64 z-50
      opacity-0 group-hover:opacity-100
      transition-opacity duration-150
      pointer-events-none shadow-xl shadow-black/90
      backdrop-blur-md
      text-left
    ">
      <div className="flex justify-between items-center border-b border-[#2e2e42]/50 pb-1 mb-1.5">
        <span className="font-bold text-[#e0e0f0] font-mono text-[9px]">{title}</span>
        <span
          className="text-[8px] uppercase font-mono px-1.5 py-px rounded border"
          style={{ color, borderColor: `${color}40`, backgroundColor: `${color}10` }}
        >
          {category}
        </span>
      </div>
      <div className="font-serif italic text-[#a9b1d6] mb-2 leading-relaxed text-[10.5px]">
        "{statement}"
      </div>
      <div className="grid grid-cols-2 gap-1 text-[8px] font-mono text-[#6c6c8a] border-t border-[#2e2e42]/30 pt-1.5">
        <div>Mass: <span className="text-white">{mass.toFixed(1)}</span></div>
        <div>Confidence: <span className="text-white">{(confidence * 100).toFixed(0)}%</span></div>
      </div>
      {origin && (
        <div className="text-[8px] font-mono text-[#6c6c8a] mt-1">
          Origin: <span className="text-[#a9b1d6]">{origin}</span>
        </div>
      )}
      {lastEvent && (
        <div className="text-[8px] font-mono text-[#6c6c8a] mt-0.5 leading-snug">
          Last trace: <span className="text-[#a9b1d6]">{lastEvent}</span>
        </div>
      )}
      <div className="text-[8px] text-[#565f89] mt-1.5 leading-normal">
        {getCatDesc(category)}
      </div>
    </div>
  )
}

export function BeliefsSection({ data, error }: BeliefsSectionProps) {
  const [expandedBelief, setExpandedBelief] = useState<string | null>(null)

  if (error && !data) {
    return <p className="text-[9px] text-[#ef4444] font-mono">{error}</p>
  }

  if (!data) {
    return <p className="text-[9px] text-[#444] font-mono">waiting for data...</p>
  }

  const { beliefs, somatic, attractor_window, spectral_margin } = data

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      {somatic && (
        <div className="mb-3 bg-[#0c0c12] border border-[#222]/40 rounded p-2 font-mono text-[9px] space-y-1">
          <div className="text-[#6c6c8a] uppercase text-[8px] tracking-wider mb-1">[ Somatic Reservoir State ]</div>
          <div className="flex justify-between items-center">
            <span className="text-[#888]">Somatic Shock (Ad):</span>
            <span className="text-[#ccc] font-bold">{somatic.somatic_reservoir_ad.toFixed(3)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#888]">Matrix Warping:</span>
            <span className="text-[#ccc] font-bold">{somatic.matrix_warping.toFixed(3)}</span>
          </div>
          {somatic.immunological_directive_active && (
            <div className="mt-1 px-1.5 py-0.5 bg-[#ef4444]/15 border border-[#ef4444]/40 text-[#ef4444] text-[8px] font-bold uppercase tracking-wider rounded animate-pulse text-center">
              ⚠️ Aesthetic Immune Response Triggered
            </div>
          )}
        </div>
      )}

      <div className="mb-3 space-y-1.5">
        <div>
          <span className="text-[#6c6c8a] font-mono text-[8px] uppercase tracking-wider block mb-1">
            [ Attractor Window Slots ]
          </span>
          {attractor_window.length === 0 ? (
            <span className="text-[9px] text-[#444] italic font-mono">No active attractors</span>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {attractor_window.map((label) => {
                const b = beliefs.find(x => x.label === label)
                const catColor = b ? getCategoryColor(b.category) : "#555"
                return (
                  <span
                    key={label}
                    className="relative group text-[9px] font-mono bg-[#141414] text-[#aaa] border border-[#222] px-1.5 py-0.5 rounded flex items-center gap-1 shadow-sm cursor-help hover:border-[#444] transition-colors"
                  >
                    <span className="text-[8px] leading-none" style={{ color: catColor }}>●</span>
                    <span>{label}</span>
                    {b && (
                      <BeliefTooltip
                        title={b.label}
                        category={b.category}
                        mass={b.ontological_mass}
                        confidence={b.confidence}
                        statement={b.statement}
                        origin={b.origin}
                        lastEvent={b.events[0]?.description}
                      />
                    )}
                  </span>
                )
              })}
            </div>
          )}
        </div>

        {spectral_margin.length > 0 && (
          <div>
            <span className="text-[#6c6c8a] font-mono text-[8px] uppercase tracking-wider block mb-1">
              [ Spectral Margin - Obsessive Ghosts ]
            </span>
            <div className="flex flex-wrap gap-1.5">
              {spectral_margin.map((label) => {
                const b = beliefs.find(x => x.label === label)
                return (
                  <span
                    key={label}
                    className="relative group text-[9px] font-mono bg-[#141414] text-[#888]/60 border border-[#222]/60 px-1.5 py-0.5 rounded flex items-center gap-1 opacity-70 line-through cursor-help hover:border-[#444]/60 transition-colors"
                  >
                    👻 {label}
                    {b && (
                      <BeliefTooltip
                        title={b.label}
                        category={b.category}
                        mass={b.ontological_mass}
                        confidence={b.confidence}
                        statement={b.statement}
                        origin={b.origin}
                        lastEvent={b.events[0]?.description}
                      />
                    )}
                  </span>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <div className="mb-2 flex items-center justify-between text-[8px] font-mono text-[#555] border-b border-[#222]/30 pb-1.5">
        <span className="text-[#6c6c8a] uppercase tracking-wider">[ Nodes Legend ]</span>
        <div className="flex gap-2">
          <span className="text-[#4ade80] flex items-center gap-0.5"><span className="text-[10px]">●</span> foundational</span>
          <span className="text-[#a78bfa] flex items-center gap-0.5"><span className="text-[10px]">●</span> ontological</span>
          <span className="text-[#facc15] flex items-center gap-0.5"><span className="text-[10px]">●</span> methodological</span>
        </div>
      </div>

      <div className="space-y-1">
        <span className="text-[#6c6c8a] font-mono text-[8px] uppercase tracking-wider block mb-1">
          [ Belief Network Nodes ]
        </span>
        {beliefs.map((b: BeliefNodeInfo) => {
          const catColor = getCategoryColor(b.category)
          const isExpanded = expandedBelief === b.id
          const isCollapsed = b.confidence < 0.20

          let vec: number[] = []
          try {
            if (b.vector_16d) {
              vec = JSON.parse(b.vector_16d)
            }
          } catch { }

          return (
            <div
              key={b.id}
              className={`border border-[#1f1f2e]/30 bg-[#070709] rounded overflow-hidden transition-all duration-200 ${isCollapsed ? "opacity-55" : ""
                }`}
            >
              <div
                className="relative group p-1.5 flex items-center justify-between hover:bg-[#12121a] cursor-pointer transition-colors"
                onClick={() => setExpandedBelief(isExpanded ? null : b.id)}
              >
                <div className="flex items-center gap-1.5 truncate">
                  <span className="text-[9px] leading-none" style={{ color: catColor }}>●</span>
                  <span className="font-mono text-[10px] font-bold truncate text-[#ccc] group-hover:text-[#eee]">
                    {b.label}
                  </span>
                </div>
                <div className="flex items-center gap-2 shrink-0 pl-2">
                  <span className="text-[8px] font-mono text-[#555]">
                    m:{b.ontological_mass}
                  </span>
                  <span className="text-[10px] font-mono font-bold text-[#aaa] group-hover:text-white">
                    {(b.confidence * 100).toFixed(0)}%
                  </span>
                  <span className="text-[8px] text-[#666] font-mono leading-none">
                    {isExpanded ? "▼" : "▶"}
                  </span>
                </div>

                <BeliefTooltip
                  title={b.label}
                  category={b.category}
                  mass={b.ontological_mass}
                  confidence={b.confidence}
                  statement={b.statement}
                  origin={b.origin}
                  lastEvent={b.events[0]?.description}
                />
              </div>

              {isExpanded && (
                <div className="px-2 pb-2.5 pt-1 border-t border-[#1a1a24] bg-[#0c0c12] space-y-2 text-[10px] font-sans">
                  <div>
                    <div className="text-[#555] font-mono text-[8px] uppercase">[ Statement ]</div>
                    <div className="text-[#ccc] text-[10.5px] italic font-serif leading-relaxed mt-0.5">
                      "{b.statement}"
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[9px] font-mono text-[#888]">
                    <div>
                      <span className="text-[#444]">Category:</span>{" "}
                      <span style={{ color: catColor }}>{b.category}</span>
                    </div>
                    <div>
                      <span className="text-[#444]">Origin:</span>{" "}
                      <span className="text-[#aaa]">{b.origin}</span>
                    </div>
                  </div>

                  {vec.length > 0 && (
                    <div>
                      <div className="text-[#555] font-mono text-[8px] uppercase mb-1">[ 16D Autopoietic Vector ]</div>
                      <div className="flex items-end gap-0.5 h-4 bg-[#08080c] border border-[#1a1a24] p-0.5 rounded w-fit">
                        {vec.map((val: number, idx: number) => {
                          const heightPercent = Math.min(100, Math.max(10, Math.round(((val + 1.0) / 2.0) * 100)))
                          return (
                            <div
                              key={idx}
                              style={{ height: `${heightPercent}%` }}
                              title={`Dimension ${idx + 1}: ${val.toFixed(4)}`}
                              className="w-1 bg-[#a78bfa]/50 hover:bg-[#a78bfa]"
                            />
                          )
                        })}
                      </div>
                    </div>
                  )}

                  <div>
                    <div className="text-[#555] font-mono text-[8px] uppercase">[ Metabolism Log ]</div>
                    {b.events.length === 0 ? (
                      <div className="text-[9px] text-[#444] italic mt-0.5">No metabolic events logged</div>
                    ) : (
                      <div className="space-y-1.5 mt-1 max-h-24 overflow-y-auto pr-1">
                        {b.events.map((e) => {
                          const isPositive = e.delta_confidence >= 0
                          const diffStr = isPositive
                            ? `+${e.delta_confidence.toFixed(3)}`
                            : `${e.delta_confidence.toFixed(3)}`
                          return (
                            <div
                              key={e.id}
                              className="text-[9px] border-b border-[#222]/30 pb-1 last:border-b-0 leading-normal"
                            >
                              <div className="flex items-center justify-between text-[#888]">
                                <span className="font-mono text-[8px]">
                                  {new Date(e.timestamp).toLocaleTimeString()}
                                </span>
                                <span
                                  className={`font-mono text-[8px] font-bold ${isPositive ? "text-[#4ade80]" : "text-[#f87171]"
                                    }`}
                                >
                                  {diffStr}
                                </span>
                              </div>
                              <div className="text-[#ccc] mt-0.5">
                                <span className="text-[#6c6c8a] font-mono text-[8px] mr-1">
                                  [{e.source_type}:{e.source_id}]
                                </span>
                                {e.description}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
