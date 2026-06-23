import { memo } from "react"
import {
  approveProposal, rejectProposal, cancelTask, retryTask, deleteTask,
  rerunTask, executeStep,
} from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import { doActionAndReload } from "./taskHelpers"

interface TaskActionsProps {
  taskId: string
  taskStatus: string
  taskObjective: string
  taskTitle: string
  maxDepth: number
  maxBreadth: number
  isAgonistic: boolean
  budgetLimitUsd: number
  onRefreshTask?: () => void
}

export const TaskActions = memo(function TaskActions({
  taskId, taskStatus, taskObjective, taskTitle,
  maxDepth, maxBreadth, isAgonistic, budgetLimitUsd,
  onRefreshTask,
}: TaskActionsProps) {
  const navigateHome = () => { window.location.href = "/research" }

  const doDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this research task?")) return
    try {
      await deleteTask(taskId)
      navigateHome()
    } catch (err: any) {
      console.error("Failed to delete task:", err)
      alert(`Failed to delete task: ${err.message || err}`)
    }
  }

  const doContinue = async () => {
    const { dispatchResearch } = await import("../../../../api/research")
    await dispatchResearch({
      objective: taskObjective, title: taskTitle,
      max_depth: (maxDepth || 2) + 1, max_breadth: maxBreadth || 2,
      is_agonistic: !!isAgonistic, budget_limit_usd: budgetLimitUsd || 0.50,
    })
    navigateHome()
  }

  return (
    <div className="flex flex-wrap gap-2">
      {taskStatus === "proposed" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => approveProposal(taskId))} intent="save">✓ approve</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => rejectProposal(taskId))} intent="delete">✗ dismiss</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "queued" && (
        <>
          <TerminalButton onClick={async () => { await executeStep(taskId); onRefreshTask?.() }} intent="save">▶ run</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => cancelTask(taskId))} intent="delete">✕ cancel</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "active" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => cancelTask(taskId))} intent="delete">✕ cancel</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "failed" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => rerunTask(taskId))} intent="edit">⟳ rerun</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => retryTask(taskId))} intent="neutral">↻ retry (clone)</TerminalButton>
          <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "completed" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => rerunTask(taskId))} intent="edit">⟳ rerun</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => retryTask(taskId))} intent="save">↻ retry (clone)</TerminalButton>
          <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "cancelled" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => rerunTask(taskId))} intent="edit">⟳ rerun</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => retryTask(taskId))} intent="neutral">↻ retry (clone)</TerminalButton>
          <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "rejected" && (
        <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
      )}
    </div>
  )
})
