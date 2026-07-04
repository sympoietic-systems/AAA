import { memo, useState } from "react"
import type { TaskStepsResponse, StepPreview } from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import { usePipelineCycles } from "./pipeline/usePipelineCycles"
import { CycleBlock } from "./pipeline/CycleBlock"

interface StepPipelineProps {
  data: TaskStepsResponse | null
  preview: StepPreview | null
  orchPhase: string
  taskStatus: string
  selectedId: string | null
  stepping: boolean
  onSelect: (id: string | null) => void
  onDoStep: () => void
  onDoRerun: () => void
  onRerunPhase: (stepType: string) => void
}

export const StepPipeline = memo(function StepPipeline({
  data, preview, orchPhase, taskStatus, selectedId, stepping,
  onSelect, onDoStep, onDoRerun, onRerunPhase,
}: StepPipelineProps) {
  const allComplete = taskStatus === "completed" && orchPhase === "complete"
  const hasPipeline = !!orchPhase && orchPhase !== "complete" && orchPhase !== "not_started"

  const { cycles, activeGroupIdx, planQueries, activeDepth } = usePipelineCycles(data, orchPhase, preview)

  const resultsByStep = (data?.results_by_step || {}) as Record<string, unknown[]>

  const [collapsedCycles, setCollapsedCycles] = useState<Record<number, boolean>>({})

  const isCollapsed = (depth: number) => {
    if (collapsedCycles[depth] !== undefined) {
      return collapsedCycles[depth]
    }
    return depth !== activeDepth
  }

  const toggleCycle = (depth: number) => {
    setCollapsedCycles((prev) => ({
      ...prev,
      [depth]: !isCollapsed(depth),
    }))
  }

  return (
    <div className="flex-1 overflow-y-auto pr-1 space-y-3">
      <div>
        <div className="text-semantic-header uppercase text-[9px] tracking-wider mb-1.5 font-mono">[ Pipeline ]</div>

        {cycles.map((cycle) => (
          <CycleBlock
            key={cycle.depth}
            cycle={cycle}
            collapsed={isCollapsed(cycle.depth)}
            onToggle={toggleCycle}
            allComplete={allComplete}
            hasPipeline={hasPipeline}
            orchPhase={orchPhase}
            selectedId={selectedId}
            stepping={stepping}
            activeDepth={activeDepth}
            activeGroupIdx={activeGroupIdx}
            planQueries={planQueries}
            preview={preview}
            resultsByStep={resultsByStep}
            onSelect={onSelect}
            onDoStep={onDoStep}
            onRerunPhase={onRerunPhase}
          />
        ))}

        {taskStatus === "completed" && orchPhase === "complete" && (
          <div className="mt-2">
            <TerminalButton onClick={onDoRerun} intent="edit">⟳ rerun all</TerminalButton>
          </div>
        )}
      </div>
    </div>
  )
})
