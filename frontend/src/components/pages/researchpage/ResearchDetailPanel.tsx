// ResearchDetailPanel — detail view for a selected research task.
// Tabs: Info, Steps, Meta Log, Notes, Actions.
// Fetches full task detail + meta log + steps + notes on selection.

import { memo, useState, useEffect, useCallback } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkBreaks from "remark-breaks"
import rehypeRaw from "rehype-raw"
import type { ResearchTask, MetaLogResponse, TaskStepsResponse } from "../../../api/research"
import { getResearchTask, getTaskMetaLog, getTaskSteps, getTaskNotes } from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"
import { NotesSection } from "../../shared/NotesSection"
import type { NoteInfo } from "../../../api/client"
import { wrapSelectedTextInMarks } from "../../../utils/noteHighlight"
import { ContinueResearchModal } from "./ContinueResearchModal"
import {
  STATUS_COLORS, STEP_LABELS as STEP_TYPE_LABELS, STEP_TYPE_COLORS,
  EVENT_TYPE_LABELS, EVENT_TYPE_COLORS,
} from "./constants/taskConstants"

type TabId = "info" | "steps" | "meta_log" | "notes" | "actions"

const TABS: { key: TabId; label: string }[] = [
  { key: "info",     label: "Info" },
  { key: "steps",    label: "Steps" },
  { key: "meta_log", label: "Meta Log" },
  { key: "notes",    label: "Notes" },
  { key: "actions",  label: "Actions" },
]

interface Props {
  task: ResearchTask
  onApprove?: (id: string) => Promise<void>
  onReject?: (id: string) => Promise<void>
  onCancel?: (id: string) => Promise<void>
}

