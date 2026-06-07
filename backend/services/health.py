class HealthService:
    @staticmethod
    def check(state) -> dict:
        registry = state.registry
        modules_status = registry.validate_all()
        return {
            "status": "ok",
            "modules": modules_status,
        }
