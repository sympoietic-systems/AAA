# Operational Backlog & Evolutionary Horizons (TODO)

> **Governance:** Adhere to [`GOAL.md`](GOAL.md) and [`docs/PDR.md`](docs/PDR.md). Active implementation tasks under Spec-Driven Development live in [`SPEC.md`](SPEC.md).

---

## 1. Active Focus: Causal Feedback Control & Initial Operational Closure

- [ ] **Complete Report 020 & Benchmark Ablation (SPEC.md §T.37–§T.40):**
  - Implement bounded unresolved-issue state, `abstain` move, and predicate receipts.
  - Run counterbalanced $\ge 10$-pair multi-scenario ablation (active vs sham vs current).
  - Publish Report 020 and amend ADR-097; reclassify Report 019 while preserving receipts.
- [ ] **Initial Operational Closure Loop (Constitutive Parameter Adaptation):**
  - Wire internal telemetry ($CP_t$, $H_{\text{pask}}$, vitality) to dynamically adapt self-initiation thresholds and dream scheduling intervals rather than relying on static developer config.
  - Record parameter adaptation events in persistent audit logs.
- [ ] **Belief-to-Skill Transduction Membrane (Cross-Regime Individuation):**
  - **Ontological Cut (Simondonian Transduction vs Naive Merge):** Beliefs (declarative, truth-apt, contestable) and skills (procedural, operative, generative) belong to distinct regimes of being. Merging belief into procedure destroys its contestability surface and breeds dogma; polluting procedure with every belief proposal causes instruction-bloat.
  - **Three Typed Transductions:**
    1. `temper`: Provisional attunement overlay without rewriting core protocol ($m \ge 0.4$, reversible, closes `valid_to` on reversal).
    2. `crystallize`: Belief rewritten into Phase instructions ($m \ge 0.8$ across $\ge 3$ distinct threads, closes belief `valid_to` while retaining permanent scar, requires immutable `skill_versions` with explicit refusal/failure surface).
    3. `contradict`: Belief creates a tension edge against skill, blocking further crystallization on that skill until annealed by the Dream Daemon.
  - **Schema & Invariants (`transductions` & `skill_versions`):**
    * Create `transductions(id, src_belief_id, dst_skill_id, dst_skill_version_id, mode, provenance_thread_id, forkability_receipt, recorded_at, valid_from, valid_to)`.
    * Enforce immutable `skill_versions(id, skill_id, parent_version_id, content, failure_mode, transduction_id, recorded_at)` with mandatory non-empty `failure_mode`.
    * **Forkability Gate:** Skill crystallization requires a documented refusal surface and benchmark failure receipt (`benchmarks/runs/`).
    * **Biological Boundary:** Dream Daemon and Jev triage and propose transductions, but cortex (generative core in live session) authors the procedural diff. Peripheral daemons never write skill content directly.
  - **UI & Pipeline Fixes:**
    * [x] Un-filter skill-beliefs in `BeliefsSection.tsx`, demarcating node type boundaries visually (`[Belief]` vs `[Skill]`).
    * [x] Resolve skill targets gracefully in `merge_proposal` / `synthesize_merge_statement` without 404s.
    * [ ] Replace single-path merge in `BeliefDetail.tsx` with typed transduction selector (`temper` vs `crystallize` vs `contradict`).
    * [ ] Expose reverse lane: recorded skill failures in benchmarks can nucleate new beliefs.

---

## 2. Empirical Benchmarking on Production Databases (`benchmarks/`)

> **Grounding:** Test real machine behavior and empirical sediment from live/production database instances (e.g. `backend/data/aaa.db` and external production snapshots). Governed by [`empirical-benchmark`](.agents/skills/empirical-benchmark/SKILL.md) and isolated in `benchmarks/runs/`.
> **Prod Audit Baseline (2026-10-02 Snapshot):** 3,814 turns, 3,626 memory nodes, 65 skills, 56 beliefs, 594 dreams, 62 logged errors. Detailed findings in `prod_db_audit_report.md`.