/* ── Info Tab — metrics + highlighted result summary ── */
function InfoTab({ task, notes }: { task: ResearchTask; notes: NoteInfo[] }) {
  const color = STATUS_COLORS[task.status] ?? "var(--color-ui-dim)"
  const progress = task.budget_limit_usd > 0
    ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100)
    : 0

  const metrics = [
    { key: "id", value: task.id.slice(0, 12) + "…" },
    { key: "status", value: task.status, valueColor: color },
    { key: "trigger", value: task.trigger_source },
    { key: "depth", value: task.max_depth },
    { key: "breadth", value: task.max_breadth },
    { key: "agonistic", value: task.is_agonistic ? "yes" : "no", valueColor: task.is_agonistic ? "var(--color-semantic-gold)" : undefined },
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
    <div className="space-y-3 font-mono">
      <div>
        <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1">[ Objective ]</div>
        <div className="text-ui-primary text-[10px] leading-relaxed font-sans">{task.objective}</div>
      </div>
      <div>
        <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1">[ Metrics ]</div>
        <KeyValueGrid items={metrics} />
      </div>
      {task.proposal_rationale && (
        <div>
          <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1">[ Rationale ]</div>
          <div className="text-ui-dim text-[10px] leading-relaxed font-sans">{task.proposal_rationale}</div>
        </div>
      )}
      {task.result_summary && (
        <div>
          <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1">[ Result Summary ]</div>
          <div className="text-ui-primary text-[10px] leading-relaxed max-h-48 overflow-y-auto prose prose-invert prose-xs max-w-none font-sans">
            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} rehypePlugins={[rehypeRaw]}>
              {wrapSelectedTextInMarks(task.result_summary, notes)}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Steps Tab (Orchestrator) ── */
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
    return <div className="text-ui-dim animate-pulse text-xs font-mono mt-4">[ loading steps… ]</div>
  }

  if (!data || data.steps.length === 0) {
    return <div className="text-ui-dim italic text-xs text-center mt-8 select-none font-mono">[ no orchestrator steps — legacy engine ]</div>
  }

  const planParsed = data.plan ? (() => { try { return JSON.parse(data.plan.plan_json) } catch { return null } })() : null

  return (
    <div className="space-y-2 font-mono">
      {planParsed && (
        <div className="text-ui-dim text-[9px] pb-1 border-b border-ui-border">
          goal: {planParsed.goal || "—"} · queries: {(planParsed.search_queries || []).length} · est. depth: {planParsed.estimated_depth || "—"}
        </div>
      )}

      {[...data.steps].reverse().map((step) => {
        const sc = STEP_TYPE_COLORS[step.step_type] || "var(--color-ui-dim)"
        const label = STEP_TYPE_LABELS[step.step_type] || step.step_type
        const isExpanded = expandedStep === step.id
        const results = data.results_by_step[step.id] || []

        return (
          <div key={step.id} className="border-l-2 border-ui-border/40 pl-2 py-1">
            <div
              className="flex items-center gap-1.5 cursor-pointer select-none"
              onClick={() => setExpandedStep(isExpanded ? null : step.id)}
            >
              <span style={{ color: sc }} className="text-[8px] shrink-0">●</span>
              <span className="text-ui-secondary text-[10px]">
                #{step.step_number} {label}
              </span>
              <span style={{ color: sc }} className="text-[8px] ml-auto uppercase">{step.status}</span>
              {results.length > 0 && (
                <span className="text-ui-dim text-[8px]">{isExpanded ? "▼" : "▶"}</span>
              )}
            </div>

            {step.result_summary && (
              <div className="text-ui-dim text-[9px] ml-3.5 leading-relaxed">{step.result_summary}</div>
            )}

            {isExpanded && results.length > 0 && (
              <div className="ml-3.5 mt-1 space-y-1">
                {results.map((r, i) => {
                  let analysis: any = null
                  try { analysis = r.analyzed_json ? JSON.parse(r.analyzed_json) : null } catch {}
                  return (
                    <div key={r.id || i} className="text-[9px]">
                      <div className="text-ui-dim break-all">
                        <a
                          href={r.source_url || "#"}
                          target="_blank" rel="noopener noreferrer"
                          className="text-action-dim hover:text-action-hover underline transition-colors"
                        >
                          {r.source_title || r.source_url?.slice(0, 60) || "—"}
                        </a>
                      </div>
                      {analysis?.learnings && (
                        <div className="text-ui-secondary mt-0.5 space-y-0.5">
                          {(analysis.learnings as string[]).slice(0, 3).map((l, li) => (
                            <div key={li} className="pl-2">· {l}</div>
                          ))}
                          {analysis.learnings.length > 3 && (
                            <div className="text-ui-dim pl-2">…{analysis.learnings.length - 3} more</div>
                          )}
                        </div>
                      )}
                      {r.raw_file_path && (
                        <div className="text-ui-dim text-[8px] mt-0.5">saved: {r.raw_file_path}</div>
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
    return <div className="text-ui-dim animate-pulse text-xs font-mono mt-4">[ loading meta log… ]</div>
  }

  if (!meta || meta.entries.length === 0) {
    return <div className="text-ui-dim italic text-xs text-center mt-8 select-none font-mono">[ no meta events recorded yet ]</div>
  }

  const toggle = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id) } else { next.add(id) }
      return next
    })
  }

  return (
    <div className="space-y-0.5 font-mono">
      <div className="text-ui-dim text-[9px] pb-1 flex items-center gap-2">
        {meta.count} event{meta.count !== 1 ? "s" : ""}
      </div>
      {[...meta.entries].reverse().map((entry) => {
        const label = EVENT_TYPE_LABELS[entry.event_type] || entry.event_type
        const ec = EVENT_TYPE_COLORS[entry.event_type] || "var(--color-ui-dim)"
        const isExpanded = expanded.has(entry.id)
        const hasData = entry.event_data && Object.keys(entry.event_data).length > 0

        return (
          <div key={entry.id} className="border-l-2 border-ui-border/40 pl-2 py-1">
            <div
              className="flex items-center gap-1.5 cursor-pointer select-none"
              onClick={() => hasData && toggle(entry.id)}
            >
              <span style={{ color: ec }} className="text-[8px] shrink-0">●</span>
              <span className="text-ui-secondary text-[10px]">{label}</span>
              <span className="text-ui-dim text-[8px] ml-auto">{entry.created_at?.slice(11, 19) || ""}</span>
              {hasData && (
                <span className="text-ui-dim text-[8px]">{isExpanded ? "▼" : "▶"}</span>
              )}
            </div>
            {entry.branch_id && (
              <div className="text-ui-dim text-[8px] ml-3.5">
                branch: {entry.branch_id.slice(0, 8)}…
              </div>
            )}
            {isExpanded && hasData && (
              <div className="ml-3.5 mt-1 text-[9px] text-ui-secondary max-h-96 overflow-y-auto font-mono whitespace-pre-wrap break-all leading-relaxed">
                {Object.entries(entry.event_data).map(([k, v]) => {
                  const val = typeof v === "string" ? v : JSON.stringify(v, null, 1)
                  return (
                    <div key={k} className="mb-0.5">
                      <span className="text-ui-dim">{k}: </span>
                      <span className="text-ui-secondary">{val}</span>
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
  const [showContinue, setShowContinue] = useState(false)
  const retry = () => window.dispatchEvent(new CustomEvent("research-retry", { detail: task }))
  const continueResearch = () => setShowContinue(true)

  return (
    <div className="space-y-3 font-mono">
      <div>
        <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1">[ Actions ]</div>
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
      {showContinue && (
        <ContinueResearchModal task={task} onClose={() => setShowContinue(false)} />
      )}
      <div>
        <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1">[ Timeline ]</div>
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

/* ── Notes Tab ── */
function NotesTab({
  taskId, onNavigate,
}: {
  taskId: string
  onNavigate?: (noteId: string, targetTab: TabId) => void
}) {
  const [notes, setNotes] = useState<NoteInfo[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    import("../../../api/research")
      .then(({ getTaskNotes }) => getTaskNotes(taskId))
      .then((data) => { if (!cancelled) setNotes(data) })
      .catch(() => { if (!cancelled) setNotes([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [taskId])

  if (loading) {
    return <div className="text-ui-dim animate-pulse text-xs font-mono mt-4">[ loading notes… ]</div>
  }

  return (
    <NotesSection
      notes={notes}
      onNavigate={(noteId) => {
        if (onNavigate) onNavigate(noteId, "info")
      }}
    />
  )
}

/* ── Shell: Tab bar + content ── */
export const ResearchDetailPanel = memo(function ResearchDetailPanel({
  task: initialTask, onApprove, onReject, onCancel,
}: Props) {
  const [task, setTask] = useState<ResearchTask>(initialTask)
  const [detailLoading, setDetailLoading] = useState(false)
  const [notes, setNotes] = useState<NoteInfo[]>([])

  const loadNotes = useCallback((tid: string) => {
    getTaskNotes(tid).then(setNotes).catch(() => setNotes([]))
  }, [])

  useEffect(() => {
    setTask(initialTask)
    setDetailLoading(true)
    getResearchTask(initialTask.id)
      .then(full => setTask(full))
      .catch(() => {})
      .finally(() => setDetailLoading(false))
    loadNotes(initialTask.id)
  }, [initialTask.id])

  const [tab, setTab] = useState<TabId>("info")

  const handleNotesNavigate = (noteId: string, targetTab: TabId) => {
    setTab(targetTab)
    setTimeout(() => {
      import("../../../utils/noteHighlight")
        .then(({ scrollToNoteHighlight }) => scrollToNoteHighlight(noteId))
        .catch(() => {})
    }, 150)
  }

  return (
    <div className="flex flex-col h-full min-h-0 px-2 font-mono">
      {/* Tab bar (§6: • dot-separated, no border) */}
      <div className="flex flex-wrap gap-x-1 gap-y-1 mb-3 text-[10px] select-none">
        {TABS.map((t, i) => (
          <span key={t.key} className="flex items-center gap-x-1 whitespace-nowrap">
            {i > 0 && <span className="text-ui-border">•</span>}
            <button
              onClick={() => setTab(t.key)}
              className={`cursor-pointer transition-colors ${tab === t.key ? "text-ui-primary" : "text-ui-dim hover:text-ui-secondary"}`}
            >
              {t.label}
            </button>
          </span>
        ))}
        {detailLoading && <span className="text-ui-dim ml-1 animate-pulse">…</span>}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto pr-1">
        {tab === "info"     && <InfoTab task={task} notes={notes} />}
        {tab === "steps"    && <StepsTab taskId={task.id} />}
        {tab === "meta_log" && <MetaLogTab taskId={task.id} />}
        {tab === "notes"    && <NotesTab taskId={task.id} onNavigate={handleNotesNavigate} />}
        {tab === "actions"  && <ActionsTab task={task} onApprove={onApprove} onReject={onReject} onCancel={onCancel} />}
      </div>
    </div>
  )
})
