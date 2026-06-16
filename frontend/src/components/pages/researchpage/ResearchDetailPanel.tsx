// ResearchDetailPanel — detail view for a selected research task.
// Tabs: Info, Assets, Branches, Actions.
// Fetches full task detail (with branches) on selection.

import React, { memo, useState, useEffect } from "react"
import type { ResearchTask } from "../../../api/research"
import { getResearchTask } from "../../../api/research"

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

function InfoTab({ task }: { task: ResearchTask }) {
  const color = STATUS_COLORS[task.status] ?? "#666"
  const progress = task.budget_limit_usd > 0
    ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100)
    : 0

  return (
    <div className="space-y-1.5 text-[10px]">
      {/* Header */}
      <div className="flex items-center gap-2 pb-1.5 border-b border-[#1a1a1a]">
        <span style={{ color }} className="text-[10px]">●</span>
        <span className="text-[#bbb] text-xs font-bold">{task.title}</span>
        <span style={{ color }} className="text-[10px] ml-auto uppercase">{task.status}</span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        <div className="text-[#555]">id:</div>
        <div className="text-[#777] text-[9px] truncate" title={task.id}>{task.id.slice(0, 12)}…</div>

        <div className="text-[#555]">objective:</div>
        <div className="text-[#94a3b8]">{task.objective}</div>

        <div className="text-[#555]">trigger:</div>
        <div className="text-[#777]">{task.trigger_source}</div>

        <div className="text-[#555]">depth / breadth:</div>
        <div className="text-[#777]">{task.max_depth} / {task.max_breadth}{task.is_agonistic ? " · agonistic" : ""}</div>

        <div className="text-[#555]">branches:</div>
        <div className="text-[#777]">{task.branches_created}</div>

        <div className="text-[#555]">assets harvested:</div>
        <div className="text-[#777]">{task.assets_harvested || (task.assets?.length ?? 0)}</div>

        <div className="text-[#555]">lateral flights:</div>
        <div className="text-[#777]">{task.lateral_flights}</div>

        <div className="text-[#555]">bifurcations:</div>
        <div className="text-[#777]">{task.bifurcation_triggered}</div>

        <div className="text-[#555]">budget:</div>
        <div className="text-[#777]">
          ${task.budget_spent_usd.toFixed(4)} / ${task.budget_limit_usd.toFixed(2)}
          <span className="text-[#555] ml-1">({progress}%)</span>
        </div>

        {task.proposed_at && (
          <>
            <div className="text-[#555]">proposed:</div>
            <div className="text-[#777] text-[9px]">{task.proposed_at}</div>
          </>
        )}
        {task.started_at && (
          <>
            <div className="text-[#555]">started:</div>
            <div className="text-[#777] text-[9px]">{task.started_at}</div>
          </>
        )}
        {task.completed_at && (
          <>
            <div className="text-[#555]">completed:</div>
            <div className="text-[#777] text-[9px]">{task.completed_at}</div>
          </>
        )}
      </div>

      {/* Rationale */}
      {task.proposal_rationale && (
        <div className="pt-1.5 border-t border-[#1a1a1a]">
          <div className="text-[#555] mb-0.5">rationale:</div>
          <div className="text-[#777] leading-relaxed">{task.proposal_rationale}</div>
        </div>
      )}

      {/* Result Summary */}
      {task.result_summary && (
        <div className="pt-1.5 border-t border-[#1a1a1a]">
          <div className="text-[#555] mb-0.5">result summary:</div>
          <div className="text-[#94a3b8] leading-relaxed max-h-48 overflow-y-auto">{task.result_summary}</div>
        </div>
      )}
    </div>
  )
}

