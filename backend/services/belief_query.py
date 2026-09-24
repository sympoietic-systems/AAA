"""Belief read/query use cases."""

import logging
from datetime import UTC
from typing import cast

from backend.services.belief_common import BeliefResult, BeliefUseCase
from backend.services.belief_ports import BeliefQueryRepository
from backend.services.belief_serializer import (
    _parse_event_rationale,
    serialize_belief_event,
    serialize_proposal,
)

logger = logging.getLogger(__name__)


class BeliefQueryUseCases(BeliefUseCase):
    async def get_beliefs(self, conversation_id: str | None = None, agent_id: str = "symbia") -> BeliefResult:
        state = self._state
        belief_repo = cast(BeliefQueryRepository | None, getattr(state, "belief_repo", None))
        engine = getattr(state, "belief_metabolism", None)
        if not belief_repo:
            return {
                "beliefs": [],
                "proto_beliefs": [],
                "ghosts": [],
                "somatic": None,
                "attractor_window": [],
                "spectral_margin": [],
                "ecosystem": None,
            }

        raw_beliefs = belief_repo.list_beliefs(agent_id)
        beliefs_list = []

        for b in raw_beliefs:
            if b.lifecycle_stage not in ("crystallized", "senescence"):
                continue

            events = belief_repo.get_events_for_belief(b.id)
            if b.ontological_mass >= 1.5:
                cat = "foundational"
            elif b.ontological_mass >= 1.2:
                cat = "ontological"
            else:
                cat = "methodological"

            beliefs_list.append(
                {
                    "id": b.id,
                    "label": b.label,
                    "statement": b.statement,
                    "category": cat,
                    "confidence": b.confidence,
                    "ontological_mass": b.ontological_mass,
                    "version": b.version,
                    "vector_16d": b.vector_16d,
                    "origin": b.origin,
                    "lifecycle_stage": b.lifecycle_stage,
                    "last_reinforced_at": b.last_reinforced_at.isoformat() if b.last_reinforced_at else None,
                    "updated_at": b.updated_at.isoformat() if b.updated_at else None,
                    "events": [serialize_belief_event(e) for e in events],
                }
            )

        raw_proposals = belief_repo.list_proposals(agent_id)
        proto_beliefs_list = []
        ghosts_list = []

        for p in raw_proposals:
            proposal_data = serialize_proposal(p)
            if p.status in ("pending", "refined"):
                proto_beliefs_list.append(proposal_data)
            elif p.status == "rejected":
                ghosts_list.append(proposal_data)

        somatic_state = None
        attractor_window = []
        spectral_margin = []

        if conversation_id:
            somatic = belief_repo.get_conversation_somatic_state(conversation_id)
            if somatic:
                somatic_state = {
                    "somatic_reservoir_ad": somatic.get("somatic_reservoir_ad", 0.0),
                    "matrix_warping": somatic.get("matrix_warping", 0.0),
                    "immunological_directive_active": bool(somatic.get("immunological_directive_active", 0)),
                }

                if engine:
                    try:
                        active = [
                            b
                            for b in raw_beliefs
                            if b.lifecycle_stage not in ("collapsed", "faded") and b.confidence >= 0.20
                        ]
                        collapsed = [
                            b for b in raw_beliefs if b.lifecycle_stage in ("collapsed", "faded") or b.confidence < 0.20
                        ]

                        attractors = []
                        used_ids = set()

                        if active:
                            # Top 2 by mass
                            sorted_mass = sorted(active, key=lambda b: b.ontological_mass, reverse=True)
                            for b in sorted_mass[:2]:
                                attractors.append(b)
                                used_ids.add(b.id)

                            # Bottom 2 by confidence among stressed
                            stressed = [b for b in active if b.confidence < 0.50 and b.id not in used_ids]
                            sorted_stressed = sorted(stressed, key=lambda b: b.confidence)
                            for b in sorted_stressed[:2]:
                                attractors.append(b)
                                used_ids.add(b.id)

                            # Top 2 remaining by confidence (no user vector available for UI view)
                            remaining = [b for b in active if b.id not in used_ids]
                            sorted_remaining = sorted(remaining, key=lambda b: b.confidence)
                            for b in sorted_remaining[:2]:
                                attractors.append(b)
                                used_ids.add(b.id)

                            attractor_window = [a.label for a in attractors]

                        spectral_margin = [b.label for b in collapsed]
                    except Exception as e:
                        logger.error("Error computing UI attractor window: %s", e)

        ecosystem = None
        if engine:
            try:
                ecosystem = await engine.compute_ecosystem_health(agent_id)
            except Exception as e:
                logger.error("Error computing ecosystem health: %s", e)

        return {
            "beliefs": beliefs_list,
            "proto_beliefs": proto_beliefs_list,
            "ghosts": ghosts_list,
            "somatic": somatic_state,
            "attractor_window": attractor_window,
            "spectral_margin": spectral_margin,
            "ecosystem": ecosystem,
        }

    async def get_belief_timeseries(
        self,
        belief_id: str,
        days: int = 30,
    ) -> BeliefResult:
        """Return bucketed mass/confidence timeseries for a belief chart.

        Bucketing: hourly if span <= 7 days, daily if span > 7 days.
        Within each bucket, the latest event's parsed mass/confidence is used.
        """
        state = self._state
        belief_repo = cast(BeliefQueryRepository | None, getattr(state, "belief_repo", None))
        if not belief_repo:
            return {"status": "error", "message": "Belief repository not initialized"}

        from datetime import datetime, timedelta

        belief = belief_repo.get_belief("symbia", belief_id)
        if not belief:
            return {"status": "error", "message": "Belief not found"}

        now = datetime.now(UTC)
        cutoff = now - timedelta(days=days)

        # Fetch events in the time window
        raw_events = belief_repo.get_events_for_belief(belief_id, limit=5000)

        # Parse events to extract mass/confidence from rationale
        parsed = []
        for event in raw_events:
            ts = event.timestamp
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff:
                continue
            mass, conf = _parse_event_rationale(event.rationale)
            parsed.append((ts, mass, conf))

        if not parsed:
            return {
                "belief_id": belief_id,
                "label": belief.label,
                "points": [],
                "span_days": 0,
                "bucket_size": "none",
            }

        # Sort by timestamp ascending
        parsed.sort(key=lambda x: x[0])

        span = parsed[-1][0] - parsed[0][0]
        span_days = span.total_seconds() / 86400.0

        # Choose bucket: hourly for <=7 days, daily for >7 days
        if span_days <= 7:
            bucket_seconds = 3600  # 1 hour
            bucket_size = "hour"
        else:
            bucket_seconds = 86400  # 1 day
            bucket_size = "day"

        # Assign each event to a bucket (integer floor of seconds since epoch / bucket_seconds)
        buckets: dict[int, tuple[datetime, float | None, float | None]] = {}
        for ts, mass, conf in parsed:
            bucket_key = int(ts.timestamp() / bucket_seconds)
            if bucket_key not in buckets or ts > buckets[bucket_key][0]:
                buckets[bucket_key] = (ts, mass, conf)

        # Build sorted output
        points = [
            {
                "timestamp": ts.isoformat(),
                "mass": mass,
                "confidence": conf,
            }
            for _k, (ts, mass, conf) in sorted(buckets.items())
        ]

        return {
            "belief_id": belief_id,
            "label": belief.label,
            "points": points,
            "span_days": round(span_days, 2),
            "bucket_size": bucket_size,
        }
