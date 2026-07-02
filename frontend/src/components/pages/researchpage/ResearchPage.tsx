// ResearchPage — Research task list with right-side basic detail.
// Pattern matches ConversationLandingPage: two-column, select to inspect.

import React, { memo, useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useResearch } from "../../../hooks/useResearch"
import type { ResearchTask } from "../../../api/research"
import { CSS_VARS } from "../../../config/colors"
import { CollapsibleSection } from "../agentpage/shared/CollapsibleSection"
import { TerminalButton, KeyValueGrid, HeaderContainer, HeaderIndicator, HeaderLogo, HeaderSeparator, HeaderLabel, HeaderActionButton, CreasesDropdown, UnifiedFooter } from "../../UI"

const STATUS_GROUPS: { key: string; label: string; icon: string; color: string; defaultOpen: boolean }[] = [
  { key: "proposed",  label: "Pending Proposals",   icon: "●", color: CSS_VARS.semanticGold,   defaultOpen: true },
  { key: "active",    label: "Active",               icon: "●", color: CSS_VARS.semanticGreen,  defaultOpen: true },
  { key: "queued",    label: "Queued",               icon: "●", color: CSS_VARS.semanticPurple, defaultOpen: true },
  { key: "completed", label: "Completed",             icon: "●", color: CSS_VARS.semanticSlate,  defaultOpen: true },
  { key: "failed",    label: "Failed",                icon: "●", color: CSS_VARS.semanticRed,    defaultOpen: true },
  { key: "cancelled", label: "Cancelled",             icon: "●", color: CSS_VARS.uiDim,          defaultOpen: false },
  { key: "rejected",  label: "Rejected",              icon: "●", color: CSS_VARS.semanticSand,   defaultOpen: false },
]

const STATUS_COLORS: Record<string, string> = Object.fromEntries(STATUS_GROUPS.map(g => [g.key, g.color]))

const TRIGGER_BADGES: Record<string, string> = {
  user_console: "console", user_inline: "chat",
  symbia_proposal: "symbia", symbia_dream: "dream",
  symbia_conflict: "conflict", symbia_stagnation: "stagnation",
}

/* ── Row item ── */
const TaskRow = memo(function TaskRow({ task, isSelected }: { task: ResearchTask; isSelected: boolean }) {
  const color = STATUS_COLORS[task.status] ?? CSS_VARS.uiDim
  const badge = TRIGGER_BADGES[task.trigger_source] || task.trigger_source
  const date = task.proposed_at?.slice(0, 16) || ""

  return (
    <div
      data-task-id={task.id}
      className={`flex items-center gap-2 px-1.5 py-1 cursor-pointer border-l-2 transition-colors ${
        isSelected ? "border-action-hover bg-action-hover/5" : "border-transparent hover:bg-[#111]"
      }`}
    >
      <span className="text-[9px] leading-none shrink-0" style={{ color }}>●</span>
      <span className="text-[#555] text-[9px] shrink-0 w-12 hidden md:inline">{date.slice(5) || "—"}</span>
      <span style={{ color }} className="text-[8px] uppercase shrink-0 w-14">{task.status}</span>
      <span className="font-mono text-[11px] truncate flex-1 min-w-0 text-[#bbb]">{task.title}</span>
      <span className="text-[9px] font-mono text-[#555] shrink-0 hidden md:inline">{badge}</span>
      {task.status === "active" && <span className="text-[#4ade80] text-[7px] shrink-0 animate-pulse">●</span>}
    </div>
  )
})

/* ── Right-side basic detail panel ── */
interface TaskPreviewProps {
  task: ResearchTask
  onEnter: () => void
  onApprove?: (id: string) => void
  onCancel?: (id: string) => void
}

