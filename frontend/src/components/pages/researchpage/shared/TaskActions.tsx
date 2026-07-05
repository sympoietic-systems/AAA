import { memo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  approveProposal, rejectProposal, cancelTask, retryTask, deleteTask,
  rerunTask, executeStep, downloadResearchStagesExport,
} from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import { doActionAndReload } from "./taskHelpers"
import { ContinueResearchModal } from "../ContinueResearchModal"
import type { ResearchTask } from "../../../../api/research"

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
  task?: ResearchTask
}

export const TaskActions = memo(function TaskActions({
  taskId, taskStatus, taskObjective, taskTitle,
  maxDepth, maxBreadth, isAgonistic, budgetLimitUsd,
  onRefreshTask, task,
}: TaskActionsProps) {
  const [showContinue, setShowContinue] = useState(false)
  const navigate = useNavigate()
  const navigateHome = () => { navigate("/research") }

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
    setShowContinue(true)
  }

  const doExportStages = async () => {
    try {
      await downloadResearchStagesExport(taskId, taskTitle, task?.rerun_count)
    } catch (err: any) {
      console.error("Stage export failed:", err)
      alert(`Export failed: ${err.message || err}`)
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {taskStatus === "proposed" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => approveProposal(taskId))} intent="save">✓ approve</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => rejectProposal(taskId))} intent="delete">✗ dismiss</TerminalButton>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "queued" && (
        <>
          <TerminalButton onClick={async () => { await executeStep(taskId); onRefreshTask?.() }} intent="save">▶ run</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => cancelTask(taskId))} intent="delete">✕ cancel</TerminalButton>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "active" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => cancelTask(taskId))} intent="delete">✕ cancel</TerminalButton>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "failed" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => rerunTask(taskId))} intent="edit">⟳ rerun</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => retryTask(taskId))} intent="neutral">↻ retry (clone)</TerminalButton>
          <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "completed" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => rerunTask(taskId))} intent="edit">⟳ rerun</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => retryTask(taskId))} intent="save">↻ retry (clone)</TerminalButton>
          <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "cancelled" && (
        <>
          <TerminalButton onClick={() => doActionAndReload(() => rerunTask(taskId))} intent="edit">⟳ rerun</TerminalButton>
          <TerminalButton onClick={() => doActionAndReload(() => retryTask(taskId))} intent="neutral">↻ retry (clone)</TerminalButton>
          <TerminalButton onClick={doContinue} intent="cyan">▶ continue deeper</TerminalButton>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {taskStatus === "rejected" && (
        <>
          <TerminalButton onClick={doExportStages} intent="neutral">⇲ export stages</TerminalButton>
          <TerminalButton onClick={doDelete} intent="delete">✕ delete</TerminalButton>
        </>
      )}
      {showContinue && task && (
        <ContinueResearchModal task={task} onClose={() => setShowContinue(false)} onContinued={onRefreshTask} />
      )}
    </div>
  )
})
