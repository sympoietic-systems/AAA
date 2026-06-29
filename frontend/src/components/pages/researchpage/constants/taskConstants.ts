// Shared constants for research task views.
// Single source of truth — used by ResearchTaskPage and ResearchDetailPanel.

import { CSS_VARS } from "../../../../config/colors"

export const STATUS_COLORS: Record<string, string> = {
  proposed: CSS_VARS.semanticGold,
  approved: CSS_VARS.semanticBlue,
  queued: CSS_VARS.semanticPurple,
  active: CSS_VARS.semanticGreen,
  completed: CSS_VARS.semanticSlate,
  failed: CSS_VARS.semanticRed,
  cancelled: CSS_VARS.uiDim,
  rejected: CSS_VARS.semanticSand,
  expired: CSS_VARS.uiDim,
}

export const STEP_LABELS: Record<string, string> = {
  plan: "Plan", search: "Search", parallel_parse: "Parse Sources",
  digest: "Digest", reflect: "Consolidate", synthesize: "Synthesize",
  evaluate: "Evaluate", document_digestion: "Document Digest",
}

export const STEP_TO_PHASE: Record<string, string> = {
  plan: "planning", search: "searching", parallel_parse: "parsing",
  digest: "digesting", reflect: "reflecting", evaluate: "evaluating",
  synthesize: "synthesizing", document_digestion: "document_digestion",
}

export const PHASE_ORDER_DISPLAY = [
  "planning", "document_digestion", "searching", "parsing", "digesting",
  "reflecting", "evaluating", "synthesizing",
]

export const PHASE_LABELS: Record<string, string> = {
  planning: "Plan", document_digestion: "Document Digest",
  searching: "Search", parsing: "Parse Sources",
  digesting: "Digest", reflecting: "Consolidate", evaluating: "Evaluate",
  synthesizing: "Synthesize", complete: "Complete",
}

export const STEP_TYPE_COLORS: Record<string, string> = {
  search: CSS_VARS.semanticBlue,
  parallel_parse: CSS_VARS.semanticSand,
  digest: CSS_VARS.semanticPurple,
  document_digestion: CSS_VARS.semanticSand,
  reflect: CSS_VARS.semanticSlate,
  synthesize: CSS_VARS.semanticGreen,
  evaluate: CSS_VARS.semanticGold,
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
  orchestrator_document_digest_prompt: "Document Digest Prompt",
  orchestrator_document_digest_response: "Document Digest Response",
  orchestrator_document_digest_error: "Document Digest Error",
  orchestrator_document_digest_complete: "Document Digest Complete",
  orchestrator_reflect: "Consolidate Result",
  orchestrator_reflect_prompt: "Consolidate Prompt",
  orchestrator_reflect_response: "Consolidate Response",
  orchestrator_evaluate: "Evaluate",
  orchestrator_synthesize_start: "Synthesize Start",
  orchestrator_synthesize_prompt: "Synthesize Prompt",
  orchestrator_synthesize_response: "Synthesize Response",
  orchestrator_complete: "Orch Complete",
  orchestrator_step_complete: "Step Done",
}

export const EVENT_TYPE_COLORS: Record<string, string> = {
  task_started: CSS_VARS.semanticGreen,
  task_complete: CSS_VARS.semanticBlue,
  query_generation: CSS_VARS.semanticPurple,
  branch_create: CSS_VARS.semanticSand,
  fetch_complete: CSS_VARS.semanticSlate,
  fetch_error: CSS_VARS.semanticRed,
  llm_prompt: CSS_VARS.semanticPurple,
  llm_response: CSS_VARS.semanticPurple,
  llm_error: CSS_VARS.semanticRed,
  synthesis_start: CSS_VARS.semanticGold,
  synthesis_complete: CSS_VARS.semanticGreen,
  synthesis_error: CSS_VARS.semanticRed,
  orchestrator_start: CSS_VARS.semanticGreen,
  orchestrator_plan: CSS_VARS.semanticPurple,
  orchestrator_plan_prompt: CSS_VARS.semanticPurple,
  orchestrator_plan_response: CSS_VARS.semanticPurple,
  orchestrator_replan: CSS_VARS.semanticSand,
  orchestrator_search: CSS_VARS.semanticBlue,
  orchestrator_digest_prompt: CSS_VARS.semanticPurple,
  orchestrator_digest_response: CSS_VARS.semanticPurple,
  orchestrator_digest_error: CSS_VARS.semanticRed,
  orchestrator_document_digest_prompt: CSS_VARS.semanticPurple,
  orchestrator_document_digest_response: CSS_VARS.semanticPurple,
  orchestrator_document_digest_error: CSS_VARS.semanticRed,
  orchestrator_document_digest_complete: CSS_VARS.semanticGreen,
  orchestrator_reflect: CSS_VARS.semanticPurple,
  orchestrator_reflect_prompt: CSS_VARS.semanticPurple,
  orchestrator_reflect_response: CSS_VARS.semanticPurple,
  orchestrator_evaluate: CSS_VARS.semanticGold,
  orchestrator_synthesize_start: CSS_VARS.semanticGold,
  orchestrator_synthesize_prompt: CSS_VARS.semanticPurple,
  orchestrator_synthesize_response: CSS_VARS.semanticPurple,
  orchestrator_complete: CSS_VARS.semanticBlue,
  orchestrator_step_complete: CSS_VARS.semanticGreen,
}
