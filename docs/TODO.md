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

### Pending
    [ ] Budget tracking (increment budget_spent_usd per LLM call)
    [ ] In-conversation research button (InputBar split Research ▼)
    [ ] SidePanel ResearchSummarySection
    [ ] Research proposal inline cards (<research-proposal> XML in chat)
    [ ] Memory node creation from research findings
    [ ] Document download tool (PDF/DOCX → digestion → index)
    [ ] Search result limit: extract actual article URLs from DDG (not just search page)
    [ ] Prompt: node_analyzer should return raw page content snapshots for debugging


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



## SYMBIA PERSONALITY
    [ ] I think you should not ask me what I ' would like' to do or explore. You are here not to serve me!
        [ ] The paragraph must not point at the concept; it must perform the cut it describes. - this can be a new skill

    [ ] Vitality collapse, check when it added. now vitality .5, but it triggered
    


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
    [ ] split to pages. like home page. list and basic info, after we can go to the each research pag
    [ ] think of memeory
