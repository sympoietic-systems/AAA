// ResearchDetailPanel — detail view for a selected research task.
// Tabs: Info, Assets, Branches, Actions.
// Fetches full task detail (with branches) on selection (§2: self-supporting).
// Follows FRONTEND_DESIGN_PRINCIPLES.md §6: tabbed content, inline metadata, bracket headers.

import React, { memo, useState, useEffect } from "react"
import type { ResearchTask } from "../../../api/research"
import { getResearchTask } from "../../../api/research"
import { KeyValueGrid, TerminalButton } from "../../UI"

type TabId = "info" | "assets" | "branches" | "actions"

const TABS: { key: TabId; label: string }[] = [
  { key: "info",    label: "Info" },
  { key: "assets",  label: "Assets" },
  { key: "branches", label: "Branches" },
  { key: "actions", label: "Actions" },
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
      {/* Objective (§6: bracket header) */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
          [ Objective ]
        </div>
        <div className="text-[#94a3b8] text-[10px] leading-relaxed">{task.objective}</div>
      </div>

      {/* Metrics (§6: inline KeyValueGrid) */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
          [ Metrics ]
        </div>
        <KeyValueGrid items={metrics} />
      </div>

      {/* Rationale */}
      {task.proposal_rationale && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
            [ Rationale ]
          </div>
          <div className="text-[#777] text-[10px] leading-relaxed">{task.proposal_rationale}</div>
        </div>
      )}

      {/* Result Summary */}
      {task.result_summary && (
        <div>
          <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
            [ Result Summary ]
          </div>
          <div className="text-[#94a3b8] text-[10px] leading-relaxed max-h-48 overflow-y-auto">
            {task.result_summary}
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Assets Tab (§6: bracket header, plain list) ── */
function AssetsTab({ task }: { task: ResearchTask }) {
  const assets = task.assets ?? []

  if (assets.length === 0) {
    return (
      <div className="text-[#444] italic text-xs text-center mt-8 select-none">
        [ no assets harvested ]
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="text-[#555] text-[9px] pb-1">
        {assets.length} asset{assets.length !== 1 ? "s" : ""}
      </div>
      {assets.map((a, i) => (
        <div key={a.id || i} className="py-1">
          <div className="text-[#94a3b8] text-[10px] break-all leading-relaxed">
            {a.url.startsWith("http") ? (
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#4ade80] hover:text-[#6ee7b0] underline"
              >
                {a.url}
              </a>
            ) : (
              <span className="text-[#888]">{a.url}</span>
            )}
          </div>
          <KeyValueGrid
            className="text-[9px] mt-0.5"
            items={[
              { key: "rel", value: (a.relevance_score ?? 0).toFixed(2), valueColor: "#4ade80" },
              { key: "nov", value: (a.novelty_score ?? 0).toFixed(2) },
              { key: "dif", value: (a.diffractive_score ?? 0).toFixed(2) },
            ]}
          />
        </div>
      ))}
    </div>
  )
}

/* ── Branches Tab (§6: bracket header, plain list) ── */
function BranchesTab({ task }: { task: ResearchTask }) {
  const branches = task.branches ?? []

  if (branches.length === 0) {
    return (
      <div className="text-[#444] italic text-xs text-center mt-8 select-none">
        [ no branches recorded ]
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="text-[#555] text-[9px] pb-1">
        {branches.length} branch{branches.length !== 1 ? "es" : ""}
      </div>
      {branches.map((b: any, i: number) => {
        const statusColor = STATUS_COLORS[b.status] ?? "#666"
        return (
          <div key={b.id || i} className="py-1">
            <div className="flex items-center gap-1.5">
              <span style={{ color: statusColor }} className="text-[9px]">●</span>
              <span className="text-[#bbb] text-[10px] truncate">{b.query || b.id?.slice(0, 12)}</span>
              <span style={{ color: statusColor }} className="text-[8px] uppercase">{b.status}</span>
            </div>
            <KeyValueGrid
              className="text-[9px] mt-0.5 ml-3.5"
              items={[
                { key: "depth", value: b.depth ?? 0 },
                { key: "children", value: b.children_created ?? 0 },
                { key: "assets", value: b.assets_harvested ?? 0 },
              ]}
            />
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
  return (
    <div className="space-y-3">
      {/* Actions */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
          [ Actions ]
        </div>
        <div className="flex flex-wrap gap-2">
          {task.status === "proposed" && (
            <>
              {onApprove && (
                <TerminalButton onClick={() => onApprove(task.id)} intent="save">
                  ✓ approve & dispatch
                </TerminalButton>
              )}
              {onReject && (
                <TerminalButton onClick={() => onReject(task.id)} intent="delete">
                  ✗ dismiss
                </TerminalButton>
              )}
            </>
          )}

          {(task.status === "queued" || task.status === "active") && onCancel && (
            <TerminalButton onClick={() => onCancel(task.id)} intent="delete">
              ✕ cancel task
            </TerminalButton>
          )}

          {task.status === "failed" && (
            <TerminalButton
              onClick={() => window.dispatchEvent(new CustomEvent("research-retry", { detail: task }))}
              intent="edit"
            >
              ↻ retry task
            </TerminalButton>
          )}

          {["completed", "cancelled", "rejected"].includes(task.status) && (
            <span className="text-[#555] italic text-[10px]">
              no actions — task is {task.status}
            </span>
          )}
        </div>
      </div>

      {/* Timestamps (§6: bracket header + KeyValueGrid) */}
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1">
          [ Timeline ]
        </div>
        <KeyValueGrid
          items={[
            ...(task.proposed_at ? [{ key: "proposed", value: task.proposed_at }] : []),
            ...(task.approved_at ? [{ key: "approved", value: task.approved_at }] : []),
            ...(task.started_at ? [{ key: "started", value: task.started_at }] : []),
            ...(task.completed_at ? [{ key: "completed", value: task.completed_at }] : []),
          ]}
        />
      </div>
    </div>
  )
}

/* ── Shell: Tab bar + content (§6) ── */
export const ResearchDetailPanel = memo(function ResearchDetailPanel({
  task: initialTask, onApprove, onReject, onCancel,
}: Props) {
  // §2: Self-supporting — fetch full detail (with branches) on selection
  const [task, setTask] = useState<ResearchTask>(initialTask)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    setTask(initialTask)
    setDetailLoading(true)
    getResearchTask(initialTask.id)
      .then(full => setTask(full))
      .catch(() => { /* keep initialTask as fallback */ })
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
              className={`cursor-pointer transition-colors ${
                tab === t.key
                  ? "text-[#94a3b8]"
                  : "text-[#444] hover:text-[#777]"
              }`}
            >
              {t.label}
            </button>
          </span>
        ))}
        {detailLoading && <span className="text-[#555] ml-1 animate-pulse">…</span>}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto pr-1">
        {tab === "info"    && <InfoTab task={task} />}
        {tab === "assets"  && <AssetsTab task={task} />}
        {tab === "branches" && <BranchesTab task={task} />}
        {tab === "actions" && (
          <ActionsTab
            task={task}
            onApprove={onApprove}
            onReject={onReject}
            onCancel={onCancel}
          />
        )}
      </div>
    </div>
  )
})
