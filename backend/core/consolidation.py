"""Conversation consolidation mixin for the Dream Daemon."""

import logging
from datetime import datetime, timezone

from backend.core.sedimentation import (
    parse_sedimentation_yaml,
    merge_nodes,
    build_compact_node_summary,
)

logger = logging.getLogger(__name__)


class ConsolidationMixin:
    """Handles pending conversation consolidation, re-consolidation, and diffractive tag syncing."""

    async def consolidate_pending_conversations(self) -> None:
        if not self.conversation_repo or not self.checkpoint_repo:
            return

        memory_node_repo = getattr(self.app_state, "memory_node_repo", None)

        convs = self.conversation_repo.list_all()
        for c in convs:
            needs_reconsolidation = False

            # Backfill: parse existing checkpoint summaries into memory nodes (no LLM cost)
            if memory_node_repo:
                existing_nodes = memory_node_repo.get_nodes(c.id)
                if not existing_nodes:
                    checkpoint = self.checkpoint_repo.get_latest(c.id)
                    if checkpoint and checkpoint.get("summary", "").strip():
                        parsed_nodes, _ = parse_sedimentation_yaml(checkpoint["summary"])
                        if parsed_nodes:
                            try:
                                checkpoint_id = checkpoint["id"]
                                memory_node_repo.delete_by_conversation(c.id)
                                memory_node_repo.save_nodes(c.id, checkpoint_id, parsed_nodes)
                                self._sync_diffractive_tags(c.id, parsed_nodes)
                                logger.info(
                                    "Backfilled %d memory nodes from existing checkpoint for %s",
                                    len(parsed_nodes), c.id,
                                )
                                continue
                            except Exception as e:
                                logger.warning(
                                    "Failed to backfill memory nodes for %s: %s", c.id, e,
                                )
                        else:
                            needs_reconsolidation = True
                            self.conversation_repo.mark_requires_consolidation(c.id, True)
                            logger.info(
                                "Flagged %s for re-consolidation (unparseable old-format checkpoint)",
                                c.id,
                            )

            requires_consolidation = getattr(c, "requires_consolidation", 0)

            if requires_consolidation:
                # Rule 3: Explicit flag — always consolidate, no conditions
                pass
            elif needs_reconsolidation:
                # Old-format backfill — also bypass all checks
                pass
            else:
                # Compute message counts for proactive rules
                checkpoint = self.checkpoint_repo.get_latest(c.id)
                checkpoint_msg_count = checkpoint["message_count"] if checkpoint else 0
                total_msg_count = self.message_repo.count_messages(c.id)
                new_msg_count = total_msg_count - checkpoint_msg_count

                if new_msg_count <= 0:
                    continue

                last_time = getattr(c, "last_consolidated_at", None)
                if last_time:
                    # Rule 1: Previously consolidated — consolidate if >cooldown AND ≥N new messages
                    if last_time.tzinfo is None:
                        last_time = last_time.replace(tzinfo=timezone.utc)
                    elapsed = datetime.now(timezone.utc) - last_time
                    if elapsed.total_seconds() < self.consolidate_cooldown_hours * 3600:
                        continue
                    if new_msg_count < self.consolidate_min_new_messages:
                        continue
                else:
                    # Rule 2: Never consolidated — consolidate if ≥N total messages
                    if total_msg_count < self.consolidate_first_time_threshold:
                        continue

            # Perform incremental consolidation
            try:
                await self._consolidate_conversation(c)
            except Exception as e:
                logger.exception("Failed to consolidate conversation %s: %s", c.id, e)

    async def _consolidate_conversation(self, conversation) -> None:
        conversation_id = conversation.id
        checkpoint = self.checkpoint_repo.get_latest(conversation_id)

        total_msg_count = self.message_repo.count_messages(conversation_id)
        checkpoint_msg_count = checkpoint["message_count"] if checkpoint else 0

        # Detect re-consolidation: old-format checkpoint with no structured memory nodes
        memory_node_repo = getattr(self.app_state, "memory_node_repo", None)
        existing_nodes = memory_node_repo.get_nodes(conversation_id) if memory_node_repo else []
        is_reconsolidation = bool(checkpoint and not existing_nodes and checkpoint.get("summary"))

        if is_reconsolidation:
            # Fetch ALL messages for a full re-sedimentation pass
            new_messages = self.message_repo.get_messages_since(conversation_id, 0)
            logger.info(
                "Re-consolidating %s from scratch (old-format checkpoint, %d total messages)",
                conversation_id, total_msg_count,
            )
        else:
            new_messages = self.message_repo.get_messages_since(conversation_id, checkpoint_msg_count)

        if not new_messages:
            self.conversation_repo.mark_requires_consolidation(conversation_id, False)
            self.conversation_repo.update_last_consolidated_at(conversation_id)
            logger.info(
                "No new messages since last checkpoint for %s, cleared requires_consolidation flag.",
                conversation_id,
            )
            return

        # Format new messages text
        formatted_lines = []
        for msg in new_messages:
            speaker_label = "Human" if msg.speaker == "human" else "Agent"
            formatted_lines.append(f"{speaker_label}: {msg.content}")
        new_messages_text = "\n".join(formatted_lines)

        # Build prompt
        if existing_nodes:
            compact_summary = build_compact_node_summary(existing_nodes)
            prompt_text = (
                "We are incrementally updating the intra-active memory nodes from a conversation.\n\n"
                "Existing Memory Nodes (preserve unchanged ones by not including them in output):\n"
                f"\"\"\"\n{compact_summary}\n\"\"\"\n\n"
                "New Messages to integrate:\n"
                f"\"\"\"\n{new_messages_text}\n\"\"\"\n\n"
                "Return ONLY new nodes and nodes whose stance, intensity, or shape has shifted due to the new messages. "
                "Use existing node IDs for modifications. Omit nodes that are unchanged."
            )
        else:
            prompt_text = (
                "Perform sedimentation on this conversation encounter.\n\n"
                "\"\"\"\n{new_messages_text}\n\"\"\"\n"
            ).format(new_messages_text=new_messages_text)

        bg_engine = getattr(self.app_state, "background_engine", None)
        if not bg_engine:
            logger.warning("No background engine available for consolidation")
            return

        # ── Call 1: Memory nodes (YAML) ──
        logger.info(
            "Running node consolidation for conversation %s (messages offset: %d)",
            conversation_id, checkpoint_msg_count,
        )
        node_result = await bg_engine.run("consolidate", {"text": prompt_text})

        raw_output = node_result.get("content", "").strip()
        model_used = node_result.get("model", "")

        if not raw_output:
            logger.warning("Empty consolidation result for %s", conversation_id)
            self.conversation_repo.mark_requires_consolidation(conversation_id, False)
            self.conversation_repo.update_last_consolidated_at(conversation_id)
            return

        # ── Call 2: Human-readable summary (prose) ──
        summary_result = await bg_engine.run("conversation_summary", {"text": new_messages_text})
        human_summary = summary_result.get("content", "").strip()
        summary_model = summary_result.get("model", model_used)
        if human_summary:
            logger.info("Generated human summary for %s (%d chars)", conversation_id, len(human_summary))
        else:
            logger.warning("Empty summary result for %s", conversation_id)

        # Save checkpoint with both raw nodes output and human summary
        self.checkpoint_repo.save(
            conversation_id, total_msg_count, raw_output, model_used,
            human_summary=human_summary,
        )
        logger.info("Consolidation checkpoint saved for %s (%d msgs)", conversation_id, total_msg_count)

        # Parse structured nodes
        parsed_nodes, parse_tier = parse_sedimentation_yaml(raw_output)

        # Merge with existing nodes
        merged_nodes = merge_nodes(existing_nodes, parsed_nodes)

        # Store structured nodes
        if memory_node_repo and merged_nodes:
            try:
                # Get new checkpoint ID for linking
                new_checkpoint = self.checkpoint_repo.get_latest(conversation_id)
                checkpoint_id = new_checkpoint["id"] if new_checkpoint else 0
                memory_node_repo.delete_by_conversation(conversation_id)
                memory_node_repo.save_nodes(conversation_id, checkpoint_id, merged_nodes)
            except Exception as e:
                logger.exception("Failed to save memory nodes for %s: %s", conversation_id, e)

        # Diffractive keys from merged nodes (replace old keyword tags)
        self._sync_diffractive_tags(conversation_id, merged_nodes)

        # Clear flag and update timestamp
        self.conversation_repo.mark_requires_consolidation(conversation_id, False)
        self.conversation_repo.update_last_consolidated_at(conversation_id)

        logger.info(
            "Consolidated %s: %d nodes (tier %d, %d chars raw output)",
            conversation_id, len(merged_nodes), parse_tier, len(raw_output),
        )

    def _sync_diffractive_tags(self, conversation_id: str, nodes: list[dict]) -> None:
        """Remove old keyword/diffractive tags and re-add from merged nodes."""
        # Remove old keyword and diffractive tags
        existing_tags = self.conversation_repo.get_tags(conversation_id)
        for t in existing_tags:
            if t["tag_type"] in ("keyword", "diffractive"):
                try:
                    self.conversation_repo.remove_tag(conversation_id, t["tag"])
                except Exception:
                    pass

        # Add diffractive keys as tags
        seen_keys = set()
        for node in nodes:
            dk = node.get("diffractive_key", "").strip()
            if dk and dk not in seen_keys:
                seen_keys.add(dk)
                try:
                    self.conversation_repo.add_tag(conversation_id, dk, "diffractive")
                except Exception:
                    pass

        if seen_keys:
            logger.info(
                "Synced %d diffractive keys for conversation %s",
                len(seen_keys), conversation_id,
            )
