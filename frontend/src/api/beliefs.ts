import { BASE } from "./http"
import type { BeliefsResponse, BeliefNodeInfo, BeliefEventInfo, BeliefProposalInfo, BeliefTimeseriesResponse } from "./types"

export { type BeliefsResponse, type BeliefNodeInfo, type BeliefEventInfo, type BeliefProposalInfo, type BeliefTimeseriesResponse }

export async function getBeliefProposals(agentId: string = "symbia"): Promise<BeliefProposalInfo[]> {
  const res = await fetch(`${BASE}/beliefs/proposals?agent_id=${agentId}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function vetBeliefProposal(proposalId: string, payload: { action: "adopt" | "reject" | "merge"; suggested_label?: string; suggested_statement?: string; rejection_rationale?: string; target_belief_id?: string }): Promise<any> {
  const res = await fetch(`${BASE}/beliefs/proposals/${proposalId}/vet`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to vet proposal" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function refineBeliefProposal(proposalId: string): Promise<any> {
  const res = await fetch(`${BASE}/beliefs/proposals/${proposalId}/refine`, { method: "POST" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function synthesizeMergeStatement(proposalId: string, targetBeliefId: string): Promise<{ status: string; synthesized_statement: string }> {
  const res = await fetch(`${BASE}/beliefs/proposals/${proposalId}/synthesize-merge`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ target_belief_id: targetBeliefId }) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to synthesize statement" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function getBeliefs(conversationId?: string): Promise<BeliefsResponse> {
  const params = conversationId ? `?conversation_id=${conversationId}` : ""
  const res = await fetch(`${BASE}/beliefs${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function createBelief(data: { label: string; statement: string; confidence: number; ontological_mass: number; lifecycle_stage: string; agent_id: string }): Promise<{ status: string; belief_id: string; label: string }> {
  const res = await fetch(`${BASE}/beliefs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to create belief" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function updateBelief(beliefId: string, data: { label: string; statement: string; confidence: number; ontological_mass: number; lifecycle_stage: string }): Promise<{ status: string; belief_id: string; version: number; speciation_alert: boolean }> {
  const res = await fetch(`${BASE}/beliefs/${beliefId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to update belief" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function deleteBelief(beliefId: string): Promise<void> {
  const res = await fetch(`${BASE}/beliefs/${beliefId}`, { method: "DELETE" })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to delete belief" })); throw new Error(err.detail || `HTTP ${res.status}`) }
}

export async function revertBelief(beliefId: string, version: number): Promise<{ status: string; belief_id: string; version: number; speciation_alert: boolean }> {
  const res = await fetch(`${BASE}/beliefs/${beliefId}/revert/${version}`, { method: "POST" })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Failed to revert belief version" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function getBeliefTimeseries(beliefId: string, days: number = 30): Promise<BeliefTimeseriesResponse> {
  const res = await fetch(`${BASE}/beliefs/${beliefId}/timeseries?days=${days}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
