// ResearchTaskPage — single research task detail with tabbed left list + right detail.
// Pattern: /agent page — tab bar, then two-panel (left list, right detail).
// Actions merged into Info tab (FRONTEND_DESIGN_PRINCIPLES.md §1, §3, §4, §6).

import React, { memo, useState, useEffect, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import type {
  ResearchTask, TaskStepsResponse,
  MetaLogResponse,
} from "../../../api/research"
import {
  getResearchTask, getTaskSteps, getTaskMetaLog,
  approveProposal, rejectProposal, cancelTask, retryTask, deleteTask,
} from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"

type SubTabId = "info" | "steps" | "assets" | "branches" | "meta_log"

const SUB_TABS: { key: SubTabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "assets",   label: "Assets" },
  { key: "branches", label: "Branches" },
  { key: "meta_log", label: "Meta Log" },
]

const STATUS_COLORS: Record<string, string> = {
  proposed: "#f59e0b", approved: "#3b82f6", queued: "#8b5cf6",
  active: "#4ade80", completed: "#22d3ee", failed: "#ef4444",
  cancelled: "#666666", rejected: "#f97316", expired: "#444444",
}

interface Props {
  taskId: string
  isNew?: boolean
}

/* ── Shared action helpers ── */
async function doActionAndReload(action: () => Promise<any>) {
  await action()
  window.location.reload()
}

/* ── Info Tab (with inline actions) ── */
function InfoTab({ task }: { task: ResearchTask }) {
  const color = STATUS_COLORS[task.status] ?? "#666"
  const progress = task.budget_limit_usd > 0 ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100) : 0
  const metrics = [
    { key: "id", value: task.id.slice(0, 12) + "…" },
    { key: "status", value: task.status, valueColor: color },
    { key: "trigger", value: task.trigger_source },
    { key: "depth", value: task.max_depth },
    { key: "breadth", value: task.max_breadth },
    { key: "agonistic", value: task.is_agonistic ? "yes" : "no", valueColor: task.is_agonistic ? "#f59e0b" : undefined },
    { key: "branches", value: task.branches_created },
    { key: "assets", value: task.assets_harvested || (task.assets?.length ?? 0) },
    { key: "budget", value: `$${task.budget_spent_usd.toFixed(4)} / $${task.budget_limit_usd.toFixed(2)} (${progress}%)` },
    ...(task.proposed_at ? [{ key: "proposed", value: task.proposed_at }] : []),
    ...(task.started_at ? [{ key: "started", value: task.started_at }] : []),
    ...(task.completed_at ? [{ key: "completed", value: task.completed_at }] : []),
  ]

  const navigateHome = () => { window.location.href = "/research" }

  const doContinue = async () => {
    const { dispatchResearch } = await import("../../../api/research")
    await dispatchResearch({
      objective: task.objective, title: task.title,
      max_depth: (task.max_depth || 2) + 1, max_breadth: task.max_breadth || 2,
      is_agonistic: !!task.is_agonistic, budget_limit_usd: task.budget_limit_usd || 0.50,
    })
    navigateHome()
  }

  return (
    <div className="space-y-3">
      {/* Objective */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Objective ]</div>
        <div className="text-[#94a3b8] text-[10px] leading-relaxed">{task.objective}</div>
      </div>

      {/* Metrics §6: inline KeyValueGrid */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Metrics ]</div>
        <KeyValueGrid items={metrics} />
      </div>

      {/* Actions — inline, no separate tab */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Actions ]</div>
        <div className="flex flex-wrap gap-2">
          {task.status === "proposed" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => approveProposal(task.id))} intent="save">✓ approve</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => rejectProposal(task.id))} intent="delete">✗ dismiss</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {(task.status === "queued" || task.status === "active") && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => cancelTask(task.id))} intent="delete">✕ cancel</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "failed" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => retryTask(task.id))} intent="edit">↻ retry</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "completed" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => retryTask(task.id))} intent="save">↻ retry</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "cancelled" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => retryTask(task.id))} intent="edit">↻ retry</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "rejected" && (
            <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
          )}
        </div>
      </div>

      {/* Result Summary — markdown rendered */}
      {task.result_summary && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Result Summary ]</div>
          <div className="text-[#94a3b8] text-[10px] leading-relaxed max-h-96 overflow-y-auto prose prose-invert prose-xs max-w-none">
            <ReactMarkdown>{task.result_summary}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Steps Tab (§3: left list + right detail) ── */