function TaskPreview({ task, onEnter, onApprove, onCancel }: TaskPreviewProps) {
  const color = STATUS_COLORS[task.status] ?? CSS_VARS.uiDim
  const progress = task.budget_limit_usd > 0 ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100) : 0

  return (
    <div className="space-y-3">
      {/* Title + status + enter button */}
      <div className="flex items-center gap-2 pb-1 border-b border-[#1a1a1a]">
        <span style={{ color }} className="text-[10px]">●</span>
        <span className="text-[#bbb] text-xs font-bold flex-1 truncate">{task.title}</span>
        <span style={{ color }} className="text-[10px] uppercase">{task.status}</span>
        <TerminalButton onClick={onEnter} intent="save">enter</TerminalButton>
      </div>

      {/* Metrics */}
      <KeyValueGrid items={[
        { key: "objective", value: task.objective },
        { key: "trigger", value: task.trigger_source },
        { key: "depth / breadth", value: `${task.max_depth} / ${task.max_breadth}${task.is_agonistic ? " · agonistic" : ""}` },
        { key: "branches", value: task.branches_created },
        { key: "assets", value: task.assets_harvested || (task.assets?.length ?? 0) },
        { key: "flights", value: task.lateral_flights },
        { key: "budget", value: `$${task.budget_spent_usd.toFixed(4)} / $${task.budget_limit_usd.toFixed(2)} (${progress}%)` },
        ...(task.proposed_at ? [{ key: "proposed", value: task.proposed_at }] : []),
        ...(task.started_at ? [{ key: "started", value: task.started_at }] : []),
        ...(task.completed_at ? [{ key: "completed", value: task.completed_at }] : []),
      ]} />

      {/* Result summary preview */}
      {task.result_summary && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Result ]</div>
          <div className="text-[#888] text-[10px] leading-relaxed max-h-32 overflow-y-auto">
            {task.result_summary.slice(0, 400)}{task.result_summary.length > 400 ? "…" : ""}
          </div>
        </div>
      )}

      {/* Quick actions */}
      <div className="flex flex-wrap gap-2 pt-1 border-t border-[#1a1a1a]">
        {task.status === "proposed" && onApprove && (
          <TerminalButton onClick={() => onApprove(task.id)} intent="save">✓ approve</TerminalButton>
        )}
        {(task.status === "queued" || task.status === "active") && onCancel && (
          <TerminalButton onClick={() => onCancel(task.id)} intent="delete">✕ cancel</TerminalButton>
        )}
      </div>
    </div>
  )
}

export const ResearchPage = memo(function ResearchPage() {
  const navigate = useNavigate()
  const { tasks, summary, loading, error, approve, cancel } = useResearch()
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const handleListClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-task-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-task-id")
    if (id) setSelectedId(prev => prev === id ? null : id)
  }, [])

  // Double-click → enter detail page
  const handleDoubleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-task-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-task-id")
    if (id) navigate(`/research?id=${id}`)
  }, [navigate])

  const groups: Record<string, ResearchTask[]> = {}
  for (const g of STATUS_GROUPS) groups[g.key] = tasks.filter(t => t.status === g.key)
  const selected = selectedId ? tasks.find(t => t.id === selectedId) ?? null : null

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Header — single line */}
      <HeaderContainer>
        <span className="text-[11px] text-semantic-header tracking-widest uppercase select-none flex items-center gap-1.5">
          <HeaderIndicator intent="gold" />
          <HeaderLogo onClick={() => navigate('/nodes')} />
          <HeaderSeparator />
          <HeaderLabel intent="gold">research</HeaderLabel>
          <span className="text-[#555] text-[10px] ml-2 normal-case hidden sm:inline">
            {summary.active_count} active · {summary.queued_count} queued · {summary.pending_proposals} proposals
          </span>
        </span>
        <div className="flex items-center gap-4">
          {loading && <span className="text-[#555] text-[10px] animate-pulse">polling…</span>}
          <CreasesDropdown />
          <HeaderActionButton onClick={() => navigate('/agent')}>
            agent
          </HeaderActionButton>
          <HeaderActionButton onClick={() => navigate('/research?id=new')}>
            + new research
          </HeaderActionButton>
        </div>
      </HeaderContainer>

      {error && (
        <div className="text-semantic-red text-[10px] font-mono px-6 py-1 border-b border-[#1a1a1a]">[{error}]</div>
      )}

      {/* Two-column layout */}
      <div className="flex flex-col md:flex-row gap-3 flex-1 min-h-0 p-4 md:overflow-hidden">
        {/* Left: list */}
        <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[45vh]">
          {tasks.length === 0 && !loading ? (
            <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no tasks — create one above ]</div>
          ) : (
            <div
              onClick={handleListClick}
              onDoubleClick={handleDoubleClick}
              className="flex-1 space-y-2 overflow-y-auto pr-1 select-none"
            >
              {STATUS_GROUPS.map(g => {
                const items = groups[g.key]
                if (items.length === 0) return null
                return (
                  <CollapsibleSection key={g.key} label={g.label} count={items.length} icon={g.icon} iconColor={g.color} defaultOpen={g.defaultOpen}>
                    {items.map(t => <TaskRow key={t.id} task={t} isSelected={selectedId === t.id} />)}
                  </CollapsibleSection>
                )
              })}
            </div>
          )}
        </div>

        {/* Right: detail preview */}
        <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
          {selected ? (
            <TaskPreview
              task={selected}
              onEnter={() => navigate(`/research?id=${selected.id}`)}
              onApprove={approve}
              onCancel={cancel}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">
              [ select a task to preview, double-click or [enter] for full detail ]
            </div>
          )}
        </div>
      </div>
      <UnifiedFooter />
    </div>
  )
})
