import { memo } from "react"
import type { ResearchStep, StepPreview } from "../../../../../api/research"
import { STEP_TO_PHASE, STEP_LABELS, PHASE_LABELS } from "../../constants/taskConstants"
import { PipelineRow } from "./PipelineRow"
import { stepCountSuffix, getStepRationale, formatStepId } from "./helpers"
import type { Cycle } from "./types"

interface CycleBlockProps {
  cycle: Cycle
  collapsed: boolean
  onToggle: (depth: number) => void
  allComplete: boolean
  hasPipeline: boolean
  orchPhase: string
  selectedId: string | null
  stepping: boolean
  activeDepth: number
  activeGroupIdx: number
  planQueries: string[]
  preview: StepPreview | null
  resultsByStep: Record<string, unknown[]>
  onSelect: (id: string | null) => void
  onDoStep: () => void
  onRerunPhase: (stepType: string) => void
}

export const CycleBlock = memo(function CycleBlock({
  cycle, collapsed, onToggle, allComplete, hasPipeline, orchPhase, selectedId, stepping,
  activeDepth, activeGroupIdx, planQueries, preview, resultsByStep, onSelect, onDoStep, onRerunPhase,
}: CycleBlockProps) {
  const isCycleCurrent = cycle.depth === activeDepth

  const renderRow = (step: ResearchStep, phase: string, baseLabel: string, keySuffix: string) => {
    const stale = step.status === "stale"
    const failed = step.status === "failed"
    const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
    const pending = step.id ? "" : " —"
    const done = !failed && (allComplete || step.status === "completed" || stale)
    const isActive = !allComplete && hasPipeline && isCycleCurrent && phase === orchPhase && step.status !== "completed" && step.status !== "failed"
    const stepIdPrefix = (step.phase_group != null || step.sub_sequence != null)
      ? `[${formatStepId(step)}] ` : ""
    return (
      <PipelineRow
        key={step.id || `${cycle.depth}-${keySuffix}`}
        label={stepIdPrefix + baseLabel + suffix + pending}
        stepId={step.id || null}
        stepType={step.step_type || null}
        isDone={done}
        isCurrent={isActive}
        isStale={stale}
        isFailed={failed}
        isSelected={step.id ? selectedId === step.id : (selectedId === null && isActive)}
        rationale={getStepRationale(step)}
        onSelect={onSelect}
        onDoStep={onDoStep}
        onRerunPhase={onRerunPhase}
        stepping={stepping}
      />
    )
  }

  return (
    <div className="mb-2">
      <div
        onClick={() => onToggle(cycle.depth)}
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
                const ps = cycle.planStep!
                const stale = ps.status === "stale"
                const failed = ps.status === "failed"
                const suffix = (stale || ps.status === "completed") ? stepCountSuffix(ps, resultsByStep) : ""
                const pending = ps.id ? "" : " —"
                const done = !failed && (allComplete || ps.status === "completed" || stale)
                const isActive = !allComplete && hasPipeline && isCycleCurrent && orchPhase === "planning" && ps.status !== "completed" && ps.status !== "failed"
                return (
                  <PipelineRow
                    label={`Plan${suffix}${pending}${ps.status === "completed" ? "" : allComplete ? "" : " (" + ps.status + ")"}`}
                    stepId={ps.id || null}
                    stepType={ps.step_type || null}
                    isDone={done}
                    isCurrent={isActive}
                    isStale={stale}
                    isFailed={failed}
                    isSelected={ps.id ? selectedId === ps.id : (selectedId === null && isActive)}
                    rationale={getStepRationale(ps)}
                    onSelect={onSelect}
                    onDoStep={onDoStep}
                    onRerunPhase={onRerunPhase}
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
                const ds = cycle.documentDigestionStep!
                const stale = ds.status === "stale"
                const failed = ds.status === "failed"
                const suffix = (stale || ds.status === "completed") ? stepCountSuffix(ds, resultsByStep) : ""
                const pending = ds.id ? "" : " —"
                const done = !failed && (allComplete || ds.status === "completed" || stale)
                const isActive = !allComplete && hasPipeline && isCycleCurrent && orchPhase === "document_digestion" && ds.status !== "completed" && ds.status !== "failed"
                return (
                  <PipelineRow
                    label={`Document Digest${suffix}${pending}${ds.status === "completed" ? "" : allComplete ? "" : " (" + ds.status + ")"}`}
                    stepId={ds.id || null}
                    stepType={ds.step_type || null}
                    isDone={done}
                    isCurrent={isActive}
                    isStale={stale}
                    isFailed={failed}
                    isSelected={ds.id ? selectedId === ds.id : (selectedId === null && isActive)}
                    rationale={getStepRationale(ds)}
                    onSelect={onSelect}
                    onDoStep={onDoStep}
                    onRerunPhase={onRerunPhase}
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
                  const failed = step.status === "failed"
                  const suffix = (stale || step.status === "completed") ? stepCountSuffix(step, resultsByStep) : ""
                  const pending = step.id ? "" : " —"
                  const done = !failed && (allComplete || step.status === "completed" || stale)
                  const isActive = !allComplete && hasPipeline
                    && isCycleCurrent
                    && group.queryIndex - 1 === activeGroupIdx
                    && STEP_TO_PHASE[step.step_type] === orchPhase
                    && step.status !== "completed"
                    && step.status !== "failed"
                  return (
                    <PipelineRow
                      key={step.id || `${cycle.depth}-${group.queryIndex}-${step.step_type}`}
                      label={baseLabel + suffix + pending}
                      stepId={step.id || null}
                      stepType={step.step_type || null}
                      isDone={done}
                      isCurrent={isActive}
                      isStale={stale}
                      isFailed={failed}
                      isSelected={step.id ? selectedId === step.id : (selectedId === null && isActive)}
                      rationale={getStepRationale(step)}
                      onSelect={onSelect}
                      onDoStep={onDoStep}
                      onRerunPhase={onRerunPhase}
                      stepping={stepping}
                    />
                  )
                })}
              </div>
            )
          })}

          {/* Cycle final steps: Reflect & Evaluate */}
          <div className="pl-1.5 pt-1.5 border-t border-ui-border/50 mt-1 space-y-1">
            {renderRow(cycle.reflectStep, "consolidating", PHASE_LABELS["consolidating"] || cycle.reflectStep.step_type, "reflect")}
            {cycle.reflectionStep && renderRow(cycle.reflectionStep, "reflection", PHASE_LABELS["reflection"] || cycle.reflectionStep.step_type, "reflection")}
            {renderRow(cycle.evaluateStep, "evaluating", PHASE_LABELS["evaluating"] || cycle.evaluateStep.step_type, "evaluate")}
            {cycle.synthesizeStep && renderRow(cycle.synthesizeStep, "synthesizing", PHASE_LABELS["synthesizing"] || cycle.synthesizeStep.step_type, "synthesize")}
          </div>
        </>
      )}
    </div>
  )
})
