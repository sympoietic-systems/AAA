// All API type definitions in one file.
// Domain files import from here; the barrel re-exports everything.

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
  phase_shifts: Array<{ metric: string; event: string; delta: number; direction: string; from: number; to: number }> | null
}

export interface HomeostaticRecommendations {
  temperature: { value: number; base: number; delta: number; clamped: boolean } | null
  presence_penalty: { value: number; base: number; delta: number; clamped: boolean } | null
  frequency_penalty: { value: number; base: number; delta: number; clamped: boolean } | null
  state: string
  triggered_flags: string[]
}

export interface AttachmentInfo {
  file_name: string; file_type: string; token_count: number; preview?: string | null
}

export interface ChatMessage {
  id: number; timestamp: string; conversation_id?: string; speaker: "human" | "apparatus" | "system"; content: string
  thinking?: string; content_tokens?: number; thinking_tokens?: number | null
  metrics?: MetricsInfo; homeostatic_recommendations?: HomeostaticRecommendations; attachments?: AttachmentInfo[] | null
  context_sent?: string | null; has_context?: boolean; model_used?: string | null; provider_used?: string | null
  structural_signature?: number[] | null; structural_justification?: string | null
  active_skills?: string[]; active_beliefs?: string[]
  user_message_id?: number | null; user_structural_signature?: number[] | null; user_structural_justification?: string | null
  truncated?: boolean | null; finish_reason?: string | null; parent_message_id?: number | null
  proposed_branches?: Array<{ title: string; content: string }> | null
}

export interface AgentInfo { name: string; version?: string; agent_flux?: boolean }

export interface ConversationTreeNode { id: number; speaker: string; content: string; parent_message_id: number | null; timestamp: string }
export interface ConversationTreeLink { id: string; source_id: number; target_id: number; link_type: string; status: "active" | "proposed"; justification?: string }

export interface ImageMetadata { id: string; image_path: string; artifact_type: string; raw_transcription?: string | null; somatic_notes?: string | null; diffractive_analysis?: string | null; g_f_score: number; a_d_score: number; structural_vector_16d: string; timestamp: string; belief_nodes_implicated?: string | null }
export interface WebMetadata { id: string; query_used: string; source_url: string; raw_content: string; interference_score: number; belief_nodes_implicated?: string | null; state_vector_impact?: string | null; timestamp: string }
export interface DocumentMetadata { interference_score: number; belief_nodes_implicated: string[]; state_vector_impact: number[] }

export interface SkillInfo { name: string; description: string; category: string; always_run: boolean; triggers: string[]; cost: string; status: boolean; children: SkillInfo[] }
export interface SkillsResponse { pipeline: SkillInfo[]; on_demand: SkillInfo[] }
export interface DbSkillInfo { id: string; name: string; description: string; always_active: boolean; trigger_keywords: string[]; lifecycle_stage: string; confidence: number; ontological_mass: number; vector_16d: number[]; source: string; version: number; changelog: string; last_used_at: string | null; created_at: string | null; updated_at: string | null; refusal_reason?: string }
export interface DbSkillsResponse { always_active: DbSkillInfo[]; on_demand: DbSkillInfo[]; collapsed?: DbSkillInfo[]; proposed?: DbSkillInfo[]; all: DbSkillInfo[] }
export interface WorkshopResponse { status: string; message?: string; skill_id?: string; name?: string; content?: string; description?: string; confidence?: number; version?: number; approval_tier?: string; lifecycle_stage?: string; anti_mastery_assessment?: Record<string, unknown>; skills?: Record<string, unknown>[]; count?: number; skill?: Record<string, unknown>; events?: Record<string, unknown>[] }

export interface MetricsResponse { window_size: number; aggregates: Record<string, number | null>; latest: MetricsInfo | null; recommendations: HomeostaticRecommendations | null; diffractive: DiffractiveInfo | null }
export interface DiffractiveSourceInfo { type: string; source_title: string; similarity: number }
export interface DiffractiveInfo { state: string; previous_state: string; p_diffract: number; stagnation_index: number; r_context: number; dynamic_max: number; cohesion_timer: number; similarity_range_memory: number[]; similarity_range_files: number[]; candidates_searched: number; items_injected: number; tokens_used: number; token_budget: number; duration_ms: number; sources: DiffractiveSourceInfo[] }

export interface BeliefEventInfo { id: string; timestamp: string; source_id: string; source_type: string; delta_confidence: number; description: string }
export interface BeliefNodeInfo { id: string; label: string; statement: string; category: string; confidence: number; ontological_mass: number; version: number; vector_16d: string; origin: string; lifecycle_stage: string; last_reinforced_at: string | null; updated_at: string | null; events: BeliefEventInfo[]; is_proposal?: boolean; proposal_status?: string; suggested_label?: string | null; suggested_statement?: string | null; symbia_reflection?: string | null; symbia_friction_rationale?: string | null; rejection_rationale?: string | null; potential_merge_target?: string | null; source_trace?: any[] }
export interface SomaticStateInfo { somatic_reservoir_ad: number; matrix_warping: number; immunological_directive_active: boolean }
export interface EcosystemSnapshot { diversity: number; coherence: number; tension: number; plasticity: number; ghost_burden: number; eco_vitality: number; active_count: number; proto_count: number; ghost_count: number; self_tuning: Record<string, unknown> }
export interface BeliefsResponse { beliefs: BeliefNodeInfo[]; proto_beliefs: BeliefNodeInfo[]; ghosts: BeliefNodeInfo[]; somatic: SomaticStateInfo | null; attractor_window: string[]; spectral_margin: string[]; ecosystem: EcosystemSnapshot | null }
export interface BeliefProposalInfo { id: string; agent_id: string; provisional_statement: string; source_trace: any[]; initial_signature: number[]; nucleation_mass: number; confidence: number; status: string; suggested_label: string | null; suggested_statement: string | null; potential_merge_target: string | null; symbia_reflection: string | null; symbia_friction_rationale: string | null; rejection_rationale: string | null; created_at: string | null; updated_at: string | null }

