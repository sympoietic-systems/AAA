"""Module initialization.

Extracted from backend/main.py.
Creates and wires all pipeline processing modules, identity loading,
and belief engine.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


# ── Identity loading ───────────────────────────────────────────────────

def _load_identity(config: dict) -> tuple[dict, str, Path]:
    """Load agent identity from the configured YAML file.

    Returns: (identity_data, agent_name, identity_path)
    """
    personality_cfg = config.get("personality", {})
    identity_path = Path(personality_cfg.get("path", "backend/personality/identity.yaml"))
    if not identity_path.is_absolute():
        # __file__ is backend/bootstrap/modules.py → 3 levels up = project root
        identity_path = Path(__file__).parent.parent.parent / identity_path

    identity_data = {}
    agent_name = "symbia"
    if identity_path.exists():
        with open(identity_path) as f:
            identity_data = yaml.safe_load(f)
            agent_name = identity_data.get("agent", {}).get("name", "symbia")
    logger.info("Agent identity: %s", agent_name)
    return identity_data, agent_name, identity_path


# ── Pipeline modules ───────────────────────────────────────────────────

def _init_modules(
    config: dict,
    repos: dict,
    embedder,
    structural_provider,
    vision_provider,
) -> dict:
    """Create all pipeline processing module instances."""
    ctx_cfg = config.get("context", {})
    llm_compression_cfg = config.get("llm_compression", {})

    # ── Context Collector ──
    from backend.modules.context_collector import ContextCollectorModule
    context_collector = ContextCollectorModule(
        message_repo=repos["message_repo"],
        note_repo=repos["note_repo"],
        max_history=ctx_cfg.get("max_history", 20),
        floating_window=ctx_cfg.get("floating_window", 8),
        caveman_enabled=ctx_cfg.get("caveman_enabled", True),
        compressed_message_repo=repos.get("compressed_message_repo"),
        llm_compression_enabled=llm_compression_cfg.get("enabled", False),
    )

    # ── Conversation Metrics ──
    metrics_cfg = config.get("homeostasis", {})
    from backend.modules.conversation_metrics import ConversationMetricsModule
    conversation_metrics = ConversationMetricsModule(
        message_repo=repos["message_repo"],
        pairwise_window=metrics_cfg.get("pairwise_window", 5),
        entropy_window=metrics_cfg.get("entropy_window", 5),
        agent_self_window=metrics_cfg.get("agent_self_window", 5),
    )

    # ── Homeostatic Regulator ──
    from backend.modules.homeostatic_regulator import HomeostaticRegulatorModule
    homeostatic_regulator = HomeostaticRegulatorModule()

    # ── Trait Computer ──
    trait_cfg = config.get("dynamic_personality", {}).get("trait_computer", {})
    from backend.modules.trait_computer import TraitComputer
    trait_computer = TraitComputer(
        personality_state_repo=repos["personality_state_repo"],
        config=trait_cfg,
        notification_repo=repos["notification_repo"],
    )

    # ── Expertise Engine ──
    expertise_cfg = config.get("dynamic_personality", {}).get("expertise", {})
    from backend.modules.structural_engine import LexiconScorer
    from backend.modules.expertise_engine import ExpertiseEngine
    expert_lexicon = LexiconScorer()
    expertise_engine = ExpertiseEngine(
        expertise_repo=repos["expertise_repo"],
        config=expertise_cfg,
        lexicon_scorer=expert_lexicon,
        notification_repo=repos["notification_repo"],
    )

    # ── Commitment Store ──
    commitment_cfg = config.get("dynamic_personality", {}).get("commitments", {})
    from backend.modules.commitment_store import CommitmentStore
    commitment_store = CommitmentStore(
        commitment_repo=repos["commitment_repo"],
        belief_repo=repos["belief_repo"],
        config=commitment_cfg,
        lexicon_scorer=expert_lexicon,
        notification_repo=repos["notification_repo"],
    )

    # ── Sedimentation Retrieval ──
    sediment_cfg = config.get("sedimentation", {})
    from backend.modules.sedimentation_retrieval import SedimentationRetrievalModule
    sedimentation_retrieval = SedimentationRetrievalModule(
        message_repo=repos["message_repo"],
        sediment_token_budget=sediment_cfg.get("sediment_token_budget", 2000),
        sediment_count=sediment_cfg.get("sediment_count", 10),
        similarity_threshold=sediment_cfg.get("similarity_threshold", 0.3),
        semantic_knot_repo=repos.get("semantic_knot_repo"),
        knot_warping_enabled=sediment_cfg.get("knot_warping_enabled", True),
        knot_warping_weight=sediment_cfg.get("knot_warping_weight", 1.0),
    )

    # ── Diffractive Retrieval ──
    diffractive_cfg = config.get("diffractive_retrieval", {})
    from backend.modules.diffractive_retrieval import DiffractiveRetrievalModule
    diffractive_retrieval = DiffractiveRetrievalModule(
        message_repo=repos["message_repo"],
        perception_repo=repos["perception_repo"],
        semantic_knot_repo=repos["semantic_knot_repo"],
        enabled=diffractive_cfg.get("enabled", True),
        similarity_range_min=diffractive_cfg.get("similarity_range_min", 0.35),
        similarity_range_max=diffractive_cfg.get("similarity_range_max", 0.55),
        file_range_min=diffractive_cfg.get("file_range_min", 0.25),
        file_range_max=diffractive_cfg.get("file_range_max", 0.45),
        max_diffractive_count=diffractive_cfg.get("max_diffractive_count", 3),
        token_budget=diffractive_cfg.get("token_budget", 1500),
        adaptive_hysteresis=diffractive_cfg.get("adaptive_hysteresis", True),
        hysteresis_delta_threshold=diffractive_cfg.get("hysteresis_delta_threshold", 0.35),
    )

    # ── Structural Scorer ──
    from backend.modules.structural_engine import (
        CompositeStructuralScorer,
        StructuralScorerModule,
    )
    structural_scorer = StructuralScorerModule(
        CompositeStructuralScorer(llm_provider=structural_provider, config=config)
    )

    # ── Perception Module ──
    perception_cfg = config.get("perception", {})
    from backend.modules.perception import PerceptionModule
    perception_module = PerceptionModule(
        perception_repo=repos["perception_repo"],
        embedding_service=embedder.service,
        file_token_budget=perception_cfg.get("file_token_budget", 3000),
        top_k_chunks=perception_cfg.get("top_k_chunks", 6),
        chunk_size=perception_cfg.get("chunk_size", 512),
        chunk_overlap=perception_cfg.get("chunk_overlap", 64),
        similarity_threshold=perception_cfg.get("similarity_threshold", 0.25),
        llm_provider=structural_provider,
        vision_provider=vision_provider,
    )

    # ── Web Retrieval ──
    from backend.modules.web_retrieval import WebRetrievalModule
    web_retrieval = WebRetrievalModule(
        perception_repo=repos["perception_repo"],
        embedder=embedder,
        structural_scorer=structural_scorer,
        llm_provider=structural_provider,
        config=config,
    )

    # ── Consolidation Checkpoint ──
    from backend.modules.consolidation_checkpoint import ConsolidationCheckpointModule
    consolidation_checkpoint = ConsolidationCheckpointModule(
        checkpoint_repo=repos["checkpoint_repo"],
        consolidate_threshold=ctx_cfg.get("consolidate_threshold", 15),
        memory_node_repo=repos["memory_node_repo"],
        max_memory_nodes=ctx_cfg.get("max_memory_nodes", 6),
        guaranteed_node_types=ctx_cfg.get(
            "guaranteed_node_types", ["scar", "concept", "tension"]
        ),
        cross_branch_similarity_threshold=ctx_cfg.get(
            "cross_branch_similarity_threshold", 0.4
        ),
    )

    return {
        "context_collector": context_collector,
        "conversation_metrics": conversation_metrics,
        "trait_computer": trait_computer,
        "expertise_engine": expertise_engine,
        "commitment_store": commitment_store,
        "homeostatic_regulator": homeostatic_regulator,
        "sedimentation_retrieval": sedimentation_retrieval,
        "diffractive_retrieval": diffractive_retrieval,
        "structural_scorer": structural_scorer,
        "perception_module": perception_module,
        "web_retrieval": web_retrieval,
        "consolidation_checkpoint": consolidation_checkpoint,
    }


# ── Belief Engine ──────────────────────────────────────────────────────

def _init_belief_engine(repos: dict, identity_path: Path, llm_provider=None):
    """Create the Belief Dynamics Engine."""
    from backend.modules.belief_engine import BeliefDynamicsEngine
    return BeliefDynamicsEngine(
        belief_repo=repos["belief_repo"],
        message_repo=repos["message_repo"],
        identity_yaml_path=identity_path,
        llm_provider=llm_provider,
    )
