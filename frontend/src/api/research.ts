// Research API — Autonomous Research Engine endpoints.
// See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 4.8.

import { BASE } from "./http"

export interface ResearchTask {
  id: string
  conversation_id: string | null
  title: string
  objective: string
  trigger_source: string
  status: string
  priority: number
  max_depth: number
  max_breadth: number
  is_agonistic: number
  budget_limit_usd: number
  budget_spent_usd: number
  branches_created: number
  assets_harvested: number
  lateral_flights: number
  bifurcation_triggered: number
  result_summary: string | null
  proposal_rationale: string | null
  proposal_message_id: number | null
  approved_by: string | null
  proposed_at: string | null
  approved_at: string | null
  started_at: string | null
  completed_at: string | null
  branches?: any[]
  assets?: { id: string; url: string; relevance_score: number; novelty_score: number; diffractive_score: number; created_at: string | null }[]
  asset_count?: number
}

export interface ResearchSummary {
  active_count: number
  queued_count: number
  pending_proposals: number
}

export interface DispatchPayload {
  objective: string
  title?: string
  conversation_id?: string
  max_depth?: number
  max_breadth?: number
  is_agonistic?: boolean
  budget_limit_usd?: number
}

// ── Queries ──────────────────────────────────────────────────────────

export async function getResearchTasks(params?: {
  status?: string
  trigger_source?: string
  conversation_id?: string
  limit?: number
}): Promise<ResearchTask[]> {
  const qs = new URLSearchParams()
  if (params?.status) qs.set("status", params.status)
  if (params?.trigger_source) qs.set("trigger_source", params.trigger_source)
  if (params?.conversation_id) qs.set("conversation_id", params.conversation_id)
  if (params?.limit) qs.set("limit", String(params.limit))
  const res = await fetch(`${BASE}/research/tasks?${qs}`)
  if (!res.ok) throw new Error(`Research tasks fetch failed: ${res.status}`)
  return res.json()
}

export async function getResearchTask(taskId: string): Promise<ResearchTask> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}`)
  if (!res.ok) throw new Error(`Research task fetch failed: ${res.status}`)
  return res.json()
}

export async function getResearchSummary(): Promise<ResearchSummary> {
  const res = await fetch(`${BASE}/research/tasks/active/summary`)
  if (!res.ok) throw new Error(`Research summary fetch failed: ${res.status}`)
  return res.json()
}

// ── Mutations ────────────────────────────────────────────────────────

export async function dispatchResearch(payload: DispatchPayload): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/research/dispatch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Research dispatch failed: ${res.status}`)
  return res.json()
}

export async function approveProposal(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/research/proposals/${taskId}/approve`, { method: "POST" })
  if (!res.ok) throw new Error(`Proposal approval failed: ${res.status}`)
  return res.json()
}

export async function rejectProposal(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/research/proposals/${taskId}/reject`, { method: "POST" })
  if (!res.ok) throw new Error(`Proposal rejection failed: ${res.status}`)
  return res.json()
}

export async function cancelTask(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/cancel`, { method: "POST" })
  if (!res.ok) throw new Error(`Task cancellation failed: ${res.status}`)
  return res.json()
}

export async function deleteTask(taskId: string): Promise<{ task_id: string; deleted: boolean }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`Task deletion failed: ${res.status}`)
  return res.json()
}

export async function retryTask(taskId: string): Promise<{ task_id: string; status: string; retried_from: string }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/retry`, { method: "POST" })
  if (!res.ok) throw new Error(`Task retry failed: ${res.status}`)
  return res.json()
}

export async function runTask(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/run`, { method: "POST" })
  if (!res.ok) throw new Error(`Task run failed: ${res.status}`)
  return res.json()
}

export async function rerunTask(taskId: string): Promise<{ task_id: string; status: string; rerun_count: number; auto_run: boolean }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/rerun`, { method: "POST" })
  if (!res.ok) throw new Error(`Task rerun failed: ${res.status}`)
  return res.json()
}

export async function executeStep(taskId: string, rerunStepType?: string, rerunStepId?: string): Promise<{
  task_id: string
  executed_phase: string
  next_phase: string
  error?: string
  message?: string
  plan?: any
  query?: string
  results_count?: number
  parsed_count?: number
  digested_count?: number
  new_learnings?: number
  total_learnings?: number
  completeness?: number
  should_stop?: boolean
  reason?: string
  result_summary?: string
}> {
  const params = new URLSearchParams()
  if (rerunStepType) params.set("rerun_step_type", rerunStepType)
  if (rerunStepId) params.set("rerun_step_id", rerunStepId)
  const qs = params.toString()
  const url = qs ? `${BASE}/research/tasks/${taskId}/step?${qs}` : `${BASE}/research/tasks/${taskId}/step`
  const res = await fetch(url, { method: "POST" })
  if (!res.ok) throw new Error(`Step failed: ${res.status}`)
  return res.json()
}

// ── Orchestrator Phase / Preview ────────────────────────────────────

