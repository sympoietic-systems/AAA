import { BASE } from "./http"
import type { MetricsResponse, HomeostaticRecommendations, MetricsInfo, DiffractiveInfo, DaemonStatusResponse, SchedulerStatusResponse, DreamEntry, DreamHistoryResponse, AgentInfo, ConversationTokenInfo, TokenResponse } from "./types"
import type { ImageMetadata, WebMetadata, DocumentMetadata } from "./types"

export { type MetricsResponse, type HomeostaticRecommendations, type MetricsInfo, type DiffractiveInfo }
export { type DaemonStatusResponse, type SchedulerStatusResponse, type DreamEntry, type DreamHistoryResponse }
export { type AgentInfo, type ConversationTokenInfo, type TokenResponse }

export async function getMetrics(window = 20): Promise<MetricsResponse> {
  const res = await fetch(`${BASE}/metrics?window=${window}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getTokens(conversationId?: string): Promise<TokenResponse> {
  const params = conversationId ? `?conversation_id=${conversationId}` : ""
  const res = await fetch(`${BASE}/tokens${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getDaemonStatus(): Promise<DaemonStatusResponse> {
  const res = await fetch(`${BASE}/daemon/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getSchedulerStatus(): Promise<SchedulerStatusResponse> {
  const res = await fetch(`${BASE}/scheduler/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getRecentDreams(hours: number = 48): Promise<DreamHistoryResponse> {
  const res = await fetch(`${BASE}/daemon/dreams?hours=${hours}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getHealth() {
  const res = await fetch(`${BASE}/health`)
  return res.json()
}

export async function getAgent(): Promise<AgentInfo> {
  const res = await fetch(`${BASE}/agent`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getFileSummary(
  conversationId: string,
  fileName: string
): Promise<{
  summary: string | null
  summary_model: string | null
  image_metadata?: ImageMetadata | null
  web_metadata?: WebMetadata | null
  document_metadata?: DocumentMetadata | null
}> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/files/${encodeURIComponent(fileName)}/summary`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
