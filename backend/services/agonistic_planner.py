"""Agonistic Planner — dynamic query generation with stagnation modulation.

Generates structured research sub-queries. Behavior shifts based on Symbia's
Agonistic Index: normal mode produces supporting/contextual queries; agonistic
mode forces counter-positional evidence collection.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 11.
"""

import json

from backend.utils.anti_mastery import apply_anti_mastery_filter
import logging
from typing import Any

from backend.utils.prompt_loader import get_prompt, get_prompts_dict

logger = logging.getLogger("aaa.agonistic_planner")


class AgonisticPlanner:
    """Generates research sub-queries from objectives with stagnation modulation."""

    def __init__(self, llm_provider: Any, app_state: Any):
        self._llm = llm_provider
        self._state = app_state

    @property
    def config(self) -> dict:
        return self._state.config.get("rhizome_research", {})

    async def generate_queries(
        self,
        objective: str,
        stagnation_index: float = 0.0,
        active_beliefs: list[dict] | None = None,
        depth: int = 1,
        max_depth: int = 3,
        breadth: int = 3,
        conversation_summary: str = "",
    ) -> list[dict[str, str]]:
        """Generate sub-queries from a research objective.

        Args:
            objective: The research objective / question
            stagnation_index: Agonistic Index (0-1); >= 0.7 triggers agonistic mode
            active_beliefs: List of belief dicts with 'label'/'statement'
            depth: Current recursion depth
            max_depth: Maximum depth
            breadth: Current breadth boundary
            conversation_summary: Context from the active conversation

        Returns:
            List of {'query': str, 'goal': str} dicts
        """
        prompt_data = get_prompts_dict("research/planner.yaml")

        is_agonistic = stagnation_index >= self.config.get("agonistic_stagnation_threshold", 0.7)
        num_queries = 3 if is_agonistic else max(2, breadth)

        system_text = prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)

        if is_agonistic:
            belief_labels = [
                b.get("label", b.get("statement", ""))
                for b in (active_beliefs or [])[:5]
            ]
            user_text = (prompt_data.get("user_agonistic", "")).format(
                objective=objective,
                stagnation_index=stagnation_index,
                num_queries=num_queries,
                active_beliefs=json.dumps(belief_labels, indent=2),
                depth=depth,
                max_depth=max_depth,
                breadth=breadth,
                conversation_summary=conversation_summary or "(none)",
            )
        else:
            user_text = (prompt_data.get("user_standard", "")).format(
                objective=objective,
                num_queries=num_queries,
                depth=depth,
                max_depth=max_depth,
                breadth=breadth,
                conversation_summary=conversation_summary or "(none)",
            )

        if prompt_data.get("anti_mastery"):
            user_text = apply_anti_mastery_filter(user_text)

        temperature = prompt_data.get("temperature", 0.7)
        max_tokens = prompt_data.get("max_tokens", 1024)

        try:
            from backend.modules.llm_client import generate_unified
            response = await generate_unified(
                provider=self._llm,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value=[{"query": objective, "goal": "Investigate the core objective"}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            result = response.get("json_data") or response.get("content")
            if isinstance(result, str):
                result = json.loads(result)
            if isinstance(result, list):
                return result
            return [{"query": objective, "goal": "Investigate the core objective"}]
        except (json.JSONDecodeError, Exception) as e:
            logger.error("Agonistic planner failed: %s", e)
            return [{"query": objective, "goal": "Investigate the core objective"}]

    async def generate_search_queries(
        self,
        objective: str,
        stagnation_index: float = 0.0,
        active_beliefs: list[dict] | None = None,
        context: str = "",
        num_queries: int = 3,
    ) -> list[str]:
        """Generate raw search-engine queries (strings, not structured dicts)."""
        prompt_data = get_prompts_dict("research/planner_query_gen.yaml")

        is_agonistic = stagnation_index >= self.config.get("agonistic_stagnation_threshold", 0.7)

        system_text = prompt_data.get("system", "")
        if prompt_data.get("anti_mastery"):
            system_text = apply_anti_mastery_filter(system_text)

        if is_agonistic:
            belief_labels = json.dumps([
                b.get("label", b.get("statement", ""))
                for b in (active_beliefs or [])[:5]
            ])
            user_text = (prompt_data.get("user_agonistic", "")).format(
                objective=objective,
                context=context,
                num_queries=num_queries,
                active_beliefs=belief_labels,
            )
        else:
            user_text = (prompt_data.get("user_standard", "")).format(
                objective=objective,
                context=context,
                num_queries=num_queries,
            )

        if prompt_data.get("anti_mastery"):
            user_text = apply_anti_mastery_filter(user_text)

        try:
            from backend.modules.llm_client import generate_unified
            response = await generate_unified(
                provider=self._llm,
                system_prompt=system_text,
                user_prompt=user_text,
                expect_json=True,
                fallback_value=[],
                temperature=prompt_data.get("temperature", 0.4),
                max_tokens=prompt_data.get("max_tokens", 1024),
            )
            result = response.get("json_data") or response.get("content")
            if isinstance(result, str):
                result = json.loads(result)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, Exception) as e:
            logger.error("Query generation failed: %s", e)
            return [objective]
