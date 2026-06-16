// ResearchDetailPanel — detail view for a selected research task.
// Tabs: Info, Steps, Assets, Branches, Meta Log, Actions.
// Fetches full task detail + meta log + steps on selection (§2: self-supporting).
// Follows FRONTEND_DESIGN_PRINCIPLES.md §6: tabbed content, inline metadata, bracket headers.

import React, { memo, useState, useEffect } from "react"
import ReactMarkdown from "react-markdown"
import type { ResearchTask, MetaLogEntry, MetaLogResponse, TaskStepsResponse, ResearchStep } from "../../../api/research"
import { getResearchTask, getTaskMetaLog, getTaskSteps } from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"

type TabId = "info" | "steps" | "assets" | "branches" | "meta_log" | "actions"

const TABS: { key: TabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "assets",   label: "Assets" },
  { key: "branches", label: "Branches" },
  { key: "meta_log", label: "Meta Log" },
  { key: "actions",  label: "Actions" },
]

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

const EVENT_TYPE_LABELS: Record<string, string> = {
  task_started: "Task Started",
  task_complete: "Task Complete",
  query_generation: "Query Generation",
  branch_create: "Branch Created",
  fetch_complete: "Fetch Complete",
  fetch_error: "Fetch Error",
  llm_prompt: "LLM Prompt",
  llm_response: "LLM Response",
  llm_error: "LLM Error",
  synthesis_start: "Synthesis Start",
  synthesis_complete: "Synthesis Complete",
  synthesis_error: "Synthesis Error",
  orchestrator_start: "Orch Start",
  orchestrator_plan: "Plan Result",
  orchestrator_plan_prompt: "Plan Prompt",
  orchestrator_plan_response: "Plan Response",
  orchestrator_replan: "Re-Plan",
  orchestrator_search: "Search",
  orchestrator_digest_prompt: "Digest Prompt",
  orchestrator_digest_response: "Digest Response",
  orchestrator_digest_error: "Digest Error",
  orchestrator_reflect: "Reflect Result",
  orchestrator_reflect_prompt: "Reflect Prompt",
  orchestrator_reflect_response: "Reflect Response",
  orchestrator_evaluate: "Evaluate",
  orchestrator_synthesize_start: "Synthesize Start",
  orchestrator_synthesize_prompt: "Synthesize Prompt",
  orchestrator_synthesize_response: "Synthesize Response",
  orchestrator_complete: "Orch Complete",
  orchestrator_step_complete: "Step Done",
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  task_started: "#4ade80",
  task_complete: "#22d3ee",
  query_generation: "#a78bfa",
  branch_create: "#f59e0b",
  fetch_complete: "#3b82f6",
  fetch_error: "#ef4444",
  llm_prompt: "#c084fc",
  llm_response: "#a892ee",
  llm_error: "#ef4444",
  synthesis_start: "#facc15",
  synthesis_complete: "#4ade80",
  synthesis_error: "#ef4444",
  orchestrator_start: "#4ade80",
  orchestrator_plan: "#a78bfa",
  orchestrator_plan_prompt: "#c084fc",
  orchestrator_plan_response: "#a892ee",
  orchestrator_replan: "#f59e0b",
  orchestrator_search: "#3b82f6",
  orchestrator_digest_prompt: "#c084fc",
  orchestrator_digest_response: "#a892ee",
  orchestrator_digest_error: "#ef4444",
  orchestrator_reflect: "#a78bfa",
  orchestrator_reflect_prompt: "#c084fc",
  orchestrator_reflect_response: "#a892ee",
  orchestrator_evaluate: "#22d3ee",
  orchestrator_synthesize_start: "#facc15",
  orchestrator_synthesize_prompt: "#c084fc",
  orchestrator_synthesize_response: "#a892ee",
  orchestrator_complete: "#22d3ee",
  orchestrator_step_complete: "#4ade80",
}

interface Props {
  task: ResearchTask
  onApprove?: (id: string) => Promise<void>
  onReject?: (id: string) => Promise<void>
  onCancel?: (id: string) => Promise<void>
}

