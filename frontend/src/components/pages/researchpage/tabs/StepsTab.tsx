import React, { memo, useState, useEffect, useCallback } from "react"
import type { TaskStepsResponse } from "../../../../api/research"
import { getTaskSteps, executeStep, rerunTask } from "../../../../api/research"
import { TwoPanelLayout } from "../shared/TwoPanelLayout"
import { StepPipeline } from "../steps/StepPipeline"
import { StepDetailPanel } from "../steps/StepDetailPanel"

export const StepsTab = memo(function StepsTab({ taskId, orchPhase, taskStatus, onRefreshTask }: {
  taskId: string
  orchPhase: string
  taskStatus: string
  onRefreshTask?: () => void
}) {
  const [data, setData] = useState<TaskStepsResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [stepping, setStepping] = useState(false)

  const load = useCallback(() => {
    getTaskSteps(taskId).then(setData).catch(() => {})
  }, [taskId])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (taskStatus !== "active") return
    const t = setInterval(load, 3000)
    return () => clearInterval(t)
  }, [load, taskStatus])

  const doStep = async () => {
    setStepping(true)
    try { await executeStep(taskId) } catch {}
    setStepping(false)
    load()
    onRefreshTask?.()
  }

  const doRerun = async () => {
    setStepping(true)
    try { await rerunTask(taskId) } catch {}
    setStepping(false)
    load()
    onRefreshTask?.()
  }

  return (
    <TwoPanelLayout
      left={
        <StepPipeline
          data={data}
          orchPhase={orchPhase}
          taskStatus={taskStatus}
          selectedId={selectedId}
          stepping={stepping}
          onSelect={setSelectedId}
          onDoStep={doStep}
          onDoRerun={doRerun}
        />
      }
      right={
        <StepDetailPanel
          taskId={taskId}
          data={data}
          selectedId={selectedId}
          orchPhase={orchPhase}
          taskStatus={taskStatus}
        />
      }
    />
  )
})
