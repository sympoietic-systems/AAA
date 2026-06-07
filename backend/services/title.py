import logging

logger = logging.getLogger(__name__)


class TitleService:
    @staticmethod
    async def generate(engine, first_message: str) -> str:
        try:
            result = await engine.run("generate_title", {"text": first_message[:300]})
            content = result.get("content", "").strip().strip('"').strip("'")
            if not content:
                return first_message[:60]
            return content
        except Exception:
            logger.debug("Title generation failed, using fallback", exc_info=True)
            return first_message[:60]

    @staticmethod
    async def generate_from_conversation(engine, message_repo, conversation_id: str) -> str:
        try:
            rows = message_repo.get_recent_with_metrics(limit=20, conversation_id=conversation_id)
            if not rows:
                return "Untitled"
            lines = []
            for r in rows:
                speaker = r.get("speaker", "unknown")
                content = r.get("content", "")[:300]
                if speaker == "human":
                    lines.append(f"Human: {content}")
                else:
                    lines.append(f"Agent: {content}")
            context = "\n".join(lines)

            result = await engine.run("generate_title", {
                "context": {"first_message": rows[0].get("content", "")[:300]},
                "text": context[:2000],
            })
            content = result.get("content", "").strip().strip('"').strip("'")
            if not content:
                return rows[0].get("content", "")[:60]
            return content
        except Exception:
            logger.debug("Conversation title generation failed", exc_info=True)
            return "Untitled"
