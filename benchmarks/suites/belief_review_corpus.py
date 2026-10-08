"""Source-bound Beliefs v2 review packets; offline validation never calls an evaluator.

Collection is an explicit GET-only command, separate from preparation and freezing.
"""

import argparse
import copy
import hashlib
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

from backend.core.logging_config import mask_secrets
from benchmarks.suites.calibration_contract import digest, validate_splits

RELATIONS = {"equivalent", "extension", "contradiction", "distinct", "insufficient_context", "no_comparison"}
WARRANTS = {"empirical", "artistic", "tension", "mixed", "unknown"}


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def annotation_binding(case: dict[str, Any]) -> str:
    return digest({"a": case["a"], "b": case["b"], "source_snapshot_sha256": case["source_snapshot_sha256"]})


def safe_text(text: str, secrets: tuple[str, ...] = ()) -> str:
    for secret in secrets:
        if len(secret) >= 8:
            text = text.replace(secret, "[REDACTED]")
    return mask_secrets(text)


def source_key(trace: dict[str, Any]) -> str:
    if trace.get("conversation_id"):
        return "conversation:" + str(trace["conversation_id"])
    return str(trace.get("type", "unknown")) + ":" + str(trace.get("id", "unknown"))


def passage(message: dict[str, Any], *, secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    content = str(message.get("content") or "")
    cleaned = safe_text(content, secrets)
    return {
        "message_id": str(message["id"]),
        "speaker": message.get("speaker"),
        "timestamp": message.get("timestamp"),
        "model_used": message.get("model_used"),
        "provider_used": message.get("provider_used"),
        "source_content_sha256": text_hash(content),
        "sanitized_content_sha256": text_hash(cleaned),
        "content": cleaned[:12000],
        "excerpt_sha256": text_hash(cleaned[:12000]),
        "truncated": len(cleaned) > 12000,
        "redaction_policy": "known-credential-values+mask-secrets-v1",
        "redacted": content != cleaned,
    }


def collect(proposals: list[dict[str, Any]], client: httpx.Client, secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    """Bounded GETs of referenced sources; absence is an explicit record, never a verdict."""
    traces = {source_key(t): t for p in proposals for t in p.get("source_trace", [])}
    if len(traces) > 100:
        raise ValueError("Source recovery is bounded to 100 references")
    sources: dict[str, Any] = {}
    for key, trace in sorted(traces.items()):
        row: dict[str, Any] = {"source_key": key, "retrieved_at": datetime.now(UTC).isoformat()}
        try:
            if trace.get("conversation_id"):
                response = client.get("history", params={"conversation_id": trace["conversation_id"], "limit": 50})
                route = "/history?conversation_id=" + str(trace["conversation_id"]) + "&limit=50"
            elif trace.get("type") == "chat_turn" and str(trace.get("id", "")).isdigit():
                route = "/messages/" + str(trace["id"]) + "/path"
                response = client.get(route.lstrip("/"))
            else:
                sources[key] = {**row, "status": "unavailable", "reason": "no_supported_source_read", "passages": []}
                continue
            row.update(route=route, http_status=response.status_code)
            if response.status_code in (401, 403):
                raise PermissionError("Source recovery authentication failed")
            if response.status_code != 200:
                sources[key] = {**row, "status": "unavailable", "reason": "source_http_failure", "passages": []}
                continue
            data = response.json()
            if trace.get("conversation_id"):
                messages = data["messages"]
                row["reported_count"] = data["count"]
                row["coverage"] = "returned_conversation"
                if data["count"] > 50:
                    older = client.get(
                        "history", params={"conversation_id": trace["conversation_id"], "limit": 50, "offset": 50}
                    )
                    if older.status_code in (401, 403):
                        raise PermissionError("Source recovery authentication failed")
                    older.raise_for_status()
                    known = {m["id"] for m in messages}
                    messages += [m for m in older.json()["messages"] if m["id"] not in known]
                    row["coverage"] = "latest_100" if data["count"] > 100 else "returned_conversation_two_pages"
                    row["pagination_consistency"] = "live_offset_pages_not_atomic_snapshot"
            else:
                # The path supplies only the referenced message and its immediate predecessor.
                messages = data
                position = next((i for i, m in enumerate(messages) if str(m["id"]) == str(trace["id"])), None)
                messages = messages[max(0, position - 1) : position + 1] if position is not None else []
                row["coverage"] = "referenced_message_and_predecessor"
            sources[key] = {
                **row,
                "status": "available" if messages else "unavailable",
                "reason": None if messages else "source_not_returned",
                "passages": [passage(m, secrets=secrets) for m in messages],
            }
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            sources[key] = {**row, "status": "unavailable", "reason": "recovery_" + type(exc).__name__, "passages": []}
    return {"method": "authenticated_GET_only", "sources": sources}


def snapshot(record: dict[str, Any]) -> dict[str, Any]:
    statement = safe_text(record["statement"])
    return {
        "id": record["id"],
        "label": record["label"],
        "statement": statement,
        "statement_sha256": text_hash(statement),
        "legacy_status": record.get("proposal_status", record.get("lifecycle_stage")),
        "version": record.get("version"),
        "scope": None,
        "temporal_scope": None,
        "scope_status": "requires_review",
        "canonical_review_state": None,
        "record_kind": "skill_projection"
        if str(record["id"]).startswith("skill:")
        else "proposal"
        if record.get("proposal_status")
        else "belief",
    }


def assign_splits(cases: list[dict[str, Any]]) -> None:
    """Connected records, comparison hubs and source ancestry stay in one partition."""
    parent: dict[str, str] = {}

    def root(key: str) -> str:
        parent.setdefault(key, key)
        if parent[key] != key:
            parent[key] = root(parent[key])
        return parent[key]

    for case in cases:
        entities = case["split_entities"]
        first = root(entities[0])
        for entity in entities[1:]:
            parent[root(entity)] = first
    groups: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        groups.setdefault(root(case["split_entities"][0]), []).append(case)
    counts = {"tune": 0, "validation": 0, "heldout": 0}
    targets = {"tune": len(cases) * 0.2, "validation": len(cases) * 0.2, "heldout": len(cases) * 0.6}
    for _, group in sorted(groups.items(), key=lambda item: (-len(item[1]), digest(sorted(c["id"] for c in item[1])))):
        split = max(counts, key=lambda name: targets[name] - counts[name])
        family = digest(sorted(c["id"] for c in group))[:20]
        for case in group:
            case.update(split=split, family_id=family)
            case["split_entities"].append("family:" + family)
        counts[split] += len(group)
    validate_splits(cases)


def prepare(proposals: list[dict[str, Any]], beliefs: list[dict[str, Any]], recovery: dict[str, Any]) -> dict[str, Any]:
    if not 1 <= len(proposals) <= 100:
        raise ValueError("Expected 1..100 saved proposals")
    records = {r["id"]: r for r in beliefs + proposals}
    cases = []
    for p in sorted(proposals, key=lambda r: r["id"]):
        target = records.get(p.get("potential_merge_target"))
        candidate_refs = sorted({source_key(t) for t in p.get("source_trace", [])})
        comparison_refs = sorted({source_key(t) for t in target.get("source_trace", [])}) if target else []
        refs = sorted(set(candidate_refs + comparison_refs))
        case = {
            "id": "proposal:" + p["id"],
            "a": snapshot(p),
            "b": snapshot(target) if target else None,
            "comparison_basis": "historical_model_nomination" if target else "no_saved_comparison",
            "source_refs": refs,
            "candidate_source_refs": candidate_refs,
            "comparison_source_refs": comparison_refs,
            "comparison_context_status": "not_applicable"
            if target is None
            else "available"
            if comparison_refs
            and all(recovery["sources"].get(r, {}).get("status") == "available" for r in comparison_refs)
            else "unavailable",
            "source_binding": "legacy_trace_reference_not_emission_proof",
            "source_snapshot_sha256": digest({r: recovery["sources"].get(r) for r in refs}),
            "lineage_baseline": {
                "independence_status": "unknown",
                "activity": "internal"
                if any(t.get("type") == "intention" for t in p.get("source_trace", []))
                else "unknown",
                "reason": "Shared source identity groups ancestry; recurrence and internal formulation supply no independent corroboration",
            },
            "context_status": "available"
            if candidate_refs
            and all(recovery["sources"].get(r, {}).get("status") == "available" for r in candidate_refs)
            else "unavailable",
            "split_entities": ["record:" + p["id"]]
            + ["source:" + r for r in refs]
            + (["record:" + target["id"]] if target else []),
            "annotations": [],
            "author_model": "unknown_legacy_author",
            "author_independence_status": "unverified",
            "review_requirements": [
                "source_binding",
                "scope",
                "temporal_scope",
                "lineage",
                "consequence",
                "challenge",
                "warrant",
                "relation",
                "useful_distinction_or_conflict",
            ],
        }
        cases.append(case)
        case["review_input_sha256"] = annotation_binding(case)
    assign_splits(cases)
    packet = {
        "schema_version": 2,
        "agent_id": "symbia",
        "purpose": "independent review of saved v1 proposals; not adoption commands",
        "cases": cases,
        "recovery": recovery,
        "frozen": False,
        "annotation_status": "UNREVIEWED",
        "promotion": "BLOCKED",
        "manifest_sha256": digest(cases),
    }
    packet["coverage"] = {
        "legacy_statuses": dict(Counter(c["a"]["legacy_status"] for c in cases)),
        "context_statuses": dict(Counter(c["context_status"] for c in cases)),
        "comparison_context_statuses": dict(Counter(c["comparison_context_status"] for c in cases)),
        "splits": dict(Counter(c["split"] for c in cases)),
        "families": len({c["family_id"] for c in cases}),
    }
    return packet


def validate(packet: dict[str, Any]) -> None:
    cases = packet["cases"]
    if not 1 <= len(cases) <= 100:
        raise ValueError("Packet requires 1..100 cases")
    validate_splits(cases)
    if packet["manifest_sha256"] != digest(cases):
        raise ValueError("Packet manifest changed")
    for case in cases:
        if case["review_input_sha256"] != annotation_binding(case):
            raise ValueError("Review input binding changed")
        for side in ("a", "b"):
            record = case[side]
            if record and record["statement_sha256"] != text_hash(record["statement"]):
                raise ValueError("Statement binding changed")
        for key in case["source_refs"]:
            source = packet["recovery"]["sources"].get(key)
            if source is None or source["status"] not in ("available", "unavailable"):
                raise ValueError("Source must be available or explicitly unavailable")
        if case["source_snapshot_sha256"] != digest(
            {r: packet["recovery"]["sources"].get(r) for r in case["source_refs"]}
        ):
            raise ValueError("Case source snapshot changed")
    for source in packet["recovery"]["sources"].values():
        for item in source["passages"]:
            if text_hash(item["content"]) != item["excerpt_sha256"]:
                raise ValueError("Recovered passage changed")
    if packet.get("frozen") and packet.get("frozen_sha256") != digest({"cases": cases, "recovery": packet["recovery"]}):
        raise ValueError("Frozen corpus changed")


def freeze(packet: dict[str, Any]) -> dict[str, Any]:
    validate(packet)
    packet = copy.deepcopy(packet)
    if {c["split"] for c in packet["cases"]} != {"tune", "validation", "heldout"}:
        raise ValueError("All three disjoint partitions are required")
    for case in packet["cases"]:
        annotations = case["annotations"]
        if not annotations:
            raise ValueError("Independent review required for every case")
        # Legacy author provenance is unknown. Model-only declarations cannot prove independence.
        humans = [
            a
            for a in annotations
            if a.get("method") == "human" and a.get("independent") is True and a.get("annotator_id")
        ]
        if not humans:
            raise ValueError("Independent human review required while legacy author is unknown")
        for a in annotations:
            if a.get("case_sha256") != annotation_binding(case):
                raise ValueError("Annotation must bind current claims and sources")
            if a.get("relation") not in RELATIONS or a.get("warrant") not in WARRANTS:
                raise ValueError("Unknown annotation relation or warrant")
            if case["b"] is not None and a["relation"] == "no_comparison":
                raise ValueError("Existing comparison requires a relation or insufficient_context")
            for field in (
                "scope",
                "temporal_scope",
                "lineage",
                "consequence",
                "challenge",
                "rationale",
                "useful_distinction_or_conflict",
            ):
                if not isinstance(a.get(field), str) or not a[field].strip() or len(a[field]) > 4000:
                    raise ValueError("Annotation requires bounded " + field)
            if (case["context_status"] == "unavailable" or case["comparison_context_status"] == "unavailable") and a[
                "relation"
            ] not in (
                "insufficient_context",
                "no_comparison",
            ):
                raise ValueError("Unavailable sources cannot establish semantic relation")
        case["review_outcome"] = (
            "disagreement" if len({(a["relation"], a["warrant"]) for a in annotations}) > 1 else "reviewed"
        )
    result = copy.deepcopy(packet)
    result.update(frozen=True, annotation_status="INDEPENDENTLY_REVIEWED", promotion="BLOCKED")
    result["manifest_sha256"] = digest(result["cases"])
    result["frozen_sha256"] = digest({"cases": result["cases"], "recovery": result["recovery"]})
    return result


def annotate(packet: dict[str, Any], submissions: list[dict[str, Any]]) -> dict[str, Any]:
    validate(packet)
    if packet.get("frozen"):
        raise ValueError("Frozen corpus cannot accept new annotations")
    if not 1 <= len(submissions) <= 100:
        raise ValueError("Expected 1..100 annotations")
    result = copy.deepcopy(packet)
    cases = {c["id"]: c for c in result["cases"]}
    for submission in submissions:
        case = cases.get(submission["case_id"])
        if case is None or submission.get("case_sha256") != annotation_binding(case):
            raise ValueError("Annotation refers to unknown or changed case")
        if any(a.get("annotator_id") == submission.get("annotator_id") for a in case["annotations"]):
            raise ValueError("Reviewer already annotated this case; retain original receipt")
        case["annotations"].append(copy.deepcopy(submission))
    result["manifest_sha256"] = digest(result["cases"])
    result["annotation_status"] = "REVIEW_IN_PROGRESS"
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("collect", "prepare", "annotate", "validate", "freeze"))
    parser.add_argument("--proposals", type=Path)
    parser.add_argument("--beliefs", type=Path)
    parser.add_argument("--recovery", type=Path)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    required = {
        "collect": ("proposals",),
        "prepare": ("proposals", "beliefs", "recovery"),
        "annotate": ("packet", "annotations"),
        "validate": ("packet",),
        "freeze": ("packet",),
    }
    if any(getattr(args, name) is None for name in required[args.action]):
        parser.error("missing required input for " + args.action)
    if args.action != "validate" and (args.output is None or args.output.exists()):
        parser.error("output must be a fresh path")

    def read(path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    if args.action == "collect":
        values = {**dotenv_values(".env"), **os.environ}
        token = values.get("AAA_PASSWORD")
        if not token:
            parser.error("AAA_PASSWORD is required")
        secrets = tuple(str(v) for k, v in values.items() if v and ("API_KEY" in k or k == "AAA_PASSWORD"))
        # Fixed production authority; credentials are never forwarded on redirects.
        with httpx.Client(
            base_url="https://aaa.sympoietic.systems/api/",
            headers={"Authorization": "Bearer " + token},
            timeout=30,
            follow_redirects=False,
        ) as client:
            result = collect(read(args.proposals), client, secrets)
    elif args.action == "prepare":
        result = prepare(read(args.proposals), read(args.beliefs)["beliefs"], read(args.recovery))
    elif args.action == "freeze":
        result = freeze(read(args.packet))
    elif args.action == "annotate":
        result = annotate(read(args.packet), read(args.annotations))
    else:
        validate(read(args.packet))
        print("Packet bindings and split integrity passed; this is not semantic review")
        return
    if args.output is None or args.output.exists():
        parser.error("output must be a fresh path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
