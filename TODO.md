## UI
    [x] Add the information for the request to see (context, metrics, diffractive range, match, and search candidates in SidePanel)

## OTHER
    [x] Background belief digester (integrated into BackgroundStartupScheduler on restart)
    [x] Belief Digestor for the documents too

## Future Metrics & Refinements
    [ ] Implement Glitch Fidelity variance metric under adversarial rotation to capture system limits.
    [ ] Implement Aesthetic Dissidence perplexity measurements to trace semantic and stylistic rebellion.
    [ ] Research allostatic entrainment and phase-coupling metrics (e.g. transfer entropy) for long-term multi-turn conversations.
    [ ] Implement direct continuous non-linear parameter modulation (temperature, penalties) from metrics, bypassing the discrete allostatic regime arbiter.
    [ ] Design a reflection protocol allowing Symbia to directly voice its structural metrics state back to the collaborator (e.g., "I sense our coupling is thinning...").
    [ ] Leverage "floating" parameters and calculated metrics inside homeostatic regulation:
        - Bypassed penalties (`presence_penalty`, `frequency_penalty`): Map them to internal prompt dynamics/weights since they are not sent to providers.
        - Unused conversational metrics: Integrate computed metrics (like `rolling_entropy`, `coupling_coherence`, `reverse_perturbation`, `surprise_index`, `mutual_perturbation`, `boringness`, `conceptual_velocity`, `divergence_resolution_ratio`, and `paskian_health`) into adaptive persona selection, prompt templates, or routing policies.

## Test Suite Rehabilitation
    [ ] Resolve hardcoded "D:/AAA" path in all test files (replace with relative workspace paths).
        - Update `test_step1_db.py` through `test_step6_api.py` and `test_allostatic_metrics.py` to calculate root paths dynamically via `sys.path.insert(0, os.path.abspath(...))`.
    [ ] Fix `test_diffractive_retrieval.py` (`test_dynamic_bounds_and_budget` failure) by mocking `get_embeddings_and_signatures_except`.
        - Inject mock data containing matching 384-dimensional embedding BLOBs and 16-dimensional structural signature BLOBs.
        - Ensure mock inputs satisfy the isomorphic filter constraints (semantic similarity <= 0.45, structural similarity >= 0.80) to correctly trigger nomadic retrieval simulation.

## Memory & Sedimentation (Semantic Knots)
    [ ] Create `semantic_knots` SQLite table schema and migration scripts.
        - Fields: `id` (TEXT PRIMARY KEY), `conversation_id` (TEXT, FK), `created_at` (DATETIME), `weight` (REAL), `concept_payload` (TEXT), `embedding` (BLOB), `embedding_model` (TEXT), `token_count` (INTEGER), `structural_signature` (BLOB).
    [ ] Create `SemanticKnotRepository` with query, retrieval, and signature support.
        - Implement methods: `insert_knot`, `get_by_conversation`, `get_embeddings_and_signatures_except`, and `get_knots_in_similarity_range`.
    [ ] Implement compaction/consolidation of dense conversation logs into semantic knots.
        - Trigger logic: Trigger when conversation exceeds $N$ messages or state transitions to STAGNANT.
        - Compactor: Group older messages, call LLM to distill into an atomic concept, embed, compute 16D signature, and insert as a Knot.
    [ ] Integrate semantic knots querying into diffractive retrieval.
        - Query the `semantic_knots` table during diffractive retrieval alongside nomadic logs.
        - Test the integration to ensure compressed knots are injected into prompt context windows under stagnation.