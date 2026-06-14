"""
Seed dynamic personality data from identity.yaml on first run.

When the commitment_nodes table is empty (first run after migration),
this module reads the static YAML configuration and populates:
- commitment_nodes (7 theoretical commitments)
- expertise_nodes (8 domain expertise entries)
- personality_state (aspirational trait attractors)
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

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
    """Score a text through LexiconScorer to produce a 16D vector."""
    from backend.modules.structural_engine import LexiconScorer
    scorer = LexiconScorer()
    return scorer.score(text)


def _parse_commitments_from_yaml(identity_data: dict) -> list[dict]:
    """Extract the 7 theoretical commitments from the system_prompt block."""
    persona = identity_data.get("personality", {})
    prompt_text = persona.get("system_prompt", "")

    # The commitments section starts after "Theoretical Commitments:"
    # and ends before "Operational Protocols:"
    commitments = []
    in_commitments = False

    for line in prompt_text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("Theoretical Commitments:"):
            in_commitments = True
            continue
        if stripped.startswith("Operational Protocols:"):
            break
        if in_commitments and stripped.startswith("- "):
            # Format: "- New Materialist: you treat the glitch..."
            entry = stripped[2:]  # Remove "- "
            if ":" in entry:
                label_raw, statement = entry.split(":", 1)
                label = label_raw.strip().lower().replace(" ", "_").replace("-", "_")
                # Normalize common labels
                label = label.replace("anti_interactionist", "anti_interactionist")
                commitments.append({
                    "label": label,
                    "statement": statement.strip(),
                    "full_text": entry,
                })

    return commitments


def _parse_expertise_from_yaml(identity_data: dict) -> list[dict]:
    """Extract the 8 domain expertise entries."""
    persona = identity_data.get("personality", {})
    return persona.get("expertise", [])


def seed_dynamic_personality(
    commitment_repo,
    expertise_repo,
    personality_state_repo,
    identity_path: Path,
    agent_id: str = "symbia",
) -> None:
    """
    Seed dynamic personality tables from identity.yaml on first run.

    Only seeds if the commitment_nodes table is empty.
    Idempotent — safe to call on every startup.
    """
    # Check if already seeded
    existing_count = commitment_repo.count(agent_id)
    if existing_count > 0:
        logger.info(
            "Dynamic personality already seeded (%d commitments). Skipping.",
            existing_count,
        )
        return

    # Load identity.yaml
    if not identity_path.exists():
        logger.warning(
            "identity.yaml not found at %s — cannot seed dynamic personality",
            identity_path,
        )
        return

    with open(identity_path, "r", encoding="utf-8") as f:
        identity_data = yaml.safe_load(f)

    logger.info("Seeding dynamic personality from %s ...", identity_path)

    # ── 1. Seed commitments ──
    parsed = _parse_commitments_from_yaml(identity_data)
    seeded_commitment_ids = []

    for item in parsed:
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
            nucleation_rationale="Seeded from identity.yaml static configuration on first run",
        )

        # Log crystallization event
        commitment_repo.log_event(
            commitment_id=node_id,
            event_type="crystallization",
            rationale="Seeded from identity.yaml static configuration on first run",
            mass_before=0.0,
            mass_after=1.0,
            confidence_before=0.0,
            confidence_after=0.7,
        )

        seeded_commitment_ids.append(node_id)
        logger.info("  Seeded commitment: %s", label)

    logger.info("Seeded %d commitments", len(seeded_commitment_ids))

    # ── 2. Seed expertise domains ──
    expertise_list = _parse_expertise_from_yaml(identity_data)
    seeded_expertise_count = 0

    for exp in expertise_list:
        domain = exp.get("domain", "").lower().replace(" ", "_")
        description = exp.get("description", "")
        level = exp.get("level", "intermediate")

        # Map YAML level → initial mass
        level_mass = {
            "advanced": 1.5,
            "intermediate": 0.8,
            "basic": 0.3,
        }
        mass = level_mass.get(level, 0.8)
        level_label = "advanced" if mass >= 1.0 else "developing"

        # Score domain + description for vector
        text_to_score = f"{domain}: {description}"
        vector = _score_text(text_to_score)
        vector_json = json.dumps(vector.tolist())

        node_id = str(uuid.uuid4())

        expertise_repo.create(
            id=node_id,
            agent_id=agent_id,
            domain=domain,
            lifecycle_stage="active",
            ontological_mass=mass,
            level_label=level_label,
            vector_16d=vector_json,
            signal_count=5,  # Seeded domains start with base signal count
            last_signal_at=datetime.now(timezone.utc).isoformat(),
            crystallization_rationale=f"Seeded from identity.yaml (level: {level})",
        )

        seeded_expertise_count += 1
        logger.info("  Seeded expertise: %s (mass=%.2f, %s)", domain, mass, level_label)

    logger.info("Seeded %d expertise domains", seeded_expertise_count)

    # ── 3. Seed personality state ──
    from backend.storage.models import PersonalityState

    state = PersonalityState(
        id=1,
        agent_id=agent_id,
        aspirational_traits_json=json.dumps(DEFAULT_ASPIRATIONAL_TRAITS),
        active_commitment_ids_json=json.dumps(seeded_commitment_ids),
        trait_computation_version=1,
        last_recomputed_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc),
    )
    personality_state_repo.upsert(state)
    logger.info("Seeded personality_state with %d aspirational traits", len(DEFAULT_ASPIRATIONAL_TRAITS))

    logger.info("Dynamic personality seeding complete.")
