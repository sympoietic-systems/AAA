import { useState, useEffect, memo } from "react"
import { getBeliefs } from "../../api/client"
import type { BeliefsResponse } from "../../api/client"

interface AttractorsSectionProps {
  conversationId?: string
  enabled?: boolean
  messageCount?: number
}

function AttractorsSectionComponent({
  conversationId,
  enabled = false,
  messageCount = 0,
}: AttractorsSectionProps) {
  const [beliefs, setBeliefs] = useState<BeliefsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!enabled || !conversationId) {
      setBeliefs(null)
      return
    }

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    const tick = async () => {
      if (!active) return
      setLoading(true)
      try {
        const res = await getBeliefs(conversationId)
        if (active) {
          setBeliefs(res)
          setError(null)
        }
      } catch (e: any) {
        if (active) {
          setError(e.message || "Failed to fetch beliefs")
        }
      } finally {
        if (active) setLoading(false)
      }

      if (active) {
        const delay = 15000 + (Math.random() - 0.5) * 1000 // 15s ± 500ms
        timeoutId = setTimeout(tick, delay)
      }
    }

    tick()

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [enabled, conversationId, messageCount])

  return (
    <div className="text-[10px] font-mono space-y-2">
      {error ? (
        <p className="text-[9px] text-[#ef4444]">{error}</p>
      ) : loading && !beliefs ? (
        <p className="text-[9px] text-[#444] animate-pulse">loading...</p>
      ) : !beliefs ? (
        <p className="text-[9px] text-[#444]">waiting for data...</p>
      ) : (
        <>
          {beliefs.attractor_window.length === 0 ? (
            <p className="text-[9px] text-[#444] italic">No active attractors</p>
          ) : (
            <div>
              <span className="text-[#6c6c8a] text-[8px] uppercase tracking-wider block mb-1">
                [ Attractor Window ]
              </span>
              <div className="flex flex-wrap gap-1">
                {beliefs.attractor_window.map((label) => {
                  const b = [...(beliefs.beliefs || []), ...(beliefs.proto_beliefs || []), ...(beliefs.ghosts || [])].find(x => x.label === label)
                  const catColor =
                    b?.category === "foundational" ? "#4ade80"
                    : b?.category === "ontological" ? "#a78bfa"
                    : b?.category === "methodological" ? "#facc15"
                    : "#555"
                  return (
                    <span
                      key={label}
                      title={b ? `${b.category} · mass ${b.ontological_mass.toFixed(1)} · ${(b.confidence * 100).toFixed(0)}%` : label}
                      className="text-[9px] font-mono bg-[#141414] text-[#aaa] border border-[#222] px-1.5 py-0.5 rounded inline-flex items-center gap-1 cursor-help hover:border-[#444] transition-colors"
                    >
                      <span className="text-[8px] leading-none" style={{ color: catColor }}>●</span>
                      {label}
                    </span>
                  )
                })}
              </div>
            </div>
          )}
          {beliefs.spectral_margin.length > 0 && (
            <div>
              <span className="text-[#6c6c8a] text-[8px] uppercase tracking-wider block mb-1">
                [ Spectral Margin ]
              </span>
              <div className="flex flex-wrap gap-1">
                {beliefs.spectral_margin.map((label) => (
                  <span
                    key={label}
                    className="text-[9px] font-mono bg-[#141414] text-[#888]/60 border border-[#222]/60 px-1.5 py-0.5 rounded inline-flex items-center gap-1 opacity-70 line-through cursor-help hover:border-[#444]/60 transition-colors"
                  >
                    👻 {label}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export const AttractorsSection = memo(AttractorsSectionComponent)
