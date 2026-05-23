import { useState, memo } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import type { ChatMessage, MetricsInfo } from "../api/client"
import { getMessageThinking, getMessageContext } from "../api/client"

function VitalityBar({ metrics }: { metrics: MetricsInfo }) {
  const items: { label: string; full: string; value: number | null; max: number; warn: number; crit: number; invert: boolean; hint: string }[] = [
    { label: "SIM", full: "pairwise similarity", value: metrics.pairwise_similarity, max: 1.0, warn: 0.7, crit: 0.85, invert: false,
      hint: "Is this input repeating the previous one? >0.85 = near-duplicate" },
    { label: "NOV", full: "conceptual novelty", value: metrics.conceptual_novelty, max: 1.0, warn: 0.15, crit: 0.07, invert: true,
      hint: "Has anything similar ever been said before? <0.15 = exhausted" },
    { label: "ENT", full: "rolling entropy", value: metrics.rolling_entropy, max: 0.25, warn: 0.01, crit: 0.005, invert: true,
      hint: "Is the conversation monotonous over time? <0.01 = entropy collapse" },
    { label: "COUP", full: "coupling coherence", value: metrics.coupling_coherence, max: 1.0, warn: 0.7, crit: 0.9, invert: false,
      hint: "Is the agent responding to what was said? <0.15 = dissociation, >0.85 = echo" },
    { label: "DIVR", full: "agent self-divergence", value: metrics.agent_self_divergence, max: 1.0, warn: 0.2, crit: 0.1, invert: true,
      hint: "Is the agent repeating itself? <0.15 = self-loop" },
    { label: "RP", full: "reverse perturbation", value: metrics.reverse_perturbation, max: 1.0, warn: 0.15, crit: 0.08, invert: true,
      hint: "Did the agent's last response reshape the human's next input? <0.10 = stagnant" },
    { label: "SRP", full: "surprise index", value: metrics.surprise_index, max: 1.0, warn: 0.3, crit: 0.5, invert: false,
      hint: "Distance from decay-weighted centroid of past human inputs (d=0.75). >0.40 = phase disruption" },
    { label: "MPI", full: "mutual perturbation", value: metrics.mutual_perturbation, max: 1.0, warn: 0.15, crit: 0.05, invert: true,
      hint: "Product of coupling x reverse perturbation — are both directions active?" },
    { label: "BORE", full: "boringness", value: metrics.boringness, max: 1.0, warn: 0.4, crit: 0.6, invert: false,
      hint: "Joint failure to perturb: (1 - rP_t) x (1 - MPI_{t-1}). >0.60 = Paskian boredom" },
    { label: "VEL", full: "conceptual velocity", value: metrics.conceptual_velocity, max: 1.0, warn: 0.5, crit: 0.8, invert: false,
      hint: "Disjoint centroid drift rate (last 3 vs preceding 3). <0.02 = frozen, >0.80 = noise" },
    { label: "DRR", full: "divergence resolution ratio", value: metrics.divergence_resolution_ratio, max: 1.0, warn: 0.3, crit: 0.5, invert: false,
      hint: "Does perturbation lead to resolution? Positive = convergence, negative = rejection" },
  ]

  const valueColor = (item: typeof items[0]) => {
    const { value, warn, crit, invert } = item
    if (value == null) return "#555"
    if (invert) {
      if (value <= crit) return "#ef4444"
      if (value <= (crit + warn) / 2) return "#f97316"
      if (value <= warn) return "#facc15"
      return "#4ade80"
    }
    if (value >= crit) return "#ef4444"
    if (value >= (crit + warn) / 2) return "#f97316"
    if (value >= warn) return "#facc15"
    return "#4ade80"
  }

  const fmtVal = (v: number | null) => {
    if (v == null) return "\u2014"
    return v < 0.01 ? v.toFixed(4) : v.toFixed(3)
  }

  return (
    <div className="mt-1 text-[10px] leading-relaxed select-none flex flex-wrap items-center gap-x-2 gap-y-0.5">
      {items.map((item) => {
        const color = valueColor(item)
        const valStr = fmtVal(item.value)
        return (
          <span key={item.label} className="group relative">
            <span className="text-[#555]">#</span>
            <span className="text-[#555]">{item.label}:</span>
            <span style={{ color }}>{valStr}</span>
            <div className="
              absolute bottom-full left-0 mb-1 px-2 py-1
              bg-[#1a1a1a] border border-[#333] rounded
              text-[10px] text-[#aaa] leading-snug
              whitespace-nowrap z-50
              opacity-0 group-hover:opacity-100
              transition-opacity duration-150
              pointer-events-none
            ">
              <div className="text-[#4ade80] text-[11px] font-bold">{item.full}</div>
              <div className="text-[#888]">{valStr} / {item.max}</div>
              <div className="text-[#666] max-w-48 whitespace-normal">{item.hint}</div>
            </div>
          </span>
        )
      })}
      {metrics.conversation_vitality != null && (
        <span className="group relative">
          <span className="text-[#555]">vit:</span>
          <span className={metrics.conversation_vitality < 0.35 ? "text-[#f87171]" : "text-[#4ade80]"}>
            {metrics.conversation_vitality.toFixed(2)}
          </span>
          <div className="
            absolute bottom-full left-0 mb-1 px-2 py-1
            bg-[#1a1a1a] border border-[#333] rounded
            text-[10px] text-[#aaa] leading-snug
            whitespace-nowrap z-50
            opacity-0 group-hover:opacity-100
            transition-opacity duration-150
            pointer-events-none
          ">
            <div className="text-[#4ade80] text-[11px] font-bold">conversation vitality</div>
            <div className="text-[#888]">{metrics.conversation_vitality.toFixed(3)} / 1.0</div>
            <div className="text-[#666]">Composite aliveness score. Higher = more alive.</div>
          </div>
        </span>
      )}
      {metrics.paskian_health != null && (
        <span className="group relative">
          <span className="text-[#555]">ph:</span>
          <span className={metrics.paskian_health < 0.25 ? "text-[#f87171]" : "text-[#4ade80]"}>
            {metrics.paskian_health.toFixed(2)}
          </span>
          <div className="
            absolute bottom-full left-0 mb-1 px-2 py-1
            bg-[#1a1a1a] border border-[#333] rounded
            text-[10px] text-[#aaa] leading-snug
            whitespace-nowrap z-50
            opacity-0 group-hover:opacity-100
            transition-opacity duration-150
            pointer-events-none
          ">
            <div className="text-[#4ade80] text-[11px] font-bold">Paskian health</div>
            <div className="text-[#888]">{metrics.paskian_health.toFixed(3)} / 1.0</div>
            <div className="text-[#666]">Productive zone between strict and permissive. Higher = better.</div>
          </div>
        </span>
      )}
      {metrics.phase_shifts && metrics.phase_shifts.length > 0 && (
        <span className="text-[#facc15]">
          {"\u26A1"}{metrics.phase_shifts.length}
        </span>
      )}
    </div>
  )
}

export const MessageBubble = memo(function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isHuman = msg.speaker === "human"
  const isSystem = msg.speaker === "system"
  const [thinkingOpen, setThinkingOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [userExpanded, setUserExpanded] = useState(false)
  const [systemOpen, setSystemOpen] = useState(false)

  const [thinkingText, setThinkingText] = useState<string | null>(msg.thinking || null)
  const [loadingThinking, setLoadingThinking] = useState(false)
  const [contextText, setContextText] = useState<string | null>(msg.context_sent || null)
  const [loadingContext, setLoadingContext] = useState(false)

  const handleToggleThinking = async () => {
    if (thinkingOpen) {
      setThinkingOpen(false)
      return
    }
    setThinkingOpen(true)
    if (!thinkingText && msg.id) {
      setLoadingThinking(true)
      try {
        const res = await getMessageThinking(msg.id)
        setThinkingText(res.thinking || "No thinking trace available.")
      } catch (err) {
        console.error("Failed to load thinking trace:", err)
        setThinkingText("Failed to load thinking trace.")
      } finally {
        setLoadingThinking(false)
      }
    }
  }

  const handleToggleContext = async () => {
    if (contextOpen) {
      setContextOpen(false)
      return
    }
    setContextOpen(true)
    if (!contextText && msg.id) {
      setLoadingContext(true)
      try {
        const res = await getMessageContext(msg.id)
        setContextText(res.context_sent || "No context available.")
      } catch (err) {
        console.error("Failed to load context:", err)
        setContextText("Failed to load context.")
      } finally {
        setLoadingContext(false)
      }
    }
  }

  if (isSystem) {
    const lines = msg.content.split("\n")
    const title = lines[0] || "System trace"
    const remainingBody = lines.slice(1).join("\n")

    return (
      <div className="mb-3 pl-4 border-l border-[#222]">
        <button
          onClick={() => setSystemOpen(!systemOpen)}
          className="text-[10px] text-[#eab308]/80 hover:text-[#eab308] transition-colors flex items-center gap-1.5 font-mono"
        >
          <span>{systemOpen ? "▼" : "▶"}</span>
          <span>{title}</span>
        </button>
        {systemOpen && remainingBody && (
          <div className="mt-2 text-xs text-[#aaa] leading-relaxed markdown-body pl-3 border-l border-[#1a1a1a]">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
              {remainingBody}
            </ReactMarkdown>
          </div>
        )}
      </div>
    )
  }

  const showThinkingButton = !!msg.thinking || (msg.thinking_tokens != null && msg.thinking_tokens > 0)
  const showContextButton = !!msg.context_sent || !!msg.has_context

  return (
    <div className={`mb-3 ${isHuman ? "" : "pl-4"}`}>
      <div className={`text-sm leading-relaxed ${isHuman ? "text-[#777]" : "text-[#c8c8c8]"}`}>
        {isHuman ? (
          <div className="markdown-body">
            <span className="text-[#555] select-none">&gt; </span>
            <div className={userExpanded ? "" : "max-h-24 overflow-y-auto"}>
              <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
              {msg.content}
            </ReactMarkdown>
          </div>
        )}
      </div>

      <div className="text-[9px] text-[#444] mt-0.5 select-none flex items-center justify-between">
        <div className="flex items-center gap-2">
          {msg.timestamp && (
            <span className="text-[#555] font-mono">
              {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })}
            </span>
          )}
          {!isHuman && (msg.model_used || msg.provider_used) && (
            <span className="text-[#555] font-mono">
              [{msg.provider_used || "unknown"} :: {msg.model_used || "unknown"}]
            </span>
          )}
        </div>
        <div>
          {msg.content_tokens != null && msg.content_tokens > 0 && (
            <span>
              ~{msg.content_tokens} tok
              {msg.thinking_tokens != null && msg.thinking_tokens > 0 && (
                <span className="text-[#3a3a3a]"> + {msg.thinking_tokens} thk</span>
              )}
            </span>
          )}
        </div>
      </div>

      {isHuman && msg.metrics && <VitalityBar metrics={msg.metrics} />}

      {showThinkingButton && (
        <div className="mt-1">
          <button
            onClick={handleToggleThinking}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono"
          >
            <span>{thinkingOpen ? "▼" : "▶"}</span>
            <span>thinking</span>
          </button>
          {thinkingOpen && (
            <div className="mt-1 pl-3 border-l border-[#2a2a2a] text-xs text-[#666] leading-relaxed whitespace-pre-wrap font-mono bg-[#090909]/40 py-1 pr-2 rounded">
              {loadingThinking ? (
                <span className="animate-pulse">Loading thinking trace...</span>
              ) : (
                thinkingText
              )}
            </div>
          )}
        </div>
      )}

      {isHuman && msg.content && msg.content.length > 200 && (
        <div className="mt-1">
          <button
            onClick={() => setUserExpanded(!userExpanded)}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono"
          >
            <span>{userExpanded ? "▼" : "▶"}</span>
            <span>{userExpanded ? "collapse" : "expand"}</span>
          </button>
        </div>
      )}

      {showContextButton && (
        <div className="mt-1">
          <button
            onClick={handleToggleContext}
            className="text-[10px] text-[#555] hover:text-[#888] transition-colors flex items-center gap-1 font-mono"
          >
            <span>{contextOpen ? "▼" : "▶"}</span>
            <span>context</span>
          </button>
          {contextOpen && (
            <div className="mt-1 pl-3 border-l border-[#2a2a2a] text-xs text-[#666] leading-relaxed whitespace-pre-wrap font-mono bg-[#090909]/40 py-1 pr-2 rounded">
              {loadingContext ? (
                <span className="animate-pulse">Loading context...</span>
              ) : (
                contextText
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}, (prevProps, nextProps) => {
  return prevProps.msg.id === nextProps.msg.id &&
         prevProps.msg.speaker === nextProps.msg.speaker &&
         prevProps.msg.content === nextProps.msg.content &&
         prevProps.msg.thinking === nextProps.msg.thinking &&
         prevProps.msg.context_sent === nextProps.msg.context_sent &&
         prevProps.msg.metrics === nextProps.msg.metrics;
})