export interface ConversationTagInfo { tag: string; tag_type: string }
export interface MemoryNodeInfo { id: string; node_type: string; intensity: number; scar: string; glitch_potential: number; intra_active_text: string; surface_fragment: string; agential_symmetry: string; diffractive_key: string; tendril_ids: string[]; created_at: string | null }
export interface ConversationInfo { id: string; title: string; created_at: string | null; updated_at: string | null; message_count: number; tags?: ConversationTagInfo[]; summary?: string; human_summary?: string }

export interface ConversationTokenInfo { conversation_id: string; title: string; user_tokens: number; agent_tokens: number; thinking_tokens: number; total_tokens: number }
export interface TokenResponse { conversations: ConversationTokenInfo[]; system_prompt_tokens: number; grand_total_tokens: number }

export interface ConversationFile { file_name: string; file_type: string; status: "uploading" | "processing" | "ready" | "error"; summary?: string | null; summary_model?: string | null; token_count: number; chunk_count: number; created_at?: string | null; updated_at?: string | null }
export interface ConversationFilesResponse { conversation_id: string; files: ConversationFile[] }

export interface SchedulerStatusResponse { status: "pending" | "running" | "completed" | "error" | "not_initialized"; indexing_tasks_found: number; indexing_tasks_completed: number; indexing_tasks_failed: number; active_indexing_jobs: string[]; belief_turns_found: number; belief_turns_completed: number; belief_turns_failed: number; error_details?: string | null }
export interface DaemonStatusResponse { enabled: boolean; running: boolean; idle_time_seconds: number; idle_threshold_seconds: number; last_dream_time: string | null; dreams_today: number; max_daily_dreams: number; last_dream_action: string | null; dream_action_counts: Record<string, number>; min_dream_interval: number; check_interval: number }
export interface DreamEntry { id: number; conversation_id: string; action: string; response_msg_id: number | null; turns: number; timestamp: string; title: string; msg_count: number; last_snippet: string | null }
export interface DreamHistoryResponse { dreams: DreamEntry[]; count: number }

export interface NoteInfo { id: string; conversation_id: string; message_id: number; selected_text: string; comment: string; visibility: "personal" | "shared" | "agent"; created_at: string; updated_at: string }

export interface SedimentFileInfo { conversation_id: string; conversation_title: string; file_name: string; file_type: string; summary: string | null; token_count: number; chunk_count: number; created_at: string | null; updated_at: string | null }
export interface SedimentInjectionInfo { id: string; source_conversation_id: string; source_file_name: string; source_conversation_title: string; file_type: string; token_count: number; chunk_count: number; summary: string | null; injected_at: string | null }
export interface SpectralSuggestion { message_id: number; speaker: string; content: string; similarity: number; timestamp: string }

export interface SkillEventInfo { id: string; skill_id: string; event_type: 'emergence' | 'crystallization' | 'revision' | 'collapse'; source_type: string; rationale: string; annotation: string; created_at: string; skill_name: string }
export interface SedimentNotification { id: string; type: 'sediment' | 'glitch' | 'trace'; conversationId?: string; messageId?: number; parentMessageId?: number; timestamp: string; snippet: string; speaker?: string; source?: string; sourceType?: string; sourceId?: string; read?: boolean; dismissed?: boolean }

export interface BasinBelief { label: string; statement: string; confidence: number; mass: number; stage: string; similarity: number }
export interface PersonalityCommitment { id: string; label: string; statement: string; lifecycle_stage: string; confidence: number; ontological_mass: number; vector_16d?: number[] | null; basin_belief_count?: number; basin_belief_labels?: string[]; basin_beliefs?: BasinBelief[]; nucleation_rationale?: string | null; collapse_rationale?: string | null; created_at?: string | null; updated_at?: string | null }
export interface PersonalityExpertise { id: string; domain: string; description?: string; lifecycle_stage: string; ontological_mass: number; level_label: string; signal_count: number; vector_16d?: number[] | null; last_signal_at?: string | null; crystallization_rationale?: string | null; created_at?: string | null }
export interface PersonalityResponse { traits: Record<string, number> | null; aspirational_traits: Record<string, number>; aspirational_gap: number; anti_erosion_boost: number; source_metrics: Record<string, number>; commitments: { active: PersonalityCommitment[]; proto: PersonalityCommitment[]; spectral: PersonalityCommitment[] }; expertise: { active: PersonalityExpertise[]; proto: PersonalityExpertise[]; dormant: PersonalityExpertise[] } }
