import { memo } from "react"
import { useTelemetryMetrics } from "../../../hooks/useTelemetry"
import type { DiffractiveInfo } from "../../../api/client"

interface DiffractionSectionProps {
  enabled?: boolean
  messageCount?: number
}

function DiffractiveTooltip({ title, value, desc }: { title: string; value?: string; desc: string }) {
  return (
    <div className="
      absolute bottom-full left-0 mb-1.5 px-2 py-1.5
      bg-[#111] border border-[#262626] rounded
      text-[9px] text-[#aaa] font-sans leading-relaxed
      whitespace-normal w-56 z-50
      opacity-0 group-hover:opacity-100
      transition-opacity duration-150
      pointer-events-none shadow-lg shadow-black/80
      backdrop-blur-sm
    ">
      <div className="text-[#f43f5e] font-bold text-[10px]">{title}</div>
      {value && <div className="text-[#777] font-mono text-[8px] mt-0.5">{value}</div>}
      <div className="text-[#888] mt-1 font-normal leading-normal">{desc}</div>
    </div>
  )
}

function DiffractionSectionComponent({ enabled = false }: DiffractionSectionProps) {
  const { metrics, metricsLoading: loading, metricsError: error } = useTelemetryMetrics(enabled)

  if (error && !metrics) {
    return (
      <div className="mt-2 border-t border-[#1a1a1a] pt-2">
        <p className="text-[9px] text-[#ef4444] font-mono">{error}</p>
      </div>
    )
  }

  if (loading && !metrics) {
    return (
      <div className="mt-2 border-t border-[#1a1a1a] pt-2">
        <p className="text-[9px] text-[#444] font-mono animate-pulse">loading...</p>
      </div>
    )
  }

  const diff: DiffractiveInfo | null | undefined = metrics?.diffractive

  if (!diff) {
    return (
      <div className="mt-2 border-t border-[#1a1a1a] pt-2">
        <p className="text-[9px] text-[#444] font-mono">no diffractive data yet</p>
      </div>
    )
  }

  const isActive = diff.state === "STAGNANT"
  const stateColor = isActive ? "#f43f5e" : "#555"

  const maxTimer = 3
  const timerBlocks = Array.from({ length: maxTimer }, (_, i) =>
    i < diff.cohesion_timer ? "█" : "░"
  ).join(" ")

  const firstSim = diff.sources.length > 0 ? diff.sources[0].similarity : 0
  const barWidth = 30
  const memMin = diff.similarity_range_memory[0] ?? 0.45
  const memMax = diff.similarity_range_memory[1] ?? 0.85
  const barChars: string[] = Array.from({ length: barWidth }, (_, pos) => {
    const val = pos / barWidth
    if (val >= memMin && val <= memMax) return "▒"
    return "─"
  })
  const markerPos = Math.min(barWidth - 1, Math.max(0, Math.floor(firstSim * barWidth)))
  barChars[markerPos] = "▓"
  const barStr = barChars.join("")

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-1.5 font-mono">
        <span
          className="text-[8px] leading-none"
          style={{ color: stateColor }}
        >
          {isActive ? "●" : "○"}
        </span>
        <span className="text-[10px] text-[#888]">diffraction</span>
        <span className="text-[9px] ml-auto" style={{ color: stateColor }}>
          {diff.state}
        </span>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 font-mono text-[8px] leading-relaxed space-y-px">
        <div className="text-[#555]">
          {"=== STAGNATION TELEMETRY ==="}
        </div>
        <div className="flex gap-1 flex-wrap">
          <span className="text-[#666]">METRICS</span>
          <span className={`group relative cursor-help ${isActive ? "text-[#f43f5e]/80" : "text-[#888]"}`}>
            P:{diff.p_diffract.toFixed(2)}
            <DiffractiveTooltip
              title="Diffraction Probability (P)"
              value={`Value: ${diff.p_diffract.toFixed(4)}`}
              desc="The calculated chance of triggering diffractive context injection, driven by boringness (+), low entropy (+), and low vitality (-)."
            />
          </span>
          <span className="group relative cursor-help text-[#888]">
            S:{diff.stagnation_index.toFixed(2)}
            <DiffractiveTooltip
              title="Stagnation Index (S)"
              value={`Value: ${diff.stagnation_index.toFixed(4)}`}
              desc="Ratio between boringness and vitality. Reflects the presence and intensity of conversational loops."
            />
          </span>
          <span className="group relative cursor-help text-[#888]">
            R:{diff.r_context.toFixed(2)}
            <DiffractiveTooltip
              title="Context Ratio (R)"
              value={`Value: ${diff.r_context.toFixed(4)}`}
              desc="The dynamic context ratio used to scale down the token budget limit based on loop severity."
            />
          </span>
        </div>
        <div className="flex gap-1 flex-wrap group relative cursor-help">
          <span className="text-[#666]">STATE</span>
          <span style={{ color: stateColor }}>{diff.state}</span>
          {diff.previous_state !== diff.state && (
            <span className="text-[#555]">(was {diff.previous_state})</span>
          )}
          <DiffractiveTooltip
            title="Stagnation State"
            value={`Current: ${diff.state} | Previous: ${diff.previous_state}`}
            desc="FLOWING = standard loop-free generation. STAGNANT = loop detected, context injection active."
          />
        </div>
        <div className="flex gap-1 group relative cursor-help">
          <span className="text-[#666]">LOCK</span>
          <span className={isActive ? "text-[#f43f5e]/80" : "text-[#888]"}>[{timerBlocks}]</span>
          <span className="text-[#555]">({diff.cohesion_timer}t)</span>
          <DiffractiveTooltip
            title="Cohesion Lock Timer"
            value={`Turns Locked: ${diff.cohesion_timer}`}
            desc="Countdown timer holding the STAGNANT state active for a minimum duration. Gives new conceptual paths space to establish themselves."
          />
        </div>

        <div className="text-[#555] mt-1">
          {"=== INTERFERENCE PATTERN ==="}
        </div>

        {diff.sources.length > 0 ? (
          <>
            {diff.sources.map((s, i) => (
              <div key={i} className="flex gap-1 flex-wrap group relative cursor-help">
                <span className={s.type === "nomadic" ? "text-[#60a5fa]/70" : s.type === "semantic_knot" ? "text-[#a78bfa]/70" : "text-[#4ade80]/70"}>
                  {s.type === "nomadic" ? "NOM" : s.type === "semantic_knot" ? "KNOT" : "DRM"}
                </span>
                <span className="text-[#888] truncate max-w-32">{s.source_title}</span>
                <span className="text-[#888] ml-auto">δ{s.similarity.toFixed(3)}</span>
                <DiffractiveTooltip
                  title={s.type === "nomadic" ? "Nomadic Memory Source (NOM)" : s.type === "semantic_knot" ? "Sedimented Semantic Knot (KNOT)" : "Dormant Document Sediment (DRM)"}
                  value={`Similarity (delta): ${s.similarity.toFixed(4)}`}
                  desc={s.type === "nomadic"
                    ? "Injected context retrieved from an orthogonal/external conversation memory to shift the loop."
                    : s.type === "semantic_knot"
                      ? "Injected context retrieved from distilled semantic knots of past conversations."
                      : "Injected context retrieved from static uploaded files matching the Goldilocks zone."}
                />
              </div>
            ))}
            <div className="mt-0.5 text-[#555] overflow-hidden whitespace-nowrap group relative cursor-help">
              [{barStr}]
              <DiffractiveTooltip
                title="Goldilocks Zone Matcher"
                value={`Mem: [${diff.similarity_range_memory.map(v => v.toFixed(2)).join(",")}] | File: [${diff.similarity_range_files.map(v => v.toFixed(2)).join(",")}]`}
                desc="Visualization of similarity matching. Shaded regions (▒) show Goldilocks bounds. Marker (▓) shows similarity of the primary source relative to bounds."
              />
            </div>
          </>
        ) : (
          <div className="text-[#444]">no sources injected</div>
        )}

        <div className="flex gap-1 flex-wrap mt-1 group relative cursor-help">
          <span className="text-[#555]">SEARCH</span>
          <span className="text-[#888]">{diff.candidates_searched} cand</span>
          <span className="text-[#888]">{diff.items_injected} inj</span>
          <span className="text-[#555]">{diff.tokens_used}/{diff.token_budget}tok</span>
          <span className="text-[#444] ml-auto">{diff.duration_ms.toFixed(0)}ms</span>
          <DiffractiveTooltip
            title="Vector Search & Budgeting"
            value={`Duration: ${diff.duration_ms.toFixed(1)}ms | Injected: ${diff.items_injected}`}
            desc="cand = scanned similarity candidates; inj = items injected under the budget limit; tok = tokens used / dynamic budget limit; ms = vector search duration."
          />
        </div>

        <div className="flex gap-1 flex-wrap group relative cursor-help">
          <span className="text-[#555]">RANGE</span>
          <span className="text-[#888]">mem:[{diff.similarity_range_memory.map(v => v.toFixed(2)).join(",")}]</span>
          <span className="text-[#888]">file:[{diff.similarity_range_files.map(v => v.toFixed(2)).join(",")}]</span>
          <DiffractiveTooltip
            title="Dynamic Similarity Ranges"
            desc="Similarity matching ranges (Goldilocks zone). mem = ranges for external conversation memory; file = ranges for static document chunks."
          />
        </div>
        <div className="flex gap-1 group relative cursor-help">
          <span className="text-[#555]">MAX</span>
          <span className="text-[#888]">{diff.dynamic_max} slots</span>
          <DiffractiveTooltip
            title="Dynamic Slot Limit"
            value={`Limit: ${diff.dynamic_max} slots`}
            desc="Maximum number of diffractive candidate slots allowed to be injected during this turn, scaled dynamically based on stagnation index."
          />
        </div>
      </div>
    </div>
  )
}

export const DiffractionSection = memo(DiffractionSectionComponent)
