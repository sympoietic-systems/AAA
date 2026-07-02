import type { ResearchStep, ResearchStepResult } from "../../../../../api/research"
import type { NotableContentHooks } from "../../../../shared/NotableContent"

/** Shape of the pre-parsed result payload passed to every result renderer. */
export interface ParsedResult {
  queries: string[]
  goal: string
  completeness: number
  answer: string
  confidence: number
  learnings: string[]
  reflection?: string
  key_insights?: string[]
  remaining_gaps?: string[]
  next_queries?: string[]
  next_direct_urls?: string[]
  reflection_notes?: string
  detected_biases?: string[]
  knowledge_gaps?: string[]
  glitch_fidelity?: number
  contradiction_density?: number
  source_entropy?: number
  signal_flags?: string[]
  refined_queries?: string[]
  revised_confidence?: number
  monologue_trace?: any[]
  critique_log?: any[]
  diffractive_audit?: string
  diffractive_audit_description?: string
}

/** Common props shared by the result renderers (each uses the subset it needs). */
export interface ResultRendererProps {
  selected: ResearchStep
  selectedResults: ResearchStepResult[]
  parsedResult: ParsedResult
  responseEntries: any[]
  inputEntries?: any[]
  noteHook: NotableContentHooks
}
