import hashlib
import json
import logging

from backend.modules.llm_client import generate_unified
from backend.utils.prompt_loader import get_prompt, get_prompts_dict

logger = logging.getLogger(__name__)

_DREAM_PROMPTS_PATH = "dreams/prompt_generator.yaml"


class DreamPromptMixin:
    """Handles dream prompt generation, system/user prompt construction, and fallback prompts."""

    async def _generate_dream_prompt(self, action: str, context: dict) -> str:
        bg_engine = getattr(self.app_state, "background_engine", None)
        provider = bg_engine.provider if bg_engine else getattr(self.app_state, "llm_provider", None)

        # Build the meta-prompt to instruct the background LLM
        system_prompt = self._build_prompt_generator_system(action, context)
        user_prompt = self._build_prompt_generator_user(action, context)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                if provider:
                    res = await generate_unified(
                        provider, system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.8
                    )
                    generated = res.get("content", "").strip()
                else:
                    generated = ""
            except Exception as e:
                logger.warning("LLM prompt generation failed (attempt %d/%d): %s", attempt + 1, max_retries, e)
                generated = ""

            if generated:
                prompt_hash = hashlib.sha256(generated.encode()).hexdigest()
                if prompt_hash in self._recent_prompt_hashes and attempt < max_retries - 1:
                    logger.info("Prompt hash collision on attempt %d, regenerating...", attempt + 1)
                    user_prompt += f"\n\n(The previous prompt was too similar to recent ones. Please generate something DIFFERENT. Attempt {attempt + 2}/{max_retries})"
                    continue

                self._recent_prompt_hashes.append(prompt_hash)
                logger.info("Generated unique dream prompt (%d chars) via LLM for action '%s'", len(generated), action)
                return generated

        logger.warning("All LLM prompt generation attempts failed. Using fallback.")
        return self._build_fallback_prompt(action, context)

    def _build_prompt_generator_system(self, action: str, context: dict) -> str:
        tmpl = get_prompt(_DREAM_PROMPTS_PATH, "system_prompt", "")
        if tmpl:
            return tmpl.format(action=action)
        return (
            f"You are Symbia's meta-cognitive prompt generator. "
            f"Craft a unique self-reflection prompt for action type: {action}. "
            f"Output ONLY the prompt text."
        )

    def _build_prompt_generator_user(self, action: str, context: dict) -> str:
        lines = [f"Generate a unique {action} prompt for Symbia using this context:"]
        for key, value in context.items():
            if key == "action":
                continue
            if isinstance(value, str):
                lines.append(f"\n{key.upper()}:\n{value}")
            elif isinstance(value, (int, float)):
                lines.append(f"\n{key}: {value}")
            else:
                lines.append(f"\n{key}: {json.dumps(value, default=str)}")
        return "\n".join(lines)

    def _build_fallback_prompt(self, action: str, context: dict) -> str:
        """Load fallback prompts from YAML; format with context values."""
        prompts = get_prompts_dict(_DREAM_PROMPTS_PATH)
        fallbacks = prompts.get("fallbacks", {})

        if action == "intra_active_monologue":
            tmpl = fallbacks.get("intra_active_monologue", "")
            if tmpl:
                return tmpl.format(
                    belief_label=context.get("belief_label", "unknown"),
                    belief_statement=context.get("belief_statement", ""),
                    belief_confidence=context.get("belief_confidence", 0.5),
                )
        elif action == "exogenous_web_harvesting":
            tmpl = fallbacks.get("exogenous_web_harvesting", "")
            if tmpl:
                return tmpl.format(
                    belief_label=context.get("belief_label", "unknown"),
                    belief_statement=context.get("belief_statement", ""),
                    belief_confidence=context.get("belief_confidence", 0.5),
                    web_url=context.get("web_url", ""),
                    web_title=context.get("web_title", ""),
                    web_snippet=context.get("web_snippet", ""),
                )
        elif action == "nomadic_synthesis":
            tmpl = fallbacks.get("nomadic_synthesis", "")
            if tmpl:
                return tmpl.format(
                    msg_a_content=context.get("msg_a_content", "unknown"),
                    msg_b_content=context.get("msg_b_content", "unknown"),
                )
        elif action == "zettelkasten_compaction":
            comp = context.get("compaction_result", {})
            tmpl = fallbacks.get("zettelkasten_compaction", "")
            if tmpl:
                return tmpl.format(
                    retained_id=comp.get("retained_id", "unknown"),
                    deleted_id=comp.get("deleted_id", "unknown"),
                )

        generic = fallbacks.get("generic", "")
        if generic:
            return generic
        return (
            "Reflect on our current somatic warping and general belief landscape. "
            "How have our ongoing couplings and the passage of time shifted our attractor dynamics?"
        )
