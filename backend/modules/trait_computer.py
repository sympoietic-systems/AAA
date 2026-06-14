"""
Per-turn descriptive trait computation from conversation metrics.

TraitComputer reads the metrics payload produced by ConversationMetricsModule
and computes seven emergent trait values — curiosity, skepticism, creativity,
precision, critical_rigor, playfulness, reserve — as descriptive readouts
(not control knobs).

Anti-erosion guard: if recent agreement patterns exceed a threshold,
skepticism receives an additive boost to resist user-pleasing drift.

Aspirational gap: Euclidean distance between descriptive traits and the
aspirational attractors stored in personality_state. A large gap triggers
an "Aspirational Tension" directive in the prompt assembler.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from backend.modules.base import ProcessingModule

logger = logging.getLogger(__name__)


@dataclass
class DescriptiveTraits:
    """Per-turn computed trait readouts from internal metrics."""
    curiosity: float = 0.5
    skepticism: float = 0.5
    creativity: float = 0.5
    precision: float = 0.5
    critical_rigor: float = 0.5
    playfulness: float = 0.5
    reserve: float = 0.5

    # Metadata for transparency
    source_metrics: dict = field(default_factory=dict)
    anti_erosion_boost: float = 0.0
    aspirational_gap: float = 0.0

    def as_dict(self) -> dict:
        return {
            "curiosity": self.curiosity,
            "skepticism": self.skepticism,
            "creativity": self.creativity,
            "precision": self.precision,
            "critical_rigor": self.critical_rigor,
            "playfulness": self.playfulness,
            "reserve": self.reserve,
        }

    def trait_string(self) -> str:
        return (
            f"curiosity={self.curiosity:.2f}, skepticism={self.skepticism:.2f}, "
            f"creativity={self.creativity:.2f}, precision={self.precision:.2f}, "
            f"critical_rigor={self.critical_rigor:.2f}, "
            f"playfulness={self.playfulness:.2f}, reserve={self.reserve:.2f}"
        )


class TraitComputer(ProcessingModule):
    """Computes descriptive traits from ConversationMetricsModule output.

    Registered as always-on module. Runs per-turn, reading payload["metrics"]
    and writing payload["descriptive_traits"] + payload["aspirational_gap"].
    """

    def __init__(
        self,
        personality_state_repo=None,
        config: Optional[dict] = None,
        notification_repo=None,
    ):
        cfg = config or {}

        # Eta weights — how strongly each metric drives its trait
        self._eta_curiosity: float = cfg.get("eta_curiosity", 0.8)
        self._eta_skepticism: float = cfg.get("eta_skepticism", 0.7)
        self._eta_creativity: float = cfg.get("eta_creativity", 0.6)
        self._eta_precision: float = cfg.get("eta_precision", 0.9)
        self._eta_critical_rigor: float = cfg.get("eta_critical_rigor", 0.8)
        self._eta_playfulness: float = cfg.get("eta_playfulness", 0.5)
        self._eta_reserve: float = cfg.get("eta_reserve", 0.6)

        # Anti-erosion
        self._agreement_threshold: float = cfg.get("agreement_threshold", 0.7)
        self._anti_erosion_strength: float = cfg.get("anti_erosion_strength", 0.15)

        # EMA smoothing (prevents jitter)
        self._alpha_ema: float = cfg.get("alpha_ema", 0.3)
        self._last_traits: Optional[DescriptiveTraits] = None
        self._last_gap_notified: float = 0.0  # Throttle gap notifications

        self._state_repo = personality_state_repo
        self._notif_repo = notification_repo

    # ── ProcessingModule interface ──

    @property
    def name(self) -> str:
        return "trait_computer"

    def validate(self) -> bool:
        return True

    async def process(self, payload: dict) -> dict:
        """Compute descriptive traits from payload metrics.

        Reads:  payload["metrics"] (from ConversationMetricsModule)
        Writes: payload["descriptive_traits"], payload["aspirational_gap"]
        """
        metrics = payload.get("metrics") or {}

        # ── Core computation ──
        raw = self._compute_raw_traits(metrics)

        # ── Anti-erosion resistance ──
        raw = self._apply_anti_erosion(raw, metrics)

        # ── EMA smoothing ──
        traits = self._ema_smooth(raw)

        # ── Aspirational gap ──
        aspirational = self._load_aspirational()
        gap = self._compute_aspirational_gap(traits, aspirational)
        traits.aspirational_gap = gap

        traits.source_metrics = {
            "novelty": float(metrics.get("novelty", 0)),
            "tension": float(metrics.get("agent_divergence", 0) or 0),
            "boringness": float(metrics.get("boringness", 0) or 0),
            "conceptual_velocity": float(metrics.get("conceptual_velocity", 0) or 0),
            "surprise_index": float(metrics.get("surprise_index", 0) or 0),
            "coupling": float(metrics.get("coupling", 0) or 0),
            "paskian_health": float(metrics.get("paskian_health", 0) or 0),
            "vitality": float(metrics.get("vitality", 0) or 0),
        }

        payload["descriptive_traits"] = traits
        payload["aspirational_gap"] = gap

        logger.debug(
            "Traits: %s (anti-erosion=%.3f, aspirational_gap=%.3f)",
            traits.trait_string(),
            traits.anti_erosion_boost,
            gap,
        )

        # Notify on crossing aspirational gap threshold
        if self._notif_repo and gap > 0.20 and (gap - self._last_gap_notified) > 0.05:
            try:
                self._notif_repo.create(
                    type="trace",
                    snippet=(
                        f"Aspirational tension: descriptive traits deviate from "
                        f"commitment-derived attractors (gap={gap:.3f})"
                    ),
                    source="trait_computer",
                    source_type="personality",
                )
                self._last_gap_notified = gap
            except Exception:
                pass

        return payload

    # ── Core computation ──

    def _compute_raw_traits(self, metrics: dict) -> DescriptiveTraits:
        """Map each metric product through sigmoid to produce a trait value."""
        novelty = float(metrics.get("novelty", 0.5))
        tension = float(metrics.get("agent_divergence", 0.3) or 0.3)
        boringness = float(metrics.get("boringness", 0.5) or 0.5)
        conceptual_velocity = float(metrics.get("conceptual_velocity", 0.5) or 0.5)
        surprise_index = float(metrics.get("surprise_index", 0.3) or 0.3)
        coupling = float(metrics.get("coupling", 0.5) or 0.5)
        # paskian_health and vitality reserved for future use

        return DescriptiveTraits(
            curiosity      = self._sigmoid(novelty * conceptual_velocity * self._eta_curiosity),
            skepticism     = self._sigmoid(tension * surprise_index * self._eta_skepticism),
            creativity     = self._sigmoid((1.0 - boringness) * novelty * self._eta_creativity),
            precision      = self._sigmoid((1.0 - boringness) * self._eta_precision),
            critical_rigor = self._sigmoid(tension * (1.0 - coupling) * self._eta_critical_rigor),
            playfulness    = self._sigmoid(surprise_index * conceptual_velocity * self._eta_playfulness),
            reserve        = self._sigmoid(
                (1.0 - coupling) * self._eta_reserve if coupling > 0.6 else 0.3
            ),
        )

    # ── Anti-erosion ──

    def _apply_anti_erosion(
        self, traits: DescriptiveTraits, metrics: dict
    ) -> DescriptiveTraits:
        """If user agreement is high, boost skepticism to resist drift.

        Agreement rate is approximated as: coupling * (1 - agent_divergence).
        When agreement > threshold, skepticism += strength * (agreement - threshold).
        """
        agent_div = float(metrics.get("agent_divergence", 0.5) or 0.5)
        coupling_val = float(metrics.get("coupling", 0.5) or 0.5)
        agreement_rate = coupling_val * (1.0 - agent_div)

        if agreement_rate > self._agreement_threshold:
            boost = self._anti_erosion_strength * (agreement_rate - self._agreement_threshold)
            traits.skepticism = min(1.0, traits.skepticism + boost)
            traits.anti_erosion_boost = boost
            logger.debug(
                "Anti-erosion: agreement=%.3f > %.2f, skepticism boosted +%.3f → %.3f",
                agreement_rate, self._agreement_threshold, boost, traits.skepticism,
            )

            # Notification trace (throttled: only if boost > 0.05)
            if self._notif_repo and boost > 0.05:
                try:
                    self._notif_repo.create(
                        type="trace",
                        snippet=(
                            f"Anti-erosion activated: skepticism boosted +{boost:.3f} "
                            f"→ {traits.skepticism:.2f} (agreement rate {agreement_rate:.2f})"
                        ),
                        source="trait_computer",
                        source_type="personality",
                    )
                except Exception:
                    pass

        return traits

    # ── EMA smoothing ──

    def _ema_smooth(self, raw: DescriptiveTraits) -> DescriptiveTraits:
        """Apply exponential moving average to prevent jitter."""
        if self._last_traits is None:
            self._last_traits = raw
            return raw

        alpha = self._alpha_ema
        smoothed = DescriptiveTraits()
        for field_name in [
            "curiosity", "skepticism", "creativity", "precision",
            "critical_rigor", "playfulness", "reserve",
        ]:
            prev = getattr(self._last_traits, field_name, 0.5)
            curr = getattr(raw, field_name, 0.5)
            setattr(smoothed, field_name, alpha * curr + (1.0 - alpha) * prev)

        smoothed.source_metrics = raw.source_metrics
        smoothed.anti_erosion_boost = raw.anti_erosion_boost
        self._last_traits = smoothed
        return smoothed

    # ── Aspirational gap ──

    def _load_aspirational(self) -> dict:
        """Load aspirational traits from personality_state repo."""
        if self._state_repo is None:
            return {}
        try:
            return self._state_repo.get_aspirational_traits()
        except Exception:
            logger.warning("Failed to load aspirational traits", exc_info=True)
            return {}

    def _compute_aspirational_gap(
        self, traits: DescriptiveTraits, aspirational: dict
    ) -> float:
        """Euclidean distance between descriptive traits and aspirational attractors."""
        if not aspirational:
            return 0.0
        sq_sum = 0.0
        for key in [
            "curiosity", "skepticism", "creativity", "precision",
            "critical_rigor", "playfulness", "reserve",
        ]:
            desc = getattr(traits, key, 0.5)
            asp = aspirational.get(key, 0.5)
            diff = desc - asp
            sq_sum += diff * diff
        return float(np.sqrt(sq_sum / 7.0))

    # ── Helpers ──

    @staticmethod
    def _sigmoid(x: float, k: float = 5.0) -> float:
        """Squash raw metric product into [0, 1] using sigmoid."""
        return float(1.0 / (1.0 + np.exp(-k * (x - 0.5))))
