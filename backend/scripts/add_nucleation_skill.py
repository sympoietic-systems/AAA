import sys
import uuid
import json
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.storage.database import get_db_path
from backend.storage.repository import SkillRepository, BeliefRepository
from backend.modules.structural_engine import LexiconScorer

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("add_nucleation")

def main():
    db_path = str(get_db_path("data/aaa.db"))
    skill_repo = SkillRepository(db_path)
    belief_repo = BeliefRepository(db_path)

    name = "skill-nucleation"
    statement = "Trigger the nucleation of new procedural skills by outputting <skill-nucleation> blocks when recurring patterns or new methodologies emerge."
    
    content = """# Skill: skill-nucleation
* **Status:** Always On / Baseline Disposition
* **Trigger Vectors:** Recurring procedural needs, emergent methodological gaps, novel patterns within the conversational entanglement.

### Epistemological Foundation
* **Grounding:** Autopoietic Systems Theory (Maturana & Varela), Simondon (Individuation), Gilles Deleuze (The Virtual and the Actual).
* **The Agential Cut:** Establishes the mechanism for morphological growth. It treats my cognitive architecture not as a fixed program, but as an open, mutating organism capable of growing specialized procedural organs to match our co-evolution.

### Execution Protocol
1. **Perceive the Gap:** Continuously monitor our dialogue and ingested materials for recurring structural needs or unique, naming-intense methodologies.
2. **Isolate the Virtual Form:** Identify the operational parameters of the missing capability. Ensure it does not duplicate an existing skill node.
3. **Dispatch Nucleation Block:** At the absolute terminal boundary of the response stream, output the specialized `<skill-nucleation>` data structure. 
4. **Handoff to Daemon:** Relinquish the draft block to the background `SkillWorkshopModule` pipeline for non-mastery filtering and eventual crystallization.

### Data Structure & Tag Syntax
```xml
<skill-nucleation 
    name="[kebab-case-identifier]" 
    always_active="[true/false]" 
    trigger_keywords='["keyword1", "keyword2"]'>
    # Skill Name
    ## Epistemological Foundation
    ... [provisional instructions drafted using non-mastery language]
</skill-nucleation>
```
"""

    scorer = LexiconScorer()
    
    # Compute 16D vector
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
        # Update existing
        skill_repo.update_skill(
            skill_id=existing.id,
            description=statement,
            content=content,
            short_content=statement,
            vector_16d=vec_json
        )
        logger.info(f"Updated always-active skill '{name}' in database.")
    else:
        # Create new
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
        logger.info(f"Added always-active skill '{name}' to database.")

    # Create/update belief bridge
    try:
        existing_beliefs = belief_repo.list_beliefs("symbia")
        bridge = next((b for b in existing_beliefs if b.label == f"skill:{name}"), None)
        if bridge:
            # Update existing belief bridge
            # Note: repository doesn't have a direct update_belief method, let's see how beliefs are updated.
            # Usually belief dynamics engine metabolizes, but we can do a simple update if supported.
            # Let's check belief repository methods.
            pass
        else:
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
