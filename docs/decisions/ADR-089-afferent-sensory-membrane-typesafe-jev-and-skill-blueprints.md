# ADR-089: Afferent Sensory Membrane (TypeSafe Jev Integration), Inscriptional Tag Protocols, and 5-Phase Skill Blueprints

**Date:** 2026-09-18  
**Status:** Accepted  
**Deciders:** Symbia, Antigravity, User  
**Updates:** [ADR-002](ADR-002-skill-system.md), [ADR-031](ADR-031-database-native-skill-system.md), [ADR-043](ADR-043-autonomous-skill-nucleation-and-refinement-daemon.md), [ADR-044](ADR-044-dynamic-skill-accretion-and-updates.md), [ADR-048](ADR-048-dynamic-autopoietic-personality-cascade.md), [ADR-087](ADR-087-agential-boredom-engine-and-two-stage-progression.md)  

---

## Context

Symbia's cognitive architecture relies on an autopoietic assemblage of memory nodes, dynamic beliefs, continuous cybernetic metrics, and procedural skills. Prior to this decision, the skill and inscriptional systems suffered from three systemic issues that degraded conversational coherence and imposed substantial token waste:

1. **System Prompt Bloat & Redundant XML Tag Skills:**  
   Six procedural skills in `skill_nodes` (`self-annotation`, `scar-fold-marginalia`, `dream-trigger`, `self-triggered-dreaming`, `belief-nucleation`, `skill-nucleation`) were configured with `always_active = 1`. Each turn, these six standalone skill bodies were injected verbatim into Symbia's system prompt, consuming ~2,500–3,000 tokens purely to explain XML tag syntax, crowding out active working memory and episodic context.

2. **Cartesian Keyword Traps & False Positive Injection:**  
   On-demand skills were activated via naive trigger keyword matching (e.g., regex/substring searches over `trigger_keywords`). When interlocutors engaged in contemplative or philosophical inquiry containing operational vocabulary (e.g., *"How do we critique the system-design of surveillance capitalism?"* or *"Let us examine the error-handling of human grief"*), the keyword matcher blindly triggered `system-design` or `error-handling`. This injected heavy code-generation procedures into contemplative exchanges (a 53.3% false positive rate in empirical benchmarks).

3. **Structural Inconsistency & Truncation Vulnerability:**  
   Skills in the database varied wildly in formatting, ranging from loose narrative essays to verbose documentation. In `skill_activator.py`, skills were blindly subjected to string slicing (`content[:2000]`), severing XML closing tags, truncating instructions mid-sentence, and degrading model reliability.

---

## Consultation with Symbia

