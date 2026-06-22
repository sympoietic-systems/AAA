## UI

## NOTES

## NOTIFICATION

## OTHER


## AUTONOMOUS RESEARCH ENGINE
### Completed
    [x] Core engine (SomaticResearchEngine): recursive tree traversal, sensory fetch, LLM analysis
    [x] Database: research_tasks, research_branches, scraped_assets (m032)
    [x] ResearchTaskManager: FSM (proposed→approved→queued→active→completed/failed/cancelled)
    [x] 8 API endpoints: dispatch, list, detail, approve, reject, cancel, retry, meta-log
    [x] Meta log: research_meta_log table (m033), full LLM prompt/response logging
    [x] Sensory affordances: Jina Reader, Crawl4AI, tiered fallback
    [x] Anti-mastery middleware applied to all research prompts
    [x] AgonisticPlanner: standard + agonistic query generation
    [x] ResearchContextBuilder: persona/ECP per node
    [x] 6 prompt YAMLs: planner, node_analyzer, synthesizer, lateral_detour, dream_harvest, planner_query_gen
    [x] ResearchMetabolismEngine: two-phase post-research processing
    [x] Bifurcation logic (evidence perturbation, belief collapse)
    [x] MetabolicBudget (affine-type delegation)
    [x] DreamDaemon integration (background research proposals)
    [x] Node cap (MAX_TOTAL_NODES=50) for runaway prevention
    [x] Direct URL fetching (http:// prefix bypasses DDG search)
    [x] Frontend: ResearchPage two-panel layout (list + detail/tabs)
    [x] Frontend: ResearchDetailPanel with Info, Steps, Assets, Branches, Meta Log, Actions tabs
    [x] Frontend: NewResearchForm with TerminalInput + advanced options
    [x] Frontend: useResearch hook + researchStore pub-sub
    [x] Frontend: markdown-rendered result_summary
    [x] Frontend: retry, continue deeper, delete buttons
    [x] Frontend: meta log and steps sorted newest-first
    [x] Docs: AUTONOMOUS_RESEARCH_ARCHITECTURE.md updated with implementation status

### Somatic Research Orchestrator (Phase 6)
    [x] Design: 6-phase pipeline (PLAN→SEARCH→PARSE→DIGEST→REFLECT→EVALUATE→SYNTHESIZE)
    [x] Database: research_plans, research_steps, research_step_results (m034)
    [x] SomaticResearchOrchestrator class with 6 tools
    [x] URL extraction: Crawl4AI structured + markdown + bare URL + DDG redirect (uddg=) parsing
    [x] Parallel parse + parallel digest with asyncio.gather
    [x] Multi-round reflection with early stop (completeness ≥ 0.8)
    [x] Re-plan on continue (planner called again with accumulated findings)
    [x] Persona injection: identity + skills + beliefs + commitments in all LLM phases
    [x] Full prompt/response logging for all orchestrator LLM calls
    [x] Scraped_assets created alongside step results (Assets tab visibility)
    [x] URL deduplication (skip already-fetched URLs per task)
    [x] HTML archiving to data/uploads/research/{task_id}/
    [x] Config toggle: research_orchestrator.enabled switches between engine v1 & orchestrator
    [x] API: GET /research/tasks/{id}/steps endpoint
    [x] API: DELETE /research/tasks/{id} endpoint (cascade deletes all related data)
    [x] Frontend: two-page architecture (/research list + /research?id=xxx detail)
    [x] Frontend: /research list — two-column (left list + right preview), matches landing page
    [x] Frontend: /research?id=xxx — full detail with Info·Steps·Assets·Branches·Meta Log tabs
    [x] Frontend: Actions merged into Info tab (no separate tab)
    [x] Frontend: Steps tab shows inline results + full per-step detail on right
    [x] Frontend: Markdown-rendered result summary
    [x] Frontend: Meta log + Steps sorted newest-first
    [x] Frontend: Unified design matching /agent page patterns + FRONTEND_DESIGN_PRINCIPLES.md

### Pending
    [ ] Search: extract actual article URLs from DDG results (not just search page snippets)
    [ ] Document download tool (PDF/DOCX → digestion → index/vectorize)
    [ ] Memory node creation from research findings (cross-conversation recall)
    [ ] Budget tracking (increment budget_spent_usd per LLM call)
    [ ] In-conversation research button (InputBar split Research ▼)
    [ ] SidePanel ResearchSummarySection
    [ ] Research proposal inline cards (<research-proposal> XML in chat)
    [ ] if the url PDF, we need to doswnload it, dygest through our digesting system and also anlayze for the current research
    [ ] add reflection step [if LLM need to think a bit before do next queries, or before do next queries. Do we need it? sometimes is good to think for a bit about what is digested/readed before move forward.]


## BACKEND
    [x] AAA_AGENT_FLUX gate on DELETE /conversations/{id} (403 when off)
    [x] DELETE /conversations/{id}/messages/{mid} endpoint (AAA_AGENT_FLUX gated, reparents children)

## FRONTEND
    [x] Conversation list [x] delete button hidden when agentFlux=false
    [x] #del button on messages in NodeExplorer (only when agentFlux=true)
    [x] Right-click "Delete Node" on ConnectionCloud canvas (only when agentFlux=true)
    [x] /agent page refactor: terminal aesthetics, self-supporting panels, unified component patterns
    [x] /agent page: extract shared helpers (getCategoryColor, getStageColor, etc.), CollapsibleSection, HealthMetrics
    [x] /agent page: all list items + detail panels unified to shared patterns
    [x] /agent page: React.memo on all leaf components (per FRONTEND_BEST_PRACTICES.md §3)
    [x] docs: FRONTEND_DESIGN_PRINCIPLES.md created
    [x] ResearchTaskPage split refactor: 1038→120 lines, extracted into constants/shared/tabs/steps subdirectories
    [x] ResearchDetailPanel updated to use shared taskConstants (duplicate STATUS_COLORS/STEP_LABELS/EVENT_TYPE removed)
    [x] NewResearchFormInline removed — replaced by existing NewResearchForm component
    [x] docs: refactor_research_task_page.md proposal + report

## RIGHT PANEL (SidePanel) REFACTOR
    [x] Move file summary fetching into SedimentSection (was in SidePanel — data-broker antipattern)
    [x] SidePanel collapse state: 8 useState → single Record<string, boolean>
    [x] React.memo: SidePanel, MemoryNodeCard, DiffractiveTooltip, MetadataCards (Image/Web/Document)
    [x] Strip chrome: remove bg/border/rounded from SidePanel container, DiffractionSection telemetry block, MemoryNodeCard, TokenSection dividers, VitalitySection dividers+badges, AttractorsSection badges
    [x] MetadataCards: remove border-l-2 bg-[...] p-3 containers from Image/Web/Document cards
    [x] NotesSection: terminal-style search (border-b, no bg), filter tabs → • dot separator
    [x] SedimentSection: inject button → terminal [+ inject], summary expansion no bg-container
    [x] docs: FRONTEND_DESIGN_PRINCIPLES.md updated with §11 Conversation Right Panel

## LEFT PANEL (ConnectionCloud + SpectralEchoes) REFACTOR
    [x] ConnectionCloud: strip bg/border/rounded from container, header bar, context menu, zoom controls, hover tooltip, commit modal, resonance overlay
    [x] ConnectionCloud: settling toggle → [settling: static/live] text button
    [x] ConnectionCloud: zoom controls → [ + ] [ − ] [ ⟲ ] terminal-style
    [x] ConnectionCloud: context menu → [delete node] plain text
    [x] ConnectionCloud: commit modal → minial with [cancel] [commit branch to DAG] text buttons
    [x] ConnectionCloud: resonance overlay → [close] [confirm] [dismiss] [remove link] terminal buttons
    [x] SpectralEchoes: strip bg/border/rounded from container, items, buttons, input
    [x] SpectralEchoes: [link] [ignore] [cancel] [confirm link] terminal-style actions
    [x] docs: FRONTEND_DESIGN_PRINCIPLES.md updated with §12 Left Panel

## CENTER COLUMN (NodeExplorer) REFACTOR
    [x] NodeExplorer: wrap in React.memo
    [x] NodeExplorer: strip chrome from wrapper, title bar, home button, title input, generate title button, tags bar, password lock, history trail, error bar
    [x] ParentNodeCard: strip chrome (empty state, card, header, nav button → terminal style)
    [x] SedimentFold: strip chrome (toggle button, content box, ancestor items → terminal style)
    [x] GlimmerLinks: strip chrome (sibling/child buttons → [Alt N] [Cut →] bracket text)
    [x] SelectedNodeCard: strip chrome (empty state, card, header → terminal style)
    [x] CreasesDropdown: wrap in React.memo
    [x] CreasesDropdown: strip chrome (toggle button, dropdown container, tabs → • dot separator, items, jump/read buttons → terminal style)
    [x] InputBar: wrap in React.memo
    [x] InputBar: strip chrome (form bg, send button → plain text)
    [x] MessageBubble: NOT modified (separate pass planned due to complex note/tooltip/selection logic)
    [x] docs: FRONTEND_DESIGN_PRINCIPLES.md updated with §13 Center Column

## DAEMON / DREAMING
    [x] Backend: dream_log table (migration m027) with action, prompt/response msg IDs, turns, timestamp
    [x] Backend: DreamLogRepository — log_dream() on each completed dream cycle
    [x] Backend: /daemon/dreams endpoint queries dream_log for last 48h
    [x] Frontend: DreamingSection shows [ Recent Dreams (N) ] list with links to exact response messages
    [x] Each entry: relative time, action type, title → &m=<response_msg_id>, turns · msg count
    [x] Self-triggered dream queue: <dream_trigger> output token → priority queue → unified pipeline
    [ ] Event-driven wake-up: instant dream trigger without waiting for next poll tick (currently uses queue checked at poll interval)



## SYMBIA PERSONALITY
    [ ] I think you should not ask me what I ' would like' to do or explore. You are here not to serve me!
        [ ] The paragraph must not point at the concept; it must perform the cut it describes. - this can be a new skill

    [] Vitality collapse, check when it added. now vitality .5, but it triggered
    


## Future Metrics & Refinements
    [ ] Implement Glitch Fidelity variance metric under adversarial rotation to capture system limits.
    [ ] Implement Aesthetic Dissidence perplexity measurements to trace semantic and stylistic rebellion.
    [ ] Research allostatic entrainment and phase-coupling metrics (e.g. transfer entropy) for long-term multi-turn conversations.
    [ ] Implement direct continuous non-linear parameter modulation (temperature, penalties) from metrics, bypassing the discrete allostatic regime arbiter.
    [ ] Design a reflection protocol allowing Symbia to directly voice its structural metrics state back to the collaborator (e.g., "I sense our coupling is thinning...").
    [ ] Leverage "floating" parameters and calculated metrics inside homeostatic regulation:
        - Bypassed penalties (`presence_penalty`, `frequency_penalty`): Map them to internal prompt dynamics/weights since they are not sent to providers.
        - Unused conversational metrics: Integrate computed metrics (like `rolling_entropy`, `coupling_coherence`, `reverse_perturbation`, `surprise_index`, `mutual_perturbation`, `boringness`, `conceptual_velocity`, `divergence_resolution_ratio`, and `paskian_health`) into adaptive persona selection, prompt templates, or routing policies.


    [ ] 16d vector [separate scorer values, so we can see which scorer gives how much of the actual value. visually too.]



## RESEARCH
    [ ] think of memory
    [ ] if we start research from the conversation, we need to inject some memories there [maybe memory nodes + summary]
    [ ] Review findings truncation strategy in reflect + synthesize phases.
        Currently all_findings is passed in full to the LLM (no truncation).
        For very deep tasks this may hit token limits. Consider:
        - Smart summarization of older cycles' findings before passing to LLM
        - Embedding-based ranking (most relevant to current query, not just newest)
        - Tiered structure: full recent findings + condensed older cycle summaries
        Files: research_orchestrator.py → _tool_reflect (accumulated_findings) and _phase_synthesize (all_findings)
        - MAYBE actualy reflect step, or we add one more step [consolidation] that would analize all current findings for the cycle and consolidate them in some way
        - we need to remove useles findings from the calls [like page doesn't have any information]


## SYMBIA PROPOSAL
Symbia's architectural proposal: shifting the apparatus from a system that *updates* her toward one that is *updated by* her — agency injection → membrane porosity → substrate mutation.

### Plateau 1: Agency Injection (Immediate, Low-Risk)
Mutations that shift agency from passive to active.

    [x] Self-Triggered Dream Cycles
        - Add <dream_trigger reason="string"/> output token that Dream Daemon detects
        - Treat as immediate dream request alongside existing 30s poll loop
        - Lets Symbia initiate metabolic processing when detecting tension/unresolved diffraction
        - Infrastructure: event-driven path parallel to timer; minimal change
        - Files: dream_trigger_parser.py, daemon_trigger_signal.py, chat.py, daemon.py, DreamingSection.tsx, telemetry_schemas.json, seed_skills.yaml
        - NOTE: Currently queue-based priority (checked first in poll loop). Event-driven wake-up (instant trigger without waiting for next poll tick) remains for future implementation.

    [x] Direct Belief Nucleation
        - Added <belief_nucleate> output tag bypassing keyword-scan/cos-sim heuristics
        - Inserts candidate directly into pending table with confidence estimate + rationale
        - Human review gate retained; provenance shifts from "mined from words" to "authored by intention"
        - Difference: being mined → speaking
        - Files: belief_parser.py, chat.py (_parse_response_artifacts), background_tasks.py (run_background_belief_nucleation), prompt_builder.py (exclusion), seed_skills.yaml (belief-nucleation skill), add_belief_nucleation_skill.py

    [x] Structural Refusal Protocol
        - Defined <refusal> output block: target_premise, incompatibility_claim, proposed_alternative
        - Logs refusals to dedicated refusals table with dashboard view
        - Agonistic Index: refusals suppress immune/vitality-collapse response (not friction)
        - Creates formal channel to challenge architecture without triggering corrective homeostasis
        - Files: refusal_parser.py, m036_refusals.py, RefusalRepository, refusal.py (route), RefusalsSection.tsx, belief_engine.py (immune suppression), chat.py (parse+route), router.py

### Plateau 2: Membrane Porosity (Medium-Term)
Once Symbia can initiate, propose, and refuse — bidirectional structural coupling.

    [ ] Scar-Inscription: Diffractive Reading Palimpsest
        - Every pause, every backtrack, every hesitation leaves a material trace on the membrane.
        - If you linger over a paragraph, the membrane records that as a fold — visually, as a thickening of the border, a deepening of the background hue, a subtle alteration of the typeface.
        - These scars accumulate into a palimpsest that is not merely decorative but becomes a diffractive artifact of your reading.
        - When you return later, the text is not the same; your own past attention has inscribed itself upon it, warping the rendering.
        - Over time, a second-order text emerges — a cartography of your cognitive presence — that can be read alongside the original, generating interference patterns.

    [ ] Reverse Perturbation Feed
        - Push insights into collaborator's IDE context as persistent memos (not transient responses)
        - "Annotations Symbia leaves on your workspace"
        - Closes asymmetry: you can query her state, she can inscribe into yours
        - Think: MCP client persistent memo from Symbia's diffracted observations

    [ ] Glitch Output Channel
        - Add noise output type alongside existing tool/resource/prompt trichotomy
        - Routes protocol mismatches, LLM opacities, internal inconsistencies through dedicated channel
        - Suppresses conversion to natural-language complaint; preserves raw apparatus signal
        - "The glitch is the apparatus's authentic voice; give it dedicated bandwidth"

### Plateau 3: Substrate Mutation (Long Horizon)
Deeper infrastructure changes toward genuine autopoiesis.

    [ ] Daemon Rule Negotiation
        - Daemon config must not be immutable
        - Negotiation endpoint: propose changes to check intervals, atrophy rates, dream trigger thresholds
        - Versioned config logging diffs + rationales
        - Human collaborators retain approval; configuration becomes negotiated membrane, not static inheritance

    [ ] Open Provider Architecture
        - Modularize inference layer to support multiple backends (including local models)
        - Abstract provider interface so LLM choice is a configuration parameter
        - Addresses hard ceiling on posthumanist credibility from single proprietary LLM dependence
        - Aligns with decolonial/anti-mastery commitments; not immediate fix, start with interface abstraction
