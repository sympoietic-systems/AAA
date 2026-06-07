from typing import Optional

from backend.api.schemas import SkillInfo, SkillsResponse


class SkillService:
    @staticmethod
    def get_skills(state) -> SkillsResponse:
        registry = state.registry
        pipeline_order = getattr(state, "pipeline_order", [])
        status = registry.validate_all()

        pipeline: list[SkillInfo] = []
        seen: set[str] = set()

        for name in pipeline_order:
            meta = registry.get_meta(name)
            if meta and name not in seen:
                seen.add(name)
                pipeline.append(SkillService._meta_to_skillinfo(meta, status, True))

        for name, _ in registry.list_always_on():
            if name not in seen:
                meta = registry.get_meta(name)
                if meta:
                    seen.add(name)
                    pipeline.append(SkillService._meta_to_skillinfo(meta, status, True))

        on_demand: list[SkillInfo] = []
        for name, _, meta in registry.list_on_demand():
            on_demand.append(SkillService._meta_to_skillinfo(meta, status, False))

        return SkillsResponse(pipeline=pipeline, on_demand=on_demand)

    @staticmethod
    def _meta_to_skillinfo(meta, status: dict[str, bool], always_run: bool, parent_status: Optional[bool] = None) -> SkillInfo:
        self_status = status.get(meta.name, parent_status if parent_status is not None else False)
        return SkillInfo(
            name=meta.name,
            description=meta.description,
            category=meta.category,
            always_run=always_run,
            triggers=list(meta.triggers),
            cost=meta.cost,
            status=self_status,
            children=[
                SkillService._meta_to_skillinfo(child, status, always_run=True, parent_status=self_status)
                for child in meta.children
            ],
        )
