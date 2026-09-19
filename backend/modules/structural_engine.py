import contextlib
import json
import logging
import re
from typing import Any

import numpy as np

from backend.modules.base import ProcessingModule
from backend.modules.llm_client import generate_unified
from backend.utils.prompt_loader import get_prompt
from backend.utils.vector import CYBERNETIC_DIMENSIONS

logger = logging.getLogger(__name__)


# In-memory cache for LLM justifications
JUSTIFICATION_CACHE: dict[str, str] = {}


def get_justification(content: str) -> str | None:
    if not content:
        return None
    import hashlib

    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return JUSTIFICATION_CACHE.get(h)


def set_justification(content: str, justification: str) -> None:
    if not content or not justification:
        return
    import hashlib

    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    JUSTIFICATION_CACHE[h] = justification
    # Prevent memory leaks
    if len(JUSTIFICATION_CACHE) > 1000:
        first_key = next(iter(JUSTIFICATION_CACHE))
        JUSTIFICATION_CACHE.pop(first_key)


class StructuralScorer:
    """Interface for structural signature calculators."""

    def score(self, text: str, context: dict | None = None) -> np.ndarray:
        raise NotImplementedError()


def parse_scorer_response(content: str) -> tuple[list[float] | None, str | None]:
    """Robustly parse structural scorer response even under truncation, think tags, or trailing commas."""
    # Clean up <think> tags if any (e.g. from reasoning/R1 models)
    content_clean = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    # Try standard JSON extraction
    start_brace = content_clean.find("{")
    end_brace = content_clean.rfind("}")

    scores = None
    justification = None

    if start_brace != -1 and end_brace > start_brace:
        json_str = content_clean[start_brace : end_brace + 1]
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                scores = data.get("scores")
                justification = data.get("justification")
        except Exception:
            # Try removing trailing commas and parse again
            try:
                cleaned_json = re.sub(r",\s*([\]\}])", r"\1", json_str)
                data = json.loads(cleaned_json)
                if isinstance(data, dict):
                    scores = data.get("scores")
                    justification = data.get("justification")
            except Exception:
                pass

    # Fallback for scores: if standard parse failed, search scores array with regex
    if not isinstance(scores, list) or len(scores) == 0:
        scores = None
        scores_match = re.search(r'"scores"\s*:\s*\[', content_clean, re.IGNORECASE)
        if not scores_match:
            scores_match = re.search(r"scores\s*:\s*\[", content_clean, re.IGNORECASE)

        if scores_match:
            start_idx = scores_match.end()
            remainder = content_clean[start_idx:]
            end_idx = remainder.find("]")
            if end_idx != -1:
                array_content = remainder[:end_idx]
            else:
                end_idx = remainder.find("}")
                array_content = remainder[:end_idx] if end_idx != -1 else remainder

            nums = re.findall(r"-?\d*\.\d+|-?\d+", array_content)
            scores_list = []
            for n in nums:
                with contextlib.suppress(ValueError):
                    scores_list.append(float(n))
            if len(scores_list) > 0:
                scores = scores_list

    # Fallback for justification: search with regex
    if not isinstance(justification, str) or not justification:
        just_match = re.search(r'"justification"\s*:\s*"([^"]*)"', content_clean, re.IGNORECASE)
        if not just_match:
            just_match = re.search(r'justification\s*:\s*"([^"]*)"', content_clean, re.IGNORECASE)
        if just_match:
            justification = just_match.group(1)
        else:
            # Truncated string within quotes fallback
            just_match_trunc = re.search(r'"justification"\s*:\s*"([^"]*)$', content_clean, re.IGNORECASE)
            if not just_match_trunc:
                just_match_trunc = re.search(r'justification\s*:\s*"([^"]*)$', content_clean, re.IGNORECASE)
            if just_match_trunc:
                justification = just_match_trunc.group(1)

    return scores, justification


