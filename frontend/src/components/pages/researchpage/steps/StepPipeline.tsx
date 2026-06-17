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

const CYCLE_PHASES = ["search", "parallel_parse", "digest"] as const
const FINAL_PHASES = ["reflect", "evaluate", "synthesize"] as const

/** Parse result_summary or results_by_step into a compact count label. */
function stepCountSuffix(step: ResearchStep, resultsByStep: Record<string, unknown[]>): string {
  const summary = step.result_summary || ""
  // Search: "5 results" → "(5 hits)"
  const hits = summary.match(/^(\d+)\s+results?$/i)
  if (hits) return ` (${hits[1]} hits)`
  // Parse: "parsed 3 sources" → "(3 urls)"
  const parsed = summary.match(/parsed\s+(\d+)\s+sources?/i)
  if (parsed) return ` (${parsed[1]} urls)`
  // Digest: "digested 5 sources" → "(5 analyzed)"
  const digested = summary.match(/digested\s+(\d+)\s+sources?/i)
  if (digested) return ` (${digested[1]} analyzed)`
  // Reflect: "completeness: 0.75" → "(75%)"
  const completeness = summary.match(/completeness:\s*([\d.]+)/i)
  if (completeness) return ` (${Math.round(parseFloat(completeness[1]) * 100)}%)`
  // Fallback: check results_by_step count
  if (step.id && resultsByStep[step.id]) {
    const n = resultsByStep[step.id].length
    if (n > 0) return ` (${n})`
  }
  return ""
}

/** Safely parse plan_json to get search_queries. */
function getPlanQueryCount(data: TaskStepsResponse | null): number {
  if (!data?.plan?.plan_json) return 0
  try {
    const plan = JSON.parse(data.plan.plan_json)
    return Array.isArray(plan.search_queries) ? plan.search_queries.length : 0
  } catch { return 0 }
}

