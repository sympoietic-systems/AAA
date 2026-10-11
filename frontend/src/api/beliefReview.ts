import { apiJson, BASE } from "./http"

export type ReviewState = "candidate" | "awaiting_context" | "under_review" | "adopted" | "deferred" | "declined" | "superseded"
export type ReviewAction = "adopt" | "decline" | "defer" | "request_context" | "request_review"
export type Recorded = Record<string, unknown>
export type ReasoningKey = "encounter" | "claim_or_tension" | "comparison" | "consequence_or_challenge" | "decision_or_uncertainty"
export interface ReviewExportItem {
  export_id: string; id: string; timestamp: string | null
  kind: "encounter" | "assessment" | "legacy_assessment" | "decision" | "event" | "legacy_event"
  record: Recorded; source_accounting: Recorded | null
  reasoning: Record<ReasoningKey, Recorded | Recorded[] | null>
  reasoning_sources: { id: string; kind: string; timestamp: string | null }[]
  unknown_reasoning_fields: string[]; comparison_truncated: boolean
  tool_authority: "none"; content_redacted: boolean
}
export interface ReviewSnapshot {
  id: string; label: string; statement: string; statement_sha256: string
  kind: string; legacy_status: string; scope: string; temporal_scope: string
  quote: string; source_current: boolean; context_provenance: string
  state: { state: ReviewState; version: number; scope: string } | null
}
export interface ReviewCommand {
  action: ReviewAction; expected_review_version: number; expected_statement_sha256: string
  expected_state: ReviewState | null; scope: string; temporal_scope: string
  rationale: string; consequence: string; challenge: string; dissent: string[]
  assessment_ids: string[]
}
export interface ReviewDecision extends Recorded {
  id: string; agent_id: string; timestamp: string; next_state: ReviewState
  rationale: string; dissent: string[]
}
export interface WorkshopReceipt {
  id: string; agent_id: string; record_id: string; command: Recorded
  decision: ReviewDecision; record_snapshot: ReviewSnapshot
  relation_snapshots: Recorded[]; alternative_snapshot: Recorded | null
  counter_trace: Recorded | null; tool_authority: "none"; shared_agreement: "not_inferred"
}
export interface WorkshopView {
  agent_id: string; record: ReviewSnapshot; family: ReviewSnapshot[]; nomination_only: true
  uncompared_in_bounded_scan: number; commands: WorkshopReceipt[]; counter_traces: Recorded[]
  history_truncated: boolean; counter_traces_truncated: boolean
  command_count: number; counter_trace_count: number
  advisory_assessments: { receipt: Recorded; binding: string; tool_authority: "none" }[]
  participant_identity: string; tool_authority: "none"
}

const reviewBase = (agent: string) => `${BASE}/beliefs/v2/agents/${encodeURIComponent(agent)}`
export function getReviewReceipt(agent: string, resource: "encounters" | "assessments" | "decisions", id: string, signal?: AbortSignal) {
  return apiJson<ReviewExportItem>(`${reviewBase(agent)}/${resource}/${encodeURIComponent(id)}`, { signal })
}
export function getBeliefReview(agent: string, record: string, signal?: AbortSignal) {
  return apiJson<WorkshopView>(`${reviewBase(agent)}/records/${encodeURIComponent(record)}/review`, { signal })
}
export function decideBelief(agent: string, record: string, command: ReviewCommand, key: string) {
  return apiJson<WorkshopReceipt>(`${reviewBase(agent)}/records/${encodeURIComponent(record)}/decisions`, {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": key }, body: JSON.stringify(command),
  })
}
