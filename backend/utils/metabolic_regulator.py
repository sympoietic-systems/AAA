"""Metabolic Budget Controller — financial and reasoning guardrails.

Three-layer budget architecture:
  1. In-Process: MetabolicBudget class with affine-type delegation
  2. API Gateway: LiteLLM proxy limits (optional)
  3. Provider-Side: thinking.budget_tokens / reasoning_effort

Homeostatic traits (Curiosity, Boredom) dynamically scale reasoning budgets.

See docs/systems/AUTONOMOUS_RESEARCH_ARCHITECTURE.md Section 14.
"""

import logging
from typing import Any

logger = logging.getLogger("aaa.metabolic_budget")


class MetabolicDepletionError(Exception):
    """Hard budget boundary reached — no further spending permitted."""
    pass


class BudgetDelegationError(Exception):
    """Attempted to spend from a delegated (locked) budget context."""
    pass


class MetabolicBudget:
    """Non-aliasing budget controller with affine-type delegation semantics.

    A budget delegated to a child thread cannot be spent from directly.
    It is locked until the child's unspent capacity is reclaimed.
    This prevents double-spending across recursive async research branches.
    """

    def __init__(self, limit_usd: float, name: str = "unnamed"):
        self._limit_usd = limit_usd
        self._name = name
        self._spent_usd = 0.0
        self._is_delegated = False
        self._child_budgets: list[MetabolicBudget] = []

    @property
    def remaining(self) -> float:
        return max(0.0, self._limit_usd - self._spent_usd)

    @property
    def is_exhausted(self) -> bool:
        return self.remaining <= 0.0

    @property
    def utilization_pct(self) -> float:
        if self._limit_usd <= 0:
            return 0.0
        return (self._spent_usd / self._limit_usd) * 100

    @property
    def spent(self) -> float:
        return self._spent_usd

    @property
    def limit(self) -> float:
        return self._limit_usd

    def spend(self, amount_usd: float) -> None:
        """Record a metabolic expenditure."""
        if self._is_delegated:
            raise BudgetDelegationError(
                f"Budget '{self._name}' is delegated — cannot spend directly."
            )
        if self._spent_usd + amount_usd > self._limit_usd:
            raise MetabolicDepletionError(
                f"Metabolic budget '{self._name}' exhausted: "
                f"${self._spent_usd:.4f} / ${self._limit_usd:.2f}"
            )
        self._spent_usd += amount_usd

    def try_spend(self, amount_usd: float) -> bool:
        """Attempt to spend. Returns True if successful, False otherwise."""
        try:
            self.spend(amount_usd)
            return True
        except (MetabolicDepletionError, BudgetDelegationError):
            return False

    def delegate(self, limit_usd: float) -> 'MetabolicBudget':
        """Create a child budget for a sub-branch (research branch).

        Locks the parent from direct spending until the child is reclaimed.
        """
        if self._is_delegated:
            raise BudgetDelegationError(f"Budget '{self._name}' already delegated.")

        if limit_usd > self.remaining:
            limit_usd = self.remaining

        self._is_delegated = True
        child = MetabolicBudget(limit_usd, f"{self._name}_child")
        self._child_budgets.append(child)
        return child

    def reclaim(self, child: 'MetabolicBudget') -> None:
        """Reclaim a child budget, adding its spent amount to parent."""
        if child not in self._child_budgets:
            raise ValueError(f"Cannot reclaim unrecognized child budget.")
        self._spent_usd += child._spent_usd
        self._child_budgets.remove(child)
        self._is_delegated = bool(self._child_budgets)

    def __repr__(self) -> str:
        return (
            f"MetabolicBudget('{self._name}': "
            f"${self._spent_usd:.4f}/${self._limit_usd:.2f}"
            f"{' [DELEGATED]' if self._is_delegated else ''})"
        )


# ── Homeostatic → Reasoning Parameter Mapping ───────────────────────

def get_llm_execution_parameters(
    traits: dict[str, float],
    config: dict | None = None,
) -> dict[str, Any]:
    """Map Symbia's dynamic personality traits to LLM reasoning parameters.

    - High Curiosity → Extended thinking budget
    - High Boredom → Restricted budget (prevent wasteful loops)
    """
    cfg = config or {}
    curiosity = traits.get("curiosity", 0.5)
    boredom = traits.get("boringness", 0.3)

    base_completion_tokens = cfg.get("base_completion_tokens", 4096)
    base_thinking_budget = cfg.get("base_thinking_budget", 2048)

    # Adaptive scaling: curiosity expands, boredom contracts
    metabolic_multiplier = 1.0 + (curiosity * 0.8) - (boredom * 0.5)
    metabolic_multiplier = max(0.4, min(2.0, metabolic_multiplier))

    return {
        "max_completion_tokens": int(base_completion_tokens * metabolic_multiplier),
        "thinking_budget_tokens": int(base_thinking_budget * metabolic_multiplier),
        "reasoning_effort": (
            "high" if curiosity > 0.8 else ("low" if boredom > 0.7 else "medium")
        ),
        "depth_limit": 4 if curiosity > 0.8 else 2,
        "breadth_limit": 4 if curiosity > 0.7 else 2,
    }
