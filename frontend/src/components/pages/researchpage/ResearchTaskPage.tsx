// ResearchTaskPage — single research task detail with tabbed left list + right detail.
// Pattern: /agent page — tab bar, then two-panel (left list, right detail).

import React, { memo, useState, useEffect, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import type {
  ResearchTask, TaskStepsResponse, ResearchStep, ResearchStepResult,
  MetaLogResponse, MetaLogEntry,
} from "../../../api/research"
import {
  getResearchTask, getTaskSteps, getTaskMetaLog,
  approveProposal, rejectProposal, cancelTask, retryTask, deleteTask,
} from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"

type SubTabId = "info" | "steps" | "assets" | "branches" | "meta_log" | "actions"

const SUB_TABS: { key: SubTabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "assets",   label: "Assets" },
  { key: "branches", label: "Branches" },
  { key: "meta_log", label: "Meta Log" },
  { key: "actions",  label: "Actions" },
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

/* ── Info Tab ── */
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
  return (
    <div className="space-y-3">
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Objective ]</div>
        <div className="text-[#94a3b8] text-[10px] leading-relaxed">{task.objective}</div>
      </div>
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Metrics ]</div>
        <KeyValueGrid items={metrics} />
      </div>
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

/* ── Steps Tab ── */
function StepsTab({ taskId }: { taskId: string }) {
  const [data, setData] = useState<TaskStepsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null)
  useEffect(() => { getTaskSteps(taskId).then(setData).finally(() => setLoading(false)) }, [taskId])

  if (loading) return <div className="text-[#555] animate-pulse text-xs">loading…</div>
  if (!data || data.steps.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8">[ no steps — legacy engine ]</div>

  const steps = [...data.steps].reverse()
  const selectedStep = selectedStepId ? data.steps.find(s => s.id === selectedStepId) : null
  const selectedResults = selectedStepId ? (data.results_by_step[selectedStepId] || []) : []

  const handleListClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-step-id]") as HTMLElement | null
    if (!el) return
    const sid = el.getAttribute("data-step-id")
    setSelectedStepId(prev => prev === sid ? null : sid)
  }

  const STEP_COLORS: Record<string, string> = {
    search: "#3b82f6", parallel_parse: "#f59e0b", digest: "#a892ee",
    reflect: "#c084fc", synthesize: "#4ade80", evaluate: "#22d3ee",
  }

  return (
    <div className="flex flex-col md:flex-row gap-3">
      {/* Left list */}
      <div className="md:w-[450px] shrink-0 min-h-0 max-h-[40vh] md:max-h-[calc(100vh-220px)] overflow-y-auto" onClick={handleListClick}>
        {steps.map(s => {
          const sc = STEP_COLORS[s.step_type] || "#666"
          return (
            <div
              key={s.id} data-step-id={s.id}
              className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px] ${
                selectedStepId === s.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"
              }`}
            >
              <span style={{ color: sc }} className="text-[8px]">●</span>
              <span className="text-[#bbb]">#{s.step_number} {s.step_type}</span>
              <span style={{ color: sc }} className="text-[8px] ml-auto">{s.status}</span>
            </div>
          )
        })}
      </div>

      {/* Right detail */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        {selectedStep ? (
          <div className="space-y-2 text-[10px]">
            <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">
              [ Step #{selectedStep.step_number}: {selectedStep.step_type} ]
            </div>
            {selectedStep.result_summary && <div className="text-[#94a3b8]">{selectedStep.result_summary}</div>}
            {selectedResults.length > 0 && (
              <div className="space-y-1">
                <div className="text-[#555] text-[9px]">{selectedResults.length} source{selectedResults.length !== 1 ? "s" : ""}</div>
                {selectedResults.map(r => {
                  let analysis: any = null
                  try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
                  return (
                    <div key={r.id} className="border-l border-[#222] pl-2 py-1">
                      <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:text-[#6ee7b0] underline text-[10px] break-all">{r.source_title || r.source_url?.slice(0, 80) || "—"}</a>
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
            )}
          </div>
        ) : (
          <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ select a step ]</div>
        )}
      </div>
    </div>
  )
}

/* ── Assets Tab ── */
function AssetsTab({ task }: { task: ResearchTask }) {
  const assets = task.assets ?? []
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = selectedId ? assets.find(a => a.id === selectedId) : null

  if (assets.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8">[ no assets harvested ]</div>

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-asset-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-asset-id")
    setSelectedId(prev => prev === id ? null : id)
  }

  return (
    <div className="flex flex-col md:flex-row gap-3">
      <div className="md:w-[450px] shrink-0 min-h-0 max-h-[40vh] md:max-h-[calc(100vh-220px)] overflow-y-auto" onClick={handleClick}>
        {[...assets].reverse().map(a => (
          <div
            key={a.id} data-asset-id={a.id}
            className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px] ${
              selectedId === a.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"
            }`}
          >
            <span className="text-[#4ade80] text-[8px]">{(a.relevance_score ?? 0).toFixed(2)}</span>
            <span className="text-[#bbb] truncate">{a.url.slice(0, 60)}</span>
          </div>
        ))}
      </div>
      <div className="flex-1 min-w-0 overflow-y-auto text-[10px]">
        {selected ? (
          <div className="space-y-2">
            <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">[ Asset Detail ]</div>
            <a href={selected.url} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all">{selected.url}</a>
            <KeyValueGrid items={[
              { key: "relevance", value: (selected.relevance_score ?? 0).toFixed(2), valueColor: "#4ade80" },
              { key: "novelty", value: (selected.novelty_score ?? 0).toFixed(2) },
              { key: "diffractive", value: (selected.diffractive_score ?? 0).toFixed(2) },
            ]} />
          </div>
        ) : (
          <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ select an asset ]</div>
        )}
      </div>
    </div>
  )
}

