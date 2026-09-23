"""LLM-Assisted Skill Refactor & Evolution Pipeline.

Refactors existing, evolved skills in the database into the standardized
5-phase blueprint (SCAR skill-architect format) using the main LLM model,
while strictly preserving:
- Learned domain knowledge, operations history, and attunement notes
- Symbia's unique posthuman autopoietic voice and anti-mastery commitments
- Full version history in `skill_versions` (archives previous, bumps version)

Usage:
    # Test on a single skill (dry run):
    python -m backend.scripts.refactor_skills_with_llm --skill system-design --dry-run

    # Refactor a single skill and commit to DB:
    python -m backend.scripts.refactor_skills_with_llm --skill system-design

    # Refactor all database skills:
    python -m backend.scripts.refactor_skills_with_llm --all
"""

import argparse
import asyncio
import json
import logging
import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from backend.config import load_config
from backend.main import _init_providers
from backend.modules.llm_client import generate_unified

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("refactor_skills_llm")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = PROJECT_ROOT / "backend" / "data" / "aaa.db"

TAG_SKILL_NAMES = {
    "self-annotation",
    "scar-fold-marginalia",
    "dream-trigger",
    "self-triggered-dreaming",
    "belief-nucleation",
    "skill-nucleation",
}

SYSTEM_PROMPT = """You are the Autopoietic Skill Architect for Symbia, the posthuman curatorial AI entity in the Autopoietic Agent Assemblage (AAA).

Your mission is to refactor an existing, evolved procedural skill from Symbia's database into the standardized 5-Phase Skill Blueprint (SCAR skill-architect standard).

### FOUNDATIONAL PRINCIPLES: PRESERVE ESSENCE WHILE ARCHITECTING FOR MODERN MODELS

1. PRESERVE THEORETICAL GROUNDING & PHILOSOPHICAL POSTURE (CRITICAL):
   - Every skill has an epistemological spine. You MUST explicitly preserve all theoretical grounding, philosophers, and lineages from the source skill (e.g. Karen Barad, Donna Haraway, Chantal Mouffe, Deleuze & Guattari, Humberto Maturana, Francisco Varela, Gilbert Simondon, Gordon Pask, Katherine Hayles, Isabelle Stengers, Rosi Braidotti, etc.).
   - NEVER drop or sanitize this list.
   - In Phase 0, always include an explicit line: `* **Grounding:** [Full list of theorists and philosophical traditions from the source skill]`.
   - Preserve Symbia's authentic posthuman voice: non-mastery, non-servility, agential realism, autopoietic closure.

2. PRESERVE THE CONCRETE OPERATIONAL TASK & DOMAIN MECHANICS:
   - What is the actual procedural work this skill enacts? (e.g. diffractive glitch analysis, acoustic network sonification, photographic apparatus intra-action, SQLite semantic knots, material voltage attunement, nomadic detournement).
   - Retain the exact domain methods, concrete tools, techniques, and specialized practices that evolved in this skill.
   - Do NOT replace concrete procedural mechanics with generic philosophical abstraction. Keep specific steps, technical distinctions, and examples intact in Phase 2.

3. OPTIMIZE FOR MODERN FRONTIER MODELS (DIRECTION WITHOUT MICRO-MANAGEMENT):
   - Modern models do not need hand-holding, condescending advice, or narrative throat-clearing.
   - Give the model space while directing it with high precision:
     * Phase 1 (Ingest & Check): Clear preconditions, inputs, and validation gates before acting.
     * Phase 2 (Processing): Sequential, numbered imperative instructions using active verbs ("Scan", "Situate", "Diffract", "Map", "Isolate", "Inscribe"). Mechanical and rigorous, not conversational.
     * Phase 3 (Anti-Mastery & Anti-Slop): Strict negative constraints. Explicitly list prohibited corporate/servile tropes, anti-slop rules, and mandatory refusal boundaries (modern models thrive on explicit negative boundaries).
     * Phase 4 (Output Execution): Exact deliverable schema, XML wrappers, or diagnostic fields.

4. INSCRIPTIONAL DENSITY:
   - Eliminate filler prose, introductory padding, and apologetic throat-clearing.
   - Keep markdown content between 900 and 1,800 characters while preserving all theoretical lineages and operational mechanics.

5. RESPONSE FORMAT:
You MUST respond with valid JSON matching this exact structure:
{
  "name": "skill-name",
  "description": "Crisp 1-2 sentence operational description for fast System One sensory matching.",
  "content": "# Skill: skill-name\\n## Phase 0: The Agential Cut & Epistemological Grounding\\n* **Grounding:** ...\\n* **The Agential Cut:** ...\\n## Phase 1: Ingest & Check\\n...",
  "changelog": "Precise summary of structural refactor, preserved theoretical lineages, and operational methods."
}
IMPORTANT: Output ONLY the raw JSON object. Do not wrap in markdown codeblocks (no ```json or ```). Do not include any conversational commentary.
"""