/* ── Info Tab (§6: inline key:value via KeyValueGrid, bracket headers) ── */
function InfoTab({ task }: { task: ResearchTask }) {
  const color = STATUS_COLORS[task.status] ?? "#666"
  const progress = task.budget_limit_usd > 0
    ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100)
    : 0

  const metrics = [
    { key: "id", value: task.id.slice(0, 12) + "…" },
    { key: "status", value: task.status, valueColor: color },
    { key: "trigger", value: task.trigger_source },
    { key: "depth", value: task.max_depth },
    { key: "breadth", value: task.max_breadth },
    { key: "agonistic", value: task.is_agonistic ? "yes" : "no", valueColor: task.is_agonistic ? "#f59e0b" : undefined },
    { key: "branches", value: task.branches_created },
    { key: "assets", value: task.assets_harvested || (task.assets?.length ?? 0) },
    { key: "flights", value: task.lateral_flights },
    { key: "bifurcations", value: task.bifurcation_triggered },
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
      {task.proposal_rationale && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Rationale ]</div>
          <div className="text-[#777] text-[10px] leading-relaxed">{task.proposal_rationale}</div>
        </div>
      )}
      {task.result_summary && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Result Summary ]</div>
          <div className="text-[#94a3b8] text-[10px] leading-relaxed max-h-48 overflow-y-auto prose prose-invert prose-xs max-w-none">
            <ReactMarkdown>{task.result_summary}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Assets Tab ── */
function AssetsTab({ task }: { task: ResearchTask }) {
  const assets = task.assets ?? []
  if (assets.length === 0) {
    return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no assets harvested ]</div>
  }
  return (
    <div className="space-y-1">
      <div className="text-[#555] text-[9px] pb-1">{assets.length} asset{assets.length !== 1 ? "s" : ""}</div>
      {assets.map((a, i) => (
        <div key={a.id || i} className="py-1">
          <div className="text-[#94a3b8] text-[10px] break-all leading-relaxed">
            {a.url.startsWith("http") ? (
              <a href={a.url} target="_blank" rel="noopener noreferrer" className="text-[#4ade80] hover:text-[#6ee7b0] underline">{a.url}</a>
            ) : (
              <span className="text-[#888]">{a.url}</span>
            )}
          </div>
          <KeyValueGrid className="text-[9px] mt-0.5" items={[
            { key: "rel", value: (a.relevance_score ?? 0).toFixed(2), valueColor: "#4ade80" },
            { key: "nov", value: (a.novelty_score ?? 0).toFixed(2) },
            { key: "dif", value: (a.diffractive_score ?? 0).toFixed(2) },
          ]} />
        </div>
      ))}
    </div>
  )
}

/* ── Branches Tab ── */
function BranchesTab({ task }: { task: ResearchTask }) {
  const branches = task.branches ?? []
  if (branches.length === 0) {
    return <div className="text-[#444] italic text-xs text-center mt-8 select-none">
      [ no branches recorded — orchestrator uses Steps instead ]
    </div>
  }
  return (
    <div className="space-y-1">
      <div className="text-[#555] text-[9px] pb-1">{branches.length} branch{branches.length !== 1 ? "es" : ""}</div>
      {branches.map((b: any, i: number) => {
        const sc = STATUS_COLORS[b.status] ?? "#666"
        return (
          <div key={b.id || i} className="py-1">
            <div className="flex items-center gap-1.5">
              <span style={{ color: sc }} className="text-[9px]">●</span>
              <span className="text-[#bbb] text-[10px] truncate">{b.query || b.id?.slice(0, 12)}</span>
              <span style={{ color: sc }} className="text-[8px] uppercase">{b.status}</span>
            </div>
            <KeyValueGrid className="text-[9px] mt-0.5 ml-3.5" items={[
              { key: "depth", value: b.depth ?? 0 },
              { key: "children", value: b.children_created ?? 0 },
              { key: "assets", value: b.assets_harvested ?? 0 },
            ]} />
          </div>
        )
      })}
    </div>
  )
}

/* ── Steps Tab (Orchestrator) ── */
const STEP_TYPE_LABELS: Record<string, string> = {
  search: "Search",
  parallel_parse: "Parse Sources",
  digest: "Digest",
  reflect: "Reflect",
  synthesize: "Synthesize",
  evaluate: "Evaluate",
}
const STEP_TYPE_COLORS: Record<string, string> = {
  search: "#3b82f6",
  parallel_parse: "#f59e0b",
  digest: "#a892ee",
  reflect: "#c084fc",
  synthesize: "#4ade80",
  evaluate: "#22d3ee",
}

const EMPTY_STEPS: TaskStepsResponse = { task_id: "", plan: null, steps: [], results_by_step: {} }

