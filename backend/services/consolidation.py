import asyncio
import logging

logger = logging.getLogger(__name__)


class ConsolidationService:
    @staticmethod
    def fire_and_forget(engine, message_repo, checkpoint_repo, conversation_id: str, msg_count: int) -> None:
        async def _do_consolidate():
            try:
                rows = message_repo.get_recent_with_metrics(limit=msg_count + 10, conversation_id=conversation_id)
                if not rows:
                    return
                lines = []
                for r in rows:
                    speaker = r.get("speaker", "unknown")
                    content = r.get("content", "")[:500]
                    label = "Human" if speaker == "human" else "Agent"
                    lines.append(f"{label}: {content}")
                text = "\n".join(lines)

                result = await engine.run(
                    "consolidate",
                    {
                        "text": text,
                        "context": {
                            "messages": [
                                {"speaker": r.get("speaker", "unknown"), "content": r.get("content", "")} for r in rows
                            ]
                        },
                    },
                )

                summary = result.get("content", "").strip()
                if summary and checkpoint_repo:
                    model_used = result.get("model", "")
                    checkpoint_repo.save(conversation_id, msg_count, summary, model_used)
                    logger.info("Consolidation checkpoint saved for %s (%d msgs)", conversation_id, msg_count)
            except Exception:
                logger.exception("Background consolidation failed")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_do_consolidate())
        except RuntimeError:
            pass
