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
const CYCLE_ORCH_PHASES = ["searching", "parsing", "digesting"]
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

  // Build query groups from DB steps, validated against plan's search_queries
  const { planStep, queryGroups, finalSteps, plannedQueryCount } = useMemo(() => {
    const empty = { planStep: null as ResearchStep | null, queryGroups: [] as QueryGroup[], finalSteps: [] as ResearchStep[], plannedQueryCount: 0 }
    if (!data) return empty

    // Steps are already in chronological order (from top to bottom)
    const steps = [...data.steps]
    const plan = steps.find(s => s.step_type === "plan") ?? null
    const others = steps.filter(s => s.step_type !== "plan")
    const planQueryCount = getPlanQueryCount(data)

    // Group search/parse/digest by query boundary (each "search" step starts a new query group)
    const groups: QueryGroup[] = []
    let currentGroup: ResearchStep[] = []
    let groupIdx = 0
    for (const s of others) {
      if ((CYCLE_PHASES as readonly string[]).includes(s.step_type)) {
        // Start a new group when we encounter a "search" step (except for the very first)
        if (s.step_type === "search" && currentGroup.length > 0) {
          groupIdx++
          groups.push({ steps: [...currentGroup], queryIndex: groupIdx })
          currentGroup = []
        }
        currentGroup.push(s)
      } else {
        break // final phases start
      }
    }
    // Push the last query group
    if (currentGroup.length > 0) {
      groupIdx++
      groups.push({ steps: [...currentGroup], queryIndex: groupIdx })
    }

    // Cap groups to planned query count (ignore extra groups from retries)
    const capped = planQueryCount > 0 ? groups.slice(0, planQueryCount) : groups

    // Remaining steps after all cycle steps = final phases (reflect/evaluate/synthesize)
    const cycleStepIds = new Set(capped.flatMap(g => g.steps.map(s => s.id)))
    const finals: ResearchStep[] = others.filter(s => !cycleStepIds.has(s.id))

    // Also add pending final phases that haven't run yet
    const existingFinalTypes = new Set(finals.map(s => s.step_type))
    for (const ft of FINAL_PHASES) {
      if (!existingFinalTypes.has(ft)) {
        finals.push({ id: "", step_type: ft, step_number: 0, status: "pending" } as ResearchStep)
      }
    }

    return { planStep: plan, queryGroups: capped, finalSteps: finals, plannedQueryCount: planQueryCount || capped.length }
  }, [data])

  // Results by step for count labels
  const resultsByStep = (data?.results_by_step || {}) as Record<string, unknown[]>

  // Determine current cycle index from orchPhase
  const cycleActiveIdx = CYCLE_ORCH_PHASES.indexOf(orchPhase)

  // Phase-to-ID lookup for latest of each type
  const phaseToStepId: Record<string, string | null> = {}
  if (data) {
    // Chronological order — latest iteration wins for each phase
    const steps = [...data.steps]
    const seen: Record<string, boolean> = {}
    for (const s of steps) {
      const phase = STEP_TO_PHASE[s.step_type]
      if (phase && !seen[phase]) { phaseToStepId[phase] = s.id; seen[phase] = true }
    }
  }

  // Total planned queries = from plan (or at least 1)
  const totalQueries = plannedQueryCount || queryGroups.length || 1
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
                // Active if this step is in the currently-active query group and matches orchPhase
                const isActive = !allComplete && hasPipeline && group.queryIndex - 1 === effectiveActiveIdx && STEP_TO_PHASE[step.step_type] === orchPhase
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
              const isActive = !allComplete && hasPipeline && phase === orchPhase
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