_STRUCTURAL_CLASSIFICATION_PATH = "structural_engine/classification.yaml"
_DEFAULT_SYSTEM_PROMPT = "You are a cybernetic taxonomy classifier. Respond ONLY with the requested JSON object."


class LLMScorer(StructuralScorer):
    """Interrogates the LLM to score the text across the 16 dimensions using a structured schema."""

    def __init__(self, provider=None, system_prompt: str | None = None):
        self.provider = provider
        self.system_prompt = system_prompt or get_prompt(
            _STRUCTURAL_CLASSIFICATION_PATH,
            "system_prompt",
            _DEFAULT_SYSTEM_PROMPT,
        )
        # Load the user prompt template once at init
        self._user_prompt_tmpl = get_prompt(
            _STRUCTURAL_CLASSIFICATION_PATH,
            "user_prompt_template",
            "",
        )

    async def score_async(self, text: str, context: dict | None = None) -> np.ndarray:
        if not self.provider:
            return np.full(16, 0.25, dtype=np.float32)

        _FALLBACK_SCORES = {"scores": [0.25] * 16, "justification": "scorer fallback"}

        try:
            if self._user_prompt_tmpl:
                prompt = self._user_prompt_tmpl.format(text=text)
            else:
                prompt = f"Classify the following text across 16 cybernetic dimensions:\n\n{text}"
            res = await generate_unified(
                self.provider,
                system_prompt=self.system_prompt,
                user_prompt=prompt,
                expect_json=True,
                fallback_value=_FALLBACK_SCORES,
                temperature=0.1,
                max_tokens=3000,
                thinking_budget=0,
            )
            content = res.get("content", "").strip()
            data = res.get("json_data")
            if data and isinstance(data, dict) and "scores" in data:
                scores_list = data.get("scores")
                justification = data.get("justification")
            else:
                scores_list, justification = parse_scorer_response(content)
            if justification:
                set_justification(text, justification)

            if scores_list is not None and len(scores_list) > 0:
                # Pad or truncate to 16
                while len(scores_list) < 16:
                    scores_list.append(0.25)
                scores_list = scores_list[:16]
                # Clamp values strictly to [0.0, 1.0]
                clamped = [max(0.0, min(1.0, float(v))) for v in scores_list]
                return np.array(clamped, dtype=np.float32)
            logger.warning("Failed to parse scores from LLMScorer response content: %s", content)
        except Exception as e:
            logger.exception("Error in LLMScorer generation: %s", e)

        return np.full(16, 0.25, dtype=np.float32)

    def score(self, text: str, context: dict | None = None) -> np.ndarray:
        # Synchronous fallback runs asyncio loop
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running (e.g. inside FastAPI), we run it via task
                import nest_asyncio

                nest_asyncio.apply()
            return loop.run_until_complete(self.score_async(text, context))
        except Exception as e:
            logger.error("Failed to run LLMScorer synchronously: %s", e)
            return np.full(16, 0.25, dtype=np.float32)


