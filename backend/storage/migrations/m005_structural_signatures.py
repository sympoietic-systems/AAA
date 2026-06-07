import sqlite3


def up(conn):
    for sql in [
        "ALTER TABLE conversation_log ADD COLUMN structural_signature BLOB",
        "ALTER TABLE conversation_log ADD COLUMN structural_justification TEXT",
        "ALTER TABLE perception_sediment ADD COLUMN structural_signature BLOB",
    ]:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
