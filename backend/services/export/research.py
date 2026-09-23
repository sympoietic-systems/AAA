"""Research Export Builder — Reports, stages, and structured JSON."""

import json
import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class ResearchExportBuilder:
    @staticmethod
    def build_research_report_content(app_state, task_id: str) -> str:
        """Gather all research data from app_state and produce a full stages export
        as a markdown string. Falls back to a short summary if repos are unavailable.

        Used by task completion and sediment injection to generate the full report
        for LLM context injection, instead of just the result_summary string.
        """
        import logging

        logger = logging.getLogger("aaa.export")

        task_repo = getattr(app_state, "research_task_repo", None)
        task = task_repo.get(task_id) if task_repo else None
        if not task:
            return "Research task not found."

        step_repo = getattr(app_state, "research_step_repo", None)
        result_repo = getattr(app_state, "research_step_result_repo", None)
        plan_repo = getattr(app_state, "research_plan_repo", None)
        note_repo = getattr(app_state, "note_repo", None)

        try:
            steps = step_repo.get_by_task(task_id) if step_repo else []
            step_results = result_repo.get_by_task(task_id) if result_repo else []
            plan = plan_repo.get_by_task(task_id) if plan_repo else None
            notes = note_repo.get_notes_by_task(task_id) if note_repo else []

            markdown = ResearchExportBuilder.build_research_stages_export(
                task=task,
                steps=steps,
                step_results=step_results,
                plan=plan,
                notes=notes,
            )

            if markdown and markdown.strip():
                return markdown

            logger.warning(
                "build_research_stages_export returned empty for task %s, falling back to result_summary", task_id
            )
        except Exception as e:
            logger.error("Failed to build research stages export for task %s: %s", task_id, e)

        return task.get("result_summary") or "No synthesis result generated."

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
        parts.append('export_format_version: "1.0"')
        parts.append(f'exported_at: "{datetime.now(UTC).isoformat()}"')
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
        parts.append(
            f"| Budget Spent | ${task.get('budget_spent_usd', 0):.4f} / ${task.get('budget_limit_usd', 0):.2f} |"
        )
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
                parts.append(
                    f"- **Relevance:** {a.get('relevance_score', 0):.3f} | **Novelty:** {a.get('novelty_score', 0):.3f}"
                )
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
                    parts.append(
                        f"- **Result:** [{r.get('source_title') or r.get('source_url', '—')}]({r.get('source_url', '')})"
                    )
                parts.append("")

        parts.append(f"## NOTES ({len(notes)})\n")
        if not notes:
            parts.append("_No notes attached to this research task._\n")
        else:
            for n in notes:
                parts.append(
                    f"### Note `{n.get('id', 'unknown')}` — {n.get('asset_type', '')}:{n.get('asset_id', '')[:12]}"
                )
                parts.append(f"**Visibility:** {n.get('visibility', 'personal')}")
                if n.get("selected_text"):
                    parts.append(f'**Selected text:** "{n["selected_text"]}"')
                if n.get("comment"):
                    parts.append("**Comment:**")
                    for line in n["comment"].strip().split("\n"):
                        parts.append(f"> {line}")
                parts.append("")

        parts.append("## EXPORT METADATA\n")
        parts.append("| Field | Value |")
        parts.append("|---|---|")
        parts.append(f"| Exported at | {datetime.now(UTC).isoformat()} |")
        parts.append("| Format version | 1.0 |")
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
            "exported_at": datetime.now(UTC).isoformat(),
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

        parts: list[str] = []

        # ── Frontmatter ──
        parts.append("---")
        parts.append(f'task_id: "{task["id"]}"')
        parts.append(f'title: "{task.get("title", "")}"')
        parts.append(f'status: "{task.get("status", "")}"')
        parts.append(f"max_depth: {task.get('max_depth', 0)}")
        parts.append(f"max_breadth: {task.get('max_breadth', 0)}")
        parts.append('export_format_version: "1.0"')
        parts.append(f'exported_at: "{datetime.now(UTC).isoformat()}"')
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
                sd = ResearchExportBuilder._parse_step_data(step)
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
            s for s in steps if s.get("step_type") == "document_digestion" and s.get("status") == "completed"
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
                        for learning in learnings:
                            parts.append(f"- {learning}")

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

            # ── Sources (with insights and gaps per parsed link) ──
            # Digest step updates existing parse results' analyzed_json in-place,
            # so we read learnings/gaps directly from parse step results.
            parse_steps = [s for s in cycle_steps if s.get("step_type") == "parallel_parse"]
            doc_digest_steps = [s for s in cycle_steps if s.get("step_type") == "document_digestion"]

            sources: list[dict] = []  # [{url, title, learnings, gaps}]
            seen_urls: set[str] = set()

            for ps in parse_steps + doc_digest_steps:
                for r in results_by_step.get(ps["id"], []):
                    url = r.get("source_url", "")
                    title = r.get("source_title") or url
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

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

                    sources.append(
                        {
                            "title": title,
                            "url": url,
                            "learnings": analyzed.get("learnings", []),
                            "gaps": analyzed.get("gaps", []),
                        }
                    )

            if sources:
                parts.append("### Sources\n")
                for idx, s in enumerate(sources, 1):
                    name = s["title"]
                    if len(name) > 100:
                        name = name[:97] + "..."
                    if s["url"] and s["url"] != s["title"]:
                        parts.append(f"#### [{idx}] [{name}]({s['url']})\n")
                    elif s["url"]:
                        parts.append(f"#### [{idx}] {s['url']}\n")
                    else:
                        parts.append(f"#### [{idx}] {name}\n")

                    if s["learnings"]:
                        parts.append("**Insights:**")
                        for learning in s["learnings"]:
                            parts.append(f"- {learning}")
                        parts.append("")

                    if s["gaps"]:
                        parts.append("**Gaps:**")
                        for g in s["gaps"]:
                            parts.append(f"- {g}")
                        parts.append("")
                parts.append("")

            # ── Consolidation (from "reflect" step — the consolidation phase) ──
            reflect_steps = [
                s for s in cycle_steps if s.get("step_type") == "reflect" and s.get("status") == "completed"
            ]
            for rs in reflect_steps:
                sd = ResearchExportBuilder._parse_step_data(rs)
                consolidation = ResearchExportBuilder._extract_llm_content(sd)
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
            refl_steps = [
                s for s in cycle_steps if s.get("step_type") == "reflection" and s.get("status") == "completed"
            ]
            for rs in refl_steps:
                sd = ResearchExportBuilder._parse_step_data(rs)
                reflection = ResearchExportBuilder._extract_llm_content(sd)
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
                sd = ResearchExportBuilder._parse_step_data(es)
                evaluation = ResearchExportBuilder._extract_llm_content(sd)
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
        synthesize_steps = [s for s in steps if s.get("step_type") == "synthesize" and s.get("status") == "completed"]
        if synthesize_steps:
            parts.append("## SYNTHESIS\n")
            for ss in synthesize_steps:
                sd = ResearchExportBuilder._parse_step_data(ss)
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
                    parts.append(f'- **Selected text:** "{selected}"')
                if comment:
                    parts.append(f"- **Comment:**\n{comment}")
                parts.append("")

        # ── Export Metadata ──
        parts.append("## EXPORT METADATA\n")
        parts.append("| Field | Value |")
        parts.append("|---|---|")
        parts.append(f"| Exported at | {datetime.now(UTC).isoformat()} |")
        parts.append("| Format version | 1.0 |")
        parts.append(f"| Total cycles | {len(sorted_depths)} |")
        parts.append(f"| Step count | {len(steps)} |")
        parts.append(f"| Note count | {len(notes)} |")

        return "\n".join(parts)
