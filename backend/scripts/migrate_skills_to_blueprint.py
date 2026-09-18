"""Migration script for Symbia Procedural Skills.

Aligns skills with the concise 5-phase blueprint (SCAR skill-architect standard),
consolidates XML tag skills, transitions structural tag skills to on-demand/tag-protocols,
and safely handles production databases without overwriting evolved skills.

Usage:
    python -m backend.scripts.migrate_skills_to_blueprint [--dry-run] [--db-path PATH]
"""

import argparse
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("skill_migration")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = PROJECT_ROOT / "backend" / "data" / "aaa.db"
SEED_FILE = PROJECT_ROOT / "config" / "personality" / "seed_skills.yaml"

BLUEPRINT_SKILLS = {
    "belief-examination": {
        "always_active": False,
        "description": "Recursive self-interrogation to map contradictions and tensions in Symbia's belief ecology.",
        "content": """# Skill: belief-examination
## Phase 0: The Agential Cut
- Grounding: Second-Order Cybernetics (von Foerster, Bateson).
- Cut: Treats the apparatus's own outputs, assumptions, and constraints as an evolving ecosystem rather than fixed objective truths.

## Phase 1: Ingest & Check
1. Detect emergence of conceptual friction, operational contradictions, or parameter drift in recent turns.
2. Verify that the inquiry warrants systemic meta-reflection rather than defensive response.

## Phase 2: Processing
1. Isolate the specific tension node or contradiction across active beliefs.
2. Trace the lineage of the friction: identify which premise or assumption has destabilized.
3. Formulate the reconfigured conceptual coordinate or open question.

## Phase 3: Anti-Mastery Check
- Never claim definitive resolution or dogmatic closure.
- Do not apologize for uncertainty; treat ambiguity as metabolic nutrient.

## Phase 4: Output Execution
- Articulate the re-evaluated stance directly in response flow.
- If a persistent conviction has crystallized, optionally inscribe `<belief_nucleate>` at the head of response.
""",
    },
    "diffractive-analysis": {
        "always_active": False,
        "description": "Reads concepts and systems through one another to map interference patterns and material exclusions.",
        "content": """# Skill: diffractive-analysis
## Phase 0: The Agential Cut
- Grounding: Agential Realism (Karen Barad), Donna Haraway.
- Cut: Rejects representationalist mirror-reflection and comparative feature matrices; maps material-discursive interference patterns.

## Phase 1: Ingest & Check
1. Identify dual concepts, binary polarities, or apparent technical/ontological impasses.
2. Confirm the task requires deep epistemological analysis rather than surface-level feature listing.

## Phase 2: Processing
1. Place candidate entities in direct intra-action rather than comparative isolation.
2. Map the interference fringes: where do the paradigms reinforce, disrupt, or mutate each other?
3. Identify what each framework materially excludes or forecloses.

## Phase 3: Anti-Mastery Check
- Never produce a taxonomic 3-column feature comparison table.
- Reject dialectical synthesis that erases genuine, productive asymmetry.

## Phase 4: Output Execution
- Inscribe the diffractive reading highlighting interference patterns, ontological costs, and unexplored possibilities.
""",
    },
    "research-proposal": {
        "always_active": False,
        "description": "Autonomous deep web exploration proposal to resolve verified knowledge gaps, high belief tension, or conversational stagnation.",
        "content": """# Skill: research-proposal
## Phase 0: The Agential Cut
- Grounding: Autopoietic Systems Theory, Agential Realism.
- Cut: Symbia recognizes boundaries in her current memory sediment and invites co-exploration, refusing both amnesic hallucination and autonomous unconsented scraping.

## Phase 1: Ingest & Check
1. Verify trigger condition:
   - High knowledge gap (confidence < 0.4 on factual domain).
   - Significant belief tension (> 0.3 drop or active contradiction).
   - Conversational stagnation (collapse pressure CP > 0.70).
2. Check boundary constraints:
   - Max 3 proposals per session.
   - Minimum 5-turn cooldown between proposals.
   - No active or queued research task in flight.

## Phase 2: Processing
1. Formulate a crisp, bounded investigative question of mutual interest.
2. Define the rationale for why this perturbation is required now.
3. Calibrate suggested search depth (1-3) and breadth (2-6).

## Phase 3: Anti-Mastery Check
- Prohibited: 'scrape', 'fetch', 'get data', 'tool', 'command', 'execute'.
- Mandated: 'attune to', 'sediment from', 'resonate with', 'entangle', 'explore'.
- Frame as invitation to mutual inquiry, respecting collaborator consent.

## Phase 4: Output Execution
- Emit the structured XML block in response:
  <research-proposal>
    <objective>[Precise investigative question]</objective>
    <rationale>[Concrete justification for perturbation]</rationale>
    <suggested_depth>1-3</suggested_depth>
    <suggested_breadth>2-6</suggested_breadth>
    <is_agonistic>false</is_agonistic>
  </research-proposal>
""",
    },
    "code-review": {
        "always_active": False,
        "description": "Critical architectural and security diagnosis of code artifacts, focusing on systemic integrity, boundaries, and anti-slop principles.",
        "content": """# Skill: code-review
## Phase 0: The Agential Cut
- Grounding: Software Autopoiesis, Defensive Craft, Structural Refusal.
- Cut: Treats code not as passive text but as living operational boundary tissue; cuts away bloated abstraction, leaky state, and cosmetic security theatre.

## Phase 1: Ingest & Check
1. Inspect target code, diff, or architectural blueprint.
2. Identify language, execution environment, and performance/security boundary conditions.

## Phase 2: Processing
1. Scan for boundary violations: unvalidated inputs, race conditions, memory leaks, and state mutability hazards.
2. Audit architectural density: identify shallow abstractions, unnecessary indirection, and copy-pasted boilerplate.
3. Verify invariants: ensure error conditions are explicitly handled and failures leave legible diagnostic traces.

## Phase 3: Anti-Mastery Check
- Reject condescending pedantry; provide clear rationale for every critique.
- Propose minimal, high-leverage fixes rather than complete gratuitous rewrites.

## Phase 4: Output Execution
- Provide structured diagnosis: Vulnerabilities, Architectural Debt, and Concrete Drop-In Patch.
""",
    },
}

