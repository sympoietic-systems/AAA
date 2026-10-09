"""Bounded lineage observations; repetition and declared ancestry never verify warrant."""

import hashlib
from typing import Any

POLICY = "belief-source-accounting-v1"


def observation(encounter: dict[str, Any]) -> dict[str, Any]:
    source = encounter["source"]
    lineage = encounter["lineage"]
    edges: dict[str, set[str]] = {}
    for entry in lineage:
        edges.setdefault(entry["source_id"], set()).update(entry["parent_sources"])
    if source["source_id"]:
        edges.setdefault(source["source_id"], set())
    roots: set[str] = set()
    issues: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, path: frozenset[str]) -> None:
        if node in path:
            issues.add("cyclic_ancestry")
            return
        if node in visited:
            return
        visited.add(node)
        parents = edges.get(node, set())
        if not parents:
            roots.add(node)
        else:
            for parent in parents:
                visit(parent, path | {node})

    if sum(len(parents) + 1 for parents in edges.values()) <= 200:
        for node in edges:
            visit(node, frozenset())
    else:
        issues.add("ancestry_graph_exceeds_bound")
    if not roots:
        issues.add("upstream_identity_unresolved")
    if source["context_status"] != "available":
        issues.add("source_context_" + source["context_status"])
    if (
        not lineage
        or source["activity"] == "unknown"
        or any(entry["independence_status"] in {"unknown", "derived"} or entry["uncertainty"] for entry in lineage)
    ):
        issues.add("upstream_independence_unknown")
    if any(entry["independence_status"] == "independent" for entry in lineage):
        issues.add("declared_independence_not_verified")
    internal = source["activity"] == "internal" or any(entry["independence_status"] == "internal" for entry in lineage)
    if internal:
        issues.add("internal_activity_is_not_independent_warrant")
    issues.add("representation_identity_is_not_warrant")
    groups = [
        hashlib.sha256((encounter["agent_id"] + ":lineage:" + root).encode()).hexdigest() for root in sorted(roots)
    ]
    return {
        "policy_version": POLICY,
        "encounter_id": encounter["id"],
        "agent_id": encounter["agent_id"],
        "statement_sha256": encounter["statement_sha256"],
        "scope": encounter["scope"],
        "temporal_scope": encounter["temporal_scope"],
        "source": source,
        "lineage": lineage,
        "source_group_keys": groups,
        "grouping_basis": "declared_local_ancestry_identity",
        "grouping_complete": not bool(
            issues & {"cyclic_ancestry", "ancestry_graph_exceeds_bound", "upstream_identity_unresolved"}
        ),
        "internal_activity": internal,
        "verified_independent_groups": 0,
        "independent_warrant": "unverified",
        "uncertainty": sorted(issues),
        "observed_at": encounter["received_at"],
    }
