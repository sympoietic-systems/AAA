// ResearchDetailPanel — detail view for a selected research task.
// Tabs: Info, Assets, Branches, Actions, Meta Log.
// Fetches full task detail + meta log on selection (§2: self-supporting).
// Follows FRONTEND_DESIGN_PRINCIPLES.md §6: tabbed content, inline metadata, bracket headers.

import React, { memo, useState, useEffect } from "react"
import type { ResearchTask, MetaLogEntry, MetaLogResponse } from "../../../api/research"
import { getResearchTask, getTaskMetaLog } from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"

type TabId = "info" | "assets" | "branches" | "meta_log" | "actions"

const TABS: { key: TabId; label: string }[] = [
  { key: "info",     label: "Info" },
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
          <div className="text-[#94a3b8] text-[10px] leading-relaxed max-h-48 overflow-y-auto">{task.result_summary}</div>
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
    return <div className="text-[#444] italic text-xs text-center mt-8 select-none">[ no branches recorded ]</div>
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
      if (next.has(id)) next.delete(id) else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-0.5">
      <div className="text-[#555] text-[9px] pb-1 flex items-center gap-2">
        {meta.count} event{meta.count !== 1 ? "s" : ""}
      </div>
      {meta.entries.map((entry) => {
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
              <div className="ml-3.5 mt-1 text-[9px] text-[#777] max-h-40 overflow-y-auto font-mono whitespace-pre-wrap break-all leading-relaxed">
                {Object.entries(entry.event_data).map(([k, v]) => {
                  const val = typeof v === "string" ? v : JSON.stringify(v, null, 1)
                  // Truncate very large content previews
                  const display = val.length > 300 ? val.slice(0, 300) + "…" : val
                  return (
                    <div key={k} className="mb-0.5">
                      <span className="text-[#555]">{k}: </span>
                      <span className="text-[#888]">{display}</span>
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
            <TerminalButton onClick={retry} intent="edit">↻ retry task</TerminalButton>
          )}
          {task.status === "completed" && (
            <TerminalButton onClick={retry} intent="save">↻ retry research</TerminalButton>
          )}
          {["cancelled", "rejected"].includes(task.status) && (
            <span className="text-[#555] italic text-[10px]">no actions — task is {task.status}</span>
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
        {tab === "assets"   && <AssetsTab task={task} />}
        {tab === "branches" && <BranchesTab task={task} />}
        {tab === "meta_log" && <MetaLogTab taskId={task.id} />}
        {tab === "actions"  && <ActionsTab task={task} onApprove={onApprove} onReject={onReject} onCancel={onCancel} />}
      </div>
    </div>
  )
})
