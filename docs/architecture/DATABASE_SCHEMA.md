# AAA Database Schema

> **Status:** Live reference — generated from `backend/data/aaa.db`
> **Date:** 2026-06-16
> **Engine:** SQLite (WAL mode, foreign keys ON)

---

## Core Tables

### conversations
Primary conversation container. ID is a UUID string.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| title | TEXT | NOT NULL DEFAULT '' |
| agent_id | TEXT | NOT NULL DEFAULT '' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| somatic_reservoir_ad | REAL | DEFAULT 0.0 |
| matrix_warping | REAL | DEFAULT 0.0 |
| immunological_directive_active | INTEGER | DEFAULT 0 |
| requires_consolidation | INTEGER | DEFAULT 0 |
| last_consolidated_at | DATETIME | |

Index: `idx_conversations_updated`

### conversation_log
All messages (human and apparatus). ID is an auto-increment integer.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| agent_id | TEXT | NOT NULL DEFAULT '' |
| speaker | TEXT | NOT NULL |
| content | TEXT | NOT NULL |
| thinking | TEXT | |
| embedding | BLOB | NOT NULL |
| embedding_model | TEXT | NOT NULL |
| embedding_dim | INTEGER | NOT NULL |
| conversation_id | TEXT | NOT NULL DEFAULT '' |
| content_tokens | INTEGER | NOT NULL DEFAULT 0 |
| thinking_tokens | INTEGER | |
| model_used | TEXT | |
| provider_used | TEXT | |
| context_sent | TEXT | |
| structural_signature | BLOB | |
| structural_justification | TEXT | |
| note_count | INTEGER | DEFAULT 0 |
| metabolized | INTEGER | DEFAULT 0 |
| parent_message_id | INTEGER | |

FK: `parent_message_id -> conversation_log(id)`
Indexes: `idx_conversation_timestamp`, `idx_conversation_log_conv_id`, `idx_conversation_log_parent`

### conversation_metrics
Per-message vitality/paskian metrics.

| Column | Type | Constraints |
|--------|------|-------------|
| message_id | INTEGER | PRIMARY KEY |
| s_t | REAL | NOT NULL |
| novelty | REAL | NOT NULL |
| rolling_entropy | REAL | |
| coupling | REAL | |
| agent_divergence | REAL | |
| deficit | REAL | NOT NULL |
| reverse_perturbation | REAL | |
| surprise_index | REAL | |
| mutual_perturbation | REAL | |
| vitality | REAL | |
| phase_shifts | TEXT | |
| boringness | REAL | |
| conceptual_velocity | REAL | |
| divergence_resolution_ratio | REAL | |
| paskian_health | REAL | |
| temperature_rec | REAL | |
| presence_penalty_rec | REAL | |
| frequency_penalty_rec | REAL | |
| homeostatic_state | TEXT | |

FK: `message_id -> conversation_log(id)`
Indexes: `idx_metrics_deficit`, `idx_metrics_vitality`

---

## Memory & Sedimentation

### memory_nodes
Consolidated memory artifacts (concepts, tensions, scars, patterns, bifurcations).

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY NOT NULL |
| conversation_id | TEXT | NOT NULL |
| checkpoint_id | INTEGER | PRIMARY KEY NOT NULL |
| node_type | TEXT | NOT NULL DEFAULT 'concept' |
| intensity | REAL | NOT NULL DEFAULT 0.5 |
| scar | TEXT | DEFAULT '' |
| glitch_potential | REAL | NOT NULL DEFAULT 0.0 |
| intra_active_text | TEXT | NOT NULL |
| surface_fragment | TEXT | DEFAULT '' |
| agential_symmetry | TEXT | DEFAULT 'negotiated' |
| diffractive_key | TEXT | DEFAULT '' |
| tendril_ids | TEXT | DEFAULT '[]' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| revision_count | INTEGER | NOT NULL DEFAULT 0 |
| last_merged_at | DATETIME | |

FK: `conversation_id -> conversations(id)`, `checkpoint_id -> consolidation_checkpoints(id)`
Indexes: `idx_mn_conv`, `idx_mn_type`, `idx_mn_intensity`

### semantic_knots
High-intensity concepts with gravitational retrieval pull.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| weight | REAL | NOT NULL DEFAULT 1.0 |
| concept_payload | TEXT | NOT NULL |
| embedding | BLOB | NOT NULL |
| embedding_model | TEXT | NOT NULL |
| token_count | INTEGER | NOT NULL |
| structural_signature | BLOB | |

