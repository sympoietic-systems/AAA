// ResearchTaskPage — single research task detail with tabbed left list + right detail.
// Entry point: fetches task, delegates shell to TaskPageInner, handles new-task form.
// Refactored: tabs, steps, constants, and shared components extracted to subdirectories.

import React, { memo, useState, useEffect, useCallback } from "react"
import type { ResearchTask } from "../../../api/research"
import { getResearchTask, getTaskPhase } from "../../../api/research"
import { TerminalButton } from "../../UI"
import { STATUS_COLORS } from "./constants/taskConstants"
import { useTaskPolling } from "./shared/useTaskPolling"
import { InfoTab } from "./tabs/InfoTab"
import { StepsTab } from "./tabs/StepsTab"
import { MarkdownSection } from "./shared/MarkdownSection"
import { NewResearchForm } from "./NewResearchForm"

type SubTabId = "info" | "steps" | "summary"

const SUB_TABS: { key: SubTabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "summary",  label: "Summary" },
]

/* ── Shell — header, tab bar, content routing ── */
const TaskPageInner = memo(function TaskPageInner({ task }: { task: ResearchTask }) {
  const { current, orchPhase, refreshAll } = useTaskPolling(task.id, task.status, task)
  const [tab, setTab] = useState<SubTabId>(() => {
    if (task.status === "completed" && task.result_summary) return "summary"
    return "info"
  })

  const color = STATUS_COLORS[current.status] ?? "#666"

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Terminal breadcrumb header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <a href="/research" className="text-[#666] hover:text-[#bbb] text-[11px] transition-colors cursor-pointer">◀ back</a>
          <span className="text-[#333]">|</span>
          <span className="text-[11px] text-[#444] tracking-widest uppercase select-none shrink-0">
            <span className="text-[#eab308]">■</span>
            <span className="ml-2">symbia</span>
          </span>
          <span className="text-[#333]">//</span>
          <span className="text-[#bbb] text-xs truncate">{current.title}</span>
          <span style={{ color }} className="text-[10px] ml-1 uppercase shrink-0">{current.status}</span>
          {orchPhase && orchPhase !== "complete" && (
            <span className="text-[#f59e0b] text-[9px] ml-1 uppercase shrink-0">[{orchPhase}]</span>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <TerminalButton onClick={() => window.location.href = '/'}>home</TerminalButton>
          <TerminalButton onClick={() => window.open('/agent', '_blank')} intent="purple">agent</TerminalButton>
        </div>
      </div>

      {/* Tab bar — dot-separated */}
      <div className="flex flex-wrap gap-x-1 gap-y-1 px-4 py-2 text-[10px] select-none shrink-0">
        {SUB_TABS.map((t, i) => (
          <span key={t.key} className="flex items-center gap-x-1 whitespace-nowrap">
            {i > 0 && <span className="text-[#333]">•</span>}
            <button
              onClick={() => setTab(t.key)}
              className={`cursor-pointer transition-colors ${tab === t.key ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}
            >
              {t.label}
            </button>
          </span>
        ))}
      </div>

      {/* Content area */}
      <div className="flex-1 min-h-0 flex flex-col px-4 pb-4 pt-1">
        {tab === "info"     && <div className="flex-1 overflow-y-auto pr-1"><InfoTab task={current} orchPhase={orchPhase} onRefreshTask={refreshAll} /></div>}
        {tab === "steps"    && <StepsTab taskId={current.id} orchPhase={orchPhase} taskStatus={current.status} onRefreshTask={refreshAll} onSelectTab={setTab} />}
        {tab === "summary"  && (
          <div className="flex-1 overflow-y-auto pr-1">
            {current.result_summary ? (
              <MarkdownSection title=" Research Synthesis Report " content={current.result_summary} />
            ) : (
              <div className="text-[10px] text-[#444] py-2 font-mono italic">
                Synthesis in progress — the final report will be available here when completed.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
})

/* ── New Task Form Shell ── */
const NewTaskInline = memo(function NewTaskInline() {
  const handleDispatch = async (payload: any): Promise<string | null> => {
    const { dispatchResearch } = await import("../../../api/research")
    const result = await dispatchResearch(payload)
    if (result) window.location.href = `/research?id=${result.task_id}`
    return result?.task_id ?? null
  }

  const handleClose = () => { window.location.href = "/research" }

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      <div className="flex items-center px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <a href="/research" className="text-[#666] hover:text-[#bbb] text-[11px] transition-colors cursor-pointer">◀ back</a>
        <span className="text-[#333] mx-2">|</span>
        <span className="text-[#eab308] text-[11px]">■ new research</span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4 max-w-lg">
        <NewResearchForm onDispatch={handleDispatch} onClose={handleClose} />
      </div>
    </div>
  )
})

/* ── Exported Entry ── */
interface Props {
  taskId: string
  isNew?: boolean
}

export const ResearchTaskPage = memo(function ResearchTaskPage({ taskId, isNew }: Props) {
  if (isNew) return <NewTaskInline />

  const [task, setTask] = useState<ResearchTask | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getResearchTask(taskId).then(setTask).catch(e => setError(e.message))
  }, [taskId])

  if (error) return (
    <div className="flex flex-col h-screen bg-[#0c0c0c] items-center justify-center text-[#ef4444] text-xs font-mono">
      {error}
      <a href="/research" className="text-[#666] hover:text-[#bbb] mt-2">◀ back</a>
    </div>
  )
  if (!task) return <div className="flex flex-col h-screen bg-[#0c0c0c] items-center justify-center text-[#555] text-xs animate-pulse font-mono">[ loading… ]</div>

  return <TaskPageInner task={task} />
})