/* ── Branches Tab ── */
function BranchesTab({ task }: { task: ResearchTask }) {
  const branches = task.branches ?? []
  if (branches.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8">[ no branches — orchestrator uses Steps instead ]</div>

  return (
    <div className="flex flex-col md:flex-row gap-3">
      <div className="md:w-[450px] shrink-0 min-h-0 max-h-[40vh] md:max-h-[calc(100vh-220px)] overflow-y-auto">
        {branches.map((b: any) => {
          const sc = STATUS_COLORS[b.status] ?? "#666"
          return (
            <div key={b.id} className="flex items-center gap-1.5 px-1.5 py-1 text-[10px]">
              <span style={{ color: sc }} className="text-[8px]">●</span>
              <span className="text-[#bbb] truncate">{b.query || b.id?.slice(0, 12)}</span>
              <span style={{ color: sc }} className="text-[8px] ml-auto">{b.status}</span>
            </div>
          )
        })}
      </div>
      <div className="flex-1 min-w-0 text-[#444] italic text-xs text-center mt-8 select-none">[ select a branch ]</div>
    </div>
  )
}

/* ── Meta Log Tab ── */
function MetaLogTab({ taskId }: { taskId: string }) {
  const [data, setData] = useState<MetaLogResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  useEffect(() => { setLoading(true); getTaskMetaLog(taskId).then(setData).finally(() => setLoading(false)) }, [taskId])

  if (loading) return <div className="text-[#555] animate-pulse text-xs">loading…</div>
  if (!data || data.entries.length === 0) return <div className="text-[#444] italic text-xs text-center mt-8">[ no meta events ]</div>

  const entries = [...data.entries].reverse()
  const selected = selectedId ? entries.find(e => e.id === selectedId) : null

  const LABELS: Record<string, string> = {
    orchestrator_start: "Start", orchestrator_plan: "Plan", orchestrator_plan_prompt: "Plan Prompt",
    orchestrator_plan_response: "Plan Response", orchestrator_replan: "Re-Plan", orchestrator_search: "Search",
    orchestrator_digest_prompt: "Digest Prompt", orchestrator_digest_response: "Digest Response",
    orchestrator_digest_error: "Digest Error", orchestrator_reflect: "Reflect",
    orchestrator_reflect_prompt: "Reflect Prompt", orchestrator_reflect_response: "Reflect Response",
    orchestrator_evaluate: "Evaluate", orchestrator_synthesize_prompt: "Synth Prompt",
    orchestrator_synthesize_response: "Synth Response", orchestrator_complete: "Complete",
    task_started: "Start", task_complete: "Complete", fetch_complete: "Fetch", fetch_error: "Fetch Error",
    llm_prompt: "LLM Prompt", llm_response: "LLM Response", llm_error: "LLM Error",
  }
  const COLORS: Record<string, string> = {
    orchestrator_start: "#4ade80", orchestrator_plan: "#a78bfa", orchestrator_search: "#3b82f6",
    orchestrator_digest_prompt: "#c084fc", orchestrator_digest_response: "#a892ee",
    orchestrator_reflect: "#a78bfa", orchestrator_evaluate: "#22d3ee", orchestrator_complete: "#22d3ee",
    task_started: "#4ade80", task_complete: "#22d3ee", fetch_complete: "#3b82f6",
    fetch_error: "#ef4444", llm_prompt: "#c084fc", llm_response: "#a892ee", llm_error: "#ef4444",
  }

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = (e.target as HTMLElement).closest("[data-meta-id]") as HTMLElement | null
    if (!el) return
    const id = el.getAttribute("data-meta-id")
    if (id) setSelectedId(prev => prev === id ? null : id)
  }

  return (
    <div className="flex flex-col md:flex-row gap-3">
      <div className="md:w-[450px] shrink-0 min-h-0 max-h-[40vh] md:max-h-[calc(100vh-220px)] overflow-y-auto" onClick={handleClick}>
        {entries.map(entry => {
          const label = LABELS[entry.event_type] || entry.event_type
          const ec = COLORS[entry.event_type] || "#666"
          return (
            <div
              key={entry.id} data-meta-id={entry.id}
              className={`flex items-center gap-1.5 px-1.5 py-1 cursor-pointer border-l-2 transition-colors text-[10px] ${
                selectedId === entry.id ? "border-[#a78bfa] bg-[#1a1a2e]/50" : "border-transparent hover:bg-[#111]"
              }`}
            >
              <span style={{ color: ec }} className="text-[8px] shrink-0">●</span>
              <span className="text-[#bbb]">{label}</span>
              <span className="text-[#555] text-[8px] ml-auto">{entry.created_at?.slice(11, 19)}</span>
            </div>
          )
        })}
      </div>
      <div className="flex-1 min-w-0 overflow-y-auto text-[10px]">
        {selected ? (
          <div className="space-y-1 max-h-96 overflow-y-auto">
            <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
              [ {LABELS[selected.event_type] || selected.event_type} ]
            </div>
            {selected.branch_id && <div className="text-[#555] text-[9px]">branch: {selected.branch_id.slice(0, 8)}…</div>}
            <div className="text-[#777] font-mono whitespace-pre-wrap break-all leading-relaxed">
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
          <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ select an event ]</div>
        )}
      </div>
    </div>
  )
}

