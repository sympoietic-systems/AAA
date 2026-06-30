import { memo, useMemo, useState } from "react"
import type { TaskStepsResponse, ResearchStep, StepPreview } from "../../../../api/research"
import { TerminalButton } from "../../../UI"
import {
  STEP_TO_PHASE, STEP_LABELS, PHASE_LABELS,
} from "../constants/taskConstants"

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
}

interface QueryGroup {
  steps: ResearchStep[]
  queryIndex: number
}

const CYCLE_PHASES = ["search", "parallel_parse", "digest"] as const

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
  // Document digestion: "5 learnings, 3 followups from doc file.pdf (7 chunks)" → "(5L + 3F)"
  const docDigest = summary.match(/(\d+)\s+learnings?[,\s]+(\d+)\s+followups?/i)
  if (docDigest) return ` (${docDigest[1]}L + ${docDigest[2]}F)`
  // Document digestion: "No relevant document chunks found for digestion" → "(0)"
  const noChunks = summary.match(/no relevant/)
  if (noChunks) return " (0)"
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
  const sc = isStale ? "var(--color-semantic-sand)" : isDone ? "var(--color-semantic-green)" : isCurrent ? "var(--color-semantic-gold)" : "var(--color-ui-dim)"
  const canClick = (isDone || isStale) ? !!stepId : isCurrent

  const handleClick = () => {
    if (!canClick) return
    if (isSelected) {
      onSelect(null)
    } else if (stepId) {
      onSelect(stepId)
    } else {
      onSelect(null)
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`flex items-center gap-2 text-[10px] px-2 py-1 rounded-sm transition-all
        ${canClick ? "cursor-pointer hover:bg-[#111]" : ""}
        ${isCurrent ? "bg-action-hover/5 border border-semantic-gold/20" : ""}
        ${isStale ? "bg-action-hover/5 border border-semantic-sand/10" : ""}
        ${isSelected ? "border border-action-hover/20 bg-action-hover/5" : ""}`}
    >
      <span style={{ color: sc }} className="text-[8px] shrink-0 w-3 font-mono">
        {isStale ? "⟳" : isDone ? "✔" : isCurrent ? "▶" : "○"}
      </span>
      <span className={`font-mono flex-1 ${isSelected ? "text-action-hover" : isStale ? "text-semantic-sand/80" : isDone ? "text-ui-secondary" : isCurrent ? "text-semantic-gold" : "text-ui-dim"}`}>
        {label}{isStale ? " (stale)" : ""}
      </span>
      {isCurrent && (
        <button onClick={e => { e.stopPropagation(); onDoStep() }} disabled={stepping}
          className="text-action-dim hover:text-action-hover text-[9px] font-mono disabled:text-[#333] cursor-pointer transition-colors">
          [{stepping ? "…" : "▶ run"}]
        </button>
      )}
    </div>
  )
}

