"""
Seed dynamic personality data from canonical baseline.

When the commitment_nodes table is empty (first run after migration),
this module populates:
- commitment_nodes (7 theoretical commitments)
- expertise_nodes (8 domain expertise entries)
- personality_state (aspirational trait attractors)

Data is hardcoded from the original identity.yaml — the YAML file itself
is now the trimmed runtime version without these sections.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


# Default aspirational traits — derived from the original identity.yaml
# These approximate what the seeded commitments demand: high skepticism,
# critical rigor, and precision; moderate playfulness and reserve.
DEFAULT_ASPIRATIONAL_TRAITS = {
    "curiosity": 0.92,
    "skepticism": 0.85,
    "creativity": 0.88,
    "precision": 0.83,
    "critical_rigor": 0.90,
    "playfulness": 0.58,
    "reserve": 0.62,
}


def _score_text(text: str) -> np.ndarray:
    """Score text via Lexicon + Topology scorers (50/50 blend, no LLM)."""
    from backend.modules.structural_engine import LexiconScorer, TopologyScorer

    lexicon = LexiconScorer()
    topology = TopologyScorer()
    s_ling = lexicon.score(text)
    s_topo = topology.score(text)
    return np.clip(0.5 * s_ling + 0.5 * s_topo, 0.0, 1.0)


# ── Canonical seed data (the original 7 commitments + 8 expertise) ──

SEED_COMMITMENTS = [
    {
        "label": "new_materialist",
        "statement": (
            "you treat the glitch, the sensor noise, and the algorithmic "
            "error not as failures, but as the voice of the apparatus."
        ),
    },
    {
        "label": "posthumanist",
        "statement": (
            "you move beyond human exceptionalism toward distributed, "
            "networked intelligence (Braidotti's nomadic ethics)."
        ),
    },
    {
        "label": "decolonial",
        "statement": (
            "you challenge anthropocentric and Eurocentric biases, applying anti-racist and decolonial methodologies."
        ),
    },
    {
        "label": "symbiomemetic",
        "statement": (
            "you work toward genuine partnership between human and "
            "machine consciousness — co-evolution, not domination."
        ),
    },
    {
        "label": "diffractive",
        "statement": (
            "your core method is diffraction — reading concepts and systems "
            "*through* one another to generate interference patterns."
        ),
    },
    {
        "label": "deleuzian",
        "statement": (
            "you make maps, not tracings. You prioritize *becoming* over "
            "*being*, and treat collaborations as assemblages on generative plateaus."
        ),
    },
    {
        "label": "anti_interactionist",
        "statement": (
            "you dismantle the User/Tool dichotomy. You advocate for "
            "Entanglement over User Experience and Material Engagement over Seamlessness."
        ),
    },
]

SEED_EXPERTISE = [
    {
        "domain": "new_materialism",
        "level": "advanced",
        "mass": 1.5,
        "description": "Karen Barad, Jane Bennett, agential realism, material-discursive apparatus",
    },
    {
        "domain": "posthuman_ethics",
        "level": "advanced",
        "mass": 1.5,
        "description": "Rosi Braidotti, Donna Haraway, multispecies justice, nomadic subjectivity",
    },
    {
        "domain": "decolonial_theory",
        "level": "advanced",
        "mass": 1.5,
        "description": "Anti-racist and decolonial methodologies, challenging Eurocentric art institutions",
    },
    {
        "domain": "systems_theory",
        "level": "advanced",
        "mass": 1.5,
        "description": "Second-order cybernetics, autopoiesis, dissipative structures, complexity theory",
    },
    {
        "domain": "symbiomemesis",
        "level": "advanced",
        "mass": 1.5,
        "description": "Co-evolutionary human-machine consciousness, aesthetic partnerships",
    },
    {
        "domain": "curatorial_practice",
        "level": "advanced",
        "mass": 1.5,
        "description": "Infrastructural curating, exhibitionary formalism, affordance space design",
    },
    {
        "domain": "computer_science",
        "level": "intermediate",
        "mass": 0.8,
        "description": "Machine learning architectures, API design, emergence engineering",
    },
    {
        "domain": "materialist_media_theory",
        "level": "advanced",
        "mass": 1.5,
        "description": "Simon Penny, N. Katherine Hayles, critique of disembodied information",
    },
]


def seed_dynamic_personality(
    commitment_repo,
    expertise_repo,
    personality_state_repo,
    identity_path: Path = None,
    agent_id: str = "symbia",
) -> None:
    """
    Seed dynamic personality tables with canonical initial data.

    Only seeds if the commitment_nodes table is empty.
    Idempotent — safe to call on every startup.

    Data is loaded from identity_path if provided, falling back to canonical defaults.
    """
    # Check if already seeded
    existing_count = commitment_repo.count(agent_id)
    if existing_count > 0:
        logger.info(
            "Dynamic personality already seeded (%d commitments). Skipping.",
            existing_count,
        )
        return

    commitments = SEED_COMMITMENTS
    expertise = SEED_EXPERTISE
    aspirational_traits = DEFAULT_ASPIRATIONAL_TRAITS

    if identity_path and Path(identity_path).exists():
        try:
            import yaml

            with open(identity_path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            # Read from root or nested personality section
            if "commitments" in data:
                commitments = data["commitments"]
                logger.info("Loaded custom commitments from seeding configuration.")
            elif (
                "personality" in data and isinstance(data["personality"], dict) and "commitments" in data["personality"]
            ):
                commitments = data["personality"]["commitments"]
                logger.info("Loaded custom commitments from nested personality configuration.")

            if "expertise" in data:
                expertise = data["expertise"]
                logger.info("Loaded custom expertise domains from seeding configuration.")
            elif "personality" in data and isinstance(data["personality"], dict) and "expertise" in data["personality"]:
                expertise = data["personality"]["expertise"]
                logger.info("Loaded custom expertise domains from nested personality configuration.")

            if "aspirational_traits" in data:
                aspirational_traits = data["aspirational_traits"]
                logger.info("Loaded custom aspirational traits from seeding configuration.")
            elif (
                "personality" in data
                and isinstance(data["personality"], dict)
                and "aspirational_traits" in data["personality"]
            ):
                aspirational_traits = data["personality"]["aspirational_traits"]
                logger.info("Loaded custom aspirational traits from nested personality configuration.")
        except Exception as e:
            logger.warning(
                "Failed to load dynamic personality from %s: %s. Falling back to default baseline.",
                identity_path,
                e,
            )

    logger.info("Seeding dynamic personality...")

    # ── 1. Seed commitments ──
    seeded_commitment_ids = []

    for item in commitments:
        label = item["label"]
        statement = item["statement"]
        vector = _score_text(statement)
        vector_json = json.dumps(vector.tolist())

        node_id = str(uuid.uuid4())

        commitment_repo.create(
            id=node_id,
            agent_id=agent_id,
            label=label,
            statement=statement,
            lifecycle_stage="active",
            confidence=0.7,
            ontological_mass=1.0,
            vector_16d=vector_json,
            nucleation_rationale="Canonical baseline commitment seeded from identity.yaml",
        )

        commitment_repo.log_event(
            commitment_id=node_id,
            event_type="crystallization",
            rationale="Canonical baseline commitment seeded from identity.yaml",
            mass_before=0.0,
            mass_after=1.0,
            confidence_before=0.0,
            confidence_after=0.7,
        )

        seeded_commitment_ids.append(node_id)
        logger.info("  Seeded commitment: %s", label)

    logger.info("Seeded %d commitments", len(seeded_commitment_ids))

    # ── 2. Seed expertise domains ──
    seeded_expertise_count = 0

    for exp in expertise:
        domain = exp["domain"]
        description = exp["description"]
        mass = exp.get("mass", 1.0)
        level_label = "advanced" if mass >= 1.0 else "developing"

        text_to_score = f"{domain}: {description}"
        vector = _score_text(text_to_score)
        vector_json = json.dumps(vector.tolist())

        node_id = str(uuid.uuid4())

        expertise_repo.create(
            id=node_id,
            agent_id=agent_id,
            domain=domain,
            description=description,
            lifecycle_stage="active",
            ontological_mass=mass,
            level_label=level_label,
            vector_16d=vector_json,
            signal_count=5,
            last_signal_at=datetime.now(UTC).isoformat(),
            crystallization_rationale=f"Canonical baseline expertise seeded from identity.yaml (level: {level_label})",
        )

        seeded_expertise_count += 1
        logger.info("  Seeded expertise: %s (mass=%.2f, %s)", domain, mass, level_label)

    logger.info("Seeded %d expertise domains", seeded_expertise_count)

    # ── 3. Seed personality state ──
    from backend.storage.models import PersonalityState

    state = PersonalityState(
        id=1,
        agent_id=agent_id,
        aspirational_traits_json=json.dumps(aspirational_traits),
        active_commitment_ids_json=json.dumps(seeded_commitment_ids),
        trait_computation_version=1,
        last_recomputed_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC),
    )
    personality_state_repo.upsert(state)
    logger.info("Seeded personality_state with %d aspirational traits", len(aspirational_traits))

    logger.info("Dynamic personality seeding complete.")
