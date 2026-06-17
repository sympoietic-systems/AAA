import React, { memo, useState, useEffect, useCallback } from "react"
import type { StepPreview } from "../../../../api/research"
import type { TaskStepsResponse } from "../../../../api/research"
import { getStepPreview, reinitializeTask } from "../../../../api/research"
import { PHASE_LABELS } from "../constants/taskConstants"
import { DbStepDetail } from "./StepDbDetail"
import { StepPreviewPanel } from "./StepPreviewPanel"

interface StepDetailPanelProps {
  taskId: string
  data: TaskStepsResponse | null
  selectedId: string | null
  orchPhase: string
  taskStatus: string
}

export const StepDetailPanel = memo(function StepDetailPanel({
  taskId, data, selectedId, orchPhase, taskStatus,
}: StepDetailPanelProps) {
  const [preview, setPreview] = useState<StepPreview | null>(null)
  const [prevLoading, setPrevLoading] = useState(false)

  const fetchPreview = useCallback(() => {
    if (!orchPhase || orchPhase === "complete" || orchPhase === "not_started") return
    if (taskStatus !== "active" && taskStatus !== "queued") return
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

  useEffect(() => {
    if (selectedId) { setPreview(null); return }
    fetchPreview()
  }, [selectedId, fetchPreview])

  if (selectedId) return <DbStepDetail taskId={taskId} data={data} selectedId={selectedId} />

  const phaseLabel = PHASE_LABELS[orchPhase] || orchPhase
  if (prevLoading) return (
    <div className="flex items-center justify-center h-full text-[#555] animate-pulse text-xs select-none">[ loading preview… ]</div>
  )
  if (preview) return (
    <StepPreviewPanel preview={preview} phaseLabel={phaseLabel}
      onReinitialize={reinitAndFetch} reinitLoading={prevLoading} />
  )
  return (
    <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">
      [ select a step ]
    </div>
  )
})
