from backend.pipeline.metadata import ModuleMeta
from backend.pipeline.registry import PipelineRegistry


def register_all(registry: PipelineRegistry, embedder, modules: dict, belief_metabolism, llm_module):
    reg = registry

    reg.register_with_meta("embedder", lambda: embedder, ModuleMeta(
        name="embedder", description="Encodes text into vector embeddings",
        category="perception", always_run=True,
        children=[
            ModuleMeta(name="text_encoder", description="Translates textual sequences into 384-dimensional dense vectors", category="perception"),
            ModuleMeta(name="vector_cache", description="Caches computed embeddings to prevent redundant API calls", category="perception"),
        ],
    ))
    reg.register_with_meta("structural_scorer", lambda: modules["structural_scorer"], ModuleMeta(
        name="structural_scorer", description="Calculates 16-dimensional cybernetic structural signatures of the message text",
        category="perception", always_run=True,
        children=[
            ModuleMeta(name="signature_generator", description="Parses syntax pattern frequencies to output a 16D array", category="perception"),
            ModuleMeta(name="dynamic_coordinate_warper", description="Applies dynamic coordinate warping scaling factors", category="perception"),
        ],
    ))
    reg.register_with_meta("conversation_metrics", lambda: modules["conversation_metrics"], ModuleMeta(
        name="conversation_metrics", description="Computes real-time conversational vitality and paskian metrics",
        category="perception", always_run=True,
        children=[
            ModuleMeta(name="surprise_index", description="Exponentially decaying weighted surprise (d=0.75)", category="perception"),
            ModuleMeta(name="boringness", description="Joint failure of mutual perturbation: (1 - rP_t) * (1 - MPI_{t-1})", category="perception"),
            ModuleMeta(name="conceptual_velocity", description="Disjoint window centroid drift rate (k=3)", category="perception"),
        ],
    ))
    reg.register_with_meta("trait_computer", lambda: modules["trait_computer"], ModuleMeta(
        name="trait_computer", description="Computes descriptive personality traits from conversation metrics with anti-erosion guard and aspirational gap",
        category="reasoning", always_run=True,
        children=[
            ModuleMeta(name="descriptive_trait_computation", description="Maps 8 conversation metrics to 7 personality traits via sigmoid-weighted formulas", category="reasoning"),
            ModuleMeta(name="anti_erosion_resistance", description="Boosts skepticism when agreement patterns exceed threshold to resist user-pleasing drift", category="reasoning"),
            ModuleMeta(name="aspirational_gap", description="Measures Euclidean distance between descriptive traits and commitment-derived aspirational attractors", category="reasoning"),
        ],
    ))
    reg.register_with_meta("expertise_engine", lambda: modules["expertise_engine"], ModuleMeta(
        name="expertise_engine", description="Accretes domain expertise mass from demonstrable structural coupling signals (aaa-note tags, skill nucleations, cross-conversation returns)",
        category="reasoning", always_run=True,
        children=[
            ModuleMeta(name="signal_detection", description="Scans assistant messages for aaa-note domain tags, skill nucleations, and external note/document matches", category="reasoning"),
            ModuleMeta(name="mass_accretion", description="Applies diminishing-returns accretion formula with weighted signal sources (self-generated > ingested)", category="reasoning"),
            ModuleMeta(name="domain_lifecycle", description="Manages proto→active→dormant transitions based on accretion thresholds and inactivity periods", category="reasoning"),
        ],
    ))
    reg.register_with_meta("commitment_store", lambda: modules["commitment_store"], ModuleMeta(
        name="commitment_store", description="Manages theoretical commitment lifecycle — post-hoc belief filter, daemon-driven nucleation/collapse, mass recalculation",
        category="reasoning", always_run=True,
        children=[
            ModuleMeta(name="belief_filter", description="Blocks proto-belief proposals that contradict active commitments or re-adopt spectral territory", category="reasoning"),
            ModuleMeta(name="nucleation_scanner", description="Background daemon scans belief tension field for orphan clusters with sustained diffractive tension to nucleate proto-commitments", category="reasoning"),
            ModuleMeta(name="collapse_detector", description="Detects commitment collapse when all basin beliefs have collapsed and confidence drops below threshold", category="reasoning"),
            ModuleMeta(name="mass_recalculator", description="Periodically recalculates commitment ontological mass as sum of in-basin belief masses", category="reasoning"),
        ],
    ))
    reg.register_with_meta("context_collector", lambda: modules["context_collector"], ModuleMeta(
        name="context_collector", description="Gathers conversation history",
        category="memory", always_run=True,
        children=[
            ModuleMeta(name="floating_window", description="Last N messages kept raw and uncompressed", category="memory"),
            ModuleMeta(name="caveman_compression", description="Strips filler words from older messages, ~50% token reduction", category="memory"),
        ],
    ))
    reg.register_with_meta("consolidation_checkpoint", lambda: modules["consolidation_checkpoint"], ModuleMeta(
        name="consolidation_checkpoint", description="Injects LLM-consolidated conversation summaries and triggers new checkpoints",
        category="memory", always_run=True,
        children=[
            ModuleMeta(name="checkpoint_inject", description="Prepends [Consolidated memory: ...] system message from latest checkpoint", category="memory"),
            ModuleMeta(name="consolidate_trigger", description="Flags conversations for background consolidation every N messages", category="memory"),
        ],
    ))
    reg.register_with_meta("perception", lambda: modules["perception_module"], ModuleMeta(
        name="perception", description="Extracts text from uploaded files, chunks, embeds, and retrieves relevant sediment via similarity",
        category="perception", always_run=False,
        triggers=["file", "document", "pdf", "epub", "mobi", "upload", "read"],
        children=[
            ModuleMeta(name="file_extractor", description="Parses text from plain text, PDF, DOCX, EPUB, and MOBI files", category="perception"),
            ModuleMeta(name="tripartite_vision", description="Performs OCR, semantic description, diffractive analysis, and aesthetic scoring on images", category="perception"),
        ],
    ))
    reg.register_with_meta("web_retrieval", lambda: modules["web_retrieval"], ModuleMeta(
        name="web_retrieval", description="Exogenous rhizomatic web retrieval and HTML scraping",
        category="perception", always_run=True,
        children=[
            ModuleMeta(name="rhizome_web_probe", description="Scrapes search engines dynamically to bring exogenous context", category="perception"),
            ModuleMeta(name="html_scraper", description="Strips HTML styling/scripts and parses main content to markdown", category="perception"),
        ],
    ))
    reg.register_with_meta("prompt_assembler", lambda: modules["prompt_assembler"], ModuleMeta(
        name="prompt_assembler", description="Composes system prompt from identity, skills, sediment, and conversation history within token budget",
        category="reasoning", always_run=True,
    ))
    reg.register_with_meta("belief_metabolism", lambda: belief_metabolism, belief_metabolism.module_meta)
    reg.register_with_meta("skill_activator", lambda: modules["skill_activator"], ModuleMeta(
        name="skill_activator", description="Auto-loads relevant procedural skills each turn via attractor window resonance, semantic vector matching, and keyword triggers",
        category="reasoning", always_run=True,
    ))
    reg.register_with_meta("skill_workshop", lambda: modules["skill_workshop"], ModuleMeta(
        name="skill_workshop", description="Propose, revise, review, apply, and reject procedural skills with three-tier approval and diffractive anti-mastery assessment",
        category="action", always_run=False,
        triggers=["skill workshop", "create skill", "new skill", "develop skill", "load skill", "review skill"],
        children=[
            ModuleMeta(name="skill_metabolism", description="Asynchronous metabolic loop analyzing performance decay, belief-tectonic shifts, and conversation friction to trigger LLM patches", category="action"),
            ModuleMeta(name="anti_mastery_validation", description="Heuristic filter rejecting self-revisions containing prohibited master/control/user/tool vocabulary", category="action"),
        ],
    ))
    reg.register_with_meta("sedimentation_retrieval", lambda: modules["sedimentation_retrieval"], ModuleMeta(
        name="sedimentation_retrieval", description="Retrieves semantically relevant messages from other conversations via embedding similarity",
        category="memory", always_run=True,
        children=[
            ModuleMeta(name="similarity_search", description="Cosine similarity over 500 cross-conversation embeddings", category="memory"),
            ModuleMeta(name="token_budget", description="Limits sediment to configured token budget (default 2000)", category="memory"),
        ],
    ))
    reg.register_with_meta("diffractive_retrieval", lambda: modules["diffractive_retrieval"], ModuleMeta(
        name="diffractive_retrieval", description="Perturbs conversation loops by retrieving semantically orthogonal Nomadic and Dormant context fragments",
        category="memory", always_run=True,
        children=[
            ModuleMeta(name="StagnationEvaluator", description="Calculates loop severity via pairwise similarity, novelty, and entropy to trigger intervention", category="memory"),
            ModuleMeta(name="NomadicRetriever", description="Retrieves semantically distant but structurally isomorphic memories from other threads", category="memory"),
            ModuleMeta(name="SemanticKnotRetriever", description="Retrieves distilled concepts from semantic knots to perturb stagnant conversation loops", category="memory"),
            ModuleMeta(name="DormantFileRetriever", description="Retrieves inactive file context segments falling in the dynamic similarity Goldilocks zone", category="memory"),
            ModuleMeta(name="BudgetInterleaver", description="Interleaves retrieved items and enforces token context limits based on loop intensity", category="memory"),
        ],
    ))
    reg.register_with_meta("homeostatic_regulator", lambda: modules["homeostatic_regulator"], ModuleMeta(
        name="homeostatic_regulator", description="Maps conversational metrics to allostatic regimes and recommends generator parameters",
        category="reasoning", always_run=True,
        children=[
            ModuleMeta(name="allostatic_parameter_adjuster", description="Computes offsets for temperature, presence penalty, and frequency penalty", category="reasoning"),
            ModuleMeta(name="regime_diagnostician", description="Evaluates conversational metrics to determine homeostatic state flags", category="reasoning"),
        ],
    ))
    reg.register_with_meta("llm_client", lambda: llm_module, ModuleMeta(
        name="llm_client", description="Sends messages to the language model and returns the response",
        category="action", always_run=True,
        children=[
            ModuleMeta(name="llm_router", description="Manages model pools, fallback rules, and automatic rotation under rate limits", category="action"),
            ModuleMeta(name="rate_limit_handler", description="Intercepts 429/503 HTTP responses to apply provider cooling periods", category="action"),
        ],
    ))
