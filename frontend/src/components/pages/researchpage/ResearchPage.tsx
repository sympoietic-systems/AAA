// ResearchPage — Autonomous Research Console.
// Two-panel layout matching /agent beliefs/skills pattern (FRONTEND_DESIGN_PRINCIPLES.md §3).
// Self-supporting left panel, detail panel fetches own data (§2).

import React, { memo, useState, useCallback, useEffect, useRef } from "react"
import { useResearch } from "../../../hooks/useResearch"
import type { ResearchTask } from "../../../api/research"
import { retryTask, deleteTask } from "../../../api/research"
import { NewResearchForm } from "./NewResearchForm"
import { ResearchDetailPanel } from "./ResearchDetailPanel"
import { CollapsibleSection } from "../agentpage/shared/CollapsibleSection"
import { TerminalButton } from "../../UI"

/* ── Status group definitions (§5: Collapsible Sections) ── */
const STATUS_GROUPS: { key: string; label: string; icon: string; color: string; defaultOpen: boolean }[] = [
  { key: "proposed",  label: "Pending Proposals",   icon: "●", color: "#f59e0b", defaultOpen: true },
  { key: "active",    label: "Active",               icon: "●", color: "#4ade80", defaultOpen: true },
  { key: "queued",    label: "Queued",               icon: "●", color: "#8b5cf6", defaultOpen: true },
  { key: "completed", label: "Completed",             icon: "●", color: "#22d3ee", defaultOpen: false },
  { key: "failed",    label: "Failed",                icon: "●", color: "#ef4444", defaultOpen: false },
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

/* ── Compact list item (§4: Unified List Items) ── */
const TaskListItem = memo(function TaskListItem({
  task, isSelected,
}: {
  task: ResearchTask
  isSelected: boolean
}) {
  const color = STATUS_GROUPS.find(g => g.key === task.status)?.color ?? "#666"
  const badge = TRIGGER_BADGES[task.trigger_source] || task.trigger_source

  return (
    <div
      data-task-id={task.id}
      data-selected={isSelected ? "true" : undefined}
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
      <span className="text-[9px] font-mono text-[#666] shrink-0 hidden md:inline">{badge}</span>
      {task.status === "active" && (
        <span className="text-[#4ade80] text-[7px] ml-0.5 shrink-0 animate-pulse">●</span>
      )}
    </div>
  )
})

export const ResearchPage = memo(function ResearchPage() {
  const { tasks, summary, loading, error, dispatch, approve, reject, cancel, refresh } = useResearch()
  const detailRef = useRef<HTMLDivElement>(null)

  // ── URL state sync (§5 of FRONTEND_BEST_PRACTICES.md) ──
  const [selectedId, setSelectedIdState] = useState<string | null>(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get("id") || null
  })
  const [isAdding, setIsAdding] = useState(false)
  const refreshRef = useRef(refresh)
  refreshRef.current = refresh

  const setSelectedId = useCallback((id: string | null) => {
    setSelectedIdState(id)
    const params = new URLSearchParams(window.location.search)
    if (id) {
      params.set("id", id)
    } else {
      params.delete("id")
    }
    const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`
    window.history.replaceState(null, "", newUrl)
  }, [])

  // ── Mobile: scroll detail into view when selected (§10) ──
  useEffect(() => {
    if ((!selectedId && !isAdding) || !detailRef.current) return
    if (window.matchMedia("(max-width: 767px)").matches) {
      detailRef.current.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }, [selectedId, isAdding])

  // ── Event delegation for list clicks (§4) ──
  const handleListClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-task-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-task-id")
    if (id) {
      setIsAdding(false)
      setSelectedId(prevId => prevId === id ? null : id)
    }
  }, [setSelectedId])

  // ── Action handlers ──
  const handleAfterAction = useCallback(async (id: string, action: (id: string) => Promise<void>) => {
    await action(id)
    setSelectedId(null)
  }, [setSelectedId])

  // Retry via CustomEvent from ActionsTab
  useEffect(() => {
    const handler = async (e: Event) => {
      const detail = (e as CustomEvent).detail as ResearchTask
      if (detail?.id) {
        try { await retryTask(detail.id); await refreshRef.current() } catch { /* silent */ }
      }
    }
    window.addEventListener("research-retry", handler)
    return () => window.removeEventListener("research-retry", handler)
  }, [])

  // Continue (deeper) via CustomEvent from ActionsTab
  useEffect(() => {
    const handler = async (e: Event) => {
      const detail = (e as CustomEvent).detail as ResearchTask
      if (detail?.objective) {
        try {
          await dispatch({
            objective: detail.objective,
            title: detail.title,
            max_depth: (detail.max_depth || 2) + 1,
            max_breadth: detail.max_breadth || 2,
            is_agonistic: !!detail.is_agonistic,
            budget_limit_usd: detail.budget_limit_usd || 0.50,
          })
        } catch { /* silent */ }
      }
    }
    window.addEventListener("research-continue", handler)
    return () => window.removeEventListener("research-continue", handler)
  }, [dispatch])

  // Delete via CustomEvent from ActionsTab
  useEffect(() => {
    const handler = async (e: Event) => {
      const detail = (e as CustomEvent).detail as ResearchTask
      if (detail?.id) {
        try { await deleteTask(detail.id); await refreshRef.current(); setSelectedId(null) } catch { /* silent */ }
      }
    }
    window.addEventListener("research-delete", handler)
    return () => window.removeEventListener("research-delete", handler)
  }, [])

  // ── Group tasks by status ──
  const groups: Record<string, ResearchTask[]> = {}
  for (const g of STATUS_GROUPS) {
    groups[g.key] = tasks.filter(t => t.status === g.key)
  }

  const selectedTask = selectedId ? tasks.find(t => t.id === selectedId) ?? null : null

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* ── Header (§1: Terminal Aesthetics) ── */}
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
          <TerminalButton onClick={() => window.location.href = '/'}>
            home
          </TerminalButton>
          <TerminalButton onClick={() => window.open('/agent', '_blank')} intent="purple">
            agent
          </TerminalButton>
          <TerminalButton onClick={() => { setSelectedId(null); setIsAdding(true) }} intent="save">
            + new research
          </TerminalButton>
        </div>
      </div>

      {/* ── Error (§1) ── */}
      {error && (
        <div className="text-[#ef4444] text-[10px] font-mono px-6 py-1 border-b border-[#1a1a1a]">
          [{error}]
        </div>
      )}

      {/* ── Two-Panel Layout (§3) ── */}
      <div className="flex flex-col md:flex-row gap-3 flex-1 min-h-0 p-4 md:overflow-hidden">
        {/* ── Left: Grouped task list (§3: md:w-[450px]) ── */}
        <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[45vh]">
          {tasks.length === 0 && !loading ? (
            <div className="text-[#444] italic text-xs text-center mt-8 select-none">
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

        {/* ── Right: Detail panel (§3, §6) ── */}
        <div ref={detailRef} className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
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
            <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">
              [ select a task from the list, or [+ new research] ]
            </div>
          )}
        </div>
      </div>
    </div>
  )
})
