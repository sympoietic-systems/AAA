import sqlite3


def up(conn):
    for sql in [
        "ALTER TABLE conversation_log ADD COLUMN thinking TEXT",
        "ALTER TABLE conversation_log ADD COLUMN context_sent TEXT",
        "ALTER TABLE conversation_log ADD COLUMN agent_id TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE conversation_log ADD COLUMN conversation_id TEXT NOT NULL DEFAULT ''",
        "CREATE INDEX IF NOT EXISTS idx_conversation_log_conv_id ON conversation_log(conversation_id)",
        "ALTER TABLE conversation_log ADD COLUMN content_tokens INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE conversation_log ADD COLUMN thinking_tokens INTEGER",
        "ALTER TABLE conversation_log ADD COLUMN model_used TEXT",
        "ALTER TABLE conversation_log ADD COLUMN provider_used TEXT",
        "ALTER TABLE conversation_log ADD COLUMN note_count INTEGER DEFAULT 0",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
