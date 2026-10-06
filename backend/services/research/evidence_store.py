"""Record extraction and legacy interpretation without inventing semantic support."""

import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from backend.core.logging_config import mask_secrets
from backend.services.research.action_journal import input_hash
from backend.storage.repositories.research.evidence import ResearchEvidenceRepository
from backend.storage.research_evidence import (
    ClaimEvidence,
    DecisionReceipt,
    EvidenceExclusion,
    EvidenceSegment,
    ParserQuality,
    ResearchContract,
    SourceArtifact,
    SourceReference,
    text_hash,
)
from backend.storage.research_receipts import EvidencePacket


class ResearchEvidenceStore:
    def __init__(self, repo: ResearchEvidenceRepository):
        self.repo = repo

    @staticmethod
    def initial_contract(task_id: str, state: dict[str, Any], policy_version: int) -> ResearchContract:
        return ResearchContract(
            task_id=task_id,
            objective=state["objective"],
            policy_version=policy_version,
            mode="document" if state.get("inject_file_id") or state.get("injected_documents") else "research",
            resource_ceilings={"budget_limit_usd": state["budget"], "max_depth": state["max_depth"]},
        )

    def record_text(
        self,
        task_id: str,
        url: str,
        content: str,
        *,
        reused: bool = False,
        quality: ParserQuality | None = None,
        unavailable_reason: str = "empty_extraction",
        observed_at: datetime | None = None,
    ) -> tuple[SourceArtifact, tuple[EvidenceSegment, ...]]:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Evidence URL must be an HTTP source without embedded credentials")
        canonical = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, ""))
        source_id = "source:" + text_hash(canonical)
        quality = quality or ParserQuality(warnings=("parser_route_unobserved", "original_bytes_unavailable"))
        if reused:
            quality = quality.model_copy(update={"warnings": quality.warnings + ("legacy_cache_may_be_truncated",)})
        return self._record_representation(
            task_id,
            source_id,
            content,
            canonical,
            None,
            "legacy_step_result_text_v1" if reused else "sensory_text_v1",
            quality,
            None if reused else (observed_at or datetime.now(UTC)),
            unavailable_reason,
        )

    def record_document(
        self, task_id: str, authorized_file_ref: str, content: str
    ) -> tuple[SourceArtifact, tuple[EvidenceSegment, ...]]:
        return self._record_representation(
            task_id,
            "source:" + text_hash(authorized_file_ref),
            content,
            None,
            authorized_file_ref,
            "indexed_document_context_v1",
            ParserQuality(
                warnings=(
                    "original_bytes_unavailable",
                    "selected_indexed_chunks",
                    "context_includes_breadcrumbs_and_separators",
                )
            ),
            None,
            "no_indexed_content",
        )

    def _record_representation(
        self,
        task_id: str,
        source_id: str,
        content: str,
        canonical_url: str | None,
        authorized_file_ref: str | None,
        representation: str,
        quality: ParserQuality,
        acquired_at: datetime | None,
        unavailable_reason: str,
    ) -> tuple[SourceArtifact, tuple[EvidenceSegment, ...]]:
        if len(content) > 2_000_000:
            raise ValueError("Evidence representation exceeds text limit")
        version = input_hash(
            {
                "representation": representation,
                "observed_at": acquired_at.isoformat() if acquired_at and content else None,
                "text_hash": text_hash(content),
                "quality": quality.model_dump(mode="json"),
                "unavailable_reason": unavailable_reason if not content else None,
            }
        )
        artifact = SourceArtifact(
            task_id=task_id,
            source_id=source_id,
            source_version=version,
            canonical_url=canonical_url,
            authorized_file_id=authorized_file_ref,
            acquired_at=acquired_at if content else None,
            representation=representation,
            representation_hash=text_hash(content) if content else None,
            fetch_status="available" if content else "unavailable",
            unavailable_reason=None if content else unavailable_reason,
            quality=quality,
        )
        segments = tuple(
            EvidenceSegment(
                task_id=task_id,
                segment_id="segment:"
                + input_hash(
                    {"source": source_id, "version": version, "start": start, "end": min(start + 2000, len(content))}
                ),
                source_id=source_id,
                source_version=version,
                representation=representation,
                start=start,
                end=min(start + 2000, len(content)),
                text=content[start : start + 2000],
                text_hash=text_hash(content[start : start + 2000]),
                quality=quality,
            )
            for start in range(0, len(content), 2000)
        )
        return self.repo.put_source(artifact, content, segments), segments

    def record_interpretation(
        self, task_id: str, state: dict[str, Any], source: SourceArtifact, result: dict[str, Any]
    ) -> tuple[str, ...]:
        policy = state["action_journal_policy"]
        revision = state.get("contract_revision", 1)
        ref = SourceReference(source_id=source.source_id, source_version=source.source_version)
        ids = []
        learnings = result.get("learnings") or []
        if not isinstance(learnings, list):
            raise ValueError("Legacy learnings must be a list, not implicit character claims")
        for item in learnings[:50]:
            if not isinstance(item, str) or not item.strip():
                continue
            claim_id = "claim:" + input_hash(
                {"action": state["active_action_id"], "source": ref.model_dump(), "text": item}
            )
            objections = ("semantic_support_unreviewed", "no_anchor_in_legacy", *source.quality.warnings)
            notes = result.get("diffractive_notes") or []
            if isinstance(notes, list):
                objections += tuple(mask_secrets(note) for note in notes[:10] if isinstance(note, str))
            claim = ClaimEvidence(
                task_id=task_id,
                claim_id=claim_id,
                contract_revision=revision,
                text=mask_secrets(item),
                source_lineage=(ref,),
                inference_label="interpretation",
                support_status="unverified",
                unresolved_objections=objections,
            )
            self.repo.put_claim(claim)
            ids.append(claim_id)
        candidate = source.source_id + "@" + source.source_version
        exclusion = None
        if not ids:
            exclusion = EvidenceExclusion(
                candidate_id=candidate,
                reason="no_anchor_in_legacy",
                explanation="Legacy digest returned no claims; parser and relevance causes remain unadjudicated",
            )
        self.repo.put_decision(
            DecisionReceipt(
                task_id=task_id,
                decision_id="decision:" + str(uuid.uuid4()),
                action_id=state["active_action_id"],
                input_hash=input_hash({"source": candidate, "result": result}),
                contract_hash=policy["contract_hash"],
                policy_hash=policy["policy_hash"],
                allowed_actions=("digesting",),
                candidate_ids=(candidate,),
                selected_ids=(candidate,) if ids else (),
                exclusions=(exclusion,) if exclusion else (),
                abstained=not bool(ids),
                fallback_reason="no_claims_returned" if not ids else None,
            )
        )
        return tuple(ids)

    @staticmethod
    def packet(
        source: SourceArtifact, claim_ids: tuple[str, ...] = (), segments: tuple[EvidenceSegment, ...] = ()
    ) -> EvidencePacket:
        return EvidencePacket(
            source_id=source.source_id,
            source_version=source.source_version,
            representation=source.representation,
            representation_span_locators=tuple(segment.locator() for segment in segments),
            claim_ids=claim_ids,
            extraction_method=source.quality.method,
            extraction_quality=source.quality.score,
            unavailable_evidence={source.source_id: source.unavailable_reason or "unknown"}
            if source.fetch_status != "available"
            else {},
            unresolved_gaps=("semantic_support_unreviewed",) if claim_ids else (),
        )
