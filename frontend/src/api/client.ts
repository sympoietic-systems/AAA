const BASE = "/api"

export interface MetricsInfo {
  pairwise_similarity: number | null
  conceptual_novelty: number | null
  rolling_entropy: number | null
  coupling_coherence: number | null
  agent_self_divergence: number | null
  reverse_perturbation: number | null
  surprise_index: number | null
  mutual_perturbation: number | null
  homeostatic_deficit: number | null
  conversation_vitality: number | null
  boringness: number | null
  conceptual_velocity: number | null
  divergence_resolution_ratio: number | null
  paskian_health: number | null
  phase_shifts: Array<{
    metric: string
    event: string
    delta: number
    direction: string
    from: number
    to: number
  }> | null
}

export interface HomeostaticRecommendations {
  temperature: { value: number; base: number; delta: number; clamped: boolean } | null
  presence_penalty: { value: number; base: number; delta: number; clamped: boolean } | null
  frequency_penalty: { value: number; base: number; delta: number; clamped: boolean } | null
  state: string
  triggered_flags: string[]
}

export interface ChatMessage {
  id: number
  timestamp: string
  conversation_id?: string
  speaker: "human" | "apparatus"
  content: string
  thinking?: string
  metrics?: MetricsInfo
  homeostatic_recommendations?: HomeostaticRecommendations
}

export interface AgentInfo {
  name: string
  version?: string
}

export async function sendMessage(content: string, conversationId?: string): Promise<ChatMessage> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, speaker: "human", conversation_id: conversationId || "" }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getHistory(limit = 50, conversationId?: string): Promise<{ messages: ChatMessage[] }> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (conversationId) params.set("conversation_id", conversationId)
  const res = await fetch(`${BASE}/history?${params}`)
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

export interface MetricsResponse {
  window_size: number
  aggregates: Record<string, number | null>
  latest: MetricsInfo | null
  recommendations: HomeostaticRecommendations | null
}

export async function getMetrics(window = 20): Promise<MetricsResponse> {
  const res = await fetch(`${BASE}/metrics?window=${window}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface ConversationInfo {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
  message_count: number
}

export async function listConversations(): Promise<{ conversations: ConversationInfo[] }> {
  const res = await fetch(`${BASE}/conversations`)
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
