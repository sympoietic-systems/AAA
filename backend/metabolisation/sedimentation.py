"""Sedimentation parsing, merging, and metrics utilities for the Dream Daemon."""

import json
import re
import uuid

import yaml


def generate_node_id() -> str:
    return "mem_" + uuid.uuid4().hex[:4]


def parse_sedimentation_yaml(raw_output: str) -> tuple[list[dict], int]:
    """Parse LLM sedimentation output into structured memory nodes.

    Returns (nodes, tier) where tier indicates parse quality (1=best, 5=fallback).
    """
    nodes: list[dict] = []
    tier = 5

    raw = raw_output.strip()
    if not raw:
        return nodes, tier

    # Strip markdown code fences
    for fence in ("```yaml", "```yml", "```json", "```"):
        if raw.startswith(fence):
            raw = raw[len(fence):]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            break

    # Tier 1: Full YAML parse
    try:
        parsed = yaml.safe_load(raw)
        tier = 1
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    nodes.append(item)
        elif isinstance(parsed, dict):
            nodes.append(parsed)
    except yaml.YAMLError:
        pass

    # Tier 2: Block-level split + per-block YAML
    if not nodes:
        blocks = re.split(r"\n(?=-\s+(?:id|type|intensity):)", raw)
        if len(blocks) > 1:
            for block in blocks:
                try:
                    parsed = yaml.safe_load(block.strip())
                    if isinstance(parsed, dict):
                        nodes.append(parsed)
                    elif isinstance(parsed, list):
                        nodes.extend(p for p in parsed if isinstance(p, dict))
                except yaml.YAMLError:
                    pass
            if nodes:
                tier = 2

    # Tier 3: JSON fallback
    if not nodes:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                nodes = [n for n in parsed if isinstance(n, dict)]
            elif isinstance(parsed, dict):
                nodes = [parsed]
            if nodes:
                tier = 3
        except (json.JSONDecodeError, ValueError):
            pass

    # Tier 4: Regex structural extraction
    if not nodes:
        candidate_blocks = re.split(r"\n\n+", raw)
        for block in candidate_blocks:
            block = block.strip()
            if not block:
                continue

            node = {}
            m = re.search(r'id:\s*(mem_\w{4})', block)
            if m:
                node["id"] = m.group(1)

            m = re.search(
                r'type:\s*(scar|concept|tension|pattern|bifurcation)',
                block, re.IGNORECASE,
            )
            if m:
                node["type"] = m.group(1).lower()

            m = re.search(r'intensity:\s*([\d.]+)', block)
            if m:
                try:
                    node["intensity"] = float(m.group(1))
                except ValueError:
                    pass

            m = re.search(r'scar:\s*(.+?)(?=\n\s*\w+:|$)', block, re.DOTALL)
            if m:
                node["scar"] = m.group(1).strip()

            m = re.search(r'glitch_potential:\s*([\d.]+)', block)
            if m:
                try:
                    node["glitch_potential"] = float(m.group(1))
                except ValueError:
                    pass

            m = re.search(
                r'intra_active_text:\s*>\s*\n\s*(.+?)(?=\n\s*\w+:|$)',
                block, re.DOTALL,
            )
            if m:
                node["intra_active_text"] = m.group(1).strip()
            if not node.get("intra_active_text"):
                m = re.search(
                    r'intra_active_text:\s*"([^"]+)"',
                    block,
                )
                if m:
                    node["intra_active_text"] = m.group(1)

            m = re.search(r'diffractive_key:\s*"([^"]+)"', block)
            if not m:
                m = re.search(r'diffractive_key:\s*(.+?)(?=\n|$)', block)
            if m:
                node["diffractive_key"] = m.group(1).strip().strip('"')

            m = re.search(r'surface_fragment:\s*"([^"]+)"', block)
            if not m:
                m = re.search(r'surface_fragment:\s*(.+?)(?=\n|$)', block)
            if m:
                node["surface_fragment"] = m.group(1).strip().strip('"')

            m = re.search(
                r'agential_symmetry:\s*(imposed|negotiated|co-constituted)',
                block, re.IGNORECASE,
            )
            if m:
                node["agential_symmetry"] = m.group(1).lower()

            m = re.search(r'tendrils:\s*\[(.+?)\]', block)
            if m:
                tendril_ids = [
                    tid.strip().strip("'\"") for tid in m.group(1).split(",") if tid.strip()
                ]
                node["tendrils"] = tendril_ids

            if node.get("intra_active_text"):
                nodes.append(node)

        if nodes:
            tier = 4

    # Normalize and validate all nodes
    valid_nodes = []
    for node in nodes:
        intra = node.get("intra_active_text", "")
        if not intra or not isinstance(intra, str) or not intra.strip():
            continue

        node_id = node.get("id", "")
        if not node_id or not node_id.startswith("mem_"):
            node["id"] = generate_node_id()

        node.setdefault("type", "concept")
        node.setdefault("intensity", 0.5)
        node.setdefault("scar", "")
        node.setdefault("glitch_potential", 0.0)
        node.setdefault("agential_symmetry", "negotiated")
        node.setdefault("diffractive_key", "")
        node.setdefault("surface_fragment", "")
        node.setdefault("tendrils", [])

        valid_types = {"scar", "concept", "tension", "pattern", "bifurcation"}
        if node.get("type") not in valid_types:
            node["type"] = "concept"

        valid_asym = {"imposed", "negotiated", "co-constituted"}
        if node.get("agential_symmetry") not in valid_asym:
            node["agential_symmetry"] = "negotiated"

        try:
            node["intensity"] = max(0.0, min(1.0, float(node["intensity"])))
        except (ValueError, TypeError):
            node["intensity"] = 0.5

        try:
            node["glitch_potential"] = max(0.0, min(1.0, float(node["glitch_potential"])))
        except (ValueError, TypeError):
            node["glitch_potential"] = 0.0

        valid_nodes.append(node)

    return valid_nodes, tier


