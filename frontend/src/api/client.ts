const BASE = "/api"

export interface ChatMessage {
  id: number
  timestamp: string
  speaker: "human" | "apparatus"
  content: string
  thinking?: string
}

export interface AgentInfo {
  name: string
  version?: string
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

export async function getAgent(): Promise<AgentInfo> {
  const res = await fetch(`${BASE}/agent`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface SkillInfo {
  name: string
  description: string
  category: string
  always_run: boolean
  triggers: string[]
  cost: string
  status: boolean
}

export interface SkillsResponse {
  pipeline: SkillInfo[]
  on_demand: SkillInfo[]
}

export async function getSkills(): Promise<SkillsResponse> {
  const res = await fetch(`${BASE}/skills`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
