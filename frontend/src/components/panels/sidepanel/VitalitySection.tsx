import { memo, useState } from "react"
import { useTelemetryMetrics } from "../../../hooks/useTelemetry"
import { Tooltip } from "../../UI/Tooltip"
import type { MetricsInfo } from "../../../api/client"

interface VitalitySectionProps {
  conversationId?: string | null
  enabled?: boolean
  messageCount?: number
}

type MetricKey =
  | "vit"
  | "ph"
  | "cpi"
  | "tb"
  | "act"
  | "cp"
  | "sim"
  | "nov"
  | "ent"
  | "coup"
  | "divr"
  | "rP"
  | "srp"
  | "mpi"
  | "vel"
  | "drr"

const METRIC_CONFIG: Record<
  MetricKey,
  {
    label: string
    fullName: string
    color: string
    max: number
    getValue: (m: MetricsInfo) => number | null | undefined
  }
> = {
  vit: {
    label: "vit",
    fullName: "vitality",
    color: "var(--color-semantic-green)",
    max: 1.0,
    getValue: (m) => m.conversation_vitality,
  },
  ph: {
    label: "ph",
    fullName: "paskian health",
    color: "#a855f7",
    max: 1.0,
    getValue: (m) => m.paskian_health,
  },
  cpi: {
    label: "cpi",
    fullName: "conversational progress index",
    color: "var(--color-semantic-gold)",
    max: 1.0,
    getValue: (m) => m.cpi,
  },
  tb: {
    label: "tb",
    fullName: "teachback ratio",
    color: "#38bdf8",
    max: 1.0,
    getValue: (m) => m.teachback_ratio,
  },
  act: {
    label: "act",
    fullName: "actionability",
    color: "#34d399",
    max: 1.0,
    getValue: (m) => m.actionability,
  },
  cp: {
    label: "cp",
    fullName: "collapse pressure",
    color: "var(--color-semantic-red)",
    max: 1.0,
    getValue: (m) => m.collapse_pressure ?? m.boringness,
  },
  sim: {
    label: "sim",
    fullName: "pairwise similarity",
    color: "#94a3b8",
    max: 1.0,
    getValue: (m) => m.pairwise_similarity,
  },
  nov: {
    label: "nov",
    fullName: "conceptual novelty",
    color: "#60a5fa",
    max: 1.0,
    getValue: (m) => m.conceptual_novelty,
  },
  ent: {
    label: "ent",
    fullName: "rolling entropy",
    color: "#818cf8",
    max: 0.25,
    getValue: (m) => m.rolling_entropy,
  },
  coup: {
    label: "coup",
    fullName: "coupling coherence",
    color: "#2dd4bf",
    max: 1.0,
    getValue: (m) => m.coupling_coherence,
  },
  divr: {
    label: "divr",
    fullName: "agent self-divergence",
    color: "#f472b6",
    max: 1.0,
    getValue: (m) => m.agent_self_divergence,
  },
  rP: {
    label: "rP",
    fullName: "reverse perturbation",
    color: "#fb923c",
    max: 1.0,
    getValue: (m) => m.reverse_perturbation,
  },
  srp: {
    label: "srp",
    fullName: "surprise index",
    color: "#e879f9",
    max: 1.0,
    getValue: (m) => m.surprise_index,
  },
  mpi: {
    label: "mpi",
    fullName: "mutual perturbation",
    color: "#facc15",
    max: 1.0,
    getValue: (m) => m.mutual_perturbation,
  },
  vel: {
    label: "vel",
    fullName: "conceptual velocity",
    color: "#4ade80",
    max: 1.0,
    getValue: (m) => m.conceptual_velocity,
  },
  drr: {
    label: "drr",
    fullName: "divergence resolution ratio",
    color: "#22d3ee",
    max: 1.0,
    getValue: (m) => m.divergence_resolution_ratio,
  },
}

