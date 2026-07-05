import type { ResearchStep, TaskStepsResponse } from "../../../../../api/research"

/** Format the hierarchical step ID from phase_group, query_group, sub_sequence. */
export function formatStepId(step: ResearchStep): string {
  const pg = step.phase_group ?? step.step_number
  const qg = step.query_group ?? 0
  const ss = step.sub_sequence ?? 0
  if (qg > 0) {
    return `${pg}.${qg}.${ss}`
  }
  return `${pg}`
}

/** Parse result_summary or results_by_step into a compact count label. */
export function stepCountSuffix(step: ResearchStep, resultsByStep: Record<string, unknown[]>): string {
  const summary = step.result_summary || ""
  const hits = summary.match(/^(\d+)\s+results?$/i)
  if (hits) return ` (${hits[1]} hits)`
  const parsed = summary.match(/parsed\s+(\d+)\s+sources?/i)
  if (parsed) return ` (${parsed[1]} urls)`
  const digested = summary.match(/digested\s+(\d+)\s+sources?/i)
  if (digested) return ` (${digested[1]} analyzed)`
  const completeness = summary.match(/completeness:\s*([\d.]+)/i)
  if (completeness) return ` (${Math.round(parseFloat(completeness[1]) * 100)}%)`
  const docDigest = summary.match(/(\d+)\s+learnings?[,\s]+(\d+)\s+followups?/i)
  if (docDigest) return ` (${docDigest[1]}L + ${docDigest[2]}F)`
  const noChunks = summary.match(/no relevant/)
  if (noChunks) return " (0)"
  if (step.id && resultsByStep[step.id]) {
    const n = resultsByStep[step.id].length
    if (n > 0) return ` (${n})`
  }
  return ""
}

/** Safely parse plan_json to get search_queries count. */
export function getPlanQueryCount(data: TaskStepsResponse | null): number {
  if (!data?.plan?.plan_json) return 0
  try {
    const plan = JSON.parse(data.plan.plan_json)
    return Array.isArray(plan.search_queries) ? plan.search_queries.length : 0
  } catch { return 0 }
}

/** Safely extract transition rationale from step_data JSON. */
export function getStepRationale(step: ResearchStep | null): string | null {
  if (!step?.step_data) return null
  try {
    const parsed = JSON.parse(step.step_data)
    return parsed.transition_rationale || null
  } catch { return null }
}
