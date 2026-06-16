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

export async function retryTask(taskId: string): Promise<{ task_id: string; status: string; retried_from: string }> {
  const res = await fetch(`${BASE}/research/tasks/${taskId}/retry`, { method: "POST" })
  if (!res.ok) throw new Error(`Task retry failed: ${res.status}`)
  return res.json()
}
