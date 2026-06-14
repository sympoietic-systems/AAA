"""
Expertise mass accretion from demonstrable structural coupling signals.

ExpertiseEngine scans each turn's assistant message for evidence of structural
coupling — aaa-note domain tags, skill nucleations, unprompted domain returns,
shared note matches, and document matches — and accretes ontological mass to
the corresponding expertise domain.

Signal weights (self-generated > externally ingested):
  aaa_note_domain    : 0.6  (Symbia actively self-reflected in the domain)
  skill_nucleation   : 0.5  (She grew a procedural organ)
  unprompted_return  : 0.4  (Independent recall without user prompting)
  shared_note_match  : 0.3  (External material encountered)
  document_match     : 0.2  (Passive ingestion)

Mass accretion: Δmass = η × signal_weight / (1.0 + current_mass)
Diminishing returns prevent infinite growth.

Lifecycle transitions:
  - mass > proto_threshold (0.3) → proto → active, level=developing
  - no signal for N turns → active → dormant
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from backend.modules.base import ProcessingModule

logger = logging.getLogger(__name__)

# Signal weight configuration
SIGNAL_WEIGHTS = {
    "aaa_note_domain": 0.6,
    "skill_nucleation": 0.5,
    "unprompted_return": 0.4,
    "shared_note_match": 0.3,
    "document_match": 0.2,
}


class ExpertiseEngine(ProcessingModule):
    """Accretes expertise mass from demonstrable structural coupling.

    Registered as always-on module. Runs per-turn.
    """

    def __init__(
        self,
        expertise_repo=None,
        config: Optional[dict] = None,
        lexicon_scorer=None,
        notification_repo=None,
    ):
        cfg = config or {}
        self._repo = expertise_repo
        self._eta: float = cfg.get("eta_accretion", 0.1)
        self._proto_threshold: float = cfg.get("proto_threshold", 0.3)
        self._dormancy_turns: int = cfg.get("dormancy_turns", 50)
        self._scorer = lexicon_scorer
        self._notif_repo = notification_repo

        # Allow config to override signal weights
        cfg_weights = cfg.get("signal_weights", {})
        self._weights = {**SIGNAL_WEIGHTS, **cfg_weights}

        # Dormancy check throttle
        self._turn_counter: int = 0
        self._dormancy_check_interval: int = 20

    # ── ProcessingModule interface ──

    @property
    def name(self) -> str:
        return "expertise_engine"

    def validate(self) -> bool:
        return self._repo is not None

    async def process(self, payload: dict) -> dict:
        """Scan for structural coupling signals and accrete mass."""
        self._turn_counter += 1

        signals = self._detect_signals(payload)

        for signal in signals:
            await self._accrete(signal)

        # Periodic dormancy check
        if self._turn_counter % self._dormancy_check_interval == 0:
            await self._check_dormancy()

        payload["expertise_signals_detected"] = len(signals)
        return payload

    # ── Signal detection ──

    def _detect_signals(self, payload: dict) -> list[dict]:
        """Extract all structural coupling signals from the current turn."""
        signals = []
        messages = payload.get("messages", [])

        # Find the last assistant message
        assistant_content = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                assistant_content = msg.get("content", "")
                break

        if not assistant_content:
            return signals

        # 1. <aaa-note domain="X"> tags
        # Pattern: <aaa-note comment="..." domain="systems_theory" visibility="shared">
        domain_pattern = r'<aaa-note[^>]*domain="([^"]+)"[^>]*>'
        seen_domains = set()
        for match in re.finditer(domain_pattern, assistant_content):
            domain = match.group(1).lower().strip().replace(" ", "_")
            if domain and domain not in seen_domains:
                seen_domains.add(domain)
                signals.append({
                    "type": "aaa_note_domain",
                    "domain": domain,
                    "weight": self._weights["aaa_note_domain"],
                    "source_text": match.group(0),
                })

        # 2. <skill-nucleation> blocks with domain vocabulary
        # (these come from skill_workshop via payload)
        skill_events = payload.get("skill_nucleation_events", [])
        for event in skill_events:
            domain = (event.get("domain_affinity") or "").lower().strip().replace(" ", "_")
            if domain:
                signals.append({
                    "type": "skill_nucleation",
                    "domain": domain,
                    "weight": self._weights["skill_nucleation"],
                    "source_text": event.get("name", ""),
                })

        # 3. Shared note / document matches (pre-computed upstream)
        for match_key, signal_type in [
            ("expertise_signal_matches", "shared_note_match"),
        ]:
            for match in payload.get(match_key, []):
                domain = (match.get("domain") or "").lower().strip()
                if domain:
                    signals.append({
                        "type": signal_type,
                        "domain": domain,
                        "weight": match.get("weight", self._weights.get(signal_type, 0.3)),
                        "source_text": match.get("source", ""),
                    })

        return signals

    # ── Mass accretion ──

    async def _accrete(self, signal: dict) -> None:
        """Accrete mass to a domain node. Create proto-node if new."""
        domain = signal["domain"]
        weight = signal["weight"]

        if not self._repo:
            return

        node = self._repo.get_by_domain(domain)

        if node is None:
            # Nucleate a proto-domain
            from backend.storage.models import ExpertiseNode

            # Score the domain name for vector representation
            vector_json = "[]"
            if self._scorer is not None:
                try:
                    vec = self._scorer.score(domain)
                    import json
                    vector_json = json.dumps(vec.tolist())
                except Exception:
                    pass

            node = ExpertiseNode(
                id=str(uuid.uuid4()),
                agent_id="symbia",
                domain=domain,
                lifecycle_stage="proto",
                ontological_mass=0.05,
                level_label="nascent",
                vector_16d=vector_json,
                signal_count=0,
                last_signal_at=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

        # Accrete mass with diminishing returns
        delta = self._eta * weight / (1.0 + node.ontological_mass)
        node.ontological_mass += delta
        node.signal_count += 1
        node.last_signal_at = datetime.now(timezone.utc)
        node.updated_at = datetime.now(timezone.utc)

        # Check crystallization threshold
        if node.lifecycle_stage == "proto" and node.ontological_mass >= self._proto_threshold:
            was_proto = True
            node.lifecycle_stage = "active"
            node.level_label = "developing"
            node.crystallization_rationale = (
                f"Crystallized from proto-domain after {node.signal_count} "
                f"structural coupling signals (mass={node.ontological_mass:.3f})"
            )

            # Notification for crystallization
            if self._notif_repo:
                try:
                    self._notif_repo.create(
                        type="trace",
                        snippet=(
                            f"Expertise domain '{domain}' crystallized to active "
                            f"(mass={node.ontological_mass:.3f}, {node.signal_count} signals)"
                        ),
                        source=f"expertise:{domain}",
                        source_type="expertise",
                        source_id=node.id,
                    )
                except Exception:
                    pass

        # Update level label from mass
        node.level_label = self._compute_level_label(node)

        self._repo.upsert(node)

        logger.debug(
            "Expertise '%s': +%.4f mass → %.3f (%s, %s)",
            domain, delta, node.ontological_mass, node.lifecycle_stage, node.level_label,
        )

    # ── Dormancy ──

    async def _check_dormancy(self) -> None:
        """Mark domains with no recent signal as dormant."""
        if not self._repo:
            return

        active_nodes = self._repo.get_active()
        now = datetime.now(timezone.utc)

        for node in active_nodes:
            if node.last_signal_at is None:
                continue
            # Approximate turns-since-last-signal from time delta
            # In a real system with known turn frequency, this would be more precise
            hours_since = (now - node.last_signal_at).total_seconds() / 3600.0
            # Rough heuristic: ~1 turn per minute → dormancy_turns minutes
            if hours_since > (self._dormancy_turns / 60.0):
                node.lifecycle_stage = "dormant"
                node.level_label = "dormant"
                self._repo.update(node)
                logger.info(
                    "Expertise '%s' marked dormant (no signal for ~%.1f hours)",
                    node.domain, hours_since,
                )
                # Notification for dormancy
                if self._notif_repo:
                    try:
                        self._notif_repo.create(
                            type="trace",
                            snippet=f"Expertise domain '{node.domain}' went dormant (no signals for {self._dormancy_turns}+ turns)",
                            source=f"expertise:{node.domain}",
                            source_type="expertise",
                            source_id=node.id,
                        )
                    except Exception:
                        pass

    # ── Helpers ──

    @staticmethod
    def _compute_level_label(node) -> str:
        """Map ontological_mass to human-readable level."""
        if node.lifecycle_stage == "dormant":
            return "dormant"
        if node.ontological_mass < 0.3:
            return "nascent"
        if node.ontological_mass < 1.0:
            return "developing"
        return "advanced"
