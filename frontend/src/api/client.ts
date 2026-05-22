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

export interface AttachmentInfo {
  file_name: string
  file_type: string
  token_count: number
  preview?: string | null
}

export interface ChatMessage {
  id: number
  timestamp: string
  conversation_id?: string
  speaker: "human" | "apparatus" | "system"
  content: string
  thinking?: string
  content_tokens?: number
  thinking_tokens?: number | null
  metrics?: MetricsInfo
  homeostatic_recommendations?: HomeostaticRecommendations
  attachments?: AttachmentInfo[] | null
  context_sent?: string | null
  model_used?: string | null
  provider_used?: string | null
}

export interface AgentInfo {
  name: string
  version?: string
}

export async function sendMessage(
  content: string,
  conversationId?: string,
  files?: File[]
): Promise<ChatMessage> {
  if (files && files.length > 0) {
    const formData = new FormData()
    formData.append("content", content)
    formData.append("speaker", "human")
    formData.append("conversation_id", conversationId || "")
    for (const file of files) {
      formData.append("files", file)
    }
    const res = await fetch(`${BASE}/chat`, {
      method: "POST",
      body: formData,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Unknown error" }))
      throw new Error(err.detail || `HTTP ${res.status}`)
    }
    return res.json()
  }

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
  children: SkillInfo[]
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

export async function renameConversation(id: string, title: string): Promise<ConversationInfo> {
  const res = await fetch(`${BASE}/conversations/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function generateConversationTitle(id: string): Promise<ConversationInfo> {
  const res = await fetch(`${BASE}/conversations/${id}/generate-title`, {
    method: "POST",
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface ConversationTokenInfo {
  conversation_id: string
  title: string
  user_tokens: number
  agent_tokens: number
  thinking_tokens: number
  total_tokens: number
}

export interface TokenResponse {
  conversations: ConversationTokenInfo[]
  system_prompt_tokens: number
  grand_total_tokens: number
}

export async function getTokens(conversationId?: string): Promise<TokenResponse> {
  const params = conversationId ? `?conversation_id=${conversationId}` : ""
  const res = await fetch(`${BASE}/tokens${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface ConversationFile {
  file_name: string
  file_type: string
  status: "uploading" | "processing" | "ready" | "error"
  summary?: string | null
  summary_model?: string | null
  token_count: number
  chunk_count: number
  created_at?: string | null
  updated_at?: string | null
}

export interface ConversationFilesResponse {
  conversation_id: string
  files: ConversationFile[]
}

export async function uploadFiles(
  conversationId: string,
  files: File[]
): Promise<ConversationFilesResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append("files", file)
  }
  const res = await fetch(`${BASE}/conversations/${conversationId}/files`, {
    method: "POST",
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getConversationFiles(
  conversationId: string
): Promise<ConversationFilesResponse> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/files`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteConversationFile(
  conversationId: string,
  fileName: string
): Promise<void> {
  const res = await fetch(
    `${BASE}/conversations/${conversationId}/files/${encodeURIComponent(fileName)}`,
    {
      method: "DELETE",
    }
  )
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

