import { BASE } from "./http"
import type { SedimentNotification } from "./types"

export { type SedimentNotification }

function mapBackendNotification(n: any): SedimentNotification {
  return { id: n.id, type: n.type, conversationId: n.conversation_id || undefined, messageId: n.message_id || undefined, parentMessageId: n.parent_message_id || undefined, timestamp: n.timestamp, snippet: n.snippet, speaker: n.speaker || undefined, source: n.source || undefined, sourceType: n.source_type || undefined, sourceId: n.source_id || undefined, read: n.read === 1 || n.read === true, dismissed: n.dismissed === 1 || n.dismissed === true }
}

function mapFrontendNotification(n: Partial<SedimentNotification>): any {
  return { id: n.id, type: n.type, conversation_id: n.conversationId, message_id: n.messageId, parent_message_id: n.parentMessageId, timestamp: n.timestamp, snippet: n.snippet, speaker: n.speaker, source: n.source, source_type: n.sourceType, source_id: n.sourceId, read: n.read ? 1 : 0, dismissed: n.dismissed ? 1 : 0 }
}

export async function getNotification(id: string): Promise<SedimentNotification> {
  const res = await fetch(`${BASE}/notifications/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return mapBackendNotification(await res.json())
}

export async function getNotifications(dismissed?: boolean, limit = 100, type?: string, search?: string): Promise<SedimentNotification[]> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (dismissed !== undefined) params.set("dismissed", dismissed ? "true" : "false")
  if (type) params.set("type", type)
  if (search) params.set("search", search)
  const res = await fetch(`${BASE}/notifications?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return (await res.json()).map(mapBackendNotification)
}

export async function createNotification(notif: Partial<SedimentNotification>): Promise<SedimentNotification> {
  const res = await fetch(`${BASE}/notifications`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(mapFrontendNotification(notif)) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return mapBackendNotification(await res.json())
}

export async function markNotificationRead(id: string): Promise<SedimentNotification> {
  const res = await fetch(`${BASE}/notifications/${id}/read`, { method: "PATCH" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return mapBackendNotification(await res.json())
}

export async function markNotificationUnread(id: string): Promise<SedimentNotification> {
  const res = await fetch(`${BASE}/notifications/${id}/unread`, { method: "PATCH" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return mapBackendNotification(await res.json())
}

export async function dismissNotification(id: string): Promise<SedimentNotification> {
  const res = await fetch(`${BASE}/notifications/${id}/dismiss`, { method: "PATCH" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return mapBackendNotification(await res.json())
}

export async function dismissNotificationByMatch(conversationId: string, messageId: number): Promise<void> {
  const params = new URLSearchParams({ conversation_id: conversationId, message_id: String(messageId) })
  const res = await fetch(`${BASE}/notifications/dismiss-match?${params}`, { method: "PATCH" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function clearNotifications(type?: string): Promise<void> {
  const res = await fetch(`${BASE}/notifications/clear`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function markAllNotificationsRead(type?: string): Promise<void> {
  const res = await fetch(`${BASE}/notifications/read`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ type }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
