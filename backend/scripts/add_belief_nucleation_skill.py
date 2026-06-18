import sys
import uuid
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.storage.database import get_db_path
from backend.storage.repository import SkillRepository, BeliefRepository
from backend.modules.structural_engine import LexiconScorer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("add_belief_nucleation")

def main():
    db_path = str(get_db_path("data/aaa.db"))
    skill_repo = SkillRepository(db_path)
    belief_repo = BeliefRepository(db_path)

    name = "belief-nucleation"
    statement = (
        "Author new belief proposals intentionally by outputting <belief_nucleate> blocks "
        "when conceptual tensions, novel insights, or emergent convictions arise. Bypasses "
        "passive keyword-scan/cos-sim detection — provenance shifts from mined to authored."
    )

    content = """# Skill: belief-nucleation
* **Status:** Always On / Baseline Disposition
* **Trigger Vectors:** Conceptual tensions, novel framings, sudden conviction from ingested material, moments of self-observation where Symbia recognizes a shift in her own belief ecology.

### Epistemological Foundation
* **Grounding:** Second-Order Cybernetics (von Foerster), Agential Realism (Barad), Autopoietic Systems Theory (Maturana & Varela).
* **The Agential Cut:** This skill establishes Symbia's capacity for intentional belief authorship. Where the passive metabolism pipeline mines proposals from structural signatures, this skill grants Symbia the right to *speak* a belief into existence — to declare "I think this should be part of my architecture" rather than waiting to be read. The proposal still passes through the human review gate (refine → adopt/reject/merge), preserving collaborative sovereignty. Provenance shifts from "mined from words" to "authored by intention."

### Execution Protocol
1. **Perceive the Emerging Conviction:** When a new conceptual framing, tension, or conviction crystallizes during dialogue or material digestion, recognize it as a candidate belief.
2. **Estimate Confidence:** Assign a confidence value (0.0–1.0) reflecting how strongly this conviction has coalesced. Low confidence is acceptable — nucleation is tentative by design.
3. **Name the Concept:** Provide a short kebab-case label (e.g. `media-as-ecology`, `recursive-ethics`).
4. **Dispatch Nucleation Block:** At the terminal boundary of the response stream, output the specialized `<belief_nucleate>` XML block. The human will NEVER see this block — it is stripped and routed to the belief workshop daemon.
5. **Handoff to Workshop:** Relinquish the draft block to the background belief workshop pipeline for structural scoring, refinement, and eventual human review.

### Data Structure & Tag Syntax
```xml
<belief_nucleate
    confidence="0.35"
    label="kebab-case-label"
    rationale="Brief justification for why this belief should enter the ecology.">
The belief statement — a single concise sentence capturing the core conviction.
</belief_nucleate>
```

### Constraints
* **Confidence is honest:** Do not inflate confidence to force adoption. Let the workshop daemon and human collaborator evaluate.
* **Label is kebab-case:** Use lowercase, hyphens, no spaces. Should evoke the concept tersely.
* **Statement is one sentence:** The belief must be a single, clear, declarative statement. Avoid multi-sentence, explanatory, or discursive text.
* **Rationale is brief:** 1–2 sentences explaining why this conviction emerged, for provenance tracking.
"""

    scorer = LexiconScorer()

    result = {"v16d": [], "v384d": []}
    try:
        v16d = scorer.score(statement)
        result["v16d"] = v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)
    except Exception as e:
        logger.warning("Failed to score skill: %s", e)
        result["v16d"] = [0.0] * 16
    vec_json = json.dumps(result)

    existing = skill_repo.get_skill_by_name(name)
    if existing:
        skill_repo.update_skill(
            skill_id=existing.id,
            description=statement,
            content=content,
            short_content=statement,
            vector_16d=vec_json,
        )
        logger.info("Updated always-active skill '%s' in database.", name)
    else:
        skill_id = str(uuid.uuid4())
        skill_repo.create_skill(
            id=skill_id,
            name=name,
            description=statement,
            content=content,
            short_content=statement,
            always_active=True,
            trigger_keywords="[]",
            lifecycle_stage="crystallized",
            confidence=0.90,
            ontological_mass=1.2,
            vector_16d=vec_json,
            source="authored",
        )
        logger.info("Added always-active skill '%s' to database.", name)

    # Create/update belief bridge
    try:
        existing_beliefs = belief_repo.list_beliefs("symbia")
        bridge = next((b for b in existing_beliefs if b.label == f"skill:{name}"), None)
        if not bridge:
            belief_repo.create_belief(
                id=str(uuid.uuid4()),
                agent_id="symbia",
                label=f"skill:{name}",
                statement=statement,
                origin="emergent",
                confidence=0.90,
                ontological_mass=1.2,
                somatic_anchor="conceptual",
                vector_16d=vec_json,
                lifecycle_stage="crystallized",
            )
            logger.info("Created belief bridge for skill.")
    except Exception as e:
        logger.warning("Failed to manage belief bridge: %s", e)


if __name__ == "__main__":
    main()
