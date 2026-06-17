// TaskCard — displays a research task with status-aware actions.
// Terminal aesthetic: no bg/border/rounded. Status shown via color and badge.

import React, { memo, useState } from "react"
import type { ResearchTask } from "../../../api/research"
import { runTask, rerunTask } from "../../../api/research"

interface Props {
  task: ResearchTask & { assets?: { id: string; url: string; relevance_score: number }[] }
  onApprove?: (id: string) => Promise<void>
  onReject?: (id: string) => Promise<void>
  onCancel?: (id: string) => Promise<void>
  onRefresh?: () => void
}

const STATUS_COLORS: Record<string, string> = {
  proposed: "#f59e0b",
  approved: "#3b82f6",
  queued: "#8b5cf6",
  active: "#4ade80",
  completed: "#22d3ee",
  failed: "#ef4444",
  cancelled: "#666666",
  rejected: "#f97316",
  expired: "#444444",
}

const TRIGGER_BADGES: Record<string, string> = {
  user_console: "console",
  user_inline: "conversation",
  symbia_proposal: "symbia · conversation",
  symbia_dream: "symbia · dream",
  symbia_conflict: "symbia · conflict",
  symbia_stagnation: "symbia · stagnation",
}

export const TaskCard = memo(function TaskCard({ task, onApprove, onReject, onCancel, onRefresh }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [acting, setActing] = useState(false)
  const color = STATUS_COLORS[task.status] || "#666"
  const badge = TRIGGER_BADGES[task.trigger_source] || task.trigger_source
  const progress = task.budget_limit_usd > 0
    ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100)
    : 0

  const doRun = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setActing(true)
    try { await runTask(task.id) } catch {} finally { setActing(false); onRefresh?.() }
  }
  const doRerun = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setActing(true)
    try { await rerunTask(task.id) } catch {} finally { setActing(false); onRefresh?.() }
  }

  return (
    <div className="text-xs font-mono">
      {/* Title row */}
      <div className="flex items-center gap-2 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <span className="text-[10px] shrink-0" style={{ color }}>●</span>
        <span className="text-[#bbb] flex-1 truncate">{task.title}</span>
        <span className="text-[10px] shrink-0" style={{ color }}>{task.status}</span>
        <span className="text-[#555] text-[9px] shrink-0">{badge}</span>
        {task.status === "active" && onCancel && (
          <button
            onClick={e => { e.stopPropagation(); onCancel(task.id) }}
            className="text-[#666] hover:text-[#ef4444] text-[9px]"
          >
            [cancel]
          </button>
        )}
        {task.status === "queued" && (
          <button onClick={doRun} disabled={acting}
            className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] disabled:text-[#333]"
          >
            [{acting ? "..." : "▶ run"}]
          </button>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="ml-3 mt-1 text-[10px] text-[#777] space-y-0.5">
          <div>objective: {task.objective}</div>
          <div>depth: {task.max_depth} · breadth: {task.max_breadth}{task.is_agonistic ? " · agonistic" : ""}</div>
          <div>branches: {task.branches_created} · assets: {task.assets_harvested} · flights: {task.lateral_flights}</div>
          <div>budget: ${task.budget_spent_usd.toFixed(4)} / ${task.budget_limit_usd.toFixed(2)} ({progress}%)</div>
          {task.proposal_rationale && (
            <div className="text-[#555]">rationale: {task.proposal_rationale}</div>
          )}
          {task.result_summary && (
            <div className="text-[#94a3b8] mt-1 max-h-32 overflow-y-auto">{task.result_summary}</div>
          )}

          {/* Scraped assets / results */}
          {task.assets && task.assets.length > 0 && (
            <div className="mt-1">
              <div className="text-[#555] text-[9px] uppercase mb-1">[harvested assets ({task.assets.length})]</div>
              <div className="space-y-0.5 max-h-40 overflow-y-auto">
                {task.assets.map(a => (
                  <div key={a.id} className="text-[#666] text-[9px]">
                    <span className="text-[#4ade80]">{a.relevance_score.toFixed(2)}</span>
                    {" "}{a.url.slice(0, 80)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Proposal actions */}
          {task.status === "proposed" && (
            <div className="flex gap-2 mt-1">
              {onApprove && (
                <button onClick={() => onApprove(task.id)} className="text-[#4ade80] hover:text-[#6ee7b0]">
                  [✓ approve & dispatch]
                </button>
              )}
              {onReject && (
                <button onClick={() => onReject(task.id)} className="text-[#ef4444] hover:text-[#f87171]">
                  [✗ dismiss]
                </button>
              )}
            </div>
          )}

          {/* Queued actions */}
          {task.status === "queued" && (
            <div className="flex gap-2 mt-1">
              <button onClick={doRun} disabled={acting}
                className="text-[#4ade80] hover:text-[#6ee7b0] text-[10px] disabled:text-[#333]"
              >[{acting ? "..." : "▶ run"}]</button>
              {onCancel && (
                <button onClick={() => onCancel(task.id)} className="text-[#ef4444] hover:text-[#f87171] text-[10px]">
                  [✕ cancel]
                </button>
              )}
            </div>
          )}

          {/* Terminal actions: rerun */}
          {(task.status === "completed" || task.status === "failed" || task.status === "cancelled") && (
            <div className="flex gap-2 mt-1">
              <button onClick={doRerun} disabled={acting}
                className="text-[#f59e0b] hover:text-[#fbbf24] text-[10px] disabled:text-[#333]"
              >[{acting ? "..." : "⟳ rerun"}]</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
})
