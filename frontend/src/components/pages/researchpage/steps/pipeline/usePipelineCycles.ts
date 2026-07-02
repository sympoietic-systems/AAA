import { useMemo } from "react"
import type { TaskStepsResponse, ResearchStep, StepPreview } from "../../../../../api/research"
import { STEP_TO_PHASE } from "../../constants/taskConstants"
import { getPlanQueryCount } from "./helpers"
import type { Cycle, QueryGroup, PipelineModel } from "./types"

const CYCLE_PHASES = ["search", "parallel_parse", "digest"] as const

/** Build the plan-driven cycle model from raw steps, orchestrator phase, and live preview. */
export function usePipelineCycles(
  data: TaskStepsResponse | null,
  orchPhase: string,
  preview: StepPreview | null,
): PipelineModel {
  return useMemo(() => {
    const empty: PipelineModel = {
      cycles: [],
      activeGroupIdx: -1,
      planQueries: [],
      activeDepth: 0,
    }
    if (!data) return empty

    const steps = [...data.steps]
    const planQueryCount = getPlanQueryCount(data)
    const totalQ = planQueryCount || 1

    const getStepDepth = (step: ResearchStep): number => {
      if (!step.step_data) return 0
      try {
        const parsed = JSON.parse(step.step_data)
        return typeof parsed.depth === "number" ? parsed.depth : 0
      } catch {
        return 0
      }
    }

    const getPlanQueriesFromStep = (step: ResearchStep | null): string[] => {
      if (!step?.step_data) return []
      try {
        const parsed = JSON.parse(step.step_data)
        if (parsed.plan?.search_queries) return parsed.plan.search_queries
      } catch {}
      return []
    }

    const globalPlanQueries: string[] = []
    try {
      if (data?.plan?.plan_json) {
        const pj = JSON.parse(data.plan.plan_json)
        globalPlanQueries.push(...(pj.search_queries || []))
      }
    } catch {}

    let actDepth = 0
    if (steps.length > 0) {
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

    const cyclesList: Cycle[] = []
    for (let d = 0; d <= actDepth; d++) {
      const depthSteps = steps.filter(s => getStepDepth(s) === d)

      const depthPlan = depthSteps.find(s => s.step_type === "plan") ??
        (d === actDepth && orchPhase === "planning" ? { id: "", step_type: "plan", status: "pending" } as ResearchStep : null)

      const depthPlanQueries = getPlanQueriesFromStep(depthPlan)
      const queryGroupsInDepth = Array.from(new Set(depthSteps.map(s => s.query_group).filter(Boolean))) as number[]
      const depthQCount = queryGroupsInDepth.length || (d === actDepth ? (previewQueryCount || totalQ) : 1)

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

      const reflectStep = depthSteps.find(s => s.step_type === "reflect") ||
        ({ id: "", step_type: "reflect", step_number: 0, status: "pending" } as ResearchStep)

      const reflectionStep = depthSteps.find(s => s.step_type === "reflection") ||
        (d === actDepth && orchPhase === "reflection" ? { id: "", step_type: "reflection", status: "pending" } as ResearchStep : null)

      const evaluateStep = depthSteps.find(s => s.step_type === "evaluate") ||
        ({ id: "", step_type: "evaluate", step_number: 0, status: "pending" } as ResearchStep)

      const docDigestStep = depthSteps.find(s => s.step_type === "document_digestion") ||
        (d === actDepth && orchPhase === "document_digestion" ? { id: "", step_type: "document_digestion", status: "pending" } as ResearchStep : null)

      const synthesizeStep = depthSteps.find(s => s.step_type === "synthesize") ||
        (d === actDepth && orchPhase === "synthesizing" ? { id: "", step_type: "synthesize", status: "pending" } as ResearchStep : null)

      cyclesList.push({
        depth: d,
        planStep: depthPlan,
        documentDigestionStep: docDigestStep,
        groups,
        reflectStep,
        reflectionStep,
        evaluateStep,
        synthesizeStep,
        queryTexts,
        planQueries: depthPlanQueries,
      })
    }

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
      activeGroupIdx: activeGIdx,
      planQueries: globalPlanQueries,
      activeDepth: actDepth,
    }
  }, [data, orchPhase, preview])
}
