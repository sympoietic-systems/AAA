"""TypeSafe Jev (System One) Decision Provider.

Non-blocking async client implementing the System One evaluation protocol
for calibrated probabilistic decision-making (Choice, Noul, Score).
Supports direct TypeSafe API and OpenRouter Decisions endpoints.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TYPESAFE_BASE = "https://api.typesafe.ai/v1"
OPENROUTER_DECISIONS_BASE = "https://openrouter.ai/api/alpha"
DEFAULT_MODEL = "typesafe/jev-1.13"


class TypeSafeDecisionClient:
    """Async decision client for TypeSafe Jev System One models."""

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        model: str | None = None,
        timeout: float = 3.0,
        config: dict | None = None,
    ):
        if config:
            api_key = api_key or config.get("api_key")
            api_base = api_base or config.get("api_base")
            model = model or config.get("model")
            timeout = float(config.get("timeout", timeout))

        self.api_key = api_key
        self.api_base = (api_base or DEFAULT_TYPESAFE_BASE).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self._is_openrouter = "openrouter.ai" in self.api_base

    @classmethod
    def from_config(cls, config: dict | None = None) -> "TypeSafeDecisionClient":
        return cls(config=config)

    @property
    def is_configured(self) -> bool:
        """Return True if API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _resolve_url(self) -> str:
        """Resolve the evaluation endpoint URL."""
        if self._is_openrouter:
            if self.api_base.endswith("/decisions"):
                return self.api_base
            return f"{self.api_base}/decisions"
        if self.api_base.endswith("/systemone"):
            return self.api_base
        return f"{self.api_base}/systemone"

    def _build_headers(self) -> dict[str, str]:
        """Build HTTP headers for request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self._is_openrouter:
            headers["HTTP-Referer"] = "https://github.com/sympoietic-systems/AAA"
            headers["X-Title"] = "AAA-Symbia"
        return headers

    async def evaluate(
        self,
        state: dict[str, Any] | str,
        questions: dict[str, dict[str, Any]],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Evaluate state against a dictionary of typed questions.

        Args:
            state: Context/state object or string to evaluate.
            questions: Dictionary mapping question_id -> question definition.
                Question definition format:
                  Choice: {"type": "choice", "instructions": "...", "criteria": {"opt": "desc", ...}}
                  Noul: {"type": "noul", "instructions": "..."}
                  Score: {"type": "score", "instructions": "...", "criteria": ["Level 0", "Level 1", ...]}
            model: Optional model override (defaults to self.model).

        Returns:
            dict containing:
              - "success": bool
              - "model": str
              - "answers": dict[str, dict]
              - "usage": dict
              - "error": str | None
        """
        if not self.is_configured:
            return {
                "success": False,
                "model": self.model,
                "answers": {},
                "usage": {},
                "error": "TypeSafe API key not configured",
            }

        url = self._resolve_url()
        selected_model = model or self.model

        payload = {
            "state": state,
            "questions": questions,
            "model": selected_model,
        }

        headers = self._build_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code != 200:
                    logger.warning(
                        "TypeSafe Jev request returned HTTP %d: %s",
                        response.status_code,
                        response.text[:200],
                    )
                    return {
                        "success": False,
                        "model": selected_model,
                        "answers": {},
                        "usage": {},
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    }

                data = response.json()
                answers = data.get("answers") or data.get("results", {})
                usage = data.get("usage", {})

                return {
                    "success": True,
                    "model": data.get("model", selected_model),
                    "answers": answers,
                    "usage": usage,
                    "error": None,
                }
        except httpx.TimeoutException:
            logger.warning("TypeSafe Jev evaluation timed out after %.2fs", self.timeout)
            return {
                "success": False,
                "model": selected_model,
                "answers": {},
                "usage": {},
                "error": f"Timeout after {self.timeout}s",
            }
        except Exception as e:
            logger.warning("TypeSafe Jev evaluation failed: %s", e)
            return {
                "success": False,
                "model": selected_model,
                "answers": {},
                "usage": {},
                "error": str(e),
            }


def build_choice_question(question: str, options: list[str], id: str | None = None) -> dict[str, Any]:
    """Helper to build a TypeSafe Choice question."""
    payload: dict[str, Any] = {
        "type": "Choice",
        "question": question,
        "options": options,
    }
    if id:
        payload["id"] = id
    return payload


def build_noul_question(question: str, id: str | None = None) -> dict[str, Any]:
    """Helper to build a TypeSafe Noul question."""
    payload: dict[str, Any] = {
        "type": "Noul",
        "question": question,
    }
    if id:
        payload["id"] = id
    return payload


def build_score_question(question: str, options: list[str], id: str | None = None) -> dict[str, Any]:
    """Helper to build a TypeSafe Score question."""
    payload: dict[str, Any] = {
        "type": "Score",
        "question": question,
        "options": options,
    }
    if id:
        payload["id"] = id
    return payload
