import contextlib
import sqlite3


def up(conn):
    for sql in [
        "ALTER TABLE conversation_log ADD COLUMN structural_signature BLOB",
        "ALTER TABLE conversation_log ADD COLUMN structural_justification TEXT",
        "ALTER TABLE perception_sediment ADD COLUMN structural_signature BLOB",
    ]:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute(sql)
