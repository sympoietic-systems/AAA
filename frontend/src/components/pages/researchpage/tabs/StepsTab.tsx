import React, { memo, useState, useEffect, useCallback } from "react"
import type { TaskStepsResponse, StepPreview } from "../../../../api/research"
import { getTaskSteps, executeStep, rerunTask, getStepPreview, reinitializeTask } from "../../../../api/research"
import { TwoPanelLayout } from "../shared/TwoPanelLayout"
import { StepPipeline } from "../steps/StepPipeline"
import { StepDetailPanel } from "../steps/StepDetailPanel"

export const StepsTab = memo(function StepsTab({ taskId, orchPhase, taskStatus, onRefreshTask, onSelectTab, externalStepId }: {
  taskId: string
  orchPhase: string
  taskStatus: string
  onRefreshTask?: () => void
  onSelectTab?: (tabId: "info" | "steps" | "report") => void
  externalStepId?: string | null
}) {
  const [data, setData] = useState<TaskStepsResponse | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [stepping, setStepping] = useState(false)
  const [preview, setPreview] = useState<StepPreview | null>(null)
  const [prevLoading, setPrevLoading] = useState(false)

  useEffect(() => {
    if (externalStepId && data) {
      const step = data.steps.find(s => s.id === externalStepId)
      if (step) setSelectedId(externalStepId)
    }
  }, [externalStepId, data])

  const load = useCallback(() => {
    getTaskSteps(taskId).then(setData).catch(() => {})
  }, [taskId])

  const fetchPreview = useCallback(() => {
    if (!orchPhase || orchPhase === "complete" || orchPhase === "not_started") {
      setPreview(null)
      return
    }
    if (taskStatus !== "active" && taskStatus !== "queued") {
      setPreview(null)
      return
    }
    setPrevLoading(true)
    getStepPreview(taskId, orchPhase)
      .then(setPreview)
      .catch(() => setPreview(null))
      .finally(() => setPrevLoading(false))
  }, [taskId, orchPhase, taskStatus])

  const reinitAndFetch = useCallback(async () => {
    if (!orchPhase || orchPhase === "complete" || orchPhase === "not_started") return
    if (taskStatus !== "active" && taskStatus !== "queued") return
    setPrevLoading(true)
    try {
      await reinitializeTask(taskId)
      const p = await getStepPreview(taskId, orchPhase)
      setPreview(p)
    } catch { setPreview(null) }
    finally { setPrevLoading(false) }
  }, [taskId, orchPhase, taskStatus])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (selectedId) {
      setPreview(null)
      return
    }
    fetchPreview()
  }, [selectedId, fetchPreview])

  useEffect(() => {
    if (taskStatus !== "active") return
    const t = setInterval(() => {
      load()
      if (!selectedId) {
        getStepPreview(taskId, orchPhase).then(setPreview).catch(() => {})
      }
    }, 3000)
    return () => clearInterval(t)
  }, [load, taskStatus, selectedId, taskId, orchPhase])

  const doStep = async () => {
    setStepping(true)
    try { await executeStep(taskId) } catch {}
    setStepping(false)
    load()
    fetchPreview()
    onRefreshTask?.()
  }

  const doRerun = async () => {
    setStepping(true)
    try { await rerunTask(taskId) } catch {}
    setStepping(false)
    load()
    fetchPreview()
    onRefreshTask?.()
  }

  return (
    <TwoPanelLayout
      left={
        <StepPipeline
          data={data}
          preview={preview}
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
          preview={preview}
          prevLoading={prevLoading}
          onReinitialize={reinitAndFetch}
          onSelectTab={onSelectTab}
        />
      }
    />
  )
})
