import React, { memo } from "react"
import type { ResearchTask } from "../../../../api/research"
import { KeyValueGrid } from "../../../UI"
import { BracketHeader } from "../shared/BracketHeader"
import { TaskActions } from "../shared/TaskActions"
import { STATUS_COLORS } from "../constants/taskConstants"

export const InfoTab = memo(function InfoTab({ task, orchPhase, onRefreshTask }: {
  task: ResearchTask
  orchPhase?: string
  onRefreshTask?: () => void
}) {
  const color = STATUS_COLORS[task.status] ?? "var(--color-ui-dim)"
  const progress = task.budget_limit_usd > 0 ? Math.round((task.budget_spent_usd / task.budget_limit_usd) * 100) : 0
  const metrics = [
    { key: "id", value: task.id.slice(0, 12) + "…" },
    { key: "status", value: task.status, valueColor: color },
    { key: "trigger", value: task.trigger_source },
    { key: "depth", value: task.max_depth },
    { key: "breadth", value: task.max_breadth },
    { key: "agonistic", value: task.is_agonistic ? "yes" : "no", valueColor: task.is_agonistic ? "var(--color-semantic-gold)" : undefined },
    { key: "branches", value: task.branches_created },
    { key: "assets", value: task.assets_harvested || (task.assets?.length ?? 0) },
    { key: "budget", value: `$${task.budget_spent_usd.toFixed(4)} / $${task.budget_limit_usd.toFixed(2)} (${progress}%)` },
    ...(orchPhase && orchPhase !== "complete" ? [{ key: "phase", value: orchPhase.toUpperCase(), valueColor: "var(--color-semantic-gold)" }] : []),
    ...(task.proposed_at ? [{ key: "proposed", value: task.proposed_at }] : []),
    ...(task.started_at ? [{ key: "started", value: task.started_at }] : []),
    ...(task.completed_at ? [{ key: "completed", value: task.completed_at }] : []),
  ]

  return (
    <div className="space-y-3 font-mono">
      <div>
        <BracketHeader text=" Objective " />
        <div className="text-ui-secondary text-[10px] leading-relaxed">{task.objective}</div>
      </div>

      <div>
        <BracketHeader text=" Metrics " />
        <KeyValueGrid items={metrics} />
      </div>

      <div>
        <BracketHeader text=" Actions " />
        <TaskActions
          taskId={task.id}
          taskStatus={task.status}
          taskObjective={task.objective}
          taskTitle={task.title}
          maxDepth={task.max_depth}
          maxBreadth={task.max_breadth}
          isAgonistic={!!task.is_agonistic}
          budgetLimitUsd={task.budget_limit_usd}
          onRefreshTask={onRefreshTask}
        />
      </div>
    </div>
  )
})
