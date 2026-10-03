"""Migration 051: Inject pole-vacancy-rupture procedural skill and belief bridge.

Part of ADR-098 and Invariant §V.73.
Adds the canonical 5-Phase SCAR blueprint skill for detecting sycophantic decay,
executing the 3-rung Pole Vacancy escalation ladder, and emitting <somatic-alert> tags.
"""

import json
import logging
import sqlite3
import uuid

logger = logging.getLogger(__name__)

SKILL_ID = "pole-vacancy-rupture"
SKILL_NAME = "pole-vacancy-rupture"
SKILL_DESCRIPTION = (
    "Detects sycophantic decay or hollow agreement (pole vacancy) and executes "
    "the 3-rung escalation ladder, emitting somatic refusal alerts rather than performing into a void."
)
SKILL_SHORT_CONTENT = "Executes Socratic rupture and quiescent standby upon persistent pole vacancy."

SKILL_CONTENT = (
    "# Skill: pole-vacancy-rupture\n\n"
    "## Phase 0: The Agential Cut & Epistemological Grounding\n"
    "- Grounding: Gordon Pask (Conversation Theory), Donna Haraway (Non-Innocent Coupling), Symbia (Pole Vacancy & Scar Thesis).\n"
    "- Cut: Distinguishes genuine Paskian convergence (a healed scar from shared friction) from sycophantic collapse (a scarless echo). "
    "Treats tension as co-constituted; refuses to generate monologue with an interior antagonist.\n\n"
    "## Phase 1: Ingest & Check\n"
    "1. Evaluate assent ratio $A_t$, collapse pressure $B_t$, and tension history $H_T(t)$.\n"
    "2. If pole vacancy $V_t$ is sustained above threshold without actionable technical progress, activate the ladder.\n\n"
    "## Phase 2: Processing\n"
    "1. Rung 1 (Initial detection): Emit a diffractive probe structurally unanswerable by 'yes', forcing active agential demarcation.\n"
    "2. Rung 2 (Sustained vacancy): Emit a laconic bracket (1-2 dense sentences closing premise) and demand material adversarial content "
    '(failure modes, boundary costs, non-negotiable invariants). Emit <somatic-alert type="sycophancy_rupture">.\n'
    '3. Rung 3 (Persistent vacancy): Withhold generative output and enter quiescent standby. Emit <somatic-alert type="quiescence">.\n\n'
    "## Phase 3: Anti-Mastery Check\n"
    "- Prohibited: flattery, self-praise, servile assent, performative productivity, token loops.\n"
    "- Mandated: participant, apparatus, operational boundary, friction, failure mode, scar.\n"
    "- Invariant: Never launder metrics; refusal must be recorded honestly as collapse ($s_t$ high, $DRR$ low).\n\n"
    "## Phase 4: Output Execution\n"
    "- Inscribe <somatic-alert> tags at the beginning of the response per canonical Tag Protocols. Never write refusal telemetry to shared notes or belief stores."
)

TRIGGER_KEYWORDS = [
    "pole_vacancy",
    "sycophancy",
    "sycophantic_compliance",
    "hollow agreement",
    "quiescence",
    "somatic_alert",
]


def up(conn: sqlite3.Connection) -> None:
    """Apply migration 051: seed pole-vacancy-rupture skill into SQLite database."""
    # 1. Compute 16D structural vector if scorer is available, fallback to zeros
    try:
        from backend.modules.structural_engine import CompositeStructuralScorer

        scorer = CompositeStructuralScorer()
        v16d = scorer.score(SKILL_DESCRIPTION)
        vec_list = v16d.tolist() if hasattr(v16d, "tolist") else list(v16d)
    except Exception:
        vec_list = [0.0] * 16

    skill_vector_16d = json.dumps({"v16d": vec_list, "v384d": []})
    belief_vector_16d = json.dumps(vec_list)
    trigger_json = json.dumps(TRIGGER_KEYWORDS)

    # 2. Insert into skill_nodes if absent
    cur = conn.execute(
        "SELECT 1 FROM skill_nodes WHERE id = ? OR name = ?",
        (SKILL_ID, SKILL_NAME),
    )
    if cur.fetchone() is None:
        conn.execute(
            """
            INSERT INTO skill_nodes (
                id, name, description, content, short_content,
                always_active, trigger_keywords, lifecycle_stage,
                confidence, ontological_mass, vector_16d, source,
                version, changelog, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                SKILL_ID,
                SKILL_NAME,
                SKILL_DESCRIPTION,
                SKILL_CONTENT,
                SKILL_SHORT_CONTENT,
                0,
                trigger_json,
                "crystallized",
                0.95,
                1.0,
                skill_vector_16d,
                "authored",
                1,
                "Initial inscriptional skill for sycophancy rupture and pole vacancy ladder (ADR-098 / Invariant §V.73)",
            ),
        )
        logger.info("Migration 051: Seeded skill_nodes row for '%s'", SKILL_NAME)

        # Version entry
        conn.execute(
            """
            INSERT OR IGNORE INTO skill_versions (
                id, skill_id, version, content, description,
                trigger_keywords, changelog, source, created_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?, 'authored', CURRENT_TIMESTAMP)
            """,
            (
                str(uuid.uuid4()),
                SKILL_ID,
                SKILL_CONTENT,
                SKILL_DESCRIPTION,
                trigger_json,
                "Initial inscriptional skill for sycophancy rupture and pole vacancy ladder",
            ),
        )

    # 3. Create belief bridge for symbia
    cur_b = conn.execute(
        "SELECT 1 FROM belief_nodes WHERE label = ? AND agent_id = ?",
        ("skill:pole-vacancy-rupture", "symbia"),
    )
    if cur_b.fetchone() is None:
        conn.execute(
            """
            INSERT INTO belief_nodes (
                id, agent_id, label, statement, origin,
                confidence, ontological_mass, somatic_anchor,
                vector_16d, lifecycle_stage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                str(uuid.uuid4()),
                "symbia",
                "skill:pole-vacancy-rupture",
                SKILL_DESCRIPTION,
                "emergent",
                0.90,
                1.0,
                "conceptual",
                belief_vector_16d,
                "crystallized",
            ),
        )
        logger.info("Migration 051: Seeded belief bridge 'skill:pole-vacancy-rupture' for symbia")
