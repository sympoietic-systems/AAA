const BASE = "/api"

// Intercept global fetch to automatically inject AAA_PASSWORD header for API requests
const originalFetch = window.fetch
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const urlStr = typeof input === "string" ? input : input instanceof URL ? input.toString() : (input as Request).url
  if (urlStr.includes("/api/")) {
    const password = localStorage.getItem("aaa_password")
    if (password) {
      const headers = new Headers(init?.headers || {})
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${password}`)
      }
      return originalFetch(input, { ...init, headers })
    }
  }
  return originalFetch(input, init)
}

export async function checkAuthStatus(): Promise<{ authenticated: boolean; authEnabled: boolean }> {
  try {
    const res = await fetch(`${BASE}/auth/verify`)
    if (res.status === 401) {
      return { authenticated: false, authEnabled: true }
    }
    const data = await res.json().catch(() => ({}))
    return {
      authenticated: res.ok,
      authEnabled: !!data.auth_enabled,
    }
  } catch {
    return { authenticated: true, authEnabled: false }
  }
}

export async function verifyPassword(password: string): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/auth/verify`, {
      headers: { "Authorization": `Bearer ${password}` }
    })
    return res.ok
  } catch {
    return false
  }
}

export function logout(): void {
  localStorage.removeItem("aaa_password")
}


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
  has_context?: boolean
  model_used?: string | null
  provider_used?: string | null
  structural_signature?: number[] | null
  structural_justification?: string | null
  active_skills?: string[]
  active_beliefs?: string[]
  user_message_id?: number | null
  user_structural_signature?: number[] | null
  user_structural_justification?: string | null
  truncated?: boolean | null
  finish_reason?: string | null
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

export interface ImageMetadata {
  id: string
  image_path: string
  artifact_type: string
  raw_transcription?: string | null
  somatic_notes?: string | null
  diffractive_analysis?: string | null
  g_f_score: number
  a_d_score: number
  structural_vector_16d: string
  timestamp: string
  belief_nodes_implicated?: string | null
}

export interface WebMetadata {
  id: string
  query_used: string
  source_url: string
  raw_content: string
  interference_score: number
  belief_nodes_implicated?: string | null
  state_vector_impact?: string | null
  timestamp: string
}

