class DaemonService:
    @staticmethod
    def get_status(state) -> dict | None:
        daemon = getattr(state, "dream_daemon", None)
        if not daemon:
            return None
        return daemon.get_status()

    @staticmethod
    async def trigger(state) -> dict | None:
        daemon = getattr(state, "dream_daemon", None)
        if not daemon:
            return None
        result = await daemon.check_and_trigger_dream(force=True)
        if result is None:
            return {"status": "skipped", "reason": "No active conversation or compilation error"}
        return {"status": "success", "dream": result}

    @staticmethod
    def get_recent_dreams(state, hours: int = 48) -> list[dict]:
        daemon = getattr(state, "dream_daemon", None)
        if not daemon:
            return []
        if hasattr(daemon, "conversation_repo"):
            return daemon.conversation_repo.get_recent_dreams(hours)
        return []
