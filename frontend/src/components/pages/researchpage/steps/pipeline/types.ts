import type { ResearchStep } from "../../../../../api/research"

export interface QueryGroup {
  steps: ResearchStep[]
  queryIndex: number
}

export interface Cycle {
  depth: number
  planStep: ResearchStep | null
  documentDigestionStep: ResearchStep | null
  groups: QueryGroup[]
  reflectStep: ResearchStep
  reflectionStep: ResearchStep | null
  evaluateStep: ResearchStep
  synthesizeStep: ResearchStep | null
  queryTexts: Record<number, string>
  planQueries: string[]
}

export interface PipelineModel {
  cycles: Cycle[]
  activeGroupIdx: number
  planQueries: string[]
  activeDepth: number
}
