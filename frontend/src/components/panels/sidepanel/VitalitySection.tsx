import { memo } from "react"
import { useTelemetryMetrics } from "../../../hooks/useTelemetry"

interface VitalitySectionProps {
  enabled?: boolean
  messageCount?: number
}

function VitalitySectionComponent({ enabled = false }: VitalitySectionProps) {
  const { metrics, metricsLoading: loading, metricsError: error } = useTelemetryMetrics(enabled)

  const vitality = metrics?.latest?.conversation_vitality
  const paskHealth = metrics?.latest?.paskian_health
  const state = metrics?.recommendations?.state ?? "unknown"

  const stateColor =
    (state === "flowing" || state === "healthy") ? "#4ade80" :
      (state === "consolidating" || state === "compensating") ? "#facc15" :
        (state === "disrupted" || state === "critical") ? "#ef4444" : "#555"

  const renderBar = (
    label: string,
    fullName: string,
    value: number | null | undefined,
    max: number,
    hint: string
  ) => {
    const pct = value != null ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
    const display = value != null ? (value < 0.01 ? value.toFixed(4) : value.toFixed(3)) : "—"

    return (
      <div className="flex items-center gap-1.5 group relative" key={label}>
        <span className="w-7 text-[9px] text-[#555] text-right font-mono">{label}</span>
        <div className="w-12 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
          <div
            className="h-full rounded-sm bg-[#444] group-hover:bg-[#4ade80] transition-all transition-colors duration-200"
            style={{
              width: `${pct}%`,
              opacity: 0.6,
              animation: "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            }}
          />
        </div>
        <span className="text-[9px] text-[#666] group-hover:text-[#aaa] transition-colors w-10 text-right font-mono">{display}</span>
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
          <div className="text-[#888] font-mono">{display} / {max}</div>
          <div className="text-[#666] max-w-48 whitespace-normal">{hint}</div>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5 font-mono">
        <span
          className="text-[8px] leading-none"
          style={{ color: stateColor }}
        >
          ●
        </span>
        <span className="text-[10px] text-[#888]">vitality</span>
        <span className="text-[9px] ml-auto" style={{ color: stateColor }}>
          {state} {vitality != null ? `vit:${vitality.toFixed(2)}` : ""}{paskHealth != null ? ` ph:${paskHealth.toFixed(2)}` : ""}
        </span>
      </div>

      {error && <p className="text-[9px] text-[#ef4444] font-mono">{error}</p>}

      {metrics?.latest && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-1.5">
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
            "Distance from decay-weighted centroid of past human inputs (d=0.75). >0.40 = phase disruption")}
          {renderBar("mpi", "mutual perturbation", metrics.latest.mutual_perturbation, 1.0,
            "Product of coupling x reverse perturbation. <0.05 = deadlock")}
          {renderBar("bore", "boringness", metrics.latest.boringness, 1.0,
            "Joint failure to perturb: (1 - rP_t) x (1 - MPI_{t-1}). >0.60 = Paskian boredom")}
          {renderBar("vel", "conceptual velocity", metrics.latest.conceptual_velocity, 1.0,
            "Disjoint centroid drift rate (last 3 vs preceding 3). <0.02 = frozen, >0.80 = noise")}
          {renderBar("drr", "divergence resolution ratio", metrics.latest.divergence_resolution_ratio, 1.0,
            "Does perturbation lead to resolution? Positive = convergence, negative = rejection")}
        </div>
      )}

      {loading && !metrics && (
        <p className="text-[9px] text-[#444] font-mono animate-pulse">loading...</p>
      )}

      {!metrics && !error && !loading && (
        <p className="text-[9px] text-[#444] font-mono">waiting for data...</p>
      )}

      {metrics?.latest?.phase_shifts && metrics.latest.phase_shifts.length > 0 && (
        <div className="mt-1.5 font-mono">
          <span className="text-[9px] text-[#facc15]">phase shifts:</span>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {metrics.latest.phase_shifts.map((s, i) => (
              <span key={i} className="text-[8px] text-[#facc15] border border-[#332200] px-1 rounded">
                {s.event} {s.direction === "rise" ? "↑" : "↓"}{s.delta.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
      )}

      {metrics?.recommendations?.triggered_flags && metrics.recommendations.triggered_flags.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1 font-mono">
          {metrics.recommendations.triggered_flags.map((f) => (
            <span key={f} className="text-[8px] text-[#f87171] border border-[#3a1a1a] px-1 rounded">
              {f}
            </span>
          ))}
        </div>
      )}

      {metrics?.recommendations?.temperature?.delta !== undefined && metrics.recommendations.temperature.delta !== 0 && (
        <div className="mt-1 text-[9px] text-[#666] font-mono">
          param: T{metrics.recommendations.temperature.value.toFixed(2)}
          {metrics.recommendations.temperature.clamped ? " (clamped)" : ""}
        </div>
      )}
    </div>
  )
}

export const VitalitySection = memo(VitalitySectionComponent)
