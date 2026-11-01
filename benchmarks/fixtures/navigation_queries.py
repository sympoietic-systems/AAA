"""Synthetic, deterministic large-content fixtures; no production records."""

import sqlite3
from types import SimpleNamespace

from backend.services.skill import SkillService
from backend.storage.migrations import run_all_migrations
from backend.storage.models import SkillNode
from backend.storage.repositories.conversation.message import MessageRepository


def skills():
    nodes = [
        SkillNode(
            id=str(i),
            name=f"skill-{i}",
            description="Summary " * 20,
            content="Full skill instructions.\n" * 120,
            short_content="Short " * 30,
            always_active=i % 2 == 0,
            lifecycle_stage="crystallized",
        )
        for i in range(89)
    ]
    repo = SimpleNamespace(
        list_always_active=lambda: nodes[::2], list_on_demand=lambda: nodes[1::2], list_skills=lambda: nodes
    )
    return SkillService(SimpleNamespace(skill_repo=repo))


def history(path, rich=False):
    conn = sqlite3.connect(path)
    run_all_migrations(conn)
    conn.close()
    repo = MessageRepository(str(path))
    ids = []
    for i in range(50):
        message = repo.insert(
            speaker="apparatus",
            content=f"Message {i}: " + "visible " * 100,
            thinking="reasoning " * 2000,
            context_sent="context " * 3000,
            embedding=b"",
            embedding_model="",
            embedding_dim=0,
            conversation_id="fixture",
            parent_message_id=ids[-1] if rich and ids else None,
            active_skills=["fixture"],
            active_beliefs=["fixture-belief"],
        )
        ids.append(message.id)
    if rich:
        with sqlite3.connect(path) as conn:
            for i, message_id in enumerate(ids):
                if i % 3 != 0:
                    conn.execute(
                        "UPDATE conversation_log SET context_sent = ? WHERE id = ?",
                        (None if i % 3 == 1 else "", message_id),
                    )
                conn.execute(
                    "UPDATE conversation_log SET quality_status = ?, quality_receipt = ? WHERE id = ?",
                    ("accepted", '{"fixture": true}', message_id),
                )
                conn.execute(
                    "INSERT INTO conversation_metrics(message_id, s_t, novelty, deficit) VALUES (?, .5, .2, .1)",
                    (message_id,),
                )
    return repo