const STEP_COLORS: Record<string, string> = {
  search: "#3b82f6", parallel_parse: "#f59e0b", digest: "#a892ee",
  reflect: "#c084fc", synthesize: "#4ade80", evaluate: "#22d3ee",
}

function StepsTab({ taskId }: { taskId: string }) {
  const [data, setData] = useState<TaskStepsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => { getTaskSteps(taskId).then(setData).finally(() => setLoading(false)) }, [taskId])

  if (loading) return <div className="text-[#555] animate-pulse text-xs font-mono">[ loading… ]</div>
  if (!data || data.steps.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no steps — legacy engine ]</div>

  const steps = [...data.steps].reverse()
  const selected = selectedId ? steps.find(s => s.id === selectedId) : null
  const selectedResults = selectedId ? (data.results_by_step[selectedId] || []) : []

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-sid]") as HTMLElement | null
    if (!el) return
    setSelectedId(prev => prev === el.getAttribute("data-sid") ? null : el.getAttribute("data-sid"))
  }

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-200px)]">
      {/* Left list §4 */}
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[40vh]" onClick={handleClick}>
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none">
          {steps.map(s => {
            const sc = STEP_COLORS[s.step_type] || "#666"
            return (
              <div key={s.id} data-sid={s.id}
                className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px]
                  ${selectedId === s.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}`}
              >
                <span style={{ color: sc }} className="text-[8px] shrink-0">●</span>
                <span className="text-[#bbb] font-mono">#{s.step_number} {s.step_type}</span>
                <span style={{ color: sc }} className="text-[8px] ml-auto uppercase">{s.status}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Right detail §3 */}
      <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
        {selected ? (
          <div className="space-y-2 text-[10px]">
            <div className="flex items-center gap-2 text-[#6c6c8a] uppercase text-[9px] tracking-wider">
              [ Step #{selected.step_number}: {selected.step_type} ]
            </div>
            {selected.result_summary && <div className="text-[#94a3b8]">{selected.result_summary}</div>}
            {selectedResults.map(r => {
              let analysis: any = null
              try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
              return (
                <div key={r.id} className="py-1">
                  <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                    className="text-[#4ade80] hover:text-[#6ee7b0] underline text-[10px] break-all"
                  >{r.source_title || r.source_url?.slice(0, 80) || "—"}</a>
                  {analysis?.learnings && (
                    <div className="text-[#888] text-[9px] mt-0.5 space-y-0.5">
                      {(analysis.learnings as string[]).map((l, li) => <div key={li} className="pl-2">· {l}</div>)}
                    </div>
                  )}
                  {r.raw_file_path && <div className="text-[#555] text-[8px] mt-0.5">saved: {r.raw_file_path}</div>}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">[ select a step ]</div>
        )}
      </div>
    </div>
  )
}

/* ── Assets Tab (§3, §4) ── */
function AssetsTab({ task }: { task: ResearchTask }) {
  const assets = task.assets ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)

  if (assets.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no assets harvested ]</div>

  const selected = selectedId ? assets.find(a => a.id === selectedId) : null

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-aid]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-aid")
    setSelectedId(prev => prev === id ? null : id)
  }

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-200px)]">
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[40vh]" onClick={handleClick}>
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none">
          {[...assets].reverse().map(a => (
            <div key={a.id} data-aid={a.id}
              className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px]
                ${selectedId === a.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}`}
            >
              <span className="text-[#4ade80] text-[8px] font-mono shrink-0">{(a.relevance_score ?? 0).toFixed(2)}</span>
              <span className="text-[#bbb] font-mono truncate">{a.url.slice(0, 60)}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
        {selected ? (
          <div className="space-y-2 text-[10px]">
            <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Asset Detail ]</div>
            <a href={selected.url} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">{selected.url}</a>
            <KeyValueGrid items={[
              { key: "relevance", value: (selected.relevance_score ?? 0).toFixed(2), valueColor: "#4ade80" },
              { key: "novelty", value: (selected.novelty_score ?? 0).toFixed(2) },
              { key: "diffractive", value: (selected.diffractive_score ?? 0).toFixed(2) },
            ]} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">[ select an asset ]</div>
        )}
      </div>
    </div>
  )
}