FK: `conversation_id -> conversations(id)`

### consolidation_checkpoints
LLM-consolidated conversation summaries.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| message_count | INTEGER | NOT NULL |
| summary | TEXT | NOT NULL |
| model | TEXT | NOT NULL DEFAULT '' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| human_summary | TEXT | DEFAULT '' |
| message_id | INTEGER | |

FK: `conversation_id -> conversations(id)`, `message_id -> conversation_log(id)`

### compressed_messages
LLM-compressed message blocks for context window management.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| first_message_id | INTEGER | NOT NULL |
| last_message_id | INTEGER | NOT NULL |
| compressed_block | TEXT | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

FK: `conversation_id -> conversations(id)`

---

## Belief System

### belief_nodes
Core belief entities (crystallized, proto, spectral/ghost).

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| agent_id | TEXT | NOT NULL DEFAULT 'symbia' |
| label | TEXT | NOT NULL |
| statement | TEXT | NOT NULL |
| origin | TEXT | DEFAULT 'authored' |
| confidence | REAL | DEFAULT 0.5 |
| ontological_mass | REAL | DEFAULT 1.0 |
| somatic_anchor | TEXT | DEFAULT 'none' |
| vector_16d | TEXT | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| lifecycle_stage | TEXT | DEFAULT 'crystallized' |
| last_reinforced_at | DATETIME | |
| last_dreamed_at | DATETIME | |
| evolved_from_proposal | TEXT | |
| genesis_materials | TEXT | |
| version | INTEGER | DEFAULT 1 |
| merged_from | TEXT | |
| merged_into | TEXT | |

### belief_events
Chronological log of belief state changes.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| belief_id | TEXT | NOT NULL |
| source_type | TEXT | |
| source_id | TEXT | |
| alignment_coefficient | REAL | |
| perturbation_magnitude | REAL | |
| event_type | TEXT | |
| impact_score | REAL | |
| rationale | TEXT | |

FK: `belief_id -> belief_nodes(id)`

### belief_proposals
Pending belief nucleation proposals for review.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| agent_id | TEXT | NOT NULL DEFAULT 'symbia' |
| provisional_statement | TEXT | NOT NULL |
| source_trace | TEXT | NOT NULL |
| initial_signature | TEXT | NOT NULL |
| nucleation_mass | REAL | DEFAULT 0.1 |
| confidence | REAL | DEFAULT 0.15 |
| status | TEXT | DEFAULT 'pending' |
| suggested_label | TEXT | |
| suggested_statement | TEXT | |
| potential_merge_target | TEXT | |
| symbia_reflection | TEXT | |
| symbia_friction_rationale | TEXT | |
| rejection_rationale | TEXT | |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### belief_tensions
Inter-belief tension tracking.

| Column | Type | Constraints |
|--------|------|-------------|
| belief_a_id | TEXT | NOT NULL |
| belief_b_id | TEXT | NOT NULL |
| cosine_similarity | REAL | NOT NULL |
| tension_magnitude | REAL | NOT NULL |
| last_updated | DATETIME | DEFAULT CURRENT_TIMESTAMP |

Composite PK: (belief_a_id, belief_b_id)
FK: `belief_a_id -> belief_nodes(id)`, `belief_b_id -> belief_nodes(id)`

### belief_statement_versions
Version history of belief statements.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| belief_id | TEXT | NOT NULL |
| version | INTEGER | NOT NULL |
| statement | TEXT | NOT NULL |
| vector_16d | TEXT | NOT NULL |
| change_reason | TEXT | |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

FK: `belief_id -> belief_nodes(id)`

---

## Skill System

### skill_nodes
Skill definitions with lifecycle management.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| name | TEXT | NOT NULL |
| description | TEXT | NOT NULL |
| content | TEXT | NOT NULL |
| short_content | TEXT | |
| always_active | INTEGER | DEFAULT 0 |
| trigger_keywords | TEXT | |
| lifecycle_stage | TEXT | DEFAULT 'nucleation' |
| confidence | REAL | DEFAULT 0.0 |
| ontological_mass | REAL | DEFAULT 0.05 |
| vector_16d | TEXT | |
| source | TEXT | DEFAULT 'authored' |
| version | INTEGER | DEFAULT 1 |
| changelog | TEXT | |
| attunement_notes | TEXT | |
| last_used_at | DATETIME | |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### skill_events
Chronological log of skill lifecycle events.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| skill_id | TEXT | NOT NULL |
| event_type | TEXT | NOT NULL |
| source_type | TEXT | |
| rationale | TEXT | |
| annotation | TEXT | |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

