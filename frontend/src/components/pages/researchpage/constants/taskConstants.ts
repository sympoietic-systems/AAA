// Shared constants for research task views.
// Single source of truth — used by ResearchTaskPage and ResearchDetailPanel.

export const STATUS_COLORS: Record<string, string> = {
  proposed: "#f59e0b", approved: "#3b82f6", queued: "#8b5cf6",
  active: "#4ade80", completed: "#22d3ee", failed: "#ef4444",
  cancelled: "#666666", rejected: "#f97316", expired: "#444444",
}

export const STEP_LABELS: Record<string, string> = {
  plan: "Plan", search: "Search", parallel_parse: "Parse Sources",
  digest: "Digest", reflect: "Reflect", synthesize: "Synthesize",
  evaluate: "Evaluate",
}

export const STEP_TO_PHASE: Record<string, string> = {
  plan: "planning", search: "searching", parallel_parse: "parsing",
  digest: "digesting", reflect: "reflecting", evaluate: "evaluating",
  synthesize: "synthesizing",
}

export const PHASE_ORDER_DISPLAY = [
  "planning", "searching", "parsing", "digesting", "reflecting", "evaluating", "synthesizing",
]

export const PHASE_LABELS: Record<string, string> = {
  planning: "Plan", searching: "Search", parsing: "Parse Sources",
  digesting: "Digest", reflecting: "Reflect", evaluating: "Evaluate",
  synthesizing: "Synthesize", complete: "Complete",
}

export const STEP_TYPE_COLORS: Record<string, string> = {
  search: "#3b82f6",
  parallel_parse: "#f59e0b",
  digest: "#a892ee",
  reflect: "#c084fc",
  synthesize: "#4ade80",
  evaluate: "#22d3ee",
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  task_started: "Task Started",
  task_complete: "Task Complete",
  query_generation: "Query Generation",
  branch_create: "Branch Created",
  fetch_complete: "Fetch Complete",
  fetch_error: "Fetch Error",
  llm_prompt: "LLM Prompt",
  llm_response: "LLM Response",
  llm_error: "LLM Error",
  synthesis_start: "Synthesis Start",
  synthesis_complete: "Synthesis Complete",
  synthesis_error: "Synthesis Error",
  orchestrator_start: "Orch Start",
  orchestrator_plan: "Plan Result",
  orchestrator_plan_prompt: "Plan Prompt",
  orchestrator_plan_response: "Plan Response",
  orchestrator_replan: "Re-Plan",
  orchestrator_search: "Search",
  orchestrator_digest_prompt: "Digest Prompt",
  orchestrator_digest_response: "Digest Response",
  orchestrator_digest_error: "Digest Error",
  orchestrator_reflect: "Reflect Result",
  orchestrator_reflect_prompt: "Reflect Prompt",
  orchestrator_reflect_response: "Reflect Response",
  orchestrator_evaluate: "Evaluate",
  orchestrator_synthesize_start: "Synthesize Start",
  orchestrator_synthesize_prompt: "Synthesize Prompt",
  orchestrator_synthesize_response: "Synthesize Response",
  orchestrator_complete: "Orch Complete",
  orchestrator_step_complete: "Step Done",
}

export const EVENT_TYPE_COLORS: Record<string, string> = {
  task_started: "#4ade80",
  task_complete: "#22d3ee",
  query_generation: "#a78bfa",
  branch_create: "#f59e0b",
  fetch_complete: "#3b82f6",
  fetch_error: "#ef4444",
  llm_prompt: "#c084fc",
  llm_response: "#a892ee",
  llm_error: "#ef4444",
  synthesis_start: "#facc15",
  synthesis_complete: "#4ade80",
  synthesis_error: "#ef4444",
  orchestrator_start: "#4ade80",
  orchestrator_plan: "#a78bfa",
  orchestrator_plan_prompt: "#c084fc",
  orchestrator_plan_response: "#a892ee",
  orchestrator_replan: "#f59e0b",
  orchestrator_search: "#3b82f6",
  orchestrator_digest_prompt: "#c084fc",
  orchestrator_digest_response: "#a892ee",
  orchestrator_digest_error: "#ef4444",
  orchestrator_reflect: "#a78bfa",
  orchestrator_reflect_prompt: "#c084fc",
  orchestrator_reflect_response: "#a892ee",
  orchestrator_evaluate: "#22d3ee",
  orchestrator_synthesize_start: "#facc15",
  orchestrator_synthesize_prompt: "#c084fc",
  orchestrator_synthesize_response: "#a892ee",
  orchestrator_complete: "#22d3ee",
  orchestrator_step_complete: "#4ade80",
}

/** Determine phase status relative to current orchestrator phase index */
export function phaseStatus(idx: number, currentIdx: number): "done" | "current" | "pending" {
  if (currentIdx < 0) return "pending"
  if (idx < currentIdx) return "done"
  if (idx === currentIdx) return "current"
  return "pending"
}
