import { memo } from "react"
import type { StepPreview, TaskStepsResponse } from "../../../../api/research"
import { PHASE_LABELS } from "../constants/taskConstants"
import { DbStepDetail } from "./StepDbDetail"
import { StepPreviewPanel } from "./StepPreviewPanel"

interface StepDetailPanelProps {
  taskId: string
  data: TaskStepsResponse | null
  selectedId: string | null
  orchPhase: string
  preview: StepPreview | null
  prevLoading: boolean
  onReinitialize: () => void
}

export const StepDetailPanel = memo(function StepDetailPanel({
  taskId, data, selectedId, orchPhase,
  preview, prevLoading, onReinitialize,
}: StepDetailPanelProps) {
  if (selectedId) return <DbStepDetail taskId={taskId} data={data} selectedId={selectedId} />

  const phaseLabel = PHASE_LABELS[orchPhase] || orchPhase
  if (prevLoading) return (
    <div className="flex items-center justify-center h-full text-[#555] animate-pulse text-xs select-none">[ loading preview… ]</div>
  )
  if (preview) return (
    <StepPreviewPanel preview={preview} phaseLabel={phaseLabel}
      onReinitialize={onReinitialize} reinitLoading={prevLoading} />
  )
  return (
    <div className="flex items-center justify-center h-full text-[#444] italic text-xs select-none">
      [ select a step ]
    </div>
  )
})
