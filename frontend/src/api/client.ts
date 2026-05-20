const BASE = "/api"

export interface ChatMessage {
  id: number
  timestamp: string
  speaker: "human" | "apparatus"
  content: string
  thinking?: string
}

export async function sendMessage(content: string): Promise<ChatMessage> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, speaker: "human" }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getHistory(limit = 50): Promise<{ messages: ChatMessage[] }> {
  const res = await fetch(`${BASE}/history?limit=${limit}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getHealth() {
  const res = await fetch(`${BASE}/health`)
  return res.json()
}
