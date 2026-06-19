import { useState, useEffect, memo, useMemo } from "react"
import { getDaemonStatus, getRecentDreams } from "../../../api/client"
import type { DaemonStatusResponse, DreamEntry } from "../../../api/client"
import { formatRelativeTime } from "../../../utils/dateFormat"
import telemetrySchemas from "../../../config/telemetry_schemas.json"

const { DREAM_TYPE_LABELS } = telemetrySchemas as { DREAM_TYPE_LABELS: Record<string, { code: string; label: string; color: string }> }

// §3: Stable references — avoid inline object creation each render
const EMPTY_COUNTS: Record<string, number> = {}
const UNKNOWN_TYPE = { code: "???", label: "", color: "#888" } as const
const EMPTY_ARRAY: DreamEntry[] = []

export const DreamingSection = memo(function DreamingSection() {
  const [status, setStatus] = useState<DaemonStatusResponse | null>(null)
  const [dreams, setDreams] = useState<DreamEntry[]>(EMPTY_ARRAY)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getDaemonStatus().then(setStatus).catch(e => setError(e.message || "Failed"))
    getRecentDreams(24).then(d => setDreams(d.dreams)).catch(() => {})
    const id = setInterval(() => {
      getDaemonStatus().then(setStatus).catch(() => {
        // If daemon goes down, keep last known state (no spam)
      })
      getRecentDreams(24).then(d => setDreams(d.dreams)).catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  // §3: useMemo — always called (before early returns) to keep stable hook count
  const derived = useMemo(() => {
    if (!status) return null
    let label = "dormant"; let color = "#555"
    if (status.enabled && status.running) {
      const tsd = status.last_dream_time ? (Date.now() - new Date(status.last_dream_time).getTime()) / 1000 : Infinity
      label = tsd < status.check_interval * 2 ? "dreaming" : "resting"
      color = label === "dreaming" ? "#a78bfa" : "#6c6c8a"
    } else if (status.enabled && !status.running) { label = "resting"; color = "#6c6c8a" }

    const action = status.last_dream_action
      ? DREAM_TYPE_LABELS[status.last_dream_action] || { ...UNKNOWN_TYPE, label: status.last_dream_action }
      : null

    const counts = Object.entries(status.dream_action_counts || EMPTY_COUNTS)
      .map(([key, count]) => ({
        key, count,
        ...(DREAM_TYPE_LABELS[key] || { ...UNKNOWN_TYPE, label: key }),
      }))
      .sort((a, b) => b.count - a.count)

    const idle = status.idle_threshold_seconds > 0
      ? Math.min(100, (status.idle_time_seconds / status.idle_threshold_seconds) * 100)
      : 0
    const budget = status.max_daily_dreams > 0
      ? Math.min(100, (status.dreams_today / status.max_daily_dreams) * 100)
      : 0
    const hasSW = (status.short_window_hours ?? 0) > 0 && (status.short_window_max ?? 0) > 0
    const swPct = hasSW
      ? Math.min(100, ((status.short_window_count ?? 0) / status.short_window_max!) * 100)
      : 0

    return { stateLabel: label, stateColor: color, lastAction: action, typeCounts: counts, idlePct: idle, budgetPct: budget, hasShortWindow: hasSW, shortWindowPct: swPct }
  }, [status])

  if (error && !status) return <div className="text-[#ef4444] font-mono">{error}</div>
  if (!status || !derived) return <div className="text-[#444] font-mono">waiting for data...</div>

  const { stateLabel, stateColor, lastAction, typeCounts, idlePct, budgetPct, hasShortWindow, shortWindowPct } = derived

  return (
    <div className="px-4 py-2">
      <div className="flex items-center gap-1.5 mb-3 font-mono">
        <span className={`text-[9px] leading-none ${stateLabel === "dreaming" ? "animate-pulse" : ""}`} style={{ color: stateColor }}>
          {stateLabel === "dreaming" ? "◉" : stateLabel === "resting" ? "●" : "○"}
        </span>
        <span className="text-[11px]" style={{ color: stateColor }}>{stateLabel}</span>
        <span className="text-[10px] ml-auto text-[#888]">{status.dreams_today} / {status.max_daily_dreams}</span>
      </div>

      {/* Self-triggered dream queue indicator */}
      {(status.pending_self_triggers ?? 0) > 0 && (
        <div className="font-mono text-[10px] mb-2 flex items-center gap-1" style={{ color: "#c084fc" }}>
          <span>⟳</span>
          <span>{status.pending_self_triggers} self-triggered dream{status.pending_self_triggers > 1 ? "s" : ""} queued</span>
        </div>
      )}

      <div className="font-mono text-[10px] space-y-1.5">
        <div className="flex gap-1 flex-wrap">
          <span className="text-[#666]">LAST</span>
          {status.last_dream_time ? <span className="text-[#aaa]">{formatRelativeTime(status.last_dream_time)}</span> : <span className="text-[#444]">no dreams yet</span>}
        </div>
        {lastAction && (
          <div className="flex gap-1 flex-wrap">
            <span className="text-[#666]">TYPE</span>
            <span style={{ color: lastAction.color }}>{lastAction.code}</span>
            <span className="text-[#888]">{lastAction.label}</span>
          </div>
        )}
        <div className="flex gap-1 items-center">
          <span className="text-[#666]">IDLE</span>
          <span className="text-[#888]">{status.idle_time_seconds >= 60 ? `${Math.floor(status.idle_time_seconds / 60)}m ${Math.round(status.idle_time_seconds % 60)}s` : `${Math.round(status.idle_time_seconds)}s`}</span>
          <span className="text-[#444]">/</span>
          <span className="text-[#555]">{status.idle_threshold_seconds}s</span>
          <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
            <div className="h-full rounded-sm transition-all duration-500" style={{ width: `${idlePct}%`, backgroundColor: idlePct > 90 ? "#a78bfa" : "#333" }} />
          </div>
        </div>
        <div className="flex gap-1 items-center">
          <span className="text-[#666]">BUDGET</span>
          <span className="text-[#888]">{status.dreams_today}</span>
          <span className="text-[#444]">/</span>
          <span className="text-[#555]">{status.max_daily_dreams}</span>
          <span className="text-[#444]">· 24h</span>
          <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
            <div className="h-full rounded-sm transition-all duration-500" style={{ width: `${budgetPct}%`, backgroundColor: budgetPct > 80 ? "#ef4444" : budgetPct > 50 ? "#facc15" : "#4ade80", opacity: 0.7 }} />
          </div>
        </div>
        {/* Short window burst-prevention bar (only when configured) */}
        {hasShortWindow && (
          <div className="flex gap-1 items-center">
            <span className="text-[#666]">BURST</span>
            <span className="text-[#888]">{status.short_window_count ?? 0}</span>
            <span className="text-[#444]">/</span>
            <span className="text-[#555]">{status.short_window_max}</span>
            <span className="text-[#444]">· {status.short_window_hours}h</span>
            <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
              <div className="h-full rounded-sm transition-all duration-500" style={{ width: `${shortWindowPct}%`, backgroundColor: shortWindowPct >= 100 ? "#ef4444" : shortWindowPct > 50 ? "#facc15" : "#f472b6", opacity: 0.7 }} />
            </div>
          </div>
        )}
        {typeCounts.length > 0 && (
          <>
            <div className="text-[#555] mt-2 font-bold">=== DREAM TYPES ===</div>
            {typeCounts.map(t => (
              <div key={t.key} className="flex gap-1 items-center">
                <span style={{ color: t.color }}>{t.code}</span>
                <span className="text-[#888] truncate flex-1">{t.label}</span>
                <span className="text-[#aaa] font-bold ml-auto">×{t.count}</span>
              </div>
            ))}
          </>
        )}
      </div>

      {/* Dream History — last 24 entries */}
      {dreams.length > 0 && (
        <div className="mt-4 font-mono text-[10px]">
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1.5">
            [ Recent Dreams ({dreams.length}) ]
          </div>
          <div className="flex flex-col gap-0.5 max-h-80 overflow-y-auto">
            {dreams.map((d) => {
              const isSelfTriggered = d.action === "self_triggered"
              const typeDef = DREAM_TYPE_LABELS[d.action]
              return (
                <div key={d.id} className="py-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[#555] text-[9px] shrink-0">{formatRelativeTime(d.timestamp)}</span>
                    <span className="text-[9px] shrink-0" style={{ color: typeDef?.color || "#555" }}>
                      {typeDef?.code || d.action}
                    </span>
                    <a
                      href={`/?c=${d.conversation_id}${d.response_msg_id ? `&m=${d.response_msg_id}` : ""}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#94a3b8] hover:text-[#a78bfa] truncate flex-1 min-w-0 transition-colors"
                      title={d.last_snippet || d.title}
                    >
                      {d.title}
                    </a>
                    <span className="text-[#555] text-[9px] shrink-0">{d.turns}t · {d.msg_count}m</span>
                  </div>
                  {/* Self-triggered metadata: reason + source conversation link */}
                  {isSelfTriggered && (d.trigger_reason || d.source_conversation_id) && (
                    <div className="flex items-center gap-2 ml-0 mt-0.5">
                      {d.trigger_reason && (
                        <span className="text-[#6b4b8a] text-[8px] truncate flex-1 min-w-0 italic" title={d.trigger_reason}>
                          ← {d.trigger_reason}
                        </span>
                      )}
                      {d.source_conversation_id && (
                        <a
                          href={`/?c=${d.source_conversation_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#8b6cba] hover:text-[#c084fc] text-[8px] shrink-0 transition-colors"
                          title="Jump to source conversation"
                        >
                          [→ src]
                        </a>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
})