export async function getTaskPhase(taskId: string): Promise<{ task_id: string; phase: string }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/phase`)
  if (!res.ok) throw new Error(`Phase fetch failed: ${res.status}`)
  return res.json()
}

export interface StepPreview {
  phase: string
  objective?: string
  max_depth?: number
  budget_limit_usd?: number
  system_prompt?: string
  user_prompt?: string
  model?: string
  temperature?: number
  max_tokens?: number
  pending_queries?: string[]
  note?: string
  urls_to_fetch?: { url: string; title: string; query_group?: number }[]
  sources_to_digest?: { url: string; title: string; snippet?: string; query_group?: number }[]
  findings_count?: number
  sources_count?: number
  sources_analyzed?: number
  stagnation_counter?: number
  completeness_score?: number
  current_depth?: number
  max_rounds?: number
  accumulated_findings?: string[]
  parsed_urls?: { url: string; title?: string; status?: string }[]
  sources?: { url: string; title?: string; status?: string }[]
  findings?: string[]
  reflection?: {
    reflection?: string
    key_insights?: string[]
    remaining_gaps?: string[]
  }
  eval_path?: string
  eval_path_reason?: string
  satisfaction_threshold?: number
  key_insights?: string[]
  remaining_gaps?: string[]
  next_queries?: string[]
  next_direct_urls?: string[]
  digest_signals?: {
    followups?: string[]
    direct_urls?: string[]
    gaps?: string[]
  }
}

export async function getStepPreview(taskId: string, phase: string): Promise<StepPreview> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/preview/${phase}`)
  if (!res.ok) throw new Error(`Preview fetch failed: ${res.status}`)
  return res.json()
}

export async function reinitializeTask(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/reinitialize`, { method: "POST" })
  if (!res.ok) throw new Error(`Reinitialize failed: ${res.status}`)
  return res.json()
}

// ── Meta Log ────────────────────────────────────────────────────────

export interface MetaLogEntry {
  id: string
  task_id: string
  branch_id: string | null
  event_type: string
  event_data: Record<string, any>
  created_at: string | null
}

export interface MetaLogResponse {
  task_id: string
  title: string
  status: string
  branch_id?: string
  entries: MetaLogEntry[]
  count: number
}

export async function getTaskMetaLog(taskId: string, branchId?: string): Promise<MetaLogResponse> {
  const url = branchId
    ? `${BASE}/research/tasks/${taskId}/meta-log?step_id=${branchId}`
    : `${BASE}/research/tasks/${taskId}/meta-log`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Meta log fetch failed: ${res.status}`)
  return res.json()
}

// ── Orchestrator Steps ──────────────────────────────────────────────

export interface ResearchStepResult {
  id: string
  source_url: string | null
  source_title: string | null
  analyzed_json: string | null
  relevance_score: number
  novelty_score: number
  raw_file_path: string | null
  error?: string
  content_preview?: string
}

export interface ResearchStep {
  id: string
  task_id: string
  plan_id: string
  step_number: number
  step_type: string
  step_data: string
  status: string
  result_summary: string | null
  started_at: string | null
  completed_at: string | null
  query_group?: number
  query_text?: string
}

export interface ResearchPlanInfo {
  id: string
  task_id: string
  plan_json: string
  status: string
  created_at: string | null
}

export interface TaskStepsResponse {
  task_id: string
  plan: ResearchPlanInfo | null
  steps: ResearchStep[]
  results_by_step: Record<string, ResearchStepResult[]>
}

export async function getTaskSteps(taskId: string): Promise<TaskStepsResponse> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/steps`)
  if (!res.ok) throw new Error(`Steps fetch failed: ${res.status}`)
  return res.json()
}

// ── Assets ──────────────────────────────────────────────────────────

export interface ScrapedAsset {
  id: string
  branch_id: string
  task_id: string
  url: string
  raw_markdown: string
  relevance_score: number
  novelty_score: number
  diffractive_score: number
  created_at: string | null
}

export async function getTaskAssets(taskId: string): Promise<ScrapedAsset[]> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}`)
  if (!res.ok) throw new Error(`Task fetch failed: ${res.status}`)
  const task = await res.json()
  return task.assets || []
}

export function downloadResearchExport(taskId: string): void {
  const token = localStorage.getItem("aaa_token")
  const qs = token ? `?token=${encodeURIComponent(token)}` : ""
  const a = document.createElement("a")
  a.href = `${BASE}/research/tasks/${taskId}/export${qs}`
  a.download = `research_export_${taskId.slice(0, 8)}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

export async function getTaskNotes(taskId: string): Promise<NoteInfo[]> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/notes`)
  if (!res.ok) throw new Error(`Task notes fetch failed: ${res.status}`)
  return res.json()
}

export interface UnifiedNoteInfo extends NoteInfo {
  step_number?: number | null
  step_type?: string | null
}

export async function getTaskUnifiedNotes(taskId: string): Promise<UnifiedNoteInfo[]> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/notes/unified`)
  if (!res.ok) throw new Error(`Unified notes fetch failed: ${res.status}`)
  return res.json()
}

import type { NoteInfo } from "./types"
