"""Compatibility facade for focused belief use cases."""

from typing import Any

from backend.services.belief.mutation import BeliefMutationUseCases
from backend.services.belief.proposal import BeliefProposalUseCases
from backend.services.belief.query import BeliefQueryUseCases
from backend.services.belief.version import BeliefVersionUseCases


class BeliefService(
    BeliefQueryUseCases,
    BeliefProposalUseCases,
    BeliefMutationUseCases,
    BeliefVersionUseCases,
):
    """Preserve the historical belief service API across focused collaborators."""

    def __init__(self, state: Any) -> None:
        self._state = state
