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
            message_id = n.get("asset_id", n.get("message_id", "?"))
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

    # ── Research Export ──────────────────────────────────────────────

    @staticmethod
    def build_research_export(
        task: dict,
        branches: list[dict],
        assets: list[dict],
        steps: list[dict],
        plan: dict | None,
        results_by_step: dict,
        notes: list[dict],
    ) -> str:
        parts: list[str] = []

        parts.append("---")
        parts.append(f'task_id: "{task["id"]}"')
        parts.append(f'title: "{task.get("title", "")}"')
        parts.append(f'status: "{task.get("status", "")}"')
        parts.append(f'trigger_source: "{task.get("trigger_source", "")}"')
        parts.append(f"max_depth: {task.get('max_depth', 0)}")
        parts.append(f"max_breadth: {task.get('max_breadth', 0)}")
        parts.append(f"assets_harvested: {task.get('assets_harvested', 0)}")
        parts.append(f"branches_created: {task.get('branches_created', 0)}")
        parts.append(f"note_count: {len(notes)}")
        parts.append(f'export_format_version: "1.0"')
        parts.append(f'exported_at: "{datetime.now(timezone.utc).isoformat()}"')
        parts.append("---")
        parts.append("")

        title = task.get("title", "") or "Untitled Research Task"
        parts.append(f"# Research Task: {title}\n")

        parts.append("## METADATA\n")
        parts.append("| Field | Value |")
        parts.append("|---|---|")
        parts.append(f"| Task ID | `{task['id']}` |")
        parts.append(f"| Status | {task.get('status', '')} |")
        parts.append(f"| Trigger | {task.get('trigger_source', '')} |")
        parts.append(f"| Max Depth | {task.get('max_depth', '')} |")
        parts.append(f"| Max Breadth | {task.get('max_breadth', '')} |")
        parts.append(f"| Budget Spent | ${task.get('budget_spent_usd', 0):.4f} / ${task.get('budget_limit_usd', 0):.2f} |")
        if task.get("started_at"):
            parts.append(f"| Started | {task['started_at']} |")
        if task.get("completed_at"):
            parts.append(f"| Completed | {task['completed_at']} |")
        parts.append("")

        parts.append("## OBJECTIVE\n")
        objective = task.get("objective", "")
        if objective:
            parts.append(objective.strip())
        else:
            parts.append("_No objective provided._")
        parts.append("")

        if task.get("proposal_rationale"):
            parts.append("## PROPOSAL RATIONALE\n")
            parts.append(task["proposal_rationale"].strip())
            parts.append("")

        if task.get("result_summary"):
            parts.append("## RESULT SUMMARY\n")
            parts.append(task["result_summary"].strip())
            parts.append("")

        if plan:
            parts.append("## RESEARCH PLAN\n")
            try:
                import json
                plan_json = json.loads(plan.get("plan_json", "{}"))
                parts.append("```json")
                parts.append(json.dumps(plan_json, indent=2))
                parts.append("```")
            except Exception:
                parts.append(f"```\n{plan.get('plan_json', '')}\n```")
            parts.append("")

        parts.append(f"## BRANCHES ({len(branches)})\n")
        if not branches:
            parts.append("_No branches created._\n")
        else:
            for b in branches:
                parts.append(f"### Branch `{b['id'][:12]}…`")
                parts.append(f"- **Query:** {b.get('query', '—')}")
                parts.append(f"- **Goal:** {b.get('goal', '—')}")
                parts.append(f"- **Depth:** {b.get('depth', 0)} | **Breadth:** {b.get('breadth', 0)}")
                parts.append(f"- **Status:** {b.get('status', 'unknown')}")
                parts.append("")

        parts.append(f"## SCRAPED ASSETS ({len(assets)})\n")
        if not assets:
            parts.append("_No assets harvested._\n")
        else:
            for a in assets:
                parts.append(f"### Asset `{a['id'][:12]}…`")
                parts.append(f"- **URL:** {a.get('url', '—')}")
                parts.append(f"- **Relevance:** {a.get('relevance_score', 0):.3f} | **Novelty:** {a.get('novelty_score', 0):.3f}")
                parts.append("")
                raw = a.get("raw_markdown", "")
                if raw:
                    parts.append(raw[:5000])
                    if len(raw) > 5000:
                        parts.append(f"\n\n_…truncated ({len(raw) - 5000} more chars)_")
                parts.append("")

        parts.append(f"## ORCHESTRATOR STEPS ({len(steps)})\n")
        if not steps:
            parts.append("_No steps recorded (legacy engine or not started)._")
        else:
            for step in steps:
                results = results_by_step.get(step["id"], [])
                parts.append(f"### Step #{step.get('step_number', '?')} — {step.get('step_type', 'unknown')}")
                parts.append(f"- **Status:** {step.get('status', 'unknown')}")
                if step.get("result_summary"):
                    parts.append(f"- **Summary:** {step['result_summary']}")
                for r in results:
                    parts.append(f"- **Result:** [{r.get('source_title') or r.get('source_url', '—')}]({r.get('source_url', '')})")
                parts.append("")

        parts.append(f"## NOTES ({len(notes)})\n")
        if not notes:
            parts.append("_No notes attached to this research task._\n")
        else:
            for n in notes:
                parts.append(f"### Note `{n.get('id', 'unknown')}` — {n.get('asset_type', '')}:{n.get('asset_id', '')[:12]}")
                parts.append(f"**Visibility:** {n.get('visibility', 'personal')}")
                if n.get("selected_text"):
                    parts.append(f"**Selected text:** \"{n['selected_text']}\"")
                if n.get("comment"):
                    parts.append("**Comment:**")
                    for line in n["comment"].strip().split("\n"):
                        parts.append(f"> {line}")
                parts.append("")

        parts.append("## EXPORT METADATA\n")
        parts.append("| Field | Value |")
        parts.append("|---|---|")
        parts.append(f"| Exported at | {datetime.now(timezone.utc).isoformat()} |")
        parts.append(f"| Format version | 1.0 |")
        parts.append(f"| Branch count | {len(branches)} |")
        parts.append(f"| Asset count | {len(assets)} |")
        parts.append(f"| Step count | {len(steps)} |")
        parts.append(f"| Note count | {len(notes)} |")

        return "\n".join(parts)

    # ── Research JSON Export ────────────────────────────────────────────

    @staticmethod
    def build_research_export_json(
        task: dict,
        branches: list[dict],
        assets: list[dict],
        steps: list[dict],
        plan: dict | None,
        step_results: list[dict],
        notes: list[dict],
        meta_log: list[dict],
    ) -> dict:
        """Build a structured JSON export for re-import."""
        return {
            "export_format_version": "2.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "task": task,
            "branches": branches,
            "assets": assets,
            "plan": plan,
            "steps": steps,
            "step_results": step_results,
            "meta_log": meta_log,
            "notes": notes,
        }

    # ── Research Stages Export ────────────────────────────────────────────

    @staticmethod
    def _parse_step_data(step: dict) -> dict:
        """Parse step_data JSON string, returning empty dict on failure."""
        import json
        raw = step.get("step_data", "{}")
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}

    @staticmethod
    def _extract_llm_content(step_data: dict) -> dict:
        """Extract the actual LLM response content from step_data,
        unwrapping nested llm_response.content / llm_response.json_data."""
        import json
        llm_resp = step_data.get("llm_response", {})
        if isinstance(llm_resp, str):
            try:
                llm_resp = json.loads(llm_resp)
            except Exception:
                return {}
        if not isinstance(llm_resp, dict):
            return {}
        content = llm_resp.get("json_data") or llm_resp.get("content")
        if isinstance(content, str):
            try:
                return json.loads(content)
            except Exception:
                return {}
        if isinstance(content, dict):
            return content
        return {}

    @staticmethod
    def build_research_stages_export(
        task: dict,
        steps: list[dict],
        step_results: list[dict],
        plan: dict | None,
        notes: list[dict],
    ) -> str:
        """Build a clean markdown export of research stages and findings,
        organized by cycle. Excludes raw source materials — only links[names].
        """
        import json

        parts: list[str] = []

        # ── Frontmatter ──
        parts.append("---")
        parts.append(f'task_id: "{task["id"]}"')
        parts.append(f'title: "{task.get("title", "")}"')
        parts.append(f'status: "{task.get("status", "")}"')
        parts.append(f"max_depth: {task.get('max_depth', 0)}")
        parts.append(f"max_breadth: {task.get('max_breadth', 0)}")
        parts.append(f'export_format_version: "1.0"')
        parts.append(f'exported_at: "{datetime.now(timezone.utc).isoformat()}"')
        parts.append("---")
        parts.append("")

        # ── Title ──
        title = task.get("title", "") or "Untitled Research Task"
        parts.append(f"# Research: {title}\n")

        # ── Objectives ──
        parts.append("## OBJECTIVES\n")
        objective = task.get("objective", "")
        if objective:
            parts.append(objective.strip())
        else:
            parts.append("_No objective provided._")
        parts.append("")

        # ── Limits ──
        parts.append("## LIMITS\n")
        parts.append(f"- **Max Depth:** {task.get('max_depth', 'N/A')} cycles")
        parts.append(f"- **Max Breadth:** {task.get('max_breadth', 'N/A')} branches per cycle")
        parts.append(f"- **Budget:** ${task.get('budget_spent_usd', 0):.4f} / ${task.get('budget_limit_usd', 0):.2f}")
        if task.get("started_at"):
            parts.append(f"- **Started:** {task['started_at']}")
        if task.get("completed_at"):
            parts.append(f"- **Completed:** {task['completed_at']}")
        parts.append("")

        # ── Helper: group step results by step_id ──
        results_by_step: dict[str, list[dict]] = {}
        for r in step_results:
            sid = r.get("step_id", "")
            if sid not in results_by_step:
                results_by_step[sid] = []
            results_by_step[sid].append(r)

        # ── Helper: get step depth ──
        def get_depth(step: dict) -> int:
            try:
                sd = ExportService._parse_step_data(step)
                return int(sd.get("depth", 0))
            except Exception:
                return 0

        # ── Group steps by depth (cycle) ──
        depth_steps: dict[int, list[dict]] = {}
        for step in steps:
            d = get_depth(step)
            if d not in depth_steps:
                depth_steps[d] = []
            depth_steps[d].append(step)

        sorted_depths = sorted(depth_steps.keys())

        # ── Document Digestion (depth 0, before first cycle) ──
        doc_digest_steps = [
            s for s in steps
            if s.get("step_type") == "document_digestion" and s.get("status") == "completed"
        ]
        if doc_digest_steps:
            parts.append("## DOCUMENT DIGESTION\n")
            for ds in doc_digest_steps:
                dd_results = results_by_step.get(ds["id"], [])
                for r in dd_results:
                    source_title = r.get("source_title") or "Uploaded Document"
                    source_url = r.get("source_url", "")
                    parts.append(f"### Document: {source_title}\n")
                    if source_url and source_url != source_title:
                        parts.append(f"- **File:** [{source_title}]({source_url})")

                    analyzed = {}
                    raw_analyzed = r.get("analyzed_json")
                    if raw_analyzed:
                        try:
                            if isinstance(raw_analyzed, str):
                                analyzed = json.loads(raw_analyzed)
                            elif isinstance(raw_analyzed, dict):
                                analyzed = raw_analyzed
                        except Exception:
                            pass

                    learnings = analyzed.get("learnings", [])
                    if learnings:
                        parts.append("\n#### Learnings\n")
                        for l in learnings:
                            parts.append(f"- {l}")

                    followups = analyzed.get("followups", [])
                    if followups:
                        parts.append("\n#### Follow-up Questions\n")
                        for f in followups:
                            parts.append(f"- {f}")

                    gaps = analyzed.get("gaps", [])
                    if gaps:
                        parts.append("\n#### Identified Gaps\n")
                        for g in gaps:
                            parts.append(f"- {g}")

                    parts.append("")
            parts.append("")

        # ── Per-cycle export ──
        for depth_idx, depth in enumerate(sorted_depths):
            cycle_steps = depth_steps[depth]
            cycle_num = depth_idx + 1

            # Determine if this is the final cycle (has synthesize)
            has_synthesize = any(s.get("step_type") == "synthesize" for s in cycle_steps)
            cycle_label = f"Cycle {cycle_num}" + (" (Final)" if has_synthesize else "")

            parts.append(f"## {cycle_label}\n")

            # ── Sources ──
            all_source_urls: dict[str, dict] = {}
            parse_steps = [s for s in cycle_steps if s.get("step_type") == "parallel_parse"]
            doc_steps = [s for s in cycle_steps if s.get("step_type") == "document_digestion"]
            for ps in parse_steps + doc_steps:
                for r in results_by_step.get(ps["id"], []):
                    url = r.get("source_url", "")
                    title = r.get("source_title") or url
                    if url and url not in all_source_urls:
                        all_source_urls[url] = {"title": title, "url": url}

            if all_source_urls:
                parts.append("### Sources\n")
                for idx, (url, info) in enumerate(all_source_urls.items(), 1):
                    name = info["title"]
                    if len(name) > 100:
                        name = name[:97] + "..."
                    parts.append(f"- [{idx}] [{name}]({url})")
                parts.append("")

            # ── Findings (from digest steps) ──
            digest_steps = [s for s in cycle_steps if s.get("step_type") == "digest"]
            all_findings: list[str] = []
            if digest_steps:
                for ds in digest_steps:
                    for r in results_by_step.get(ds["id"], []):
                        analyzed = {}
                        raw_analyzed = r.get("analyzed_json")
                        if raw_analyzed:
                            try:
                                if isinstance(raw_analyzed, str):
                                    analyzed = json.loads(raw_analyzed)
                                elif isinstance(raw_analyzed, dict):
                                    analyzed = raw_analyzed
                            except Exception:
                                pass
                        learnings = analyzed.get("learnings", [])
                        source_title = r.get("source_title") or r.get("source_url", "")[:80]
                        for l in learnings:
                            all_findings.append(f"[{source_title}]: {l}")

            if all_findings:
                parts.append("### Findings\n")
                for f in all_findings:
                    parts.append(f"- {f}")
                parts.append("")

            # ── Consolidation (from "reflect" step — the consolidation phase) ──
            reflect_steps = [s for s in cycle_steps if s.get("step_type") == "reflect" and s.get("status") == "completed"]
            for rs in reflect_steps:
                sd = ExportService._parse_step_data(rs)
                consolidation = ExportService._extract_llm_content(sd)
                if not consolidation and sd:
                    consolidation = sd

                if consolidation:
                    parts.append("### Consolidation\n")

                    completeness = consolidation.get("completeness_score")
                    if completeness is not None:
                        try:
                            pct = float(completeness) * 100
                            parts.append(f"- **Completeness Score:** {pct:.1f}%")
                        except Exception:
                            parts.append(f"- **Completeness Score:** {completeness}")

                    key_insights = consolidation.get("key_insights", [])
                    if key_insights:
                        parts.append("\n**Key Insights:**")
                        for ins in key_insights:
                            parts.append(f"- {ins}")

                    remaining_gaps = consolidation.get("remaining_gaps", [])
                    if remaining_gaps:
                        parts.append("\n**Remaining Gaps:**")
                        for gap in remaining_gaps:
                            parts.append(f"- {gap}")

                    next_queries = consolidation.get("next_queries", [])
                    if next_queries:
                        parts.append("\n**Next Queries:**")
                        for q in next_queries:
                            parts.append(f"- {q}")

                    next_urls = consolidation.get("next_direct_urls", [])
                    if next_urls:
                        parts.append("\n**Next Direct URLs:**")
                        for u in next_urls:
                            parts.append(f"- [{u}]({u})")

                    reflection_text = consolidation.get("reflection") or consolidation.get("reflection_notes")
                    if reflection_text:
                        parts.append(f"\n**Reflection:**\n{reflection_text}")

                    parts.append("")

            # ── Reflection (from "reflection" step — meta-cognitive reflection) ──
            refl_steps = [s for s in cycle_steps if s.get("step_type") == "reflection" and s.get("status") == "completed"]
            for rs in refl_steps:
                sd = ExportService._parse_step_data(rs)
                reflection = ExportService._extract_llm_content(sd)
                if not reflection and sd:
                    reflection = sd

                if reflection:
                    parts.append("### Meta-Reflection\n")

                    refl_notes = reflection.get("reflection_notes")
                    if refl_notes:
                        parts.append(f"**Reflection Notes:**\n{refl_notes}\n")

                    key_insights = reflection.get("key_insights", [])
                    if key_insights:
                        parts.append("\n**Key Insights:**")
                        for ins in key_insights:
                            parts.append(f"- {ins}")

                    biases = reflection.get("detected_biases", [])
                    if biases:
                        parts.append("\n**Detected Biases:**")
                        for b in biases:
                            parts.append(f"- {b}")

                    gaps = reflection.get("knowledge_gaps", []) or reflection.get("remaining_gaps", [])
                    if gaps:
                        parts.append("\n**Knowledge Gaps:**")
                        for g in gaps:
                            parts.append(f"- {g}")

                    refined = reflection.get("refined_queries", [])
                    if refined:
                        parts.append("\n**Refined Queries:**")
                        for q in refined:
                            parts.append(f"- {q}")

                    signals = reflection.get("signal_flags", [])
                    if signals:
                        parts.append(f"\n**Signal Flags:** {', '.join(str(s) for s in signals)}")

                    metrics = []
                    for mn in ("glitch_fidelity", "contradiction_density", "source_entropy", "revised_confidence"):
                        if mn in reflection:
                            val = reflection[mn]
                            try:
                                metrics.append(f"- **{mn.replace('_', ' ').title()}:** {float(val):.4f}")
                            except Exception:
                                metrics.append(f"- **{mn.replace('_', ' ').title()}:** {val}")
                    if metrics:
                        parts.append("\n**Cognitive Metrics:**")
                        parts.extend(metrics)

                    parts.append("")

            # ── Evaluation ──
            eval_steps = [s for s in cycle_steps if s.get("step_type") == "evaluate" and s.get("status") == "completed"]
            for es in eval_steps:
                sd = ExportService._parse_step_data(es)
                evaluation = ExportService._extract_llm_content(sd)
                if not evaluation and sd:
                    evaluation = sd

                if evaluation:
                    parts.append("### Evaluation\n")
                    should_stop = evaluation.get("should_stop", False)
                    stop_reason = evaluation.get("stop_reason", "")
                    parts.append(f"- **Decision:** {'STOP' if should_stop else 'CONTINUE'}")
                    if stop_reason:
                        parts.append(f"- **Reason:** {stop_reason}")
                    parts.append("")

        # ── Synthesis ──
        synthesize_steps = [
            s for s in steps
            if s.get("step_type") == "synthesize" and s.get("status") == "completed"
        ]
        if synthesize_steps:
            parts.append("## SYNTHESIS\n")
            for ss in synthesize_steps:
                sd = ExportService._parse_step_data(ss)
                depth = sd.get("depth", 0)
                report = sd.get("report_markdown", "")
                if report:
                    parts.append(f"### Final Report (Cycle {depth + 1})\n")
                    parts.append(report.strip())
                    parts.append("")
                elif ss.get("result_summary"):
                    parts.append(ss["result_summary"].strip())
                    parts.append("")

        # ── Notes ──
        if notes:
            parts.append("## NOTES\n")
            for n in notes:
                nid = n.get("id", "unknown")
                visibility = n.get("visibility", "personal")
                selected = n.get("selected_text", "")
                comment = n.get("comment", "")
                parts.append(f"### Note `{nid}`")
                parts.append(f"- **Visibility:** {visibility}")
                if selected:
                    parts.append(f"- **Selected text:** \"{selected}\"")
                if comment:
                    parts.append(f"- **Comment:**\n{comment}")
                parts.append("")

        # ── Export Metadata ──
        parts.append("## EXPORT METADATA\n")
        parts.append("| Field | Value |")
        parts.append("|---|---|")
        parts.append(f"| Exported at | {datetime.now(timezone.utc).isoformat()} |")
        parts.append(f"| Format version | 1.0 |")
        parts.append(f"| Total cycles | {len(sorted_depths)} |")
        parts.append(f"| Step count | {len(steps)} |")
        parts.append(f"| Note count | {len(notes)} |")

        return "\n".join(parts)
