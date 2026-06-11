import { useState, useEffect, memo } from "react"
import { getDaemonStatus } from "../../../api/client"
import type { DaemonStatusResponse } from "../../../api/client"
import telemetrySchemas from "../../../config/telemetry_schemas.json"

const { DREAM_TYPE_LABELS } = telemetrySchemas as {
  DREAM_TYPE_LABELS: Record<string, { code: string; label: string; color: string }>
}

function formatRelativeTime(isoString: string): string {
  const now = Date.now()
  const then = new Date(isoString).getTime()
  const diffMs = now - then
  if (diffMs < 0) return "just now"
  const seconds = Math.floor(diffMs / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function DreamingSectionComponent() {
  const [status, setStatus] = useState<DaemonStatusResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getDaemonStatus()
      .then(setStatus)
      .catch(e => setError(e.message || "Failed"))
    const id = setInterval(() => {
      getDaemonStatus()
        .then(setStatus)
        .catch(() => {})
    }, 10000)
    return () => clearInterval(id)
  }, [])

  if (error && !status) {
    return <p className="text-[10px] text-[#ef4444] font-mono">{error}</p>
  }

  if (!status) {
    return <p className="text-[10px] text-[#444] font-mono">waiting for data...</p>
  }

  // Determine display state
  let stateLabel = "dormant"
  let stateColor = "#555"
  if (status.enabled && status.running) {
    const timeSinceLastDream = status.last_dream_time
      ? (Date.now() - new Date(status.last_dream_time).getTime()) / 1000
      : Infinity
    if (timeSinceLastDream < status.check_interval * 2) {
      stateLabel = "dreaming"
      stateColor = "#a78bfa"
    } else {
      stateLabel = "resting"
      stateColor = "#6c6c8a"
    }
  } else if (status.enabled && !status.running) {
    stateLabel = "resting"
    stateColor = "#6c6c8a"
  }

  const lastAction = status.last_dream_action
    ? DREAM_TYPE_LABELS[status.last_dream_action] || { code: "???", label: status.last_dream_action, color: "#888" }
    : null

  // Sort dream types by count descending
  const typeCounts = Object.entries(status.dream_action_counts || {})
    .map(([key, count]) => ({
      key,
      count,
      ...(DREAM_TYPE_LABELS[key] || { code: "???", label: key, color: "#888" }),
    }))
    .sort((a, b) => b.count - a.count)

  // Idle progress (how close to next potential trigger)
  const idlePct = status.idle_threshold_seconds > 0
    ? Math.min(100, (status.idle_time_seconds / status.idle_threshold_seconds) * 100)
    : 0

  // Budget usage
  const budgetPct = status.max_daily_dreams > 0
    ? Math.min(100, (status.dreams_today / status.max_daily_dreams) * 100)
    : 0

  return (
    <div className="mt-2 border-t border-[#1a1a1a] pt-2">
      <div className="flex items-center gap-1.5 mb-2 font-mono">
        <span
          className={`text-[9px] leading-none ${stateLabel === "dreaming" ? "animate-pulse" : ""}`}
          style={{ color: stateColor }}
        >
          {stateLabel === "dreaming" ? "◉" : stateLabel === "resting" ? "●" : "○"}
        </span>
        <span className="text-[11px]" style={{ color: stateColor }}>
          {stateLabel}
        </span>
        <span className="text-[10px] ml-auto text-[#888]">
          {status.dreams_today} / {status.max_daily_dreams}
        </span>
      </div>

      <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded p-2 font-mono text-[9px] leading-relaxed space-y-px">
        <div className="text-[#555]">
          {"=== AUTOPOIETIC PULSE ==="}
        </div>

        {/* Last dream */}
        <div className="flex gap-1 flex-wrap">
          <span className="text-[#666]">LAST</span>
          {status.last_dream_time ? (
            <span className="text-[#aaa]">{formatRelativeTime(status.last_dream_time)}</span>
          ) : (
            <span className="text-[#444]">no dreams yet</span>
          )}
        </div>

        {/* Last dream type */}
        {lastAction && (
          <div className="flex gap-1 flex-wrap">
            <span className="text-[#666]">TYPE</span>
            <span style={{ color: lastAction.color }}>{lastAction.code}</span>
            <span className="text-[#888]">{lastAction.label}</span>
          </div>
        )}

        {/* Idle timer */}
        <div className="flex gap-1 items-center">
          <span className="text-[#666]">IDLE</span>
          <span className="text-[#888]">
            {status.idle_time_seconds >= 60
              ? `${Math.floor(status.idle_time_seconds / 60)}m ${Math.round(status.idle_time_seconds % 60)}s`
              : `${Math.round(status.idle_time_seconds)}s`
            }
          </span>
          <span className="text-[#444]">/</span>
          <span className="text-[#555]">{status.idle_threshold_seconds}s</span>
          <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all duration-500"
              style={{
                width: `${idlePct}%`,
                backgroundColor: idlePct > 90 ? "#a78bfa" : "#333",
              }}
            />
          </div>
        </div>

        {/* Budget bar */}
        <div className="flex gap-1 items-center">
          <span className="text-[#666]">BUDGET</span>
          <span className="text-[#888]">{status.dreams_today}</span>
          <span className="text-[#444]">/</span>
          <span className="text-[#555]">{status.max_daily_dreams}</span>
          <div className="ml-auto w-10 h-1 bg-[#1a1a1a] rounded-sm overflow-hidden">
            <div
              className="h-full rounded-sm transition-all duration-500"
              style={{
                width: `${budgetPct}%`,
                backgroundColor: budgetPct > 80 ? "#ef4444" : budgetPct > 50 ? "#facc15" : "#4ade80",
                opacity: 0.7,
              }}
            />
          </div>
        </div>

        {/* Dream type breakdown */}
        {typeCounts.length > 0 && (
          <>
            <div className="text-[#555] mt-1">
              {"=== DREAM TYPES ==="}
            </div>
            {typeCounts.map((t) => (
              <div key={t.key} className="flex gap-1 items-center">
                <span style={{ color: t.color }}>{t.code}</span>
                <span className="text-[#888] truncate flex-1">{t.label}</span>
                <span className="text-[#aaa] font-bold ml-auto">×{t.count}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}

export const DreamingSection = memo(DreamingSectionComponent)
