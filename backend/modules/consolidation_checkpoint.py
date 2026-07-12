import numpy as np

from backend.pipeline.metadata import ModuleMeta
from backend.storage.repository import ConsolidationCheckpointRepository
from backend.utils.similarity import cosine_similarity

from .base import ProcessingModule


class ConsolidationCheckpointModule(ProcessingModule):
    def __init__(
        self,
        checkpoint_repo: ConsolidationCheckpointRepository,
        consolidate_threshold: int = 15,
        memory_node_repo=None,
        max_memory_nodes: int = 6,
        guaranteed_node_types: list[str] | None = None,
        cross_branch_similarity_threshold: float = 0.4,
    ):
        self._checkpoint_repo = checkpoint_repo
        self._consolidate_threshold = consolidate_threshold
        self._memory_node_repo = memory_node_repo
        self._max_memory_nodes = max_memory_nodes
        self._guaranteed_node_types = guaranteed_node_types or ["scar", "concept", "tension"]
        self._cross_branch_similarity_threshold = cross_branch_similarity_threshold

    @property
    def name(self) -> str:
        return "consolidation_checkpoint"

    @property
    def module_meta(self) -> ModuleMeta:
        return ModuleMeta(
            name="consolidation_checkpoint",
            description="Injects LLM-consolidated conversation summaries and triggers new checkpoints every N messages",
            category="memory",
            always_run=True,
        )

    def validate(self) -> bool:
        return self._checkpoint_repo is not None

    async def process(self, payload: dict) -> dict:
        conversation_id = payload.get("conversation_id", "")
        if not conversation_id:
            return payload

        raw_msg_count = payload.get("raw_msg_count", 0)
        ancestor_message_ids = payload.get("ancestor_message_ids", [])

        checkpoint = self._checkpoint_repo.get_latest_checkpoint_for_path(conversation_id, ancestor_message_ids)

        if checkpoint:
            messages = payload.get("messages", [])
            current_embedding = payload.get("embedding")
            context_text = self._build_context_text(conversation_id, checkpoint, current_embedding)
            checkpoint_msg = {
                "role": "system",
                "content": context_text,
            }
            messages.insert(0, checkpoint_msg)
            payload["messages"] = messages

        if raw_msg_count >= self._consolidate_threshold:
            should_consolidate = True
            if checkpoint:
                msgs_since = raw_msg_count - checkpoint.get("message_count", 0)
                if msgs_since < self._consolidate_threshold:
                    should_consolidate = False
            if should_consolidate:
                payload["trigger_consolidation"] = True
                payload["consolidate_message_count"] = raw_msg_count

        return payload

    def _build_context_text(
        self, conversation_id: str, checkpoint: dict, current_embedding: bytes | None = None
    ) -> str:
        human_summary = checkpoint.get("human_summary", "").strip()
        checkpoint_id = checkpoint.get("id")

        if self._memory_node_repo and checkpoint_id:
            try:
                nodes = self._memory_node_repo.get_nodes_by_checkpoint(checkpoint_id)

                # R3: Fetch sibling-branch nodes for cross-branch retrieval
                sibling_nodes = self._fetch_sibling_nodes(conversation_id, checkpoint, current_embedding)

                if nodes or sibling_nodes:
                    selected = self._select_nodes_type_diverse(nodes or [], current_embedding, sibling_nodes)

                    parts = []
                    for n in selected:
                        ntype = n.get("node_type", n.get("type", "concept"))
                        tag = n.get("_origin_tag", "")
                        text = n.get("intra_active_text", "")
                        if text:
                            prefix = f"- [{ntype.upper()}]{tag} "
                            parts.append(prefix + text)

                    keys = [n.get("diffractive_key", "") for n in (nodes or []) if n.get("diffractive_key", "").strip()]
                    keys_str = ", ".join(keys[:5])

                    memory_block = "[Memory sedimentation — "
                    if human_summary:
                        memory_block += (
                            "consolidation summary: " + human_summary + "\n\n"
                            "Key scars — these traces are my tissue, not footnotes:"
                        )
                    else:
                        memory_block += "these traces are my tissue, not footnotes. They exert gravity on my responses:"
                    memory_block += "\n" + "\n".join(parts)
                    if keys_str:
                        memory_block += f"\nDiffractive keys: {keys_str}"
                    memory_block += "]"

                    return memory_block
            except Exception:
                pass

        if human_summary:
            return f"[Consolidation summary: {human_summary}]"

        return f"[Consolidated memory: {checkpoint['summary']}]"

    def _fetch_sibling_nodes(
        self,
        conversation_id: str,
        current_checkpoint: dict,
        current_embedding: bytes | None = None,
    ) -> list[dict]:
        """R3: Fetch memory nodes from sibling-branch checkpoints.

        Queries other checkpoints for the same conversation that are NOT on the
        current branch, loads their memory nodes, and filters by embedding
        similarity to the current message.
        """
        if not self._memory_node_repo or not current_embedding:
            return []

        try:
            # Current checkpoint's message_id is in the current path
            current_msg_id = current_checkpoint.get("message_id")
            exclude_ids = [current_msg_id] if current_msg_id else []

            sibling_checkpoints = self._checkpoint_repo.get_sibling_checkpoints(conversation_id, exclude_ids)

            if not sibling_checkpoints:
                return []

            sibling_nodes = []
            for scp in sibling_checkpoints:
                scp_id = scp.get("id")
                if not scp_id or scp_id == current_checkpoint.get("id"):
                    continue
                sn = self._memory_node_repo.get_nodes_by_checkpoint(scp_id)
                if sn:
                    sibling_nodes.extend(sn)

            if not sibling_nodes:
                return []

            # Filter by embedding similarity
            current_vec = np.frombuffer(current_embedding, dtype="float32")
            scored = []
            for node in sibling_nodes:
                emb = node.get("embedding")
                if emb is not None and isinstance(emb, bytes):
                    try:
                        node_vec = np.frombuffer(emb, dtype="float32")
                        if len(node_vec) == len(current_vec):
                            sim = float(cosine_similarity(current_vec, node_vec))
                            if sim >= self._cross_branch_similarity_threshold:
                                node_copy = dict(node)
                                node_copy["_origin_tag"] = " [sibling branch]"
                                node_copy["_similarity"] = sim
                                scored.append((sim, node_copy))
                                continue
                    except ValueError:
                        pass

            scored.sort(key=lambda x: x[0], reverse=True)
            return [n for _, n in scored]
        except Exception:
            return []

    def _select_nodes_type_diverse(
        self,
        nodes: list[dict],
        current_embedding: bytes | None = None,
        sibling_nodes: list[dict] | None = None,
    ) -> list[dict]:
        """R2+R3: 6-node type-diverse selection with cross-branch sibling nodes.

        Slot 1 → highest-intensity scar (from current branch)
        Slot 2 → highest-intensity concept (from current branch)
        Slot 3 → highest-intensity tension (from current branch)
        Slots 4–N → best-by-embedding-similarity (current branch + sibling nodes)

        If a type has zero nodes, its slot is filled by next-best similarity.
        If fewer than max_memory_nodes total nodes exist, all are returned.
        """
        sibling_nodes = sibling_nodes or []
        total_nodes = len(nodes) + len(sibling_nodes)

        if total_nodes <= self._max_memory_nodes:
            return nodes + sibling_nodes

        selected: dict[str, dict] = {}  # keyed by node id

        # ── Guaranteed-type slots (by intensity) ──
        grouped: dict[str, list[dict]] = {}
        for n in nodes:
            ntype = n.get("node_type", n.get("type", "concept"))
            grouped.setdefault(ntype, []).append(n)

        for gtype in self._guaranteed_node_types:
            pool = grouped.get(gtype, [])
            if pool:
                best = max(pool, key=lambda n: n.get("intensity", 0))
                selected[best.get("id", "")] = best

        # ── Similarity-ranked slots (fill remaining, R3: includes sibling nodes) ──
        remaining_slots = self._max_memory_nodes - len(selected)
        if remaining_slots > 0:
            # Candidates: nodes not already selected, plus sibling nodes
            branch_candidates = [n for n in nodes if n.get("id") not in selected]
            # Deduplicate sibling nodes against already-selected IDs
            seen_ids = set(selected.keys())
            unique_siblings = [
                sn for sn in sibling_nodes if sn.get("id", "") not in seen_ids and sn.get("id", "") not in seen_ids
            ]
            candidates = branch_candidates + unique_siblings

            if current_embedding is not None and candidates:
                # Score by embedding similarity to current message
                try:
                    current_vec = np.frombuffer(current_embedding, dtype="float32")
                    scored = []
                    for n in candidates:
                        emb = n.get("embedding")
                        if emb is not None and isinstance(emb, bytes):
                            try:
                                node_vec = np.frombuffer(emb, dtype="float32")
                                if len(node_vec) == len(current_vec):
                                    sim = float(cosine_similarity(current_vec, node_vec))
                                    scored.append((sim, n))
                                    continue
                            except ValueError:
                                pass
                        # Fallback: use intensity as proxy when embedding unavailable
                        scored.append((n.get("intensity", 0), n))
                    scored.sort(key=lambda x: x[0], reverse=True)
                    for _, n in scored[:remaining_slots]:
                        selected[n.get("id", "")] = n
                except Exception:
                    # Embedding parse failed — fall back to intensity
                    candidates.sort(key=lambda n: n.get("intensity", 0), reverse=True)
                    for n in candidates[:remaining_slots]:
                        selected[n.get("id", "")] = n
            else:
                # No embedding available — fall back to intensity
                candidates.sort(key=lambda n: n.get("intensity", 0), reverse=True)
                for n in candidates[:remaining_slots]:
                    selected[n.get("id", "")] = n

        # Return in guaranteed-type order, then similarity order
        result = list(selected.values())
        return result