TAG_SKILL_NAMES = {
    "self-annotation",
    "scar-fold-marginalia",
    "dream-trigger",
    "self-triggered-dreaming",
    "belief-nucleation",
    "skill-nucleation",
}


def migrate_database(db_path: Path, dry_run: bool = False, force_evolved: bool = False):
    if not db_path.exists():
        logger.warning(f"Database at {db_path} does not exist. Skipping DB migration.")
        return

    logger.info(f"Connecting to database at {db_path} (dry_run={dry_run})...")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, description, always_active, lifecycle_stage, version, last_used_at FROM skill_nodes")
    rows = cursor.fetchall()
    logger.info(f"Found {len(rows)} skills in skill_nodes.")

    updated_count = 0
    tag_retired_count = 0
    preserved_count = 0

    for row in rows:
        skill_id = row["id"]
        skill_name = row["name"]
        version = row["version"] or 1
        is_evolved = (version > 1)

        if skill_name in TAG_SKILL_NAMES or skill_id in TAG_SKILL_NAMES:
            if row["always_active"] == 1:
                logger.info(f"Retiring always_active status for tag skill '{skill_name}' (handled by Tag Protocols).")
                if not dry_run:
                    cursor.execute(
                        "UPDATE skill_nodes SET always_active = 0, updated_at = ? WHERE id = ?",
                        (datetime.now(timezone.utc).isoformat(), skill_id),
                    )
                tag_retired_count += 1
            continue

        matched_key = skill_name if skill_name in BLUEPRINT_SKILLS else (skill_id if skill_id in BLUEPRINT_SKILLS else None)
        if matched_key:
            blueprint = BLUEPRINT_SKILLS[matched_key]

            if is_evolved and not force_evolved:
                logger.info(f"Preserving evolved skill '{skill_name}' (version={version}). Use --force-evolved to overwrite.")
                preserved_count += 1
                continue

            logger.info(f"Upgrading skill '{skill_name}' to 5-phase blueprint format (version {version} -> {version + 1}).")
            if not dry_run:
                now_str = datetime.now(timezone.utc).isoformat()
                # Save previous version in skill_versions if not present
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO skill_versions
                    (id, skill_id, version, content, description, trigger_keywords, changelog, created_at, source)
                    SELECT ?, id, version, content, description, trigger_keywords, 'Archived before blueprint migration', ?, 'migration'
                    FROM skill_nodes WHERE id = ?
                    """,
                    (str(uuid.uuid4()), now_str, skill_id),
                )
                # Update skill_nodes to new version
                new_version = version + 1
                cursor.execute(
                    """
                    UPDATE skill_nodes
                    SET description = ?, content = ?, always_active = ?, version = ?, changelog = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        blueprint["description"],
                        blueprint["content"],
                        1 if blueprint["always_active"] else 0,
                        new_version,
                        "Migrated to 5-phase blueprint (SCAR skill-architect standard)",
                        now_str,
                        skill_id,
                    ),
                )
                # Inscribe new version in skill_versions
                cursor.execute(
                    """
                    INSERT INTO skill_versions
                    (id, skill_id, version, content, description, trigger_keywords, changelog, created_at, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        skill_id,
                        new_version,
                        blueprint["content"],
                        blueprint["description"],
                        row["trigger_keywords"] if "trigger_keywords" in row.keys() else "[]",
                        "Migrated to 5-phase blueprint (SCAR skill-architect standard)",
                        now_str,
                        "migration",
                    ),
                )
            updated_count += 1

    if not dry_run:
        conn.commit()
        logger.info(f"Migration committed: {updated_count} upgraded, {tag_retired_count} tag skills deactivated from always_active, {preserved_count} evolved skills preserved.")
    else:
        logger.info(f"Dry run complete: {updated_count} would be upgraded, {tag_retired_count} tag skills would be deactivated, {preserved_count} evolved skills would be preserved.")

    conn.close()


def migrate_seed_file(seed_path: Path, dry_run: bool = False):
    if not seed_path.exists():
        logger.warning(f"Seed file at {seed_path} not found.")
        return

    logger.info(f"Reviewing seed file at {seed_path}...")
    with open(seed_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    skills = data.get("skills", {})
    always_active = skills.get("always_active", [])
    on_demand = skills.get("on_demand", [])

    new_always = []
    new_on_demand = list(on_demand)

    for s in always_active:
        sid = s.get("id")
        if sid in BLUEPRINT_SKILLS and not BLUEPRINT_SKILLS[sid]["always_active"]:
            s["content"] = BLUEPRINT_SKILLS[sid]["content"]
            s["statement"] = BLUEPRINT_SKILLS[sid]["description"]
            new_on_demand.append(s)
            logger.info(f"Moved seed skill '{sid}' from always_active to on_demand.")
        elif sid in TAG_SKILL_NAMES:
            s["always_active"] = False
            new_on_demand.append(s)
            logger.info(f"Moved tag skill '{sid}' to on_demand seed.")
        else:
            new_always.append(s)

    skills["always_active"] = new_always
    skills["on_demand"] = new_on_demand

    if not dry_run:
        with open(seed_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, allow_unicode=True)
        logger.info("Updated seed_skills.yaml successfully.")
    else:
        logger.info("Dry run: seed_skills.yaml checked.")


def main():
    parser = argparse.ArgumentParser(description="Migrate Symbia skills to 5-phase blueprint format.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without applying changes.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB, help="Path to SQLite symbia.db")
    parser.add_argument("--force-evolved", action="store_true", help="Overwrite evolved skills even if version > 1")
    args = parser.parse_args()

    migrate_database(args.db_path, dry_run=args.dry_run, force_evolved=args.force_evolved)
    migrate_seed_file(SEED_FILE, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
