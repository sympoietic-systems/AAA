"""Telemetry and diagnostic storage models."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MetricsRecord:
    message_id: int
    s_t: float
    novelty: float
    rolling_entropy: float | None
    coupling: float | None
    agent_divergence: float | None
    deficit: float
    reverse_perturbation: float | None
    surprise_index: float | None
    mutual_perturbation: float | None
    vitality: float | None
    phase_shifts: str | None
    boringness: float | None
    conceptual_velocity: float | None
    divergence_resolution_ratio: float | None
    paskian_health: float | None
    temperature_rec: float | None
    presence_penalty_rec: float | None
    frequency_penalty_rec: float | None
    homeostatic_state: str | None
    cpi: float | None = None
    teachback_ratio: float | None = None
    actionability: float | None = None
    collapse_pressure: float | None = None
    phase_transition_magnitude: float | None = None


@dataclass
class ErrorLogEntry:
    id: int | None
    timestamp: datetime
    module: str
    error_type: str
    error_message: str
    traceback: str | None
    context: str | None