export interface DocumentMetadata {
  interference_score: number
  belief_nodes_implicated: string[]
  state_vector_impact: number[]
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

export interface DbSkillInfo {
  id: string
  name: string
  description: string
  always_active: boolean
  trigger_keywords: string[]
  lifecycle_stage: string
  confidence: number
  ontological_mass: number
  vector_16d: number[]
  source: string
  version: number
  changelog: string
  last_used_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DbSkillsResponse {
  always_active: DbSkillInfo[]
  on_demand: DbSkillInfo[]
  all: DbSkillInfo[]
}

export async function getDbSkills(): Promise<DbSkillsResponse> {
  const res = await fetch(`${BASE}/skills/db`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface WorkshopResponse {
  status: string
  message?: string
  skill_id?: string
  name?: string
  content?: string
  description?: string
  confidence?: number
  version?: number
  approval_tier?: string
  lifecycle_stage?: string
  anti_mastery_assessment?: Record<string, unknown>
  skills?: Record<string, unknown>[]
  count?: number
  skill?: Record<string, unknown>
  events?: Record<string, unknown>[]
}

export async function getSkillContent(skillName: string): Promise<WorkshopResponse> {
  const res = await fetch(`${BASE}/skills/workshop/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: skillName }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface MetricsResponse {
  window_size: number
  aggregates: Record<string, number | null>
  latest: MetricsInfo | null
  recommendations: HomeostaticRecommendations | null
  diffractive: DiffractiveInfo | null
}

export interface DiffractiveSourceInfo {
  type: string
  source_title: string
  similarity: number
}

export interface DiffractiveInfo {
  state: string
  previous_state: string
  p_diffract: number
  stagnation_index: number
  r_context: number
  dynamic_max: number
  cohesion_timer: number
  similarity_range_memory: number[]
  similarity_range_files: number[]
  candidates_searched: number
  items_injected: number
  tokens_used: number
  token_budget: number
  duration_ms: number
  sources: DiffractiveSourceInfo[]
}


export interface BeliefEventInfo {
  id: string
  timestamp: string
  source_id: string
  source_type: string
  delta_confidence: number
  description: string
}

export interface BeliefNodeInfo {
  id: string
  label: string
  statement: string
  category: string
  confidence: number
  ontological_mass: number
  vector_16d: string
  origin: string
  lifecycle_stage: string
  last_reinforced_at: string | null
  updated_at: string | null
  events: BeliefEventInfo[]
}

export interface SomaticStateInfo {
  somatic_reservoir_ad: number
  matrix_warping: number
  immunological_directive_active: boolean
}

export interface EcosystemSnapshot {
  diversity: number
  coherence: number
  tension: number
  plasticity: number
  ghost_burden: number
  eco_vitality: number
  active_count: number
  proto_count: number
  ghost_count: number
  self_tuning: Record<string, unknown>
}

export interface BeliefsResponse {
  beliefs: BeliefNodeInfo[]
  proto_beliefs: BeliefNodeInfo[]
  ghosts: BeliefNodeInfo[]
  somatic: SomaticStateInfo | null
  attractor_window: string[]
  spectral_margin: string[]
  ecosystem: EcosystemSnapshot | null
}

export async function getBeliefs(conversationId?: string): Promise<BeliefsResponse> {
  const params = conversationId ? `?conversation_id=${conversationId}` : ""
  const res = await fetch(`${BASE}/beliefs${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}


export async function getMetrics(window = 20): Promise<MetricsResponse> {
  const res = await fetch(`${BASE}/metrics?window=${window}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface ConversationTagInfo {
  tag: string
  tag_type: string
}

export interface MemoryNodeInfo {
  id: string
  node_type: string
  intensity: number
  scar: string
  glitch_potential: number
  intra_active_text: string
  surface_fragment: string
  agential_symmetry: string
  diffractive_key: string
  tendril_ids: string[]
  created_at: string | null
}

export interface ConversationInfo {
  id: string
  title: string
  created_at: string | null
  updated_at: string | null
  message_count: number
  tags?: ConversationTagInfo[]
  summary?: string
  human_summary?: string
}

export async function listConversations(tag?: string): Promise<{ conversations: ConversationInfo[] }> {
  const params = tag ? `?tag=${encodeURIComponent(tag)}` : ""
  const res = await fetch(`${BASE}/conversations${params}`)
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

export async function addConversationTag(conversationId: string, tag: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/tags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tag }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export async function removeConversationTag(conversationId: string, tag: string): Promise<void> {
  const res = await fetch(
    `${BASE}/conversations/${conversationId}/tags/${encodeURIComponent(tag)}`,
    {
      method: "DELETE",
    }
  )
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

export async function reprocessFile(
  conversationId: string,
  fileName: string
): Promise<{ status: string }> {
  const res = await fetch(
    `${BASE}/conversations/${conversationId}/files/${encodeURIComponent(fileName)}/reprocess`,
    {
      method: "POST",
    }
  )
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export interface SchedulerStatusResponse {
  status: "pending" | "running" | "completed" | "error" | "not_initialized"
  indexing_tasks_found: number
  indexing_tasks_completed: number
  indexing_tasks_failed: number
  active_indexing_jobs: string[]
  belief_turns_found: number
  belief_turns_completed: number
  belief_turns_failed: number
  error_details?: string | null
}

export async function getSchedulerStatus(): Promise<SchedulerStatusResponse> {
  const res = await fetch(`${BASE}/scheduler/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export interface DaemonStatusResponse {
  enabled: boolean
  running: boolean
  idle_time_seconds: number
  idle_threshold_seconds: number
  last_dream_time: string | null
  dreams_today: number
  max_daily_dreams: number
  last_dream_action: string | null
  dream_action_counts: Record<string, number>
  min_dream_interval: number
  check_interval: number
}

export async function getDaemonStatus(): Promise<DaemonStatusResponse> {
  const res = await fetch(`${BASE}/daemon/status`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}


export interface NoteInfo {
  id: string
  conversation_id: string
  message_id: number
  selected_text: string
  comment: string
  visibility: "personal" | "shared"
  created_at: string
  updated_at: string
}

export async function createNote(
  conversationId: string,
  messageId: number,
  selectedText: string,
  comment = "",
  visibility: "personal" | "shared" = "personal",
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

export async function getNotes(conversationId: string): Promise<NoteInfo[]> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function updateNote(
  conversationId: string,
  noteId: string,
  comment?: string,
  visibility?: "personal" | "shared"
): Promise<NoteInfo> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes/${noteId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ comment, visibility }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function deleteNote(conversationId: string, noteId: string): Promise<void> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/notes/${noteId}`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}


// ── Sediment Injection (cross-conversation linking) ────────────────

export interface SedimentFileInfo {
  conversation_id: string
  conversation_title: string
  file_name: string
  file_type: string
  summary: string | null
  token_count: number
  chunk_count: number
  created_at: string | null
  updated_at: string | null
}

export interface SedimentInjectionInfo {
  id: string
  source_conversation_id: string
  source_file_name: string
  source_conversation_title: string
  file_type: string
  token_count: number
  chunk_count: number
  summary: string | null
  injected_at: string | null
}

export async function listSedimentFiles(
  excludeConversationId?: string,
  search?: string
): Promise<{ files: SedimentFileInfo[] }> {
  const params = new URLSearchParams()
  if (excludeConversationId) params.set("exclude_conversation_id", excludeConversationId)
  if (search) params.set("search", search)
  const res = await fetch(`${BASE}/sediment/files?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function injectSediment(
  conversationId: string,
  files: { source_conversation_id: string; source_file_name: string }[]
): Promise<{ injections: SedimentInjectionInfo[] }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/sediment/inject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ files }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function getConversationInjections(
  conversationId: string
): Promise<{ injections: SedimentInjectionInfo[] }> {
  const res = await fetch(`${BASE}/conversations/${conversationId}/sediment/injections`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function removeSedimentInjection(injectionId: string): Promise<void> {
  const res = await fetch(`${BASE}/sediment/injections/${injectionId}`, {
    method: "DELETE",
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}