class JevStructuralScorer(StructuralScorer):
    """Evaluates the 16 cybernetic dimensions using TypeSafe Jev System One Score primitives.

    Returns both the 16D power/score vector and the 16D confidence vector, evaluated
    in a single sub-250ms parallel pass with calibrated RLCD probabilities.
    """

    # 4-level rubric for discrete cybernetic presence
    RUBRIC_LEVELS = [
        "Level 0: Negligible / completely absent",
        "Level 1: Incidental / peripheral presence",
        "Level 2: Moderate / noticeable presence",
        "Level 3: Dominant / core defining characteristic",
    ]

    def __init__(self, client: Any = None, rubric_levels: list[str] | None = None):
        self.client = client
        self.rubric_levels = rubric_levels or self.RUBRIC_LEVELS

    @property
    def is_available(self) -> bool:
        return bool(self.client and getattr(self.client, "is_configured", False))

    def _build_questions(self) -> dict[str, dict[str, Any]]:
        """Construct parallel Score questions for all 16 cybernetic dimensions."""
        questions: dict[str, dict[str, Any]] = {}
        for i, (dim_slug, dim_title, dim_focus) in enumerate(CYBERNETIC_DIMENSIONS):
            q_id = f"dim_{i:02d}_{dim_slug}"
            questions[q_id] = {
                "type": "score",
                "instructions": (
                    f"Assess the degree to which this text exhibits cybernetic dimension {i+1} ({dim_title}): {dim_focus}."
                ),
                "criteria": self.rubric_levels,
            }
        return questions

    async def score_with_confidence_async(
        self, text: str, context: dict | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate text returning both power vector and confidence vector.

        Returns:
            (power_16d, confidence_16d) as (np.ndarray, np.ndarray) with values in [0.0, 1.0].
        """
        fallback_power = np.full(16, 0.25, dtype=np.float32)
        fallback_conf = np.full(16, 0.50, dtype=np.float32)

        if not self.is_available or not text:
            return fallback_power, fallback_conf

        state = {
            "text": text[:3000],
            "char_count": len(text),
        }
        if context:
            state["context"] = {k: v for k, v in context.items() if isinstance(v, (str, int, float, bool))}

        questions = self._build_questions()

        try:
            res = await self.client.evaluate(state=state, questions=questions)
            if not res.get("success"):
                logger.warning("JevStructuralScorer evaluation unsuccessful: %s", res.get("error"))
                return fallback_power, fallback_conf

            answers = res.get("answers") or res.get("results") or {}
            power_list: list[float] = []
            conf_list: list[float] = []

            max_level = max(1, len(self.rubric_levels) - 1)

            for i, (dim_slug, _, _) in enumerate(CYBERNETIC_DIMENSIONS):
                q_id = f"dim_{i:02d}_{dim_slug}"
                q_ans = answers.get(q_id, {})

                # Parse score value (continuous or level index)
                # Jev score can be continuous (0..max_level) or normalized
                raw_score = q_ans.get("score")
                if raw_score is None:
                    raw_score = q_ans.get("value")
                if raw_score is None:
                    raw_score = q_ans.get("level")

                if raw_score is not None:
                    try:
                        val = float(raw_score)
                        # Normalize to [0.0, 1.0] if scaled by max_level
                        if val > 1.0:
                            norm_val = val / float(max_level)
                        else:
                            norm_val = val
                        power_list.append(max(0.0, min(1.0, norm_val)))
                    except (ValueError, TypeError):
                        power_list.append(0.25)
                else:
                    power_list.append(0.25)

                # Parse confidence value
                raw_conf = q_ans.get("confidence")
                if raw_conf is None:
                    raw_conf = q_ans.get("certainty")
                if raw_conf is not None:
                    try:
                        c_val = float(raw_conf)
                        conf_list.append(max(0.0, min(1.0, c_val)))
                    except (ValueError, TypeError):
                        conf_list.append(0.50)
                else:
                    conf_list.append(0.50)

            power_arr = np.array(power_list[:16], dtype=np.float32)
            conf_arr = np.array(conf_list[:16], dtype=np.float32)

            if len(power_arr) < 16:
                power_arr = np.pad(power_arr, (0, 16 - len(power_arr)), constant_values=0.25)
            if len(conf_arr) < 16:
                conf_arr = np.pad(conf_arr, (0, 16 - len(conf_arr)), constant_values=0.50)

            return power_arr, conf_arr

        except Exception as e:
            logger.exception("Error during JevStructuralScorer execution: %s", e)
            return fallback_power, fallback_conf

    async def score_async(self, text: str, context: dict | None = None) -> np.ndarray:
        """Standard StructuralScorer async interface returning 16D power vector."""
        power, _ = await self.score_with_confidence_async(text, context)
        return power

    def score(self, text: str, context: dict | None = None) -> np.ndarray:
        """Synchronous score wrapper, robust to running event loops."""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop is not None and loop.is_running():
                # Running event loop exists — run coroutine in dedicated worker thread
                with ThreadPoolExecutor(max_workers=1) as executor:
                    return executor.submit(asyncio.run, self.score_async(text, context)).result()
            else:
                return asyncio.run(self.score_async(text, context))
        except Exception as e:
            logger.error("Failed to run JevStructuralScorer synchronously: %s", e)
            return np.full(16, 0.25, dtype=np.float32)


class CompositeStructuralScorer(StructuralScorer):
    """Coordinates calculation from different strategies and applies weighted linear combination."""

    def __init__(
        self,
        llm_provider=None,
        jev_client=None,
        config: dict | None = None,
        w_ling: float = 0.25,
        w_topo: float = 0.25,
        w_llm: float = 0.50,
        w_jev: float = 0.0,
    ):
        if config is None:
            try:
                from backend.config import load_config

                config = load_config()
            except Exception:
                config = {}

        ss_cfg = config.get("structural_signature", {})
        self.backend = ss_cfg.get("backend", "jev").lower().strip()
        lexicon_config = ss_cfg.get("lexicon")
        llm_prompt_config = ss_cfg.get("llm_system_prompt")
        self.llm_scorer_enabled = ss_cfg.get("llm_scorer_enabled", self.backend == "llm")

        # Auto-resolve Jev client from config if not explicitly passed
        if jev_client is None:
            ts_cfg = config.get("typesafe", {})
            if ts_cfg.get("enabled", True):
                try:
                    from backend.modules.providers.typesafe_provider import TypeSafeDecisionClient
                    jev_client = TypeSafeDecisionClient.from_config(ts_cfg)
                except Exception as e:
                    logger.debug("Failed to auto-instantiate TypeSafeDecisionClient: %s", e)

        self.llm_scorer = LLMScorer(llm_provider, system_prompt=llm_prompt_config)
        self.jev_scorer = JevStructuralScorer(client=jev_client)

    async def score_async(
        self, text: str, context: dict | None = None, use_llm_scorer: bool | None = None
    ) -> np.ndarray:
        # 1. Primary Jev path (default unless LLM explicitly forced)
        force_llm = (use_llm_scorer is True) or (self.backend == "llm")
        if not force_llm and self.jev_scorer.is_available:
            return await self.jev_scorer.score_async(text, context)

        # 2. LLM fallback / override path
        if self.llm_scorer.provider and (force_llm or not self.jev_scorer.is_available):
            return await self.llm_scorer.score_async(text, context)

        # 3. Fallback if both unavailable
        if self.jev_scorer.is_available:
            return await self.jev_scorer.score_async(text, context)
        return np.full(16, 0.25, dtype=np.float32)

    def score(self, text: str, context: dict | None = None, use_llm_scorer: bool | None = None) -> np.ndarray:
        force_llm = (use_llm_scorer is True) or (self.backend == "llm")
        if not force_llm and self.jev_scorer.is_available:
            return self.jev_scorer.score(text, context)

        if self.llm_scorer.provider and (force_llm or not self.jev_scorer.is_available):
            return self.llm_scorer.score(text, context)

        if self.jev_scorer.is_available:
            return self.jev_scorer.score(text, context)
        return np.full(16, 0.25, dtype=np.float32)


class StructuralScorerModule(ProcessingModule):
    """Pipeline module wrapping CompositeStructuralScorer."""

    def __init__(self, composite_scorer: CompositeStructuralScorer):
        self._scorer = composite_scorer

    @property
    def name(self) -> str:
        return "structural_scorer"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        content = payload.get("content", "")
        use_llm = payload.get("include_structural_scoring")
        if content:
            sig = await self._scorer.score_async(content, use_llm_scorer=use_llm)
            payload["structural_signature"] = sig.tobytes()
        return payload

    @property
    def module_meta(self) -> "ModuleMeta":  # noqa: F821
        from backend.pipeline.metadata import ModuleMeta  # noqa: E402

        return ModuleMeta(
            name="structural_scorer",
            description="Calculates 16-dimensional cybernetic structural signatures of the message text",
            category="perception",
            always_run=True,
        )
