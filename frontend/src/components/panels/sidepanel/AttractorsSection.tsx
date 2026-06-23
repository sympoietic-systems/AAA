import { memo } from "react"
import { useTelemetryBeliefs } from "../../../hooks/useTelemetry"
import { getCategoryColor } from "../../pages/agentpage/shared/helpers"

const EMPTY_BELIEF_ARRAY: any[] = []

interface AttractorsSectionProps {
  conversationId?: string
  enabled?: boolean
  messageCount?: number
}

function AttractorsSectionComponent({
  conversationId,
  enabled = false,
}: AttractorsSectionProps) {
  const { beliefs, beliefsLoading: loading, beliefsError: error } = useTelemetryBeliefs(conversationId || null, enabled)

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
              <span className="text-semantic-header text-[8px] uppercase tracking-wider block mb-1">
                [ Attractor Window ]
              </span>
              <div className="flex flex-wrap gap-1">
                {beliefs.attractor_window.map((label) => {
                  const b = [...(beliefs.beliefs ?? EMPTY_BELIEF_ARRAY), ...(beliefs.proto_beliefs ?? EMPTY_BELIEF_ARRAY), ...(beliefs.ghosts ?? EMPTY_BELIEF_ARRAY)].find(x => x.label === label)
                  const catColor = b ? getCategoryColor(b.category) : "var(--color-ui-dim)"
                  return (
                    <span
                      key={label}
                      title={b ? `${b.category} · mass ${b.ontological_mass.toFixed(1)} · ${(b.confidence * 100).toFixed(0)}%` : label}
                      className="text-[9px] font-mono text-[#aaa] inline-flex items-center gap-1 cursor-help hover:text-[#ccc] transition-colors"
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
              <span className="text-semantic-header text-[8px] uppercase tracking-wider block mb-1">
                [ Spectral Margin ]
              </span>
              <div className="flex flex-wrap gap-1">
                {beliefs.spectral_margin.map((label) => (
                  <span
                    key={label}
                    className="text-[9px] font-mono text-[#888]/60 inline-flex items-center gap-1 opacity-70 line-through cursor-help hover:text-[#aaa] transition-colors"
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