/* ── Actions Tab ── */
function ActionsTab({ task }: { task: ResearchTask }) {
  const navigateHome = () => { window.location.href = "/research" }

  const doApprove = async () => { await approveProposal(task.id); navigateHome() }
  const doReject = async () => { await rejectProposal(task.id); navigateHome() }
  const doCancel = async () => { await cancelTask(task.id); navigateHome() }
  const doRetry = async () => { await retryTask(task.id); navigateHome() }
  const doDelete = async () => { await deleteTask(task.id); navigateHome() }
  const doContinue = async () => {
    // Dispatch new task with depth+1
    const { dispatchResearch } = await import("../../../api/research")
    await dispatchResearch({
      objective: task.objective,
      title: task.title,
      max_depth: (task.max_depth || 2) + 1,
      max_breadth: task.max_breadth || 2,
      is_agonistic: !!task.is_agonistic,
      budget_limit_usd: task.budget_limit_usd || 0.50,
    })
    navigateHome()
  }

  return (
    <div className="space-y-3">
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Actions ]</div>
        <div className="flex flex-wrap gap-2 text-[10px]">
          {task.status === "proposed" && (
            <>
              <TerminalButton onClick={doApprove} intent="save">✓ approve</TerminalButton>
              <TerminalButton onClick={doReject} intent="delete">✗ dismiss</TerminalButton>
              <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {(task.status === "queued" || task.status === "active") && (
            <>
              <TerminalButton onClick={doCancel} intent="delete">✕ cancel</TerminalButton>
              <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "failed" && (
            <>
              <TerminalButton onClick={doRetry} intent="edit">↻ retry</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "completed" && (
            <>
              <TerminalButton onClick={doRetry} intent="save">↻ retry</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "cancelled" && (
            <>
              <TerminalButton onClick={doRetry} intent="edit">↻ retry</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "rejected" && (
            <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
          )}
        </div>
      </div>
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Timeline ]</div>
        <KeyValueGrid items={[
          ...(task.proposed_at ? [{ key: "proposed", value: task.proposed_at }] : []),
          ...(task.approved_at ? [{ key: "approved", value: task.approved_at }] : []),
          ...(task.started_at ? [{ key: "started", value: task.started_at }] : []),
          ...(task.completed_at ? [{ key: "completed", value: task.completed_at }] : []),
        ]} />
      </div>
    </div>
  )
}

/* ── Shell ── */
function TaskPageInner({ task }: { task: ResearchTask }) {
  const [tab, setTab] = useState<SubTabId>("info")

  // Poll for updates if task is active
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
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1a1a1a] shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <a href="/research" className="text-[#666] hover:text-[#bbb] text-[11px] transition-colors">◀ back</a>
          <span className="text-[#333]">|</span>
          <span className="text-[11px] text-[#444] tracking-widest uppercase select-none shrink-0">
            <span className="text-[#eab308]">■</span>
            <span className="ml-2">research</span>
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

      {/* Sub-tab bar */}
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

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {tab === "info"     && <InfoTab task={current} />}
        {tab === "steps"    && <StepsTab taskId={current.id} />}
        {tab === "assets"   && <AssetsTab task={current} />}
        {tab === "branches" && <BranchesTab task={current} />}
        {tab === "meta_log" && <MetaLogTab taskId={current.id} />}
        {tab === "actions"  && <ActionsTab task={current} />}
      </div>
    </div>
  )
}

export const ResearchTaskPage = memo(function ResearchTaskPage({ taskId, isNew }: Props) {
  // New research form (no existing task)
  if (isNew) {
    return (
      <div className="flex flex-col h-screen w-full bg-[#0c0c0c] font-mono text-[#666]">
        <div className="flex items-center px-6 py-3 border-b border-[#1a1a1a] shrink-0">
          <a href="/research" className="text-[#666] hover:text-[#bbb] text-[11px] transition-colors">◀ back</a>
          <span className="text-[#333] mx-2">|</span>
          <span className="text-[#eab308] text-[11px]">■ new research</span>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4">
          <NewResearchFormInline />
        </div>
      </div>
    )
  }

  // Existing task
  const [task, setTask] = useState<ResearchTask | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    getResearchTask(taskId)
      .then(setTask)
      .catch(e => setError(e.message))
  }, [taskId])

  if (error) return <div className="flex flex-col h-screen bg-[#0c0c0c] items-center justify-center text-[#ef4444] text-xs font-mono">{error} <a href="/research" className="text-[#666] hover:text-[#bbb] mt-2">◀ back</a></div>
  if (!task) return <div className="flex flex-col h-screen bg-[#0c0c0c] items-center justify-center text-[#555] text-xs animate-pulse font-mono">loading…</div>

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
      const result = await dispatchResearch({
        objective: objective.trim(),
        max_depth: depth, max_breadth: breadth,
        budget_limit_usd: budget,
      })
      if (result) window.location.href = `/research?id=${result.task_id}`
    } catch {} finally { setSending(false) }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-lg">
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
          <input type="number" value={budget} step={0.25} min={0.10} max={5.00}
            onChange={e => setBudget(Number(e.target.value))}
            className="w-16 bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none"
          />
        </label>
      </div>
      <button type="submit" disabled={!objective.trim() || sending}
        className="text-[10px] text-[#4ade80] font-mono disabled:text-[#333] transition-colors hover:text-[#6ee7b0]"
      >
        [{sending ? "dispatching..." : "▶ dispatch research"}]
      </button>
    </form>
  )
}