function PipelineRow({ label, stepId, isDone, isCurrent, isStale, isSelected, onSelect, onDoStep, stepping }: {
  label: string; stepId?: string | null; isDone: boolean; isCurrent: boolean; isStale: boolean; isSelected: boolean
  onSelect: (id: string | null) => void; onDoStep: () => void; stepping: boolean
}) {
  const sc = isStale ? "#f97316" : isDone ? "#4ade80" : isCurrent ? "#f59e0b" : "#444"
  const canClick = (isDone || isStale) && stepId

  return (
    <div
      onClick={canClick ? (() => onSelect(stepId!)) : undefined}
      className={`flex items-center gap-2 text-[10px] px-2 py-1 rounded-sm
        ${canClick ? "cursor-pointer hover:bg-[#111]" : ""}
        ${isCurrent ? "bg-[#1a1a2e]/30 border border-[#f59e0b]/20" : ""}
        ${isStale ? "bg-[#1a1a2e]/30 border border-[#f97316]/10" : ""}
        ${isSelected ? "border border-[#a78bfa]/30 bg-[#1a1a2e]/30" : ""}`}>
      <span style={{ color: sc }} className="text-[8px] shrink-0 w-3">
        {isStale ? "⟳" : isDone ? "✔" : isCurrent ? "▶" : "○"}
      </span>
      <span className={`font-mono flex-1 ${isSelected ? "text-[#c4b5fd]" : isStale ? "text-[#f97316]/80" : isDone ? "text-[#94a3b8]" : isCurrent ? "text-[#fbbf24]" : "text-[#555]"}`}>
        {label}{isStale ? " (stale)" : ""}
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

  // ── Simple plan-driven grouping ──
  const { planStep, queryGroups, finalSteps, totalQueries, activeGroupIdx } = useMemo(() => {
    const empty = {
      planStep: null as ResearchStep | null,
      queryGroups: [] as QueryGroup[],
      finalSteps: [] as ResearchStep[],
      totalQueries: 0,
      activeGroupIdx: -1,
    }
    if (!data) return empty

    const steps = [...data.steps]
    const plan = steps.find(s => s.step_type === "plan") ?? null
    const planQueryCount = getPlanQueryCount(data)
    const totalQ = planQueryCount || 1

    // Collect cycle-phase steps in chronological order
    const cycleSteps = steps.filter(s =>
      (CYCLE_PHASES as readonly string[]).includes(s.step_type)
    )

    // Build groups: for each query, pick the Nth step of each type
    const groups: QueryGroup[] = []
    for (let q = 0; q < totalQ; q++) {
      const groupSteps: ResearchStep[] = []
      for (const ct of CYCLE_PHASES) {
        const sameType = cycleSteps.filter(s => s.step_type === ct)
        const step = sameType[q] ?? null
        if (step) {
          groupSteps.push(step)
        } else {
          groupSteps.push({ id: "", step_type: ct, step_number: 0, status: "pending" } as ResearchStep)
        }
      }
      groups.push({ queryIndex: q + 1, steps: groupSteps })
    }

    // Final phases: filter out steps already in groups
    const groupedIds = new Set(groups.flatMap(g => g.steps.map(s => s.id)))
    const finals: ResearchStep[] = steps.filter(s =>
      (FINAL_PHASES as readonly string[]).includes(s.step_type) && !groupedIds.has(s.id)
    )
    // Add pending final phases
    const existingFinalTypes = new Set(finals.map(s => s.step_type))
    for (const ft of FINAL_PHASES) {
      if (!existingFinalTypes.has(ft)) {
        finals.push({ id: "", step_type: ft, step_number: 0, status: "pending" } as ResearchStep)
      }
    }

    // ── Active step detection: first non-completed step matching orchPhase ──
    let activeGIdx = -1
    for (let g = 0; g < groups.length; g++) {
      for (const s of groups[g].steps) {
        if (s.status !== "completed" && STEP_TO_PHASE[s.step_type] === orchPhase) {
          activeGIdx = g
          break
        }
      }
      if (activeGIdx >= 0) break
    }

    return { planStep: plan, queryGroups: groups, finalSteps: finals, totalQueries: totalQ, activeGroupIdx: activeGIdx }
  }, [data, orchPhase])

  // Results by step for count labels
  const resultsByStep = (data?.results_by_step || {}) as Record<string, unknown[]>

  return (
    <div className="flex-1 overflow-y-auto pr-1 space-y-3">
      <div>
        <div className="text-[#6c6c8a] uppercase text-[9px] tracking-wider mb-1.5">[ Pipeline ]</div>

        {/* Plan */}
        {planStep && (
          <div className="mb-1">
            <PipelineRow
              label={`Plan${planStep.status === "completed" ? stepCountSuffix(planStep, resultsByStep) : allComplete ? "" : " (" + planStep.status + ")"}`}
              stepId={planStep.id}
              isDone={allComplete || planStep.status === "completed"}
              isCurrent={orchPhase === "planning"}
              isStale={planStep.status === "stale"}
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
                const baseLabel = STEP_LABELS[step.step_type] || step.step_type
                const stale = step.status === "stale"
                const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
                const pending = step.id ? "" : " —"
                const done = allComplete || step.status === "completed" || stale
                // Active: first non-completed step matching orchPhase in the active group
                const isActive = !allComplete && hasPipeline
                  && group.queryIndex - 1 === activeGroupIdx
                  && STEP_TO_PHASE[step.step_type] === orchPhase
                  && step.status !== "completed"
                return (
                  <PipelineRow
                    key={step.id || `${group.queryIndex}-${step.step_type}`}
                    label={baseLabel + suffix + pending}
                    stepId={step.id || null}
                    isDone={done}
                    isCurrent={isActive}
                    isStale={stale}
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
              const baseLabel = PHASE_LABELS[phase] || step.step_type
              const stale = step.status === "stale"
              const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
              const pending = step.id ? "" : " —"
              const done = allComplete || step.status === "completed" || stale
              const isActive = !allComplete && hasPipeline && phase === orchPhase && step.status !== "completed"
              return (
                <PipelineRow
                  key={step.id || step.step_type}
                  label={baseLabel + suffix + pending}
                  stepId={step.id || null}
                  isDone={done}
                  isCurrent={isActive}
                  isStale={stale}
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
