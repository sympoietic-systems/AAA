"""Pure belief math functions — stateless, testable without DB or LLM dependencies.

Extracted from belief_engine.py to improve modularity and testability.
"""

import json
import logging

import numpy as np

from backend.modules.structural_engine import LEXICON_MAPPINGS

logger = logging.getLogger(__name__)


def calculate_concept_density(text: str, lambda_param: float = 3.0) -> float:
    text_lower = text.lower()
    matched_dims = 0
    for stems in LEXICON_MAPPINGS:
        matched = False
        for stem in stems:
            if stem in text_lower:
                matched = True
                break
        if matched:
            matched_dims += 1
    return float(np.tanh(matched_dims / lambda_param))


def parse_vector_16d(vector_json: str) -> np.ndarray | None:
    if not vector_json or vector_json == "[]":
        return None
    try:
        data = json.loads(vector_json)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None

    if isinstance(data, dict):
        for key in ("v16d", "v384d"):
            if key in data and data[key]:
                vec = np.array(data[key], dtype=np.float32)
                if len(vec) == 16:
                    return vec
        return None

    if isinstance(data, list):
        vec = np.array(data, dtype=np.float32)
        if len(vec) == 16:
            return vec

    return None


def compute_delta_mass(source_weight: float, alignment: float, current_mass: float) -> float:
    eta = 0.02
    return eta * source_weight * alignment / (1.0 + current_mass)


def compute_delta_confidence(alignment: float, perturbation: float, current_mass: float) -> float:
    dc = 0.5
    plasticity = dc * ((1.0 - alignment) / 2.0)
    return (plasticity * alignment * perturbation) / max(current_mass, 0.01)


def clamp_mass(mass: float) -> float:
    return max(0.0, min(3.0, mass))


def clamp_confidence(conf: float) -> float:
    return max(0.0, min(1.0, conf))


def compute_lifecycle_stage(
    current_stage: str,
    new_mass: float,
    new_confidence: float,
) -> str:
    if new_confidence < 0.20:
        return "collapsed"
    if new_mass < 0.02:
        return "collapsed"
    if new_mass < 0.001:
        return "faded"

    if new_mass >= 0.5 and current_stage in ("nucleation", "accretion"):
        return "crystallized"

    if current_stage == "crystallized":
        return "crystallized"
    if current_stage == "senescence":
        if new_mass >= 0.5:
            return "crystallized"
        return "senescence"
    if current_stage == "collapsed":
        return "collapsed"
    if current_stage == "faded":
        return "faded"

    if new_mass < 0.1:
        return "nucleation"
    return "accretion"
