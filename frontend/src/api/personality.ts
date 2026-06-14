import { BASE } from "./http"
import type { PersonalityResponse, PersonalityCommitment, PersonalityExpertise, BasinBelief } from "./types"

export { type PersonalityResponse, type PersonalityCommitment, type PersonalityExpertise, type BasinBelief }

export async function getPersonality(): Promise<PersonalityResponse> {
  const res = await fetch(`${BASE}/agent/personality`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateCommitment(id: string, data: { statement?: string; lifecycle_stage?: string; confidence?: number; ontological_mass?: number }): Promise<void> {
  const res = await fetch(`${BASE}/agent/personality/commitment/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function updateExpertise(id: string, data: { lifecycle_stage?: string; ontological_mass?: number; level_label?: string }): Promise<void> {
  const res = await fetch(`${BASE}/agent/personality/expertise/${id}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function updateAspirationalTraits(traits: Record<string, number>): Promise<void> {
  const res = await fetch(`${BASE}/agent/personality/aspirational`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ traits }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function recalculateCommitmentVector(id: string): Promise<number[]> {
  const res = await fetch(`${BASE}/agent/personality/commitment/${id}/recalculate`, { method: "PUT" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return data.vector_16d
}

export async function recalculateExpertiseVector(id: string): Promise<number[]> {
  const res = await fetch(`${BASE}/agent/personality/expertise/${id}/recalculate`, { method: "PUT" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return data.vector_16d
}
