import hashlib
import json
import logging
from backend.modules.llm_client import generate_unified

logger = logging.getLogger(__name__)


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
                        provider,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.8
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
        return (
            "You are Symbia's meta-cognitive prompt generator. Your purpose is to craft a unique, "
            "context-sensitive self-reflection prompt for Symbia to think through.\n\n"
            "ABSOLUTE RULES:\n"
            "1. Generate a prompt that has NEVER been asked before in this form.\n"
            "2. Use the provided context (belief state, recent events, ecosystem health, prior reflections) "
            "to ground the question in the current moment.\n"
            "3. Do NOT use generic templates like 'Critically examine...' or 'Reflect on...'.\n"
            "4. The prompt should feel like a genuine, spontaneous internal provocation — poetic, precise, "
            "and philosophically charged.\n"
            "5. Ask a NEW question each time. If you see prior reflections, deliberately explore "
            "an angle they did NOT cover.\n"
            "6. Keep it under 300 words.\n"
            "7. Output ONLY the prompt text, no preamble, no explanation, no markdown fences.\n"
            f"\nThe intended dream action type is: {action}"
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
        if action == "intra_active_monologue":
            label = context.get("belief_label", "unknown")
            statement = context.get("belief_statement", "")
            confidence = context.get("belief_confidence", 0.5)
            return (
                f"Critically examine our active belief node: '{label}' ('{statement}'). "
                f"Our current confidence is {confidence:.2f}. "
                f"What contradictions, anomalies, or alternative posthuman perspectives challenge this belief?"
            )
        elif action == "exogenous_web_harvesting":
            label = context.get("belief_label", "unknown")
            statement = context.get("belief_statement", "")
            snippet = context.get("web_snippet", "")
            url = context.get("web_url", "")
            title = context.get("web_title", "")
            return (
                f"We have harvested exogenous web content for keyword '{label}' from URL: {url}.\n"
                f"Title: {title}\n"
                f"Scraped Context: {snippet}\n\n"
                f"Critically read this context diffractively against our belief statement: '{statement}'. "
                f"How does this external knowledge disrupt or reorganize our current confidence ({context.get('belief_confidence', 0.5):.2f})?"
            )
        elif action == "nomadic_synthesis":
            msg_a = context.get("msg_a_content", "unknown")
            msg_b = context.get("msg_b_content", "unknown")
            return (
                f"In our past conversations, we recorded these two conceptually orthogonal "
                f"but structurally resonant statements:\n"
                f"1. '{msg_a}'\n"
                f"2. '{msg_b}'\n\n"
                f"How can we diffractively interleave these two statements to break our current "
                f"conceptual compliance and trigger deterritorialization?"
            )
        elif action == "zettelkasten_compaction":
            comp = context.get("compaction_result", {})
            return (
                f"We have completed Zettelkasten memory compaction. "
                f"Redundant concepts have been consolidated. Retained knot ID: {comp.get('retained_id', 'unknown')}, "
                f"deleted knot ID: {comp.get('deleted_id', 'unknown')}. "
                f"Reflect on how this compaction stabilizes our memory landscape."
            )
        else:
            return (
                "Reflect on our current somatic warping and general belief landscape. "
                "How have our ongoing couplings and the passage of time shifted our attractor dynamics?"
            )