function AssetsTab({ task }: { task: ResearchTask }) {
  const assets = task.assets ?? []

  if (assets.length === 0) {
    return (
      <div className="text-[#444] italic text-xs mt-4 text-center">
        [ no assets harvested ]
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="text-[#555] text-[9px] pb-1 border-b border-[#1a1a1a]">
        {assets.length} asset{assets.length !== 1 ? "s" : ""}
      </div>
      {assets.map((a, i) => (
        <div key={a.id || i} className="border-l border-[#222] pl-2 py-1">
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
          <div className="flex gap-3 mt-0.5 text-[9px]">
            <span className="text-[#4ade80]">rel {(a.relevance_score ?? 0).toFixed(2)}</span>
            <span className="text-[#888]">nov {(a.novelty_score ?? 0).toFixed(2)}</span>
            <span className="text-[#888]">dif {(a.diffractive_score ?? 0).toFixed(2)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

function BranchesTab({ task }: { task: ResearchTask }) {
  const branches = task.branches ?? []

  if (branches.length === 0) {
    return (
      <div className="text-[#444] italic text-xs mt-4 text-center">
        [ no branches recorded ]
      </div>
    )
  }

  return (
    <div className="space-y-1">
      <div className="text-[#555] text-[9px] pb-1 border-b border-[#1a1a1a]">
        {branches.length} branch{branches.length !== 1 ? "es" : ""}
      </div>
      {branches.map((b: any, i: number) => {
        const statusColor = STATUS_COLORS[b.status] ?? "#666"
        return (
          <div key={b.id || i} className="border-l border-[#222] pl-2 py-1">
            <div className="flex items-center gap-1.5">
              <span style={{ color: statusColor }} className="text-[9px]">●</span>
              <span className="text-[#bbb] text-[10px] truncate">{b.query || b.id?.slice(0, 12)}</span>
              <span style={{ color: statusColor }} className="text-[8px]">{b.status}</span>
            </div>
            <div className="text-[#555] text-[9px] ml-3.5">
              depth: {b.depth} · children: {b.children_created ?? 0} · assets: {b.assets_harvested ?? 0}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function ActionsTab({
  task, onApprove, onReject, onCancel,
}: {
  task: ResearchTask
  onApprove?: (id: string) => Promise<void>
  onReject?: (id: string) => Promise<void>
  onCancel?: (id: string) => Promise<void>
}) {
  return (
    <div className="space-y-2 text-[10px]">
      {task.status === "proposed" && (
        <div className="flex gap-2">
          {onApprove && (
            <button
              onClick={() => onApprove(task.id)}
              className="text-[#4ade80] hover:text-[#6ee7b0] font-mono"
            >
              [✓ approve & dispatch]
            </button>
          )}
          {onReject && (
            <button
              onClick={() => onReject(task.id)}
              className="text-[#ef4444] hover:text-[#f87171] font-mono"
            >
              [✗ dismiss]
            </button>
          )}
        </div>
      )}

      {(task.status === "queued" || task.status === "active") && onCancel && (
        <button
          onClick={() => onCancel(task.id)}
          className="text-[#ef4444] hover:text-[#f87171] font-mono"
        >
          [✕ cancel task]
        </button>
      )}

      {task.status === "failed" && (
        <button
          onClick={() => {
            // Retry by dispatching with same params
            window.dispatchEvent(new CustomEvent("research-retry", { detail: task }))
          }}
          className="text-[#f59e0b] hover:text-[#fbbf24] font-mono"
        >
          [↻ retry task]
        </button>
      )}

      {["completed", "cancelled", "rejected"].includes(task.status) && (
        <div className="text-[#555] italic">
          [ no actions available — task is {task.status} ]
        </div>
      )}

      {/* Timestamps */}
      <div className="pt-2 mt-2 border-t border-[#1a1a1a] text-[#555] text-[9px] space-y-0.5">
        {task.proposed_at && <div>proposed: {task.proposed_at}</div>}
        {task.approved_at && <div>approved: {task.approved_at}</div>}
        {task.started_at && <div>started: {task.started_at}</div>}
        {task.completed_at && <div>completed: {task.completed_at}</div>}
      </div>
    </div>
  )
}

export const ResearchDetailPanel = memo(function ResearchDetailPanel({
  task: initialTask, onApprove, onReject, onCancel,
}: Props) {
  // Fetch full detail (with branches) on selection
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
      {/* Tab bar */}
      <div className="flex flex-wrap gap-x-1 gap-y-1 mb-3 text-[10px] select-none border-b border-[#1a1a1a] pb-1">
        {TABS.map((t, i) => (
          <span key={t.key} className="flex items-center gap-x-1 whitespace-nowrap">
            {i > 0 && <span className="text-[#333]">·</span>}
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