export const StepPipeline = memo(function StepPipeline({
  data, preview, orchPhase, taskStatus, selectedId, stepping,
  onSelect, onDoStep, onDoRerun,
}: StepPipelineProps) {
  const allComplete = taskStatus === "completed" && orchPhase === "complete"
  const hasPipeline = orchPhase && orchPhase !== "complete" && orchPhase !== "not_started"

  // ── Plan-driven grouping using query_group and depth from DB ──
  const { cycles, synthesizeStep, activeGroupIdx, planQueries, activeDepth } = useMemo(() => {
    const empty = {
      cycles: [] as {
        depth: number
        planStep: ResearchStep | null
        documentDigestionStep: ResearchStep | null
        groups: QueryGroup[]
        reflectStep: ResearchStep
        evaluateStep: ResearchStep
        queryTexts: Record<number, string>
        planQueries: string[]
      }[],
      synthesizeStep: null as ResearchStep | null,
      activeGroupIdx: -1,
      planQueries: [] as string[],
      activeDepth: 0,
    }
    if (!data) return empty

    const steps = [...data.steps]
    const planQueryCount = getPlanQueryCount(data)
    const totalQ = planQueryCount || 1

    // Helper to retrieve depth from step_data JSON
    const getStepDepth = (step: ResearchStep): number => {
      if (!step.step_data) return 0
      try {
        const parsed = JSON.parse(step.step_data)
        return typeof parsed.depth === "number" ? parsed.depth : 0
      } catch {
        return 0
      }
    }

    // Helper to extract plan queries from a plan step's step_data
    const getPlanQueriesFromStep = (step: ResearchStep | null): string[] => {
      if (!step?.step_data) return []
      try {
        const parsed = JSON.parse(step.step_data)
        if (parsed.plan?.search_queries) return parsed.plan.search_queries
      } catch {}
      return []
    }

    // Global fallback: latest plan from plan_repo
    const globalPlanQueries: string[] = []
    try {
      if (data?.plan?.plan_json) {
        const pj = JSON.parse(data.plan.plan_json)
        globalPlanQueries.push(...(pj.search_queries || []))
      }
    } catch {}

    // Infer the current active depth
    let actDepth = 0
    if (steps.length > 0) {
      // Find the maximum depth across all steps in the database
      let maxStepDepth = 0
      for (const step of steps) {
        const d = getStepDepth(step)
        if (d > maxStepDepth) {
          maxStepDepth = d
        }
      }

      const latestStep = steps[steps.length - 1]
      const latestDepth = getStepDepth(latestStep)
      if (latestStep.step_type === "evaluate" && ["searching", "parsing", "digesting"].includes(orchPhase)) {
        actDepth = Math.max(maxStepDepth, latestDepth + 1)
      } else {
        actDepth = maxStepDepth
      }
    }

    if (data && typeof data.current_depth === "number") {
      actDepth = Math.max(actDepth, data.current_depth)
    }

    // Calculate active query count from preview if available
    let previewQueryCount = 0
    if (preview) {
      if (preview.pending_queries && preview.pending_queries.length > 0) {
        previewQueryCount = preview.pending_queries.length
      } else if (preview.urls_to_fetch && preview.urls_to_fetch.length > 0) {
        const groups = preview.urls_to_fetch.map(u => u.query_group).filter(Boolean) as number[]
        if (groups.length > 0) {
          previewQueryCount = Math.max(...groups)
        }
      } else if (preview.sources_to_digest && preview.sources_to_digest.length > 0) {
        const groups = preview.sources_to_digest.map(s => s.query_group).filter(Boolean) as number[]
        if (groups.length > 0) {
          previewQueryCount = Math.max(...groups)
        }
      }
    }

    // Build cycles list
    const cyclesList = []
    for (let d = 0; d <= actDepth; d++) {
      const depthSteps = steps.filter(s => getStepDepth(s) === d)
      
      // Plan step for this depth
      const depthPlan = depthSteps.find(s => s.step_type === "plan") ?? 
        (d === actDepth && orchPhase === "planning" ? { id: "", step_type: "plan", status: "pending" } as ResearchStep : null)
      
      const depthPlanQueries = getPlanQueriesFromStep(depthPlan)
      // Determine how many query groups to display for this depth
      const queryGroupsInDepth = Array.from(new Set(depthSteps.map(s => s.query_group).filter(Boolean))) as number[]
      const depthQCount = queryGroupsInDepth.length || (d === actDepth ? (previewQueryCount || totalQ) : 1)
      
      // Get query text maps if any
      const queryTexts: Record<number, string> = {}
      for (const s of depthSteps) {
        if (s.step_type === "search" && s.query_group && s.query_text) {
          queryTexts[s.query_group] = s.query_text
        }
      }

      const groups: QueryGroup[] = []
      for (let q = 1; q <= depthQCount; q++) {
        const groupSteps: ResearchStep[] = []
        for (const ct of CYCLE_PHASES) {
          const match = depthSteps.find(s => s.step_type === ct && s.query_group === q)
          if (match) {
            groupSteps.push(match)
          } else {
            groupSteps.push({ id: "", step_type: ct, step_number: 0, status: "pending", query_group: q } as any)
          }
        }
        groups.push({ queryIndex: q, steps: groupSteps })
      }

      // Find reflect and evaluate steps for this depth
      const reflectStep = depthSteps.find(s => s.step_type === "reflect") || 
        ({ id: "", step_type: "reflect", step_number: 0, status: "pending" } as ResearchStep)
        
      const evaluateStep = depthSteps.find(s => s.step_type === "evaluate") || 
        ({ id: "", step_type: "evaluate", step_number: 0, status: "pending" } as ResearchStep)

      const docDigestStep = depthSteps.find(s => s.step_type === "document_digestion") || 
        (d === actDepth && orchPhase === "document_digestion" ? { id: "", step_type: "document_digestion", status: "pending" } as ResearchStep : null)

      cyclesList.push({
        depth: d,
        planStep: depthPlan,
        documentDigestionStep: docDigestStep,
        groups,
        reflectStep,
        evaluateStep,
        queryTexts,
        planQueries: depthPlanQueries,
      })
    }

    // Find synthesize step
    const synth = steps.find(s => s.step_type === "synthesize") || 
      ({ id: "", step_type: "synthesize", step_number: 0, status: "pending" } as ResearchStep)

    // Active step: first non-completed step matching orchPhase in the active cycle
    let activeGIdx = -1
    if (actDepth < cyclesList.length) {
      const activeCycle = cyclesList[actDepth]
      for (let g = 0; g < activeCycle.groups.length; g++) {
        for (const s of activeCycle.groups[g].steps) {
          if (s.status !== "completed" && STEP_TO_PHASE[s.step_type] === orchPhase) {
            activeGIdx = g
            break
          }
        }
        if (activeGIdx >= 0) break
      }
    }

    return { 
      cycles: cyclesList, 
      synthesizeStep: synth, 
      activeGroupIdx: activeGIdx, 
      planQueries: globalPlanQueries, 
      activeDepth: actDepth 
    }
  }, [data, orchPhase, preview])

  // Results by step for count labels
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

        {/* Cycles list */}
        {cycles.map((cycle) => {
          const isCycleCurrent = cycle.depth === activeDepth
          const collapsed = isCollapsed(cycle.depth)
          return (
            <div key={cycle.depth} className="border border-ui-border rounded-sm p-1.5 mb-2 bg-ui-card">
              <div
                onClick={() => toggleCycle(cycle.depth)}
                className="text-ui-secondary font-mono text-[9px] uppercase tracking-wider mb-1.5 border-b border-ui-border pb-0.5 flex justify-between items-center cursor-pointer select-none hover:text-ui-primary transition-colors"
              >
                <span>Cycle {cycle.depth + 1} (Depth {cycle.depth})</span>
                <span className="text-ui-dim text-[8px] font-mono shrink-0 select-none">
                  {collapsed ? "[+ expand]" : "[- collapse]"}
                </span>
              </div>

              {!collapsed && (
                <>
                  {/* Plan step for this cycle */}
                  {cycle.planStep && (
                    <div className="mb-2 pl-1.5 border-l border-ui-border/50">
                      {(() => {
                        const ps = cycle.planStep
                        const stale = ps.status === "stale"
                        const suffix = (stale || ps.status === "completed") ? stepCountSuffix(ps, resultsByStep) : ""
                        const pending = ps.id ? "" : " —"
                        const done = allComplete || ps.status === "completed" || stale
                        const isActive = !allComplete && hasPipeline && isCycleCurrent && orchPhase === "planning" && ps.status !== "completed"
                        return (
                          <PipelineRow
                            label={`Plan${suffix}${pending}${ps.status === "completed" ? "" : allComplete ? "" : " (" + ps.status + ")"}`}
                            stepId={ps.id || null}
                            isDone={done}
                            isCurrent={isActive}
                            isStale={stale}
                            isSelected={ps.id ? selectedId === ps.id : (selectedId === null && isActive)}
                            onSelect={onSelect}
                            onDoStep={onDoStep}
                            stepping={stepping}
                          />
                        )
                      })()}
                    </div>
                  )}
                  {/* Document digestion step for this cycle */}
                  {cycle.documentDigestionStep && (
                    <div className="mb-2 pl-1.5 border-l border-ui-border/50">
                      {(() => {
                        const ds = cycle.documentDigestionStep
                        const stale = ds.status === "stale"
                        const suffix = (stale || ds.status === "completed") ? stepCountSuffix(ds, resultsByStep) : ""
                        const pending = ds.id ? "" : " —"
                        const done = allComplete || ds.status === "completed" || stale
                        const isActive = !allComplete && hasPipeline && isCycleCurrent && orchPhase === "document_digestion" && ds.status !== "completed"
                        return (
                          <PipelineRow
                            label={`Document Digest${suffix}${pending}${ds.status === "completed" ? "" : allComplete ? "" : " (" + ds.status + ")"}`}
                            stepId={ds.id || null}
                            isDone={done}
                            isCurrent={isActive}
                            isStale={stale}
                            isSelected={ds.id ? selectedId === ds.id : (selectedId === null && isActive)}
                            onSelect={onSelect}
                            onDoStep={onDoStep}
                            stepping={stepping}
                          />
                        )
                      })()}
                    </div>
                  )}
                  {/* Query groups inside this cycle */}
                  {cycle.groups.map((group) => {
                    const depthQ = cycle.planQueries.length > 0 ? cycle.planQueries : planQueries
                    let qText = cycle.queryTexts[group.queryIndex] || ""
                    if (!qText && group.queryIndex <= depthQ.length) {
                      qText = depthQ[group.queryIndex - 1]
                    }

                    if (!qText && cycle.depth === activeDepth && preview && preview.pending_queries) {
                      const pq = preview.pending_queries[group.queryIndex - 1]
                      if (pq) {
                        qText = pq
                      }
                    }

                    const qDisplay = qText ? `"${qText.slice(0, 60)}${qText.length > 60 ? "…" : ""}"` : ""
                    const queryLabel = `Q${group.queryIndex}/${cycle.groups.length}${qDisplay ? `: ${qDisplay}` : ""}`
                    return (
                      <div key={group.queryIndex} className="mb-2 pl-1.5 border-l border-ui-border">
                        <div className="text-ui-dim text-[8px] tracking-wider mb-0.5 font-mono">{queryLabel}</div>
                        {group.steps.map((step) => {
                          const baseLabel = STEP_LABELS[step.step_type] || step.step_type
                          const stale = step.status === "stale"
                          const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
                          const pending = step.id ? "" : " —"
                          const done = allComplete || step.status === "completed" || stale
                          // Active: first non-completed step matching orchPhase in the active group
                          const isActive = !allComplete && hasPipeline
                            && isCycleCurrent
                            && group.queryIndex - 1 === activeGroupIdx
                            && STEP_TO_PHASE[step.step_type] === orchPhase
                            && step.status !== "completed"
                          return (
                            <PipelineRow
                              key={step.id || `${cycle.depth}-${group.queryIndex}-${step.step_type}`}
                              label={baseLabel + suffix + pending}
                              stepId={step.id || null}
                              isDone={done}
                              isCurrent={isActive}
                              isStale={stale}
                              isSelected={step.id ? selectedId === step.id : (selectedId === null && isActive)}
                              onSelect={onSelect}
                              onDoStep={onDoStep}
                              stepping={stepping}
                            />
                          )
                        })}
                      </div>
                    )
                  })}

                  {/* Cycle final steps: Reflect & Evaluate */}
                  <div className="pl-1.5 pt-1.5 border-t border-ui-border/50 mt-1 space-y-1">
                    {/* Reflect */}
                    {(() => {
                      const step = cycle.reflectStep
                      const phase = "reflecting"
                      const baseLabel = PHASE_LABELS[phase] || step.step_type
                      const stale = step.status === "stale"
                      const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
                      const pending = step.id ? "" : " —"
                      const done = allComplete || step.status === "completed" || stale
                      const isActive = !allComplete && hasPipeline && isCycleCurrent && phase === orchPhase && step.status !== "completed"
                      return (
                        <PipelineRow
                          key={step.id || `${cycle.depth}-reflect`}
                          label={baseLabel + suffix + pending}
                          stepId={step.id || null}
                          isDone={done}
                          isCurrent={isActive}
                          isStale={stale}
                          isSelected={step.id ? selectedId === step.id : (selectedId === null && isActive)}
                          onSelect={onSelect}
                          onDoStep={onDoStep}
                          stepping={stepping}
                        />
                      )
                    })()}

                    {/* Evaluate */}
                    {(() => {
                      const step = cycle.evaluateStep
                      const phase = "evaluating"
                      const baseLabel = PHASE_LABELS[phase] || step.step_type
                      const stale = step.status === "stale"
                      const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
                      const pending = step.id ? "" : " —"
                      const done = allComplete || step.status === "completed" || stale
                      const isActive = !allComplete && hasPipeline && isCycleCurrent && phase === orchPhase && step.status !== "completed"
                      return (
                        <PipelineRow
                          key={step.id || `${cycle.depth}-evaluate`}
                          label={baseLabel + suffix + pending}
                          stepId={step.id || null}
                          isDone={done}
                          isCurrent={isActive}
                          isStale={stale}
                          isSelected={step.id ? selectedId === step.id : (selectedId === null && isActive)}
                          onSelect={onSelect}
                          onDoStep={onDoStep}
                          stepping={stepping}
                        />
                      )
                    })()}
                  </div>
                </>
              )}
            </div>
          )
        })}

        {/* Global Synthesize step */}
        {synthesizeStep && (
          <div className="pl-1.5 pt-2 border-t border-ui-border mt-2">
            {(() => {
              const step = synthesizeStep
              const phase = "synthesizing"
              const baseLabel = PHASE_LABELS[phase] || step.step_type
              const stale = step.status === "stale"
              const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
              const pending = step.id ? "" : " —"
              const done = allComplete || step.status === "completed" || stale
              const isActive = !allComplete && hasPipeline && phase === orchPhase && step.status !== "completed"
              return (
                <PipelineRow
                  key={step.id || "synthesize"}
                  label={baseLabel + suffix + pending}
                  stepId={step.id || null}
                  isDone={done}
                  isCurrent={isActive}
                  isStale={stale}
                  isSelected={step.id ? selectedId === step.id : (selectedId === null && isActive)}
                  onSelect={onSelect}
                  onDoStep={onDoStep}
                  stepping={stepping}
                />
              )
            })()}
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