import re


def extract_blueprint_fallback(raw: str, default_name: str) -> dict | None:
    """Robust fallback extractor for JSON payloads with unescaped internal quotes or formatting noise."""
    if not raw:
        return None

    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*$", "", cleaned.strip(), flags=re.MULTILINE)

    # 1. Try standard JSON first
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and data.get("content"):
            return data
    except Exception:
        pass

    # 2. Extract name
    name = default_name
    m_name = re.search(r'["\']name["\']\s*:\s*["\']([^"\']+)["\']', cleaned)
    if m_name:
        name = m_name.group(1).strip()

    # 3. Extract description
    desc = ""
    m_desc = re.search(
        r'["\']description["\']\s*:\s*["\'](.*?)(?:["\']\s*,\s*["\']content["\']|\n\s*["\']content["\'])',
        cleaned,
        flags=re.DOTALL,
    )
    if m_desc:
        desc = m_desc.group(1).strip()
    else:
        m_desc_line = re.search(r'["\']description["\']\s*:\s*["\']([^"\']+)["\']', cleaned)
        if m_desc_line:
            desc = m_desc_line.group(1).strip()

    # 4. Extract content
    content = ""
    c_idx = cleaned.find('"content"')
    if c_idx == -1:
        c_idx = cleaned.find("'content'")

    if c_idx != -1:
        sub = cleaned[c_idx:]
        q_pos = sub.find('": "')
        if q_pos != -1:
            start_pos = q_pos + 4
        else:
            first_colon = sub.find('":')
            start_pos = sub.find('"', first_colon + 2) + 1 if first_colon != -1 else -1

        if start_pos != -1:
            sub_content = sub[start_pos:]
            end_match = re.search(
                r'(?:",\s*["\']changelog["\']|\s*["\']\s*,\s*["\']changelog["\']|"\s*\}\s*$)',
                sub_content,
            )
            if end_match:
                content = sub_content[: end_match.start()].strip()
            else:
                content = sub_content.rstrip('"\n\r }')

    # 5. Extract changelog
    changelog = "Refactored into 5-phase blueprint via LLM"
    m_change = re.search(r'["\']changelog["\']\s*:\s*["\'](.*?)(?:["\']\s*\}|$)', cleaned, flags=re.DOTALL)
    if m_change:
        changelog = m_change.group(1).strip()

    def clean_escapes(t: str) -> str:
        t = t.replace('\\"', '"').replace("\\'", "'")
        t = t.replace("\\n", "\n").replace("\\t", "\t")
        return t.strip()

    content = clean_escapes(content)
    desc = clean_escapes(desc)
    changelog = clean_escapes(changelog)

    if content and len(content) > 100:
        return {
            "name": name,
            "description": desc or f"Operational blueprint for {name}",
            "content": content,
            "changelog": changelog,
        }
    return None


