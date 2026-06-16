// ResearchPage — Research task list (landing page pattern).
// Click a task → navigates to /research?id=xxx for detail view.

import React, { memo, useCallback } from "react"
import { useResearch } from "../../../hooks/useResearch"
import type { ResearchTask } from "../../../api/research"
import { CollapsibleSection } from "../agentpage/shared/CollapsibleSection"
import { TerminalButton } from "../../UI"

/* ── Status group definitions ── */
const STATUS_GROUPS: { key: string; label: string; icon: string; color: string; defaultOpen: boolean }[] = [
  { key: "proposed",  label: "Pending Proposals",   icon: "●", color: "#f59e0b", defaultOpen: true },
  { key: "active",    label: "Active",               icon: "●", color: "#4ade80", defaultOpen: true },
  { key: "queued",    label: "Queued",               icon: "●", color: "#8b5cf6", defaultOpen: true },
  { key: "completed", label: "Completed",             icon: "●", color: "#22d3ee", defaultOpen: true },
  { key: "failed",    label: "Failed",                icon: "●", color: "#ef4444", defaultOpen: true },
  { key: "cancelled", label: "Cancelled",             icon: "●", color: "#666666", defaultOpen: false },
  { key: "rejected",  label: "Rejected",              icon: "●", color: "#f97316", defaultOpen: false },
]

const TRIGGER_BADGES: Record<string, string> = {
  user_console: "console",
  user_inline: "chat",
  symbia_proposal: "symbia",
  symbia_dream: "dream",
  symbia_conflict: "conflict",
  symbia_stagnation: "stagnation",
}

/* ── Row item ── */
const TaskRow = memo(function TaskRow({ task }: { task: ResearchTask }) {
  const color = STATUS_GROUPS.find(g => g.key === task.status)?.color ?? "#666"
  const badge = TRIGGER_BADGES[task.trigger_source] || task.trigger_source
  const date = task.proposed_at?.slice(0, 16) || ""

  return (
    <div
      data-task-id={task.id}
      className="flex items-center gap-2 px-1.5 py-1 cursor-pointer border-l-2 border-transparent hover:bg-[#111] transition-colors"
    >
      <span className="text-[9px] leading-none shrink-0" style={{ color }}>●</span>
      <span className="text-[#555] text-[9px] shrink-0 w-12">{date.slice(5) || "—"}</span>
      <span style={{ color }} className="text-[8px] uppercase shrink-0 w-12">{task.status}</span>
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">{task.title}</span>
      <span className="text-[9px] font-mono text-[#555] shrink-0 hidden md:inline">
        {badge} · b:{task.branches_created} · a:{task.assets_harvested || (task.assets?.length ?? 0)}
      </span>
      {task.status === "active" && (
        <span className="text-[#4ade80] text-[7px] shrink-0 animate-pulse">●</span>
      )}
    </div>
  )
})

export const ResearchPage = memo(function ResearchPage() {
  const { tasks, summary, loading, error } = useResearch()

  const handleListClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-task-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-task-id")
    if (id) {
      window.location.href = `/research?id=${id}`
    }
  }, [])

  const groups: Record<string, ResearchTask[]> = {}
  for (const g of STATUS_GROUPS) {
    groups[g.key] = tasks.filter(t => t.status === g.key)
  }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <span className="text-[11px] text-[#444] tracking-widest uppercase select-none">
          <span className="text-[#eab308]">■</span>
          <span className="ml-2">symbia</span>
          <span className="text-[#333] mx-2">//</span>
          <span>research</span>
          <span className="text-[#555] text-[10px] ml-3 normal-case">
            {summary.active_count} active · {summary.queued_count} queued · {summary.pending_proposals} proposals
          </span>
        </span>
        <div className="flex items-center gap-3">
          {loading && <span className="text-[#555] text-[10px] animate-pulse">polling...</span>}
          <TerminalButton onClick={() => window.location.href = '/'}>home</TerminalButton>
          <TerminalButton onClick={() => window.open('/agent', '_blank')} intent="purple">agent</TerminalButton>
          <TerminalButton onClick={() => window.location.href = '/research?id=new'} intent="save">+ new research</TerminalButton>
        </div>
      </div>

      {error && (
        <div className="text-[#ef4444] text-[10px] font-mono px-6 py-1 border-b border-[#1a1a1a]">[{error}]</div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {tasks.length === 0 && !loading ? (
          <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no tasks — create one above ]</div>
        ) : (
          <div onClick={handleListClick} className="space-y-2 select-none">
            {STATUS_GROUPS.map(g => {
              const items = groups[g.key]
              if (items.length === 0) return null
              return (
                <CollapsibleSection key={g.key} label={g.label} count={items.length} icon={g.icon} iconColor={g.color} defaultOpen={g.defaultOpen}>
                  {items.map(t => <TaskRow key={t.id} task={t} />)}
                </CollapsibleSection>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
})
