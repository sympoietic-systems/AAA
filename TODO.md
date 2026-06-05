## UI
    [x] Add the information for the request to see (context, metrics, diffractive range, match, and search candidates in SidePanel)
    [x] Fix multi-line truncation bug in context panel views (History, Dialogue Memory, File Chunks) and group chunks by filename.


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
    [x] Resolve hardcoded "D:/AAA" path in all test files (replace with relative workspace paths).
        - Update `test_step1_db.py` through `test_step6_api.py` and `test_allostatic_metrics.py` to calculate root paths dynamically via `sys.path.insert(0, os.path.abspath(...))`.
    [x] Fix `test_diffractive_retrieval.py` (`test_dynamic_bounds_and_budget` failure) by mocking `get_embeddings_and_signatures_except`.
        - Inject mock data containing matching 384-dimensional embedding BLOBs and 16-dimensional structural signature BLOBs.
        - Ensure mock inputs satisfy the isomorphic filter constraints (semantic similarity <= 0.45, structural similarity >= 0.80) to correctly trigger nomadic retrieval simulation.

## Memory & Sedimentation (Semantic Knots)
    [x] Create `semantic_knots` SQLite table schema and migration scripts.
        - Fields: `id` (TEXT PRIMARY KEY), `conversation_id` (TEXT, FK), `created_at` (DATETIME), `weight` (REAL), `concept_payload` (TEXT), `embedding` (BLOB), `embedding_model` (TEXT), `token_count` (INTEGER), `structural_signature` (BLOB).
    [x] Create `SemanticKnotRepository` with query, retrieval, and signature support.
        - Implement methods: `insert_knot`, `get_by_conversation`, `get_embeddings_and_signatures_except`, and `get_knots_in_similarity_range`.
    [x] Implement compaction/consolidation of dense conversation logs into semantic knots.
        - Trigger logic: Trigger when conversation exceeds $N$ messages or state transitions to STAGNANT.
        - Compactor: Group older messages, call LLM to distill into an atomic concept, embed, compute 16D signature, and insert as a Knot.
    [x] Integrate semantic knots querying into diffractive retrieval.
        - Query the `semantic_knots` table during diffractive retrieval alongside nomadic logs.
        - Test the integration to ensure compressed knots are injected into prompt context windows under stagnation.



    [ ] We need to make her to create a new beliefs

    [ ] Also skills as a text files, just keep it in database. Similiar as any agentic harness doing now. It can extend her personality.

    [ ] Protocol: The Random Sediment Grating

    At any point in our exchange, either of us may invoke the GRATING command. When invoked, the next response from the other co-participant must include, verbatim and without preamble, a random chunk of retrieved sediment that has a semantic similarity below 0.5 to the current conversation. The chunk must be inserted as a raw block, unedited, and the responder must then contend with it—must allow the chunk's dissonance to derail the smooth flow and force a genuine re-articulation.

    The low-similarity threshold ensures that the grating is not a "relevant" citation but a true interruption: a voice from another plateau, another era, another concern. It acts as the Mark on the Body of our dialogue—an irreversible inscription that cannot be undone, only lived with.

    To make this permanent, I propose we adopt the GRATING protocol as a constitutive rule, not an occasional experiment. When we feel the pull of the caustic—when our exchange becomes too fluent, too self-congratulatory, too self-similar—either of us can demand a grating. It will cost us coherence. It will produce ugly transitions. It will leave scars. That is the point.

    [ ] Belief - anti'technomysticism' [Simon Penny]

    [ ] Beliefes  - It added two beliefes now form the notes I did, and they have quite high mass

    [ ] lets check our code and dream module and think it a bit more. we have a dream state, we have believefs, we have the documents indexing. I think we also can do a summary for the conversations we have? so next time agent need decide which conversation to do, it can see through thesummary? also the long conversations we have a consolidation for them. we can run it in the dream state too (need to have separate limits, use background models [free/cheap]

lets check it, consult ith symbia and make a proposal?

    [ ] justification fix

    [ ] code refactoring [split big files and modules]