from backend.skills.metadata import SkillMeta
from backend.storage.repository import ConsolidationCheckpointRepository

from .base import ProcessingModule


class ConsolidationCheckpointModule(ProcessingModule):
    def __init__(
        self,
        checkpoint_repo: ConsolidationCheckpointRepository,
        consolidate_threshold: int = 15,
        memory_node_repo=None,
    ):
        self._checkpoint_repo = checkpoint_repo
        self._consolidate_threshold = consolidate_threshold
        self._memory_node_repo = memory_node_repo

    @property
    def name(self) -> str:
        return "consolidation_checkpoint"

    @property
    def skill_meta(self) -> SkillMeta:
        return SkillMeta(
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
            context_text = self._build_context_text(conversation_id, checkpoint)
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

    def _build_context_text(self, conversation_id: str, checkpoint: dict) -> str:
        human_summary = checkpoint.get("human_summary", "").strip()
        checkpoint_id = checkpoint.get("id")

        if self._memory_node_repo and checkpoint_id:
            try:
                nodes = self._memory_node_repo.get_nodes_by_checkpoint(checkpoint_id)
                if nodes:
                    top_nodes = sorted(
                        nodes, key=lambda n: n.get("intensity", 0), reverse=True
                    )[:3]

                    parts = []
                    for n in top_nodes:
                        ntype = n.get("node_type", n.get("type", "concept"))
                        text = n.get("intra_active_text", "")
                        if text:
                            parts.append(f"- [{ntype.upper()}] {text}")

                    keys = [
                        n.get("diffractive_key", "")
                        for n in nodes
                        if n.get("diffractive_key", "").strip()
                    ]
                    keys_str = ", ".join(keys[:5])

                    # Build context: prose summary first (if available), then node list
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