def merge_nodes(existing_nodes: list[dict], new_nodes: list[dict]) -> list[dict]:
    """Merge new parsed nodes into existing nodes by ID."""
    existing_by_id: dict[str, dict] = {n["id"]: n for n in existing_nodes if n.get("id")}
    merged = dict(existing_by_id)

    for node in new_nodes:
        node_id = node.get("id", "")
        if node_id and node_id in merged:
            merged[node_id].update(node)
        elif node_id:
            merged[node_id] = node
        else:
            node["id"] = generate_node_id()
            merged[node["id"]] = node

    return sorted(merged.values(), key=lambda n: n.get("intensity", 0), reverse=True)


def build_compact_node_summary(nodes: list[dict]) -> str:
    """Build a one-line-per-node summary for inclusion in consolidation prompts."""
    if not nodes:
        return "(no existing nodes)"
    lines = []
    for n in nodes:
        nid = n.get("id", "?")
        ntype = n.get("type", "concept")
        dk = n.get("diffractive_key", "")
        text = n.get("intra_active_text", "")
        one_liner = text[:120].replace("\n", " ")
        key_part = f' key="{dk}"' if dk else ""
        lines.append(f"  {nid} ({ntype}){key_part}: {one_liner}...")
    return "\n".join(lines)


def store_daemon_metrics(metrics_repo, message_id: int, metrics: dict) -> None:
    """Persist a single message's daemon metrics to the repository."""
    s_t = metrics.get("pairwise_similarity")
    novelty = metrics.get("conceptual_novelty")
    if s_t is None or novelty is None:
        return
    phase_shifts = metrics.get("phase_shifts")
    phase_shifts_json = json.dumps(phase_shifts) if phase_shifts else None
    metrics_repo.insert(
        message_id=message_id,
        s_t=float(s_t),
        novelty=float(novelty),
        deficit=float(metrics.get("homeostatic_deficit", 0.0)),
        rolling_entropy=float(metrics["rolling_entropy"]) if metrics.get("rolling_entropy") is not None else None,
        coupling=float(metrics["coupling_coherence"]) if metrics.get("coupling_coherence") is not None else None,
        agent_divergence=float(metrics["agent_self_divergence"]) if metrics.get("agent_self_divergence") is not None else None,
        reverse_perturbation=float(metrics["reverse_perturbation"]) if metrics.get("reverse_perturbation") is not None else None,
        surprise_index=float(metrics["surprise_index"]) if metrics.get("surprise_index") is not None else None,
        mutual_perturbation=float(metrics["mutual_perturbation"]) if metrics.get("mutual_perturbation") is not None else None,
        vitality=float(metrics["conversation_vitality"]) if metrics.get("conversation_vitality") is not None else None,
        phase_shifts=phase_shifts_json,
        boringness=float(metrics["boringness"]) if metrics.get("boringness") is not None else None,
        conceptual_velocity=float(metrics["conceptual_velocity"]) if metrics.get("conceptual_velocity") is not None else None,
        divergence_resolution_ratio=float(metrics["divergence_resolution_ratio"]) if metrics.get("divergence_resolution_ratio") is not None else None,
        paskian_health=float(metrics["paskian_health"]) if metrics.get("paskian_health") is not None else None,
    )


def extract_human_summary(raw_output: str) -> str:
    """Extract the human-readable CONSOLIDATION SUMMARY block from raw LLM output."""
    m = re.search(
        r"---\s*CONSOLIDATION SUMMARY\s*---\s*\n(.*?)\n\s*---\s*END SUMMARY\s*---",
        raw_output, re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return ""
