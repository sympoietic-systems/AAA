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