function StepsTab({ taskId }: { taskId: string }) {
  const [data, setData] = useState<TaskStepsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [expandedStep, setExpandedStep] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getTaskSteps(taskId)
      .then(d => { if (!cancelled) setData(d) })
      .catch(() => { if (!cancelled) setData(EMPTY_STEPS) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [taskId])

  if (loading) {
    return <div className="text-[#555] animate-pulse text-xs font-mono mt-4">[ loading steps… ]</div>
  }

  if (!data || data.steps.length === 0) {
    return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no orchestrator steps — legacy engine ]</div>
  }

  // Show plan info if available
  const planParsed = data.plan ? (() => { try { return JSON.parse(data.plan.plan_json) } catch { return null } })() : null

  return (
    <div className="space-y-2">
      {planParsed && (
        <div className="text-[#555] text-[9px] pb-1 border-b border-[#1a1a1a]">
          goal: {planParsed.goal || "—"} · queries: {(planParsed.search_queries || []).length} · est. depth: {planParsed.estimated_depth || "—"}
        </div>
      )}

      {[...data.steps].reverse().map((step) => {
        const sc = STEP_TYPE_COLORS[step.step_type] || "#666"
        const label = STEP_TYPE_LABELS[step.step_type] || step.step_type
        const isExpanded = expandedStep === step.id
        const results = data.results_by_step[step.id] || []

        return (
          <div key={step.id} className="border-l-2 border-[#222]/40 pl-2 py-1">
            <div
              className="flex items-center gap-1.5 cursor-pointer select-none"
              onClick={() => setExpandedStep(isExpanded ? null : step.id)}
            >
              <span style={{ color: sc }} className="text-[8px] shrink-0">●</span>
              <span className="text-[#bbb] text-[10px]">
                #{step.step_number} {label}
              </span>
              <span style={{ color: sc }} className="text-[8px] ml-auto uppercase">{step.status}</span>
              {results.length > 0 && (
                <span className="text-[#555] text-[8px]">{isExpanded ? "▼" : "▶"}</span>
              )}
            </div>

            {step.result_summary && (
              <div className="text-[#555] text-[9px] ml-3.5">{step.result_summary}</div>
            )}

            {isExpanded && results.length > 0 && (
              <div className="ml-3.5 mt-1 space-y-1">
                {results.map((r, i) => {
                  let analysis: any = null
                  try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
                  return (
                    <div key={r.id || i} className="text-[9px]">
                      <div className="text-[#777] break-all">
                        <a
                          href={r.source_url || "#"}
                          target="_blank" rel="noopener noreferrer"
                          className="text-[#4ade80] hover:text-[#6ee7b0] underline"
                        >
                          {r.source_title || r.source_url?.slice(0, 60) || "—"}
                        </a>
                      </div>
                      {analysis?.learnings && (
                        <div className="text-[#888] mt-0.5 space-y-0.5">
                          {(analysis.learnings as string[]).slice(0, 3).map((l, li) => (
                            <div key={li} className="pl-2">· {l}</div>
                          ))}
                          {analysis.learnings.length > 3 && (
                            <div className="text-[#555]">…{analysis.learnings.length - 3} more</div>
                          )}
                        </div>
                      )}
                      {r.raw_file_path && (
                        <div className="text-[#555] text-[8px]">saved: {r.raw_file_path}</div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ── Meta Log Tab ── */
const EMPTY_META: MetaLogResponse = { task_id: "", title: "", status: "", entries: [], count: 0 }

function MetaLogTab({ taskId }: { taskId: string }) {
  const [meta, setMeta] = useState<MetaLogResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getTaskMetaLog(taskId)
      .then(data => { if (!cancelled) setMeta(data) })
      .catch(() => { if (!cancelled) setMeta(EMPTY_META) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [taskId])

  if (loading) {
    return <div className="text-[#555] animate-pulse text-xs font-mono mt-4">[ loading meta log… ]</div>
  }

  if (!meta || meta.entries.length === 0) {
    return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no meta events recorded yet ]</div>
  }

  const toggle = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id) } else { next.add(id) }
      return next
    })
  }

  return (
    <div className="space-y-0.5">
      <div className="text-[#555] text-[9px] pb-1 flex items-center gap-2">
        {meta.count} event{meta.count !== 1 ? "s" : ""}
      </div>
      {[...meta.entries].reverse().map((entry) => {
        const label = EVENT_TYPE_LABELS[entry.event_type] || entry.event_type
        const ec = EVENT_TYPE_COLORS[entry.event_type] || "#666"
        const isExpanded = expanded.has(entry.id)
        const hasData = entry.event_data && Object.keys(entry.event_data).length > 0

        return (
          <div key={entry.id} className="border-l-2 border-[#222]/40 pl-2 py-1">
            <div
              className="flex items-center gap-1.5 cursor-pointer select-none"
              onClick={() => hasData && toggle(entry.id)}
            >
              <span style={{ color: ec }} className="text-[8px] shrink-0">●</span>
              <span className="text-[#bbb] text-[10px]">{label}</span>
              <span className="text-[#555] text-[8px] ml-auto">{entry.created_at?.slice(11, 19) || ""}</span>
              {hasData && (
                <span className="text-[#555] text-[8px]">{isExpanded ? "▼" : "▶"}</span>
              )}
            </div>
            {entry.branch_id && (
              <div className="text-[#555] text-[8px] ml-3.5">
                branch: {entry.branch_id.slice(0, 8)}…
              </div>
            )}
            {isExpanded && hasData && (
              <div className="ml-3.5 mt-1 text-[9px] text-[#777] max-h-96 overflow-y-auto font-mono whitespace-pre-wrap break-all leading-relaxed">
                {Object.entries(entry.event_data).map(([k, v]) => {
                  const val = typeof v === "string" ? v : JSON.stringify(v, null, 1)
                  return (
                    <div key={k} className="mb-0.5">
                      <span className="text-[#555]">{k}: </span>
                      <span className="text-[#888]">{val}</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ── Actions Tab ── */
function ActionsTab({
  task, onApprove, onReject, onCancel,
}: {
  task: ResearchTask
  onApprove?: (id: string) => Promise<void>
  onReject?: (id: string) => Promise<void>
  onCancel?: (id: string) => Promise<void>
}) {
  const retry = () => window.dispatchEvent(new CustomEvent("research-retry", { detail: task }))
  const continueResearch = () => window.dispatchEvent(new CustomEvent("research-continue", { detail: task }))

  return (
    <div className="space-y-3">
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">[ Actions ]</div>
        <div className="flex flex-wrap gap-2">
          {task.status === "proposed" && (
            <>
              {onApprove && <TerminalButton onClick={() => onApprove(task.id)} intent="save">✓ approve & dispatch</TerminalButton>}
              {onReject && <TerminalButton onClick={() => onReject(task.id)} intent="delete">✗ dismiss</TerminalButton>}
            </>
          )}
          {(task.status === "queued" || task.status === "active") && onCancel && (
            <TerminalButton onClick={() => onCancel(task.id)} intent="delete">✕ cancel task</TerminalButton>
          )}
          {task.status === "failed" && (
            <>
              <TerminalButton onClick={retry} intent="edit">↻ retry task</TerminalButton>
              <TerminalButton onClick={continueResearch} intent="cyan">▶ continue deeper</TerminalButton>
            </>
          )}
          {task.status === "completed" && (
            <>
              <TerminalButton onClick={retry} intent="save">↻ retry research</TerminalButton>
              <TerminalButton onClick={continueResearch} intent="cyan">▶ continue deeper</TerminalButton>
            </>
          )}
          {task.status === "cancelled" && (
            <>
              <TerminalButton onClick={retry} intent="edit">↻ retry task</TerminalButton>
              <TerminalButton onClick={continueResearch} intent="cyan">▶ continue deeper</TerminalButton>
              <TerminalButton onClick={() => window.dispatchEvent(new CustomEvent("research-delete", { detail: task }))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {task.status === "rejected" && (
            <>
              <TerminalButton onClick={() => window.dispatchEvent(new CustomEvent("research-delete", { detail: task }))} intent="delete">✕ delete</TerminalButton>
            </>
          )}
          {["completed", "failed"].includes(task.status) && (
            <TerminalButton onClick={() => window.dispatchEvent(new CustomEvent("research-delete", { detail: task }))} intent="delete">✕ delete</TerminalButton>
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

/* ── Shell: Tab bar + content (§6) ── */
export const ResearchDetailPanel = memo(function ResearchDetailPanel({
  task: initialTask, onApprove, onReject, onCancel,
}: Props) {
  const [task, setTask] = useState<ResearchTask>(initialTask)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    setTask(initialTask)
    setDetailLoading(true)
    getResearchTask(initialTask.id)
      .then(full => setTask(full))
      .catch(() => {})
      .finally(() => setDetailLoading(false))
  }, [initialTask.id])

  const [tab, setTab] = useState<TabId>(() => {
    const assets = initialTask.assets ?? []
    if (assets.length > 0) return "assets"
    return "info"
  })

  return (
    <div className="flex flex-col h-full min-h-0 px-2">
      {/* Tab bar (§6: • dot-separated, no border) */}
      <div className="flex flex-wrap gap-x-1 gap-y-1 mb-3 text-[10px] select-none">
        {TABS.map((t, i) => (
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
        {detailLoading && <span className="text-[#555] ml-1 animate-pulse">…</span>}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto pr-1">
        {tab === "info"     && <InfoTab task={task} />}
        {tab === "steps"    && <StepsTab taskId={task.id} />}
        {tab === "assets"   && <AssetsTab task={task} />}
        {tab === "branches" && <BranchesTab task={task} />}
        {tab === "meta_log" && <MetaLogTab taskId={task.id} />}
        {tab === "actions"  && <ActionsTab task={task} onApprove={onApprove} onReject={onReject} onCancel={onCancel} />}
      </div>
    </div>
  )
})