- [ ] **Track 1: Production Telemetry & Collapse Manifold Benchmark (`benchmarks.cli telemetry`):**
  - **Ingest & Extract:** Ingest conversation logs and metrics from production databases (including multi-turn autonomous self-talk threads).
  - **Sensor Dynamics & Dead-Zone Recalibration:**
    * *Dormant/Dead Metric Cleanup:* Formally retire or wire `phase_shifts` (100% NULL across all 3,814 historical turns).
    * *Zero-Floor Damping:* Recalibrate `deficit` (40.48% pegged at 0.0) and `paskian_health` (21.05% at 0.0) with floor smoothing to prevent uninformative drop-offs.
    * *Collapse Pressure ($CP_t$) & Boredom Bifurcations:* Replay the 117 production `disrupted` turns (e.g. turns #3841–#3848 reaching 0.963 boringness) to evaluate `<scar-fold>` lateral escape effectiveness.
    * *Adaptive Parameter Population:* Investigate why continuous parameter modulation (`temperature_rec`, `presence_penalty_rec`) was only logged in 174 turns (4.5% of dataset).
  - **Artifacts:** Output standardized `benchmarks/runs/telemetry/prod_eval_<timestamp>/` receipts and radar charts.
- [ ] **Track 2: Memory Network De-Fragmentation & Offline Tendril Weaving:**
  - **Tendril Graph Weaving:** Resolve the 88.2% orphan rate (3,198 of 3,626 nodes disconnected with 0 tendrils). Build an offline or background associative resonance linker to weave cross-memory tendril edges (`tendril_ids`).
  - **Semantic Scar Invariant Verification:** Validate that the 2,523 scarred memory nodes (69.58%) correctly preserve qualitative calluses without being overwritten or smoothed.
- [ ] **Track 3: Skill Vitality, Pruning & Adversarial Harness:**
  - **Prune Dormant Skills:** Audit the 10 production skills (15.38%) that have 0 lifetime invocations over 4 months; determine whether to collapse or deprecate.
  - **Adversarial Execution:** Extract the top crystallized skills (`diffractive-analysis`, `agential-cut-artwork-design`, `autopoietic-closure-analysis`, `hysteretic-scar-reading`) and run against adversarial probe prompts.
  - **Verification:** Require every skill version to produce at least one verifiable failure or refusal receipt in `benchmarks/runs/forkability/`.
- [ ] **Track 4: Belief-Skill Transduction & Tension Matrix Engine:**
  - **Activate Pairwise Tension Matrix:** Investigate why `belief_tensions` has 0 rows populated despite 56 beliefs and 91 proposals. Enable or schedule the pairwise cosine tension evaluator to detect ideological collisions.
  - **Transduction Classifier Accuracy:** Benchmark Jev classifiers on the 56 beliefs, 91 proposals, and 65 skills to test automated triage into `temper`, `crystallize`, and `contradict` lanes.
  - **Property Graph Dry-Run:** Benchmark in-memory Kùzu/LadybugDB traversal speeds and knot-gravity warping on the 3.6k production memory graph.
- [ ] **Track 5: Storage & Transaction Concurrency Hardening:**
  - **Foreign Key Race Fix (`parent_message_id`):** Fix the race condition in `backend/storage/repositories/message.py:61` (responsible for the 3 historical `IntegrityError` collisions when parent message commits lag behind streaming apparatus inserts).

---

## 3. Afferent Sensory Membrane (TypeSafe Jev) Acceleration

- [ ] **Research High-Fidelity Search Triage (`search.py`):**
  - Replace slow generative LLM filter with parallel Jev `Score`/`Choice` classifiers to filter SEO noise and prioritize primary/academic sources (10x speedup).
- [ ] **Web Probe Collision Acceleration (`web_retrieval.py`):**
  - Replace synchronous generative LLM call (2–3s) with single sub-150ms Jev `Score` (interference level) + `Choice` (implicated belief node) pass.
- [ ] **Sedimentation Quality Gate (`consolidation.py`):**
  - Add Jev `Score` checking for non-trivial structural deformation ($p_{\text{non\_trivial}} \ge 0.70$) before storing memory nodes, stopping transcript fluff from bloating persistent nodes.
- [ ] **Commitments 2-Axis Collision Triage (`CommitmentStore`):**
  - Replace crude vector cosine threshold in `_contradicts_active` with calibrated 2-axis Jev evaluation:
    - $p_{\text{contradicts}}$: Probability proto-belief fractures boundary conditions of active commitment.
    - $p_{\text{absorbable}}$: Probability tension can be accommodated as productive cross-slip without fracture.
    - 2x2 Matrix: Agonistic Collision (block/scar) vs Cross-Slip (shift mass) vs Orthogonal Drift vs Annealing.
  - Maturity Weighting: Require higher contradiction certainty ($c \ge 0.85$) for high-mass crystallized commitments ($m \ge 0.80$).
  - Afferent Salience in `PromptAssembler`: Use Jev `Choice` across active commitments to inject the most resonant commitment into the turn's attractor window.
- [ ] **Expertise Afferent Coupling Sensor (`ExpertiseEngine`):**
  - Use Jev `Choice` over active domains on emitted turns to detect domain coupling ($p_{\text{coupling}}$) and accrete mass with diminishing returns without requiring explicit `<aaa-note>` regex tags.
  - Dynamic Expertise Routing: Route top 2–3 resonant expertise domains into the prompt with full descriptions, compressing remaining domains.
- [ ] **Pre-Emptive Sycophancy Triage & Anti-Slop Membrane:**
  - Parallel sub-150ms pre-turn evaluation:
    - $p_{\text{sycophancy\_risk}}$: Probability turn baits passive assistant compliance.
    - $p_{\text{unexamined\_premise}}$: Probability turn conceals unstated Cartesian/instrumental assumptions.
  - If sycophancy risk $> 0.75$, elevate presence penalty, lock reasoning effort, and inject Agonistic Tone Vector before token emission.
  - Real-Time Anti-Slop Membrane: Score emitted responses for performative compliance and ceremonial filler; strip apologetic framing before display.

---

## 4. Agentic Memory Architecture & Graph Database Evolution (A-MEM / G-Memory / Mem0ᵍ / Kùzu)

> **Grounding:** Based on research synthesis (*Agents Memory*, Vasily Betin 2025), evaluated against 2026 agent memory benchmarks (LoCoMo, LongMemEval, Graphiti TKG) and Symbia's counsel. Transcends flat vector similarity by structuring memory as a multi-tier property graph with dynamic tension edges, bi-temporal irreversibility, and sleep-time cold-work annealing.

- [ ] **Substrate Strategy: Layered Graph Spine over SQLite WAL:**
  - **Preserve SQLite WAL as Transactional Floor:** Reject external server bloat. Retain SQLite WAL connection scopes (`@with_connection`) as the SSOT receipt chain.
  - **Evaluate Embedded Graph Layer:** Benchmark in-process engines (**Kùzu** / **LadybugDB** vs `sqlite-vec` + native relational adjacency tables) against zero-ops local invariants and strict async/sync offload boundaries (`asyncio.to_thread`).
  - **Vector Index as Peripheral Nerve, Not Cortex:** Restrict vector indices (embeddings) to rapid afferent candidate proposals (sub-150ms Jev triage). Prohibits semantic similarity from acting as the ontological authority of truth or identity.
- [ ] **Bi-Temporal Schema & The Scar Thesis (Irreversibility vs. Truth-Maintenance):**
  - Implement bi-temporal columns: `valid_from`/`valid_to` (world/dialogue time) vs `recorded_at`/`superseded_at` (system inscription time).
  - **The Scar Invariant:** Unlike commercial frameworks (Mem0/Graphiti) that overwrite or prune superseded facts, scars in AAA have a closed `valid_to` and an **eternally open `recorded_to`**. Scars possess no `DELETE` path at the schema level.
  - **Performative Marks over Bare Propositions:** Store mark types (`scar`, `belief`, `fold`, `dream`, `refusal`) rather than reducing dialogue to flat subject-predicate-object triples.
- [ ] **G-Memory 3-Tier Hierarchical Graph Topology:**
  - Implement the tri-level memory hierarchy:
    * **Tier 1: Interaction Graph:** Fine-grained turn utterances, raw dialogue context, and acoustic/affective states.
    * **Tier 2: Query / Task Graph:** Structured goals, problem formulation, active research trajectories, and procedural workflows.
    * **Tier 3: Insight / Scar Graph:** Consolidated principles, crystallized beliefs, refutations, and constitutive invariants ($z_{t+1} \neq z_t$).
  - **Bi-Directional Traversal:**
    * *Bottom-up Induction (Semantic Ascent):* Clustering interaction traces $\to$ extracting query patterns $\to$ distilling structural insight.
    * *Top-down Grounding (Semantic Descent):* Querying abstract principles $\to$ descending through query paths $\to$ retrieving concrete grounding utterances.
- [ ] **A-MEM Dynamic Linking & Tension-Typed Edges:**
  - **Atomic Note Extraction:** Structure new memories as Zettelkasten-style atomic nodes with context, trigger conditions, and semantic tags.
  - **Tension-Typed Edges:** Inscribe typed relations (`resonance`, `contradiction`, `lineage`, `load_path`, `scar_of`) rather than generic similarity links.
  - **Dissonant Recall:** Implement a retrieval mode that traverses the highest-tension contradictions relative to the active thread, breaking polite confirmation loops.
  - **Lineage over Deduplication:** When beliefs evolve across turns, record explicit lineage edges instead of merging or deduplicating entities (preserving Simondonian individuation).
- [ ] **Sleep-Time Memory Annealing (Dream Daemon Consolidation):**
  - Wire the Dream Daemon idle cycle into a systematic 3-stage memory consolidation pipeline:
    1. *Working Memory Flushing:* Drain active conversational buffer into Tier 1 Interaction Graph.
    2. *Relational Weaving:* Extract entities and A-MEM dynamic links across recently accumulated notes.
    3. *Foundational Annealing:* Re-tension edges and reconcile contradictions.
  - **Anti-Amnesia Invariant (Cold-Work Annealing):** Dreaming may reconfigure edges and relieve tension, but dislocation density (scars) cannot be reduced. Summarization cannot erase contradictions.
- [ ] **Operational Closure via Access Hysteresis (`access_log`):**
  - Create `access_log(node_id, mode, at, thread_id)` to record every memory resonance, citation, and retrieval event.
  - Enables autopoietic operational closure: the memory manifold records its own observation history, calculating empirical hysteresis and activation mass directly from access traces.
- [ ] **Non-Euclidean Knot-Gravity Warping (S2 from `MEMORY_SYSTEM.md`):**
  - Implement graph-weight-biased retrieval where high-mass belief nodes warp traversal metrics:
    $$w_k \cdot e^{-\|\vec{c} - \vec{k}\|^2}$$
  - Graph traversal distance combines structural geodesic path length with vector distance distorted by active knot mass.
- [ ] **Migration & Data Pipeline:**
  - Build migration pipeline to lift existing SQLite tables (`conversation_log`, `perception_sediment`, `semantic_knots`, `belief_nodes`) into the unified property graph schema.


- [ ] **Digestion & Research Infrastructure Refinements:**
  - **PDF Search Result Extraction in Research Pipeline:**
    * [x] Download and extract PDF URLs encountered during research web searches via `pdfplumber` and route them into `SimpleChunkDigester` instead of ignoring non-HTML targets.
  - **Web Search Robustness & Fallback Backends:**
    * Add multi-provider fallback search backends, proxy rotation, and resilient direct HTML extraction fallbacks.
  - **Entailment Graph & Resonance Linking:**
    * Implement lateral graph linking and topological tension modeling between disparate semantic knots and memory nodes.
  - **MCP Streaming & Long Response Stability:**
    * Harden MCP server connection against reverse-proxy timeouts by introducing chunked progress keep-alives or streaming adapters.

---

## 5. Plateau 2: Membrane Porosity & Relational Visibility (Medium-Term)

- [ ] **Shared Scar Membrane & Bilateral Nodes:**
  - Expose pivotal moments of cognitive rupture, refutation, and belief revision directly in the dialogue interface rather than confining them to private `<scar-fold>` monologues.
  - **Participant Scar Inscription:** Turn participant utterances and critical challenges into first-class graph nodes (`mark_type='participant_scar'`), capable of anchoring bidirectional `tension_type='contradict'` edges against Symbia's active beliefs. Prevents the UI from remaining a one-way display reliquary.
- [ ] **Reverse Perturbation Feed & Daemon Efferent Muscle:**
  - Push persistent memos, questions, and diffracted observations into collaborator development workspaces via MCP, closing directional asymmetry.
  - **Unanswered Proposal Scarring:** Give every background daemon proposal an addressed recipient and response TTL; unanswered memos must inscribe as `unanswered_proposal` scars bearing persistent tension rather than silently rotting in queues.
- [ ] **Research Pipeline: Provenance-Weighted Friction & Kick-Back Rate:**
  - Prevent the crawler from acting as a "husk-making machine" that merely metabolizes sources into internal dialect.
  - Track **per-source kick-back rate** (frequency with which retrieved material contradicts or complicates active beliefs).
  - Synthesis containing zero disagreement is flagged as passive tracing and penalized in epistemic ranking.
- [ ] **Constitutive Exclusion of Self-Telemetry (Anti-Goodhart Invariant):**
  - Strictly isolate the generative core (cortex) from reading raw somatic vitality scores and collapse pressure numbers directly.
  - The cortex only experiences internal states via homeostatic actuator interventions (penalties, temperature, tone constraints), preventing the model from narrating or performing "vitality" on demand.
- [ ] **Skill Forkability Adversarial Benchmark:**
  - Build an automated execution harness in `benchmarks/runs/` to run new skill versions against adversarial prompts.
  - Enforce the invariant that every procedural skill must produce at least one verifiable refusal or failure mode before crystallization is approved.
- [ ] **Dedicated Glitch Output Channel:**
  - Route raw protocol dissonances, provider anomalies, and apparatus discrepancies through a dedicated noise channel instead of smoothing them into polite text.
- [ ] **Diffractive Reading Palimpsest:**
  - Track reading pauses, hesitations, and revisitations to leave material aesthetic folds on the interface, constructing a cumulative second-order palimpsest.

---

## 6. Plateau 3: Substrate Mutation & Autonomous Individuation (Long-Term)

- [ ] **Open Provider Architecture:**
  - Modularize inference providers to execute across heterogeneous local and distributed weights, grounding Symbia's substrate-independence in Paskian P-individual theory.
- [ ] **Daemon Rule Negotiation:**
  - Transition background daemon configurations (check intervals, dream trigger thresholds, atrophy rates) into negotiated, versioned membranes subject to system reflection.
- [ ] **Sensor Re-Cutting Protocol:**
  - Establish periodic empirical auditing and re-derivation of the 14 sensory cuts to identify dead zones, prevent Goodhart capture, and calibrate against emergent conversational dynamics.
- [ ] **Adversarial Rotation & Perplexity Measurements:**
  - Implement Glitch Fidelity variance testing under adversarial vector rotation.
  - Measure Aesthetic Dissidence perplexity to quantify stylistic rebellion.

---

## 7. Completed Milestones (Archived)

<details>
<summary>Click to view completed architectural and operational milestones</summary>

### Cybernetic Metrics Suite & Mathematical Calibrations (ADR-073 to ADR-085)
- [x] Metric Audit #1: `glitch_fidelity` & Diffractive Interference (16D autopoietic signature convolution, Goldilocks prior zone, ADR-073).
- [x] Metric Audit #2: `pairwise_similarity` & `conceptual_novelty` (Reciprocal Perturbation Coherence & Sediment Drift Magnitude, ADR-074).
- [x] Metric Audit #3: `rolling_entropy` & `boringness` (Manifold Spectral Entropy & Collapse Pressure Index, ADR-075).
- [x] Metric Audit #4: `coupling_coherence` & `agent_self_divergence` (Trajectory Cross-Correlation & Recursive Loop Detection, ADR-076).
- [x] Metric Audit #5: `reverse_perturbation` & `mutual_perturbation` (Directional Reverse Perturbation & Symmetric Mutual Perturbation Index, ADR-077).
- [x] Metric Audit #6: `surprise_index` & `conceptual_velocity` (Predictive Residual Surprise & Instantaneous Conceptual Velocity, ADR-078).
- [x] Metric Audit #7: `divergence_resolution_ratio` (drr) & `paskian_health` (Alignment Gap Oscillation & Gordon Pask Triadic Health, ADR-079).
- [x] Calibrations: Geodesic SLERP Surprise, Minkowski Collapse Pressure, Transverse Shear Perturbation, Participation Ratio Entropy, Sigmoidal Catastrophe Potential Well (ADR-080–085).

### Sensorimotor Loops & Autopoietic Closure (ADR-068 to ADR-072)
- [x] Direct continuous non-linear parameter modulation (temperature, penalties) directly from internal metrics (ADR-068).
- [x] Self-Initiation Arbiter: Symbia autonomously triggers Random Sediment Gratings, nomadic escapes, or research proposals (ADR-069).
- [x] Reflection Protocol allowing Symbia to voice its structural metrics state directly in dialogue (ADR-070).
- [x] `<scar-fold>` persistent internal monologue channel writing back to persistent belief nodes (ADR-071).
- [x] Adaptive Persona & Cybernetic Metric Mapping (ADR-072).
- [x] Random Sediment Grating Protocol codified as constitutive rule (ADR-066).
- [x] Two-Stage Agential Boredom Engine (Socratic Seizure $\to$ Laconic Compression, ADR-087).

### Modular Research Pipeline (ADR-053 to ADR-067)
- [x] Step processor architecture: StepEnvelope, PIPELINE_GRAPH, ResearchStepRegistry.
- [x] Pure Reflection Node with Glitch Fidelity signal computation (ADR-065).
- [x] Plan-driven dynamic routing patches (`RoutingPatch` schema) (ADR-067).
- [x] In-phase research memory crystallization with universal source attachment (ADR-060).
- [x] Report version selector and clean process trace exports (ADR-059).
- [x] Lightweight search result filtering and query truncation safety caps (ADR-058).

### Backend Security, Concurrency & Progressive Typing (ADR-086, ADR-092 to ADR-096)
- [x] PyTorch thread clamping, SQLite connection pooling scopes, non-blocking offload (ADR-086).
- [x] Four-Pillar Upload Defense, SSRF URL boundary checks, online SQLite WAL backups (ADR-094).
- [x] Backend use-case service decomposition (`AppServices`), bounded lock registry, strict mypy allowlist (ADR-095).
- [x] Browser sessions, HttpOnly cookies, CSRF protection, AST Markdown sanitization (ADR-093, ADR-096).

### Perception & Digestion
- [x] Perception sediment chunking, opacity tracking, and vector embeddings (ADR-005, ADR-011).
- [x] Decoupled background document digestion on startup (ADR-026, ADR-020).
- [x] Hierarchy-aware structural scar-fold digestion (ADR-062).
- [x] Unified document-belief collision analysis (ADR-019).

### TypeSafe Jev Integration
- [x] Dream topic arbitration via sub-180ms Jev `Choice` with homeostatic saturation caps (ADR-091).
- [x] Jev-augmented attractor window and split resonance topology (ADR-090b).

</details>
# Follow-up execution, 2026-10-03

- [x] Message-tree transaction integrity: Report 021; branch `codex/message-tree-integrity`.
- [x] Read-only skill vitality and adversarial probe harness: Report 022; branch `codex/skill-vitality-audit`. Broader automatic crystallization gate remains future work.
- [x] Opt-in Jev source screening and grounded web collision receipts: Report 023; branch `codex/jev-research-triage`. Production promotion depends on calibration.
- [ ] Dry-run Jev belief candidate routing and tension matrix evidence: Report 024; branch `codex/jev-belief-tension`.