function VitalitySectionComponent({ conversationId, enabled = false }: VitalitySectionProps) {
  const { metrics, metricsLoading: loading, metricsError: error } = useTelemetryMetrics(conversationId, enabled)
  const [hoveredMetric, setHoveredMetric] = useState<MetricKey | null>(null)

  const vitality = metrics?.latest?.conversation_vitality
  const paskHealth = metrics?.latest?.paskian_health
  const state = metrics?.recommendations?.state ?? "unknown"
  const cpi = metrics?.latest?.cpi
  const intervention = metrics?.recommendations?.intervention
  const somaticDirective = metrics?.recommendations?.somatic_reflection_prompt || intervention?.directive

  const stateColor =
    (state === "flowing" || state === "healthy") ? "var(--color-semantic-green)" :
      (state === "consolidating" || state === "compensating") ? "var(--color-semantic-gold)" :
        (state === "disrupted" || state === "critical") ? "var(--color-semantic-red)" : "var(--color-ui-dim)"

  const renderBar = (
    key: MetricKey,
    fullName: string,
    value: number | null | undefined,
    max: number,
    hint: string,
    invertColor: boolean = false
  ) => {
    const pct = value != null ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
    const display = value != null ? (value < 0.01 && value > 0 ? value.toFixed(4) : value.toFixed(3)) : "—"

    const isHovered = hoveredMetric === key
    const cfg = METRIC_CONFIG[key]

    // Highlight color on hover or warning tint for high pressure
    const barColor = isHovered
      ? (cfg?.color || "#38bdf8")
      : (invertColor && value != null && value > 0.6)
        ? "var(--color-semantic-red)"
        : "var(--color-ui-dim)"

    return (
      <Tooltip
        key={key}
        title={fullName}
        subtitle={`${display} / ${max}`}
        description={`${hint} • Hover to plot trajectory`}
        titleColorClass="text-semantic-green"
        position="top-left"
      >
        <div
          className={`flex items-center gap-1.5 cursor-pointer w-full py-0.5 px-1 rounded transition-colors ${
            isHovered ? "bg-[#18181f] text-ui-primary" : "hover:bg-[#141418]"
          }`}
          onMouseEnter={() => setHoveredMetric(key)}
          onMouseLeave={() => setHoveredMetric(null)}
        >
          <span
            className={`w-7 text-[9px] text-right font-mono transition-colors ${
              isHovered ? "font-bold" : "text-ui-dim"
            }`}
            style={isHovered ? { color: cfg.color } : undefined}
          >
            {key}
          </span>
          <div className="w-12 h-1 bg-ui-border rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all duration-200"
              style={{
                width: `${pct}%`,
                backgroundColor: barColor,
                opacity: isHovered ? 1 : 0.6,
                animation: isHovered ? "none" : "pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
              }}
            />
          </div>
          <span
            className={`text-[9px] transition-colors w-10 text-right font-mono ${
              isHovered ? "font-bold text-ui-primary" : "text-ui-dim"
            }`}
          >
            {display}
          </span>
        </div>
      </Tooltip>
    )
  }

  return (
    <div className="mt-2 pt-2">
      <div className="flex items-center gap-1.5 mb-1.5 font-mono">
        <span
          className="text-[8px] leading-none"
          style={{ color: stateColor }}
        >
          ●
        </span>
        <span className="text-[10px] text-ui-secondary">vitality</span>
        <span className="text-[9px] ml-auto flex items-center gap-1.5" style={{ color: stateColor }}>
          <span>{state}</span>
          {vitality != null && (
            <span
              className="cursor-pointer hover:underline"
              onMouseEnter={() => setHoveredMetric("vit")}
              onMouseLeave={() => setHoveredMetric(null)}
            >
              vit:{vitality.toFixed(2)}
            </span>
          )}
          {paskHealth != null && (
            <span
              className="cursor-pointer hover:underline"
              onMouseEnter={() => setHoveredMetric("ph")}
              onMouseLeave={() => setHoveredMetric(null)}
            >
              ph:{paskHealth.toFixed(2)}
            </span>
          )}
          {cpi != null && (
            <span
              className="text-semantic-gold cursor-pointer hover:underline"
              onMouseEnter={() => setHoveredMetric("cpi")}
              onMouseLeave={() => setHoveredMetric(null)}
            >
              cpi:{cpi.toFixed(2)}
            </span>
          )}
        </span>
      </div>

      {error && <p className="text-[9px] text-semantic-red font-mono">{error}</p>}

      {/* Active Prompt Interventions & Somatic Directives */}
      {somaticDirective && (
        <div className="mb-2 p-1.5 bg-[#141414] border border-[#2a2a2a] rounded font-mono text-[9px] leading-snug">
          <div className="flex items-center justify-between text-semantic-gold font-bold mb-0.5">
            <span className="flex items-center gap-1">
              <span className="animate-ping inline-flex h-1.5 w-1.5 rounded-full bg-semantic-gold opacity-75"></span>
              {intervention?.mode ? `[INJECTION: ${intervention.mode.toUpperCase()}]` : "[PROMPT DIRECTIVE]"}
            </span>
            {metrics?.recommendations?.consecutive_stagnant_turns ? (
              <span className="text-ui-dim text-[8px]">streak:{metrics.recommendations.consecutive_stagnant_turns}t</span>
            ) : null}
          </div>
          <p className="text-ui-dim text-[8px] line-clamp-3 overflow-hidden text-ellipsis whitespace-normal" title={somaticDirective}>
            {somaticDirective}
          </p>
          {intervention?.reason && (
            <div className="mt-1 text-[7px] text-[#666] border-t border-[#222] pt-0.5">
              trigger: {intervention.reason}
            </div>
          )}
        </div>
      )}

      {/* Progression Sparkline (Up to 30 conversation rounds) */}
      {metrics?.history && metrics.history.length > 1 && (() => {
        const hist = metrics.history
        const width = 240
        const height = 48
        const padX = 8
        const padY = 6
        const n = hist.length

        // Helper to map points to svg path coordinates
        const getPoints = (getter: (m: MetricsInfo) => number | null | undefined, scaleMax: number = 1.0) => {
          return hist.map((item, idx) => {
            const raw = getter(item)
            const clamped = raw != null ? Math.max(0, Math.min(scaleMax, raw)) : 0
            const val = scaleMax > 0 ? clamped / scaleMax : 0.5
            const x = padX + (idx / Math.max(1, n - 1)) * (width - 2 * padX)
            const y = height - padY - val * (height - 2 * padY)
            return { x, y, val: raw }
          })
        }

        const vitPoints = getPoints(m => m.conversation_vitality)
        const cpPoints = getPoints(m => m.collapse_pressure ?? m.boringness)
        const cpiPoints = getPoints(m => m.cpi)

        const toPath = (pts: { x: number; y: number }[]) =>
          pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ")

        const lastVit = vitPoints[vitPoints.length - 1]?.val
        const lastCp = cpPoints[cpPoints.length - 1]?.val
        const lastCpi = cpiPoints[cpiPoints.length - 1]?.val

        // Dynamic Hovered Metric Trajectory Line
        const hoveredConfig = hoveredMetric ? METRIC_CONFIG[hoveredMetric] : null
        const hoveredPoints = hoveredConfig
          ? getPoints(hoveredConfig.getValue, hoveredConfig.max)
          : null
        const lastHoveredVal = hoveredPoints ? hoveredPoints[hoveredPoints.length - 1]?.val : null

        return (
          <div className="mb-2.5 p-1.5 bg-[#0e0e11] border border-ui-border/60 rounded font-mono">
            <div className="flex items-center justify-between text-[8px] text-ui-dim mb-1 border-b border-ui-border/30 pb-0.5">
              <span className="uppercase tracking-wider">
                {hoveredConfig ? (
                  <span style={{ color: hoveredConfig.color }} className="font-bold flex items-center gap-1">
                    <span className="inline-block w-1.5 h-1.5 rounded-full" style={{ backgroundColor: hoveredConfig.color }}></span>
                    {hoveredConfig.label}: {lastHoveredVal != null ? lastHoveredVal.toFixed(3) : "—"} ({n}t)
                  </span>
                ) : (
                  `Trajectory (${n} turns)`
                )}
              </span>
              <div className="flex items-center gap-2">
                <span
                  className="text-semantic-green flex items-center gap-0.5 cursor-pointer hover:underline"
                  onMouseEnter={() => setHoveredMetric("vit")}
                  onMouseLeave={() => setHoveredMetric(null)}
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-semantic-green"></span>
                  vit{lastVit != null ? `:${lastVit.toFixed(2)}` : ""}
                </span>
                <span
                  className="text-semantic-gold flex items-center gap-0.5 cursor-pointer hover:underline"
                  onMouseEnter={() => setHoveredMetric("cpi")}
                  onMouseLeave={() => setHoveredMetric(null)}
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-semantic-gold"></span>
                  cpi{lastCpi != null ? `:${lastCpi.toFixed(2)}` : ""}
                </span>
                <span
                  className="text-semantic-red flex items-center gap-0.5 cursor-pointer hover:underline"
                  onMouseEnter={() => setHoveredMetric("cp")}
                  onMouseLeave={() => setHoveredMetric(null)}
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-semantic-red"></span>
                  cp{lastCp != null ? `:${lastCp.toFixed(2)}` : ""}
                </span>
              </div>
            </div>

            <div className="w-full relative h-12 overflow-hidden">
              <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-full overflow-visible">
                {/* Horizontal reference lines */}
                <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} stroke="#222" strokeWidth="1" />
                <line x1={padX} y1={height / 2} x2={width - padX} y2={height / 2} stroke="#1f1f24" strokeWidth="1" strokeDasharray="2,2" />
                <line x1={padX} y1={padY} x2={width - padX} y2={padY} stroke="#222" strokeWidth="1" />

                {/* Baseline lines (softened if another metric is hovered) */}
                <path
                  d={toPath(vitPoints)}
                  fill="none"
                  stroke="var(--color-semantic-green)"
                  strokeWidth={hoveredMetric === "vit" ? 2.2 : 1.4}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={hoveredMetric && hoveredMetric !== "vit" ? 0.25 : 0.9}
                />
                <path
                  d={toPath(cpiPoints)}
                  fill="none"
                  stroke="var(--color-semantic-gold)"
                  strokeWidth={hoveredMetric === "cpi" ? 2.2 : 1.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray="3,1.5"
                  opacity={hoveredMetric && hoveredMetric !== "cpi" ? 0.25 : 0.85}
                />
                <path
                  d={toPath(cpPoints)}
                  fill="none"
                  stroke="var(--color-semantic-red)"
                  strokeWidth={hoveredMetric === "cp" ? 2.2 : 1.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={hoveredMetric && hoveredMetric !== "cp" ? 0.25 : 0.85}
                />

                {/* Dedicated Hovered Metric Line */}
                {hoveredPoints && hoveredConfig && hoveredMetric !== "vit" && hoveredMetric !== "cp" && hoveredMetric !== "cpi" && (
                  <path
                    d={toPath(hoveredPoints)}
                    fill="none"
                    stroke={hoveredConfig.color}
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    style={{ filter: `drop-shadow(0 0 3px ${hoveredConfig.color}66)` }}
                  />
                )}

                {/* Point dots */}
                {vitPoints.length > 0 && (!hoveredMetric || hoveredMetric === "vit") && (
                  <circle cx={vitPoints[vitPoints.length - 1].x} cy={vitPoints[vitPoints.length - 1].y} r="2.5" fill="var(--color-semantic-green)" />
                )}
                {cpiPoints.length > 0 && (!hoveredMetric || hoveredMetric === "cpi") && (
                  <circle cx={cpiPoints[cpiPoints.length - 1].x} cy={cpiPoints[cpiPoints.length - 1].y} r="2" fill="var(--color-semantic-gold)" />
                )}
                {cpPoints.length > 0 && (!hoveredMetric || hoveredMetric === "cp") && (
                  <circle cx={cpPoints[cpPoints.length - 1].x} cy={cpPoints[cpPoints.length - 1].y} r="2" fill="var(--color-semantic-red)" />
                )}
                {hoveredPoints && hoveredPoints.length > 0 && hoveredConfig && hoveredMetric !== "vit" && hoveredMetric !== "cp" && hoveredMetric !== "cpi" && (
                  <circle
                    cx={hoveredPoints[hoveredPoints.length - 1].x}
                    cy={hoveredPoints[hoveredPoints.length - 1].y}
                    r="3"
                    fill={hoveredConfig.color}
                  />
                )}
              </svg>
            </div>
          </div>
        )
      })()}

      {metrics?.latest && (
        <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-1.5">
          {renderBar("cpi", "conversational progress index", metrics.latest.cpi, 1.0,
            "Grounded conversational velocity: sqrt(velocity x teachback x actionability). <0.10 = empty drift")}
          {renderBar("tb", "teachback ratio", metrics.latest.teachback_ratio, 1.0,
            "Paskian symmetry: does the human assimilate agent concepts and feed them back? <0.10 = low uptake")}
          {renderBar("act", "actionability", metrics.latest.actionability, 1.0,
            "Operational grounding: presence of tests, code, mathematical equations, or invariants")}
          {renderBar("cp", "collapse pressure", metrics.latest.collapse_pressure ?? metrics.latest.boringness, 1.0,
            "Sycophancy attractor drag & perturbation failure. >0.60 = sycophantic entrainment or boredom", true)}
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
          {renderBar("vel", "conceptual velocity", metrics.latest.conceptual_velocity, 1.0,
            "Disjoint centroid drift rate (last 3 vs preceding 3). <0.02 = frozen, >0.80 = noise")}
          {renderBar("drr", "divergence resolution ratio", metrics.latest.divergence_resolution_ratio, 1.0,
            "Does perturbation lead to resolution? Positive = convergence, negative = rejection")}
        </div>
      )}

      {loading && !metrics && (
        <p className="text-[9px] text-ui-dim font-mono animate-pulse">loading...</p>
      )}

      {!metrics && !error && !loading && (
        <p className="text-[9px] text-ui-dim font-mono">waiting for data...</p>
      )}

      {metrics?.latest?.phase_shifts && metrics.latest.phase_shifts.length > 0 && (
        <div className="mt-1.5 font-mono">
          <span className="text-[9px] text-semantic-gold">phase shifts:</span>
          <div className="flex flex-wrap gap-1 mt-0.5">
            {metrics.latest.phase_shifts.map((s, i) => (
              <span key={i} className="text-[8px] text-semantic-gold">
                {s.event} {s.direction === "rise" ? "↑" : "↓"}{s.delta.toFixed(2)}
              </span>
            ))}
          </div>
        </div>
      )}

      {metrics?.recommendations?.triggered_flags && metrics.recommendations.triggered_flags.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1 font-mono">
          {metrics.recommendations.triggered_flags.map((f) => (
            <span key={f} className="text-[8px] text-semantic-red border border-semantic-red/30 px-1 rounded-xs">
              {f}
            </span>
          ))}
        </div>
      )}

      {metrics?.recommendations?.temperature?.delta !== undefined && metrics.recommendations.temperature.delta !== 0 && (
        <div className="mt-1 text-[9px] text-ui-dim font-mono">
          param: T{metrics.recommendations.temperature.value.toFixed(2)}
          {metrics.recommendations.temperature.clamped ? " (clamped)" : ""}
        </div>
      )}
    </div>
  )
}

export const VitalitySection = memo(VitalitySectionComponent)
