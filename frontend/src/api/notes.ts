import { BASE } from "./http"
import type { NoteInfo } from "./types"

export { type NoteInfo }

export async function createNote(conversationId: string, messageId: number, selectedText: string, comment = "", visibility: "personal" | "shared" | "agent" = "personal", startOffset?: number): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ message_id: messageId, selected_text: selectedText, comment, visibility, start_offset: startOffset }) })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Unknown error" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function getNotes(conversationId: string): Promise<NoteInfo[]> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateNote(conversationId: string, noteId: string, comment?: string, visibility?: "personal" | "shared" | "agent"): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes/${noteId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ comment, visibility }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteNote(conversationId: string, noteId: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes/${noteId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
