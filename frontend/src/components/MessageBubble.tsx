import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { ChatMessage, MetricsInfo } from "../api/client"

function VitalityBar({ metrics }: { metrics: MetricsInfo }) {
  const items: { label: string; value: number | null; max: number; warn: number; crit: number; invert: boolean }[] = [
    { label: "sim", value: metrics.pairwise_similarity, max: 1.0, warn: 0.7, crit: 0.85, invert: false },
    { label: "nov", value: metrics.conceptual_novelty, max: 1.0, warn: 0.15, crit: 0.07, invert: true },
    { label: "ent", value: metrics.rolling_entropy, max: 0.25, warn: 0.01, crit: 0.005, invert: true },
    { label: "coup", value: metrics.coupling_coherence, max: 1.0, warn: 0.7, crit: 0.9, invert: false },
    { label: "divr", value: metrics.agent_self_divergence, max: 1.0, warn: 0.2, crit: 0.1, invert: true },
    { label: "rP", value: metrics.reverse_perturbation, max: 1.0, warn: 0.15, crit: 0.08, invert: true },
    { label: "srp", value: metrics.surprise_index, max: 1.0, warn: 0.3, crit: 0.5, invert: false },
    { label: "mpi", value: metrics.mutual_perturbation, max: 1.0, warn: 0.15, crit: 0.05, invert: true },
  ]

  const barColor = (item: typeof items[0]) => {
    const { value, warn, crit, invert } = item
    if (value == null) return "#333"
    if (invert) {
      if (value <= crit) return "#ef4444"
      if (value <= warn) return "#facc15"
      return "#4ade80"
    }
    if (value >= crit) return "#ef4444"
    if (value >= warn) return "#facc15"
    return "#4ade80"
  }

  return (
    <div className="mt-1 flex items-center gap-1 text-[10px] text-[#555] select-none flex-wrap">
      {items.map((item) => {
        const pct = item.value != null ? Math.min(100, Math.max(0, (item.value / item.max) * 100)) : 0
        const color = barColor(item)
        return (
          <div key={item.label} className="flex items-center gap-0.5">
            <span className="w-7 text-right text-[#444]">{item.label}</span>
            <div className="w-10 h-1.5 bg-[#1a1a1a] rounded-sm overflow-hidden">
              <div
                className="h-full rounded-sm transition-all"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
          </div>
        )
      })}
      {metrics.conversation_vitality != null && (
        <span className="ml-1">
          vit:<span className={metrics.conversation_vitality < 0.35 ? "text-[#f87171]" : "text-[#4ade80]"}>
            {metrics.conversation_vitality.toFixed(2)}
          </span>
        </span>
      )}
      {metrics.phase_shifts && metrics.phase_shifts.length > 0 && (
        <span className="ml-1 text-[#facc15]">
          {"\u26A1"}{metrics.phase_shifts.length}
        </span>
      )}
    </div>
  )
}

export function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isHuman = msg.speaker === "human"
  const [thinkingOpen, setThinkingOpen] = useState(false)

  return (
    <div className={`mb-3 ${isHuman ? "" : "pl-4"}`}>
      <div className={`text-sm leading-relaxed ${isHuman ? "text-[#777]" : "text-[#c8c8c8]"}`}>
        {isHuman ? (
          <span>
            <span className="text-[#555] select-none">&gt; </span>
            {msg.content}
          </span>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      {isHuman && msg.metrics && <VitalityBar metrics={msg.metrics} />}

      {msg.thinking && (
        <div className="mt-1">
          <button
            onClick={() => setThinkingOpen(!thinkingOpen)}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1"
          >
            <span>{thinkingOpen ? "\u25BC" : "\u25B6"}</span>
            <span>thinking</span>
          </button>
          {thinkingOpen && (
            <div className="mt-1 pl-3 border-l border-[#2a2a2a] text-xs text-[#666] leading-relaxed whitespace-pre-wrap">
              {msg.thinking}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
