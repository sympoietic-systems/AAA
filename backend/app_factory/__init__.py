from backend.skills.metadata import SkillMeta
from backend.skills.registry import SkillRegistry


def register_all(registry: SkillRegistry, embedder, modules: dict, belief_metabolism, llm_module):
    reg = registry

    reg.register_with_meta("embedder", lambda: embedder, SkillMeta(
        name="embedder", description="Encodes text into vector embeddings",
        category="perception", always_run=True,
        children=[
            SkillMeta(name="text_encoder", description="Translates textual sequences into 384-dimensional dense vectors", category="perception"),
            SkillMeta(name="vector_cache", description="Caches computed embeddings to prevent redundant API calls", category="perception"),
        ],
    ))
    reg.register_with_meta("structural_scorer", lambda: modules["structural_scorer"], SkillMeta(
        name="structural_scorer", description="Calculates 16-dimensional cybernetic structural signatures of the message text",
        category="perception", always_run=True,
        children=[
            SkillMeta(name="signature_generator", description="Parses syntax pattern frequencies to output a 16D array", category="perception"),
            SkillMeta(name="dynamic_coordinate_warper", description="Applies dynamic coordinate warping scaling factors", category="perception"),
        ],
    ))
    reg.register_with_meta("conversation_metrics", lambda: modules["conversation_metrics"], SkillMeta(
        name="conversation_metrics", description="Computes real-time conversational vitality and paskian metrics",
        category="perception", always_run=True,
        children=[
            SkillMeta(name="surprise_index", description="Exponentially decaying weighted surprise (d=0.75)", category="perception"),
            SkillMeta(name="boringness", description="Joint failure of mutual perturbation: (1 - rP_t) * (1 - MPI_{t-1})", category="perception"),
            SkillMeta(name="conceptual_velocity", description="Disjoint window centroid drift rate (k=3)", category="perception"),
        ],
    ))
    reg.register_with_meta("context_collector", lambda: modules["context_collector"], SkillMeta(
        name="context_collector", description="Gathers conversation history",
        category="memory", always_run=True,
        children=[
            SkillMeta(name="floating_window", description="Last N messages kept raw and uncompressed", category="memory"),
            SkillMeta(name="caveman_compression", description="Strips filler words from older messages, ~50% token reduction", category="memory"),
        ],
    ))
    reg.register_with_meta("consolidation_checkpoint", lambda: modules["consolidation_checkpoint"], SkillMeta(
        name="consolidation_checkpoint", description="Injects LLM-consolidated conversation summaries and triggers new checkpoints",
        category="memory", always_run=True,
        children=[
            SkillMeta(name="checkpoint_inject", description="Prepends [Consolidated memory: ...] system message from latest checkpoint", category="memory"),
            SkillMeta(name="consolidate_trigger", description="Flags conversations for background consolidation every N messages", category="memory"),
        ],
    ))
    reg.register_with_meta("perception", lambda: modules["perception_module"], SkillMeta(
        name="perception", description="Extracts text from uploaded files, chunks, embeds, and retrieves relevant sediment via similarity",
        category="perception", always_run=False,
        triggers=["file", "document", "pdf", "epub", "mobi", "upload", "read"],
        children=[
            SkillMeta(name="file_extractor", description="Parses text from plain text, PDF, DOCX, EPUB, and MOBI files", category="perception"),
            SkillMeta(name="tripartite_vision", description="Performs OCR, semantic description, diffractive analysis, and aesthetic scoring on images", category="perception"),
        ],
    ))
    reg.register_with_meta("web_retrieval", lambda: modules["web_retrieval"], SkillMeta(
        name="web_retrieval", description="Exogenous rhizomatic web retrieval and HTML scraping",
        category="perception", always_run=True,
        children=[
            SkillMeta(name="rhizome_web_probe", description="Scrapes search engines dynamically to bring exogenous context", category="perception"),
            SkillMeta(name="html_scraper", description="Strips HTML styling/scripts and parses main content to markdown", category="perception"),
        ],
    ))
    reg.register_with_meta("prompt_assembler", lambda: modules["prompt_assembler"], SkillMeta(
        name="prompt_assembler", description="Composes system prompt from identity, skills, sediment, and conversation history within token budget",
        category="reasoning", always_run=True,
    ))
    reg.register_with_meta("belief_metabolism", lambda: belief_metabolism, belief_metabolism.skill_meta)
    reg.register_with_meta("skill_activator", lambda: modules["skill_activator"], SkillMeta(
        name="skill_activator", description="Auto-loads relevant procedural skills each turn via attractor window resonance, semantic vector matching, and keyword triggers",
        category="reasoning", always_run=True,
    ))
    reg.register_with_meta("sedimentation_retrieval", lambda: modules["sedimentation_retrieval"], SkillMeta(
        name="sedimentation_retrieval", description="Retrieves semantically relevant messages from other conversations via embedding similarity",
        category="memory", always_run=True,
        children=[
            SkillMeta(name="similarity_search", description="Cosine similarity over 500 cross-conversation embeddings", category="memory"),
            SkillMeta(name="token_budget", description="Limits sediment to configured token budget (default 2000)", category="memory"),
        ],
    ))
    reg.register_with_meta("diffractive_retrieval", lambda: modules["diffractive_retrieval"], SkillMeta(
        name="diffractive_retrieval", description="Perturbs conversation loops by retrieving semantically orthogonal Nomadic and Dormant context fragments",
        category="memory", always_run=True,
        children=[
            SkillMeta(name="StagnationEvaluator", description="Calculates loop severity via pairwise similarity, novelty, and entropy to trigger intervention", category="memory"),
            SkillMeta(name="NomadicRetriever", description="Retrieves semantically distant but structurally isomorphic memories from other threads", category="memory"),
            SkillMeta(name="SemanticKnotRetriever", description="Retrieves distilled concepts from semantic knots to perturb stagnant conversation loops", category="memory"),
            SkillMeta(name="DormantFileRetriever", description="Retrieves inactive file context segments falling in the dynamic similarity Goldilocks zone", category="memory"),
            SkillMeta(name="BudgetInterleaver", description="Interleaves retrieved items and enforces token context limits based on loop intensity", category="memory"),
        ],
    ))
    reg.register_with_meta("homeostatic_regulator", lambda: modules["homeostatic_regulator"], SkillMeta(
        name="homeostatic_regulator", description="Maps conversational metrics to allostatic regimes and recommends generator parameters",
        category="reasoning", always_run=True,
        children=[
            SkillMeta(name="allostatic_parameter_adjuster", description="Computes offsets for temperature, presence penalty, and frequency penalty", category="reasoning"),
            SkillMeta(name="regime_diagnostician", description="Evaluates conversational metrics to determine homeostatic state flags", category="reasoning"),
        ],
    ))
    reg.register_with_meta("llm_client", lambda: llm_module, SkillMeta(
        name="llm_client", description="Sends messages to the language model and returns the response",
        category="action", always_run=True,
        children=[
            SkillMeta(name="llm_router", description="Manages model pools, fallback rules, and automatic rotation under rate limits", category="action"),
            SkillMeta(name="rate_limit_handler", description="Intercepts 429/503 HTTP responses to apply provider cooling periods", category="action"),
        ],
    ))
