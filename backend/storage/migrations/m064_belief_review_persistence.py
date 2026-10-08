"""Add v2 identity/decision sidecars; assessment payloads remain in the admission ledger."""

import sqlite3


def up(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(belief_admission)")}
    for column in ("agent_id", "encounter_id", "assessment_id"):
        if column not in columns:
            conn.execute(f"ALTER TABLE belief_admission ADD COLUMN {column} TEXT")
    schema = """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_v2_identity
            ON belief_admission(agent_id,assessment_id) WHERE assessment_id IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_admission_v2_pending
            ON belief_admission(agent_id,encounter_id) WHERE assessment_id IS NOT NULL AND status='assessing';
        CREATE TABLE IF NOT EXISTS belief_review_claims (
            agent_id TEXT NOT NULL, id TEXT NOT NULL, claim_key TEXT, record_id TEXT NOT NULL,
            PRIMARY KEY(agent_id,id), UNIQUE(agent_id,claim_key), UNIQUE(agent_id,record_id)
        );
        CREATE TABLE IF NOT EXISTS belief_encounters (
            agent_id TEXT NOT NULL, id TEXT NOT NULL, event_key TEXT, request_hash TEXT NOT NULL,
            claim_id TEXT NOT NULL, received_at TEXT NOT NULL, encounter_json TEXT NOT NULL,
            source_type TEXT NOT NULL, source_id TEXT, source_hash TEXT, context_available INTEGER NOT NULL CHECK(context_available IN (0,1)),
            redaction_policy TEXT NOT NULL DEFAULT 'reject-secrets-v1',
            PRIMARY KEY(agent_id,id), UNIQUE(agent_id,event_key),
            FOREIGN KEY(agent_id,claim_id) REFERENCES belief_review_claims(agent_id,id)
        );
        CREATE INDEX IF NOT EXISTS idx_encounter_agent_claim ON belief_encounters(agent_id,claim_id,id);
        CREATE TABLE IF NOT EXISTS belief_review_assessments (
            agent_id TEXT NOT NULL, id TEXT NOT NULL, encounter_id TEXT NOT NULL, ledger_id TEXT UNIQUE NOT NULL,
            previous_id TEXT, candidate_hash TEXT NOT NULL, input_hash TEXT NOT NULL,
            redaction_policy TEXT NOT NULL DEFAULT 'reject-secrets-v1',
            PRIMARY KEY(agent_id,id),
            FOREIGN KEY(agent_id,encounter_id) REFERENCES belief_encounters(agent_id,id),
            FOREIGN KEY(agent_id,previous_id) REFERENCES belief_review_assessments(agent_id,id),
            FOREIGN KEY(ledger_id) REFERENCES belief_admission(id)
        );
        CREATE INDEX IF NOT EXISTS idx_assessment_encounter ON belief_review_assessments(agent_id,encounter_id,id);
        CREATE TABLE IF NOT EXISTS belief_review_decisions (
            agent_id TEXT NOT NULL, id TEXT NOT NULL, record_id TEXT NOT NULL, version INTEGER NOT NULL,
            decision_json TEXT NOT NULL, timestamp TEXT NOT NULL,
            PRIMARY KEY(agent_id,id), UNIQUE(agent_id,record_id,version)
        );
        CREATE TABLE IF NOT EXISTS belief_review_state (
            agent_id TEXT NOT NULL, record_id TEXT NOT NULL, statement_hash TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('candidate','awaiting_context','under_review','adopted','deferred','declined','superseded')),
            version INTEGER NOT NULL CHECK(version>=0), scope TEXT NOT NULL, decision_id TEXT,
            PRIMARY KEY(agent_id,record_id),
            FOREIGN KEY(agent_id,decision_id) REFERENCES belief_review_decisions(agent_id,id)
        );
        CREATE INDEX IF NOT EXISTS idx_review_state_agent ON belief_review_state(agent_id,state,record_id);
        CREATE TRIGGER IF NOT EXISTS immutable_v2_admission_update BEFORE UPDATE ON belief_admission
            WHEN OLD.assessment_id IS NOT NULL AND OLD.status='complete'
            BEGIN SELECT RAISE(ABORT,'completed assessment immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_v2_admission_delete BEFORE DELETE ON belief_admission
            WHEN OLD.assessment_id IS NOT NULL
            BEGIN SELECT RAISE(ABORT,'assessment history retained'); END;
    """
    statement = ""
    for line in schema.splitlines():
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""
    for table in ("belief_encounters", "belief_review_claims", "belief_review_assessments", "belief_review_decisions"):
        for operation in ("UPDATE", "DELETE"):
            conn.execute(
                f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation.lower()} BEFORE {operation} ON {table} "
                "BEGIN SELECT RAISE(ABORT,'belief review history immutable'); END"
            )
