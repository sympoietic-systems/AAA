import { BASE } from "./http"
import type { NoteInfo } from "./types"

export { type NoteInfo }

export async function createNote(params: {
  assetType: string
  assetId: string
  conversationId?: string | null
  selectedText: string
  comment?: string
  visibility?: "personal" | "shared" | "agent"
  startOffset?: number
}): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      asset_type: params.assetType,
      asset_id: params.assetId,
      conversation_id: params.conversationId ?? null,
      selected_text: params.selectedText,
      comment: params.comment ?? "",
      visibility: params.visibility ?? "personal",
      start_offset: params.startOffset,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getNotes(params: {
  assetType: string
  assetId: string
}): Promise<NoteInfo[]>
export async function getNotes(params: {
  conversationId: string
}): Promise<NoteInfo[]>
export async function getNotes(params: {
  assetType?: string
  assetId?: string
  conversationId?: string
}): Promise<NoteInfo[]> {
  const qs = new URLSearchParams()
  if (params.assetType && params.assetId) {
    qs.set("asset_type", params.assetType)
    qs.set("asset_id", params.assetId)
  } else if (params.conversationId) {
    qs.set("conversation_id", params.conversationId)
  }
  const res = await fetch(`${BASE}/notes?${qs}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateNote(
  noteId: string,
  comment?: string,
  visibility?: "personal" | "shared" | "agent"
): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/notes/${noteId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment, visibility }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteNote(noteId: string): Promise<void> {
  const res = await fetch(`${BASE}/notes/${noteId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function createConversationNote(
  conversationId: string,
  messageId: number,
  selectedText: string,
  comment = "",
  visibility: "personal" | "shared" | "agent" = "personal",
  startOffset?: number
): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message_id: messageId,
      selected_text: selectedText,
      comment,
      visibility,
      start_offset: startOffset,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getConversationNotes(conversationId: string): Promise<NoteInfo[]> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateConversationNote(
  conversationId: string,
  noteId: string,
  comment?: string,
  visibility?: "personal" | "shared" | "agent"
): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes/${noteId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment, visibility }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteConversationNote(
  conversationId: string,
  noteId: string
): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes/${noteId}`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