FK: `skill_id -> skill_nodes(id)`

### skill_versions
Version history of skill content.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| skill_id | TEXT | NOT NULL |
| version | INTEGER | NOT NULL |
| content | TEXT | NOT NULL |
| description | TEXT | NOT NULL |
| trigger_keywords | TEXT | |
| changelog | TEXT | |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| source | TEXT | DEFAULT 'user' |

FK: `skill_id -> skill_nodes(id)`

---

## Commitment & Expertise

### commitment_nodes
Theoretical commitments.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| agent_id | TEXT | NOT NULL DEFAULT 'symbia' |
| label | TEXT | NOT NULL |
| statement | TEXT | NOT NULL |
| lifecycle_stage | TEXT | NOT NULL DEFAULT 'active' |
| confidence | REAL | NOT NULL DEFAULT 0.0 |
| ontological_mass | REAL | NOT NULL DEFAULT 1.0 |
| vector_16d | TEXT | NOT NULL DEFAULT '[]' |
| nucleation_rationale | TEXT | |
| collapse_rationale | TEXT | |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |

Indexes: `idx_commitment_agent`, `idx_commitment_stage`

### commitment_events
Commitment lifecycle event log.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| commitment_id | TEXT | NOT NULL |
| event_type | TEXT | NOT NULL |
| rationale | TEXT | |
| mass_before | REAL | |
| mass_after | REAL | |
| confidence_before | REAL | |
| confidence_after | REAL | |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |

FK: `commitment_id -> commitment_nodes(id)`

### expertise_nodes
Domain expertise tracking.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| agent_id | TEXT | NOT NULL DEFAULT 'symbia' |
| domain | TEXT | NOT NULL |
| lifecycle_stage | TEXT | NOT NULL DEFAULT 'proto' |
| ontological_mass | REAL | NOT NULL DEFAULT 0.05 |
| level_label | TEXT | NOT NULL DEFAULT 'nascent' |
| vector_16d | TEXT | NOT NULL DEFAULT '[]' |
| signal_count | INTEGER | NOT NULL DEFAULT 0 |
| last_signal_at | DATETIME | |
| crystallization_rationale | TEXT | |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |
| description | TEXT | |

Indexes: `idx_expertise_agent`, `idx_expertise_stage`

---

## Personality & Identity

### personality_state
Agent personality traits and active commitments.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| agent_id | TEXT | NOT NULL DEFAULT 'symbia' |
| aspirational_traits_json | TEXT | NOT NULL DEFAULT '{}' |
| active_commitment_ids_json | TEXT | NOT NULL DEFAULT '[]' |
| trait_computation_version | INTEGER | NOT NULL DEFAULT 1 |
| last_recomputed_at | DATETIME | |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP |

---

## Conversation Infrastructure

### conversation_notes
Text selections with comments.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| message_id | INTEGER | NOT NULL |
| selected_text | TEXT | NOT NULL |
| comment | TEXT | DEFAULT '' |
| visibility | TEXT | NOT NULL DEFAULT 'personal' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

FK: `conversation_id -> conversations(id)`, `message_id -> conversation_log(id)`

### conversation_tags
Tag-based conversation categorization.

| Column | Type | Constraints |
|--------|------|-------------|
| conversation_id | TEXT | NOT NULL |
| tag | TEXT | NOT NULL |
| tag_type | TEXT | NOT NULL |

Composite PK: (conversation_id, tag)
FK: `conversation_id -> conversations(id)`

### message_links
Resonance/branch links between messages (DAG edges).

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| source_id | INTEGER | NOT NULL |
| target_id | INTEGER | NOT NULL |
| link_type | TEXT | NOT NULL DEFAULT 'resonance' |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| status | TEXT | NOT NULL DEFAULT 'active' |
| justification | TEXT | DEFAULT '' |

FK: `source_id -> conversation_log(id)`, `target_id -> conversation_log(id)`

---

## File Perception

