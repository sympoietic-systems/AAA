import { BASE } from "./http"
import type { SedimentFileInfo, SedimentInjectionInfo, SpectralSuggestion, ConversationTreeLink } from "./types"

export { type SedimentFileInfo, type SedimentInjectionInfo, type SpectralSuggestion }

export async function listSedimentFiles(excludeConversationId?: string, search?: string): Promise<{ files: SedimentFileInfo[] }> {
  const params = new URLSearchParams()
  if (excludeConversationId) params.set("exclude_conversation_id", excludeConversationId)
  if (search) params.set("search", search)
  const res = await fetch(`${BASE}/sediment/files?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function injectSediment(conversationId: string, files: { source_conversation_id: string; source_file_name: string }[]): Promise<{ injections: SedimentInjectionInfo[] }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/sediment/inject`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ files }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getConversationInjections(conversationId: string): Promise<{ injections: SedimentInjectionInfo[] }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/sediment/injections`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function removeSedimentInjection(injectionId: string): Promise<void> {
  const res = await fetch(`${BASE}/sediment/injections/${injectionId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function createResonanceLink(conversationId: string, sourceId: number, targetId: number, justification = "", status: "active" | "proposed" | "ignored" = "active"): Promise<ConversationTreeLink> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/links`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_id: sourceId, target_id: targetId, link_type: "resonance", status, justification }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function confirmResonanceLink(conversationId: string, linkId: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/links/${linkId}/confirm`, { method: "POST" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function deleteResonanceLink(conversationId: string, linkId: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/links/${linkId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function getSpectralSuggestions(conversationId: string, messageId: number, threshold = 0.70): Promise<SpectralSuggestion[]> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages/${messageId}/spectral-suggestions?threshold=${threshold}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
