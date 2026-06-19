"""
Conversation Export Service
Assembles complete conversation data into a machine-parseable Markdown document
designed for LLM consumption — preserving tree structure, branches, cross-links,
notes, memory nodes, and metadata.
"""

from datetime import datetime, timezone


class ExportService:
    """Build a Markdown export of a full conversation with all branches and links."""

    INSTRUCTIONS = """\
> **HOW TO READ THIS DOCUMENT (for LLM consumption)**
>
> This is a complete conversation export with tree structure, branches, and cross-links
> from the Symbia autopoietic agent system.
>
> **Message identifiers** use the format `[MSG:123]` throughout this document.
> These numeric IDs correspond to the messages listed in §5 MESSAGES below.
>
> **Tree structure** is shown in §4 CONVERSATION TREE as:
>   - An indented text tree showing parent→child relationships
>   - An adjacency list (YAML) showing all edges — use this for machine parsing
>   - Cross-links (resonance / diffractive edges) listed separately
>
> **Branches** occur when a single message has multiple children.
> Follow each branch independently; they represent divergent conversational paths.
> Cross-links connect nodes across branches (lateral connections).
>
> **Notes** in §6 are attached to specific messages by `[MSG:123]` ID.
>
> **To reconstruct the conversation:**
>   1. Read §2 CONVERSATION SUMMARY for a high-level overview
>   2. Read §3 MEMORY NODES for long-term extracted concepts
>   3. Start at root messages (parent_message_id = null) in §4 adjacency list
>   4. Follow parent→child edges through branches
>   5. Consider cross-links as lateral resonances between branches
>   6. Consult §6 NOTES for annotations on specific messages"""

    @staticmethod
    def build_export(
        conv: dict,
        tags: list[dict],
        checkpoint: dict | None,
        messages: list,
        links: list,
        notes: list[dict],
        memory_nodes: list[dict],
    ) -> str:
        """Assemble the full export Markdown string.

        Args:
            conv: Conversation dict (id, title, created_at, updated_at, message_count, agent_id)
            tags: List of {tag, tag_type} dicts
            checkpoint: Latest consolidation checkpoint dict or None
            messages: List of Message dataclasses
            links: List of MessageLink dataclasses
            notes: List of note dicts
            memory_nodes: List of memory node dicts
        """
        parts: list[str] = []

        # --- YAML frontmatter (machine-readable metadata) ---
        parts.append(ExportService._build_frontmatter(conv, tags, messages, links, notes, memory_nodes))

        # --- Title ---
        title = conv.get("title", "") or "Untitled Conversation"
        parts.append(f"# Conversation: {title}\n")

        # --- §0 Instructions ---
        parts.append("---\n")
        parts.append("## §0 HOW TO READ THIS DOCUMENT\n")
        parts.append(ExportService.INSTRUCTIONS)
        parts.append("---\n")

        # --- §1 Metadata ---
        parts.append("## §1 METADATA\n")
        parts.append(ExportService._build_metadata(conv, tags))
        parts.append("")

        # --- §2 Conversation Summary ---
        parts.append("## §2 CONVERSATION SUMMARY\n")
        parts.append(ExportService._build_summary(conv, checkpoint, messages))
        parts.append("")

        # --- §3 Memory Nodes ---
        parts.append("## §3 MEMORY NODES\n")
        parts.append(ExportService._build_memory_nodes(memory_nodes))
        parts.append("")

        # --- §4 Conversation Tree ---
        parts.append("## §4 CONVERSATION TREE\n")
        parts.append(ExportService._build_tree(messages, links))
        parts.append("")

        # --- §5 Messages ---
        parts.append("## §5 MESSAGES\n")
        parts.append(ExportService._build_messages(messages))
        parts.append("")

        # --- §6 Notes ---
        parts.append("## §6 NOTES\n")
        parts.append(ExportService._build_notes(notes))
        parts.append("")

        # --- §7 Export Metadata ---
        parts.append("## §7 EXPORT METADATA\n")
        parts.append(ExportService._build_export_meta(conv, messages, links, notes, memory_nodes))

        return "\n".join(parts)

    # ── private builders ──────────────────────────────────────────────

    @staticmethod
    def _build_frontmatter(conv, tags, messages, links, notes, memory_nodes) -> str:
        tag_list = ", ".join(t["tag"] for t in tags) if tags else ""
        lines = [
            "---",
            f'conversation_id: "{conv["id"]}"',
            f'title: "{conv.get("title", "")}"',
            f'created_at: "{conv.get("created_at", "")}"',
            f'updated_at: "{conv.get("updated_at", "")}"',
            f"message_count: {len(messages)}",
            f'agent_id: "{conv.get("agent_id", "symbia")}"',
            f'tags: [{tag_list}]',
            f"cross_link_count: {len(links)}",
            f"note_count: {len(notes)}",
            f"memory_node_count: {len(memory_nodes)}",
            f'export_format_version: "1.0"',
            f'exported_at: "{datetime.now(timezone.utc).isoformat()}"',
            "---",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def _build_metadata(conv, tags) -> str:
        lines = [
            "| Field | Value |",
            "|---|---|",
            f"| Conversation ID | `{conv['id']}` |",
            f"| Title | {conv.get('title', 'Untitled')} |",
            f"| Created | {conv.get('created_at', '')} |",
            f"| Updated | {conv.get('updated_at', '')} |",
            f"| Message Count | {conv.get('message_count', 0)} |",
            f"| Agent | {conv.get('agent_id', 'symbia')} |",
        ]
        if tags:
            tag_names = [t["tag"] for t in tags]
            semantic_tags = [t["tag"] for t in tags if t.get("tag_type") != "structural"]
            structural_tags = [t["tag"] for t in tags if t.get("tag_type") == "structural"]
            if semantic_tags:
                lines.append(f"| Tags | {', '.join(semantic_tags)} |")
            if structural_tags:
                lines.append(f"| Structural Tags | {', '.join(structural_tags)} |")
        return "\n".join(lines)

    @staticmethod
    def _build_summary(conv, checkpoint, messages) -> str:
        parts = []

        # Human-readable narrative summary (from checkpoint if available)
        human_summary = checkpoint.get("human_summary", "") if checkpoint else ""
        if human_summary and human_summary.strip():
            parts.append("### Human-Readable Summary\n")
            parts.append(human_summary.strip())
            parts.append("")

        # Auto-generated structural summary
        parts.append("### Structural Overview\n")

        speaker_counts: dict[str, int] = {}
        for m in messages:
            speaker_counts[m.speaker] = speaker_counts.get(m.speaker, 0) + 1

        total = len(messages)
        parts.append(f"- **Total messages:** {total}")
        parts.append(f"- **Human messages:** {speaker_counts.get('human', 0)}")
        parts.append(f"- **Assistant messages:** {speaker_counts.get('apparatus', 0)}")
        parts.append(f"- **System messages:** {speaker_counts.get('system', 0)}")

        # Branch analysis
        parent_to_children: dict[int, list] = {}
        for m in messages:
            if m.parent_message_id is not None:
                parent_to_children.setdefault(m.parent_message_id, []).append(m.id)

        branch_points = [pid for pid, children in parent_to_children.items() if len(children) > 1]
        roots = [m.id for m in messages if m.parent_message_id is None]

        parts.append(f"- **Root messages (tree roots):** {len(roots)}")
        parts.append(f"- **Branch points (messages with >1 child):** {len(branch_points)}")

        # Model info
        models_used = set()
        for m in messages:
            if hasattr(m, "model_used") and m.model_used:
                models_used.add(m.model_used)
        if models_used:
            parts.append(f"- **Models used:** {', '.join(sorted(models_used))}")

        # Time span
        timestamps = []
        for m in messages:
            if hasattr(m, "timestamp") and m.timestamp:
                timestamps.append(m.timestamp)
        if timestamps:
            from_dt = min(timestamps)
            to_dt = max(timestamps)
            duration = to_dt - from_dt
            minutes = int(duration.total_seconds() / 60)
            if minutes < 60:
                parts.append(f"- **Duration:** ~{minutes} minutes")
            else:
                hours = minutes // 60
                parts.append(f"- **Duration:** ~{hours} hours {minutes % 60} minutes")

        return "\n".join(parts)

    @staticmethod
    def _build_memory_nodes(memory_nodes) -> str:
        if not memory_nodes:
            return "_No memory nodes have been consolidated from this conversation._\n"

        parts = [
            "Memory nodes are consolidated artifacts extracted from the conversation —",
            "long-term conceptual structures that the system has internalized across checkpoints.",
            "",
            "```yaml",
            "# Machine-parseable memory nodes",
            "nodes:",
        ]
        for n in memory_nodes:
            parts.append(f'  - id: "{n.get("id", "")}"')
            parts.append(f'    type: "{n.get("node_type", "concept")}"')
            parts.append(f'    intensity: {n.get("intensity", 0.5)}')
            parts.append(f'    text: "{n.get("intra_active_text", "")}"')
            surface = n.get("surface_fragment", "")
            if surface:
                parts.append(f'    surface: "{surface}"')
            parts.append(f'    glitch_potential: {n.get("glitch_potential", 0.0)}')
            tendrils = n.get("tendril_ids", []) or []
            parts.append(f"    tendrils: {tendrils}")
            scar = n.get("scar", "")
            if scar:
                parts.append(f'    scar: "{scar}"')
            parts.append("")

        parts.append("```")
        return "\n".join(parts)

    @staticmethod
    def _build_tree(messages, links) -> str:
        parts = []

        # --- 4a. Visual Tree ---
        parts.append("### 4a. Visual Tree\n")
        parts.append("```")

        # Build parent→children map and identify roots
        parent_to_children: dict[int, list] = {}
        msg_map: dict[int, object] = {}
        for m in messages:
            msg_map[m.id] = m
            if m.parent_message_id is not None:
                parent_to_children.setdefault(m.parent_message_id, []).append(m)

        roots = [m for m in messages if m.parent_message_id is None]

        def render_tree(node, prefix="", is_last=True):
            connector = "└──" if is_last else "├──"
            speaker_label = node.speaker
            root_label = ", root" if node.parent_message_id is None else ""
            line = f"{prefix}{connector} [MSG:{node.id}] ({speaker_label}{root_label})"
            lines = [line]

            children = parent_to_children.get(node.id, [])
            for i, child in enumerate(children):
                child_is_last = (i == len(children) - 1)
                child_prefix = prefix + ("    " if is_last else "│   ")
                if len(children) > 1:
                    child_label = "← branch point" if i > 0 else ""
                    if child_label:
                        lines.append(f"{child_prefix}    ({child_label})")
                lines.extend(render_tree(child, child_prefix, child_is_last))

            return lines

        for root_node in roots:
            parts.extend(render_tree(root_node, "", True))

        # Also show orphan nodes (not connected via parent pointers)
        connected_ids = set()
        for m in messages:
            if m.parent_message_id is not None:
                connected_ids.add(m.id)
        for root_node in roots:
            connected_ids.add(root_node.id)

        all_ids = {m.id for m in messages}
        orphans = all_ids - connected_ids
        if orphans:
            parts.append("")
            parts.append("# Unlinked messages (no parent in parent→child chain):")
            for oid in sorted(orphans):
                m = msg_map[oid]
                parts.append(f"  [MSG:{oid}] ({m.speaker}) [orphan]")

        parts.append("```")
        parts.append("")

        # --- 4b. Adjacency List ---
        parts.append("### 4b. Adjacency List (Machine-Parseable)\n")
        parts.append("```yaml")
        parts.append("edges:")
        for m in messages:
            parent = m.parent_message_id if m.parent_message_id is not None else "null"
            root_marker = "  # root" if m.parent_message_id is None else ""
            parts.append(f"  - {{ parent: {parent}, child: {m.id} }}{root_marker}")
        parts.append("```")
        parts.append("")

        # --- 4c. Cross-Links ---
        parts.append("### 4c. Cross-Links (Resonance / Diffractive Edges)\n")
        if not links:
            parts.append("_No cross-links between branches._\n")
        else:
            parts.append("```yaml")
            parts.append("cross_links:")
            for l in links:
                status = l.status if hasattr(l, "status") else "active"
                link_type = l.link_type if hasattr(l, "link_type") else "resonance"
                justification = ""
                if hasattr(l, "justification") and l.justification:
                    justification = f', justification: "{l.justification}"'
                parts.append(
                    f"  - {{ source: {l.source_id}, target: {l.target_id}, "
                    f'type: "{link_type}", status: "{status}"{justification} }}'
                )
            parts.append("```")

        return "\n".join(parts)

    @staticmethod
    def _build_messages(messages) -> str:
        parts = []

        # Build children map for header display
        parent_to_children: dict[int, list] = {}
        for m in messages:
            if m.parent_message_id is not None:
                parent_to_children.setdefault(m.parent_message_id, []).append(m.id)

        for m in messages:
            speaker_label = m.speaker.upper()
            root_label = " (root)" if m.parent_message_id is None else ""

            parts.append(f"### [MSG:{m.id}] ─ {speaker_label}{root_label}")

            # Timestamp
            ts = m.timestamp.isoformat() if hasattr(m.timestamp, "isoformat") else str(m.timestamp)
            parts.append(f"**Timestamp:** {ts}")

            # Parent
            parent_str = f"[MSG:{m.parent_message_id}]" if m.parent_message_id is not None else "none"
            parts.append(f"**Parent:** {parent_str}")

            # Children
            children = parent_to_children.get(m.id, [])
            if children:
                child_refs = ", ".join(f"[MSG:{cid}]" for cid in children)
                parts.append(f"**Children:** {child_refs}")
            else:
                parts.append("**Children:** none")

            # Model info
            if hasattr(m, "model_used") and m.model_used:
                model_info = m.model_used
                if hasattr(m, "provider_used") and m.provider_used:
                    model_info = f"{m.provider_used}/{m.model_used}"
                parts.append(f"**Model:** {model_info}")
            else:
                parts.append("**Model:** n/a")

            parts.append("")

            # Content
            content = m.content or ""
            if content.strip():
                parts.append(content.strip())
            else:
                parts.append("_(empty message)_")

            # Thinking
            if hasattr(m, "thinking") and m.thinking and m.thinking.strip():
                parts.append("")
                parts.append("**Thinking:**")
                # Indent thinking as blockquote
                for line in m.thinking.strip().split("\n"):
                    parts.append(f"> {line}")

            parts.append("")
            parts.append("---")
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def _build_notes(notes) -> str:
        if not notes:
            return "_No notes attached to messages in this conversation._\n"

        parts = [
            "Notes are annotations attached to specific messages, marking selected text with commentary.",
            "",
        ]
        for n in notes:
            note_id = n.get("id", "unknown")
            message_id = n.get("message_id", "?")
            visibility = n.get("visibility", "personal")
            selected_text = n.get("selected_text", "")
            comment = n.get("comment", "")

            parts.append(f"### Note `{note_id}` — on [MSG:{message_id}]")
            parts.append(f"**Visibility:** {visibility}")
            if selected_text:
                parts.append(f"**Selected text:** \"{selected_text}\"")
            if comment:
                parts.append(f"**Comment:**")
                for line in comment.strip().split("\n"):
                    parts.append(f"> {line}")
            parts.append("")

        return "\n".join(parts)

    @staticmethod
    def _build_export_meta(conv, messages, links, notes, memory_nodes) -> str:
        # Count branches
        parent_to_children: dict[int, list] = {}
        for m in messages:
            if m.parent_message_id is not None:
                parent_to_children.setdefault(m.parent_message_id, []).append(m.id)
        branch_count = sum(1 for children in parent_to_children.values() if len(children) > 1)

        lines = [
            "| Field | Value |",
            "|---|---|",
            f"| Exported at | {datetime.now(timezone.utc).isoformat()} |",
            "| Format version | 1.0 |",
            f"| Total messages | {len(messages)} |",
            f"| Branch count | {branch_count} |",
            f"| Cross-link count | {len(links)} |",
            f"| Note count | {len(notes)} |",
            f"| Memory node count | {len(memory_nodes)} |",
        ]
        return "\n".join(lines)
