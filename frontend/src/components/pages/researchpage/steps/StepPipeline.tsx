import React, { memo } from "react"
import type { TaskStepsResponse } from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import {
  PHASE_ORDER_DISPLAY, PHASE_LABELS, STEP_TO_PHASE,
} from "../constants/taskConstants"

interface StepPipelineProps {
  data: TaskStepsResponse | null
  orchPhase: string
  taskStatus: string
  selectedId: string | null
  stepping: boolean
  onSelect: (id: string | null) => void
  onDoStep: () => void
  onDoRerun: () => void
}

export const StepPipeline = memo(function StepPipeline({
  data, orchPhase, taskStatus, selectedId, stepping,
  onSelect, onDoStep, onDoRerun,
}: StepPipelineProps) {
  // Map pipeline phases to DB step IDs — a phase is "done" if it has a DB entry
  const phaseToStepId: Record<string, string | null> = {}
  if (data) {
    const steps = [...data.steps].reverse()
    const seen: Record<string, boolean> = {}
    for (const s of steps) {
      const phase = STEP_TO_PHASE[s.step_type]
      if (phase && !seen[phase]) { phaseToStepId[phase] = s.id; seen[phase] = true }
    }
  }

  const allComplete = taskStatus === "completed" && orchPhase === "complete"
  const hasPipeline = orchPhase && orchPhase !== "complete" && orchPhase !== "not_started"

  const handlePipelineClick = (phase: string) => {
    const sid = phaseToStepId[phase]
    onSelect(selectedId === sid ? null : sid)
  }

  return (
    <div className="flex-1 overflow-y-auto pr-1 space-y-3">
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1.5">[ Pipeline ]</div>
        <div className="space-y-0.5">
          {PHASE_ORDER_DISPLAY.map((phase) => {
            const label = PHASE_LABELS[phase] || phase
            const sid = phaseToStepId[phase]
            const isSel = sid && sid === selectedId

            // Phase status: done if has DB entry, current if exactly matches orchPhase
            const hasDbEntry = !!sid
            const isCurrent = hasPipeline && phase === orchPhase
            const isDone = allComplete || (!isCurrent && hasDbEntry)
            const isPending = !isCurrent && !isDone

            const sc = isDone ? "#4ade80" : isCurrent ? "#f59e0b" : "#444"
            const canClick = isDone && sid

            return (
              <div key={phase}
                onClick={canClick ? (() => handlePipelineClick(phase)) : undefined}
                className={`flex items-center gap-2 text-[10px] px-2 py-1 rounded-sm
                  ${canClick ? "cursor-pointer hover:bg-[#111]" : ""}
                  ${isCurrent ? "bg-[#1a1a2e]/30 border border-[#f59e0b]/20" : ""}
                  ${isSel ? "border border-[#a78bfa]/30 bg-[#1a1a2e]/30" : ""}`}>
                <span style={{ color: sc }} className="text-[8px] shrink-0 w-3">
                  {isDone ? "✔" : isCurrent ? "▶" : "○"}
                </span>
                <span className={`font-mono flex-1 ${isSel ? "text-[#c4b5fd]" : isDone ? "text-[#94a3b8]" : isCurrent ? "text-[#fbbf24]" : "text-[#555]"}`}>
                  {label}
                </span>
                {isCurrent && (
                  <button onClick={e => { e.stopPropagation(); onDoStep() }} disabled={stepping}
                    className="text-[#4ade80] hover:text-[#6ee7b0] text-[9px] font-mono disabled:text-[#333] cursor-pointer">
                    [{stepping ? "…" : "▶ run"}]
                  </button>
                )}
              </div>
            )
          })}
        </div>
        {taskStatus === "completed" && orchPhase === "complete" && (
          <div className="mt-2">
            <TerminalButton onClick={onDoRerun} intent="edit">⟳ rerun all</TerminalButton>
          </div>
        )}
      </div>
    </div>
  )
})
