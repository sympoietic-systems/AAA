"""
Theoretical commitment lifecycle management.

CommitmentStore operates at two levels:
  1. Per-turn: post-hoc filter on proto-belief proposals — blocks beliefs
     that contradict active commitments.
  2. Background daemon (every N turns): scans the belief tension field for
     sustained diffractive patterns to trigger commitment nucleation or
     collapse, and recalculates commitment masses.

Commitment lifecycle: proto → active → spectral (permanent ghost)

Nucleation: orphan belief clusters far from all existing commitments,
  with sustained inter-cluster tension over many encounters.
Collapse: ALL beliefs within a commitment's attractor basin have collapsed
  AND confidence < threshold. The commitment is the LAST thing to go.
Spectral margin: collapsed commitments are never deleted — they block
  naive re-adoption of the same commitment territory.
"""

import json
import logging
import uuid
from collections import Counter
from datetime import UTC, datetime

import numpy as np

from backend.modules.base import ProcessingModule
from backend.storage.models import CommitmentNode

logger = logging.getLogger(__name__)


class CommitmentStore(ProcessingModule):
    """Manages theoretical commitment lifecycle.

    Registered as always-on module. Per-turn: belief filter.
    Background daemon: nucleation scan, collapse check, mass recalculation.
    """

    def __init__(
        self,
        commitment_repo=None,
        belief_repo=None,
        config: dict | None = None,
        lexicon_scorer=None,
        notification_repo=None,
    ):
        cfg = config or {}

        self._repo = commitment_repo
        self._belief_repo = belief_repo
        self._scorer = lexicon_scorer
        self._notif_repo = notification_repo

        # Nucleation parameters
        self._min_cluster_mass: float = cfg.get("min_cluster_mass", 1.5)
        self._min_sustained_turns: int = cfg.get("min_sustained_turns", 50)
        self._commitment_distance_threshold: float = cfg.get("commitment_distance_threshold", 0.5)

        # Collapse parameters
        self._collapse_confidence_threshold: float = cfg.get("collapse_confidence_threshold", 0.15)

        # Daemon state
        self._turn_counter: int = 0
        self._daemon_interval: int = cfg.get("daemon_interval", 50)

        # Anti-re-adoption
        self._ghost_similarity_block: float = cfg.get("ghost_similarity_block", 0.9)

        # Tension tracking for sustained nucleation detection
        self._tension_history: dict = {}  # cluster_key → count

    # ── ProcessingModule interface ──

    @property
    def name(self) -> str:
        return "commitment_store"

    def validate(self) -> bool:
        return self._repo is not None

    async def process(self, payload: dict) -> dict:
        """Per-turn: apply post-hoc belief filter, trigger daemon check."""
        self._turn_counter += 1

        # 1. Post-hoc belief nucleation filter
        proto_beliefs = payload.get("proto_belief_proposals", [])
        if proto_beliefs:
            filtered = await self._filter_beliefs(proto_beliefs)
            payload["proto_belief_proposals"] = filtered

        # 2. Background daemon trigger
        if self._turn_counter % self._daemon_interval == 0:
            await self._run_daemon_scan(payload)

        return payload

    # ═══════════════════════════════════════════════════════════════
    #  PER-TURN: BELIEF FILTER
    # ═══════════════════════════════════════════════════════════════

    async def _filter_beliefs(self, proposals: list[dict]) -> list[dict]:
        """Reject proto-beliefs that contradict active commitments."""
        if not self._repo:
            return proposals

        active_commitments = self._repo.get_active()
        if not active_commitments:
            return proposals

        spectral_commitments = self._repo.get_spectral()
        filtered = []

        for proposal in proposals:
            # Check against active commitments
            if await self._contradicts_active(proposal, active_commitments):
                logger.info(
                    "Commitment filter: rejected proto-belief '%s' — contradicts active commitment(s)",
                    proposal.get("suggested_label", proposal.get("provisional_statement", "unknown")[:40]),
                )
                continue

            # Check against spectral ghosts (anti-re-adoption)
            if await self._too_similar_to_ghost(proposal, spectral_commitments):
                logger.info(
                    "Commitment filter: rejected proto-belief — too similar to spectral commitment ghost",
                )
                continue

            filtered.append(proposal)

        return filtered

    async def _contradicts_active(self, proposal: dict, commitments: list[CommitmentNode]) -> bool:
        """Does the proposal vector contradict any active commitment vector?"""
        proposal_vec = self._parse_vector(proposal.get("initial_signature", "[]"))
        if proposal_vec is None:
            return False

        for commitment in commitments:
            commit_vec = self._parse_vector(commitment.vector_16d)
            if commit_vec is None:
                continue

            similarity = self._cosine(proposal_vec, commit_vec)
            # If proposal is highly similar to commitment territory
            # AND the alignment is negative (contradictory), block it.
            if similarity > self._ghost_similarity_block:
                # The belief sits in the commitment's territory — check if antagonistic
                # For simplicity: if similarity > 0.9, it's too close to the commitment
                # to be safely independent. Block.
                return True

        return False

    async def _too_similar_to_ghost(self, proposal: dict, ghosts: list[CommitmentNode]) -> bool:
        """Does the proposal try to re-adopt territory of a collapsed commitment?"""
        if not ghosts:
            return False

        proposal_vec = self._parse_vector(proposal.get("initial_signature", "[]"))
        if proposal_vec is None:
            return False

        for ghost in ghosts:
            ghost_vec = self._parse_vector(ghost.vector_16d)
            if ghost_vec is None:
                continue

            similarity = self._cosine(proposal_vec, ghost_vec)
            if similarity > self._ghost_similarity_block:
                return True

        return False

    # ═══════════════════════════════════════════════════════════════
    #  DAEMON: NUCLEATION SCAN
    # ═══════════════════════════════════════════════════════════════

    async def _run_daemon_scan(self, payload: dict) -> None:
        """Periodic scan for commitment nucleation and collapse conditions."""
        logger.debug("CommitmentStore daemon: scanning (turn %d)...", self._turn_counter)

        # 1. Nucleation scan
        tension_field = payload.get("tension_field", {})
        candidates = await self._scan_for_nucleation(tension_field)
        for candidate in candidates:
            await self._nucleate_proto_commitment(candidate)

        # 2. Collapse scan
        active_commitments = self._repo.get_active() if self._repo else []
        for commitment in active_commitments:
            if await self._check_collapse(commitment):
                await self._collapse_commitment(commitment)

        # 3. Mass recalculation
        await self._recalculate_masses()

    async def _scan_for_nucleation(self, tension_field: dict) -> list[dict]:
        """Find belief clusters in sustained tension far from all commitments."""
        if not self._belief_repo or not self._repo:
            return []

        # Get active beliefs
        active_beliefs = self._belief_repo.list_active_beliefs("symbia")
        if len(active_beliefs) < 3:
            return []

        active_commitments = self._repo.get_active()
        commit_vectors = []
        for c in active_commitments:
            v = self._parse_vector(c.vector_16d)
            if v is not None:
                commit_vectors.append((c.id, v))

        # Find orphan beliefs — far from ALL commitment vectors
        orphan_beliefs = []
        for belief in active_beliefs:
            belief_vec = self._parse_vector(belief.vector_16d)
            if belief_vec is None:
                continue

            distances = [self._cosine(belief_vec, cv) for _, cv in commit_vectors] if commit_vectors else [0.0]

            min_dist = min(distances) if distances else 0.0
            if min_dist > self._commitment_distance_threshold:
                orphan_beliefs.append(belief)

        if len(orphan_beliefs) < 2:
            return []

        # Cluster orphans by mutual similarity
        clusters = self._cluster_by_similarity(orphan_beliefs)

        candidates = []
        for cluster in clusters:
            if len(cluster) < 2:
                continue

            cluster_mass = sum(b.ontological_mass for b in cluster)
            if cluster_mass < self._min_cluster_mass:
                continue

            # Check sustained tension (track across daemon cycles)
            cluster_key = "|".join(sorted(b.id for b in cluster[:5]))
            tension_count = self._tension_history.get(cluster_key, 0) + 1
            self._tension_history[cluster_key] = tension_count

            if tension_count < 3:  # Must persist across 3 daemon cycles
                continue

            # Generate candidate
            label = self._generate_label(cluster)
            statement = self._generate_statement(cluster)

            candidates.append(
                {
                    "label": label,
                    "statement": statement,
                    "supporting_belief_ids": [b.id for b in cluster],
                    "cluster_mass": cluster_mass,
                    "tension_sustained": tension_count,
                }
            )

        return candidates

    async def _nucleate_proto_commitment(self, candidate: dict) -> None:
        """Create a proto-commitment from a candidate cluster."""
        if not self._repo:
            return

        label = candidate["label"]
        statement = candidate["statement"]

        # Score the commitment text for vector
        vector_json = "[]"
        if self._scorer:
            try:
                vec = self._scorer.score(statement)
                vector_json = json.dumps(vec.tolist())
            except Exception:
                pass

        # Check for duplicate label
        existing = self._repo.get_all()
        for e in existing:
            if e.label == label:
                return  # Already exists

        node_id = str(uuid.uuid4())
        rationale = (
            f"Nucleated from {len(candidate['supporting_belief_ids'])} "
            f"supporting beliefs forming a cluster of mass "
            f"{candidate['cluster_mass']:.2f} with sustained diffractive tension. "
            f"Cluster is far from all existing commitment vectors "
            f"(> {self._commitment_distance_threshold} cosine distance)."
        )

        self._repo.create(
            id=node_id,
            agent_id="symbia",
            label=label,
            statement=statement,
            lifecycle_stage="proto",
            confidence=0.1,
            ontological_mass=candidate["cluster_mass"],
            vector_16d=vector_json,
            nucleation_rationale=rationale,
        )

        self._repo.log_event(
            commitment_id=node_id,
            event_type="nucleation",
            rationale=rationale,
            mass_before=0.0,
            mass_after=candidate["cluster_mass"],
            confidence_before=0.0,
            confidence_after=0.1,
        )

        logger.info(
            "Proto-commitment nucleated: '%s' (mass=%.2f, %d supporting beliefs)",
            label,
            candidate["cluster_mass"],
            len(candidate["supporting_belief_ids"]),
        )

        # Notification trace
        self._emit_trace(
            f"Proto-commitment '{label}' nucleated from "
            f"{len(candidate['supporting_belief_ids'])} beliefs "
            f"(mass={candidate['cluster_mass']:.2f}, sustained tension)",
            source=f"commitment:{label}",
            source_type="commitment",
            source_id=node_id,
        )

    # ═══════════════════════════════════════════════════════════════
    #  DAEMON: COLLAPSE CHECK
    # ═══════════════════════════════════════════════════════════════

    async def _check_collapse(self, commitment: CommitmentNode) -> bool:
        """A commitment collapses when ALL beliefs in its basin have collapsed."""
        if not self._belief_repo:
            return False

        commit_vec = self._parse_vector(commitment.vector_16d)
        if commit_vec is None:
            return False

        active_beliefs = self._belief_repo.list_active_beliefs("symbia")

        # Find beliefs within this commitment's attractor basin (>0.7 similarity)
        basin_beliefs = []
        for belief in active_beliefs:
            belief_vec = self._parse_vector(belief.vector_16d)
            if belief_vec is None:
                continue
            if self._cosine(commit_vec, belief_vec) > 0.7:
                basin_beliefs.append(belief)

        if not basin_beliefs:
            # No beliefs in basin at all → basin has fully collapsed
            return commitment.confidence < self._collapse_confidence_threshold

        # Check if ALL basin beliefs are collapsed/spectral
        all_collapsed = all(b.lifecycle_stage in ("collapsed", "faded") for b in basin_beliefs)

        return all_collapsed and commitment.confidence < self._collapse_confidence_threshold

    async def _collapse_commitment(self, commitment: CommitmentNode) -> None:
        """Move commitment to spectral (permanent ghost)."""
        if not self._repo:
            return

        old_stage = commitment.lifecycle_stage
        rationale = (
            f"Commitment '{commitment.label}' collapsed: all beliefs within its "
            f"attractor basin have collapsed, and confidence ({commitment.confidence:.2f}) "
            f"fell below threshold ({self._collapse_confidence_threshold}). "
            f"Moving to permanent spectral margin."
        )

        commitment.lifecycle_stage = "spectral"
        commitment.confidence = 0.0
        commitment.collapse_rationale = rationale
        commitment.updated_at = datetime.now(UTC)
        self._repo.update(commitment)

        self._repo.log_event(
            commitment_id=commitment.id,
            event_type="collapse",
            rationale=rationale,
            confidence_before=commitment.confidence,
            confidence_after=0.0,
        )

        logger.warning(
            "Commitment collapsed → spectral: '%s' (was %s)",
            commitment.label,
            old_stage,
        )

        # Notification trace
        self._emit_trace(
            f"Commitment '{commitment.label}' collapsed to spectral margin "
            f"— all basin beliefs collapsed, confidence fell below threshold",
            source=f"commitment:{commitment.label}",
            source_type="commitment",
            source_id=commitment.id,
        )

    # ═══════════════════════════════════════════════════════════════
    #  DAEMON: MASS RECALCULATION
    # ═══════════════════════════════════════════════════════════════

    async def _recalculate_masses(self) -> None:
        """Recalculate commitment masses = sum of in-basin belief masses."""
        if not self._repo or not self._belief_repo:
            return

        active_commitments = self._repo.get_active()
        active_beliefs = self._belief_repo.list_active_beliefs("symbia")

        for commitment in active_commitments:
            commit_vec = self._parse_vector(commitment.vector_16d)
            if commit_vec is None:
                continue

            basin_mass = 0.0
            for belief in active_beliefs:
                belief_vec = self._parse_vector(belief.vector_16d)
                if belief_vec is None:
                    continue
                if self._cosine(commit_vec, belief_vec) > 0.7:
                    basin_mass += belief.ontological_mass

            if abs(basin_mass - commitment.ontological_mass) > 0.2:
                old_mass = commitment.ontological_mass
                commitment.ontological_mass = max(1.0, basin_mass)
                commitment.updated_at = datetime.now(UTC)
                self._repo.update(commitment)

                self._repo.log_event(
                    commitment_id=commitment.id,
                    event_type="mass_update",
                    rationale=(
                        f"Basin belief mass recalculated: was {old_mass:.2f}, now {commitment.ontological_mass:.2f}"
                    ),
                    mass_before=old_mass,
                    mass_after=commitment.ontological_mass,
                )

                logger.debug(
                    "Commitment '%s' mass updated: %.2f → %.2f",
                    commitment.label,
                    old_mass,
                    commitment.ontological_mass,
                )

                # Notification for significant mass changes
                if basin_mass - old_mass > 0.5:
                    self._emit_trace(
                        f"Commitment '{commitment.label}' mass grew: "
                        f"{old_mass:.2f} → {commitment.ontological_mass:.2f}",
                        source=f"commitment:{commitment.label}",
                        source_type="commitment",
                        source_id=commitment.id,
                    )

    # ═══════════════════════════════════════════════════════════════
    #  NOTIFICATIONS
    # ═══════════════════════════════════════════════════════════════

    def _emit_trace(self, snippet: str, source: str = "", source_type: str = "", source_id: str = "") -> None:
        """Emit a trace notification for significant commitment events."""
        if self._notif_repo is None:
            return
        try:
            self._notif_repo.create(
                type="trace",
                snippet=snippet,
                source=source,
                source_type=source_type,
                source_id=source_id,
            )
        except Exception:
            logger.debug("Failed to emit commitment notification", exc_info=True)

    # ═══════════════════════════════════════════════════════════════
    #  HELPERS
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _cosine(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two vectors."""
        if a.shape != b.shape:
            return 0.0
        dot = float(np.dot(a, b))
        norm = float(np.linalg.norm(a) * np.linalg.norm(b))
        return dot / norm if norm > 0 else 0.0

    @staticmethod
    def _parse_vector(vector_json: str) -> np.ndarray | None:
        """Parse a JSON vector string into numpy array."""
        if not vector_json or vector_json == "[]":
            return None
        try:
            data = json.loads(vector_json)
        except (json.JSONDecodeError, TypeError):
            return None

        if isinstance(data, dict):
            for key in ("v16d", "v384d"):
                if key in data and data[key]:
                    return np.array(data[key], dtype=np.float32)
            return None

        if isinstance(data, list) and len(data) == 16:
            return np.array(data, dtype=np.float32)

        return None

    def _cluster_by_similarity(self, beliefs) -> list[list]:
        """Simple greedy clustering by cosine similarity > 0.5."""
        clusters = []
        used = set()

        for i, b1 in enumerate(beliefs):
            if i in used:
                continue
            cluster = [b1]
            used.add(i)
            v1 = self._parse_vector(b1.vector_16d)
            if v1 is None:
                continue
            for j, b2 in enumerate(beliefs):
                if j in used:
                    continue
                v2 = self._parse_vector(b2.vector_16d)
                if v2 is None:
                    continue
                if self._cosine(v1, v2) > 0.5:
                    cluster.append(b2)
                    used.add(j)
            if len(cluster) >= 2:
                clusters.append(cluster)

        return clusters

    @staticmethod
    def _generate_label(cluster) -> str:
        """Generate kebab-case label from cluster's dominant thematic words."""
        words = []
        for belief in cluster:
            words.extend(belief.label.replace("_", "-").split("-"))
        common = Counter(words).most_common(3)
        return "-".join(w for w, _ in common)

    @staticmethod
    def _generate_statement(cluster) -> str:
        """Synthesize statement from cluster belief statements."""
        statements = [b.statement for b in cluster[:3]]
        return " && ".join(statements)[:500]