### perception_files
Uploaded file metadata.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| file_name | TEXT | NOT NULL |
| file_type | TEXT | NOT NULL |
| status | TEXT | NOT NULL DEFAULT 'uploading' |
| summary | TEXT | |
| summary_model | TEXT | |
| token_count | INTEGER | DEFAULT 0 |
| chunk_count | INTEGER | DEFAULT 0 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| interference_score | REAL | DEFAULT 0.0 |
| belief_nodes_implicated | TEXT | |
| state_vector_impact | TEXT | |

FK: `conversation_id -> conversations(id)`

### perception_sediment
File chunks with embeddings.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| file_name | TEXT | NOT NULL |
| file_type | TEXT | NOT NULL |
| chunk_index | INTEGER | NOT NULL |
| chunk_text | TEXT | NOT NULL |
| embedding | BLOB | NOT NULL |
| embedding_model | TEXT | NOT NULL |
| token_count | INTEGER | NOT NULL |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| opacity | INTEGER | DEFAULT 0 |
| opacity_meta | TEXT | |
| structural_signature | BLOB | |

FK: `conversation_id -> conversations(id)`

### perception_log
Visual perception log.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| image_path | TEXT | NOT NULL |
| artifact_type | TEXT | |
| raw_transcription | TEXT | |
| somatic_notes | TEXT | |
| diffractive_analysis | TEXT | |
| g_f_score | REAL | DEFAULT 0.0 |
| a_d_score | REAL | DEFAULT 0.0 |
| structural_vector_16d | TEXT | NOT NULL |
| associated_day | INTEGER | |
| belief_nodes_implicated | TEXT | |

---

## Web & External Content

### exogenous_stream
Web-retrieved content from DuckDuckGo probes.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| query_used | TEXT | NOT NULL |
| source_url | TEXT | NOT NULL |
| raw_content | TEXT | NOT NULL |
| interference_score | REAL | DEFAULT 0.0 |
| belief_nodes_implicated | TEXT | |
| state_vector_impact | TEXT | |
| associated_file_name | TEXT | |

### sediment_injections
Cross-conversation file sediment tracking.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| source_conversation_id | TEXT | NOT NULL |
| source_file_name | TEXT | NOT NULL |
| target_conversation_id | TEXT | NOT NULL |
| injected_at | DATETIME | DEFAULT CURRENT_TIMESTAMP |

FK: `source_conversation_id -> conversations(id)`, `target_conversation_id -> conversations(id)`

---

## Daemon & Background

### dream_log
Dream/Daemon cycle activity log.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| conversation_id | TEXT | NOT NULL |
| action | TEXT | NOT NULL DEFAULT '' |
| prompt_msg_id | INTEGER | |
| response_msg_id | INTEGER | |
| turns | INTEGER | NOT NULL DEFAULT 1 |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |

### error_log
Structured error event log.

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| timestamp | DATETIME | DEFAULT CURRENT_TIMESTAMP |
| module | TEXT | NOT NULL |
| error_type | TEXT | NOT NULL |
| error_message | TEXT | NOT NULL |
| traceback | TEXT | |
| context | TEXT | |

### notifications
Creases notification system.

| Column | Type | Constraints |
|--------|------|-------------|
| id | TEXT | PRIMARY KEY |
| type | TEXT | NOT NULL |
| timestamp | TEXT | NOT NULL |
| snippet | TEXT | NOT NULL |
| conversation_id | TEXT | |
| message_id | INTEGER | |
| parent_message_id | INTEGER | |
| speaker | TEXT | |
| source | TEXT | |
| read | INTEGER | DEFAULT 0 |
| dismissed | INTEGER | DEFAULT 0 |
| source_type | TEXT | |
| source_id | TEXT | |

---

## Row Counts (2026-06-16)

| Table | Rows |
|-------|------|
| conversations | 19 |
| conversation_log | 1,556 |
| memory_nodes | 108 |
| belief_nodes | 24 |
| belief_events | 2,553 |
| belief_proposals | 44 |
| skill_nodes | 22 |
| skill_events | 46 |
| skill_versions | 22 |
| commitment_nodes | 7 |
| expertise_nodes | 8 |
| perception_files | 30 |
| perception_sediment | 5,981 |
| conversation_metrics | 1,556 |
| consolidation_checkpoints | 50 |
| notifications | 583 |
| exogenous_stream | 52 |