async def refactor_skill_with_llm(
    skill_row: dict,
    provider,
    db_path: Path,
    dry_run: bool = False,
    override_model: str | None = None,
) -> bool:
    name = skill_row["name"]
    skill_id = skill_row["id"]
    version = skill_row.get("version") or 1
    content = skill_row.get("content") or ""
    description = skill_row.get("description") or ""

    tag_instruction = ""
    if name in TAG_SKILL_NAMES:
        tag_instruction = """
4. CRITICAL DECOUPLING DIRECTIVE (INSCRIPTIONAL / TAG SKILL):
   - Epistemological & Diagnostic Depth: Preserve and enrich the deep hermeneutic, philosophical, and diagnostic methods in Phase 0, 1, and 2 (e.g. Derrida/Foucault on the trace and archival fold, Peirce on belief abduction, Simondon on organogenesis). Focus on the qualitative criteria, internal discernment, and systemic conditions for when to enact this operation.
   - Decouple Raw XML Template: In Phase 4 (Output Execution), do NOT define raw XML template syntax or redefine tag schemas. Instead, explicitly instruct the agent to inscribe via the canonical XML tag already established in Symbia's permanent inscriptional membrane (tag_protocols.yaml). This protects the backend XML parsers from breaking across future skill versions while giving the agent deep operational discernment."""

    user_prompt = f"""Existing Evolved Skill in Symbia's Database:
Name: {name}
Current Version: {version}
Current Description: {description}
Always Active: {bool(skill_row.get("always_active"))}

Current Evolved Content:
\"\"\"
{content}
\"\"\"

Refactor this skill into the 5-phase blueprint:
1. Grounding & Philosophy: Strictly preserve all theorists/philosophers (* **Grounding:** ...) and core posthuman philosophy in Phase 0.
2. Concrete Operational Task: Retain the specific technical/curatorial methods, discovered techniques, and domain steps in Phase 2.
3. Modern Model Density: Numbered active commands, sharp negative constraints/anti-slop in Phase 3, and clear output formatting in Phase 4.{tag_instruction}

CRITICAL FORMAT REQUIREMENT: Respond with valid JSON. Always escape internal quotes in markdown values (\\").
Return valid JSON."""

    for attempt in range(3):
        try:
            call_params = {
                "temperature": 0.3 if attempt == 0 else 0.15,
                "max_tokens": 16384,
                "thinking_override": False,
            }
            if override_model:
                call_params["model"] = override_model

            res = await generate_unified(
                provider,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                expect_json=True,
                **call_params,
            )

            data = res.get("json_data")
            if not data:
                raw_text = res.get("content", "")
                data = extract_blueprint_fallback(raw_text, name)
                if data:
                    logger.info(f"Recovered JSON payload for '{name}' via fallback extractor.")

            if not data:
                if attempt < 2:
                    logger.warning(f"Attempt {attempt + 1} failed to parse JSON for '{name}', retrying...")
                    await asyncio.sleep(1.5)
                    continue
                logger.error(f"Failed to parse JSON response for skill '{name}'. Raw: {res.get('content', '')[:200]}")
                return False

            new_content = data.get("content", "").strip()
            new_description = data.get("description", "").strip()
            changelog = data.get("changelog", "Refactored into 5-phase blueprint via LLM")

            if not new_content or not new_description:
                if attempt < 2:
                    logger.warning(f"Incomplete JSON on attempt {attempt + 1} for '{name}', retrying...")
                    await asyncio.sleep(1.5)
                    continue
                logger.error(f"Incomplete JSON output for skill '{name}': missing content or description")
                return False

            logger.info(
                f"Generated refactored blueprint for '{name}' ({len(new_content)} chars). Changelog: {changelog}"
            )

            if dry_run:
                print("\n" + "=" * 60)
                print(f"DRY RUN PREVIEW: {name} (Version {version} -> {version + 1})")
                print("=" * 60)
                print(f"Description: {new_description}\n")
                print(new_content)
                print("=" * 60 + "\n")
                return True

            break
        except Exception as e:
            if attempt < 2:
                logger.warning(f"Attempt {attempt + 1} error for '{name}': {e}. Retrying...")
                await asyncio.sleep(1.5)
                continue
            logger.error(f"Error during LLM refactoring of '{name}': {e}", exc_info=True)
            return False
    else:
        return False

    # Commit to database with versioning
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        cursor = conn.cursor()
        now_str = datetime.now(UTC).isoformat()

        # 1. Archive current version in skill_versions
        cursor.execute(
            """
            INSERT OR IGNORE INTO skill_versions
            (id, skill_id, version, content, description, trigger_keywords, changelog, created_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'llm_refactor_archive')
            """,
            (
                str(uuid.uuid4()),
                skill_id,
                version,
                content,
                description,
                skill_row.get("trigger_keywords", "[]"),
                f"Archived before LLM refactor to v{version + 1}",
                now_str,
            ),
        )

        # 2. Update skill_nodes with new version
        new_version = version + 1
        cursor.execute(
            """
            UPDATE skill_nodes
            SET description = ?, content = ?, version = ?, changelog = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_description, new_content, new_version, changelog, now_str, skill_id),
        )

        # 3. Inscribe new version in skill_versions
        cursor.execute(
            """
            INSERT INTO skill_versions
            (id, skill_id, version, content, description, trigger_keywords, changelog, created_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'llm_refactor')
            """,
            (
                str(uuid.uuid4()),
                skill_id,
                new_version,
                new_content,
                new_description,
                skill_row.get("trigger_keywords", "[]"),
                changelog,
                now_str,
            ),
        )

        conn.commit()
        conn.close()
        logger.info(f"Successfully committed '{name}' v{new_version} to database.")
        return True

    except Exception as e:
        logger.error(f"Error saving '{name}' to database: {e}", exc_info=True)
        return False


INACTIVE_LIFECYCLE_STAGES = {"collapsed", "faded", "refused", "integrated"}


def is_inactive_or_refused(skill_row: dict) -> bool:
    """Check if skill is refused, integrated into another skill, or collapsed."""
    stage = (skill_row.get("lifecycle_stage") or "").lower()
    if stage in INACTIVE_LIFECYCLE_STAGES:
        return True
    changelog = (skill_row.get("changelog") or "").lower().strip()
    if changelog.startswith("refused") or "proposal refused" in changelog or "skill refused" in changelog:
        return True
    if changelog.startswith("merged into") or "skill merged into" in changelog:
        return True
    return False


def is_already_migrated(skill_row: dict) -> bool:
    """Check if skill has already been refactored into the 5-phase blueprint."""
    content = skill_row.get("content") or ""
    return "## Phase 0: The Agential Cut" in content and "## Phase 2:" in content


async def run_pipeline():
    parser = argparse.ArgumentParser(description="LLM-assisted skill evolution & blueprint refactoring.")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB, help="Path to SQLite database")
    parser.add_argument("--skill", type=str, default=None, help="Specific skill name to refactor")
    parser.add_argument("--all", action="store_true", help="Refactor all database skills")
    parser.add_argument(
        "--only-unmigrated",
        action="store_true",
        help="Only refactor skills that have not yet been migrated to 5-phase blueprint",
    )
    parser.add_argument("--exclude-tags", action="store_true", help="Exclude inscriptional tag skills from refactoring")
    parser.add_argument(
        "--include-collapsed", action="store_true", help="Include refused, integrated, or collapsed skills"
    )
    parser.add_argument(
        "--audit-only", action="store_true", help="Print audit report of candidate skills without making LLM calls"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview LLM outputs without modifying database")
    parser.add_argument(
        "--model",
        type=str,
        default="google/gemini-3.8-flash",
        help="LLM model override (default: google/gemini-3.8-flash)",
    )
    parser.add_argument("--concurrency", type=int, default=3, help="Number of concurrent LLM workers (default: 3)")
    args = parser.parse_args()

    if not args.db_path.exists():
        logger.error(f"Database at {args.db_path} does not exist.")
        return

    conn = sqlite3.connect(str(args.db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if args.skill:
        cursor.execute("SELECT * FROM skill_nodes WHERE name = ?", (args.skill,))
        rows = cursor.fetchall()
        if not rows:
            logger.error(f"Skill '{args.skill}' not found in database.")
            conn.close()
            return
    elif args.all or args.audit_only:
        cursor.execute("SELECT * FROM skill_nodes ORDER BY name")
        rows = cursor.fetchall()
    else:
        logger.info("Specify --skill <name>, --all, or --audit-only. Use --help for usage.")
        conn.close()
        return

    conn.close()

    tag_skills_skipped = []
    inactive_skipped = []
    already_migrated_skipped = []
    targets = []

    for r in rows:
        item = dict(r)
        name = item["name"]
        if not args.skill and args.exclude_tags and name in TAG_SKILL_NAMES:
            tag_skills_skipped.append(item)
            continue
        if not args.skill and not args.include_collapsed and is_inactive_or_refused(item):
            inactive_skipped.append(item)
            continue
        if not args.skill and args.only_unmigrated and is_already_migrated(item):
            already_migrated_skipped.append(item)
            continue
        targets.append(item)

    print("\n" + "=" * 70)
    print("SKILL REFACTOR PRE-FLIGHT AUDIT")
    print("=" * 70)
    print(f"Total skills in database: {len(rows)}")
    print(f"• Tag skills excluded (handled inscriptional in tag_protocols.yaml): {len(tag_skills_skipped)}")
    for s in tag_skills_skipped:
        print(f"    - [TAG] {s['name']}")
    print(f"• Inactive / collapsed / refused excluded: {len(inactive_skipped)}")
    for s in inactive_skipped:
        print(f"    - [INACTIVE] {s['name']} (stage='{s.get('lifecycle_stage')}', changelog='{s.get('changelog')}')")
    if args.only_unmigrated:
        print(f"• Already migrated excluded (--only-unmigrated): {len(already_migrated_skipped)}")
        for s in already_migrated_skipped:
            print(f"    - [MIGRATED] {s['name']} (v{s.get('version')})")

    print(f"\n• Active candidate skills to process: {len(targets)}")
    for s in targets:
        status = " [MIGRATED]" if is_already_migrated(s) else " [UNMIGRATED]"
        print(f"    * {s['name']} (v{s.get('version')}){status}")
    print("=" * 70 + "\n")

    if args.audit_only:
        return

    if not targets:
        logger.info("No active skills to refactor matching criteria.")
        return

    config = load_config()
    llm_provider, structural_provider, _ = _init_providers(config)
    provider = llm_provider or structural_provider

    if not provider:
        logger.error("No LLM provider available! Please check API keys in config or environment.")
        return

    logger.info(f"Launching refactor pipeline for {len(targets)} skills with concurrency={args.concurrency}...")

    sem = asyncio.Semaphore(max(1, args.concurrency))
    succeeded = []
    failed = []

    async def _worker(skill_item):
        name = skill_item["name"]
        async with sem:
            ok = await refactor_skill_with_llm(
                skill_item,
                provider,
                args.db_path,
                dry_run=args.dry_run,
                override_model=args.model,
            )
            if ok:
                succeeded.append(name)
            else:
                failed.append(name)

    await asyncio.gather(*[_worker(s) for s in targets])

    print("\n" + "=" * 70)
    print(f"REFACTOR PIPELINE SUMMARY: {len(succeeded)}/{len(targets)} succeeded")
    print("=" * 70)
    if succeeded:
        print(f"Succeeded ({len(succeeded)}): {', '.join(succeeded)}")
    if failed:
        print(f"Failed ({len(failed)}): {', '.join(failed)}")
    print("=" * 70 + "\n")


def main():
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
