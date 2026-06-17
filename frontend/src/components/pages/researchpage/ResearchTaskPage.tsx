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
  getResearchTask, getTaskSteps, getTaskMetaLog, getTaskPhase, getStepPreview,
  approveProposal, rejectProposal, cancelTask, retryTask, deleteTask,
  rerunTask, executeStep,
} from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"

type SubTabId = "info" | "steps" | "assets" | "branches"

const SUB_TABS: { key: SubTabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "assets",   label: "Assets" },
  { key: "branches", label: "Branches" },
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
function InfoTab({ task, orchPhase }: { task: ResearchTask; orchPhase?: string }) {
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
    ...(orchPhase && orchPhase !== "complete" ? [{ key: "phase", value: orchPhase.toUpperCase(), valueColor: "#f59e0b" }] : []),
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
          {task.status === "queued" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => executeStep(task.id))} intent="save">▶ run</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => cancelTask(task.id))} intent="delete">✕ cancel</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "active" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => cancelTask(task.id))} intent="delete">✕ cancel</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "failed" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => rerunTask(task.id))} intent="edit">⟳ rerun</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => retryTask(task.id))} intent="neutral">↻ retry (clone)</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "completed" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => rerunTask(task.id))} intent="edit">⟳ rerun</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => retryTask(task.id))} intent="save">↻ retry (clone)</TerminalButton>
              <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => deleteTask(task.id))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "cancelled" && (
            <>
              <TerminalButton onClick={() => doActionAndReload(() => rerunTask(task.id))} intent="edit">⟳ rerun</TerminalButton>
              <TerminalButton onClick={() => doActionAndReload(() => retryTask(task.id))} intent="neutral">↻ retry (clone)</TerminalButton>
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

/* ── Steps Tab (§3: left list + right detail, with orchestrator pipeline) ── */
const STEP_LABELS: Record<string, string> = {
  plan: "Plan", search: "Search", parallel_parse: "Parse Sources",
  digest: "Digest", reflect: "Reflect", synthesize: "Synthesize",
  evaluate: "Evaluate",
}

const PHASE_ORDER_DISPLAY = [
  "planning", "searching", "parsing", "digesting", "reflecting", "evaluating", "synthesizing",
]
const PHASE_LABELS: Record<string, string> = {
  planning: "Plan", searching: "Search", parsing: "Parse Sources",
  digesting: "Digest", reflecting: "Reflect", evaluating: "Evaluate",
  synthesizing: "Synthesize", complete: "Complete",
}

/** Determine phase status relative to current orch phase */
function phaseStatus(idx: number, currentIdx: number): "done" | "current" | "pending" {
  if (currentIdx < 0) return "pending"
  if (idx < currentIdx) return "done"
  if (idx === currentIdx) return "current"
  return "pending"
}

function StepsTab({ taskId, orchPhase, taskStatus }: { taskId: string; orchPhase: string; taskStatus: string }) {
  const [data, setData] = useState<TaskStepsResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [stepping, setStepping] = useState(false)

  const reload = () => window.location.reload()

  const load = useCallback(() => {
    getTaskSteps(taskId).then(setData).catch(() => {})
  }, [taskId])

  useEffect(() => { load() }, [load])

  // Poll while task is active
  useEffect(() => {
    if (taskStatus !== "active") return
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load, taskStatus])

  const currentPhaseIdx = PHASE_ORDER_DISPLAY.indexOf(orchPhase)
  // If phase isn't in the display list (e.g. "not_started" or "complete"), use -2
  const hasPipeline = orchPhase && orchPhase !== "complete" && orchPhase !== "not_started"

  const doStep = async () => {
    setStepping(true)
    try { await executeStep(taskId) } catch {}
    setStepping(false)
    reload()
  }
  const doRerun = async () => {
    setStepping(true)
    try { await rerunTask(taskId) } catch {}
    setStepping(false)
    reload()
  }

  // Map pipeline phases to DB step IDs
  const phaseToStepId: Record<string, string | null> = {}
  if (data) {
    const steps = [...data.steps].reverse()
    const seen: Record<string, boolean> = {}
    for (const s of steps) {
      const phase = STEP_TO_PHASE[s.step_type]
      if (phase && !seen[phase]) { phaseToStepId[phase] = s.id; seen[phase] = true }
    }
  }

  const handlePipelineClick = (phase: string) => {
    const sid = phaseToStepId[phase]
    setSelectedId(prev => prev === sid ? null : sid)
  }

  return (
    <div className="flex flex-col md:flex-row gap-3 md:h-[calc(100vh-200px)]">
      {/* ── LEFT: Pipeline (clickable) ── */}
      <div className="md:w-[450px] shrink-0 w-full flex flex-col min-h-0 md:max-h-full max-h-[40vh]">
        <div className="flex-1 overflow-y-auto pr-1 space-y-3">
          <div>
            <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1.5">[ Pipeline ]</div>
            <div className="space-y-0.5">
              {PHASE_ORDER_DISPLAY.map((phase, idx) => {
                const label = PHASE_LABELS[phase] || phase
                const sid = phaseToStepId[phase]
                const isSel = sid && sid === selectedId
                // Determine status
                const allComplete = taskStatus === "completed" && orchPhase === "complete"
                const status = allComplete ? "done" : hasPipeline ? phaseStatus(idx, currentPhaseIdx) : "pending"
                const isDone = status === "done"
                const isCurrent = status === "current"
                const sc = isDone ? "#4ade80" : isCurrent ? "#f59e0b" : "#444"
                const canClick = isDone && sid

                return (
                  <div key={phase}
                    onClick={canClick ? (() => handlePipelineClick(phase)) : undefined}
                    className={`flex items-center gap-2 text-[10px] px-2 py-1 rounded-sm
                      ${canClick ? "cursor-pointer hover:bg-[#111]" : ""}
                      ${isCurrent ? "bg-[#1a1a2e]/30 border border-[#f59e0b]/20" : ""}
                      ${isSel ? "border border-[#a78bfa]/30 bg-[#1a1a2e]/30" : ""}`}>
                    <span style={{ color: sc }} className="text-[8px] shrink-0 w-3">
                      {isDone ? "✔" : isCurrent ? "▶" : "○"}
                    </span>
                    <span className={`font-mono flex-1 ${isSel ? "text-[#c4b5fd]" : isDone ? "text-[#94a3b8]" : isCurrent ? "text-[#fbbf24]" : "text-[#555]"}`}>
                      {label}
                    </span>
                    {isCurrent && (
                      <button onClick={e => { e.stopPropagation(); doStep() }} disabled={stepping}
                        className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
                        [{stepping ? "…" : "▶ run"}]
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
            {taskStatus === "completed" && orchPhase === "complete" && (
              <div className="mt-2">
                <TerminalButton onClick={doRerun} intent="edit">⟳ rerun all</TerminalButton>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── RIGHT: Detail Panel ── */}
      <div className="flex-1 min-w-0 w-full md:flex md:flex-col md:min-h-0 overflow-y-auto">
        <StepDetailRight taskId={taskId} data={data} selectedId={selectedId} orchPhase={orchPhase} taskStatus={taskStatus} />
      </div>
    </div>
  )
}

/* ── Right: Detail Panel (summary + source results + meta log) ── */
function StepDetailRight({ taskId, data, selectedId, orchPhase, taskStatus }: {
  taskId: string
  data: TaskStepsResponse | null
  selectedId: string | null
  orchPhase: string
  taskStatus: string
}) {
  const [preview, setPreview] = useState<import("../../../api/research").StepPreview | null>(null)
  const [prevLoading, setPrevLoading] = useState(false)

  const fetchPreview = useCallback(() => {
    if (!orchPhase || orchPhase === "complete" || orchPhase === "not_started") return
    if (taskStatus !== "active" && taskStatus !== "queued") return
    setPrevLoading(true)
    getStepPreview(taskId, orchPhase)
      .then(setPreview)
      .catch(() => setPreview(null))
      .finally(() => setPrevLoading(false))
  }, [taskId, orchPhase, taskStatus])

  // Fetch preview for current phase when no DB step is selected
  useEffect(() => {
    if (selectedId) { setPreview(null); return }
    fetchPreview()
  }, [selectedId, fetchPreview])

  // If a DB step is selected, show its details
  if (selectedId) return <DbStepDetail {...{ taskId, data, selectedId }} />

  // If no DB step selected, show placeholder or preview
  const phaseLabel = PHASE_LABELS[orchPhase] || orchPhase
  if (prevLoading) return (
    <div className="flex items-center justify-center h-full text-[#555] animate-pulse text-xs select-none">[ loading preview… ]</div>
  )
  if (preview) return (
    <PreviewDetail preview={preview} phaseLabel={phaseLabel}
      onReinitialize={() => { setPrevLoading(true); fetchPreview() }} reinitLoading={prevLoading} />
  )
  return (
    <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">
      [ select a step ]
    </div>
  )
}

/* ── Preview: shows inputs before step execution ── */
function PreviewDetail({ preview, phaseLabel, onReinitialize, reinitLoading }: {
  preview: import("../../../api/research").StepPreview
  phaseLabel: string
  onReinitialize: () => void
  reinitLoading: boolean
}) {
  return (
    <div className="space-y-2 text-[10px]">
      <div className="flex items-center justify-between">
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">
          [ {phaseLabel} — preview ]
        </div>
        <button onClick={onReinitialize} disabled={reinitLoading}
          className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
          [{reinitLoading ? "…" : "⟳ reinitialize"}]
        </button>
      </div>
      <div className="flex gap-3 border-b border-[#1a1a1a] pb-1">
        <span className="text-[#94a3b8] text-[9px] uppercase">input</span>
      </div>
      {preview.objective && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">objective:</div>
          <div className="text-[#94a3b8] pl-2">{preview.objective}</div>
        </div>
      )}
      {preview.max_depth != null && (
        <div className="flex gap-4 text-[#777] flex-wrap">
          <span>depth: {preview.max_depth}</span>
          <span>budget: ${preview.budget_limit_usd?.toFixed(2)}</span>
          {preview.model && <span>model: {preview.model}</span>}
          {preview.temperature != null && <span>temp: {preview.temperature}</span>}
          {preview.max_tokens && <span>tokens: {preview.max_tokens}</span>}
        </div>
      )}
      {preview.system_prompt && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">system prompt:</div>
          <pre className="text-[#888] text-[9px] bg-[#0c0c0c] border border-[#1a1a1a] p-2 rounded-sm max-h-48 overflow-y-auto whitespace-pre-wrap break-all">{preview.system_prompt}</pre>
        </div>
      )}
      {preview.user_prompt && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">user prompt:</div>
          <pre className="text-[#888] text-[9px] bg-[#0c0c0c] border border-[#1a1a1a] p-2 rounded-sm max-h-32 overflow-y-auto whitespace-pre-wrap break-all">{preview.user_prompt}</pre>
        </div>
      )}
      {preview.pending_queries && preview.pending_queries.length > 0 && (
        <div>
          <div className="text-[#555] text-[9px] mb-0.5">pending queries:</div>
          {preview.pending_queries.map((q, i) => (
            <div key={i} className="text-[#94a3b8] pl-2">· {q}</div>
          ))}
        </div>
      )}
      {preview.note && (
        <div className="text-[#444] italic text-[9px]">{preview.note}</div>
      )}
    </div>
  )
}

const STEP_TO_PHASE: Record<string, string> = {
  plan: "planning", search: "searching", parallel_parse: "parsing",
  digest: "digesting", reflect: "reflecting", evaluate: "evaluating",
  synthesize: "synthesizing",
}

type DetailTab = "input" | "result" | "log"

/* ── DB Step Detail (when a step is selected from the results list) ── */
function DbStepDetail({ taskId, data, selectedId }: {
  taskId: string
  data: TaskStepsResponse | null
  selectedId: string
}) {
  const steps = data ? [...data.steps].reverse() : []
  const selected = steps.find(s => s.id === selectedId)
  if (!selected) return null
  const selectedResults = data ? (data.results_by_step[selectedId] || []) : []
  const [tab, setTab] = useState<DetailTab>("result")
  const [metaLog, setMetaLog] = useState<MetaLogResponse | null>(null)
  const [logLoading, setLogLoading] = useState(false)
  const [liveInput, setLiveInput] = useState<import("../../../api/research").StepPreview | null>(null)
  const [reinitLoading, setReinitLoading] = useState(false)

  const stepPhase = STEP_TO_PHASE[selected.step_type] || ""

  useEffect(() => {
    setLogLoading(true)
    getTaskMetaLog(taskId, selectedId).then(m => { setMetaLog(m); setTab("result") }).catch(() => setMetaLog(null)).finally(() => setLogLoading(false))
  }, [selectedId, taskId])

  const fetchLiveInput = () => {
    if (!stepPhase) return
    setReinitLoading(true)
    getStepPreview(taskId, stepPhase).then(setLiveInput).catch(() => {}).finally(() => setReinitLoading(false))
  }
  // Auto-fetch when switching to input tab
  useEffect(() => { if (tab === "input" && !liveInput) fetchLiveInput() }, [tab])

  const entries = metaLog?.entries ?? []
  const inputEntries = entries.filter(e => {
    const d = e.event_data as any
    return e.event_type.endsWith("_prompt") || e.event_type === "orchestrator_search" ||
      (d && (d.system_prompt || d.user_prompt))
  })
  const responseEntries = entries.filter(e =>
    e.event_type.endsWith("_response") && !e.event_type.endsWith("_prompt")
  )
  const otherEntries = entries.filter(e => !inputEntries.includes(e) && !responseEntries.includes(e))

  const handleRerunStep = async () => {
    await doActionAndReload(() => executeStep(taskId))
  }

  return (
    <div className="space-y-2 text-[10px]">
      <div className="flex items-center justify-between">
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider">
          [ Step #{selected.step_number}: {STEP_LABELS[selected.step_type] || selected.step_type} <span className="text-[#555]">({selected.status})</span> ]
        </div>
        {selected.status === "completed" && (
          <TerminalButton onClick={handleRerunStep} intent="edit">⟳ rerun step</TerminalButton>
        )}
      </div>

      {/* Mini-tabs */}
      <div className="flex gap-3 border-b border-[#1a1a1a] pb-1">
        {(["input","result","log"] as DetailTab[]).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`text-[9px] uppercase cursor-pointer transition-colors
              ${tab === t ? "text-[#94a3b8]" : "text-[#444] hover:text-[#777]"}`}>
            {t}{entries.length > 0 ? ` (${t==="input"?inputEntries.length:t==="log"?otherEntries.length:entries.length})` : ""}
          </button>
        ))}
      </div>

      {tab === "result" && (
        <div className="space-y-2">
          {selected.result_summary && <div className="text-[#94a3b8]">{selected.result_summary}</div>}
          {selectedResults.length > 0 && selectedResults.map(r => {
            let analysis: any = null
            try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
            return (
              <div key={r.id} className="border-t border-[#1a1a1a] pt-2">
                <a href={r.source_url || "#"} target="_blank" rel="noopener noreferrer"
                  className="text-[#4ade80] hover:text-[#6ee7b0] underline break-all font-bold">{r.source_title || r.source_url?.slice(0, 100) || "—"}</a>
                {analysis?.learnings?.length > 0 && <div className="mt-1">
                  <div className="text-[#555] text-[9px] mb-0.5">learnings:</div>
                  {analysis.learnings.map((l: string, li: number) => (
                    <div key={li} className="text-[#888] text-[9px] pl-2 leading-relaxed">· {l}</div>
                  ))}
                </div>}
                {analysis?.gaps?.length > 0 && <div className="mt-1">
                  <div className="text-[#555] text-[9px] mb-0.5">gaps:</div>
                  {analysis.gaps.map((g: string, gi: number) => (
                    <div key={gi} className="text-[#f59e0b] text-[9px] pl-2 leading-relaxed">◇ {g}</div>
                  ))}
                </div>}
                {r.raw_file_path && <div className="text-[#555] text-[8px] mt-1">saved: {r.raw_file_path}</div>}
              </div>
            )
          })}

          {/* Raw LLM response(s) */}
          {responseEntries.length > 0 && (
            <div className="border-t border-[#1a1a1a] pt-2">
              <div className="text-[#555] text-[9px] mb-1">raw response:</div>
              {responseEntries.map((entry, ei) => {
                const d = entry.event_data as any
                const resp = d?.raw_response || d?.response || JSON.stringify(d)
                if (!resp || resp === "{}") return null
                return (
                  <details key={ei} className="mb-1">
                    <summary className="text-[#777] text-[9px] cursor-pointer hover:text-[#aaa]">
                      {entry.event_type.replace("orchestrator_","").replace("_response","")} ({entry.created_at?.slice(11,19)})
                    </summary>
                    <pre className="text-[#666] text-[8px] bg-[#0c0c0c] border border-[#1a1a1a] p-2 mt-1 rounded-sm max-h-48 overflow-y-auto whitespace-pre-wrap break-all">{String(resp).slice(0, 4000)}</pre>
                  </details>
                )
              })}
            </div>
          )}

          {selectedResults.length === 0 && !selected.result_summary && responseEntries.length === 0 && (
            <div className="text-[#444] italic text-[9px]">no result data</div>
          )}
        </div>
      )}

      {tab === "input" && (
        <div className="space-y-3">
          {/* Live preview (re-fetchable) */}
          {stepPhase && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <div className="text-[#555] text-[9px]">live input preview ({stepPhase})</div>
                <button onClick={fetchLiveInput} disabled={reinitLoading}
                  className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
                  [{reinitLoading ? "…" : "⟳ reinitialize"}]
                </button>
              </div>
              {reinitLoading ? (
                <div className="text-[#555] text-[9px] animate-pulse">regenerating…</div>
              ) : liveInput ? (
                <div className="space-y-2">
                  {liveInput.objective && <div><div className="text-[#555] text-[8px]">objective:</div><div className="text-[#94a3b8] text-[9px] pl-2">{liveInput.objective}</div></div>}
                  {liveInput.max_depth != null && <div className="flex gap-3 text-[#777] text-[9px] flex-wrap"><span>depth:{liveInput.max_depth}</span><span>budget:${liveInput.budget_limit_usd?.toFixed(2)}</span>{liveInput.model && <span>model:{liveInput.model}</span>}{liveInput.temperature != null && <span>temp:{liveInput.temperature}</span>}</div>}
                  {liveInput.system_prompt && <div><div className="text-[#555] text-[8px] mb-0.5">system prompt:</div><pre className="text-[#888] text-[8px] bg-[#0c0c0c] border border-[#1a1a1a] p-2 rounded-sm max-h-32 overflow-y-auto whitespace-pre-wrap break-all">{liveInput.system_prompt}</pre></div>}
                  {liveInput.user_prompt && <div><div className="text-[#555] text-[8px] mb-0.5">user prompt:</div><pre className="text-[#888] text-[8px] bg-[#0c0c0c] border border-[#1a1a1a] p-2 rounded-sm max-h-24 overflow-y-auto whitespace-pre-wrap break-all">{liveInput.user_prompt}</pre></div>}
                  {liveInput.pending_queries && liveInput.pending_queries.length > 0 && <div><div className="text-[#555] text-[8px] mb-0.5">queries:</div>{liveInput.pending_queries.map((q,i)=><div key={i} className="text-[#94a3b8] text-[9px] pl-2">· {q}</div>)}</div>}
                  {liveInput.note && <div className="text-[#444] italic text-[8px]">{liveInput.note}</div>}
                </div>
              ) : (
                <div className="text-[#444] italic text-[9px]">click reinitialize to load</div>
              )}
            </div>
          )}

          {/* Recorded log inputs */}
          {inputEntries.length > 0 && (
            <div className="border-t border-[#1a1a1a] pt-2">
              <div className="text-[#555] text-[9px] mb-1">logged inputs ({inputEntries.length}):</div>
              <LogEntries entries={inputEntries} loading={false} emptyMsg="" />
            </div>
          )}
          {inputEntries.length === 0 && !stepPhase && (
            <div className="text-[#444] italic text-[9px]">no input data for this step</div>
          )}
        </div>
      )}

      {tab === "log" && (
        <LogEntries entries={otherEntries} loading={logLoading} emptyMsg="no additional log entries" />
      )}
    </div>
  )
}

/* ── Shared log entry renderer ── */
function LogEntries({ entries, loading, emptyMsg }: { entries: any[]; loading: boolean; emptyMsg: string }) {
  if (loading) return <div className="text-[#555] text-[9px] animate-pulse">loading…</div>
  if (entries.length === 0) return <div className="text-[#444] italic text-[9px]">{emptyMsg}</div>
  return (
    <div className="space-y-1 max-h-80 overflow-y-auto">
      {entries.map((entry, ei) => (
        <div key={ei} className="text-[9px] border-l border-[#222] pl-2">
          <div className="flex gap-1">
            <span className="text-[#f59e0b] shrink-0">{entry.event_type}</span>
            <span className="text-[#555]">{entry.created_at?.slice(11, 19)}</span>
          </div>
          {entry.event_data && typeof entry.event_data === "object" && (
            <div className="text-[#666] mt-0.5 break-all space-y-0.5">
              {/* Show relevant fields, skip huge raw_response blobs */}
              {Object.entries(entry.event_data as Record<string, any>)
                .filter(([k]) => k !== "raw_response")
                .map(([k, v]) => {
                  const val = typeof v === "string" ? v : JSON.stringify(v)
                  if (val.length > 8000) return <div key={k} className="text-[#444] italic">{k}: [too large to display]</div>
                  return <div key={k} className="text-[#777]"><span className="text-[#555]">{k}:</span> <span className="whitespace-pre-wrap break-all">{val.slice(0, 2000)}</span></div>
                })}
            </div>
          )}
        </div>
      ))}
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
/* ── Shell (§1: terminal header, §6: tab bar) ── */
function TaskPageInner({ task }: { task: ResearchTask }) {
  const [tab, setTab] = useState<SubTabId>("info")
  const [liveTask, setLiveTask] = useState(task)
  const [orchPhase, setOrchPhase] = useState(task.status === "queued" ? "planning" : "")

  useEffect(() => {
    if (task.status !== "active" && task.status !== "queued") return
    const timer = setInterval(() => {
      getResearchTask(task.id).then(t => { if (t) setLiveTask(t) }).catch(() => {})
      // Poll phase for both active and queued tasks
      getTaskPhase(task.id).then(p => {
        if (p.phase && p.phase !== "not_started") setOrchPhase(p.phase)
      }).catch(() => {})
    }, 3000)
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
          {orchPhase && orchPhase !== "complete" && (
            <span className="text-[#f59e0b] text-[9px] ml-1 uppercase shrink-0">[{orchPhase}]</span>
          )}
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
        {tab === "info"     && <InfoTab task={current} orchPhase={orchPhase} />}
        {tab === "steps"    && <StepsTab taskId={current.id} orchPhase={orchPhase} taskStatus={current.status} />}
        {tab === "assets"   && <AssetsTab task={current} />}
        {tab === "branches" && <BranchesTab task={current} />}
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
          <input type="number" value={budget} step={0.01} min={0.10} max={5.00} onChange={e => setBudget(Number(e.target.value))} className="w-16 bg-transparent border-b border-[#222]/40 text-[#94a3b8] outline-none" />
        </label>
      </div>
      <button type="submit" disabled={!objective.trim() || sending} className="text-[10px] text-[#4ade80] font-mono disabled:text-[#333] transition-colors hover:text-[#6ee7b0] cursor-pointer">[{sending ? "dispatching..." : "▶ dispatch research"}]</button>
    </form>
  )
}