/* ── Branches Tab ── */
function BranchesTab({ task }: { task: ResearchTask }) {
  const branches = task.branches ?? []
  if (branches.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no branches — orchestrator uses Steps instead ]</div>

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-200px)]">
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[40vh]">
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1">
          {branches.map((b: any) => {
            const sc = STATUS_COLORS[b.status] ?? "#666"
            return (
              <div key={b.id} className="flex items-center gap-1.5 px-1.5 py-1 text-[10px]">
                <span style={{ color: sc }} className="text-[8px]">●</span>
                <span className="text-[#bbb] font-mono truncate">{b.query || b.id?.slice(0, 12)}</span>
                <span style={{ color: sc }} className="text-[8px] ml-auto">{b.status}</span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="flex-1 min-w-0 flex items-center justify-center text-[#444] italic text-xs select-none">[ select a branch ]</div>
    </div>
  )
}

/* ── Meta Log Tab (§3, §4) ── */
const EVENT_LABELS: Record<string, string> = {
  orchestrator_plan: "Plan", orchestrator_plan_prompt: "Plan Prompt",
  orchestrator_plan_response: "Plan Response", orchestrator_replan: "Re-Plan",
  orchestrator_search: "Search", orchestrator_digest_prompt: "Digest Prompt",
  orchestrator_digest_response: "Digest Response", orchestrator_digest_error: "Digest Error",
  orchestrator_reflect: "Reflect", orchestrator_reflect_prompt: "Reflect Prompt",
  orchestrator_reflect_response: "Reflect Response", orchestrator_evaluate: "Evaluate",
  orchestrator_synthesize_prompt: "Synth Prompt", orchestrator_synthesize_response: "Synth Response",
  orchestrator_complete: "Complete", orchestrator_start: "Start",
  task_started: "Start", task_complete: "Complete",
  fetch_complete: "Fetch", fetch_error: "Fetch Error",
  llm_prompt: "LLM Prompt", llm_response: "LLM Response", llm_error: "LLM Error",
}
const EVENT_COLORS: Record<string, string> = { ...STATUS_COLORS,
  orchestrator_search: "#3b82f6", orchestrator_digest_prompt: "#c084fc",
  orchestrator_digest_response: "#a892ee", orchestrator_reflect: "#a78bfa",
  orchestrator_synthesize_prompt: "#c084fc", orchestrator_synthesize_response: "#a892ee",
  orchestrator_evaluate: "#22d3ee", llm_prompt: "#c084fc", llm_response: "#a892ee",
  fetch_complete: "#3b82f6", fetch_error: "#ef4444",
}

function MetaLogTab({ taskId }: { taskId: string }) {
  const [data, setData] = useState<MetaLogResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  useEffect(() => { getTaskMetaLog(taskId).then(setData).finally(() => setLoading(false)) }, [taskId])

  if (loading) return <div className="text-[#555] animate-pulse text-xs font-mono">[ loading… ]</div>
  if (!data || data.entries.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no meta events ]</div>

  const entries = [...data.entries].reverse()
  const selected = selectedId ? entries.find(e => e.id === selectedId) : null

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-mid]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-mid")
    if (id) setSelectedId(prev => prev === id ? null : id)
  }

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-200px)]">
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[40vh]" onClick={handleClick}>
        <div className="flex-1 space-y-0.5 overflow-y-auto pr-1 select-none">
          {entries.map(entry => {
            const label = EVENT_LABELS[entry.event_type] || entry.event_type
            const ec = EVENT_COLORS[entry.event_type] || "#666"
            return (
              <div key={entry.id} data-mid={entry.id}
                className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px]
                  ${selectedId === entry.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"}`}
              >
                <span style={{ color: ec }} className="text-[8px] shrink-0">●</span>
                <span className="text-[#bbb] font-mono">{label}</span>
                <span className="text-[#555] text-[8px] ml-auto">{entry.created_at?.slice(11, 19)}</span>
              </div>
            )
          })}
        </div>
      </div>
      <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
        {selected ? (
          <div className="space-y-1 text-[10px]">
            <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ {EVENT_LABELS[selected.event_type] || selected.event_type} ]</div>
            {selected.branch_id && <div className="text-[#555] text-[9px]">branch: {selected.branch_id.slice(0, 8)}…</div>}
            <div className="text-[#777] font-mono whitespace-pre-wrap break-all leading-relaxed max-h-96 overflow-y-auto">
              {Object.entries(selected.event_data || {}).map(([k, v]) => {
                const val = typeof v === "string" ? v : JSON.stringify(v, null, 1)
                return (
                  <div key={k} className="mb-0.5">
                    <span className="text-[#555]">{k}: </span>
                    <span className="text-[#888]">{val}</span>
                  </div>
                )
              })}
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">[ select an event ]</div>
        )}
      </div>
    </div>
  )
}

