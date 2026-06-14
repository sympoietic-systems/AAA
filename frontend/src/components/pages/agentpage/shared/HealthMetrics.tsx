import { memo } from "react"
import type { SomaticStateInfo, EcosystemSnapshot } from "../../../../api/client"
import { TerminalHeader } from "../../../UI"

/* ── Single Metric Display ── */
const EcoMetric = memo(function EcoMetric({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <span className="w-[calc(50%-0.5rem)] md:w-auto">
      <span className="text-[#666]">{label}:</span>{" "}
      <span className={accent ? "text-[#4ade80] font-bold" : "text-[#ccc]"}>{value}</span>
    </span>
  )
})

interface HealthMetricsProps {
  somatic?: SomaticStateInfo | null
  ecosystem?: EcosystemSnapshot | null
}

export const HealthMetrics = memo(function HealthMetrics({ somatic, ecosystem }: HealthMetricsProps) {
  if (!somatic && !ecosystem) {
    return (
      <div className="p-6 text-center text-[#555] text-[11px] italic">
        No health metrics available yet.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Somatic Reservoir */}
      {somatic && (
        <div className="font-mono text-[10px] space-y-1">
          <TerminalHeader>[ Somatic Reservoir State ]</TerminalHeader>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5">
            <span><span className="text-[#888]">Somatic Shock (Ad):</span> <span className="text-[#ccc] font-bold">{somatic.somatic_reservoir_ad.toFixed(3)}</span></span>
            <span><span className="text-[#888]">Matrix Warping:</span> <span className="text-[#ccc] font-bold">{somatic.matrix_warping.toFixed(3)}</span></span>
          </div>
          {somatic.immunological_directive_active && (
            <div className="text-[#ef4444] text-[9px] font-bold uppercase tracking-wider animate-pulse">
              ⚡ Immunological Response Triggered
            </div>
          )}
        </div>
      )}

      {/* Ecosystem Health */}
      {ecosystem && (
        <div className="font-mono text-[10px]">
          <TerminalHeader>[ Ecosystem Health ]</TerminalHeader>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 md:gap-x-6 mt-0.5">
            <EcoMetric label="Diversity" value={ecosystem.diversity.toFixed(2)} />
            <EcoMetric label="Coherence" value={ecosystem.coherence.toFixed(2)} />
            <EcoMetric label="Tension" value={ecosystem.tension.toFixed(2)} />
            <EcoMetric label="Plasticity" value={ecosystem.plasticity.toFixed(2)} />
            <EcoMetric label="Ghosts" value={`${ecosystem.ghost_count}/${ecosystem.active_count}`} />
            <EcoMetric label="Vitality" value={ecosystem.eco_vitality.toFixed(3)} accent />
          </div>
        </div>
      )}
    </div>
  )
})
