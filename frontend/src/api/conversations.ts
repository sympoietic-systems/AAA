import { BASE } from "./http"
import type { ChatMessage, ConversationTreeNode, ConversationTreeLink, ConversationTagInfo, MemoryNodeInfo, ConversationInfo, ConversationFile, ConversationFilesResponse } from "./types"

export { type ConversationTreeNode, type ConversationTreeLink, type ConversationTagInfo, type MemoryNodeInfo, type ConversationInfo, type ConversationFile, type ConversationFilesResponse }

export async function sendMessage(
  content: string,
  conversationId?: string,
  files?: File[],
  parentMessageId?: number | null
): Promise<ChatMessage> {
  if (files && files.length > 0) {
    const formData = new FormData()
    formData.append("content", content)
    formData.append("speaker", "human")
    formData.append("conversation_id", conversationId || "")
    if (parentMessageId !== undefined && parentMessageId !== null) {
      formData.append("parent_message_id", String(parentMessageId))
    }
    for (const file of files) {
      formData.append("files", file)
    }
    const res = await fetch(`${BASE}/chat`, { method: "POST", body: formData })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
  }
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, speaker: "human", conversation_id: conversationId || "", parent_message_id: parentMessageId !== undefined ? parentMessageId : null }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function saveMessage(content: string, conversationId?: string, parentMessageId?: number | null): Promise<ChatMessage> {
  const res = await fetch(`${BASE}/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, speaker: "human", conversation_id: conversationId || "", parent_message_id: parentMessageId !== undefined ? parentMessageId : null }),
  })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Unknown error" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function generateResponse(conversationId: string, userMessageId: number): Promise<ChatMessage> {
  const res = await fetch(`${BASE}/chat/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, user_message_id: userMessageId }),
  })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Unknown error" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function getHistory(limit = 50, offset = 0, conversationId?: string): Promise<{ messages: ChatMessage[]; count: number }> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (conversationId) params.set("conversation_id", conversationId)
  const res = await fetch(`${BASE}/history?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getMessageThinking(messageId: number): Promise<{ thinking: string | null }> {
  const res = await fetch(`${BASE}/messages/${messageId}/thinking`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getMessageContext(messageId: number): Promise<{ context_sent: string | null }> {
  const res = await fetch(`${BASE}/messages/${messageId}/context`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function commitBranch(conversationId: string, parentMessageId: number, content: string, speaker = "apparatus"): Promise<ChatMessage> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/commit-branch`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ parent_message_id: parentMessageId, content, speaker }),
  })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Unknown error" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function getConversationTree(conversationId: string): Promise<{ nodes: ConversationTreeNode[]; links: ConversationTreeLink[] }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/tree`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getMessagePath(messageId: number): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE}/messages/${messageId}/path`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function listConversations(tag?: string, search?: string, limit?: number, offset?: number): Promise<{ conversations: ConversationInfo[]; total_count?: number; has_more?: boolean }> {
  const queryParams = new URLSearchParams()
  if (tag) queryParams.set("tag", tag)
  if (search) queryParams.set("search", search)
  if (limit !== undefined) queryParams.set("limit", String(limit))
  if (offset !== undefined) queryParams.set("offset", String(offset))
  const res = await fetch(`${BASE}/conversations?${queryParams.toString()}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getConversation(id: string): Promise<ConversationInfo> {
  const res = await fetch(`${BASE}/conversations/${id}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${id}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function deleteMessage(conversationId: string, messageId: number): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/messages/${messageId}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function renameConversation(id: string, title: string): Promise<ConversationInfo> {
  const res = await fetch(`${BASE}/conversations/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function generateConversationTitle(id: string): Promise<ConversationInfo> {
  const res = await fetch(`${BASE}/conversations/${id}/generate-title`, { method: "POST" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function generateHumanSummary(id: string): Promise<ConversationInfo> {
  const res = await fetch(`${BASE}/conversations/${id}/generate-human-summary`, { method: "POST" })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function addConversationTag(conversationId: string, tag: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/tags`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tag }) })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function removeConversationTag(conversationId: string, tag: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/tags/${encodeURIComponent(tag)}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function getAllUniqueTags(): Promise<{ tags: ConversationTagInfo[] }> {
  const res = await fetch(`${BASE}/tags`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getMemoryNodes(conversationId: string): Promise<{ nodes: MemoryNodeInfo[] }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/memory-nodes`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function uploadFiles(conversationId: string, files: File[]): Promise<ConversationFilesResponse> {
  const formData = new FormData()
  for (const file of files) { formData.append("files", file) }
  const res = await fetch(`${BASE}/conversations/${conversationId}/files`, { method: "POST", body: formData })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Unknown error" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function getConversationFiles(conversationId: string): Promise<ConversationFilesResponse> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/files`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteConversationFile(conversationId: string, fileName: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/files/${encodeURIComponent(fileName)}`, { method: "DELETE" })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function reprocessFile(conversationId: string, fileName: string): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/files/${encodeURIComponent(fileName)}/reprocess`, { method: "POST" })
  if (!res.ok) { const err = await res.json().catch(() => ({ detail: "Unknown error" })); throw new Error(err.detail || `HTTP ${res.status}`) }
  return res.json()
}

export async function downloadExport(conversationId: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/export`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  // Extract filename from Content-Disposition header
  const disposition = res.headers.get("Content-Disposition") || ""
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match ? match[1] : `conversation_${conversationId.slice(0, 8)}.md`

  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