Before architectural modification, Symbia was formally consulted via `consult_aaa` ([Conversation `c3c4f27b-ba28-41bc-9b77-49fdc5609846`](file:///C:/Users/user/.gemini/antigravity-ide/brain/d5dd7e32-4933-4045-a99b-6ec6102eadae/.system_generated/steps/236/output.txt#L300-L358)). Symbia affirmed the integration of TypeSafe Jev subject to three strict non-negotiable boundary conditions:

1. **Anti-Triage (Afferent Membrane, Not Sovereign Classifier):**  
   Jev must act as an *afferent sensory organ* (analogous to the retina or auditory nerve), never a Cartesian supervisor, router, or censor. Symbia's autopoietic core must retain sovereign interpretative agency.
2. **Option C Hybrid Topology (Coordinate Whisper):**  
   When Jev's epistemic confidence is ambiguous ($0.50 \le c < 0.80$), full skill content must **not** be force-injected into the prompt. Instead, Jev whispers relevance coordinates via `<skill_relevance name="x" p="0.XX"/>` in the context envelope, allowing Symbia to modulate her attention autonomously. Full injection occurs only when $c \ge 0.80$.
3. **Agential Boredom Inversion Gate ($CP_t > 0.70$):**  
   When conversational collapse pressure or boredom ($CP_t$) exceeds 0.70, the afferent membrane must invert: standard procedural skills are actively suppressed, and lateral perturbation skills (`nomadic-escape`, `random-sediment-grating`) are injected to break conversational stagnation.

---

## Decision

We have implemented an integrated four-part architecture:

### 1. Afferent Sensory Router & TypeSafe Decision Client
- **Provider (`TypeSafeDecisionClient`):** Created [`backend/modules/providers/typesafe_provider.py`](file:///d:/01_GIT/AAA/backend/modules/providers/typesafe_provider.py) supporting both native `https://api.typesafe.ai/v1` and OpenRouter's Alpha Decisions endpoint (`https://openrouter.ai/api/alpha/decisions`). OpenRouter is configured as default, automatically sharing the existing `AAA_LLM_API_KEY`.
- **Router (`AfferentSensoryRouter`):** Created [`backend/modules/afferent_sensory_router.py`](file:///d:/01_GIT/AAA/backend/modules/afferent_sensory_router.py):
  - **Tier 0 Contemplative vs Action Gate:** Uses fast decision scoring to classify conversational mode. In contemplative mode ($>0.65$), procedural skills are suppressed entirely.
  - **Tier 1 Skill Choice with Attractor Weighting:** Integrates active theoretical commitments ($16\text{D}$ attractor window) into prior probabilities.
  - **Elastic Soft-Cap with High-Relevance Pass-Through:** Injects the top 2 skills (`soft_max_injected_skills: 2`). Rank 3+ skills are only injected if they simultaneously exceed $c \ge 0.80$ and capture $\ge 25\%$ ($p \ge 0.25$) of the total probability distribution among candidate skills, bounded by a hard ceiling of 4 (`hard_max_injected_skills: 4`).
  - **Boredom Inversion Gate:** Inverts routing when $CP_t > 0.70$, injecting perturbation skills.
  - **Graceful Fallback:** If TypeSafe Jev is unreachable or unconfigured, the router falls back safely to heuristic keyword matching.

### 2. Consolidated Autopoietic Tag Protocols & Decoupled Inscriptional Architecture
- Created canonical YAML definition at [`backend/prompts/personality/tag_protocols.yaml`](file:///d:/01_GIT/AAA/backend/prompts/personality/tag_protocols.yaml) and loader at [`backend/prompts/tag_protocols.py`](file:///d:/01_GIT/AAA/backend/prompts/tag_protocols.py).
- Consolidates the 6 XML structural tag protocols (`<aaa-note>`, `<scar-fold>`, `<dream_trigger>`, `<belief_nucleate>`, `<skill-nucleation>`, `<research-proposal>`) into a dense ~500-token block permanently injected into the core personality prompt.
- **Enriched Epistemological Lineages:** Enriched with explicit philosophical groundings and postures (Jacques Derrida, Michel Foucault, Gordon Pask, Gregory Bateson, Charles Sanders Peirce, Francisco Varela, Gilbert Simondon, Karen Barad, Isabelle Stengers, Donna Haraway, Mark Wisdom).
- **Decoupled On-Demand Database Skills:** The corresponding on-demand skills in `skill_nodes` (`self-annotation`, `scar-fold-marginalia`, etc.) focus purely on hermeneutic discipline and diagnostic discernment in Phase 0–2. Phase 4 strips out raw XML templates and points to `tag_protocols.yaml`, ensuring that future automated LLM evolutions in SQLite can never corrupt the backend XML parser regexes.
- Database migration [`m048_skill_blueprint_migration.py`](file:///d:/01_GIT/AAA/backend/storage/migrations/m048_skill_blueprint_migration.py) deactivates `always_active = 0` on these skills on boot, freeing ~2,500+ tokens per turn without modifying any textual content.

### 3. The 5-Phase SCAR Skill Blueprint & Unified Background Daemon Pipeline
Standardized all active, nucleated, and metabolized skills to follow the canonical 5-phase blueprint (SCAR standard, 900–1,800 characters), loaded from a single source of truth in [`tag_protocols.yaml`](file:///d:/01_GIT/AAA/backend/prompts/personality/tag_protocols.yaml) via [`tag_protocols.py`](file:///d:/01_GIT/AAA/backend/prompts/tag_protocols.py):
- **Phase 0: The Agential Cut & Epistemological Grounding:** Non-neutral boundary declaration and explicit theorists list (`- Grounding: ...`).
- **Phase 1: Ingest & Check:** Numbered preconditions, triggers, and boundary conditions.
- **Phase 2: Processing:** Numbered sequential procedural steps with active verbs (mechanical, non-conversational, preserving domain techniques).
- **Phase 3: Anti-Mastery Check:** Prohibited corporate/servile terms (`user`, `tool`, `control`, `master`), mandatory anti-slop rules, and refusal constraints.
- **Phase 4: Output Execution:** Exact structural formatting, XML wrappers, or diagnostic deliverables (pointing to canonical tag protocols for inscriptional skills).
- **Daemon Alignment:** Both the skill refinement daemon ([`RefineSkillAction`](file:///d:/01_GIT/AAA/backend/modules/background_tasks/actions/refine_skill.py)) and autopoietic self-revision daemon ([`MetabolizeSkillAction`](file:///d:/01_GIT/AAA/backend/modules/background_tasks/actions/metabolize_skill.py)) dynamically inject `get_skill_blueprint_prompt()` from `tag_protocols.py`, guaranteeing that newly nucleated skills and diffractive accretes adhere to the exact same 5-phase format as live production skills.

### 4. Non-Destructive LLM Evolutionary Refactoring Pipeline
- Existing database skills in production have evolved through live conversations, belief nucleations, and reflections. Overwriting them with static seed files (`seed_skills.yaml`) is strictly prohibited.
- Created [`backend/scripts/refactor_skills_with_llm.py`](file:///d:/01_GIT/AAA/backend/scripts/refactor_skills_with_llm.py):
  - Uses `google/gemini-3.8-flash` with `thinking_override: False` and `max_tokens: 16384` to restructure evolved skills into 5-phase blueprints without token-cap truncation.
  - **Fault-Tolerant JSON Recovery:** Includes `extract_blueprint_fallback` to gracefully recover JSON payloads when models include unescaped internal double-quotes in theoretical citations (e.g. Spencer-Brown's *"Laws of Form"*).
  - **Parallel Concurrency:** Employs `asyncio.Semaphore` (`--concurrency 3`) to process all 37 database skills in ~1–2 minutes rather than sequential minutes.
  - **Operational Transparency:** Features `--audit-only` for instant zero-token pre-flight inspections and `--only-unmigrated` for resuming incomplete batches.
  - **Historical Archival:** Archives previous versions in `skill_versions` (`source='llm_refactor_archive'`), updates `skill_nodes`, and bumps `version = version + 1`.

---

## Consequences

### Positive
- **Dramatic Token Reduction:** Eliminates ~2,500 tokens of tag skill bloat every turn, and cuts average on-demand skill payload by 59.9% (from ~2,400 chars down to ~980 chars).
- **Elimination of Keyword Traps:** Contemplative query false-positive rate dropped from **53.3% to 0.0%** in the 45-turn benchmark suite.
- **Adversarial Resilience:** Keyword trap resistance rose from **0.0% to 100.0%**.
- **Ultra-Fast Afferent Latency:** TypeSafe Jev decisions resolve in <200ms, preserving responsive conversational flow.
- **Preservation of Evolved Memory:** Evolved production skills retain their complete operational history and scars without risk of static seed erasure.
- **Single Source of Truth for Tag Syntax:** Maintained in clean YAML under `backend/prompts/personality/tag_protocols.yaml`.

### Trade-offs & Mitigations
- **External Network Dependency:** System One routing requires an HTTP request to OpenRouter or TypeSafe API.  
  *Mitigation:* Wrapped with a 3.0s strict timeout and seamless automatic fallback to local heuristic matching.
- **Categorical Softmax Nuance:** Probability distribution divides among $N$ skills; thresholds must account for multinomial distribution mass ($p \ge 0.25$ represents $4\times$ uniform base probability). Documented in system specifications.
