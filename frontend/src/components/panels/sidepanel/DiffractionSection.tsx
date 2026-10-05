import { memo } from "react"
import { useTelemetryMetrics } from "../../../hooks/useTelemetry"
import { Tooltip } from "../../UI/Tooltip"
import type { DiffractiveInfo } from "../../../api/client"

interface DiffractionSectionProps {
  conversationId?: string | null
  enabled?: boolean
  messageCount?: number
}

function DiffractionSectionComponent({ conversationId, enabled = false }: DiffractionSectionProps) {
  const { metrics, metricsLoading: loading, metricsError: error } = useTelemetryMetrics(conversationId, enabled)

  if (error && !metrics) {
    return (
      <div className="mt-2 border-t border-ui-border/40 pt-2">
        <p className="text-[10px] text-semantic-red font-mono">{error}</p>
      </div>
    )
  }

  if (loading && !metrics) {
    return (
      <div className="mt-2 border-t border-ui-border/40 pt-2">
        <p className="text-[10px] text-ui-dim font-mono animate-pulse">loading telemetry...</p>
      </div>
    )
  }

  const diff: DiffractiveInfo | null | undefined = metrics?.diffractive

  if (!diff) {
    return (
      <div className="mt-2 border-t border-ui-border/40 pt-2">
        <p className="text-[10px] text-ui-dim font-mono">no diffractive data yet</p>
      </div>
    )
  }

  const isStagnant = diff.state === "STAGNANT"
  const maxTimer = 3
  const activeTimer = Math.max(0, Math.min(diff.cohesion_timer, maxTimer))

  // Range bounds for Goldilocks visualizer
  const memMin = diff.similarity_range_memory[0] ?? 0.45
  const memMax = diff.similarity_range_memory[1] ?? 0.85
  const firstSim = diff.sources.length > 0 ? diff.sources[0].similarity : null

  return (
    <div className="mt-2 pt-2 space-y-3 font-mono">
      {/* State & Lock Header */}
      <div className="flex items-center justify-between gap-2 p-2 rounded bg-black/40 border border-white/5">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isStagnant
                ? "bg-semantic-red animate-pulse shadow-[0_0_8px_rgba(244,63,94,0.6)]"
                : "bg-semantic-green/80"
            }`}
          />
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className={`text-[11px] font-bold tracking-wide ${isStagnant ? "text-semantic-red" : "text-ui-primary"}`}>
                {diff.state}
              </span>
              {diff.previous_state && diff.previous_state !== diff.state && (
                <span className="text-[9px] text-ui-dim">(was {diff.previous_state})</span>
              )}
            </div>
            {diff.activation_reason && (
              <span className="text-[8px] text-ui-dim lowercase">
                trigger: {diff.activation_reason.replace(/_/g, " ")}
              </span>
            )}
          </div>
        </div>

        {/* Cohesion Lock Widget */}
        <Tooltip
          title="Cohesion Lock Timer"
          subtitle={`Turns remaining: ${diff.cohesion_timer}`}
          description={`Holds STAGNANT state active for ${maxTimer} turns so injected orthogonal memories can break attractor loops.`}
          titleColorClass="text-semantic-gold"
          position="bottom-right"
        >
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-white/[0.03] border border-white/5 cursor-help">
            <span className="text-[8px] text-ui-dim tracking-wider uppercase">LOCK</span>
            <div className="flex items-center gap-0.5">
              {Array.from({ length: maxTimer }).map((_, i) => (
                <span
                  key={i}
                  className={`w-1.5 h-2.5 rounded-xs transition-colors ${
                    i < activeTimer
                      ? isStagnant
                        ? "bg-semantic-red/90"
                        : "bg-semantic-gold/80"
                      : "bg-white/10"
                  }`}
                />
              ))}
            </div>
            <span className="text-[9px] text-ui-dim">{diff.cohesion_timer}t</span>
          </div>
        </Tooltip>
      </div>

      {/* Stagnation Telemetry Cards */}
      <div className="space-y-1.5">
        <div className="text-[8px] uppercase tracking-widest text-ui-dim font-bold">
          Stagnation Telemetry
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          {/* P_diffract Card */}
          <Tooltip
            title="Diffraction Probability (P)"
            subtitle={`P: ${diff.p_diffract.toFixed(4)}`}
            description="Calculated trigger score driven by collapse pressure and persistence streaks."
            titleColorClass={diff.p_diffract >= 0.55 ? "text-semantic-red" : "text-semantic-green"}
            position="bottom-left"
            className="w-full"
          >
            <div className="p-1.5 rounded bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors cursor-help space-y-1">
              <div className="flex justify-between items-center text-[8px] text-ui-dim">
                <span>P_DIFF</span>
                <span className="text-[7px]">PROB</span>
              </div>
              <div className={`text-[12px] font-bold ${diff.p_diffract >= 0.55 ? "text-semantic-red" : "text-ui-primary"}`}>
                {diff.p_diffract.toFixed(2)}
              </div>
              <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    diff.p_diffract >= 0.55 ? "bg-semantic-red" : "bg-semantic-green/70"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, diff.p_diffract * 100))}%` }}
                />
              </div>
            </div>
          </Tooltip>

          {/* Stagnation Index Card */}
          <Tooltip
            title="Stagnation Index (S)"
            subtitle={`S: ${diff.stagnation_index.toFixed(4)}`}
            description="Ratio of collapse pressure (boringness) to vitality: B / (V + 0.01)."
            titleColorClass={diff.stagnation_index >= 0.6 ? "text-semantic-red" : "text-semantic-gold"}
            position="bottom-center"
            className="w-full"
          >
            <div className="p-1.5 rounded bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors cursor-help space-y-1">
              <div className="flex justify-between items-center text-[8px] text-ui-dim">
                <span>STAGN</span>
                <span className="text-[7px]">INDEX</span>
              </div>
              <div className={`text-[12px] font-bold ${diff.stagnation_index >= 0.6 ? "text-semantic-red" : "text-ui-primary"}`}>
                {diff.stagnation_index.toFixed(2)}
              </div>
              <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    diff.stagnation_index >= 0.6 ? "bg-semantic-red" : "bg-semantic-gold/70"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, diff.stagnation_index * 100))}%` }}
                />
              </div>
            </div>
          </Tooltip>

          {/* Context Ratio Card */}
          <Tooltip
            title="Context Ratio (R)"
            subtitle={`R: ${diff.r_context.toFixed(4)}`}
            description="Dynamic multiplier (0.20 + 0.35 * S) scaling token budget limits for injected context."
            titleColorClass="text-blue-400"
            position="bottom-right"
            className="w-full"
          >
            <div className="p-1.5 rounded bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors cursor-help space-y-1">
              <div className="flex justify-between items-center text-[8px] text-ui-dim">
                <span>R_CTX</span>
                <span className="text-[7px]">BUDGET</span>
              </div>
              <div className="text-[12px] font-bold text-ui-primary">
                {diff.r_context.toFixed(2)}
              </div>
              <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500/70 transition-all duration-300"
                  style={{ width: `${Math.min(100, Math.max(0, (diff.r_context / 0.55) * 100))}%` }}
                />
              </div>
            </div>
          </Tooltip>
        </div>
      </div>

      {/* Interference Pattern & Injected Perturbations */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[8px] uppercase tracking-widest text-ui-dim font-bold">
          <span>Interference Pattern</span>
          {diff.sources.length > 0 && (
            <span className="text-semantic-green font-normal lowercase">
              {diff.sources.length} injected
            </span>
          )}
        </div>

        {diff.sources.length > 0 ? (
          <div className="space-y-1.5">
            {diff.sources.map((s, i) => {
              const typeColor =
                s.type === "nomadic"
                  ? "text-blue-400 bg-blue-500/10 border-blue-500/30"
                  : s.type === "semantic_knot"
                    ? "text-purple-400 bg-purple-500/10 border-purple-500/30"
                    : "text-emerald-400 bg-emerald-500/10 border-emerald-500/30"
              const typeLabel =
                s.type === "nomadic" ? "NOM" : s.type === "semantic_knot" ? "KNOT" : "DRM"
              const fullTypeName =
                s.type === "nomadic"
                  ? "Nomadic Memory (Cross-Thread)"
                  : s.type === "semantic_knot"
                    ? "Semantic Knot (Distilled Concept)"
                    : "Dormant Document Chunk"

              return (
                <Tooltip
                  key={i}
                  title={fullTypeName}
                  subtitle={`Similarity δ: ${s.similarity.toFixed(4)}`}
                  description={s.source_title}
                  titleColorClass={
                    s.type === "nomadic"
                      ? "text-blue-400"
                      : s.type === "semantic_knot"
                        ? "text-purple-400"
                        : "text-emerald-400"
                  }
                  position="bottom-left"
                  className="w-full block"
                >
                  <div className="flex items-center gap-1.5 p-1.5 rounded bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors cursor-help">
                    <span className={`text-[8px] px-1 py-0.5 rounded font-bold border ${typeColor}`}>
                      {typeLabel}
                    </span>
                    <span className="text-[9px] text-ui-primary truncate flex-1">
                      {s.source_title}
                    </span>
                    <span className="text-[9px] text-ui-dim font-mono ml-auto">
                      δ{s.similarity.toFixed(3)}
                    </span>
                  </div>
                </Tooltip>
              )
            })}

            {/* Visual Goldilocks Range Meter */}
            <Tooltip
              title="Goldilocks Zone Matcher"
              subtitle={`Mem: [${memMin.toFixed(2)}, ${memMax.toFixed(2)}] | File: [${(diff.similarity_range_files[0] ?? 0.35).toFixed(2)}, ${(diff.similarity_range_files[1] ?? 0.75).toFixed(2)}]`}
              description="Dynamically sliding similarity window. Shaded zone shows accepted similarity range; gold tick marks primary candidate position."
              titleColorClass="text-blue-400"
              position="bottom-left"
              className="w-full block"
            >
              <div className="p-1.5 rounded bg-white/[0.02] border border-white/5 cursor-help space-y-1">
                <div className="flex justify-between text-[8px] text-ui-dim">
                  <span>0.0</span>
                  <span className="text-ui-dim/80">GOLDILOCKS ZONE [{memMin.toFixed(2)} - {memMax.toFixed(2)}]</span>
                  <span>1.0</span>
                </div>
                <div className="relative w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  {/* Goldilocks Shaded Zone */}
                  <div
                    className="absolute top-0 bottom-0 bg-blue-500/20 border-x border-blue-400/40"
                    style={{
                      left: `${memMin * 100}%`,
                      width: `${(memMax - memMin) * 100}%`,
                    }}
                  />
                  {/* Primary Source Marker */}
                  {firstSim !== null && (
                    <div
                      className="absolute top-0 bottom-0 w-1 bg-semantic-gold shadow-[0_0_6px_rgba(234,179,8,0.8)]"
                      style={{ left: `${Math.min(99, Math.max(1, firstSim * 100))}%` }}
                    />
                  )}
                </div>
              </div>
            </Tooltip>
          </div>
        ) : (
          <div className="p-2 rounded bg-white/[0.01] border border-white/5 text-center">
            <span className="text-[9px] text-ui-dim italic">
              [idle — no perturbation required]
            </span>
          </div>
        )}
      </div>

      {/* Vector Search & Budget Telemetry Footer */}
      <Tooltip
        title="Vector Matcher Telemetry"
        subtitle={`${diff.candidates_searched} candidates scanned • ${diff.items_injected} injected in ${diff.duration_ms.toFixed(0)}ms`}
        description={`Token budget: ${diff.tokens_used}/${diff.token_budget} tok | Max slots: ${diff.dynamic_max}`}
        titleColorClass="text-ui-primary"
        position="bottom-left"
        className="w-full block"
      >
        <div className="p-2 rounded bg-black/40 border border-white/5 text-[8px] text-ui-dim cursor-help space-y-1">
          <div className="flex justify-between items-center">
            <span className="text-ui-dim/80">SEARCH</span>
            <span className="text-ui-primary font-mono">{diff.candidates_searched} cand</span>
            <span className="text-ui-dim">•</span>
            <span className="text-ui-primary font-mono">{diff.items_injected} inj</span>
            <span className="text-ui-dim">•</span>
            <span className="text-ui-primary font-mono">{diff.tokens_used}/{diff.token_budget} tok</span>
            <span className="text-ui-dim font-mono ml-auto">{diff.duration_ms.toFixed(0)}ms</span>
          </div>
          <div className="flex justify-between items-center pt-0.5 border-t border-white/5 text-[7.5px]">
            <span>SLOTS: {diff.dynamic_max} max</span>
            <span>MEM: [{diff.similarity_range_memory.map(v => v.toFixed(2)).join(",")}]</span>
            <span>FILE: [{diff.similarity_range_files.map(v => v.toFixed(2)).join(",")}]</span>
          </div>
        </div>
      </Tooltip>
    </div>
  )
}

export const DiffractionSection = memo(DiffractionSectionComponent)
