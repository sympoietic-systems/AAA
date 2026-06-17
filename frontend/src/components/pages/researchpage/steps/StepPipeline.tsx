import React, { memo, useMemo } from "react"
import type { TaskStepsResponse, ResearchStep } from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import {
  STEP_TO_PHASE, STEP_LABELS, PHASE_LABELS,
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

interface QueryGroup {
  steps: ResearchStep[]
  queryIndex: number
}

const CYCLE_PHASES = ["search", "parse", "digest"] as const
const CYCLE_ORCH_PHASES = ["searching", "parsing", "digesting"]
const FINAL_PHASES = ["reflect", "evaluate", "synthesize"] as const
const FINAL_ORCH_PHASES = ["reflecting", "evaluating", "synthesizing"]

function PipelineRow({ label, stepId, isDone, isCurrent, isSelected, onSelect, onDoStep, stepping }: {
  label: string; stepId?: string | null; isDone: boolean; isCurrent: boolean; isSelected: boolean
  onSelect: (id: string | null) => void; onDoStep: () => void; stepping: boolean
}) {
  const sc = isDone ? "#4ade80" : isCurrent ? "#f59e0b" : "#444"
  const canClick = isDone && stepId

  return (
    <div
      onClick={canClick ? (() => onSelect(stepId!)) : undefined}
      className={`flex items-center gap-2 text-[10px] px-2 py-1 rounded-sm
        ${canClick ? "cursor-pointer hover:bg-[#111]" : ""}
        ${isCurrent ? "bg-[#1a1a2e]/30 border border-[#f59e0b]/20" : ""}
        ${isSelected ? "border border-[#a78bfa]/30 bg-[#1a1a2e]/30" : ""}`}>
      <span style={{ color: sc }} className="text-[8px] shrink-0 w-3">
        {isDone ? "✔" : isCurrent ? "▶" : "○"}
      </span>
      <span className={`font-mono flex-1 ${isSelected ? "text-[#c4b5fd]" : isDone ? "text-[#94a3b8]" : isCurrent ? "text-[#fbbf24]" : "text-[#555]"}`}>
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
}

export const StepPipeline = memo(function StepPipeline({
  data, orchPhase, taskStatus, selectedId, stepping,
  onSelect, onDoStep, onDoRerun,
}: StepPipelineProps) {
  const allComplete = taskStatus === "completed" && orchPhase === "complete"
  const hasPipeline = orchPhase && orchPhase !== "complete" && orchPhase !== "not_started"

  // Build query groups from DB steps (chronological order)
  const { planStep, queryGroups, finalSteps } = useMemo(() => {
    if (!data) return { planStep: null as ResearchStep | null, queryGroups: [] as QueryGroup[], finalSteps: [] as ResearchStep[] }

    const steps = [...data.steps] // chronological order (oldest first)
    const plan = steps.find(s => s.step_type === "plan") ?? null
    const others = steps.filter(s => s.step_type !== "plan")

    // Group search/parse/digest into triples
    const groups: QueryGroup[] = []
    let currentGroup: ResearchStep[] = []
    for (const s of others) {
      if ((CYCLE_PHASES as readonly string[]).includes(s.step_type)) {
        currentGroup.push(s)
        if (currentGroup.length === 3) {
          groups.push({ steps: [...currentGroup], queryIndex: groups.length + 1 })
          currentGroup = []
        }
      } else {
        break // final phases start
      }
    }
    // Incomplete group (still building)
    if (currentGroup.length > 0) {
      groups.push({ steps: [...currentGroup], queryIndex: groups.length + 1 })
    }

    // Remaining after all cycle steps
    const cycleStepIds = new Set(groups.flatMap(g => g.steps.map(s => s.id)))
    const finals = others.filter(s => !cycleStepIds.has(s.id))

    // Also add pending final phases that haven't run yet
    const existingFinalTypes = new Set(finals.map(s => s.step_type))
    for (const ft of FINAL_PHASES) {
      if (!existingFinalTypes.has(ft)) {
        finals.push({ id: "", step_type: ft, step_number: 0, status: "pending" } as ResearchStep)
      }
    }

    return { planStep: plan, queryGroups: groups, finalSteps: finals }
  }, [data])

  // Determine current cycle index from orchPhase
  const cycleActiveIdx = CYCLE_ORCH_PHASES.indexOf(orchPhase)

  // Phase-to-ID lookup for latest of each type
  const phaseToStepId: Record<string, string | null> = {}
  if (data) {
    const steps = [...data.steps].reverse()
    const seen: Record<string, boolean> = {}
    for (const s of steps) {
      const phase = STEP_TO_PHASE[s.step_type]
      if (phase && !seen[phase]) { phaseToStepId[phase] = s.id; seen[phase] = true }
    }
  }

  // Total planned queries = number of groups (or at least 1)
  const totalQueries = queryGroups.length || 1
  // Which query group is currently active
  const activeGroupIdx = cycleActiveIdx >= 0
    ? queryGroups.findIndex(g => g.steps.some(s => s.status !== "completed")) : -1
  const effectiveActiveIdx = activeGroupIdx >= 0 ? activeGroupIdx : queryGroups.length - 1

  return (
    <div className="flex-1 overflow-y-auto pr-1 space-y-3">
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1.5">[ Pipeline ]</div>

        {/* Plan */}
        {planStep && (
          <div className="mb-1">
            <PipelineRow
              label={`Plan${allComplete ? "" : planStep.status === "completed" ? "" : " (" + planStep.status + ")"}`}
              stepId={planStep.id}
              isDone={allComplete || planStep.status === "completed"}
              isCurrent={orchPhase === "planning"}
              isSelected={selectedId === planStep.id}
              onSelect={onSelect}
              onDoStep={onDoStep}
              stepping={stepping}
            />
          </div>
        )}

        {/* Query groups */}
        {queryGroups.map((group) => {
          const queryLabel = `Q${group.queryIndex}/${totalQueries}`
          return (
            <div key={group.queryIndex} className="mb-1 pl-2">
              <div className="text-[#555] text-[8px] tracking-wider mb-0.5">{queryLabel}</div>
              {group.steps.map((step) => {
                const label = STEP_LABELS[step.step_type] || step.step_type
                const done = allComplete || step.status === "completed"
                // Active if this step is in the currently-active query group and matches orchPhase
                const isActive = !allComplete && hasPipeline && group.queryIndex - 1 === effectiveActiveIdx && STEP_TO_PHASE[step.step_type] === orchPhase
                return (
                  <PipelineRow
                    key={step.id || `${group.queryIndex}-${step.step_type}`}
                    label={label + (step.id ? "" : " —")}
                    stepId={step.id || null}
                    isDone={done}
                    isCurrent={isActive}
                    isSelected={step.id ? selectedId === step.id : false}
                    onSelect={step.id ? onSelect : () => {}}
                    onDoStep={onDoStep}
                    stepping={stepping}
                  />
                )
              })}
            </div>
          )
        })}

        {/* Final phases: Reflect → Evaluate → Synthesize */}
        {finalSteps.length > 0 && (
          <div className="pl-2 pt-1 border-t border-[#1a1a1a]">
            {finalSteps.map((step) => {
              const phase = STEP_TO_PHASE[step.step_type]
              const label = PHASE_LABELS[phase] || step.step_type
              const done = allComplete || step.status === "completed"
              const isActive = !allComplete && hasPipeline && phase === orchPhase
              return (
                <PipelineRow
                  key={step.id || step.step_type}
                  label={label + (step.id ? "" : " —")}
                  stepId={step.id || null}
                  isDone={done}
                  isCurrent={isActive}
                  isSelected={step.id ? selectedId === step.id : false}
                  onSelect={step.id ? onSelect : () => {}}
                  onDoStep={onDoStep}
                  stepping={stepping}
                />
              )
            })}
          </div>
        )}

        {taskStatus === "completed" && orchPhase === "complete" && (
          <div className="mt-2">
            <TerminalButton onClick={onDoRerun} intent="edit">⟳ rerun all</TerminalButton>
          </div>
        )}
      </div>
    </div>
  )
})