/* ── Shell (§1: terminal header, §6: tab bar) ── */
function TaskPageInner({ task }: { task: ResearchTask }) {
  const [tab, setTab] = useState<SubTabId>("info")
  const [liveTask, setLiveTask] = useState(task)

  useEffect(() => {
    if (task.status !== "active" && task.status !== "queued") return
    const timer = setInterval(() => {
      getResearchTask(task.id).then(t => { if (t) setLiveTask(t) }).catch(() => {})
    }, 5000)
    return () => clearInterval(timer)
  }, [task.id, task.status])

  const current = liveTask || task
  const color = STATUS_COLORS[current.status] ?? "#666"

  return (
    <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
      {/* Header §1: terminal breadcrumb */}
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
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <TerminalButton onClick={() => window.location.href = '/'}>home</TerminalButton>
          <TerminalButton onClick={() => window.open('/agent', '_blank')} intent="purple">agent</TerminalButton>
        </div>
      </div>

      {/* Tab bar §6: • dot-separated */}
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

      {/* Content area — tabs with two-panel layout use their own height calc */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {tab === "info"     && <InfoTab task={current} />}
        {tab === "steps"    && <StepsTab taskId={current.id} />}
        {tab === "assets"   && <AssetsTab task={current} />}
        {tab === "branches" && <BranchesTab task={current} />}
        {tab === "meta_log" && <MetaLogTab taskId={current.id} />}
      </div>
    </div>
  )
}

export const ResearchTaskPage = memo(function ResearchTaskPage({ taskId, isNew }: Props) {
  if (isNew) {
    return (
      <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
        <div className="flex items-center px-6 py-3 border-b border-[#1a1a1a] shrink-0">
          <a href="/research" className="text-[#666] hover:text-[#bbb] text-[11px] transition-colors cursor-pointer">◀ back</a>
          <span className="text-[#333] mx-2">|</span>
          <span className="text-[#eab308] text-[11px]">■ new research</span>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4 max-w-lg">
          <NewResearchFormInline />
        </div>
      </div>
    )
  }

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

/* ── Inline New Research Form ── */
function NewResearchFormInline() {
  const [objective, setObjective] = useState("")
  const [depth, setDepth] = useState(2)
  const [breadth, setBreadth] = useState(2)
  const [budget, setBudget] = useState(0.50)
  const [sending, setSending] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!objective.trim() || sending) return
    setSending(true)
    try {
      const { dispatchResearch } = await import("../../../api/research")
      const result = await dispatchResearch({ objective: objective.trim(), max_depth: depth, max_breadth: breadth, budget_limit_usd: budget })
      if (result) window.location.href = `/research?id=${result.task_id}`
    } catch {} finally { setSending(false) }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-2">[ new research ]</div>
      <input type="text" value={objective} onChange={e => setObjective(e.target.value)}
        placeholder="What should we investigate?"
        className="w-full bg-transparent border-b border-[#222]/40 focus:border-[#444] outline-none text-[#ccc] text-xs font-mono py-1 mb-3"
        autoFocus disabled={sending}
      />
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-[10px] font-mono text-[#777]">
        <label className="flex items-center gap-1">depth:
          <select value={depth} onChange={e => setDepth(Number(e.target.value))} className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none">
            {[1,2,3,4].map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1">breadth:
          <select value={breadth} onChange={e => setBreadth(Number(e.target.value))} className="bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none">
            {[1,2,3,4,6].map(b => <option key={b} value={b}>{b}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1">budget: $
          <input type="number" value={budget} step={0.25} min={0.10} max={5.00} onChange={e => setBudget(Number(e.target.value))} className="w-16 bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none" />
        </label>
      </div>
      <button type="submit" disabled={!objective.trim() || sending} className="text-[10px] text-[#4ade80] font-mono disabled:text-[#333] transition-colors hover:text-[#6ee7b0] cursor-pointer">[{sending ? "dispatching..." : "▶ dispatch research"}]</button>
    </form>
  )
}
