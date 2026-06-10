import sqlite3
import logging

logger = logging.getLogger(__name__)


def up(conn: sqlite3.Connection):
    try:
        # Fetch all messages ordered by conversation and ID ascending
        rows = conn.execute(
            "SELECT id, conversation_id, parent_message_id FROM conversation_log ORDER BY conversation_id, id ASC"
        ).fetchall()

        # Group by conversation_id in memory
        conversations = {}
        for r in rows:
            c_id = r[1]
            if c_id not in conversations:
                conversations[c_id] = []
            conversations[c_id].append(r)

        updates = []
        for c_id, msgs in conversations.items():
            for i in range(1, len(msgs)):
                current = msgs[i]
                # If current message has no parent_message_id, link it to the previous message's ID
                if current[2] is None:
                    parent_id = msgs[i - 1][0]
                    updates.append((parent_id, current[0]))

        if updates:
            conn.executemany(
                "UPDATE conversation_log SET parent_message_id = ? WHERE id = ?",
                updates
            )
            logger.info("Backfilled parent_message_id for %d legacy messages.", len(updates))
    except Exception as e:
        logger.exception("Failed to backfill parent_message_ids: %s", e)
        # We don't want to crash the runner if a query fails, but we log the exception
