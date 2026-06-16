// ResearchPage — Autonomous Research Console.
// Two-panel layout: left = grouped list, right = detail with tabs.
// Matches the /agent beliefs/skills layout pattern.

import React, { memo, useState, useCallback, useEffect, useRef } from "react"
import { useResearch } from "../../../hooks/useResearch"
import type { ResearchTask } from "../../../api/research"
import { retryTask } from "../../../api/research"
import { NewResearchForm } from "./NewResearchForm"
import { ResearchDetailPanel } from "./ResearchDetailPanel"
import { CollapsibleSection } from "../agentpage/shared/CollapsibleSection"

/* ── Status group definitions ── */
const STATUS_GROUPS: { key: string; label: string; icon: string; color: string; defaultOpen: boolean }[] = [
  { key: "proposed",  label: "Pending Proposals",   icon: "●", color: "#f59e0b", defaultOpen: true },
  { key: "active",    label: "Active",               icon: "●", color: "#4ade80", defaultOpen: true },
  { key: "queued",    label: "Queued",               icon: "●", color: "#8b5cf6", defaultOpen: true },
  { key: "completed", label: "Completed",             icon: "●", color: "#22d3ee", defaultOpen: false },
  { key: "failed",    label: "Failed",                icon: "●", color: "#ef4444", defaultOpen: false },
  { key: "cancelled", label: "Cancelled",             icon: "●", color: "#666666", defaultOpen: false },
  { key: "rejected",  label: "Rejected",              icon: "●", color: "#f97316", defaultOpen: false },
]

/* ── Compact list item ── */
const TaskListItem = memo(function TaskListItem({
  task, isSelected,
}: {
  task: ResearchTask
  isSelected: boolean
}) {
  const color = STATUS_GROUPS.find(g => g.key === task.status)?.color ?? "#666"
  const badge = ({
    user_console: "console",
    user_inline: "chat",
    symbia_proposal: "symbia",
    symbia_dream: "dream",
    symbia_conflict: "conflict",
    symbia_stagnation: "stagnation",
  } as Record<string, string>)[task.trigger_source] || task.trigger_source

  return (
    <div
      data-task-id={task.id}
      className={`
        flex items-center gap-1.5 px-1.5 py-1 cursor-pointer
        border-l-2 transition-colors
        ${isSelected ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}
      `}
    >
      <span className="text-[9px] leading-none shrink-0" style={{ color }}>●</span>
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">
        {task.title}
      </span>
      <span className="text-[9px] font-mono text-[#555] shrink-0 hidden md:inline">{badge}</span>
      {task.status === "active" && (
        <span className="text-[#4ade80] text-[7px] ml-0.5 shrink-0 animate-pulse">●</span>
      )}
    </div>
  )
})

export const ResearchPage = memo(function ResearchPage() {
  const { tasks, summary, loading, error, dispatch, approve, reject, cancel, refresh } = useResearch()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isAdding, setIsAdding] = useState(false)
  const refreshRef = useRef(refresh)
  refreshRef.current = refresh

  const handleListClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-task-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-task-id")
    if (id) {
      setIsAdding(false)
      setSelectedId(prev => prev === id ? null : id)
    }
  }, [])

  const handleAfterAction = useCallback(async (id: string, action: (id: string) => Promise<void>) => {
    await action(id)
    setSelectedId(null)
  }, [])

  // Listen for retry custom event from ActionsTab
  useEffect(() => {
    const handler = async (e: Event) => {
      const detail = (e as CustomEvent).detail as ResearchTask
      if (detail?.id) {
        try {
          await retryTask(detail.id)
          await refreshRef.current()
        } catch { /* silent */ }
      }
    }
    window.addEventListener("research-retry", handler)
    return () => window.removeEventListener("research-retry", handler)
  }, [])

  // Group tasks by status
  const groups: Record<string, ResearchTask[]> = {}
  for (const g of STATUS_GROUPS) {
    groups[g.key] = tasks.filter(t => t.status === g.key)
  }

  // Find selected task
  const selectedTask = selectedId ? tasks.find(t => t.id === selectedId) ?? null : null

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <span className="text-[11px] text-[#444] tracking-widest uppercase select-none">
          <span className="text-[#eab308]">■</span>
          <span className="ml-2">symbia</span>
          <span className="text-[#333] mx-2">//</span>
          <span>research</span>
          <span className="text-[#555] text-[10px] ml-3">
            {summary.active_count} active · {summary.queued_count} queued · {summary.pending_proposals} proposals
          </span>
        </span>
        <div className="flex items-center gap-4">
          {loading && <span className="text-[#555] text-[10px] animate-pulse">polling...</span>}
          <button
            onClick={() => window.location.href = '/'}
            className="text-[#666] hover:text-[#bbb] text-[11px] font-mono transition-colors cursor-pointer"
          >
            home
          </button>
          <button
            onClick={() => window.open('/agent', '_blank')}
            className="text-[#666] hover:text-[#a892ee] text-[11px] font-mono transition-colors cursor-pointer"
          >
            agent
          </button>
          <button
            onClick={() => { setSelectedId(null); setIsAdding(true) }}
            className="text-[#666] hover:text-[#4ade80] text-xs font-mono transition-colors"
          >
            [+ new research]
          </button>
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="text-[#ef4444] text-[10px] font-mono px-6 py-1 border-b border-[#1a1a1a]">
          [{error}]
        </div>
      )}

      {/* ── Two-Panel Layout ── */}
      <div className="flex flex-col md:flex-row gap-3 flex-1 min-h-0 p-4">
        {/* ── Left: Grouped task list ── */}
        <div className="md:w-[420px] shrink-0 w-full flex flex-col min-h-0">
          {tasks.length === 0 && !loading ? (
            <div className="text-[#444] italic text-xs text-center mt-8">
              [ no tasks — dispatch one above ]
            </div>
          ) : (
            <div
              onClick={handleListClick}
              className="flex-1 space-y-2 overflow-y-auto pr-1 select-none"
            >
              {STATUS_GROUPS.map(g => {
                const items = groups[g.key]
                if (items.length === 0) return null
                return (
                  <CollapsibleSection
                    key={g.key}
                    label={g.label}
                    count={items.length}
                    icon={g.icon}
                    iconColor={g.color}
                    defaultOpen={g.defaultOpen}
                  >
                    {items.map(t => (
                      <TaskListItem
                        key={t.id}
                        task={t}
                        isSelected={selectedId === t.id}
                      />
                    ))}
                  </CollapsibleSection>
                )
              })}
            </div>
          )}
        </div>

        {/* ── Right: Detail panel ── */}
        <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
          {isAdding ? (
            <NewResearchForm
              onDispatch={dispatch}
              onClose={() => setIsAdding(false)}
            />
          ) : selectedTask ? (
            <ResearchDetailPanel
              task={selectedTask}
              onApprove={(id) => handleAfterAction(id, approve)}
              onReject={(id) => handleAfterAction(id, reject)}
              onCancel={(id) => handleAfterAction(id, cancel)}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-[#333] text-xs italic select-none">
              [ select a task from the list, or [+ new research] ]
            </div>
          )}
        </div>
      </div>
    </div>
  )
})
